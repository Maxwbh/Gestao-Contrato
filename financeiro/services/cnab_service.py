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
import time
import logging
import requests
import json
import base64
from decimal import Decimal
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


# Mapeamento de bancos para o BRCobranca
BANCOS_BRCOBRANCA = {
    '001': 'banco_brasil',
    '033': 'santander',
    '104': 'caixa',
    '237': 'bradesco',
    '341': 'itau',
    '399': 'hsbc',
    '422': 'safra',
    '748': 'sicredi',
    '756': 'sicoob',
    '085': 'cecred',
    '041': 'banrisul',
    '070': 'brb',
    '097': 'credisis',
    '136': 'unicred',
    '212': 'banco_original',
    '260': 'nubank',
    '655': 'votorantim',
}

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

    def gerar_remessa(
        self,
        parcelas: List,
        conta_bancaria,
        layout: str = 'CNAB_240'
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

        # Obter proximo numero de remessa
        ultimo = ArquivoRemessa.objects.filter(
            conta_bancaria=conta_bancaria
        ).order_by('-numero_remessa').first()
        numero_remessa = (ultimo.numero_remessa + 1) if ultimo else 1

        # Montar dados para BRCobranca
        banco = self._get_banco_brcobranca(conta_bancaria.banco)
        imobiliaria = conta_bancaria.imobiliaria

        # Estrutura de dados do cedente/empresa
        agencia_num, agencia_dv = self._parsear_numero_dv(conta_bancaria.agencia)
        conta_num, conta_dv = self._parsear_numero_dv(conta_bancaria.conta)
        dados_empresa = {
            'empresa_mae': imobiliaria.razao_social or imobiliaria.nome,
            'documento_cedente': self._formatar_cpf_cnpj(imobiliaria.cnpj),
            'agencia': agencia_num,
            'agencia_dv': agencia_dv,
            'conta_corrente': conta_num,
            'digito_conta': conta_dv,
            'convenio': conta_bancaria.convenio or '',
            'carteira': conta_bancaria.carteira or '',
            'sequencial_remessa': numero_remessa,
            'codigo_cedente': conta_bancaria.convenio or '',
        }

        # Campos do cedente que pertencem APENAS ao root do payload de remessa.
        # Não devem ser repetidos em cada pagamento — a API Ruby faz merge do root
        # com os campos de cada boleto; duplicatas causam NoMethodError (merge on Array).
        _CAMPOS_CEDENTE_ROOT = {
            'agencia', 'conta_corrente', 'convenio', 'carteira',
            'cedente', 'documento_cedente',
        }

        # Lista de boletos — apenas campos boleto-específicos (sacado, valores, datas, etc.)
        pagamentos = []

        valor_total = Decimal('0.00')
        for parcela in parcelas_validas:
            dados_boleto = self._montar_dados_boleto(parcela, conta_bancaria)
            # Strip de campos do cedente — ficam somente no root (dados_empresa)
            boleto_remessa = {
                k: v for k, v in dados_boleto.items()
                if k not in _CAMPOS_CEDENTE_ROOT
            }
            pagamentos.append(boleto_remessa)
            valor_total += parcela.valor_boleto or parcela.valor_atual

        try:
            # A API /api/remessa espera multipart/form-data:
            #   bank  → campo de texto (ex: 'banco_brasil')
            #   type  → campo de texto ('cnab240' | 'cnab400')
            #   data  → arquivo JSON com um Hash/objeto:
            #           {
            #             empresa_mae, documento_cedente, agencia, agencia_dv,
            #             conta_corrente, digito_conta, convenio, carteira,
            #             sequencial_remessa, codigo_cedente,
            #             "pagamentos": [{nosso_numero, valor, sacado, ...}, ...]
            #           }
            # IMPORTANTE: campos do cedente (agencia, conta_corrente, convenio, carteira,
            # cedente, documento_cedente) devem ficar APENAS no root — NÃO dentro de cada
            # pagamento. Duplicar esses campos causa NoMethodError no Ruby (merge on Array).
            tipo_cnab = 'cnab240' if layout == 'CNAB_240' else 'cnab400'
            payload = {**dados_empresa, 'pagamentos': pagamentos}
            data_json = json.dumps(payload, ensure_ascii=False).encode('utf-8')

            descricao_conta = getattr(conta_bancaria, 'descricao', None) or str(conta_bancaria)
            logger.info(
                "[Remessa] conta=%s banco=%s layout=%s boletos=%d valor=R$%.2f",
                descricao_conta, banco, tipo_cnab, len(pagamentos), float(valor_total)
            )

            if logger.isEnabledFor(logging.DEBUG) and pagamentos:
                p0 = pagamentos[0]
                logger.debug(
                    "[Remessa] payload[0] data_vencimento=%r data_documento=%r",
                    p0.get('data_vencimento'), p0.get('data_documento')
                )

            # Retry automático em 429 (rate limit): até 3 tentativas com backoff exponencial
            _max_tentativas = 3
            _response = None
            _t0 = time.monotonic()
            for _tentativa in range(_max_tentativas):
                _response = requests.post(
                    f'{self.brcobranca_url}/api/remessa',
                    data={
                        'bank': banco,
                        'type': tipo_cnab,
                    },
                    files={
                        'data': ('remessa.json', io.BytesIO(data_json), 'application/json'),
                    },
                    headers={'Accept': 'application/vnd.BoletoApi-v1+json'},
                    timeout=60
                )
                if _response.status_code != 429:
                    break
                _wait = 2 ** _tentativa  # 1s, 2s, 4s
                logger.warning(
                    "[Remessa] BRCobranca 429 (rate limit) conta=%s banco=%s — "
                    "aguardando %ds antes de nova tentativa (%d/%d)",
                    descricao_conta, banco, _wait, _tentativa + 1, _max_tentativas
                )
                time.sleep(_wait)

            response = _response
            _elapsed = time.monotonic() - _t0

            if response.status_code == 200:
                resultado = response.json()

                # Decodificar arquivo
                if resultado.get('remessa'):
                    arquivo_content = base64.b64decode(resultado['remessa'])

                    # Criar registro no banco
                    with transaction.atomic():
                        # Nome do arquivo
                        data_atual = timezone.now()
                        nome_arquivo = f"CB{data_atual.strftime('%d%m')}{numero_remessa:02d}.REM"

                        arquivo_remessa = ArquivoRemessa.objects.create(
                            conta_bancaria=conta_bancaria,
                            numero_remessa=numero_remessa,
                            layout=layout,
                            nome_arquivo=nome_arquivo,
                            quantidade_boletos=len(parcelas_validas),
                            valor_total=valor_total,
                        )

                        # Salvar arquivo
                        arquivo_remessa.arquivo.save(
                            nome_arquivo,
                            ContentFile(arquivo_content),
                            save=True
                        )

                        # Criar itens
                        for parcela in parcelas_validas:
                            ItemRemessa.objects.create(
                                arquivo_remessa=arquivo_remessa,
                                parcela=parcela,
                                nosso_numero=parcela.nosso_numero,
                                valor=parcela.valor_boleto or parcela.valor_atual,
                                data_vencimento=parcela.data_vencimento,
                            )

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
                    return {
                        'sucesso': False,
                        'erro': 'BRCobranca nao retornou arquivo de remessa'
                    }
            else:
                # HTTP error (429 persistente, 5xx, etc.) → fallback local
                logger.warning(
                    "[Remessa] BRCobranca HTTP %d conta=%s banco=%s — ativando fallback local. "
                    "Resposta: %s",
                    response.status_code, descricao_conta, banco, response.text[:200]
                )
                return self._gerar_remessa_local(
                    parcelas_validas, conta_bancaria, numero_remessa, layout, valor_total
                )

        except requests.exceptions.ConnectionError:
            logger.warning(
                "[Remessa] BRCobranca indisponivel conta=%s — ativando fallback local",
                descricao_conta
            )
            return self._gerar_remessa_local(
                parcelas_validas, conta_bancaria, numero_remessa, layout, valor_total
            )
        except Exception as e:
            logger.exception(
                "[Remessa] Erro inesperado conta=%s banco=%s: %s",
                descricao_conta, banco, e
            )
            return {
                'sucesso': False,
                'erro': str(e)
            }

    def _gerar_remessa_local(
        self,
        parcelas: List,
        conta_bancaria,
        numero_remessa: int,
        layout: str,
        valor_total: Decimal
    ) -> Dict:
        """
        Gera arquivo de remessa localmente (fallback quando BRCobranca nao disponivel).
        Gera formato CNAB 400 simplificado.
        """
        from financeiro.models import ArquivoRemessa, ItemRemessa

        linhas = []
        imobiliaria = conta_bancaria.imobiliaria

        # Header do arquivo (registro tipo 0)
        header = '0'  # Tipo registro
        header += '1'  # Operacao (remessa)
        header += 'REMESSA'.ljust(7)
        header += '01'  # Tipo servico (cobranca)
        header += 'COBRANCA'.ljust(15)
        agencia_num, agencia_dv = self._parsear_numero_dv(conta_bancaria.agencia)
        conta_num, conta_dv = self._parsear_numero_dv(conta_bancaria.conta)
        header += agencia_num.zfill(4)
        header += '00'  # Digito agencia
        header += conta_num.zfill(8)
        header += conta_dv.ljust(1)
        header += ''.ljust(6)  # Brancos
        header += (imobiliaria.razao_social or imobiliaria.nome)[:30].ljust(30)
        header += conta_bancaria.banco.zfill(3)
        header += conta_bancaria.get_banco_display()[:15].ljust(15)
        header += timezone.now().strftime('%d%m%y')
        header += ''.ljust(8)  # Brancos
        header += ''.ljust(2)  # Identificacao sistema
        header += str(numero_remessa).zfill(7)
        header += ''.ljust(277)  # Brancos ate 394
        header += '000001'  # Sequencial
        linhas.append(header[:400])

        # Registros de boletos (tipo 1)
        sequencial = 2
        for parcela in parcelas:
            contrato = parcela.contrato
            comprador = contrato.comprador

            detalhe = '1'  # Tipo registro
            # Tipo inscricao cedente
            detalhe += '02' if len(self._formatar_cpf_cnpj(imobiliaria.cnpj)) > 11 else '01'
            detalhe += self._formatar_cpf_cnpj(imobiliaria.cnpj).zfill(14)
            detalhe += agencia_num.zfill(4)
            detalhe += '00'  # Digito agencia
            detalhe += conta_num.zfill(8)
            detalhe += conta_dv.ljust(1)
            detalhe += ''.ljust(6)  # Brancos
            detalhe += (parcela.numero_documento or '')[:25].ljust(25)
            detalhe += (parcela.nosso_numero or '').zfill(20)
            detalhe += ''.ljust(25)  # Brancos
            detalhe += '0'  # Codigo mora
            detalhe += '01'  # Codigo carteira
            detalhe += '01'  # Comando (entrada)
            detalhe += (parcela.numero_documento or '')[:10].ljust(10)
            detalhe += parcela.data_vencimento.strftime('%d%m%y')
            valor_str = str(int((parcela.valor_boleto or parcela.valor_atual) * 100)).zfill(13)
            detalhe += valor_str
            detalhe += conta_bancaria.banco.zfill(3)
            detalhe += '00000'  # Agencia cobradora
            detalhe += '01'  # Especie titulo
            detalhe += 'N'  # Aceite
            data_emissao = parcela.data_geracao_boleto or timezone.now()
            detalhe += data_emissao.strftime('%d%m%y')
            detalhe += '00'  # Instrucao 1
            detalhe += '00'  # Instrucao 2
            detalhe += '0000000000000'  # Juros
            detalhe += '000000'  # Data desconto
            detalhe += '0000000000000'  # Valor desconto
            detalhe += '0000000000000'  # Valor IOF
            detalhe += '0000000000000'  # Valor abatimento
            # Tipo inscricao sacado
            cpf_cnpj_sacado = self._formatar_cpf_cnpj(comprador.cnpj or comprador.cpf)
            detalhe += '02' if len(cpf_cnpj_sacado) > 11 else '01'
            detalhe += cpf_cnpj_sacado.zfill(14)
            detalhe += comprador.nome[:40].ljust(40)
            endereco = f"{comprador.logradouro or ''} {comprador.numero or ''}"
            detalhe += endereco[:40].ljust(40)
            detalhe += ''.ljust(12)  # Mensagem
            detalhe += self._formatar_cpf_cnpj(comprador.cep or '').zfill(8)
            detalhe += (comprador.cidade or '')[:15].ljust(15)
            detalhe += (comprador.estado or '')[:2].ljust(2)
            detalhe += ''.ljust(40)  # Sacador avalista
            detalhe += str(sequencial).zfill(6)
            linhas.append(detalhe[:400])
            sequencial += 1

        # Trailer (registro tipo 9)
        trailer = '9'
        trailer += ''.ljust(393)
        trailer += str(sequencial).zfill(6)
        linhas.append(trailer[:400])

        # Criar arquivo
        conteudo = '\r\n'.join(linhas)

        with transaction.atomic():
            data_atual = timezone.now()
            nome_arquivo = f"CB{data_atual.strftime('%d%m')}{numero_remessa:02d}.REM"

            arquivo_remessa = ArquivoRemessa.objects.create(
                conta_bancaria=conta_bancaria,
                numero_remessa=numero_remessa,
                layout=layout,
                nome_arquivo=nome_arquivo,
                quantidade_boletos=len(parcelas),
                valor_total=valor_total,
                observacoes='Gerado localmente (BRCobranca indisponivel)'
            )

            arquivo_remessa.arquivo.save(
                nome_arquivo,
                ContentFile(conteudo.encode('latin-1')),
                save=True
            )

            for parcela in parcelas:
                ItemRemessa.objects.create(
                    arquivo_remessa=arquivo_remessa,
                    parcela=parcela,
                    nosso_numero=parcela.nosso_numero,
                    valor=parcela.valor_boleto or parcela.valor_atual,
                    data_vencimento=parcela.data_vencimento,
                )

        descricao_conta = getattr(conta_bancaria, 'descricao', None) or str(conta_bancaria)
        logger.info(
            "[Remessa] #%d gerada localmente (fallback): conta=%s boletos=%d valor=R$%.2f",
            numero_remessa, descricao_conta, len(parcelas), float(valor_total)
        )

        return {
            'sucesso': True,
            'arquivo_remessa': arquivo_remessa,
            'numero_remessa': numero_remessa,
            'quantidade_boletos': len(parcelas),
            'valor_total': valor_total,
            'arquivo_path': arquivo_remessa.arquivo.path,
            'aviso': 'Arquivo gerado localmente (formato simplificado)'
        }

    def regenerar_remessa(self, arquivo_remessa) -> Dict:
        """
        Regenera um arquivo de remessa existente.
        Usa os mesmos boletos do arquivo original.
        """
        from financeiro.models import ItemRemessa

        if arquivo_remessa.status not in ['GERADO', 'ERRO']:
            return {
                'sucesso': False,
                'erro': 'Apenas remessas com status GERADO ou ERRO podem ser regeneradas'
            }

        # Obter parcelas do arquivo original
        itens = arquivo_remessa.itens.select_related('parcela').all()
        parcelas = [item.parcela for item in itens]

        # Excluir itens antigos
        itens.delete()

        # Regenerar
        return self.gerar_remessa(
            parcelas,
            arquivo_remessa.conta_bancaria,
            arquivo_remessa.layout
        )

    def processar_retorno(
        self,
        arquivo_retorno,
        user=None
    ) -> Dict:
        """
        Processa um arquivo de retorno CNAB.

        Args:
            arquivo_retorno: ArquivoRetorno com o arquivo carregado
            user: Usuario que esta processando

        Returns:
            dict: Resultado do processamento
        """
        from financeiro.models import (
            ItemRetorno, StatusArquivoRetorno, Parcela
        )

        try:
            # Ler arquivo
            arquivo_retorno.arquivo.seek(0)
            conteudo = arquivo_retorno.arquivo.read()

            # Tentar decodificar
            try:
                linhas = conteudo.decode('latin-1').split('\n')
            except UnicodeDecodeError:
                linhas = conteudo.decode('utf-8').split('\n')

            # Detectar layout
            if len(linhas[0].strip()) == 240:
                return self._processar_retorno_cnab240(
                    arquivo_retorno, linhas, user
                )
            else:
                return self._processar_retorno_cnab400(
                    arquivo_retorno, linhas, user
                )

        except Exception as e:
            arquivo_retorno.status = StatusArquivoRetorno.ERRO
            arquivo_retorno.erro_mensagem = str(e)
            arquivo_retorno.save()
            logger.exception("Erro ao processar retorno: %s", e)
            return {
                'sucesso': False,
                'erro': str(e)
            }

    def _processar_retorno_cnab400(
        self,
        arquivo_retorno,
        linhas: List[str],
        user
    ) -> Dict:
        """Processa arquivo de retorno CNAB 400"""
        from financeiro.models import (
            ItemRetorno, StatusArquivoRetorno, Parcela
        )

        arquivo_retorno.layout = 'CNAB_400'
        total_registros = 0
        registros_processados = 0
        registros_erro = 0
        valor_total_pago = Decimal('0.00')

        with transaction.atomic():
            for linha in linhas:
                linha = linha.strip()
                if not linha:
                    continue

                # Registro de detalhe (tipo 1)
                if linha[0] == '1':
                    total_registros += 1

                    try:
                        # Extrair dados
                        nosso_numero = linha[62:82].strip()
                        codigo_ocorrencia = linha[108:110]
                        valor_titulo = Decimal(linha[152:165]) / 100
                        valor_pago = Decimal(linha[253:266]) / 100

                        # Data da ocorrencia
                        data_str = linha[110:116]
                        if data_str.strip():
                            data_ocorrencia = datetime.strptime(data_str, '%d%m%y').date()
                        else:
                            data_ocorrencia = None

                        # Data de credito
                        data_credito_str = linha[175:181]
                        if data_credito_str.strip():
                            data_credito = datetime.strptime(data_credito_str, '%d%m%y').date()
                        else:
                            data_credito = None

                        # Identificar tipo de ocorrencia
                        tipo_ocorrencia = 'OUTROS'
                        descricao = ''
                        if codigo_ocorrencia in OCORRENCIAS_CNAB:
                            tipo_ocorrencia, descricao = OCORRENCIAS_CNAB[codigo_ocorrencia]

                        # Buscar parcela — exact match + fallback zero-pad, prioriza conta
                        conta = arquivo_retorno.conta_bancaria
                        parcela = self._buscar_parcela_por_nosso_numero(nosso_numero, conta)

                        # Idempotência: não duplicar ItemRetorno para mesmo nosso_numero
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

                        # Processar baixa
                        if item.processar_baixa():
                            registros_processados += 1
                            if tipo_ocorrencia == 'LIQUIDACAO':
                                valor_total_pago += valor_pago or valor_titulo
                        else:
                            if item.erro_processamento:
                                registros_erro += 1

                    except Exception as e:
                        registros_erro += 1
                        logger.exception("Erro ao processar linha de retorno: %s", e)

            # Atualizar arquivo
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
            f"Retorno processado: {registros_processados}/{total_registros} registros, "
            f"R$ {valor_total_pago} pagos"
        )

        return {
            'sucesso': True,
            'total_registros': total_registros,
            'registros_processados': registros_processados,
            'registros_erro': registros_erro,
            'valor_total_pago': valor_total_pago,
        }

    def _processar_retorno_cnab240(
        self,
        arquivo_retorno,
        linhas: List[str],
        user
    ) -> Dict:
        """Processa arquivo de retorno CNAB 240"""
        from financeiro.models import (
            ItemRetorno, StatusArquivoRetorno, Parcela
        )

        arquivo_retorno.layout = 'CNAB_240'
        total_registros = 0
        registros_processados = 0
        registros_erro = 0
        valor_total_pago = Decimal('0.00')

        with transaction.atomic():
            for linha in linhas:
                linha = linha.strip()
                if len(linha) < 240:
                    continue

                tipo_registro = linha[7]

                # Registro de detalhe segmento T (tipo 3, segmento T)
                if tipo_registro == '3' and linha[13] == 'T':
                    total_registros += 1

                    try:
                        nosso_numero = linha[37:57].strip()
                        codigo_ocorrencia = linha[15:17]
                        valor_titulo = Decimal(linha[81:96]) / 100

                        # Buscar segmento U correspondente (proxima linha)
                        idx = linhas.index(linha)
                        if idx + 1 < len(linhas):
                            linha_u = linhas[idx + 1].strip()
                            if len(linha_u) >= 240 and linha_u[13] == 'U':
                                valor_pago = Decimal(linha_u[77:92]) / 100
                                data_str = linha_u[137:145]
                                if data_str.strip() and data_str != '00000000':
                                    data_ocorrencia = datetime.strptime(data_str, '%d%m%Y').date()
                                else:
                                    data_ocorrencia = None
                                data_credito_str = linha_u[145:153]
                                if data_credito_str.strip() and data_credito_str != '00000000':
                                    data_credito = datetime.strptime(data_credito_str, '%d%m%Y').date()
                                else:
                                    data_credito = None
                            else:
                                valor_pago = Decimal('0.00')
                                data_ocorrencia = None
                                data_credito = None
                        else:
                            valor_pago = Decimal('0.00')
                            data_ocorrencia = None
                            data_credito = None

                        # Identificar tipo de ocorrencia
                        tipo_ocorrencia = 'OUTROS'
                        descricao = ''
                        if codigo_ocorrencia in OCORRENCIAS_CNAB:
                            tipo_ocorrencia, descricao = OCORRENCIAS_CNAB[codigo_ocorrencia]

                        # Buscar parcela — exact match + fallback zero-pad, prioriza conta
                        conta = arquivo_retorno.conta_bancaria
                        parcela = self._buscar_parcela_por_nosso_numero(nosso_numero, conta)

                        # Idempotência: não duplicar ItemRetorno para mesmo nosso_numero
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

                        # Processar baixa
                        if item.processar_baixa():
                            registros_processados += 1
                            if tipo_ocorrencia == 'LIQUIDACAO':
                                valor_total_pago += valor_pago or valor_titulo
                        else:
                            if item.erro_processamento:
                                registros_erro += 1

                    except Exception as e:
                        registros_erro += 1
                        logger.exception("Erro ao processar linha de retorno CNAB240: %s", e)

            # Atualizar arquivo
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

        return {
            'sucesso': True,
            'total_registros': total_registros,
            'registros_processados': registros_processados,
            'registros_erro': registros_erro,
            'valor_total_pago': valor_total_pago,
        }

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
        from financeiro.models import Parcela, StatusBoleto

        queryset = Parcela.objects.filter(
            status_boleto=StatusBoleto.GERADO,
            pago=False,
            itens_remessa__arquivo_remessa__status='GERADO'
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
        layout: str = 'CNAB_240'
    ) -> Dict:
        """
        Gera remessas agrupando automaticamente as parcelas por conta_bancaria.
        Cada conta gera exatamente 1 arquivo de remessa.

        Args:
            parcela_ids: IDs das parcelas selecionadas
            layout: Layout CNAB (CNAB_240 ou CNAB_400)

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

            resultado = self.gerar_remessa(lista_parcelas, conta, layout)
            _ultimo_request_banco[banco_key] = time.monotonic()

            if resultado.get('sucesso'):
                arq = resultado['arquivo_remessa']
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
