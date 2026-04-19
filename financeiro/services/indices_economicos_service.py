"""
Servico de Integracao com APIs de Indices Economicos

Item 2.7 do Roadmap: Integracao IBGE API - IPCA, INPC
Item 2.8 do Roadmap: Integracao FGV API - IGP-M, INCC

APIs utilizadas:
- IBGE: https://servicodados.ibge.gov.br/api/docs/
- Banco Central: https://dadosabertos.bcb.gov.br/

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
import logging
import requests
from decimal import Decimal
from datetime import date
from typing import Optional, List, Dict, Tuple
from dateutil.relativedelta import relativedelta

from django.utils import timezone
from django.db import transaction

from contratos.models import IndiceReajuste

logger = logging.getLogger(__name__)


class IBGEService:
    """
    Servico para busca de indices IPCA e INPC na API do IBGE.

    O IBGE disponibiliza dados atraves do SIDRA (Sistema IBGE de
    Recuperacao Automatica).

    Tabelas utilizadas:
    - IPCA: Tabela 1737 (variacao mensal)
    - INPC: Tabela 1736 (variacao mensal)
    """

    BASE_URL = 'https://servicodados.ibge.gov.br/api/v3'

    # Codigos das tabelas SIDRA
    TABELA_IPCA = 1737
    TABELA_INPC = 1736

    def __init__(self):
        self.erros = []
        self.timeout = 30

    def _fazer_requisicao(self, url: str) -> Optional[Dict]:
        """Faz requisicao HTTP com tratamento de erros."""
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            self.erros.append(f'Timeout ao acessar IBGE: {url}')
            logger.exception(f'Timeout IBGE: {url}')
        except requests.RequestException as e:
            self.erros.append(f'Erro ao acessar IBGE: {e}')
            logger.exception(f'Erro IBGE: {e}')
        except ValueError as e:
            self.erros.append(f'Erro ao processar resposta IBGE: {e}')
            logger.exception(f'Erro JSON IBGE: {e}')
        return None

    def buscar_ipca_periodo(
        self,
        data_inicio: date,
        data_fim: date
    ) -> List[Dict]:
        """
        Busca valores do IPCA em um periodo.

        Args:
            data_inicio: Data inicial
            data_fim: Data final

        Returns:
            Lista de dicionarios com mes, ano e valor
        """
        # Formato periodo SIDRA: YYYYMM
        periodo_inicio = data_inicio.strftime('%Y%m')
        periodo_fim = data_fim.strftime('%Y%m')

        # URL da API SIDRA
        # t: tabela, v: variavel (63=variacao mensal), p: periodo, d: casas decimais
        url = (
            f'{self.BASE_URL}/agregados/{self.TABELA_IPCA}/periodos/'
            f'{periodo_inicio}-{periodo_fim}/variaveis/63'
            f'?localidades=N1[all]'
        )

        dados = self._fazer_requisicao(url)
        if not dados:
            return []

        resultados = []
        try:
            # Estrutura SIDRA: lista de variaveis -> serie -> resultados
            for variavel in dados:
                serie = variavel.get('resultados', [{}])[0].get('series', [{}])[0]
                valores = serie.get('serie', {})

                for periodo, valor in valores.items():
                    if valor and valor != '-':
                        ano = int(periodo[:4])
                        mes = int(periodo[4:6])
                        resultados.append({
                            'tipo_indice': 'IPCA',
                            'ano': ano,
                            'mes': mes,
                            'valor': Decimal(valor.replace(',', '.')),
                            'fonte': 'IBGE/SIDRA'
                        })
        except (KeyError, ValueError, TypeError) as e:
            self.erros.append(f'Erro ao processar IPCA: {e}')
            logger.exception(f'Erro processamento IPCA: {e}')

        return sorted(resultados, key=lambda x: (x['ano'], x['mes']))

    def buscar_inpc_periodo(
        self,
        data_inicio: date,
        data_fim: date
    ) -> List[Dict]:
        """
        Busca valores do INPC em um periodo.

        Args:
            data_inicio: Data inicial
            data_fim: Data final

        Returns:
            Lista de dicionarios com mes, ano e valor
        """
        periodo_inicio = data_inicio.strftime('%Y%m')
        periodo_fim = data_fim.strftime('%Y%m')

        url = (
            f'{self.BASE_URL}/agregados/{self.TABELA_INPC}/periodos/'
            f'{periodo_inicio}-{periodo_fim}/variaveis/44'
            f'?localidades=N1[all]'
        )

        dados = self._fazer_requisicao(url)
        if not dados:
            return []

        resultados = []
        try:
            for variavel in dados:
                serie = variavel.get('resultados', [{}])[0].get('series', [{}])[0]
                valores = serie.get('serie', {})

                for periodo, valor in valores.items():
                    if valor and valor != '-':
                        ano = int(periodo[:4])
                        mes = int(periodo[4:6])
                        resultados.append({
                            'tipo_indice': 'INPC',
                            'ano': ano,
                            'mes': mes,
                            'valor': Decimal(valor.replace(',', '.')),
                            'fonte': 'IBGE/SIDRA'
                        })
        except (KeyError, ValueError, TypeError) as e:
            self.erros.append(f'Erro ao processar INPC: {e}')
            logger.exception(f'Erro processamento INPC: {e}')

        return sorted(resultados, key=lambda x: (x['ano'], x['mes']))


class BCBService:
    """
    Servico para busca de indices no Banco Central do Brasil.

    Utiliza a API do Sistema de Series Temporais (SGS).

    Series utilizadas:
    - IGP-M: 189
    - IGP-DI: 190
    - INCC: 192
    - TR: 226
    - SELIC: 4189
    """

    BASE_URL = 'https://api.bcb.gov.br/dados/serie/bcdata.sgs'

    # Codigos das series no SGS
    SERIES = {
        'IGPM': 189,
        'IGPDI': 190,
        'INCC': 192,
        'TR': 226,
        'SELIC': 4189,
    }

    def __init__(self):
        self.erros = []
        self.timeout = 30

    def _fazer_requisicao(self, url: str) -> Optional[List]:
        """Faz requisicao HTTP com tratamento de erros."""
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            self.erros.append(f'Timeout ao acessar BCB: {url}')
            logger.exception(f'Timeout BCB: {url}')
        except requests.RequestException as e:
            self.erros.append(f'Erro ao acessar BCB: {e}')
            logger.exception(f'Erro BCB: {e}')
        except ValueError as e:
            self.erros.append(f'Erro ao processar resposta BCB: {e}')
            logger.exception(f'Erro JSON BCB: {e}')
        return None

    def buscar_indice_periodo(
        self,
        tipo_indice: str,
        data_inicio: date,
        data_fim: date
    ) -> List[Dict]:
        """
        Busca valores de um indice em um periodo.

        Args:
            tipo_indice: Tipo do indice (IGPM, INCC, etc.)
            data_inicio: Data inicial
            data_fim: Data final

        Returns:
            Lista de dicionarios com mes, ano e valor
        """
        codigo_serie = self.SERIES.get(tipo_indice.upper())
        if not codigo_serie:
            self.erros.append(f'Indice {tipo_indice} nao suportado pelo BCB')
            return []

        # Formato de data BCB: dd/mm/yyyy
        data_ini_str = data_inicio.strftime('%d/%m/%Y')
        data_fim_str = data_fim.strftime('%d/%m/%Y')

        url = (
            f'{self.BASE_URL}.{codigo_serie}/dados'
            f'?formato=json&dataInicial={data_ini_str}&dataFinal={data_fim_str}'
        )

        dados = self._fazer_requisicao(url)
        if not dados:
            return []

        resultados = []
        try:
            for item in dados:
                data_str = item.get('data', '')
                valor_str = item.get('valor')

                if data_str and valor_str is not None:
                    # Converter data DD/MM/YYYY
                    partes = data_str.split('/')
                    if len(partes) == 3:
                        _, mes, ano = int(partes[0]), int(partes[1]), int(partes[2])
                        resultados.append({
                            'tipo_indice': tipo_indice.upper(),
                            'ano': ano,
                            'mes': mes,
                            'valor': Decimal(str(valor_str)),
                            'fonte': 'BCB/SGS'
                        })
        except (KeyError, ValueError, TypeError) as e:
            self.erros.append(f'Erro ao processar {tipo_indice}: {e}')
            logger.exception(f'Erro processamento {tipo_indice}: {e}')

        return sorted(resultados, key=lambda x: (x['ano'], x['mes']))

    def buscar_igpm_periodo(self, data_inicio: date, data_fim: date) -> List[Dict]:
        """Busca valores do IGP-M (FGV via BCB)."""
        return self.buscar_indice_periodo('IGPM', data_inicio, data_fim)

    def buscar_incc_periodo(self, data_inicio: date, data_fim: date) -> List[Dict]:
        """Busca valores do INCC (FGV via BCB)."""
        return self.buscar_indice_periodo('INCC', data_inicio, data_fim)

    def buscar_igpdi_periodo(self, data_inicio: date, data_fim: date) -> List[Dict]:
        """Busca valores do IGP-DI (FGV via BCB)."""
        return self.buscar_indice_periodo('IGPDI', data_inicio, data_fim)


class IndicesEconomicosService:
    """
    Servico unificado para busca e importacao de indices economicos.

    Consolida IBGE e BCB em uma interface unica.
    """

    def __init__(self):
        self.ibge = IBGEService()
        self.bcb = BCBService()
        self.erros = []

    def buscar_indice(
        self,
        tipo_indice: str,
        data_inicio: date,
        data_fim: date
    ) -> List[Dict]:
        """
        Busca valores de um indice na API apropriada.

        Args:
            tipo_indice: IPCA, INPC, IGPM, INCC, IGPDI, TR, SELIC
            data_inicio: Data inicial
            data_fim: Data final

        Returns:
            Lista de valores encontrados
        """
        tipo = tipo_indice.upper()

        if tipo == 'IPCA':
            return self.ibge.buscar_ipca_periodo(data_inicio, data_fim)
        elif tipo == 'INPC':
            return self.ibge.buscar_inpc_periodo(data_inicio, data_fim)
        elif tipo in self.bcb.SERIES:
            return self.bcb.buscar_indice_periodo(tipo, data_inicio, data_fim)
        else:
            self.erros.append(f'Indice {tipo_indice} nao suportado')
            return []

    @transaction.atomic
    def importar_indices(
        self,
        tipo_indice: str,
        data_inicio: date,
        data_fim: date
    ) -> Dict:
        """
        Busca e importa indices para o banco de dados.

        Args:
            tipo_indice: Tipo do indice
            data_inicio: Data inicial
            data_fim: Data final

        Returns:
            Resumo da importacao
        """
        resultados = self.buscar_indice(tipo_indice, data_inicio, data_fim)

        criados = 0
        atualizados = 0
        erros_import = 0

        for item in resultados:
            try:
                indice, created = IndiceReajuste.objects.update_or_create(
                    tipo_indice=item['tipo_indice'],
                    ano=item['ano'],
                    mes=item['mes'],
                    defaults={
                        'valor': item['valor'],
                        'fonte': item['fonte'],
                        'data_importacao': timezone.now()
                    }
                )
                if created:
                    criados += 1
                else:
                    atualizados += 1
            except Exception as e:
                erros_import += 1
                self.erros.append(f"Erro ao importar {item}: {e}")
                logger.exception("Erro importacao indice: %s", e)

        return {
            'sucesso': erros_import == 0,
            'tipo_indice': tipo_indice,
            'periodo': f'{data_inicio} a {data_fim}',
            'total_encontrados': len(resultados),
            'criados': criados,
            'atualizados': atualizados,
            'erros': erros_import,
            'mensagens_erro': self.erros + self.ibge.erros + self.bcb.erros
        }

    def importar_todos_indices(
        self,
        data_inicio: date,
        data_fim: date,
        tipos: Optional[List[str]] = None
    ) -> Dict:
        """
        Importa todos os tipos de indices suportados.

        Args:
            data_inicio: Data inicial
            data_fim: Data final
            tipos: Lista de tipos a importar (default: todos)

        Returns:
            Resumo consolidado
        """
        if tipos is None:
            tipos = ['IPCA', 'INPC', 'IGPM', 'INCC', 'IGPDI']

        resultados = {}
        total_criados = 0
        total_atualizados = 0

        for tipo in tipos:
            resultado = self.importar_indices(tipo, data_inicio, data_fim)
            resultados[tipo] = resultado
            total_criados += resultado['criados']
            total_atualizados += resultado['atualizados']

        return {
            'sucesso': all(r['sucesso'] for r in resultados.values()),
            'periodo': f'{data_inicio} a {data_fim}',
            'total_criados': total_criados,
            'total_atualizados': total_atualizados,
            'por_indice': resultados
        }

    def verificar_indices_faltantes(
        self,
        tipo_indice: str,
        data_inicio: date,
        data_fim: date
    ) -> Tuple[bool, List[str]]:
        """
        Verifica quais meses estao faltando no banco de dados.

        Args:
            tipo_indice: Tipo do indice
            data_inicio: Data inicial
            data_fim: Data final

        Returns:
            Tuple (completo, lista_meses_faltantes)
        """
        meses_faltantes = []
        data_atual = data_inicio.replace(day=1)

        while data_atual <= data_fim:
            existe = IndiceReajuste.objects.filter(
                tipo_indice=tipo_indice.upper(),
                ano=data_atual.year,
                mes=data_atual.month
            ).exists()

            if not existe:
                meses_faltantes.append(f"{data_atual.month:02d}/{data_atual.year}")

            data_atual += relativedelta(months=1)

        return len(meses_faltantes) == 0, meses_faltantes
