"""
Servico de Integracao com boleto_cnab_api para Geracao de Boletos

Este servico integra com a API boleto_cnab_api para geracao
de boletos bancarios e arquivos CNAB. Suporta os principais bancos brasileiros.

API boleto_cnab_api: https://github.com/Maxwbh/boleto_cnab_api
Docker: docker run -p 9292:9292 maxwbh/boleto_cnab_api

Endpoints disponiveis:
- GET  /api/health           - Verificacao de saude
- GET  /api/boleto/validate  - Validar dados do boleto
- GET  /api/boleto/data      - Obter dados sem gerar PDF
- GET  /api/boleto/nosso_numero - Obter nosso numero
- GET  /api/boleto           - Gerar boleto (PDF/JPG/PNG/TIF)
- POST /api/boleto/multi     - Gerar multiplos boletos
- POST /api/remessa          - Gerar arquivo CNAB remessa
- POST /api/retorno          - Processar arquivo CNAB retorno

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
import requests
import json
import logging
import time
import re
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
    Servico para geracao de boletos bancarios via boleto_cnab_api.

    O boleto_cnab_api deve estar rodando como container Docker:
    docker run -p 9292:9292 maxwbh/boleto_cnab_api

    Configurar no settings.py:
    BRCOBRANCA_URL = 'http://localhost:9292'

    Endpoints utilizados:
    - GET /api/boleto - Gerar boleto individual
    - POST /api/boleto/multi - Gerar multiplos boletos
    - GET /api/boleto/validate - Validar dados do boleto
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
    # Baseado na analise do codigo-fonte oficial: https://github.com/kivanio/brcobranca
    # Ver documentacao completa em: docs/BRCOBRANCA_CAMPOS_REFERENCIA.md
    #
    # IMPORTANTE: Todos os campos da classe Base do BRCobranca SAO ACEITOS por
    # todos os bancos. Isso inclui:
    # - documento_numero / numero_documento (ENVIAR PARA TODOS OS BANCOS)
    # - aceite, especie_documento, especie, moeda (campos padrao)
    # - instrucoes, local_pagamento, cedente_endereco, sacado_endereco
    # - codigo_multa, valor_multa, percentual_multa, data_multa
    # - codigo_mora, valor_mora, percentual_mora, data_mora
    # - desconto, data_desconto
    #
    # Filtrar APENAS campos que:
    # 1. Excedem tamanho maximo do banco
    # 2. Sao obrigatorios mas estao vazios
    # 3. Tem formato incompativel com o banco
    #
    # NUNCA filtrar campos opcionais validos da classe Base!
    # =========================================================================
    CAMPOS_NAO_SUPORTADOS = {
        # Banco do Brasil (001)
        # Aceita TODOS os campos da Base + convenio (4-8 dig) + codigo_servico
        # IMPORTANTE: BRCobranca aceita APENAS documento_numero (não aceita numero_documento)
        '001': ['numero_documento'],

        # Banco Nordeste (004)
        # Aceita TODOS os campos da Base
        # IMPORTANTE: BRCobranca aceita APENAS documento_numero (não aceita numero_documento)
        '004': ['numero_documento'],

        # Banestes (021)
        # Aceita TODOS os campos da Base
        # IMPORTANTE: BRCobranca aceita APENAS documento_numero (não aceita numero_documento)
        '021': ['numero_documento'],

        # Santander (033)
        # Aceita TODOS os campos da Base + convenio obrigatorio (7 dig)
        # IMPORTANTE: BRCobranca aceita APENAS documento_numero (não aceita numero_documento)
        '033': ['numero_documento'],

        # Banrisul (041)
        # Aceita TODOS os campos da Base
        # IMPORTANTE: BRCobranca aceita APENAS documento_numero (não aceita numero_documento)
        '041': ['numero_documento'],

        # BRB (070)
        # Aceita TODOS os campos da Base
        # IMPORTANTE: BRCobranca aceita APENAS documento_numero (não aceita numero_documento)
        '070': ['numero_documento'],

        # Banco Inter (077)
        # Aceita TODOS os campos da Base
        # IMPORTANTE: BRCobranca aceita APENAS documento_numero (não aceita numero_documento)
        '077': ['numero_documento'],

        # Unicred (084/136)
        # Aceita TODOS os campos da Base + conta_corrente_dv
        # IMPORTANTE: BRCobranca aceita APENAS documento_numero (não aceita numero_documento)
        '084': ['numero_documento'],

        # Ailos (085)
        # Aceita TODOS os campos da Base
        # IMPORTANTE: BRCobranca aceita APENAS documento_numero (não aceita numero_documento)
        '085': ['numero_documento'],

        # Caixa (104)
        # Aceita TODOS os campos da Base + emissao (1 dig) + codigo_beneficiario
        # IMPORTANTE: BRCobranca aceita APENAS documento_numero (não aceita numero_documento)
        '104': ['numero_documento'],

        # Cresol (133)
        # Aceita TODOS os campos da Base
        # IMPORTANTE: BRCobranca aceita APENAS documento_numero (não aceita numero_documento)
        '133': ['numero_documento'],

        # Unicred (136)
        # Aceita TODOS os campos da Base + conta_corrente_dv
        # IMPORTANTE: BRCobranca aceita APENAS documento_numero (não aceita numero_documento)
        '136': ['numero_documento'],

        # Bradesco (237)
        # Aceita TODOS os campos da Base
        # IMPORTANTE: BRCobranca aceita APENAS documento_numero (não aceita numero_documento)
        '237': ['numero_documento'],

        # Itau (341)
        # Aceita TODOS os campos da Base + seu_numero (para carteiras especificas)
        # IMPORTANTE: BRCobranca aceita APENAS documento_numero (não aceita numero_documento)
        '341': ['numero_documento'],

        # Banco Mercantil (389)
        # Aceita TODOS os campos da Base
        # IMPORTANTE: BRCobranca aceita APENAS documento_numero (não aceita numero_documento)
        '389': ['numero_documento'],

        # Safra (422)
        # Aceita TODOS os campos da Base + agencia_dv + conta_corrente_dv
        # IMPORTANTE: BRCobranca aceita APENAS documento_numero (não aceita numero_documento)
        '422': ['numero_documento'],

        # Sicredi (748)
        # Aceita TODOS os campos da Base + posto (2 dig) + byte_idt (1 dig)
        # IMPORTANTE: BRCobranca aceita APENAS documento_numero (não aceita numero_documento)
        '748': ['numero_documento'],

        # Sicoob (756)
        # Aceita TODOS os campos da Base + variacao (2 dig) + quantidade (3 dig)
        # IMPORTANTE: BRCobranca aceita APENAS documento_numero (não aceita numero_documento)
        '756': ['numero_documento'],
    }

    # =========================================================================
    # CAMPOS ESPECIFICOS POR BANCO (devem ser adicionados)
    # Campos especificos alem dos campos comuns da classe Base
    # Ver documentacao completa: docs/BRCOBRANCA_CAMPOS_REFERENCIA.md
    # =========================================================================
    CAMPOS_ESPECIFICOS = {
        # Banco do Brasil (001)
        # Convenio obrigatorio (4-8 digitos)
        # Codigo_servico opcional (boolean)
        '001': {
            'obrigatorios': ['convenio'],
            'opcionais': ['codigo_servico'],
            'tamanhos': {'convenio': (4, 8)},  # min, max
        },

        # Banco Nordeste (004)
        '004': {
            'obrigatorios': [],
            'opcionais': ['digito_conta_corrente'],
            'tamanhos': {},
        },

        # Banrisul (041)
        '041': {
            'obrigatorios': [],
            'opcionais': ['digito_convenio'],
            'tamanhos': {},
        },

        # Santander (033)
        # Convenio obrigatorio (7 digitos)
        '033': {
            'obrigatorios': ['convenio'],
            'opcionais': [],
            'tamanhos': {'convenio': (7, 7)},
        },

        # Caixa (104)
        # Emissao obrigatorio (1 digito, padrao '4')
        # Codigo_beneficiario opcional (geralmente igual ao convenio)
        '104': {
            'obrigatorios': ['emissao'],
            'opcionais': ['codigo_beneficiario'],
            'tamanhos': {'emissao': (1, 1), 'convenio': (6, 6)},
        },

        # Itau (341)
        # Seu_numero obrigatorio para carteiras: 198,106,107,122,142,143,195,196
        '341': {
            'obrigatorios': [],
            'opcionais': ['seu_numero'],
            'tamanhos': {'seu_numero': (0, 7)},
            'carteiras_seu_numero': ['198', '106', '107', '122', '142', '143', '195', '196'],
        },

        # Sicredi (748)
        # Posto obrigatorio (2 digitos)
        # Byte_idt obrigatorio (1 digito, geralmente '2' para geracao pelo beneficiario)
        '748': {
            'obrigatorios': ['posto', 'byte_idt'],
            'opcionais': [],
            'tamanhos': {'posto': (2, 2), 'byte_idt': (1, 1)},
        },

        # Sicoob (756)
        # Variacao obrigatorio (2 digitos, padrao '01')
        # Quantidade opcional (3 digitos, padrao '001')
        # Codigo_beneficiario opcional
        '756': {
            'obrigatorios': ['variacao'],
            'opcionais': ['quantidade', 'codigo_beneficiario'],
            'tamanhos': {'variacao': (2, 2), 'quantidade': (3, 3)},
        },

        # Unicred (084/136)
        '084': {
            'obrigatorios': [],
            'opcionais': ['conta_corrente_dv'],
            'tamanhos': {},
        },
        '136': {
            'obrigatorios': [],
            'opcionais': ['conta_corrente_dv'],
            'tamanhos': {},
        },

        # Safra (422)
        '422': {
            'obrigatorios': [],
            'opcionais': ['agencia_dv', 'conta_corrente_dv'],
            'tamanhos': {},
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

        # Codigo do banco (necessario antes de montar 'dados')
        codigo_banco = conta_bancaria.banco

        # Numero do documento
        numero_documento = parcela.gerar_numero_documento()

        # ── Slot 1: Identificação ──────────────────────────────────────────────
        if parcela.tipo_parcela == 'INTERMEDIARIA':
            try:
                num_seq = parcela.intermediaria_origem.numero_sequencial
                id_label = f"Intermediaria {num_seq}"
            except Exception:
                id_label = "Intermediaria"
        else:
            id_label = f"Parcela {parcela.numero_parcela}/{contrato.numero_parcelas}"
        instr1 = f"{id_label} | Contrato: {contrato.numero_contrato} | 1a Via"

        # ── Slot 2: Encargos pós-vencimento (Multa | Juros) — 1 linha ─────────
        partes_encargo = []
        valor_multa_config = config_boleto.get('valor_multa', 0) or 0
        if valor_multa_config > 0:
            tipo_multa = config_boleto.get('tipo_valor_multa', 'PERCENTUAL')
            dias_carencia = config_boleto.get('dias_carencia', 0) or 0
            prefixo = f"apos {dias_carencia}d" if dias_carencia else "apos venc."
            if tipo_multa == 'PERCENTUAL':
                partes_encargo.append(f"Multa {valor_multa_config}% {prefixo}")
            else:
                partes_encargo.append(f"Multa R$ {valor_multa_config:.2f} {prefixo}")
        else:
            pct_multa = getattr(contrato, 'percentual_multa', None)
            if pct_multa and float(pct_multa) > 0:
                partes_encargo.append(f"Multa {pct_multa}% apos venc.")

        valor_juros_config = config_boleto.get('valor_juros', 0) or 0
        if valor_juros_config > 0:
            tipo_juros = config_boleto.get('tipo_valor_juros', 'PERCENTUAL')
            if tipo_juros == 'PERCENTUAL':
                partes_encargo.append(f"Juros {valor_juros_config}%/mes ({valor_juros_config/30:.4f}%/dia)")
            else:
                partes_encargo.append(f"Juros R$ {valor_juros_config:.2f}/dia")
        else:
            pct_juros = getattr(contrato, 'percentual_juros_mora', None)
            if pct_juros and float(pct_juros) > 0:
                partes_encargo.append(f"Juros {pct_juros}%/mes apos venc.")
        instr2 = ("Apos vencimento: " + " | ".join(partes_encargo)) if partes_encargo else ''

        # ── Slot 3: Desconto (só se ainda vigente na data de emissão) ──────────
        instr3 = ''
        valor_desconto_config = config_boleto.get('valor_desconto', 0) or 0
        if valor_desconto_config > 0:
            dias_desconto = config_boleto.get('dias_desconto', 0) or 0
            tipo_desconto = config_boleto.get('tipo_valor_desconto', 'PERCENTUAL')
            data_limite_desc = self._calcular_data_limite_desconto(parcela.data_vencimento, dias_desconto)
            if data_limite_desc and data_limite_desc >= date.today():
                if tipo_desconto == 'PERCENTUAL':
                    valor_desc_r = float(parcela.valor_atual) * float(valor_desconto_config) / 100
                    instr3 = f"Desconto: R$ {valor_desc_r:.2f} ({valor_desconto_config}%) ate {data_limite_desc.strftime('%d/%m/%Y')}"
                else:
                    instr3 = f"Desconto: R$ {valor_desconto_config:.2f} ate {data_limite_desc.strftime('%d/%m/%Y')}"

        # ── Slot 4: reservado para 2ª Via com valor atualizado (preenchido em gerar_segunda_via) ──
        instr4 = ''

        # ── Slots 5-7: instruções configuráveis ────────────────────────────────
        instr5 = config_boleto.get('instrucao_1', '') or ''
        instr6 = config_boleto.get('instrucao_2', '') or ''
        instr7 = config_boleto.get('instrucao_3', '') or ''

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
             # manter ambas chaves para compatibilidade com diferentes versões/expectativas
             'numero_documento': numero_documento,
             'documento_numero': numero_documento,  # Alias usado por alguns bancos/implementações
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

             # Instrucoes — slots fixos (1ª via; slot 4 preenchido pela 2ª via)
             'instrucao1': instr1,   # Identificação: Parcela/Intermediária | Contrato | 1a/2a Via
             'instrucao2': instr2,   # Encargos pós-vencimento: Multa | Juros
             'instrucao3': instr3,   # Desconto (se vigente)
             'instrucao4': instr4,   # Reservado: valor atualizado na 2ª via vencida
             'instrucao5': instr5,   # Configurável: instrucao_1 do config
             'instrucao6': instr6,   # Configurável: instrucao_2 do config
             'instrucao7': instr7,   # Configurável: instrucao_3 do config

             # Local de Pagamento
             'local_pagamento': 'Pagavel em qualquer banco ate o vencimento',
             # Codigo do banco para validacoes posteriores
             'codigo_banco': codigo_banco,
         }

        # Adicionar campos especificos por banco (usa codigo_banco ja existente)
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
            # Codigo beneficiario: usar campo especifico, com fallback para convenio
            codigo_benef = getattr(conta_bancaria, 'codigo_beneficiario', '') or conta_bancaria.convenio or ''
            dados['codigo_beneficiario'] = codigo_benef
            # Tipo de emissao: usar campo especifico, com fallback para '4' (beneficiario)
            dados['emissao'] = getattr(conta_bancaria, 'emissao', '') or '4'
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
            # Campos obrigatorios: usar valores do modelo com fallbacks seguros
            dados['posto'] = getattr(conta_bancaria, 'posto', '') or '01'
            dados['byte_idt'] = getattr(conta_bancaria, 'byte_idt', '') or '2'
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
        Gera boleto para a parcela usando BRCobranca.
        Retorna dict padronizado: {'sucesso': bool, 'erro': str, ...}
        """
        try:
            # Validar conta bancária para bancos com campos obrigatórios
            banco = getattr(conta_bancaria, 'banco', '')
            convenio = getattr(conta_bancaria, 'convenio', '') or ''
            if banco == '001' and not convenio:
                return {
                    'sucesso': False,
                    'erro': (
                        'Banco do Brasil requer o campo "Convênio" preenchido na conta bancária. '
                        'Acesse Configurações → Conta Bancária e informe o número do convênio.'
                    )
                }
            if banco == '033' and not convenio:
                return {
                    'sucesso': False,
                    'erro': (
                        'Santander requer o campo "Convênio" preenchido na conta bancária (7 dígitos). '
                        'Acesse Configurações → Conta Bancária e informe o número do convênio.'
                    )
                }
            if banco == '104' and not convenio:
                return {
                    'sucesso': False,
                    'erro': (
                        'Caixa Econômica requer o campo "Convênio" preenchido na conta bancária (6 dígitos). '
                        'Acesse Configurações → Conta Bancária e informe o número do convênio.'
                    )
                }
            if banco == '748':
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
                            'Sicredi requer o campo "Byte IDT" preenchido na conta bancária (1 dígito). '
                            'Acesse Configurações → Conta Bancária e informe o Byte IDT.'
                        )
                    }

            # Montar dados do boleto (ja inclui numero_documento e validacoes)
            dados_boleto, nosso_numero = self._montar_dados_boleto(parcela, conta_bancaria)

            # Verificar se banco e suportado
            banco_nome = self._get_banco_brcobranca(getattr(conta_bancaria, 'banco', ''))
            if not banco_nome:
                msg = f"Banco '{getattr(conta_bancaria, 'banco', '')}' nao suportado pelo BRCobranca"
                logger.error(msg)
                return {'sucesso': False, 'erro': msg}

            resultado = self._chamar_api_boleto(banco_nome, dados_boleto)

            # Em caso de sucesso, incluir identificadores locais para UI
            if resultado.get('sucesso'):
                # Usar nosso_numero retornado pela API, se disponivel
                # Caso contrario, usar o nosso_numero local
                nosso_numero_final = resultado.get('nosso_numero_api') or str(nosso_numero)

                if resultado.get('nosso_numero_api'):
                    logger.info(f"Usando nosso_numero da API: {nosso_numero_final}")
                else:
                    logger.info(f"Usando nosso_numero local: {nosso_numero_final}")

                # Usar gerar_numero_documento() para obter o numero, pois alguns bancos
                # (BB, Sicoob) removem documento_numero dos dados antes de enviar a API
                return {
                    'sucesso': True,
                    'nosso_numero': nosso_numero_final,
                    'numero_documento': parcela.gerar_numero_documento(),
                    'linha_digitavel': resultado.get('linha_digitavel', ''),
                    'codigo_barras': resultado.get('codigo_barras', ''),
                    'valor': Decimal(str(dados_boleto['valor'])),
                    'pdf_content': resultado.get('pdf_content'),
                }
            else:
                return resultado

        except Exception as e:
            logger.exception("Erro ao gerar boleto: %s", e)
            return {'sucesso': False, 'erro': 'Erro interno ao gerar boleto. Tente novamente em alguns minutos.'}

    def gerar_segunda_via(self, parcela, conta_bancaria, data_referencia=None):
        """
        Gera segunda via do boleto com juros e multa atualizados para data_referencia (padrão: hoje).
        Reutiliza o nosso_número já atribuído à parcela.
        Não salva o PDF na parcela — retorna apenas o conteúdo.

        Returns:
            dict com 'sucesso', 'pdf_content', 'valor_total', 'valor_juros', 'valor_multa', 'erro'
        """
        try:
            if data_referencia is None:
                data_referencia = timezone.localdate()

            # Calcular juros e multa atualizados
            valor_juros = Decimal('0.00')
            valor_multa = Decimal('0.00')
            if data_referencia > parcela.data_vencimento:
                valor_juros, valor_multa = parcela.calcular_juros_multa(data_referencia)

            valor_total = parcela.valor_atual + valor_juros + valor_multa

            # Montar dados base do boleto (instrucao1 já tem "1a Via")
            dados_boleto, _ = self._montar_dados_boleto(parcela, conta_bancaria)

            # Sobrepor valor com total atualizado
            dados_boleto['valor'] = float(valor_total)

            # Reutilizar nosso_número existente se disponível
            if parcela.nosso_numero:
                dados_boleto['nosso_numero'] = str(parcela.nosso_numero)

            # ── Slot 1: trocar "1a Via" por "2a Via" ──────────────────────────
            dados_boleto['instrucao1'] = dados_boleto.get('instrucao1', '').replace('1a Via', '2a Via')

            # ── Slot 4: valor atualizado — APENAS se vencida (vencimento < hoje) ──
            if data_referencia > parcela.data_vencimento:
                vt_str = f"{float(valor_total):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                dados_boleto['instrucao4'] = (
                    f"Valor atualizado p/ pagamento em "
                    f"{data_referencia.strftime('%d/%m/%Y')}   R$ {vt_str}"
                )
            # (se em dia, instrucao4 permanece vazio — reservado mas não impresso)

            banco_nome = self._get_banco_brcobranca(getattr(conta_bancaria, 'banco', ''))
            if not banco_nome:
                return {'sucesso': False, 'erro': 'Banco não suportado pelo BRCobrança'}

            resultado = self._chamar_api_boleto(banco_nome, dados_boleto)

            if resultado.get('sucesso'):
                return {
                    'sucesso': True,
                    'pdf_content': resultado.get('pdf_content'),
                    'valor_total': valor_total,
                    'valor_juros': valor_juros,
                    'valor_multa': valor_multa,
                    'linha_digitavel': resultado.get('linha_digitavel', ''),
                }
            return resultado

        except Exception as e:
            logger.exception("Erro ao gerar segunda via: %s", e)
            return {'sucesso': False, 'erro': str(e)}

    def gerar_carne(self, parcelas, conta_bancaria):
        """
        Gera carnê (múltiplos boletos em um único PDF) via POST /api/boleto/multi.

        Args:
            parcelas: lista/queryset de Parcela
            conta_bancaria: ContaBancaria a usar para todos os boletos

        Returns:
            dict: {
                'sucesso': bool,
                'pdf_content': bytes | None,
                'total': int,
                'erro': str | None,
            }
        """
        banco_nome = self._get_banco_brcobranca(getattr(conta_bancaria, 'banco', ''))
        if not banco_nome:
            return {'sucesso': False, 'erro': 'Banco não suportado pelo BRCobrança'}

        boletos_data = []
        for parcela in parcelas:
            try:
                dados = self._montar_dados_boleto(parcela, conta_bancaria)
                dados.pop('codigo_banco', None)
                boletos_data.append(dados)
            except Exception as e:
                logger.warning('gerar_carne: erro ao montar dados parcela pk=%s: %s', parcela.pk, e)

        if not boletos_data:
            return {'sucesso': False, 'erro': 'Nenhum boleto pôde ser preparado'}

        payload = {
            'bank': banco_nome,
            'type': 'pdf',
            'data': boletos_data,
        }

        url = f"{self.brcobranca_url}/api/boleto/multi"
        try:
            response = requests.post(
                url,
                json=payload,
                headers={'Accept': 'application/vnd.BoletoApi-v1+json'},
                timeout=max(self.timeout, 60),
            )
        except requests.exceptions.RequestException as e:
            logger.exception('gerar_carne: erro de conexão com BRCobrança: %s', e)
            return {'sucesso': False, 'erro': f'Erro de conexão: {e}'}

        if response.status_code == 200:
            pdf_content = response.content
            if not pdf_content:
                return {'sucesso': False, 'erro': 'BRCobrança retornou PDF vazio'}
            logger.info('Carnê PDF gerado (%d boletos, %d bytes)', len(boletos_data), len(pdf_content))
            return {
                'sucesso': True,
                'pdf_content': pdf_content,
                'total': len(boletos_data),
            }

        error_msg = self._extrair_mensagem_erro(response)
        logger.error('gerar_carne: erro HTTP %s — %s', response.status_code, error_msg)
        return {'sucesso': False, 'erro': error_msg}

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

        # Remover campos internos que nao devem ser enviados para a API
        dados_boleto.pop('codigo_banco', None)

        tentativa = 0
        delay = self.delay_inicial

        while tentativa < self.max_tentativas:
            tentativa += 1
            try:
                logger.info(f"Tentativa {tentativa}/{self.max_tentativas} de gerar boleto")

                # Gerar PDF do boleto via GET /api/boleto
                # Conforme documentacao customizada da API boleto_cnab_api:
                # https://github.com/Maxwbh/boleto_cnab_api
                # Exemplos: https://github.com/Maxwbh/boleto_cnab_api/blob/master/EXEMPLOS_MAXIMO_CAMPOS.md
                #
                # Endpoint: GET /api/boleto
                # Parametros:
                #   - bank: nome do banco (ex: 'sicoob', 'banco_brasil')
                #   - type: formato de saida (pdf, jpg, png, tif)
                #   - data: JSON stringificado com dados do boleto
                #
                # Ver documentacao completa: docs/BRCOBRANCA_CAMPOS_REFERENCIA.md

                # Preparar dados do boleto incluindo TODOS os campos disponiveis
                boleto_data = {
                    # Dados do Beneficiario (Cedente)
                    'cedente': dados_boleto.get('cedente', ''),
                    'documento_cedente': dados_boleto.get('documento_cedente', ''),

                    # Dados do Pagador (Sacado)
                    'sacado': dados_boleto.get('sacado', ''),
                    'sacado_documento': dados_boleto.get('sacado_documento', ''),
                    'sacado_endereco': dados_boleto.get('sacado_endereco', ''),

                    # Dados Bancarios
                    'agencia': dados_boleto.get('agencia', ''),
                    'conta_corrente': dados_boleto.get('conta_corrente', ''),
                    'convenio': dados_boleto.get('convenio', ''),
                    'carteira': dados_boleto.get('carteira', ''),

                    # Identificacao do Boleto
                    'nosso_numero': dados_boleto.get('nosso_numero', ''),
                    'numero_documento': dados_boleto.get('numero_documento', ''),
                    'documento_numero': dados_boleto.get('documento_numero', ''),

                    # Valores e Datas
                    'valor': dados_boleto.get('valor', ''),
                    'data_vencimento': dados_boleto.get('data_vencimento', ''),

                    # Campos obrigatorios da classe Base (ENVIAR SEMPRE)
                    'moeda': dados_boleto.get('moeda', '9'),
                    'especie': dados_boleto.get('especie', 'R$'),
                    'especie_documento': dados_boleto.get('especie_documento', 'DM'),
                    'aceite': dados_boleto.get('aceite', 'S'),

                    # Informacoes e Instrucoes
                    'local_pagamento': dados_boleto.get('local_pagamento', 'Pagavel em qualquer banco'),
                    'instrucao1': dados_boleto.get('instrucao1', ''),
                    'instrucao2': dados_boleto.get('instrucao2', ''),
                    'instrucao3': dados_boleto.get('instrucao3', ''),
                    'instrucao4': dados_boleto.get('instrucao4', ''),
                }

                # Adicionar campos opcionais se existirem
                # Enviando TODOS os campos disponiveis conforme recomendacao
                campos_opcionais = [
                    # Campos especificos por banco
                    'variacao', 'posto', 'byte_idt', 'emissao', 'codigo_beneficiario',
                    'seu_numero', 'codigo_servico',
                    # Campos adicionais
                    'data_documento', 'cedente_endereco', 'data_processamento',
                    'quantidade', 'avalista', 'avalista_documento',
                    # Multa
                    'codigo_multa', 'percentual_multa', 'valor_multa', 'data_multa',
                    # Mora/Juros
                    'codigo_mora', 'percentual_mora', 'valor_mora', 'data_mora',
                    # Desconto
                    'desconto', 'data_desconto',
                    # Instrucoes adicionais
                    'instrucao5', 'instrucao6', 'instrucao7',
                    # Outros campos opcionais da classe Base
                    'demonstrativo', 'emv', 'descontos_e_abatimentos'
                ]

                for campo in campos_opcionais:
                    if campo in dados_boleto and dados_boleto[campo]:
                        boleto_data[campo] = dados_boleto[campo]

                # Preparar parametros da requisicao conforme API customizada
                params = {
                    'bank': banco_nome,
                    'type': 'pdf',
                    'data': json.dumps(boleto_data)
                }

                # Log detalhado da requisicao
                url = f"{self.brcobranca_url}/api/boleto"
                logger.info(f"Chamando BRCobranca: {url}")
                logger.debug(f"Banco: {banco_nome}, params count: {len(params)}")

                # Enviar via GET
                # O header Accept e necessario para o versionamento via header do Grape API
                # (version 'v1', using: :header, vendor: 'BoletoApi')
                response = requests.get(
                    url,
                    params=params,
                    headers={'Accept': 'application/vnd.BoletoApi-v1+json'},
                    timeout=self.timeout
                )

                # Log da resposta
                logger.debug(f"Status code: {response.status_code}")
                if response.status_code != 200:
                    logger.debug(f"Response body: {response.text[:500]}")

                # Sucesso
                if response.status_code == 200:
                    return self._processar_resposta_sucesso(response, banco_nome, dados_boleto)

                # Erros que justificam retry (5xx)
                elif 500 <= response.status_code < 600:
                    error_msg = f"Erro do servidor {response.status_code}"
                    logger.warning(f"{error_msg} - Tentativa {tentativa}/{self.max_tentativas}")

                    # Log detalhado do erro 500 para debug
                    logger.error(f"Erro 500 da API BRCobranca. Response body: {response.text[:1000]}")
                    logger.error(f"Dados enviados - Banco: {banco_nome}")
                    logger.error(f"Dados do boleto (primeiros campos): cedente={boleto_data.get('cedente')}, "
                               f"documento_cedente={boleto_data.get('documento_cedente')}, "
                               f"sacado={boleto_data.get('sacado')}, "
                               f"valor={boleto_data.get('valor')}, "
                               f"data_vencimento={boleto_data.get('data_vencimento')}, "
                               f"nosso_numero={boleto_data.get('nosso_numero')}")

                    # Log completo dos dados em formato JSON (apenas na última tentativa)
                    if tentativa == self.max_tentativas:
                        logger.error(f"Dados completos enviados (JSON): {json.dumps(boleto_data, indent=2, default=str)}")

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
        except (ValueError, TypeError):
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
            logger.exception("Erro ao validar data do boleto: %s", e)
            erros.append(f"Erro ao validar data: {e}")

        # Validar numero_documento conforme regras por banco (configuravel)
        numero_documento = dados.get('numero_documento') or dados.get('documento_numero') or ''
        codigo_banco = str(dados.get('codigo_banco') or '')
        if numero_documento:
            # obter padroes do settings (permitir override)
            patterns = getattr(settings, 'BRCOBRANCA_NUMERO_DOCUMENTO_PATTERNS', {})
            maxlens = getattr(settings, 'BRCOBRANCA_NUMERO_DOCUMENTO_MAXLEN', {})

            default_pattern = patterns.get('default', r'^[0-9A-Za-z_\/\-\s]+$')
            pattern = patterns.get(codigo_banco, default_pattern)
            try:
                if not re.match(pattern + r'\Z', numero_documento):
                    erros.append(f"Numero do documento invalido para o banco {codigo_banco}: caracteres nao permitidos")
            except re.error:
                # padrao invalido na configuracao -> usar default seguro
                if not re.match(default_pattern + r'\Z', numero_documento):
                    erros.append("Numero do documento invalido: caracteres nao permitidos")

            maxlen = maxlens.get(codigo_banco) or maxlens.get('default')
            if maxlen:
                try:
                    if len(numero_documento) > int(maxlen):
                        erros.append(f"Numero do documento excede comprimento maximo ({maxlen}) para o banco {codigo_banco}")
                except Exception:
                    pass

        return {
            'valido': len(erros) == 0,
            'erros': erros
        }

    def _obter_dados_boleto(self, banco_nome, dados_boleto):
        """
        Obtem dados do boleto (linha digitavel, codigo de barras, nosso numero formatado)
        via endpoint /api/boleto/data da API customizada Maxwell

        Conforme documentacao: https://github.com/Maxwbh/boleto_cnab_api
        Endpoint: GET /api/boleto/data

        NOTA: Este metodo tenta obter dados adicionais do boleto para exibicao.
        Se falhar, o sistema continuara funcionando normalmente pois o PDF
        gerado ja contem todas as informacoes necessarias.

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

            # Usar endpoint customizado /api/boleto/data
            # Retorna: codigo_barras, linha_digitavel, nosso_numero com DV, agencia_conta_boleto
            response = requests.get(
                f"{self.brcobranca_url}/api/boleto/data",
                params=params,
                headers={'Accept': 'application/vnd.BoletoApi-v1+json'},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                logger.info("Dados do boleto obtidos via /api/boleto/data")
                return {
                    'linha_digitavel': data.get('linha_digitavel', ''),
                    'codigo_barras': data.get('codigo_barras', ''),
                    'nosso_numero_formatado': data.get('nosso_numero', ''),
                    'agencia_conta_boleto': data.get('agencia_conta_boleto', '')
                }
            else:
                logger.debug(f"Endpoint /api/boleto/data retornou {response.status_code}, dados opcionais nao disponiveis")
                return {}

        except Exception as e:
            logger.debug(f"Nao foi possivel obter dados opcionais do boleto: {e}")
            return {}

    def _processar_resposta_sucesso(self, response, banco_nome=None, dados_boleto=None):
        """Processa resposta bem-sucedida da API"""
        try:
            content_type = response.headers.get('content-type', '')

            # Extrair PDF da resposta
            pdf_content = response.content

            if not pdf_content:
                logger.error("PDF vazio na resposta")
                return {
                    'sucesso': False,
                    'erro': 'PDF não foi gerado corretamente'
                }

            logger.info(f"Boleto PDF gerado com sucesso ({len(pdf_content)} bytes)")

            # Obter dados adicionais do boleto (linha digitavel e codigo de barras)
            # via endpoint /api/boleto/data
            linha_digitavel = ''
            codigo_barras = ''

            if banco_nome and dados_boleto:
                logger.info("Obtendo linha digitavel e codigo de barras via /api/boleto/data")
                dados_extras = self._obter_dados_boleto(banco_nome, dados_boleto)
                linha_digitavel = dados_extras.get('linha_digitavel', '')
                codigo_barras = dados_extras.get('codigo_barras', '')

                if linha_digitavel and codigo_barras:
                    logger.info(f"Dados obtidos com sucesso - linha_digitavel: {linha_digitavel[:20]}..., codigo_barras: {codigo_barras[:20]}...")
                else:
                    logger.warning(f"Dados incompletos - linha_digitavel: {'OK' if linha_digitavel else 'VAZIO'}, codigo_barras: {'OK' if codigo_barras else 'VAZIO'}")

            # Capturar nosso_numero retornado pela API
            nosso_numero_api = ''
            if banco_nome and dados_boleto:
                nosso_numero_api = dados_extras.get('nosso_numero_formatado', '')
                if nosso_numero_api:
                    logger.info(f"Nosso numero retornado pela API: {nosso_numero_api}")

            return {
                'sucesso': True,
                'pdf_content': pdf_content,
                'linha_digitavel': linha_digitavel,
                'codigo_barras': codigo_barras,
                'nosso_numero_api': nosso_numero_api,  # Nosso numero gerado pela API
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
        except Exception:
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


# CNABService foi movido para cnab_service.py
# Importar de: from financeiro.services.cnab_service import CNABService
