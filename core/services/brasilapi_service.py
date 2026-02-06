"""
Servico de integracao com BrasilAPI

Fornece consultas de:
- CEP (endereco completo)
- CNPJ (dados da empresa)

Documentacao: https://brasilapi.com.br/docs

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
import requests
import logging
import re
from typing import Optional, Dict, Any
from django.core.cache import cache

logger = logging.getLogger(__name__)

# URLs da API
BRASILAPI_CEP_URL = "https://brasilapi.com.br/api/cep/v2/{cep}"
BRASILAPI_CNPJ_URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"

# Tempo de cache em segundos
CACHE_CEP_TIMEOUT = 60 * 60 * 24 * 30  # 30 dias (CEPs raramente mudam)
CACHE_CNPJ_TIMEOUT = 60 * 60 * 24  # 24 horas (dados podem mudar)


class BrasilAPIService:
    """
    Servico para consultas na BrasilAPI.

    Exemplos de uso:

    # Buscar CEP
    service = BrasilAPIService()
    dados = service.buscar_cep('01310100')
    # Retorna: {
    #     'cep': '01310-100',
    #     'logradouro': 'Avenida Paulista',
    #     'complemento': 'de 1047 a 1865 - lado ímpar',
    #     'bairro': 'Bela Vista',
    #     'cidade': 'São Paulo',
    #     'estado': 'SP',
    #     'ibge': '3550308',
    #     'ddd': '11'
    # }

    # Buscar CNPJ
    dados = service.buscar_cnpj('00000000000191')
    # Retorna: {
    #     'cnpj': '00.000.000/0001-91',
    #     'razao_social': 'BANCO DO BRASIL SA',
    #     'nome_fantasia': 'DIRECAO GERAL',
    #     'situacao_cadastral': 'ATIVA',
    #     'data_situacao_cadastral': '2005-11-03',
    #     'natureza_juridica': 'Sociedade de Economia Mista',
    #     'capital_social': 120000000000,
    #     'porte': 'DEMAIS',
    #     'email': 'example@bb.com.br',
    #     'telefone': '6134939002',
    #     'cep': '70040-912',
    #     'logradouro': 'SAUN QUADRA 5 LOTE B',
    #     'numero': 'S/N',
    #     'complemento': 'ANDAR 1 A 16 SALA 101 A 1601 ANDAR 1 A 16',
    #     'bairro': 'ASA NORTE',
    #     'cidade': 'BRASILIA',
    #     'estado': 'DF',
    #     ...
    # }
    """

    def __init__(self, timeout: int = 10):
        """
        Inicializa o servico.

        Args:
            timeout: Timeout em segundos para requisicoes HTTP
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'GestaoContrato/1.0',
            'Accept': 'application/json'
        })

    def _limpar_numeros(self, valor: str) -> str:
        """Remove caracteres nao numericos de uma string."""
        if not valor:
            return ''
        return re.sub(r'\D', '', str(valor))

    def _formatar_cep(self, cep: str) -> str:
        """Formata CEP para exibicao (99999-999)."""
        cep_limpo = self._limpar_numeros(cep)
        if len(cep_limpo) == 8:
            return f"{cep_limpo[:5]}-{cep_limpo[5:]}"
        return cep

    def _formatar_cnpj(self, cnpj: str) -> str:
        """Formata CNPJ para exibicao (99.999.999/9999-99)."""
        cnpj_limpo = self._limpar_numeros(cnpj)
        if len(cnpj_limpo) == 14:
            return f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:]}"
        return cnpj

    def buscar_cep(self, cep: str, usar_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Busca endereco pelo CEP na BrasilAPI.

        Args:
            cep: CEP a ser consultado (com ou sem formatacao)
            usar_cache: Se True, usa cache para evitar requisicoes repetidas

        Returns:
            Dict com dados do endereco ou None se nao encontrado
        """
        cep_limpo = self._limpar_numeros(cep)

        if len(cep_limpo) != 8:
            logger.warning(f"CEP invalido: {cep}")
            return None

        # Verificar cache
        cache_key = f"brasilapi_cep_{cep_limpo}"
        if usar_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug(f"CEP {cep_limpo} encontrado no cache")
                return cached

        try:
            url = BRASILAPI_CEP_URL.format(cep=cep_limpo)
            response = self.session.get(url, timeout=self.timeout)

            if response.status_code == 200:
                dados = response.json()

                # Normalizar resposta
                resultado = {
                    'sucesso': True,
                    'cep': self._formatar_cep(dados.get('cep', cep_limpo)),
                    'logradouro': dados.get('street', ''),
                    'complemento': dados.get('complement', ''),
                    'bairro': dados.get('neighborhood', ''),
                    'cidade': dados.get('city', ''),
                    'estado': dados.get('state', ''),
                    'ibge': dados.get('cep', {}).get('ibge', '') if isinstance(dados.get('cep'), dict) else '',
                    'ddd': dados.get('ddd', ''),
                    'fonte': 'BrasilAPI'
                }

                # Salvar no cache
                if usar_cache:
                    cache.set(cache_key, resultado, CACHE_CEP_TIMEOUT)

                logger.info(f"CEP {cep_limpo} encontrado: {resultado['cidade']}/{resultado['estado']}")
                return resultado

            elif response.status_code == 404:
                logger.info(f"CEP {cep_limpo} nao encontrado")
                return {'sucesso': False, 'erro': 'CEP nao encontrado'}

            else:
                logger.error(f"Erro na API BrasilAPI: {response.status_code}")
                return {'sucesso': False, 'erro': f'Erro na API: {response.status_code}'}

        except requests.Timeout:
            logger.error(f"Timeout ao buscar CEP {cep_limpo}")
            return {'sucesso': False, 'erro': 'Tempo limite excedido'}

        except requests.RequestException as e:
            logger.exception(f"Erro ao buscar CEP {cep_limpo}: {e}")
            return {'sucesso': False, 'erro': str(e)}

    def buscar_cnpj(self, cnpj: str, usar_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Busca dados da empresa pelo CNPJ na BrasilAPI.

        Args:
            cnpj: CNPJ a ser consultado (com ou sem formatacao)
            usar_cache: Se True, usa cache para evitar requisicoes repetidas

        Returns:
            Dict com dados da empresa ou None se nao encontrado
        """
        cnpj_limpo = self._limpar_numeros(cnpj)

        if len(cnpj_limpo) != 14:
            logger.warning(f"CNPJ invalido: {cnpj}")
            return None

        # Verificar cache
        cache_key = f"brasilapi_cnpj_{cnpj_limpo}"
        if usar_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug(f"CNPJ {cnpj_limpo} encontrado no cache")
                return cached

        try:
            url = BRASILAPI_CNPJ_URL.format(cnpj=cnpj_limpo)
            response = self.session.get(url, timeout=self.timeout)

            if response.status_code == 200:
                dados = response.json()

                # Normalizar resposta
                resultado = {
                    'sucesso': True,
                    'cnpj': self._formatar_cnpj(dados.get('cnpj', cnpj_limpo)),
                    'razao_social': dados.get('razao_social', ''),
                    'nome_fantasia': dados.get('nome_fantasia', ''),
                    'situacao_cadastral': dados.get('descricao_situacao_cadastral', ''),
                    'data_situacao_cadastral': dados.get('data_situacao_cadastral', ''),
                    'natureza_juridica': dados.get('descricao_natureza_juridica', ''),
                    'capital_social': dados.get('capital_social', 0),
                    'porte': dados.get('porte', ''),

                    # Contato
                    'email': dados.get('email', ''),
                    'telefone': dados.get('ddd_telefone_1', ''),
                    'telefone_2': dados.get('ddd_telefone_2', ''),

                    # Endereco
                    'cep': self._formatar_cep(dados.get('cep', '')),
                    'logradouro': dados.get('descricao_tipo_de_logradouro', '') + ' ' + dados.get('logradouro', ''),
                    'numero': dados.get('numero', ''),
                    'complemento': dados.get('complemento', ''),
                    'bairro': dados.get('bairro', ''),
                    'cidade': dados.get('municipio', ''),
                    'estado': dados.get('uf', ''),

                    # Atividades
                    'cnae_principal': {
                        'codigo': dados.get('cnae_fiscal', ''),
                        'descricao': dados.get('cnae_fiscal_descricao', '')
                    },
                    'cnaes_secundarios': dados.get('cnaes_secundarios', []),

                    # Socios
                    'socios': dados.get('qsa', []),

                    # Datas
                    'data_inicio_atividade': dados.get('data_inicio_atividade', ''),

                    'fonte': 'BrasilAPI'
                }

                # Salvar no cache
                if usar_cache:
                    cache.set(cache_key, resultado, CACHE_CNPJ_TIMEOUT)

                logger.info(f"CNPJ {cnpj_limpo} encontrado: {resultado['razao_social']}")
                return resultado

            elif response.status_code == 404:
                logger.info(f"CNPJ {cnpj_limpo} nao encontrado")
                return {'sucesso': False, 'erro': 'CNPJ nao encontrado'}

            elif response.status_code == 400:
                logger.info(f"CNPJ {cnpj_limpo} invalido")
                return {'sucesso': False, 'erro': 'CNPJ invalido'}

            else:
                logger.error(f"Erro na API BrasilAPI: {response.status_code}")
                return {'sucesso': False, 'erro': f'Erro na API: {response.status_code}'}

        except requests.Timeout:
            logger.error(f"Timeout ao buscar CNPJ {cnpj_limpo}")
            return {'sucesso': False, 'erro': 'Tempo limite excedido'}

        except requests.RequestException as e:
            logger.exception(f"Erro ao buscar CNPJ {cnpj_limpo}: {e}")
            return {'sucesso': False, 'erro': str(e)}


# Instancia global para uso simplificado
_service = None

def get_service() -> BrasilAPIService:
    """Retorna instancia singleton do servico."""
    global _service
    if _service is None:
        _service = BrasilAPIService()
    return _service


def buscar_cep(cep: str) -> Optional[Dict[str, Any]]:
    """Funcao de conveniencia para buscar CEP."""
    return get_service().buscar_cep(cep)


def buscar_cnpj(cnpj: str) -> Optional[Dict[str, Any]]:
    """Funcao de conveniencia para buscar CNPJ."""
    return get_service().buscar_cnpj(cnpj)
