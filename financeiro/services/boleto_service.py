"""
Servico de Integracao com BRCobranca para Geracao de Boletos

Este servico integra com a API BRCobranca (boleto_cnab_api) para geracao
de boletos bancarios. Suporta os principais bancos brasileiros.

API BRCobranca: https://github.com/akretion/boleto_cnab_api
Docker: docker run -p 9292:9292 akretion/boleto_cnab_api

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
import requests
import json
import logging
import time
from decimal import Decimal
from datetime import date, timedelta
from django.conf import settings 
from django.utils import timezone
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class BRCobrancaError(Exception):
    """Excecao para erros do BRCobranca"""
    pass


class BoletoService:
    """
    Servico para geracao de boletos bancarios via BRCobranca.

    O BRCobranca (boleto_cnab_api) deve estar rodando como container Docker:
    docker run -p 9292:9292 akretion/boleto_cnab_api

    Configurar no settings.py:
    BRCOBRANCA_URL = 'http://localhost:9292'
    """

    # Mapeamento de codigos de banco para nomes no BRCobranca
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

    # Carteiras padrao por banco (conforme documentacao BRCobranca)
    CARTEIRAS_PADRAO = {
        '001': '18',       # Banco do Brasil
        '033': '102',      # Santander
        '104': '1',        # Caixa (1=com registro)
        '237': '06',       # Bradesco
        '341': '175',      # Itau
        '748': '3',        # Sicredi (3=sem registro)
        '756': '1',        # Sicoob
    }

    # Campos especificos obrigatorios por banco
    CAMPOS_BANCO = {
        '001': {'convenio_obrigatorio': True, 'convenio_len': 7},
        '033': {'convenio_obrigatorio': True, 'convenio_len': 7},
        '104': {'emissao': '4', 'convenio_len': 6},
        '237': {'nosso_numero_len': 11},
        '341': {'seu_numero': True, 'nosso_numero_len': 8},
        '748': {'posto_obrigatorio': True, 'byte_idt': '2', 'nosso_numero_len': 5},
        '756': {
            'variacao': '01',
            'convenio_len': 7,
            'agencia_len': 4,
            'conta_len': 8,
            'nosso_numero_len': 7
        },
    }

    # =========================================================================
    # CAMPOS NAO SUPORTADOS POR BANCO (BRCobranca)
    # Baseado na documentacao oficial: https://github.com/kivanio/brcobranca
    # Estes campos serao removidos antes de enviar para a API
    # =========================================================================
    CAMPOS_NAO_SUPORTADOS = {
        # Banco do Brasil (001) - Nao suporta documento_numero, especie_documento, aceite
        '001': [
            'documento_numero',
            'especie_documento',
            'aceite',
        ],
        # Banco Nordeste (004) - Usa campos padrao
        '004': [],
        # Banestes (021) - Campos padrao
        '021': [],
        # Santander (033) - Campos padrao
        '033': [],
        # Banrisul (041) - Campos padrao
        '041': [],
        # BRB (070) - Campos padrao
        '070': [],
        # Banco Inter (077) - Campos padrao
        '077': [],
        # Unicred (084/136) - Campos padrao
        '084': [],
        # Ailos (085) - Campos padrao
        '085': [],
        # Caixa (104) - Campos padrao (usa emissao e codigo_beneficiario)
        '104': [],
        # Cresol (133) - Campos padrao
        '133': [],
        # Unicred (136) - Campos padrao
        '136': [],
        # Bradesco (237) - Campos padrao
        '237': [],
        # Itau (341) - Campos padrao (usa seu_numero para carteiras especiais)
        '341': [],
        # Banco Mercantil (389) - Campos padrao
        '389': [],
        # Safra (422) - Campos padrao
        '422': [],
        # Sicredi (748) - Nao suporta documento_numero
        '748': [
            'documento_numero',
        ],
        # Sicoob (756) - Nao suporta documento_numero, especie_documento, aceite
        '756': [
            'documento_numero',
            'especie_documento',
            'aceite',
        ],
    }

    # =========================================================================
    # CAMPOS ESPECIFICOS POR BANCO (devem ser adicionados)
    # =========================================================================
    CAMPOS_ESPECIFICOS = {
        # Banco do Brasil (001) - convenio obrigatorio
        '001': {
            'obrigatorios': ['convenio'],
            'opcionais': ['codigo_servico'],
        },
        # Banco Nordeste (004)
        '004': {
            'obrigatorios': [],
            'opcionais': ['digito_conta_corrente'],
        },
        # Banrisul (041)
        '041': {
            'obrigatorios': [],
            'opcionais': ['digito_convenio'],
        },
        # Caixa (104) - emissao obrigatorio
        '104': {
            'obrigatorios': ['emissao'],
            'opcionais': ['codigo_beneficiario'],
        },
        # Itau (341) - seu_numero para carteiras especiais
        '341': {
            'obrigatorios': [],
            'opcionais': ['seu_numero'],
        },
        # Sicredi (748) - posto e byte_idt obrigatorios
        '748': {
            'obrigatorios': ['posto', 'byte_idt'],
            'opcionais': [],
        },
        # Sicoob (756) - variacao e quantidade
        '756': {
            'obrigatorios': ['variacao'],
            'opcionais': ['quantidade', 'codigo_beneficiario'],
        },
        # Unicred (084/136)
        '084': {
            'obrigatorios': [],
            'opcionais': ['conta_corrente_dv'],
        },
        '136': {
            'obrigatorios': [],
            'opcionais': ['conta_corrente_dv'],
        },
        # Safra (422)
        '422': {
            'obrigatorios': [],
            'opcionais': ['agencia_dv', 'conta_corrente_dv'],
        },
    }

    # =========================================================================
    # TAMANHOS MAXIMOS DE CAMPOS POR BANCO
    # =========================================================================
    TAMANHOS_CAMPOS = {
        '001': {  # Banco do Brasil
            'agencia': 4,
            'conta_corrente': 8,
            'convenio': 8,  # 4-8 digitos
            'carteira': 2,
        },
        '004': {  # Banco Nordeste
            'agencia': 4,
            'conta_corrente': 7,
            'nosso_numero': 7,
            'carteira': 2,
        },
        '033': {  # Santander
            'agencia': 4,
            'convenio': 7,
            'nosso_numero': 7,
            'conta_corrente': 9,
        },
        '041': {  # Banrisul
            'agencia': 4,
            'conta_corrente': 8,
            'nosso_numero': 8,
            'convenio': 7,
            'carteira': 1,
        },
        '104': {  # Caixa
            'agencia': 4,
            'convenio': 6,
            'nosso_numero': 17,
        },
        '237': {  # Bradesco
            'agencia': 4,
            'conta_corrente': 7,
            'nosso_numero': 11,
            'carteira': 2,
        },
        '341': {  # Itau
            'agencia': 4,
            'conta_corrente': 5,
            'convenio': 5,
            'nosso_numero': 8,
            'seu_numero': 7,
        },
        '422': {  # Safra
            'agencia': 4,
            'conta_corrente': 8,
            'nosso_numero': 9,
        },
        '748': {  # Sicredi
            'agencia': 4,
            'conta_corrente': 5,
            'convenio': 5,
            'nosso_numero': 5,
            'carteira': 1,
            'posto': 2,
        },
        '756': {  # Sicoob
            'agencia': 4,
            'conta_corrente': 8,
            'convenio': 7,
            'nosso_numero': 7,
        },
        '084': {  # Unicred
            'agencia': 4,
            'conta_corrente': 9,
            'nosso_numero': 10,
            'carteira': 2,
        },
        '136': {  # Unicred
            'agencia': 4,
            'conta_corrente': 9,
            'nosso_numero': 10,
            'carteira': 2,
        },
    }

    def __init__(self, brcobranca_url=None):
        """
        Inicializa o servico de boleto.

        Args:
            brcobranca_url: URL da API BRCobranca (opcional)
        """
        self.brcobranca_url = brcobranca_url or getattr(
            settings, 'BRCOBRANCA_URL', 'http://localhost:9292'
        )
        self.timeout = getattr(settings, 'BRCOBRANCA_TIMEOUT', 30)
        # Configuracoes de retry
        self.max_tentativas = getattr(settings, 'BRCOBRANCA_MAX_TENTATIVAS', 3)
        self.delay_inicial = getattr(settings, 'BRCOBRANCA_DELAY_INICIAL', 2)

    def _get_banco_brcobranca(self, codigo_banco):
        """Retorna o nome do banco para a API BRCobranca"""
        return self.BANCOS_BRCOBRANCA.get(codigo_banco)

    def _formatar_cpf_cnpj(self, documento):
        """Remove formatacao do CPF/CNPJ"""
        if documento:
            return ''.join(filter(str.isdigit, documento))
        return ''

    def _formatar_cep(self, cep):
        """Remove formatacao do CEP"""
        if cep:
            return ''.join(filter(str.isdigit, cep))
        return ''

    def _formatar_data(self, data):
        """Formata data no padrao YYYY/MM/DD exigido pelo BRCobranca"""
        if isinstance(data, date):
            return data.strftime('%Y/%m/%d')
        return str(data).replace('-', '/')

    def _calcular_data_limite_desconto(self, data_vencimento, dias_desconto):
        """Calcula a data limite para desconto"""
        if dias_desconto and dias_desconto > 0:
            return data_vencimento - timedelta(days=dias_desconto)
        return None

    def _filtrar_campos_banco(self, dados, codigo_banco):
        """
        Filtra e valida campos do boleto conforme suporte do banco no BRCobranca.

        Remove campos nao suportados e aplica tamanhos maximos.

        Args:
            dados: Dicionario com dados do boleto
            codigo_banco: Codigo do banco (ex: '001', '756')

        Returns:
            dict: Dados filtrados e validados
        """
        dados_filtrados = dados.copy()

        # Remover campos nao suportados pelo banco
        campos_remover = self.CAMPOS_NAO_SUPORTADOS.get(codigo_banco, [])
        for campo in campos_remover:
            if campo in dados_filtrados:
                logger.debug(f"Removendo campo '{campo}' nao suportado pelo banco {codigo_banco}")
                dados_filtrados.pop(campo)

        # Aplicar tamanhos maximos de campos
        tamanhos = self.TAMANHOS_CAMPOS.get(codigo_banco, {})
        for campo, tamanho_max in tamanhos.items():
            if campo in dados_filtrados and dados_filtrados[campo]:
                valor = str(dados_filtrados[campo])
                # Remover caracteres nao numericos para campos numericos
                if campo in ['agencia', 'conta_corrente', 'convenio', 'nosso_numero', 'carteira', 'posto', 'seu_numero']:
                    valor = ''.join(filter(str.isdigit, valor))
                # Aplicar padding com zeros e truncar
                dados_filtrados[campo] = valor.zfill(tamanho_max)[:tamanho_max]

        # Validar campos obrigatorios especificos do banco
        campos_especificos = self.CAMPOS_ESPECIFICOS.get(codigo_banco, {})
        campos_obrigatorios = campos_especificos.get('obrigatorios', [])
        for campo in campos_obrigatorios:
            if not dados_filtrados.get(campo):
                logger.warning(f"Campo obrigatorio '{campo}' ausente para banco {codigo_banco}")

        logger.info(f"Campos filtrados para banco {codigo_banco}: removidos={campos_remover}")

        return dados_filtrados

    def _montar_dados_boleto(self, parcela, conta_bancaria):
        """
        Monta os dados do boleto no formato esperado pelo BRCobranca.

        Args:
            parcela: Instancia de Parcela
            conta_bancaria: Instancia de ContaBancaria

        Returns:
            tuple: (dict com dados formatados para a API, nosso_numero)
        """
        contrato = parcela.contrato
        comprador = contrato.comprador
        imobiliaria = contrato.imovel.imobiliaria

        # Obter configuracoes de boleto do contrato (personalizadas ou da imobiliaria)
        config_boleto = contrato.get_config_boleto()

        # Obter proximo nosso numero
        nosso_numero = parcela.obter_proximos_nosso_numero(conta_bancaria)

        # Documento do pagador (CPF ou CNPJ)
        documento_pagador = self._formatar_cpf_cnpj(
            comprador.cpf if comprador.tipo_pessoa == 'PF' else comprador.cnpj
        )

        # Documento do cedente (CNPJ da imobiliaria)
        documento_cedente = self._formatar_cpf_cnpj(imobiliaria.cnpj)

        # Endereco do pagador - concatenar todos os campos
        partes_endereco = []
        if comprador.logradouro:
            partes_endereco.append(comprador.logradouro)
        if comprador.numero:
            partes_endereco.append(comprador.numero)
        elif comprador.logradouro:
            partes_endereco.append('S/N')
        if comprador.complemento:
            partes_endereco.append(comprador.complemento)
        if comprador.bairro:
            partes_endereco.append(comprador.bairro)
        if comprador.cidade:
            partes_endereco.append(comprador.cidade)
        if comprador.estado:
            partes_endereco.append(comprador.estado)
        if comprador.cep:
            cep_formatado = self._formatar_cep(comprador.cep)
            if cep_formatado:
                partes_endereco.append(f"CEP {cep_formatado}")

        endereco_pagador = ', '.join(partes_endereco) if partes_endereco else ''

        # Carteira
        carteira = conta_bancaria.carteira or self.CARTEIRAS_PADRAO.get(conta_bancaria.banco, '1')

        # Numero do documento
        numero_documento = parcela.gerar_numero_documento()

        # Instrucoes (usando configuracoes do contrato)
        instrucoes = []

        # Adicionar numero do documento para bancos que nao suportam o campo
        if codigo_banco in ['001', '748', '756']:  # BB, Sicredi, Sicoob
            instrucoes.append(f"Doc: {numero_documento}")

        # Adicionar instrucoes personalizadas
        if config_boleto.get('instrucao_1'):
            instrucoes.append(config_boleto['instrucao_1'])
        if config_boleto.get('instrucao_2'):
            instrucoes.append(config_boleto['instrucao_2'])
        if config_boleto.get('instrucao_3'):
            instrucoes.append(config_boleto['instrucao_3'])

        # Adicionar instrucoes de multa se configurada
        valor_multa_config = config_boleto.get('valor_multa', 0) or 0
        if valor_multa_config > 0:
            tipo_multa = config_boleto.get('tipo_valor_multa', 'PERCENTUAL')
            dias_carencia = config_boleto.get('dias_carencia', 0) or 0
            if tipo_multa == 'PERCENTUAL':
                instrucoes.append(f"Multa de {valor_multa_config}% apos {dias_carencia} dias do vencimento")
            else:
                instrucoes.append(f"Multa de R$ {valor_multa_config:.2f} apos {dias_carencia} dias do vencimento")

        # Adicionar instrucoes de juros se configurada
        valor_juros_config = config_boleto.get('valor_juros', 0) or 0
        if valor_juros_config > 0:
            tipo_juros = config_boleto.get('tipo_valor_juros', 'PERCENTUAL')
            if tipo_juros == 'PERCENTUAL':
                # Calcular juros diario a partir do mensal
                juros_diario = valor_juros_config / 30
                instrucoes.append(f"Juros de {juros_diario:.4f}% ao dia ({valor_juros_config}% ao mes)")
            else:
                instrucoes.append(f"Juros de R$ {valor_juros_config:.2f} ao dia")

        # Adicionar instrucoes de desconto se configurada
        valor_desconto_config = config_boleto.get('valor_desconto', 0) or 0
        if valor_desconto_config > 0:
            tipo_desconto = config_boleto.get('tipo_valor_desconto', 'PERCENTUAL')
            dias_desconto = config_boleto.get('dias_desconto', 0) or 0
            if tipo_desconto == 'PERCENTUAL':
                valor_desc = float(parcela.valor_atual) * float(valor_desconto_config) / 100
                instrucoes.append(f"Desconto de R$ {valor_desc:.2f} ate {dias_desconto} dias antes do vencimento")
            else:
                instrucoes.append(f"Desconto de R$ {valor_desconto_config:.2f} ate {dias_desconto} dias antes do vencimento")

        # Adicionar informacoes padrao
        instrucoes.append(f"Parcela {parcela.numero_parcela} de {contrato.numero_parcelas}")
        instrucoes.append(f"Contrato: {contrato.numero_contrato}")
        if contrato.imovel and contrato.imovel.identificacao:
            instrucoes.append(f"Imovel: {contrato.imovel.identificacao}")

        # Dados do boleto no formato BRCobranca
        dados = {
            # Dados do Cedente (beneficiario - quem recebe)
            'cedente': imobiliaria.razao_social or imobiliaria.nome,
            'documento_cedente': documento_cedente,
            'cedente_endereco': f"{imobiliaria.logradouro}, {imobiliaria.numero}" if imobiliaria.logradouro else '',

            # Dados Bancarios
            'agencia': conta_bancaria.agencia.replace('-', '').replace('.', ''),
            'conta_corrente': conta_bancaria.conta.replace('-', '').replace('.', ''),
            'convenio': str(conta_bancaria.convenio) if conta_bancaria.convenio else '',
            'carteira': str(carteira),

            # Dados do Boleto
            'nosso_numero': str(nosso_numero),
            'documento_numero': numero_documento,  # Campo correto do BRCobranca
            'data_documento': self._formatar_data(date.today()),
            'data_vencimento': self._formatar_data(parcela.data_vencimento),
            'valor': float(parcela.valor_atual),
            'aceite': 'S' if config_boleto.get('aceite') else 'N',
            'especie_documento': config_boleto.get('tipo_titulo') or 'DM',
            'especie': 'R$',

            # Dados do Sacado (pagador - quem paga)
            # Endereco completo concatenado: Rua, Nro, Complemento, Bairro, Cidade, UF, CEP
            'sacado': comprador.nome,
            'sacado_documento': documento_pagador,
            'sacado_endereco': endereco_pagador[:80] if endereco_pagador else '',

            # Instrucoes
            'instrucao1': instrucoes[0] if len(instrucoes) > 0 else '',
            'instrucao2': instrucoes[1] if len(instrucoes) > 1 else '',
            'instrucao3': instrucoes[2] if len(instrucoes) > 2 else '',
            'instrucao4': instrucoes[3] if len(instrucoes) > 3 else '',

            # Local de Pagamento
            'local_pagamento': 'Pagavel em qualquer banco ate o vencimento',
        }

        # Adicionar campos especificos por banco
        codigo_banco = conta_bancaria.banco

        # Banco do Brasil (001)
        if codigo_banco == '001':
            # Convenio obrigatorio (4-8 digitos)
            if not dados.get('convenio'):
                dados['convenio'] = conta_bancaria.convenio or conta_bancaria.conta
            # Formatar convenio com zeros a esquerda se necessario
            if dados.get('convenio'):
                dados['convenio'] = str(dados['convenio']).zfill(7)
            # Campos nao suportados sao removidos pelo _filtrar_campos_banco

        # Santander (033)
        elif codigo_banco == '033':
            # Convenio obrigatorio (7 digitos)
            if not dados.get('convenio'):
                dados['convenio'] = conta_bancaria.convenio or ''
            if dados.get('convenio'):
                dados['convenio'] = str(dados['convenio']).zfill(7)

        # Caixa (104)
        elif codigo_banco == '104':
            dados['codigo_beneficiario'] = conta_bancaria.convenio or ''
            dados['emissao'] = '4'  # Emissao pelo beneficiario
            # Convenio deve ter 6 digitos
            if dados.get('convenio'):
                dados['convenio'] = str(dados['convenio']).zfill(6)

        # Bradesco (237)
        elif codigo_banco == '237':
            # Nosso numero max 11 digitos
            if dados.get('nosso_numero'):
                dados['nosso_numero'] = str(dados['nosso_numero']).zfill(11)[:11]

        # Itau (341)
        elif codigo_banco == '341':
            # Campo seu_numero para carteiras especiais (max 7 digitos)
            dados['seu_numero'] = (numero_documento[:7] if numero_documento else '').zfill(7)
            # Nosso numero max 8 digitos
            if dados.get('nosso_numero'):
                dados['nosso_numero'] = str(dados['nosso_numero']).zfill(8)[:8]

        # Sicredi (748)
        elif codigo_banco == '748':
            # Campos obrigatorios
            dados['posto'] = getattr(conta_bancaria, 'posto', '01') or '01'
            dados['byte_idt'] = '2'  # Geracao pelo beneficiario
            # Nosso numero max 5 digitos
            if dados.get('nosso_numero'):
                dados['nosso_numero'] = str(dados['nosso_numero']).zfill(5)[:5]

        # Sicoob (756)
        # Campos: agencia (4), conta_corrente (8), nosso_numero (7), convenio (7), variacao (2)
        elif codigo_banco == '756':
            # Variacao padrao 01
            dados['variacao'] = getattr(conta_bancaria, 'variacao', None) or '01'
            # Quantidade (obrigatorio, padrao 001)
            dados['quantidade'] = '001'
            # Convenio max 7 digitos
            if dados.get('convenio'):
                dados['convenio'] = str(dados['convenio']).zfill(7)[:7]
            # Agencia max 4 digitos
            if dados.get('agencia'):
                dados['agencia'] = str(dados['agencia']).zfill(4)[:4]
            # Conta corrente max 8 digitos
            if dados.get('conta_corrente'):
                dados['conta_corrente'] = str(dados['conta_corrente']).zfill(8)[:8]
            # Nosso numero max 7 digitos
            if dados.get('nosso_numero'):
                dados['nosso_numero'] = str(dados['nosso_numero']).zfill(7)[:7]
            # Modalidade (codigo_beneficiario quando aplicavel)
            if hasattr(conta_bancaria, 'codigo_beneficiario') and conta_bancaria.codigo_beneficiario:
                dados['codigo_beneficiario'] = conta_bancaria.codigo_beneficiario
            # Campos nao suportados sao removidos pelo _filtrar_campos_banco

        # =====================================================
        # MULTA (apos vencimento)
        # =====================================================
        valor_multa = config_boleto.get('valor_multa', 0) or 0
        if valor_multa > 0:
            dias_carencia = config_boleto.get('dias_carencia', 0) or 0
            # Data de inicio da multa (dia seguinte ao vencimento + carencia)
            data_multa = parcela.data_vencimento + timedelta(days=dias_carencia + 1)
            dados['data_multa'] = self._formatar_data(data_multa)

            if config_boleto.get('tipo_valor_multa') == 'PERCENTUAL':
                # codigo_multa: 2 = percentual
                dados['codigo_multa'] = '2'
                dados['percentual_multa'] = float(valor_multa)
            else:
                # codigo_multa: 1 = valor fixo
                dados['codigo_multa'] = '1'
                dados['valor_multa'] = float(valor_multa)

        # =====================================================
        # JUROS/MORA (por dia de atraso)
        # =====================================================
        valor_juros = config_boleto.get('valor_juros', 0) or 0
        if valor_juros > 0:
            dias_carencia = config_boleto.get('dias_carencia', 0) or 0
            # Data de inicio da mora (dia seguinte ao vencimento + carencia)
            data_mora = parcela.data_vencimento + timedelta(days=dias_carencia + 1)
            dados['data_mora'] = self._formatar_data(data_mora)

            if config_boleto.get('tipo_valor_juros') == 'PERCENTUAL':
                # codigo_mora: 1 = valor diario, 2 = taxa mensal
                dados['codigo_mora'] = '2'  # percentual ao mes
                dados['percentual_mora'] = float(valor_juros)
            else:
                # codigo_mora: 1 = valor por dia
                dados['codigo_mora'] = '1'
                dados['valor_mora'] = float(valor_juros)

        # =====================================================
        # DESCONTO (antes do vencimento)
        # =====================================================
        valor_desconto = config_boleto.get('valor_desconto', 0) or 0
        if valor_desconto > 0:
            dias_desconto = config_boleto.get('dias_desconto', 0) or 0
            data_limite = self._calcular_data_limite_desconto(
                parcela.data_vencimento,
                dias_desconto
            )
            if data_limite and data_limite >= date.today():
                dados['data_desconto'] = self._formatar_data(data_limite)
                if config_boleto.get('tipo_valor_desconto') == 'PERCENTUAL':
                    # Calcular valor do desconto baseado no percentual
                    valor_desc = float(parcela.valor_atual) * float(valor_desconto) / 100
                    dados['desconto'] = round(valor_desc, 2)
                else:
                    dados['desconto'] = float(valor_desconto)

        # =====================================================
        # FILTRAGEM E VALIDACAO FINAL POR BANCO
        # Remove campos nao suportados e aplica tamanhos maximos
        # =====================================================
        dados = self._filtrar_campos_banco(dados, codigo_banco)

        return dados, nosso_numero

    def gerar_boleto(self, parcela, conta_bancaria):
        """
        Gera um boleto para a parcela usando a API BRCobranca.

        API Endpoints:
        - GET /api/boleto - Gera boleto individual
        - GET /api/boleto/nosso_numero - Obtem nosso numero formatado
        - GET /api/boleto/validate - Valida dados do boleto
        - POST /api/boleto/multi - Gera multiplos boletos

        Args:
            parcela: Instancia de Parcela
            conta_bancaria: Instancia de ContaBancaria

        Returns:
            dict: Resultado da geracao com dados do boleto
        """
        try:
            # Verificar se o banco e suportado
            banco_nome = self._get_banco_brcobranca(conta_bancaria.banco)
            if not banco_nome:
                return {
                    'sucesso': False,
                    'erro': f'Banco {conta_bancaria.banco} nao suportado pelo BRCobranca'
                }

            # Montar dados do boleto
            dados_boleto, nosso_numero = self._montar_dados_boleto(parcela, conta_bancaria)

            # Chamar API BRCobranca
            resultado = self._chamar_api_boleto(banco_nome, dados_boleto)

            if resultado.get('sucesso'):
                # Usar gerar_numero_documento() para obter o numero, pois alguns bancos
                # (BB, Sicoob) removem documento_numero dos dados antes de enviar a API
                return {
                    'sucesso': True,
                    'nosso_numero': str(nosso_numero),
                    'numero_documento': parcela.gerar_numero_documento(),
                    'linha_digitavel': resultado.get('linha_digitavel', ''),
                    'codigo_barras': resultado.get('codigo_barras', ''),
                    'valor': Decimal(str(dados_boleto['valor'])),
                    'pdf_content': resultado.get('pdf_content'),
                }
            else:
                return resultado

        except Exception as e:
            logger.exception(f"Erro ao gerar boleto: {e}")
            return {
                'sucesso': False,
                'erro': str(e)
            }

    def _chamar_api_boleto(self, banco_nome, dados_boleto):
        """
        Chama a API BRCobranca para gerar o boleto com retry e backoff.

        Args:
            banco_nome: Nome do banco no formato BRCobranca
            dados_boleto: Dados do boleto

        Returns:
            dict: Resultado com PDF e dados do boleto
        """
        # Validar dados basicos antes de chamar API
        validacao = self._validar_dados_boleto(dados_boleto)
        if not validacao['valido']:
            logger.error(f"Dados de boleto invalidos: {validacao['erros']}")
            return {
                'sucesso': False,
                'erro': f"Dados invalidos: {'; '.join(validacao['erros'])}"
            }

        tentativa = 0
        delay = self.delay_inicial

        while tentativa < self.max_tentativas:
            tentativa += 1
            try:
                logger.info(f"Tentativa {tentativa}/{self.max_tentativas} de gerar boleto")

                # Gerar PDF do boleto
                params = {
                    'bank': banco_nome,
                    'type': 'pdf',
                    'data': json.dumps(dados_boleto)
                }

                logger.info(f"Chamando BRCobranca: {self.brcobranca_url}/api/boleto")

                response = requests.get(
                    f"{self.brcobranca_url}/api/boleto",
                    params=params,
                    timeout=self.timeout
                )

                # Sucesso
                if response.status_code == 200:
                    return self._processar_resposta_sucesso(response, banco_nome, dados_boleto)

                # Erros que justificam retry (5xx)
                elif 500 <= response.status_code < 600:
                    error_msg = f"Erro do servidor {response.status_code}"
                    logger.warning(f"{error_msg} - Tentativa {tentativa}/{self.max_tentativas}")

                    if tentativa < self.max_tentativas:
                        logger.info(f"Aguardando {delay}s antes de nova tentativa...")
                        time.sleep(delay)
                        delay *= 2  # Backoff exponencial
                        continue
                    else:
                        return {
                            'sucesso': False,
                            'erro': f'{error_msg}. Tente novamente em alguns minutos.'
                        }

                # Erros 4xx (nao fazer retry)
                else:
                    error_msg = self._extrair_mensagem_erro(response)
                    logger.error(f"Erro na API BRCobranca ({response.status_code}): {error_msg}")
                    return {
                        'sucesso': False,
                        'erro': error_msg
                    }

            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Erro de conexao (tentativa {tentativa}): {e}")
                if tentativa < self.max_tentativas:
                    logger.info(f"Aguardando {delay}s antes de nova tentativa...")
                    time.sleep(delay)
                    delay *= 2
                    continue
                else:
                    return {
                        'sucesso': False,
                        'erro': f'Nao foi possivel conectar ao servidor BRCobranca em {self.brcobranca_url}. Verifique se o servico esta disponivel e tente novamente.'
                    }

            except requests.exceptions.Timeout as e:
                logger.warning(f"Timeout (tentativa {tentativa}): {e}")
                if tentativa < self.max_tentativas:
                    logger.info(f"Aguardando {delay}s antes de nova tentativa...")
                    time.sleep(delay)
                    delay *= 2
                    continue
                else:
                    return {
                        'sucesso': False,
                        'erro': 'Timeout ao gerar boleto. Tente novamente em alguns minutos.'
                    }

            except Exception as e:
                logger.exception(f"Erro inesperado (tentativa {tentativa}): {e}")
                if tentativa < self.max_tentativas:
                    logger.info(f"Aguardando {delay}s antes de nova tentativa...")
                    time.sleep(delay)
                    delay *= 2
                    continue
                else:
                    return {
                        'sucesso': False,
                        'erro': f'Erro ao gerar boleto: {str(e)}'
                    }

        return {
            'sucesso': False,
            'erro': 'Falha ao gerar boleto apos multiplas tentativas. Tente novamente mais tarde.'
        }

    def _validar_dados_boleto(self, dados):
        """
        Valida dados basicos do boleto antes de enviar para API.

        Returns:
            dict: {'valido': bool, 'erros': list}
        """
        erros = []

        # Validacoes basicas
        campos_obrigatorios = ['cedente', 'agencia', 'conta_corrente', 'nosso_numero',
                               'data_vencimento', 'valor', 'sacado', 'sacado_documento']

        for campo in campos_obrigatorios:
            if not dados.get(campo):
                erros.append(f"Campo obrigatorio ausente: {campo}")

        # Validar valor
        try:
            valor = float(dados.get('valor', 0))
            if valor <= 0:
                erros.append("Valor do boleto deve ser maior que zero")
        except ValueError:
            erros.append("Valor do boleto invalido")

        # Validar data vencimento
        try:
            data_str = dados.get('data_vencimento', '')
            if data_str:
                # Formato esperado: YYYY/MM/DD
                parts = data_str.split('/')
                if len(parts) != 3:
                    erros.append("Data de vencimento em formato invalido")
        except Exception as e:
            erros.append(f"Erro ao validar data: {e}")

        return {
            'valido': len(erros) == 0,
            'erros': erros
        }

    def _obter_dados_boleto(self, banco_nome, dados_boleto):
        """
        Obtem dados do boleto (linha digitavel, codigo de barras, nosso numero formatado)
        via endpoint /api/boleto/data

        Args:
            banco_nome: Nome do banco no formato BRCobranca
            dados_boleto: Dados do boleto

        Returns:
            dict: Dados do boleto ou dicionario vazio se falhar
        """
        try:
            params = {
                'bank': banco_nome,
                'data': json.dumps(dados_boleto)
            }

            response = requests.get(
                f"{self.brcobranca_url}/api/boleto/data",
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                logger.info(f"Dados do boleto obtidos: linha_digitavel={'sim' if data.get('linha_digitavel') else 'nao'}, codigo_barras={'sim' if data.get('codigo_barras') else 'nao'}")
                return {
                    'linha_digitavel': data.get('linha_digitavel', ''),
                    'codigo_barras': data.get('codigo_barras', ''),
                    'nosso_numero_formatado': data.get('nosso_numero', ''),
                    'agencia_conta_boleto': data.get('agencia_conta_boleto', '')
                }
            else:
                logger.warning(f"Erro ao obter dados do boleto: HTTP {response.status_code}")
                return {}

        except Exception as e:
            logger.warning(f"Nao foi possivel obter dados do boleto via /api/boleto/data: {e}")
            return {}

    def _processar_resposta_sucesso(self, response, banco_nome=None, dados_boleto=None):
        """Processa resposta bem-sucedida da API"""
        try:
            content_type = response.headers.get('content-type', '')
            linha_digitavel = ''
            codigo_barras = ''

            if 'application/pdf' in content_type:
                # Resposta e o PDF diretamente
                pdf_content = response.content
                logger.info("Boleto gerado com sucesso (PDF)")

                # Fazer chamada adicional para obter dados do boleto
                if banco_nome and dados_boleto:
                    dados_extras = self._obter_dados_boleto(banco_nome, dados_boleto)
                    linha_digitavel = dados_extras.get('linha_digitavel', '')
                    codigo_barras = dados_extras.get('codigo_barras', '')

            elif 'application/json' in content_type:
                result = response.json()
                if isinstance(result, dict) and 'error' in result:
                    logger.error(f"Erro da API: {result['error']}")
                    return {
                        'sucesso': False,
                        'erro': result.get('error', 'Erro desconhecido')
                    }
                pdf_content = result.get('pdf')
                linha_digitavel = result.get('linha_digitavel', '')
                codigo_barras = result.get('codigo_barras', '')
                logger.info("Boleto gerado com sucesso (JSON)")

            else:
                # Assumir PDF
                pdf_content = response.content
                logger.info("Boleto gerado com sucesso")

                # Fazer chamada adicional para obter dados do boleto
                if banco_nome and dados_boleto:
                    dados_extras = self._obter_dados_boleto(banco_nome, dados_boleto)
                    linha_digitavel = dados_extras.get('linha_digitavel', '')
                    codigo_barras = dados_extras.get('codigo_barras', '')

            return {
                'sucesso': True,
                'pdf_content': pdf_content,
                'linha_digitavel': linha_digitavel,
                'codigo_barras': codigo_barras,
            }

        except Exception as e:
            logger.exception(f"Erro ao processar resposta: {e}")
            return {
                'sucesso': False,
                'erro': f'Erro ao processar resposta: {str(e)}'
            }

    def _extrair_mensagem_erro(self, response):
        """Extrai mensagem de erro da resposta"""
        try:
            error_data = response.json()
            if isinstance(error_data, dict):
                return error_data.get('error', error_data.get('message', response.text))
        except:
            pass

        return response.text or f"Erro HTTP {response.status_code}"

    def verificar_api_disponivel(self):
        """Verifica se a API BRCobranca esta disponivel com retry"""
        for tentativa in range(3):
            try:
                response = requests.get(
                    f"{self.brcobranca_url}/",
                    timeout=5
                )
                disponivel = response.status_code in [200, 404, 405]
                if disponivel:
                    logger.info("API BRCobranca disponivel")
                    return True
            except Exception as e:
                logger.debug(f"Verificacao {tentativa + 1}/3 falhou: {e}")
                if tentativa < 2:
                    time.sleep(1)

        logger.error(f"API BRCobranca indisponivel em {self.brcobranca_url}")
        return False


class CNABService:
    """
    Servico para geracao de arquivos CNAB (remessa/retorno).

    Usa a API BRCobranca para gerar arquivos CNAB240 e CNAB400.
    """

    def __init__(self, brcobranca_url=None):
        self.brcobranca_url = brcobranca_url or getattr(
            settings, 'BRCOBRANCA_URL', 'http://localhost:9292'
        )
        self.timeout = getattr(settings, 'BRCOBRANCA_TIMEOUT', 60)

    def gerar_remessa(self, parcelas, conta_bancaria, layout='240'):
        """
        Gera arquivo de remessa CNAB para as parcelas.

        Args:
            parcelas: Lista de parcelas com boletos gerados
            conta_bancaria: Conta bancaria
            layout: '240' ou '400'

        Returns:
            bytes: Conteudo do arquivo CNAB
        """
        # TODO: Implementar geracao de remessa CNAB via API
        raise NotImplementedError("Geracao de CNAB sera implementada em versao futura")

    def processar_retorno(self, arquivo_cnab, conta_bancaria):
        """
        Processa arquivo de retorno CNAB.

        Args:
            arquivo_cnab: Arquivo CNAB de retorno
            conta_bancaria: Conta bancaria

        Returns:
            list: Lista de movimentacoes processadas
        """
        # TODO: Implementar processamento de retorno CNAB
        raise NotImplementedError("Processamento de retorno CNAB sera implementado em versao futura")
