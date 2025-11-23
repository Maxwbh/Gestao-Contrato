"""
Serviço de Integração com BRCobrança para Geração de Boletos

Este serviço integra com a API BRCobrança (via Docker) para geração
de boletos bancários. Suporta os principais bancos brasileiros.

BRCobrança API: https://github.com/kivanio/brcobranca

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
import requests
import base64
import logging
from decimal import Decimal
from datetime import date, timedelta
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class BRCobrancaError(Exception):
    """Exceção para erros do BRCobrança"""
    pass


class BoletoService:
    """
    Serviço para geração de boletos bancários via BRCobrança.

    O BRCobrança deve estar rodando como container Docker:
    docker run -p 9292:9292 kivanio/brcobranca

    Configurar no settings.py:
    BRCOBRANCA_URL = 'http://localhost:9292'
    """

    # Mapeamento de códigos de banco para nomes no BRCobrança
    BANCOS_BRCOBRANCA = {
        '001': 'banco_brasil',
        '004': 'banco_nordeste',
        '021': 'banestes',
        '033': 'santander',
        '041': 'banrisul',
        '070': 'brb',
        '077': 'banco_inter',
        '084': 'unicred',
        '085': 'ailos',
        '104': 'caixa',
        '133': 'cresol',
        '136': 'unicred',
        '237': 'bradesco',
        '341': 'itau',
        '389': 'banco_mercantil',
        '422': 'safra',
        '748': 'sicredi',
        '756': 'sicoob',
    }

    # Carteiras padrão por banco
    CARTEIRAS_PADRAO = {
        '001': '17',       # Banco do Brasil
        '033': '101',      # Santander
        '104': '14',       # Caixa
        '237': '09',       # Bradesco
        '341': '109',      # Itaú
        '748': '1',        # Sicredi
        '756': '1',        # Sicoob
    }

    def __init__(self, brcobranca_url=None):
        """
        Inicializa o serviço de boleto.

        Args:
            brcobranca_url: URL da API BRCobrança (opcional)
        """
        self.brcobranca_url = brcobranca_url or getattr(
            settings, 'BRCOBRANCA_URL', 'http://localhost:9292'
        )
        self.timeout = getattr(settings, 'BRCOBRANCA_TIMEOUT', 30)

    def _get_banco_brcobranca(self, codigo_banco):
        """Retorna o nome do banco para a API BRCobrança"""
        return self.BANCOS_BRCOBRANCA.get(codigo_banco)

    def _formatar_cpf_cnpj(self, documento):
        """Remove formatação do CPF/CNPJ"""
        if documento:
            return ''.join(filter(str.isdigit, documento))
        return ''

    def _formatar_cep(self, cep):
        """Remove formatação do CEP"""
        if cep:
            return ''.join(filter(str.isdigit, cep))
        return ''

    def _calcular_data_limite_desconto(self, data_vencimento, dias_desconto):
        """Calcula a data limite para desconto"""
        if dias_desconto and dias_desconto > 0:
            return data_vencimento - timedelta(days=dias_desconto)
        return None

    def _montar_dados_boleto(self, parcela, conta_bancaria):
        """
        Monta os dados do boleto no formato esperado pelo BRCobrança.

        Args:
            parcela: Instância de Parcela
            conta_bancaria: Instância de ContaBancaria

        Returns:
            dict: Dados formatados para a API
        """
        contrato = parcela.contrato
        comprador = contrato.comprador
        imobiliaria = contrato.imovel.imobiliaria

        # Obter próximo nosso número
        nosso_numero = parcela.obter_proximos_nosso_numero(conta_bancaria)

        # Documento do pagador (CPF ou CNPJ)
        documento_pagador = self._formatar_cpf_cnpj(
            comprador.cpf if comprador.tipo_pessoa == 'PF' else comprador.cnpj
        )

        # Documento do cedente (CNPJ da imobiliária)
        documento_cedente = self._formatar_cpf_cnpj(imobiliaria.cnpj)

        # Endereço do pagador
        endereco_pagador = comprador.endereco_formatado if hasattr(comprador, 'endereco_formatado') else (
            f"{comprador.logradouro}, {comprador.numero} {comprador.complemento}".strip()
        )

        # Carteira
        carteira = conta_bancaria.carteira or self.CARTEIRAS_PADRAO.get(conta_bancaria.banco, '1')

        # Número do documento
        numero_documento = parcela.gerar_numero_documento()

        # Instruções
        instrucoes = [
            imobiliaria.instrucao_padrao or f"Parcela {parcela.numero_parcela} de {contrato.numero_parcelas}",
            f"Contrato: {contrato.numero_contrato}",
            f"Imóvel: {contrato.imovel.identificacao}",
        ]

        # Dados básicos do boleto
        dados = {
            # Dados do Cedente (quem recebe)
            'cedente': imobiliaria.razao_social,
            'documento_cedente': documento_cedente,
            'cedente_endereco': f"{imobiliaria.logradouro}, {imobiliaria.numero}",

            # Dados Bancários
            'banco': conta_bancaria.banco,
            'agencia': conta_bancaria.agencia.replace('-', '').replace('.', ''),
            'conta_corrente': conta_bancaria.conta.replace('-', '').replace('.', ''),
            'convenio': conta_bancaria.convenio or '',
            'carteira': carteira,
            'modalidade': conta_bancaria.modalidade or '',

            # Dados do Boleto
            'nosso_numero': str(nosso_numero),
            'numero_documento': numero_documento,
            'data_documento': date.today().strftime('%Y-%m-%d'),
            'data_vencimento': parcela.data_vencimento.strftime('%Y-%m-%d'),
            'valor': float(parcela.valor_atual),
            'especie': 'R$',
            'aceite': 'S' if imobiliaria.aceite else 'N',
            'especie_documento': imobiliaria.tipo_titulo or 'DM',

            # Dados do Sacado (quem paga)
            'sacado': comprador.nome,
            'documento_sacado': documento_pagador,
            'sacado_endereco': endereco_pagador[:40] if endereco_pagador else '',
            'sacado_cidade': comprador.cidade or '',
            'sacado_uf': comprador.estado or '',
            'sacado_cep': self._formatar_cep(comprador.cep),

            # Instruções
            'instrucao1': instrucoes[0] if len(instrucoes) > 0 else '',
            'instrucao2': instrucoes[1] if len(instrucoes) > 1 else '',
            'instrucao3': instrucoes[2] if len(instrucoes) > 2 else '',

            # Local de Pagamento
            'local_pagamento': 'Pagável em qualquer banco até o vencimento',
        }

        # Adicionar multa se configurada
        if imobiliaria.percentual_multa_padrao > 0:
            if imobiliaria.tipo_valor_multa == 'PERCENTUAL':
                dados['codigo_multa'] = '2'  # Percentual
                dados['percentual_multa'] = float(imobiliaria.percentual_multa_padrao)
            else:
                dados['codigo_multa'] = '1'  # Valor fixo
                dados['valor_multa'] = float(imobiliaria.percentual_multa_padrao)

            # Data início da multa (dia seguinte ao vencimento + dias sem encargos)
            dias_carencia = imobiliaria.dias_para_encargos_padrao or 0
            data_multa = parcela.data_vencimento + timedelta(days=dias_carencia + 1)
            dados['data_multa'] = data_multa.strftime('%Y-%m-%d')

        # Adicionar juros se configurado
        if imobiliaria.percentual_juros_padrao > 0:
            if imobiliaria.tipo_valor_juros == 'PERCENTUAL':
                dados['codigo_juros'] = '2'  # Percentual ao dia
                dados['percentual_juros'] = float(imobiliaria.percentual_juros_padrao)
            else:
                dados['codigo_juros'] = '1'  # Valor fixo por dia
                dados['valor_juros'] = float(imobiliaria.percentual_juros_padrao)

            dias_carencia = imobiliaria.dias_para_encargos_padrao or 0
            data_juros = parcela.data_vencimento + timedelta(days=dias_carencia + 1)
            dados['data_juros'] = data_juros.strftime('%Y-%m-%d')

        # Adicionar desconto se configurado
        if imobiliaria.percentual_desconto_padrao > 0:
            data_limite = self._calcular_data_limite_desconto(
                parcela.data_vencimento,
                imobiliaria.dias_para_desconto_padrao
            )
            if data_limite and data_limite >= date.today():
                if imobiliaria.tipo_valor_desconto == 'PERCENTUAL':
                    dados['codigo_desconto'] = '2'
                    dados['percentual_desconto'] = float(imobiliaria.percentual_desconto_padrao)
                else:
                    dados['codigo_desconto'] = '1'
                    dados['valor_desconto'] = float(imobiliaria.percentual_desconto_padrao)
                dados['data_desconto'] = data_limite.strftime('%Y-%m-%d')

        return dados, nosso_numero

    def gerar_boleto(self, parcela, conta_bancaria):
        """
        Gera um boleto para a parcela usando a API BRCobrança.

        Args:
            parcela: Instância de Parcela
            conta_bancaria: Instância de ContaBancaria

        Returns:
            dict: Resultado da geração com dados do boleto
        """
        try:
            # Verificar se o banco é suportado
            banco_nome = self._get_banco_brcobranca(conta_bancaria.banco)
            if not banco_nome:
                return {
                    'sucesso': False,
                    'erro': f'Banco {conta_bancaria.banco} não suportado pelo BRCobrança'
                }

            # Montar dados do boleto
            dados_boleto, nosso_numero = self._montar_dados_boleto(parcela, conta_bancaria)

            # Preparar payload para a API
            payload = {
                'banco': banco_nome,
                'tipo': 'pdf',  # ou 'base64', 'linha_digitavel', 'codigo_barras'
                'boletos': [dados_boleto]
            }

            # Tentar chamar a API BRCobrança
            try:
                response = requests.post(
                    f"{self.brcobranca_url}/api/boleto",
                    json=payload,
                    timeout=self.timeout,
                    headers={'Content-Type': 'application/json'}
                )

                if response.status_code == 200:
                    result = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}

                    return {
                        'sucesso': True,
                        'nosso_numero': str(nosso_numero),
                        'numero_documento': dados_boleto['numero_documento'],
                        'linha_digitavel': result.get('linha_digitavel', ''),
                        'codigo_barras': result.get('codigo_barras', ''),
                        'valor': Decimal(str(dados_boleto['valor'])),
                        'pdf_content': response.content if not result else base64.b64decode(result.get('pdf', '')),
                        'pix_copia_cola': result.get('pix_copia_cola', ''),
                        'pix_qrcode': result.get('pix_qrcode', ''),
                    }
                else:
                    logger.error(f"Erro na API BRCobrança: {response.status_code} - {response.text}")
                    # Fallback para geração local
                    return self._gerar_boleto_local(dados_boleto, nosso_numero, conta_bancaria)

            except requests.exceptions.RequestException as e:
                logger.warning(f"API BRCobrança não disponível: {e}. Usando fallback local.")
                return self._gerar_boleto_local(dados_boleto, nosso_numero, conta_bancaria)

        except Exception as e:
            logger.exception(f"Erro ao gerar boleto: {e}")
            return {
                'sucesso': False,
                'erro': str(e)
            }

    def _gerar_boleto_local(self, dados_boleto, nosso_numero, conta_bancaria):
        """
        Gera dados básicos do boleto localmente (fallback).
        Gera também um PDF simples com os dados do boleto.
        """
        try:
            # Gerar código de barras e linha digitável básicos
            codigo_barras = self._gerar_codigo_barras_simplificado(
                dados_boleto, conta_bancaria
            )
            linha_digitavel = self._gerar_linha_digitavel(codigo_barras)

            # Gerar PDF
            pdf_content = self._gerar_pdf_boleto(dados_boleto, codigo_barras, linha_digitavel)

            return {
                'sucesso': True,
                'nosso_numero': str(nosso_numero),
                'numero_documento': dados_boleto['numero_documento'],
                'linha_digitavel': linha_digitavel,
                'codigo_barras': codigo_barras,
                'valor': Decimal(str(dados_boleto['valor'])),
                'pdf_content': pdf_content,
            }
        except Exception as e:
            logger.exception(f"Erro no fallback local: {e}")
            return {
                'sucesso': False,
                'erro': f'Falha na geração local: {str(e)}'
            }

    def _gerar_pdf_boleto(self, dados, codigo_barras, linha_digitavel):
        """
        Gera um PDF simples do boleto usando reportlab.
        """
        from io import BytesIO
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.lib import colors
        from reportlab.graphics.barcode import code128

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Margens
        margin = 20 * mm
        y = height - margin

        # Cabeçalho
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, y, "BOLETO BANCÁRIO")
        y -= 10 * mm

        # Dados do cedente
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margin, y, "CEDENTE")
        y -= 5 * mm
        c.setFont("Helvetica", 10)
        c.drawString(margin, y, dados.get('cedente', ''))
        y -= 5 * mm
        c.drawString(margin, y, f"CNPJ: {dados.get('documento_cedente', '')}")
        y -= 8 * mm

        # Dados do sacado
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margin, y, "PAGADOR")
        y -= 5 * mm
        c.setFont("Helvetica", 10)
        c.drawString(margin, y, dados.get('sacado', ''))
        y -= 5 * mm
        c.drawString(margin, y, f"CPF/CNPJ: {dados.get('documento_sacado', '')}")
        y -= 5 * mm
        c.drawString(margin, y, dados.get('sacado_endereco', ''))
        y -= 8 * mm

        # Linha divisória
        c.setStrokeColor(colors.black)
        c.line(margin, y, width - margin, y)
        y -= 10 * mm

        # Dados do boleto
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margin, y, f"Banco: {dados.get('banco', '')}")
        c.drawString(margin + 80 * mm, y, f"Agência: {dados.get('agencia', '')}")
        y -= 6 * mm

        c.drawString(margin, y, f"Nosso Número: {dados.get('nosso_numero', '')}")
        c.drawString(margin + 80 * mm, y, f"Carteira: {dados.get('carteira', '')}")
        y -= 6 * mm

        c.drawString(margin, y, f"Número Documento: {dados.get('numero_documento', '')}")
        y -= 6 * mm

        c.drawString(margin, y, f"Vencimento: {dados.get('data_vencimento', '')}")
        y -= 10 * mm

        # Valor
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, y, f"VALOR: R$ {dados.get('valor', 0):.2f}")
        y -= 15 * mm

        # Linha divisória
        c.line(margin, y, width - margin, y)
        y -= 10 * mm

        # Instruções
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margin, y, "INSTRUÇÕES")
        y -= 5 * mm
        c.setFont("Helvetica", 9)
        for i in range(1, 4):
            instrucao = dados.get(f'instrucao{i}', '')
            if instrucao:
                c.drawString(margin, y, f"- {instrucao}")
                y -= 4 * mm
        y -= 6 * mm

        # Linha digitável
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margin, y, "LINHA DIGITÁVEL")
        y -= 6 * mm
        c.setFont("Courier-Bold", 12)
        c.drawString(margin, y, linha_digitavel)
        y -= 15 * mm

        # Código de barras
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margin, y, "CÓDIGO DE BARRAS")
        y -= 8 * mm

        try:
            barcode = code128.Code128(codigo_barras, barWidth=0.4 * mm, barHeight=15 * mm)
            barcode.drawOn(c, margin, y - 15 * mm)
        except Exception as e:
            c.setFont("Helvetica", 9)
            c.drawString(margin, y, f"[Código: {codigo_barras}]")

        y -= 25 * mm

        # Rodapé
        c.setFont("Helvetica", 8)
        c.drawString(margin, 15 * mm, "Autenticação mecânica - Ficha de compensação")

        c.showPage()
        c.save()

        buffer.seek(0)
        return buffer.read()

    def _gerar_codigo_barras_simplificado(self, dados, conta_bancaria):
        """
        Gera um código de barras simplificado.

        Formato padrão FEBRABAN:
        BBBMC.CCCCD DDDDD.DDDDD DDDDD.DDDDD D FFFFVVVVVVVVVV

        Onde:
        - BBB = Código do banco (3 dígitos)
        - M = Código da moeda (9 = Real)
        - CCCC = Código do beneficiário / agência
        - DDDDD... = Nosso número e outros dados
        - FFFF = Fator de vencimento
        - VVVVVVVVVV = Valor (10 dígitos)
        """
        from datetime import date

        banco = conta_bancaria.banco.zfill(3)
        moeda = '9'

        # Fator de vencimento (dias desde 07/10/1997)
        # FEBRABAN: após 21/02/2025 (fator 10000), reinicia em 22/02/2025 com fator 1000
        data_base_original = date(1997, 10, 7)
        data_base_nova = date(2025, 2, 22)  # Nova data base após overflow
        data_venc = date.fromisoformat(dados['data_vencimento'])

        if data_venc >= data_base_nova:
            # Usar nova data base (reinicia em 1000)
            fator_vencimento = 1000 + (data_venc - data_base_nova).days
        else:
            fator_vencimento = (data_venc - data_base_original).days

        # Garantir 4 dígitos
        fator_vencimento = str(fator_vencimento % 10000).zfill(4)

        # Valor (10 dígitos, sem decimais)
        valor = int(float(dados['valor']) * 100)
        valor_str = str(valor).zfill(10)

        # Campo livre (varia por banco) - simplificado
        agencia = dados['agencia'].zfill(4)[:4]
        conta = dados['conta_corrente'].zfill(8)[:8]
        nosso_num = dados['nosso_numero'].zfill(11)[:11]
        carteira = dados['carteira'].zfill(2)[:2]

        campo_livre = f"{agencia}{conta}{nosso_num}{carteira}"[:25].ljust(25, '0')

        # Montar código de barras sem DV
        codigo_sem_dv = f"{banco}{moeda}{fator_vencimento}{valor_str}{campo_livre}"

        # Calcular DV (módulo 11)
        dv = self._calcular_dv_mod11(codigo_sem_dv)

        # Inserir DV na posição 5
        codigo_barras = f"{codigo_sem_dv[:4]}{dv}{codigo_sem_dv[4:]}"

        return codigo_barras

    def _gerar_linha_digitavel(self, codigo_barras):
        """
        Converte código de barras em linha digitável.

        Formato: AAABC.CCCCX DDDDD.DDDDDY EEEEE.EEEEEZ K UUUUVVVVVVVVVV
        """
        if len(codigo_barras) != 44:
            return ''

        # Campo 1: posições 1-4 do código de barras + 20-24
        campo1 = codigo_barras[0:4] + codigo_barras[19:24]
        dv1 = self._calcular_dv_mod10(campo1)
        campo1_formatado = f"{campo1[:5]}.{campo1[5:]}{dv1}"

        # Campo 2: posições 25-34 do código de barras
        campo2 = codigo_barras[24:34]
        dv2 = self._calcular_dv_mod10(campo2)
        campo2_formatado = f"{campo2[:5]}.{campo2[5:]}{dv2}"

        # Campo 3: posições 35-44 do código de barras
        campo3 = codigo_barras[34:44]
        dv3 = self._calcular_dv_mod10(campo3)
        campo3_formatado = f"{campo3[:5]}.{campo3[5:]}{dv3}"

        # Campo 4: DV geral (posição 5 do código de barras)
        campo4 = codigo_barras[4]

        # Campo 5: Fator vencimento + Valor (posições 6-19)
        campo5 = codigo_barras[5:19]

        return f"{campo1_formatado} {campo2_formatado} {campo3_formatado} {campo4} {campo5}"

    def _calcular_dv_mod11(self, numero):
        """Calcula DV usando módulo 11 (peso 2 a 9)"""
        soma = 0
        peso = 2
        for digito in reversed(numero):
            soma += int(digito) * peso
            peso = peso + 1 if peso < 9 else 2

        resto = soma % 11
        dv = 11 - resto

        if dv in [0, 10, 11]:
            return '1'
        return str(dv)

    def _calcular_dv_mod10(self, numero):
        """Calcula DV usando módulo 10 (peso 2 e 1 alternados)"""
        soma = 0
        peso = 2
        for digito in reversed(numero):
            resultado = int(digito) * peso
            if resultado > 9:
                resultado = resultado - 9
            soma += resultado
            peso = 1 if peso == 2 else 2

        resto = soma % 10
        if resto == 0:
            return '0'
        return str(10 - resto)

    def gerar_boletos_lote(self, parcelas, conta_bancaria):
        """
        Gera boletos para múltiplas parcelas.

        Args:
            parcelas: QuerySet ou lista de Parcelas
            conta_bancaria: Conta bancária a ser usada

        Returns:
            list: Lista de resultados
        """
        resultados = []
        for parcela in parcelas:
            resultado = self.gerar_boleto(parcela, conta_bancaria)
            resultados.append({
                'parcela_id': parcela.id,
                'parcela': str(parcela),
                **resultado
            })
        return resultados

    def verificar_api_disponivel(self):
        """Verifica se a API BRCobrança está disponível"""
        try:
            response = requests.get(
                f"{self.brcobranca_url}/api/health",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False


class CNABService:
    """
    Serviço para geração de arquivos CNAB (remessa/retorno).

    Suporta layouts 240 e 400.
    """

    def __init__(self, brcobranca_url=None):
        self.brcobranca_url = brcobranca_url or getattr(
            settings, 'BRCOBRANCA_URL', 'http://localhost:9292'
        )

    def gerar_remessa(self, parcelas, conta_bancaria, layout='240'):
        """
        Gera arquivo de remessa CNAB para as parcelas.

        Args:
            parcelas: Lista de parcelas com boletos gerados
            conta_bancaria: Conta bancária
            layout: '240' ou '400'

        Returns:
            bytes: Conteúdo do arquivo CNAB
        """
        # TODO: Implementar geração de remessa CNAB
        raise NotImplementedError("Geração de CNAB será implementada em versão futura")

    def processar_retorno(self, arquivo_cnab, conta_bancaria):
        """
        Processa arquivo de retorno CNAB.

        Args:
            arquivo_cnab: Arquivo CNAB de retorno
            conta_bancaria: Conta bancária

        Returns:
            list: Lista de movimentações processadas
        """
        # TODO: Implementar processamento de retorno CNAB
        raise NotImplementedError("Processamento de retorno CNAB será implementado em versão futura")
