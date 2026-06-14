"""
Servico CNAB - Geracao de Remessa e Processamento de Retorno

Integra com boleto_cnab_api para geracao de arquivos CNAB 240/400.

API boleto_cnab_api: https://github.com/Maxwbh/boleto_cnab_api
Docker: docker run -p 9292:9292 maxwbh/boleto_cnab_api

Endpoints utilizados:
- POST /api/remessa  - Gerar arquivo CNAB remessa (240/400)
- POST /api/retorno  - Processar arquivo CNAB retorno

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
import io
import json
import re
import time
import logging
import requests
import base64
from decimal import Decimal
from datetime import datetime
from typing import Dict, List

from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


# Mapeamento de bancos para o BRCobranca
# Fonte única: financeiro.services.bancos.BANCOS_SUPORTADOS
from .bancos import BANCOS_SUPORTADOS as _BANCOS
BANCOS_BRCOBRANCA = {cod: spec['brcobranca_id'] for cod, spec in _BANCOS.items()}

# Codigos de ocorrencia padrao CNAB
OCORRENCIAS_CNAB = {
    '01': ('ENTRADA', 'Entrada Confirmada'),
    '02': ('ENTRADA', 'Entrada Confirmada'),
    '03': ('REJEICAO', 'Entrada Rejeitada'),
    '06': ('LIQUIDACAO', 'Liquidacao Normal'),
    '09': ('BAIXA', 'Baixa'),
    '10': ('BAIXA', 'Baixa por Solicitacao'),
    '11': ('BAIXA', 'Baixa por Protesto'),
    '14': ('BAIXA', 'Baixa por Devolucao'),
    '17': ('LIQUIDACAO', 'Liquidacao apos Baixa'),
    '19': ('TARIFA', 'Confirmacao de Instrucao de Protesto'),
    '23': ('PROTESTO', 'Entrada em Cartorio'),
    '25': ('PROTESTO', 'Protestado e Baixado'),
    '27': ('TARIFA', 'Tarifa'),
}


class CNABService:
    """
    Servico para geracao de arquivos de remessa e processamento de retorno.
    Integra com a API boleto_cnab_api (Docker container).

    Endpoints:
    - POST /api/remessa - Gerar arquivo CNAB remessa
    - POST /api/retorno - Processar arquivo CNAB retorno
    """

    def __init__(self):
        # URL do servico boleto_cnab_api (container Docker)
        # https://github.com/Maxwbh/boleto_cnab_api
        self.brcobranca_url = getattr(
            settings,
            'BRCOBRANCA_URL',
            'http://localhost:9292'
        )
        self.timeout = getattr(settings, 'BRCOBRANCA_TIMEOUT', 30)
        self.max_tentativas = getattr(settings, 'BRCOBRANCA_MAX_TENTATIVAS', 3)
        self.delay_inicial = getattr(settings, 'BRCOBRANCA_DELAY_INICIAL', 2)

    def _get_banco_brcobranca(self, codigo_banco: str) -> str:
        """Retorna o nome do banco para o BRCobranca"""
        return BANCOS_BRCOBRANCA.get(codigo_banco, 'banco_brasil')

    def _formatar_cpf_cnpj(self, documento: str) -> str:
        """Remove formatacao do CPF/CNPJ"""
        if documento:
            return documento.replace('.', '').replace('-', '').replace('/', '')
        return ''

    def _formatar_data(self, data) -> str:
        """
        Formata data para o padrao BRCobranca (YYYY/MM/DD).
        Aceita date, datetime (naive ou aware). Para datetime aware, converte
        para hora local antes de extrair a data (evita problema de fuso UTC-3).
        """
        if data is None:
            return ''
        if hasattr(data, 'tzinfo') and data.tzinfo is not None:
            # datetime timezone-aware: converter para local antes de .date()
            from django.utils import timezone as _tz
            data = _tz.localtime(data).date()
        elif hasattr(data, 'date') and callable(data.date):
            # datetime naive: extrair date
            data = data.date()
        # agora é um objeto date
        return data.strftime('%Y/%m/%d')

    def _formatar_valor(self, valor) -> float:
        """Formata valor para float"""
        if valor:
            try:
                return float(valor)
            except (ValueError, TypeError):
                return 0.0
        return 0.0

    def _buscar_parcela_por_nosso_numero(self, nosso_numero: str, conta_bancaria=None):
        """
        Busca Parcela pelo nosso_numero com fallback de strip de zeros à esquerda.

        Estratégia (por conta_bancaria quando fornecida):
        1. Exact match + conta_bancaria
        2. endswith(stripped) + conta_bancaria  ← CNAB envia zero-padded, DB pode ter curto
        3. Exact match global
        4. endswith(stripped) global
        """
        from financeiro.models import Parcela
        nn_stripped = nosso_numero.lstrip('0') if nosso_numero else ''

        if conta_bancaria:
            qs_conta = Parcela.objects.filter(conta_bancaria=conta_bancaria)
            parcela = qs_conta.filter(nosso_numero=nosso_numero).first()
            if not parcela and nn_stripped:
                parcela = qs_conta.filter(nosso_numero__endswith=nn_stripped).first()
            if parcela:
                return parcela

        # Fallback global (sem filtro de conta)
        parcela = Parcela.objects.filter(nosso_numero=nosso_numero).first()
        if not parcela and nn_stripped:
            parcela = Parcela.objects.filter(nosso_numero__endswith=nn_stripped).first()
        return parcela

    def _parsear_numero_dv(self, valor: str) -> tuple:
        """Separa número e dígito verificador. Aceita '1234-5' ou '1234 5' ou '1234'."""
        if not valor:
            return '', ''
        for sep in ['-', ' ']:
            if sep in valor:
                partes = valor.split(sep, 1)
                return partes[0].strip(), partes[1].strip()
        return valor.strip(), ''

    def _montar_dados_boleto(self, parcela, conta_bancaria) -> dict:
        """
        Monta os dados de um boleto para o BRCobranca.
        """
        contrato = parcela.contrato
        comprador = contrato.comprador
        imobiliaria = contrato.imobiliaria

        # Determinar tipo de documento do comprador
        cpf_cnpj = self._formatar_cpf_cnpj(
            comprador.cnpj if comprador.cnpj else comprador.cpf
        )

        # Montar endereco completo
        endereco_sacado = f"{comprador.endereco or ''}"
        if comprador.numero:
            endereco_sacado += f", {comprador.numero}"
        if comprador.complemento:
            endereco_sacado += f" - {comprador.complemento}"

        agencia_num, agencia_dv = self._parsear_numero_dv(conta_bancaria.agencia)
        conta_num, conta_dv = self._parsear_numero_dv(conta_bancaria.conta)

        convenio = conta_bancaria.convenio or ''
        # Para Banco do Brasil, convenio é obrigatório; formata com zeros à esquerda (7 dígitos)
        if conta_bancaria.banco == '001' and convenio:
            convenio = ''.join(filter(str.isdigit, convenio)).zfill(7)[:8]

        boleto_data = {
            # Identificacao
            'nosso_numero': str(parcela.nosso_numero or '1'),
            'documento_numero': parcela.numero_documento or '',

            # Valores e datas
            'valor': self._formatar_valor(parcela.valor_boleto or parcela.valor_atual),
            'data_vencimento': self._formatar_data(parcela.data_vencimento),
            # _formatar_data lida corretamente com datetime aware (UTC→local)
            'data_documento': self._formatar_data(
                parcela.data_geracao_boleto if parcela.data_geracao_boleto else timezone.now()
            ),

            # Campos obrigatórios da classe Base BRCobranca
            'moeda': '9',
            'especie': 'R$',
            'especie_documento': 'DM',
            'aceite': 'S',

            # Dados do sacado (pagador) — nomes corretos do BRCobranca
            'sacado': comprador.nome[:60],
            'sacado_documento': cpf_cnpj,
            'sacado_endereco': endereco_sacado[:80],

            # Dados do cedente (recebedor)
            'cedente': (imobiliaria.razao_social or imobiliaria.nome)[:60],
            'documento_cedente': self._formatar_cpf_cnpj(imobiliaria.cnpj),

            # Dados bancários
            'agencia': agencia_num,
            'conta_corrente': conta_num,
            'convenio': convenio,
            'carteira': conta_bancaria.carteira or '',

            # Instrucoes
            'instrucao1': f'Parcela {parcela.numero_parcela}/{contrato.numero_parcelas} - Contrato {contrato.numero_contrato}',
            'instrucao2': '',
            'instrucao3': '',
            'instrucao4': '',

            # Local de pagamento
            'local_pagamento': 'Pagavel em qualquer banco ate o vencimento',
        }

        # Campos específicos por banco
        banco = conta_bancaria.banco

        # Sicredi (748): posto e byte_idt obrigatórios
        if banco == '748':
            boleto_data['posto'] = getattr(conta_bancaria, 'posto', '') or '01'
            boleto_data['byte_idt'] = getattr(conta_bancaria, 'byte_idt', '') or '2'

        # Caixa Econômica (104): emissao e codigo_beneficiario obrigatórios
        elif banco == '104':
            boleto_data['emissao'] = getattr(conta_bancaria, 'emissao', '') or '4'
            codigo_benef = getattr(conta_bancaria, 'codigo_beneficiario', '') or conta_bancaria.convenio or ''
            boleto_data['codigo_beneficiario'] = codigo_benef

        # Sicoob (756): variacao e quantidade
        elif banco == '756':
            boleto_data['variacao'] = '01'
            boleto_data['quantidade'] = '001'
            codigo_benef = getattr(conta_bancaria, 'codigo_beneficiario', '')
            if codigo_benef:
                boleto_data['codigo_beneficiario'] = codigo_benef

        return boleto_data

    def _montar_dados_pagamento_remessa(self, parcela, conta_bancaria) -> dict:
        """
        Monta dados de pagamento para a API /api/remessa (Brcobranca::Remessa::Pagamento).

        Os campos do Pagamento de remessa seguem o schema Pagamento da spec OpenAPI:
        sacado, sacado_documento, sacado_endereco, sacado_cidade, sacado_uf, sacado_cep
        """
        contrato = parcela.contrato
        comprador = contrato.comprador

        cpf_cnpj = self._formatar_cpf_cnpj(
            comprador.cnpj if getattr(comprador, 'cnpj', None) else comprador.cpf
        )

        logradouro = getattr(comprador, 'logradouro', None) or getattr(comprador, 'endereco', None) or ''
        numero_end = getattr(comprador, 'numero', '') or ''
        rua = f"{logradouro}, {numero_end}".strip(', ') if numero_end else logradouro

        bairro = getattr(comprador, 'bairro', '') or ''
        cidade = getattr(comprador, 'cidade', '') or ''
        uf = getattr(comprador, 'estado', '') or ''
        cep = re.sub(r'\D', '', getattr(comprador, 'cep', '') or '')[:8].zfill(8)

        from django.utils import timezone as _tz
        data_emissao = (
            parcela.data_geracao_boleto if parcela.data_geracao_boleto
            else _tz.now()
        )

        return {
            'nosso_numero': str(parcela.nosso_numero or '1'),
            'numero': (parcela.numero_documento or '')[:25],
            'valor': self._formatar_valor(parcela.valor_boleto or parcela.valor_atual),
            'data_vencimento': self._formatar_data(parcela.data_vencimento),
            'data_emissao': self._formatar_data(data_emissao),
            'sacado': comprador.nome[:40],
            'sacado_documento': cpf_cnpj,
            'sacado_endereco': rua[:40],
            'sacado_cep': cep,
            'sacado_cidade': cidade[:15],
            'sacado_uf': uf[:2],
        }

    def gerar_remessa(
        self,
        parcelas: List,
        conta_bancaria,
        layout: str = 'CNAB_240',
        arquivo_para_atualizar=None,
    ) -> Dict:
        """
        Gera arquivo de remessa CNAB para um conjunto de parcelas.

        Args:
            parcelas: Lista de parcelas com boletos gerados
            conta_bancaria: ContaBancaria para a remessa
            layout: Layout do arquivo (CNAB_240 ou CNAB_400)

        Returns:
            dict: Resultado com arquivo gerado e estatisticas
        """
        from financeiro.models import ArquivoRemessa, ItemRemessa

        # Validar conta bancária para bancos com campos obrigatórios
        if conta_bancaria.banco == '001' and not conta_bancaria.convenio:
            return {
                'sucesso': False,
                'erro': (
                    'Banco do Brasil requer o campo "Convênio" preenchido na conta bancária. '
                    'Acesse Configurações → Conta Bancária e informe o número do convênio.'
                )
            }
        if conta_bancaria.banco == '033' and not conta_bancaria.convenio:
            return {
                'sucesso': False,
                'erro': (
                    'Santander requer o campo "Convênio" preenchido na conta bancária (7 dígitos). '
                    'Acesse Configurações → Conta Bancária e informe o número do convênio.'
                )
            }
        if conta_bancaria.banco == '104' and not conta_bancaria.convenio:
            return {
                'sucesso': False,
                'erro': (
                    'Caixa Econômica requer o campo "Convênio" preenchido na conta bancária (6 dígitos). '
                    'Acesse Configurações → Conta Bancária e informe o número do convênio.'
                )
            }
        if conta_bancaria.banco == '336' and not conta_bancaria.convenio:
            return {
                'sucesso': False,
                'erro': (
                    'C6 Bank requer o campo "Convênio" (código do beneficiário, 12 dígitos) '
                    'preenchido na conta bancária. '
                    'Acesse Configurações → Conta Bancária e informe o número do convênio.'
                )
            }
        if conta_bancaria.banco == '748':
            posto = getattr(conta_bancaria, 'posto', '') or ''
            byte_idt = getattr(conta_bancaria, 'byte_idt', '') or ''
            if not posto:
                return {
                    'sucesso': False,
                    'erro': (
                        'Sicredi requer o campo "Posto" preenchido na conta bancária (2 dígitos). '
                        'Acesse Configurações → Conta Bancária e informe o Posto.'
                    )
                }
            if not byte_idt:
                return {
                    'sucesso': False,
                    'erro': (
                        'Sicredi requer o campo "Byte IDT" preenchido na conta bancária (1 dígito, geralmente "2"). '
                        'Acesse Configurações → Conta Bancária e informe o Byte IDT.'
                    )
                }

        # Validar parcelas
        parcelas_validas = [p for p in parcelas if p.tem_boleto and not p.pago]
        if not parcelas_validas:
            return {
                'sucesso': False,
                'erro': 'Nenhuma parcela valida para remessa'
            }

        # Número de remessa: preservar o existente ao atualizar, ou incrementar
        if arquivo_para_atualizar:
            numero_remessa = arquivo_para_atualizar.numero_remessa
        else:
            ultimo = ArquivoRemessa.objects.filter(
                conta_bancaria=conta_bancaria
            ).order_by('-numero_remessa').first()
            numero_remessa = (ultimo.numero_remessa + 1) if ultimo else 1

        # Montar dados para BRCobranca
        banco = self._get_banco_brcobranca(conta_bancaria.banco)
        imobiliaria = conta_bancaria.imobiliaria

        # Agencia: CNAB240 usa até 5 dígitos (num+DV para BB), CNAB400 usa 4
        agencia_num, agencia_dv = self._parsear_numero_dv(conta_bancaria.agencia)
        conta_num, conta_dv = self._parsear_numero_dv(conta_bancaria.conta)
        if layout == 'CNAB_240' and agencia_dv:
            agencia_remessa = f"{agencia_num}{agencia_dv}"[:5]
        else:
            agencia_remessa = agencia_num

        dados_empresa = {
            'empresa_mae': imobiliaria.razao_social or imobiliaria.nome,
            'documento_cedente': self._formatar_cpf_cnpj(imobiliaria.cnpj),
            'agencia': agencia_remessa,
            'conta_corrente': conta_num,
            'digito_conta': conta_dv,
            'convenio': conta_bancaria.convenio or '',
            'carteira': conta_bancaria.carteira or '',
            'sequencial_remessa': numero_remessa,
        }

        # Campos extras por banco
        codigo_banco = conta_bancaria.banco
        carteira_str = conta_bancaria.carteira or ''
        if codigo_banco == '001':
            # BB: variacao = carteira zero-padded a 3 dígitos
            variacao = re.sub(r'\D', '', carteira_str).zfill(3)[:3]
            if layout == 'CNAB_240':
                dados_empresa['variacao'] = variacao
            else:
                dados_empresa['variacao_carteira'] = variacao
        elif codigo_banco == '237':
            # Bradesco: codigo_empresa obrigatório
            dados_empresa['codigo_empresa'] = conta_bancaria.convenio or ''
        elif codigo_banco == '336':
            # C6 Bank (CNAB400): a remessa exige 'codigo_beneficiario' (até 12 dígitos),
            # NÃO o campo 'convenio'. Carteira deve ser '10' (emissão banco) ou
            # '20' (emissão cliente) — brcobranca valida via inclusion.
            dados_empresa['codigo_beneficiario'] = re.sub(r'\D', '', conta_bancaria.convenio or '')[:12]
            if not carteira_str:
                dados_empresa['carteira'] = '10'
        elif codigo_banco == '756':
            # Sicoob: sequencial_remessa = string de 7 dígitos
            dados_empresa['sequencial_remessa'] = str(numero_remessa).zfill(7)[-7:]
            # brcobranca ≥12.9.0 normaliza automaticamente carteira (rjust 2) e convenio (rjust 9)
            # na remessa. Formatamos aqui como defesa extra para versões anteriores.
            dados_empresa['carteira'] = re.sub(r'\D', '', carteira_str).zfill(2)[:2] or '01'
            conv_digits = re.sub(r'\D', '', conta_bancaria.convenio or '')
            dados_empresa['convenio'] = conv_digits.zfill(9)[:9]

        # Pagamentos com campos corretos do Brcobranca::Remessa::Pagamento
        pagamentos = []
        valor_total = Decimal('0.00')
        for parcela in parcelas_validas:
            pagamentos.append(self._montar_dados_pagamento_remessa(parcela, conta_bancaria))
            valor_total += parcela.valor_boleto or parcela.valor_atual

        try:
            # A API /api/remessa espera multipart/form-data:
            #   - bank   → campo de formulário (ex: 'banco_brasil')
            #   - type   → campo de formulário ('cnab240' ou 'cnab400')
            #   - data   → arquivo JSON (empresa + pagamentos)
            # Resposta: conteúdo CNAB bruto (text/plain).
            tipo_cnab = 'cnab240' if layout == 'CNAB_240' else 'cnab400'
            data_remessa = {
                **dados_empresa,
                'pagamentos': pagamentos,
            }

            descricao_conta = getattr(conta_bancaria, 'descricao', None) or str(conta_bancaria)
            logger.info(
                "[Remessa] conta=%s banco=%s layout=%s boletos=%d valor=R$%.2f",
                descricao_conta, banco, tipo_cnab, len(pagamentos), float(valor_total)
            )

            if logger.isEnabledFor(logging.DEBUG) and pagamentos:
                p0 = pagamentos[0]
                logger.debug(
                    "[Remessa] payload[0] data_vencimento=%r data_emissao=%r",
                    p0.get('data_vencimento'), p0.get('data_emissao')
                )

            # Retry automático em 429 (rate limit): backoff exponencial configurável
            _response = None
            _t0 = time.monotonic()
            # pix=true ativa segmento PIX no CNAB quando conta tem chave PIX
            _params_remessa: dict = {'bank': banco, 'type': tipo_cnab}
            if getattr(conta_bancaria, 'chave_pix', ''):
                _params_remessa['pix'] = 'true'

            for _tentativa in range(self.max_tentativas):
                _response = requests.post(
                    f'{self.brcobranca_url}/api/remessa',
                    params=_params_remessa,
                    files={'data': ('remessa.json',
                                    json.dumps(data_remessa).encode('utf-8'),
                                    'application/json')},
                    headers={'Accept': 'application/vnd.BoletoApi-v1+json'},
                    timeout=self.timeout,
                )
                if _response.status_code != 429:
                    break
                _wait = self.delay_inicial ** _tentativa
                logger.warning(
                    "[Remessa] BRCobranca 429 (rate limit) conta=%s banco=%s — "
                    "aguardando %ds antes de nova tentativa (%d/%d)",
                    descricao_conta, banco, _wait, _tentativa + 1, self.max_tentativas
                )
                time.sleep(_wait)

            response = _response
            _elapsed = time.monotonic() - _t0

            if response.status_code == 200:
                # API retorna conteúdo CNAB bruto (text/plain)
                arquivo_content = response.content
                if arquivo_content:

                    # Criar registro no banco
                    with transaction.atomic():
                        # Nome do arquivo
                        data_atual = timezone.now()
                        nome_arquivo = f"CB{data_atual.strftime('%d%m')}{numero_remessa:02d}.REM"

                        if arquivo_para_atualizar:
                            from financeiro.models import StatusArquivoRemessa
                            arquivo_remessa = arquivo_para_atualizar
                            # Deletar itens antigos dentro da transação (somente no sucesso)
                            arquivo_remessa.itens.all().delete()
                            arquivo_remessa.quantidade_boletos = len(parcelas_validas)
                            arquivo_remessa.valor_total = valor_total
                            arquivo_remessa.nome_arquivo = nome_arquivo
                            arquivo_remessa.status = StatusArquivoRemessa.GERADO
                            arquivo_remessa.erro_mensagem = ''
                            arquivo_remessa.save(update_fields=[
                                'quantidade_boletos', 'valor_total', 'nome_arquivo',
                                'status', 'erro_mensagem',
                            ])
                            arquivo_remessa.arquivo.save(
                                nome_arquivo, ContentFile(arquivo_content), save=True
                            )
                        else:
                            arquivo_remessa = ArquivoRemessa.objects.create(
                                conta_bancaria=conta_bancaria,
                                numero_remessa=numero_remessa,
                                layout=layout,
                                nome_arquivo=nome_arquivo,
                                quantidade_boletos=len(parcelas_validas),
                                valor_total=valor_total,
                            )
                            arquivo_remessa.arquivo.save(
                                nome_arquivo, ContentFile(arquivo_content), save=True
                            )

                        # Criar itens
                        ItemRemessa.objects.bulk_create([
                            ItemRemessa(
                                arquivo_remessa=arquivo_remessa,
                                parcela=parcela,
                                nosso_numero=parcela.nosso_numero,
                                valor=parcela.valor_boleto or parcela.valor_atual,
                                data_vencimento=parcela.data_vencimento,
                            )
                            for parcela in parcelas_validas
                        ])

                    logger.info(
                        "[Remessa] #%d gerada via BRCobranca: conta=%s boletos=%d "
                        "valor=R$%.2f elapsed=%.1fs",
                        numero_remessa, descricao_conta, len(parcelas_validas),
                        float(valor_total), _elapsed
                    )

                    return {
                        'sucesso': True,
                        'arquivo_remessa': arquivo_remessa,
                        'numero_remessa': numero_remessa,
                        'quantidade_boletos': len(parcelas_validas),
                        'valor_total': valor_total,
                        'arquivo_path': arquivo_remessa.arquivo.path,
                    }
                else:
                    erro_msg = 'BRCobranca nao retornou arquivo de remessa'
                    if arquivo_para_atualizar:
                        arquivo_para_atualizar.marcar_erro(erro_msg)
                    return {
                        'sucesso': False,
                        'erro': erro_msg,
                    }
            else:
                # HTTP error (429 persistente, 5xx, etc.)
                erro_body = response.text[:500]
                logger.error(
                    "[Remessa] ERRO BRCobranca HTTP %d — conta=%s banco=%s layout=%s\n"
                    "  → Verifique se a API BRCobranca está rodando e aceitando requisições.\n"
                    "  → URL: %s\n"
                    "  → Resposta: %s",
                    response.status_code, descricao_conta, banco, layout,
                    f'{self.brcobranca_url}/api/remessa', erro_body,
                )
                erro_msg = (
                    f'BRCobranca retornou HTTP {response.status_code}. '
                    'Verifique os logs do servidor e se a API está operacional.'
                )
                if arquivo_para_atualizar:
                    arquivo_para_atualizar.marcar_erro(erro_msg)
                return {
                    'sucesso': False,
                    'erro': erro_msg,
                }

        except requests.exceptions.ConnectionError as e:
            logger.error(
                "[Remessa] ERRO DE CONEXÃO com BRCobranca — conta=%s banco=%s\n"
                "  → A API não está acessível em: %s\n"
                "  → Confirme que o container/serviço BRCobranca está rodando.\n"
                "  → Detalhe: %s",
                descricao_conta, banco, self.brcobranca_url, e,
            )
            erro_msg = (
                'Não foi possível conectar à API BRCobranca. '
                'Verifique se o serviço está ativo e acessível.'
            )
            if arquivo_para_atualizar:
                arquivo_para_atualizar.marcar_erro(erro_msg)
            return {
                'sucesso': False,
                'erro': erro_msg,
            }
        except Exception as e:
            logger.exception(
                "[Remessa] ERRO INESPERADO — conta=%s banco=%s: %s",
                descricao_conta, banco, e,
            )
            erro_msg = str(e)
            if arquivo_para_atualizar:
                arquivo_para_atualizar.marcar_erro(erro_msg)
            return {
                'sucesso': False,
                'erro': erro_msg,
            }

    def regenerar_remessa(self, arquivo_remessa) -> Dict:
        """
        Regenera um arquivo de remessa existente.
        Usa os mesmos boletos do arquivo original.
        """
        from financeiro.models import StatusArquivoRemessa
        if arquivo_remessa.status not in [
            StatusArquivoRemessa.GERADO, StatusArquivoRemessa.ERRO
        ]:
            return {
                'sucesso': False,
                'erro': 'Apenas remessas com status GERADO ou ERRO podem ser regeneradas'
            }

        # Obter parcelas do arquivo original (sem deletar — a deleção ocorre
        # dentro de gerar_remessa somente após sucesso da API, em transação atômica)
        itens = arquivo_remessa.itens.select_related('parcela').all()
        parcelas = [item.parcela for item in itens]

        if not parcelas:
            return {
                'sucesso': False,
                'erro': 'Remessa não possui boletos associados para regenerar',
            }

        # Regenerar atualizando o mesmo registro (sem criar novo ArquivoRemessa)
        return self.gerar_remessa(
            parcelas,
            arquivo_remessa.conta_bancaria,
            arquivo_remessa.layout,
            arquivo_para_atualizar=arquivo_remessa,
        )

    def processar_retorno(self, arquivo_retorno, user=None) -> Dict:
        """
        Processa um arquivo de retorno CNAB via API BRCobrança (POST /api/retorno).
        Não existe parsing local — todo processamento é delegado à API.
        """
        from financeiro.models import ItemRetorno, StatusArquivoRetorno

        try:
            arquivo_retorno.arquivo.seek(0)
            conteudo = arquivo_retorno.arquivo.read()

            # Detectar layout pelo comprimento da primeira linha
            try:
                primeira_linha = conteudo.decode('latin-1').split('\n')[0].strip()
            except Exception:
                primeira_linha = conteudo.split(b'\n')[0].decode('latin-1', errors='replace').strip()

            layout_detectado = 'CNAB_240' if len(primeira_linha) == 240 else 'CNAB_400'
            formato_api = 'cnab240' if layout_detectado == 'CNAB_240' else 'cnab400'

            conta = arquivo_retorno.conta_bancaria
            banco = self._get_banco_brcobranca(getattr(conta, 'banco', '') or '')
            descricao_conta = getattr(conta, 'descricao', None) or str(conta)

            logger.info(
                "[Retorno] Enviando para BRCobrança — conta=%s banco=%s layout=%s bytes=%d",
                descricao_conta, banco, formato_api, len(conteudo)
            )

            try:
                response = requests.post(
                    f'{self.brcobranca_url}/api/retorno',
                    params={'bank': banco, 'type': formato_api},
                    files={'data': ('retorno.ret', io.BytesIO(conteudo), 'application/octet-stream')},
                    timeout=self.timeout,
                )
            except requests.exceptions.ConnectionError as e:
                logger.error(
                    "[Retorno] ERRO DE CONEXÃO com BRCobrança — conta=%s banco=%s\n"
                    "  → A API não está acessível em: %s\n"
                    "  → Confirme que o container/serviço BRCobrança está rodando.\n"
                    "  → Detalhe: %s",
                    descricao_conta, banco, self.brcobranca_url, e,
                )
                arquivo_retorno.status = StatusArquivoRetorno.ERRO
                arquivo_retorno.erro_mensagem = (
                    'Não foi possível conectar à API BRCobrança. '
                    'Verifique se o serviço está ativo.'
                )
                arquivo_retorno.save()
                return {'sucesso': False, 'erro': arquivo_retorno.erro_mensagem}

            if response.status_code != 200:
                erro_body = response.text[:500]
                logger.error(
                    "[Retorno] ERRO BRCobrança HTTP %d — conta=%s banco=%s layout=%s\n"
                    "  → URL: %s\n"
                    "  → Resposta: %s",
                    response.status_code, descricao_conta, banco, formato_api,
                    f'{self.brcobranca_url}/api/retorno', erro_body,
                )
                arquivo_retorno.status = StatusArquivoRetorno.ERRO
                arquivo_retorno.erro_mensagem = (
                    f'BRCobrança retornou HTTP {response.status_code}. '
                    'Verifique os logs do servidor.'
                )
                arquivo_retorno.save()
                return {'sucesso': False, 'erro': arquivo_retorno.erro_mensagem}

            try:
                dados = response.json()
            except Exception:
                logger.error(
                    "[Retorno] BRCobrança retornou resposta não-JSON: %s",
                    response.text[:200]
                )
                arquivo_retorno.status = StatusArquivoRetorno.ERRO
                arquivo_retorno.erro_mensagem = 'API BRCobrança retornou resposta inválida.'
                arquivo_retorno.save()
                return {'sucesso': False, 'erro': arquivo_retorno.erro_mensagem}

            retornos = dados.get('retornos') or []
            arquivo_retorno.layout = layout_detectado

            total_registros = 0
            registros_processados = 0
            registros_erro = 0
            valor_total_pago = Decimal('0.00')

            with transaction.atomic():
                for reg in retornos:
                    total_registros += 1
                    try:
                        nosso_numero = str(reg.get('nosso_numero') or '').strip()
                        codigo_ocorrencia = str(reg.get('codigo_ocorrencia') or '')

                        def _to_dec(v):
                            try:
                                return Decimal(str(v)) if v is not None else Decimal('0.00')
                            except Exception:
                                return Decimal('0.00')

                        valor_titulo = _to_dec(reg.get('valor_titulo'))
                        valor_pago = _to_dec(reg.get('valor_pago'))

                        def _parse_date(s):
                            if not s:
                                return None
                            try:
                                parts = str(s).split('-')
                                if len(parts) == 3:
                                    return datetime(int(parts[0]), int(parts[1]), int(parts[2])).date()
                            except Exception:
                                pass
                            return None

                        data_ocorrencia = _parse_date(reg.get('data_ocorrencia'))
                        data_credito = _parse_date(reg.get('data_credito'))

                        tipo_ocorrencia = 'OUTROS'
                        descricao = ''
                        if codigo_ocorrencia in OCORRENCIAS_CNAB:
                            tipo_ocorrencia, descricao = OCORRENCIAS_CNAB[codigo_ocorrencia]

                        parcela = self._buscar_parcela_por_nosso_numero(nosso_numero, conta)

                        item, criado = ItemRetorno.objects.get_or_create(
                            arquivo_retorno=arquivo_retorno,
                            nosso_numero=nosso_numero,
                            defaults=dict(
                                parcela=parcela,
                                codigo_ocorrencia=codigo_ocorrencia,
                                descricao_ocorrencia=descricao,
                                tipo_ocorrencia=tipo_ocorrencia,
                                valor_titulo=valor_titulo,
                                valor_pago=valor_pago if valor_pago > 0 else None,
                                data_ocorrencia=data_ocorrencia,
                                data_credito=data_credito,
                            ),
                        )
                        if not criado:
                            registros_processados += (1 if item.processado else 0)
                            continue

                        if item.processar_baixa():
                            registros_processados += 1
                            if tipo_ocorrencia == 'LIQUIDACAO':
                                valor_total_pago += valor_pago or valor_titulo
                        else:
                            if item.erro_processamento:
                                registros_erro += 1

                    except Exception as e:
                        registros_erro += 1
                        logger.exception("[Retorno] Erro ao processar registro: %s", e)

                arquivo_retorno.total_registros = total_registros
                arquivo_retorno.registros_processados = registros_processados
                arquivo_retorno.registros_erro = registros_erro
                arquivo_retorno.valor_total_pago = valor_total_pago
                arquivo_retorno.data_processamento = timezone.now()
                arquivo_retorno.processado_por = user

                if registros_erro == 0:
                    arquivo_retorno.status = StatusArquivoRetorno.PROCESSADO
                elif registros_processados > 0:
                    arquivo_retorno.status = StatusArquivoRetorno.PROCESSADO_PARCIAL
                else:
                    arquivo_retorno.status = StatusArquivoRetorno.ERRO

                arquivo_retorno.save()

            logger.info(
                "[Retorno] %d/%d registros processados, R$ %.2f pagos",
                registros_processados, total_registros, float(valor_total_pago)
            )

            return {
                'sucesso': True,
                'total_registros': total_registros,
                'registros_processados': registros_processados,
                'registros_erro': registros_erro,
                'valor_total_pago': valor_total_pago,
            }

        except Exception as e:
            arquivo_retorno.status = StatusArquivoRetorno.ERRO
            arquivo_retorno.erro_mensagem = str(e)
            arquivo_retorno.save()
            logger.exception("[Retorno] Erro inesperado: %s", e)
            return {'sucesso': False, 'erro': str(e)}

    def obter_boletos_sem_remessa(
        self,
        conta_bancaria=None,
        imobiliaria_id=None,
        contrato_id=None
    ) -> List:
        """
        Retorna parcelas com boleto gerado mas sem arquivo de remessa ativo.

        Inclui parcelas que:
        - Não estão em nenhuma remessa (itens_remessa__isnull=True)
        - Estão apenas em remessas com status ERRO (podem ser re-incluídas)

        Exclui parcelas em remessas ativas (GERADO, ENVIADO, PROCESSADO).
        """
        from financeiro.models import Parcela, StatusBoleto, StatusArquivoRemessa

        queryset = Parcela.objects.filter(
            status_boleto=StatusBoleto.GERADO,
            pago=False,
        ).exclude(
            itens_remessa__arquivo_remessa__status__in=[
                StatusArquivoRemessa.GERADO,
                StatusArquivoRemessa.ENVIADO,
                StatusArquivoRemessa.PROCESSADO,
            ]
        ).select_related(
            'contrato', 'contrato__comprador', 'contrato__imovel',
            'contrato__imobiliaria', 'conta_bancaria', 'conta_bancaria__imobiliaria'
        ).distinct()

        if conta_bancaria:
            queryset = queryset.filter(conta_bancaria=conta_bancaria)

        if imobiliaria_id:
            queryset = queryset.filter(contrato__imobiliaria_id=imobiliaria_id)

        if contrato_id:
            queryset = queryset.filter(contrato_id=contrato_id)

        return list(queryset.order_by('conta_bancaria', 'data_vencimento'))

    def obter_boletos_em_remessa_pendente(
        self,
        conta_bancaria=None,
        imobiliaria_id=None,
        contrato_id=None
    ) -> List:
        """
        Retorna parcelas já incluídas em remessa com status GERADO (não enviada).
        Usado para exibir aviso de duplicata potencial.
        """
        from financeiro.models import Parcela, StatusBoleto, StatusArquivoRemessa

        queryset = Parcela.objects.filter(
            status_boleto=StatusBoleto.GERADO,
            pago=False,
            itens_remessa__arquivo_remessa__status=StatusArquivoRemessa.GERADO
        ).select_related(
            'contrato', 'contrato__comprador', 'conta_bancaria',
            'contrato__imobiliaria'
        ).prefetch_related('itens_remessa__arquivo_remessa').distinct()

        if conta_bancaria:
            queryset = queryset.filter(conta_bancaria=conta_bancaria)

        if imobiliaria_id:
            queryset = queryset.filter(contrato__imobiliaria_id=imobiliaria_id)

        if contrato_id:
            queryset = queryset.filter(contrato_id=contrato_id)

        return list(queryset.order_by('conta_bancaria', 'data_vencimento'))

    def gerar_remessas_por_escopo(
        self,
        parcela_ids: List[int],
        layout: str = None,
        usuario=None,
        transicionar_registrado: bool = False,
    ) -> Dict:
        """
        Gera remessas agrupando automaticamente as parcelas por conta_bancaria.
        Cada conta gera exatamente 1 arquivo de remessa (invariante CNAB — HU-23 RN-19).

        Args:
            parcela_ids: IDs das parcelas selecionadas
            layout: Layout CNAB forçado (CNAB_240/CNAB_400). Se None, usa o
                    layout_cnab configurado em cada conta (HU-23 RN-05).
            usuario: Quando informado, grava ArquivoRemessa.gerado_por (HU-23 RN-17).
            transicionar_registrado: Quando True, os boletos incluídos passam de
                    GERADO → REGISTRADO (HU-23 RN-14). Default False preserva o
                    comportamento da HU-16.

        Returns:
            dict com:
              - remessas_geradas: list de dicts com info das remessas criadas
              - erros: list de erros por conta
              - total_boletos: int
              - total_valor: Decimal
        """
        from financeiro.models import Parcela, StatusBoleto
        from collections import defaultdict

        # Buscar parcelas válidas — exclui apenas as já em remessas ativas
        # (inclui parcelas em remessas com ERRO, que podem ser re-incluídas)
        from financeiro.models import StatusArquivoRemessa
        parcelas = list(
            Parcela.objects.filter(
                pk__in=parcela_ids,
                status_boleto=StatusBoleto.GERADO,
                pago=False,
            ).exclude(
                itens_remessa__arquivo_remessa__status__in=[
                    StatusArquivoRemessa.GERADO,
                    StatusArquivoRemessa.ENVIADO,
                    StatusArquivoRemessa.PROCESSADO,
                ]
            ).select_related('conta_bancaria', 'contrato').distinct()
        )

        if not parcelas:
            return {
                'remessas_geradas': [],
                'erros': ['Nenhuma parcela válida selecionada.'],
                'total_boletos': 0,
                'total_valor': Decimal('0.00'),
            }

        # Agrupar por conta_bancaria
        grupos: Dict = defaultdict(list)
        sem_conta = []
        for p in parcelas:
            if p.conta_bancaria:
                grupos[p.conta_bancaria].append(p)
            else:
                sem_conta.append(p)

        remessas_geradas = []
        erros = []

        if sem_conta:
            erros.append(
                f"{len(sem_conta)} parcela(s) sem conta bancária associada foram ignoradas."
            )

        # Throttle: evita 429 no BRCobranca ao processar múltiplas contas do mesmo banco
        # em sequência rápida. Garante ao menos MIN_INTERVAL segundos entre requisições
        # ao mesmo banco.
        _MIN_INTERVAL = 1.5  # segundos
        _ultimo_request_banco: Dict[str, float] = {}
        _total_contas = len(grupos)

        for _idx, (conta, lista_parcelas) in enumerate(grupos.items(), start=1):
            descricao_conta = getattr(conta, 'descricao', None) or str(conta)
            banco_key = getattr(conta, 'banco', '')
            logger.info(
                "[Remessa lote] processando %d/%d: conta=%s banco=%s parcelas=%d",
                _idx, _total_contas, descricao_conta, banco_key, len(lista_parcelas)
            )
            _agora = time.monotonic()
            _ultimo = _ultimo_request_banco.get(banco_key, 0.0)
            _espera = _MIN_INTERVAL - (_agora - _ultimo)
            if _espera > 0:
                logger.debug(
                    "[Remessa lote] throttle banco=%s — aguardando %.1fs", banco_key, _espera
                )
                time.sleep(_espera)

            # HU-23 RN-05: layout por conta quando não forçado
            layout_conta = layout or getattr(conta, 'layout_cnab', None) or 'CNAB_240'
            resultado = self.gerar_remessa(lista_parcelas, conta, layout_conta)
            _ultimo_request_banco[banco_key] = time.monotonic()

            if resultado.get('sucesso'):
                arq = resultado['arquivo_remessa']
                # HU-23 RN-17: auditoria de quem gerou
                if usuario is not None and getattr(arq, 'gerado_por_id', None) is None:
                    arq.gerado_por = usuario
                    arq.save(update_fields=['gerado_por'])
                # HU-23 RN-14: boletos incluídos passam a REGISTRADO
                if transicionar_registrado:
                    Parcela.objects.filter(
                        pk__in=[p.pk for p in lista_parcelas],
                        status_boleto=StatusBoleto.GERADO,
                    ).update(
                        status_boleto=StatusBoleto.REGISTRADO,
                        data_registro_boleto=timezone.now(),
                    )
                remessas_geradas.append({
                    'arquivo_remessa': arq,
                    'conta_bancaria': conta,
                    'quantidade_boletos': resultado['quantidade_boletos'],
                    'valor_total': resultado['valor_total'],
                    'numero_remessa': resultado['numero_remessa'],
                    'aviso': resultado.get('aviso', ''),
                })
            else:
                erros.append(
                    f"Conta {conta}: {resultado.get('erro', 'Erro desconhecido')}"
                )

        total_boletos = sum(r['quantidade_boletos'] for r in remessas_geradas)
        total_valor = sum(r['valor_total'] for r in remessas_geradas)

        return {
            'remessas_geradas': remessas_geradas,
            'erros': erros,
            'total_boletos': total_boletos,
            'total_valor': total_valor,
        }

    # =========================================================================
    # HU-23 — Painel de Remessa Mensal (escopos + elegibilidade)
    # =========================================================================

    def obter_boletos_elegiveis_painel(
        self,
        imobiliarias=None,
        conta_bancaria=None,
        imobiliaria_id=None,
        mes=None,
        ano=None,
        hoje=None,
    ) -> List:
        """
        HU-23: boletos elegíveis para remessa no painel da contadora.

        Reaproveita obter_boletos_sem_remessa() e aplica as regras da HU-23:
          - data_vencimento >= hoje              (RN-01)
          - conta com cobranca_registrada=True   (RN-16)
          - escopo às imobiliárias acessíveis     (RN-11/RN-21)
          - (opcional) competência mês/ano do vencimento
        """
        from datetime import date as _date
        hoje = hoje or _date.today()

        parcelas = self.obter_boletos_sem_remessa(
            conta_bancaria=conta_bancaria,
            imobiliaria_id=imobiliaria_id,
        )

        ids_imobs = None
        if imobiliarias is not None:
            if hasattr(imobiliarias, 'values_list'):
                ids_imobs = set(imobiliarias.values_list('id', flat=True))
            else:
                ids_imobs = {getattr(i, 'id', i) for i in imobiliarias}

        elegiveis = []
        for p in parcelas:
            conta = p.conta_bancaria
            if not conta:
                continue
            if not getattr(conta, 'cobranca_registrada', True):
                continue  # RN-16: registro online / sem registro → sem remessa
            if ids_imobs is not None and conta.imobiliaria_id not in ids_imobs:
                continue  # RN-11: fora do escopo do usuário
            if p.data_vencimento < hoje:
                continue  # RN-01: só presente/futuro
            if mes and ano and not (
                p.data_vencimento.month == int(mes) and p.data_vencimento.year == int(ano)
            ):
                continue  # competência selecionada
            elegiveis.append(p)
        return elegiveis

    def resolver_parcela_ids_por_escopo(
        self,
        escopo: str,
        imobiliarias=None,
        conta_bancaria_id=None,
        imobiliaria_id=None,
        parcela_id=None,
        mes=None,
        ano=None,
    ) -> Dict:
        """
        HU-23: resolve um escopo de geração para a lista de parcela_ids elegíveis,
        sempre respeitando o acesso do usuário (imobiliarias).

        Escopos: 'todos' | 'imobiliaria' | 'conta' | 'boleto'.

        Returns: {'parcela_ids': [...], 'erro': str|None}
        """
        from financeiro.models import Parcela, StatusBoleto, StatusArquivoRemessa
        from datetime import date as _date

        ids_imobs = None
        if imobiliarias is not None:
            if hasattr(imobiliarias, 'values_list'):
                ids_imobs = set(imobiliarias.values_list('id', flat=True))
            else:
                ids_imobs = {getattr(i, 'id', i) for i in imobiliarias}

        if escopo == 'boleto':
            if not parcela_id:
                return {'parcela_ids': [], 'erro': 'parcela_id é obrigatório no escopo "boleto".'}
            p = Parcela.objects.select_related('conta_bancaria', 'contrato').filter(pk=parcela_id).first()
            if not p:
                return {'parcela_ids': [], 'erro': 'Boleto não encontrado.'}
            if not p.conta_bancaria:
                return {'parcela_ids': [], 'erro': 'Boleto sem conta bancária associada.'}
            if ids_imobs is not None and p.conta_bancaria.imobiliaria_id not in ids_imobs:
                return {'parcela_ids': [], 'erro': 'Sem acesso a este boleto.'}
            if p.status_boleto != StatusBoleto.GERADO or p.pago:
                return {'parcela_ids': [], 'erro': 'Boleto não elegível (status ou já pago).'}
            if p.data_vencimento < _date.today():
                return {'parcela_ids': [], 'erro': 'Boleto não elegível: vencimento no passado.'}
            ja_em_remessa = p.itens_remessa.filter(
                arquivo_remessa__status__in=[
                    StatusArquivoRemessa.GERADO,
                    StatusArquivoRemessa.ENVIADO,
                    StatusArquivoRemessa.PROCESSADO,
                ]
            ).exists()
            if ja_em_remessa:
                return {'parcela_ids': [], 'erro': 'Boleto já está em uma remessa ativa.'}
            return {'parcela_ids': [p.pk], 'erro': None}

        # Escopos agregados: todos / imobiliaria / conta
        kwargs = {'imobiliarias': imobiliarias, 'mes': mes, 'ano': ano}
        if escopo == 'conta':
            if not conta_bancaria_id:
                return {'parcela_ids': [], 'erro': 'conta_bancaria_id é obrigatório no escopo "conta".'}
            from core.models import ContaBancaria
            conta = ContaBancaria.objects.filter(pk=conta_bancaria_id).first()
            if not conta:
                return {'parcela_ids': [], 'erro': 'Conta bancária não encontrada.'}
            if ids_imobs is not None and conta.imobiliaria_id not in ids_imobs:
                return {'parcela_ids': [], 'erro': 'Sem acesso a esta conta bancária.'}
            kwargs['conta_bancaria'] = conta
        elif escopo == 'imobiliaria':
            if not imobiliaria_id:
                return {'parcela_ids': [], 'erro': 'imobiliaria_id é obrigatório no escopo "imobiliaria".'}
            if ids_imobs is not None and int(imobiliaria_id) not in ids_imobs:
                return {'parcela_ids': [], 'erro': 'Sem acesso a esta imobiliária.'}
            kwargs['imobiliaria_id'] = imobiliaria_id
        elif escopo != 'todos':
            return {'parcela_ids': [], 'erro': f'Escopo inválido: {escopo}'}

        elegiveis = self.obter_boletos_elegiveis_painel(**kwargs)
        return {'parcela_ids': [p.pk for p in elegiveis], 'erro': None}

    @staticmethod
    def _dias_uteis_ate(inicio, fim) -> int:
        """Conta dias úteis (seg–sex) entre `inicio` (excl.) e `fim` (incl.)."""
        from datetime import timedelta
        if fim <= inicio:
            return 0
        dias = 0
        d = inicio
        while d < fim:
            d += timedelta(days=1)
            if d.weekday() < 5:  # 0=seg ... 4=sex
                dias += 1
        return dias

    def validar_boletos_para_remessa(self, parcelas, lead_time_dias_uteis: int = 1, hoje=None) -> Dict:
        """
        HU-23 (CT-21 / RN-15): validação determinística pré-geração.

        Detecta inconsistências antes de gerar a remessa, sem depender de IA:
          - nosso_numero ausente
          - valor zerado/negativo
          - sacado com documento (CPF/CNPJ) inválido
          - endereço do sacado incompleto (sem CEP ou logradouro)
          - vencimento muito próximo (< lead_time dias úteis) — RN-15

        Returns: {'alertas': [...], 'total_alertas': int, 'por_tipo': {tipo: n}}
        """
        from datetime import date as _date
        from django.core.exceptions import ValidationError
        from core.validators import validar_cpf_cnpj
        from collections import Counter

        hoje = hoje or _date.today()
        alertas = []

        for p in parcelas:
            contrato = getattr(p, 'contrato', None)
            comprador = getattr(contrato, 'comprador', None) if contrato else None
            ref = {
                'parcela_id': p.pk,
                'numero_parcela': p.numero_parcela,
                'comprador': getattr(comprador, 'nome', '') if comprador else '',
                'contrato': getattr(contrato, 'numero_contrato', '') if contrato else '',
            }

            def _alerta(tipo, msg, sev='warning'):
                alertas.append({**ref, 'tipo': tipo, 'severidade': sev, 'mensagem': msg})

            if not (p.nosso_numero or '').strip():
                _alerta('sem_nosso_numero', 'Boleto sem nosso número — será ignorado na remessa.', 'erro')

            valor = p.valor_boleto or p.valor_atual or Decimal('0')
            if valor <= 0:
                _alerta('valor_invalido', 'Valor do boleto zerado ou negativo.', 'erro')

            if comprador is not None:
                doc = (comprador.cnpj or comprador.cpf or '').strip()
                if not doc:
                    _alerta('documento_ausente', 'Sacado sem CPF/CNPJ cadastrado.')
                else:
                    try:
                        validar_cpf_cnpj(doc)
                    except ValidationError:
                        _alerta('documento_invalido', f'CPF/CNPJ do sacado inválido ({doc}).')
                cep = (getattr(comprador, 'cep', '') or '').strip()
                logr = (getattr(comprador, 'logradouro', '') or getattr(comprador, 'endereco', '') or '').strip()
                if not cep or not logr:
                    _alerta('endereco_incompleto', 'Endereço do sacado incompleto (sem CEP ou logradouro).')

            dias = self._dias_uteis_ate(hoje, p.data_vencimento)
            if dias < lead_time_dias_uteis:
                _alerta(
                    'vencimento_proximo',
                    f'Vencimento muito próximo ({p.data_vencimento:%d/%m}) — pode não registrar a tempo.',
                )

        por_tipo = dict(Counter(a['tipo'] for a in alertas))
        return {'alertas': alertas, 'total_alertas': len(alertas), 'por_tipo': por_tipo}
