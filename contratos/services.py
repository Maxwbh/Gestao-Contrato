"""
Serviços para o módulo de contratos.

Inclui:
- Cache de índices econômicos
- Cálculos de reajuste
- Integração com API do Banco Central
"""
from decimal import Decimal
from datetime import date, timedelta
from typing import Optional, Dict, Any
from django.core.cache import cache
from django.conf import settings
import logging
import requests

logger = logging.getLogger(__name__)

# Tempo de cache em segundos (1 hora)
CACHE_TIMEOUT = 3600


class IndiceEconomicoService:
    """
    Serviço para obtenção e cache de índices econômicos.

    Os índices são buscados da API do Banco Central do Brasil
    e cacheados para evitar requisições desnecessárias.
    """

    # Mapeamento de tipos para séries do BCB
    SERIES_BCB = {
        'IPCA': getattr(settings, 'IPCA_SERIE_ID', '433'),
        'IGP-M': getattr(settings, 'IGPM_SERIE_ID', '189'),
        'SELIC': getattr(settings, 'SELIC_SERIE_ID', '432'),
    }

    @classmethod
    def get_indice_atual(cls, tipo: str) -> Optional[Dict[str, Any]]:
        """
        Obtém o índice mais recente de um determinado tipo.

        Args:
            tipo: Tipo do índice (IPCA, IGP-M, SELIC)

        Returns:
            Dicionário com data e valor do índice, ou None se não encontrado
        """
        cache_key = f'indice_atual_{tipo}'
        resultado = cache.get(cache_key)

        if resultado is not None:
            logger.debug(f"Índice {tipo} obtido do cache")
            return resultado

        # Buscar do banco de dados
        try:
            from contratos.models import IndiceReajuste
            indice = IndiceReajuste.objects.filter(
                tipo=tipo
            ).order_by('-data_referencia').first()

            if indice:
                resultado = {
                    'tipo': indice.tipo,
                    'data_referencia': indice.data_referencia.isoformat(),
                    'valor': float(indice.valor),
                    'valor_acumulado_ano': float(indice.valor_acumulado_ano) if indice.valor_acumulado_ano else None,
                    'valor_acumulado_12_meses': float(indice.valor_acumulado_12_meses) if indice.valor_acumulado_12_meses else None,
                }
                cache.set(cache_key, resultado, CACHE_TIMEOUT)
                logger.info(f"Índice {tipo} cacheado com sucesso")
                return resultado
        except Exception as e:
            logger.error(f"Erro ao buscar índice {tipo}: {e}")

        return None

    @classmethod
    def get_indices_periodo(
        cls,
        tipo: str,
        data_inicio: date,
        data_fim: date
    ) -> list:
        """
        Obtém índices de um período específico.

        Args:
            tipo: Tipo do índice
            data_inicio: Data inicial do período
            data_fim: Data final do período

        Returns:
            Lista de índices no período
        """
        cache_key = f'indices_{tipo}_{data_inicio}_{data_fim}'
        resultado = cache.get(cache_key)

        if resultado is not None:
            return resultado

        try:
            from contratos.models import IndiceReajuste
            indices = IndiceReajuste.objects.filter(
                tipo=tipo,
                data_referencia__gte=data_inicio,
                data_referencia__lte=data_fim
            ).order_by('data_referencia').values(
                'data_referencia', 'valor', 'valor_acumulado_ano'
            )

            resultado = list(indices)
            cache.set(cache_key, resultado, CACHE_TIMEOUT)
            return resultado
        except Exception as e:
            logger.error(f"Erro ao buscar índices do período: {e}")
            return []

    @classmethod
    def buscar_indice_bcb(cls, tipo: str, data_inicio: str, data_fim: str) -> list:
        """
        Busca índices diretamente da API do Banco Central.

        Args:
            tipo: Tipo do índice (IPCA, IGP-M, SELIC)
            data_inicio: Data inicial no formato DD/MM/YYYY
            data_fim: Data final no formato DD/MM/YYYY

        Returns:
            Lista de índices da API
        """
        serie_id = cls.SERIES_BCB.get(tipo)
        if not serie_id:
            logger.error(f"Tipo de índice não suportado: {tipo}")
            return []

        url = settings.BCBAPI_URL.format(serie_id)
        params = {
            'formato': 'json',
            'dataInicial': data_inicio,
            'dataFinal': data_fim
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Erro ao buscar índice do BCB: {e}")
            return []

    @classmethod
    def invalidar_cache(cls, tipo: Optional[str] = None):
        """
        Invalida o cache de índices.

        Args:
            tipo: Tipo específico para invalidar, ou None para todos
        """
        if tipo:
            cache.delete(f'indice_atual_{tipo}')
            logger.info(f"Cache do índice {tipo} invalidado")
        else:
            for t in cls.SERIES_BCB.keys():
                cache.delete(f'indice_atual_{t}')
            logger.info("Cache de todos os índices invalidado")


class ReajusteService:
    """
    Serviço para cálculo de reajustes de contratos.
    """

    @staticmethod
    def calcular_reajuste(
        valor_base: Decimal,
        percentual: Decimal,
        tipo_calculo: str = 'percentual'
    ) -> Decimal:
        """
        Calcula o valor reajustado.

        Args:
            valor_base: Valor original
            percentual: Percentual de reajuste
            tipo_calculo: 'percentual' ou 'fixo'

        Returns:
            Valor reajustado
        """
        if tipo_calculo == 'fixo':
            return valor_base + percentual

        # Cálculo percentual
        return valor_base * (1 + percentual / 100)

    @staticmethod
    def calcular_juros_atraso(
        valor: Decimal,
        dias_atraso: int,
        taxa_mensal: Decimal
    ) -> Decimal:
        """
        Calcula juros de mora por atraso.

        Args:
            valor: Valor da parcela
            dias_atraso: Dias em atraso
            taxa_mensal: Taxa de juros mensal (%)

        Returns:
            Valor dos juros
        """
        if dias_atraso <= 0:
            return Decimal('0.00')

        # Taxa diária = taxa mensal / 30
        taxa_diaria = taxa_mensal / 30
        juros = valor * (taxa_diaria / 100) * dias_atraso

        return juros.quantize(Decimal('0.01'))

    @staticmethod
    def calcular_multa(
        valor: Decimal,
        percentual_multa: Decimal
    ) -> Decimal:
        """
        Calcula multa por atraso.

        Args:
            valor: Valor da parcela
            percentual_multa: Percentual de multa (%)

        Returns:
            Valor da multa
        """
        multa = valor * (percentual_multa / 100)
        return multa.quantize(Decimal('0.01'))

    @staticmethod
    def calcular_valor_total_atraso(
        valor_original: Decimal,
        dias_atraso: int,
        taxa_juros_mensal: Decimal,
        percentual_multa: Decimal
    ) -> Dict[str, Decimal]:
        """
        Calcula valor total de uma parcela em atraso.

        Returns:
            Dicionário com valor_original, juros, multa e total
        """
        juros = ReajusteService.calcular_juros_atraso(
            valor_original, dias_atraso, taxa_juros_mensal
        )
        multa = ReajusteService.calcular_multa(
            valor_original, percentual_multa
        )

        return {
            'valor_original': valor_original,
            'dias_atraso': dias_atraso,
            'juros': juros,
            'multa': multa,
            'total': valor_original + juros + multa
        }
