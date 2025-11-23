"""
Servico CNAB - Geracao de Remessa e Processamento de Retorno

Integra com BRCobranca para geracao de arquivos CNAB 240/400.

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
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
    Integra com a API BRCobranca (Docker container).
    """

    def __init__(self):
        # URL do servico BRCobranca (container Docker)
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

    def _formatar_data(self, data: date) -> str:
        """Formata data para o padrao BRCobranca (DD/MM/YYYY)"""
        if data:
            return data.strftime('%d/%m/%Y')
        return ''

    def _formatar_valor(self, valor: Decimal) -> str:
        """Formata valor para string"""
        if valor:
            return str(float(valor))
        return '0.0'

    def _montar_dados_boleto(self, parcela, conta_bancaria) -> dict:
        """
        Monta os dados de um boleto para o BRCobranca.
        """
        contrato = parcela.contrato
        comprador = contrato.comprador
        imobiliaria = contrato.imovel.imobiliaria

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

        boleto_data = {
            # Identificacao
            'nosso_numero': parcela.nosso_numero,
            'numero_documento': parcela.numero_documento,

            # Valores e datas
            'valor': self._formatar_valor(parcela.valor_boleto or parcela.valor_atual),
            'data_vencimento': self._formatar_data(parcela.data_vencimento),
            'data_documento': self._formatar_data(parcela.data_geracao_boleto.date() if parcela.data_geracao_boleto else timezone.now().date()),

            # Dados do sacado (pagador)
            'sacado': comprador.nome[:60],
            'documento_sacado': cpf_cnpj,
            'endereco_sacado': endereco_sacado[:80],
            'bairro_sacado': (comprador.bairro or '')[:40],
            'cidade_sacado': (comprador.cidade or '')[:30],
            'uf_sacado': (comprador.estado or '')[:2],
            'cep_sacado': self._formatar_cpf_cnpj(comprador.cep or ''),

            # Dados do cedente (recebedor)
            'cedente': (imobiliaria.razao_social or imobiliaria.nome)[:60],
            'documento_cedente': self._formatar_cpf_cnpj(imobiliaria.cnpj),

            # Dados bancarios
            'agencia': conta_bancaria.agencia.replace('-', '').split('-')[0] if conta_bancaria.agencia else '',
            'conta_corrente': conta_bancaria.conta.replace('-', '').split('-')[0] if conta_bancaria.conta else '',
            'digito_conta_corrente': conta_bancaria.conta.split('-')[1] if '-' in (conta_bancaria.conta or '') else '',
            'convenio': conta_bancaria.convenio or '',
            'carteira': conta_bancaria.carteira or '',
            'variacao': '',
            'codigo_cedente': conta_bancaria.convenio or '',

            # Instrucoes
            'instrucao1': f'Parcela {parcela.numero_parcela}/{contrato.numero_parcelas} - Contrato {contrato.numero_contrato}',
            'instrucao2': '',
            'instrucao3': '',
            'instrucao4': '',
            'instrucao5': '',
            'instrucao6': '',

            # Multa e juros
            'percentual_multa': self._formatar_valor(contrato.percentual_multa),
            'valor_mora': self._formatar_valor(contrato.percentual_juros_mora / 30),  # Juros diario
        }

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

        dados_remessa = {
            'banco': banco,
            'tipo': 'cnab240' if layout == 'CNAB_240' else 'cnab400',
            'dados': {
                'empresa_mae': imobiliaria.razao_social or imobiliaria.nome,
                'documento_cedente': self._formatar_cpf_cnpj(imobiliaria.cnpj),
                'agencia': conta_bancaria.agencia.replace('-', '').split('-')[0] if conta_bancaria.agencia else '',
                'conta_corrente': conta_bancaria.conta.replace('-', '').split('-')[0] if conta_bancaria.conta else '',
                'digito_conta': conta_bancaria.conta.split('-')[1] if '-' in (conta_bancaria.conta or '') else '',
                'convenio': conta_bancaria.convenio or '',
                'carteira': conta_bancaria.carteira or '',
                'sequencial_remessa': numero_remessa,
                'codigo_cedente': conta_bancaria.convenio or '',
            },
            'pagamentos': []
        }

        # Adicionar boletos
        valor_total = Decimal('0.00')
        for parcela in parcelas_validas:
            dados_boleto = self._montar_dados_boleto(parcela, conta_bancaria)
            dados_remessa['pagamentos'].append(dados_boleto)
            valor_total += parcela.valor_boleto or parcela.valor_atual

        try:
            # Chamar API BRCobranca
            response = requests.post(
                f'{self.brcobranca_url}/api/remessa',
                json=dados_remessa,
                timeout=60
            )

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
                        f"Remessa {numero_remessa} gerada: {len(parcelas_validas)} boletos, "
                        f"R$ {valor_total}"
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
                erro_msg = f"Erro BRCobranca: {response.status_code} - {response.text}"
                logger.error(erro_msg)
                return {
                    'sucesso': False,
                    'erro': erro_msg
                }

        except requests.exceptions.ConnectionError:
            logger.warning("BRCobranca nao disponivel, gerando remessa local")
            return self._gerar_remessa_local(
                parcelas_validas, conta_bancaria, numero_remessa, layout, valor_total
            )
        except Exception as e:
            logger.error(f"Erro ao gerar remessa: {str(e)}")
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
        agencia_num = conta_bancaria.agencia.replace('-', '').split('-')[0] if conta_bancaria.agencia else ''
        conta_num = conta_bancaria.conta.replace('-', '').split('-')[0] if conta_bancaria.conta else ''
        conta_dv = conta_bancaria.conta.split('-')[1] if '-' in (conta_bancaria.conta or '') else ''
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
            logger.error(f"Erro ao processar retorno: {str(e)}")
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

                        # Buscar parcela
                        parcela = Parcela.objects.filter(
                            nosso_numero=nosso_numero
                        ).first()

                        # Criar item de retorno
                        item = ItemRetorno.objects.create(
                            arquivo_retorno=arquivo_retorno,
                            parcela=parcela,
                            nosso_numero=nosso_numero,
                            codigo_ocorrencia=codigo_ocorrencia,
                            descricao_ocorrencia=descricao,
                            tipo_ocorrencia=tipo_ocorrencia,
                            valor_titulo=valor_titulo,
                            valor_pago=valor_pago if valor_pago > 0 else None,
                            data_ocorrencia=data_ocorrencia,
                            data_credito=data_credito,
                        )

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
                        logger.error(f"Erro ao processar linha de retorno: {str(e)}")

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

                        # Buscar parcela
                        parcela = Parcela.objects.filter(
                            nosso_numero=nosso_numero
                        ).first()

                        # Criar item de retorno
                        item = ItemRetorno.objects.create(
                            arquivo_retorno=arquivo_retorno,
                            parcela=parcela,
                            nosso_numero=nosso_numero,
                            codigo_ocorrencia=codigo_ocorrencia,
                            descricao_ocorrencia=descricao,
                            tipo_ocorrencia=tipo_ocorrencia,
                            valor_titulo=valor_titulo,
                            valor_pago=valor_pago if valor_pago > 0 else None,
                            data_ocorrencia=data_ocorrencia,
                            data_credito=data_credito,
                        )

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
                        logger.error(f"Erro ao processar linha de retorno CNAB240: {str(e)}")

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

    def obter_boletos_sem_remessa(self, conta_bancaria=None) -> List:
        """
        Retorna lista de parcelas com boleto gerado mas sem arquivo de remessa.
        """
        from financeiro.models import Parcela, StatusBoleto

        queryset = Parcela.objects.filter(
            status_boleto=StatusBoleto.GERADO,
            pago=False,
            itens_remessa__isnull=True
        ).select_related(
            'contrato', 'contrato__comprador', 'contrato__imovel'
        )

        if conta_bancaria:
            queryset = queryset.filter(conta_bancaria=conta_bancaria)

        return list(queryset.order_by('data_vencimento'))
