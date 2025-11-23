"""
Tarefas assíncronas para o app Financeiro (Celery)

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
import requests
from datetime import datetime, timedelta
import logging

from contratos.models import Contrato, TipoCorrecao
from .models import Reajuste

logger = logging.getLogger(__name__)


@shared_task
def processar_reajustes_pendentes():
    """
    Tarefa agendada para processar reajustes pendentes de todos os contratos
    Executa diariamente verificando contratos que precisam de reajuste
    """
    logger.info("Iniciando processamento de reajustes pendentes...")

    contratos_processados = 0
    contratos_reajustados = 0

    # Buscar contratos ativos que precisam de reajuste
    contratos = Contrato.objects.filter(status='ATIVO')

    for contrato in contratos:
        contratos_processados += 1

        if contrato.verificar_reajuste_necessario():
            try:
                aplicar_reajuste_automatico(contrato.id)
                contratos_reajustados += 1
            except Exception as e:
                logger.error(f"Erro ao processar reajuste do contrato {contrato.numero_contrato}: {str(e)}")

    logger.info(f"Processamento concluído. {contratos_processados} contratos processados, {contratos_reajustados} reajustados.")

    return {
        'processados': contratos_processados,
        'reajustados': contratos_reajustados
    }


@shared_task
def aplicar_reajuste_automatico(contrato_id):
    """
    Aplica reajuste automático em um contrato específico
    Busca o índice econômico correspondente e aplica nas parcelas não pagas
    """
    try:
        contrato = Contrato.objects.get(id=contrato_id)

        if contrato.tipo_correcao == TipoCorrecao.FIXO:
            logger.info(f"Contrato {contrato.numero_contrato} com correção fixa. Ignorando reajuste.")
            return False

        # Obter o percentual do índice
        percentual = obter_percentual_indice(contrato.tipo_correcao)

        if percentual is None:
            logger.error(f"Não foi possível obter o índice {contrato.tipo_correcao} para o contrato {contrato.numero_contrato}")
            return False

        # Determinar quais parcelas devem ser reajustadas
        # Reajusta apenas parcelas não pagas
        parcelas_nao_pagas = contrato.parcelas.filter(pago=False).order_by('numero_parcela')

        if not parcelas_nao_pagas.exists():
            logger.info(f"Contrato {contrato.numero_contrato} não possui parcelas pendentes para reajustar.")
            return False

        parcela_inicial = parcelas_nao_pagas.first().numero_parcela
        parcela_final = parcelas_nao_pagas.last().numero_parcela

        # Criar registro de reajuste
        reajuste = Reajuste.objects.create(
            contrato=contrato,
            data_reajuste=timezone.now().date(),
            indice_tipo=contrato.tipo_correcao,
            percentual=percentual,
            parcela_inicial=parcela_inicial,
            parcela_final=parcela_final,
            aplicado_manual=False,
            observacoes=f'Reajuste automático aplicado em {timezone.now().date()}'
        )

        # Aplicar o reajuste
        reajuste.aplicar_reajuste()

        logger.info(f"Reajuste de {percentual}% aplicado ao contrato {contrato.numero_contrato}")

        return True

    except Contrato.DoesNotExist:
        logger.error(f"Contrato {contrato_id} não encontrado.")
        return False
    except Exception as e:
        logger.error(f"Erro ao aplicar reajuste automático no contrato {contrato_id}: {str(e)}")
        return False


def obter_percentual_indice(tipo_indice):
    """
    Busca o percentual do índice econômico nos últimos 12 meses
    Utiliza a API do Banco Central do Brasil
    """
    try:
        # Mapear tipo de índice para código da série do BCB
        series_bcb = {
            TipoCorrecao.IPCA: settings.IPCA_SERIE_ID,
            TipoCorrecao.IGPM: settings.IGPM_SERIE_ID,
            TipoCorrecao.SELIC: settings.SELIC_SERIE_ID,
        }

        serie_id = series_bcb.get(tipo_indice)
        if not serie_id:
            logger.error(f"Tipo de índice não reconhecido: {tipo_indice}")
            return None

        # Calcular datas (últimos 12 meses)
        data_fim = timezone.now().date()
        data_inicio = data_fim - timedelta(days=365)

        # Formatar datas para a API do BCB (dd/MM/yyyy)
        data_inicio_fmt = data_inicio.strftime('%d/%m/%Y')
        data_fim_fmt = data_fim.strftime('%d/%m/%Y')

        # Fazer requisição à API do BCB
        url = settings.BCBAPI_URL.format(serie_id)
        params = {
            'formato': 'json',
            'dataInicial': data_inicio_fmt,
            'dataFinal': data_fim_fmt
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        dados = response.json()

        if not dados:
            logger.warning(f"Nenhum dado retornado para o índice {tipo_indice}")
            return None

        # Calcular o acumulado dos últimos 12 meses
        # Para IPCA e IGP-M, somar os valores mensais
        # Para SELIC, calcular o composto
        if tipo_indice in [TipoCorrecao.IPCA, TipoCorrecao.IGPM]:
            # Somar os últimos 12 valores
            valores = [Decimal(str(item['valor'])) for item in dados[-12:]]
            percentual_acumulado = sum(valores)
        else:  # SELIC
            # Calcular juros compostos
            valores = [Decimal(str(item['valor'])) for item in dados[-12:]]
            fator = Decimal('1.0')
            for valor in valores:
                fator *= (1 + valor / 100)
            percentual_acumulado = (fator - 1) * 100

        return percentual_acumulado

    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao buscar dados do índice {tipo_indice}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao processar índice {tipo_indice}: {str(e)}")
        return None


@shared_task
def atualizar_juros_multa_parcelas_vencidas():
    """
    Atualiza juros e multa de todas as parcelas vencidas e não pagas
    """
    from .models import Parcela

    logger.info("Iniciando atualização de juros e multa de parcelas vencidas...")

    parcelas_vencidas = Parcela.objects.filter(
        pago=False,
        data_vencimento__lt=timezone.now().date()
    )

    count = 0
    for parcela in parcelas_vencidas:
        parcela.atualizar_juros_multa()
        count += 1

    logger.info(f"Atualização concluída. {count} parcelas atualizadas.")

    return count
