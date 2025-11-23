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
        '001': {'convenio_obrigatorio': True},
        '033': {'convenio_obrigatorio': True},
        '104': {'emissao': '4', 'convenio_len': 6},
        '341': {'seu_numero': True},
        '748': {'posto_obrigatorio': True, 'byte_idt': '2'},
        '756': {'variacao': '01'},
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

        # Endereco do pagador
        endereco_pagador = ''
        if hasattr(comprador, 'endereco_formatado') and comprador.endereco_formatado:
            endereco_pagador = comprador.endereco_formatado
        elif comprador.logradouro:
            endereco_pagador = f"{comprador.logradouro}, {comprador.numero or 'S/N'}"
            if comprador.complemento:
                endereco_pagador += f" {comprador.complemento}"

        # Carteira
        carteira = conta_bancaria.carteira or self.CARTEIRAS_PADRAO.get(conta_bancaria.banco, '1')

        # Numero do documento
        numero_documento = parcela.gerar_numero_documento()

        # Instrucoes (usando configuracoes do contrato)
        instrucoes = []
        if config_boleto.get('instrucao_1'):
            instrucoes.append(config_boleto['instrucao_1'])
        if config_boleto.get('instrucao_2'):
            instrucoes.append(config_boleto['instrucao_2'])
        if config_boleto.get('instrucao_3'):
            instrucoes.append(config_boleto['instrucao_3'])
        # Adicionar informacoes padrao
        instrucoes.append(f"Parcela {parcela.numero_parcela} de {contrato.numero_parcelas}")
        instrucoes.append(f"Contrato: {contrato.numero_contrato}")
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
            'sacado': comprador.nome,
            'sacado_documento': documento_pagador,
            'sacado_endereco': endereco_pagador[:40] if endereco_pagador else '',
            'bairro': comprador.bairro or '',
            'cep': self._formatar_cep(comprador.cep),
            'cidade': comprador.cidade or '',
            'uf': comprador.estado or '',

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
        elif codigo_banco == '756':
            dados['variacao'] = '01'
            # Nosso numero max 7 digitos
            if dados.get('nosso_numero'):
                dados['nosso_numero'] = str(dados['nosso_numero']).zfill(7)[:7]

        # Adicionar multa se configurada (usando config do contrato)
        valor_multa = config_boleto.get('valor_multa', 0) or 0
        if valor_multa > 0:
            dias_carencia = config_boleto.get('dias_carencia', 0) or 0
            data_multa = parcela.data_vencimento + timedelta(days=dias_carencia + 1)
            dados['data_mora'] = self._formatar_data(data_multa)

            if config_boleto.get('tipo_valor_multa') == 'PERCENTUAL':
                dados['percentual_multa'] = float(valor_multa)
            else:
                dados['valor_multa'] = float(valor_multa)

        # Adicionar juros se configurado (usando config do contrato)
        valor_juros = config_boleto.get('valor_juros', 0) or 0
        if valor_juros > 0:
            if config_boleto.get('tipo_valor_juros') == 'PERCENTUAL':
                dados['percentual_mora'] = float(valor_juros)
            else:
                dados['valor_mora'] = float(valor_juros)

        # Adicionar desconto se configurado (usando config do contrato)
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
                    valor_desc = float(parcela.valor_atual) * float(valor_desconto) / 100
                    dados['valor_desconto'] = valor_desc
                else:
                    dados['valor_desconto'] = float(valor_desconto)

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
                return {
                    'sucesso': True,
                    'nosso_numero': str(nosso_numero),
                    'numero_documento': dados_boleto['numero_documento'],
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
        Chama a API BRCobranca para gerar o boleto.

        Args:
            banco_nome: Nome do banco no formato BRCobranca
            dados_boleto: Dados do boleto

        Returns:
            dict: Resultado com PDF e dados do boleto
        """
        try:
            # Primeiro, obter linha digitavel e codigo de barras
            linha_digitavel = ''
            codigo_barras = ''

            # Obter nosso numero formatado
            try:
                params_nn = {
                    'bank': banco_nome,
                    'data': json.dumps(dados_boleto)
                }
                response_nn = requests.get(
                    f"{self.brcobranca_url}/api/boleto/nosso_numero",
                    params=params_nn,
                    timeout=self.timeout
                )
                if response_nn.status_code == 200:
                    nosso_numero_formatado = response_nn.text.strip().strip('"')
                    logger.info(f"Nosso numero formatado: {nosso_numero_formatado}")
            except Exception as e:
                logger.warning(f"Erro ao obter nosso numero formatado: {e}")

            # Gerar PDF do boleto
            params = {
                'bank': banco_nome,
                'type': 'pdf',
                'data': json.dumps(dados_boleto)
            }

            logger.info(f"Chamando BRCobranca: {self.brcobranca_url}/api/boleto")
            logger.debug(f"Parametros: bank={banco_nome}, data={json.dumps(dados_boleto, indent=2)}")

            response = requests.get(
                f"{self.brcobranca_url}/api/boleto",
                params=params,
                timeout=self.timeout
            )

            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')

                if 'application/pdf' in content_type:
                    # Resposta e o PDF diretamente
                    pdf_content = response.content

                    # Tentar obter linha digitavel separadamente
                    try:
                        linha_resp = self._obter_linha_digitavel(banco_nome, dados_boleto)
                        if linha_resp:
                            linha_digitavel = linha_resp.get('linha_digitavel', '')
                            codigo_barras = linha_resp.get('codigo_barras', '')
                    except Exception as e:
                        logger.warning(f"Erro ao obter linha digitavel: {e}")

                    return {
                        'sucesso': True,
                        'pdf_content': pdf_content,
                        'linha_digitavel': linha_digitavel,
                        'codigo_barras': codigo_barras,
                    }

                elif 'application/json' in content_type:
                    result = response.json()
                    if isinstance(result, dict) and 'error' in result:
                        logger.error(f"Erro da API BRCobranca: {result['error']}")
                        return {
                            'sucesso': False,
                            'erro': result.get('error', 'Erro desconhecido')
                        }
                    return {
                        'sucesso': True,
                        'pdf_content': result.get('pdf'),
                        'linha_digitavel': result.get('linha_digitavel', ''),
                        'codigo_barras': result.get('codigo_barras', ''),
                    }
                else:
                    # Assumir que e PDF
                    return {
                        'sucesso': True,
                        'pdf_content': response.content,
                        'linha_digitavel': linha_digitavel,
                        'codigo_barras': codigo_barras,
                    }

            else:
                error_msg = f"Erro HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', error_msg)
                except:
                    error_msg = response.text or error_msg

                logger.error(f"Erro na API BRCobranca: {error_msg}")
                return {
                    'sucesso': False,
                    'erro': error_msg
                }

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Erro de conexao com BRCobranca: {e}")
            return {
                'sucesso': False,
                'erro': f'Nao foi possivel conectar ao servidor BRCobranca em {self.brcobranca_url}. Verifique se o container Docker esta rodando.'
            }
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout na API BRCobranca: {e}")
            return {
                'sucesso': False,
                'erro': 'Timeout ao gerar boleto. Tente novamente.'
            }
        except Exception as e:
            logger.exception(f"Erro ao chamar API BRCobranca: {e}")
            return {
                'sucesso': False,
                'erro': str(e)
            }

    def _obter_linha_digitavel(self, banco_nome, dados_boleto):
        """
        Obtem a linha digitavel e codigo de barras do boleto.
        """
        try:
            # Alguns endpoints podem retornar isso diretamente
            # Tentar validar o boleto para obter os dados
            params = {
                'bank': banco_nome,
                'data': json.dumps(dados_boleto)
            }
            response = requests.get(
                f"{self.brcobranca_url}/api/boleto/validate",
                params=params,
                timeout=self.timeout
            )
            if response.status_code == 200:
                result = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                return {
                    'linha_digitavel': result.get('linha_digitavel', ''),
                    'codigo_barras': result.get('codigo_barras', ''),
                }
        except Exception as e:
            logger.debug(f"Erro ao obter linha digitavel: {e}")
        return None

    def gerar_boletos_lote(self, parcelas, conta_bancaria):
        """
        Gera boletos para multiplas parcelas usando POST /boleto/multi.

        Args:
            parcelas: QuerySet ou lista de Parcelas
            conta_bancaria: Conta bancaria a ser usada

        Returns:
            list: Lista de resultados
        """
        try:
            banco_nome = self._get_banco_brcobranca(conta_bancaria.banco)
            if not banco_nome:
                return [{
                    'sucesso': False,
                    'erro': f'Banco {conta_bancaria.banco} nao suportado'
                }]

            # Preparar dados de todos os boletos
            boletos_data = []
            nossos_numeros = {}

            for parcela in parcelas:
                dados, nosso_numero = self._montar_dados_boleto(parcela, conta_bancaria)
                dados['bank'] = banco_nome  # Adicionar banco em cada boleto
                boletos_data.append(dados)
                nossos_numeros[parcela.id] = nosso_numero

            # Chamar API para multiplos boletos
            payload = {
                'type': 'pdf',
                'data': boletos_data
            }

            response = requests.post(
                f"{self.brcobranca_url}/api/boleto/multi",
                json=payload,
                timeout=self.timeout * len(parcelas)
            )

            resultados = []
            if response.status_code == 200:
                # O PDF vem como conteudo unico para todos os boletos
                pdf_content = response.content

                for parcela in parcelas:
                    resultados.append({
                        'parcela_id': parcela.id,
                        'parcela': str(parcela),
                        'sucesso': True,
                        'nosso_numero': str(nossos_numeros.get(parcela.id)),
                        'pdf_content': pdf_content,  # PDF combinado
                    })
            else:
                error_msg = response.text
                for parcela in parcelas:
                    resultados.append({
                        'parcela_id': parcela.id,
                        'parcela': str(parcela),
                        'sucesso': False,
                        'erro': error_msg
                    })

            return resultados

        except Exception as e:
            logger.exception(f"Erro ao gerar boletos em lote: {e}")
            return [{
                'sucesso': False,
                'erro': str(e)
            }]

    def verificar_api_disponivel(self):
        """Verifica se a API BRCobranca esta disponivel"""
        try:
            # A API nao tem endpoint de health, tentar uma chamada basica
            response = requests.get(
                f"{self.brcobranca_url}/",
                timeout=5
            )
            return response.status_code in [200, 404]  # 404 e ok, significa que o servidor esta rodando
        except:
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
