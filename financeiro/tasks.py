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


# =============================================================================
# NOVAS TASKS - AUTOMAÇÃO COMPLETA
# =============================================================================

@shared_task
def buscar_indices_economicos():
    """
    Busca índices econômicos das APIs oficiais e armazena no banco.
    Executar diariamente.

    Fontes:
    - BCB (Banco Central): TR, SELIC
    - IBGE: IPCA, INPC
    - FGV: IGPM, IGPDI, INCC
    """
    from contratos.models import IndiceReajuste
    from .services.reajuste_service import IndiceEconomicoService

    logger.info("Iniciando busca de índices econômicos...")

    service = IndiceEconomicoService()
    resultados = {
        'sucesso': [],
        'erro': []
    }

    # Período: últimos 3 meses (para garantir dados recentes)
    hoje = timezone.now().date()
    data_inicio = hoje - timedelta(days=90)

    # Séries do BCB
    series_bcb = {
        'TR': 226,      # Taxa Referencial
        'SELIC': 4189,  # Meta SELIC
    }

    for tipo, codigo in series_bcb.items():
        try:
            dados = service.buscar_indice_bcb(codigo, data_inicio, hoje)
            if dados:
                resultado = service.importar_indices_periodo(tipo, dados)
                resultados['sucesso'].append({
                    'tipo': tipo,
                    'importados': resultado['criados'] + resultado['atualizados']
                })
                logger.info(f"Índice {tipo}: {resultado['criados']} novos, {resultado['atualizados']} atualizados")
            else:
                resultados['erro'].append({'tipo': tipo, 'erro': 'Nenhum dado retornado'})
        except Exception as e:
            logger.error(f"Erro ao buscar índice {tipo}: {e}")
            resultados['erro'].append({'tipo': tipo, 'erro': str(e)})

    logger.info(f"Busca de índices concluída. Sucesso: {len(resultados['sucesso'])}, Erros: {len(resultados['erro'])}")

    return resultados


@shared_task
def verificar_alertas_reajuste():
    """
    Verifica contratos com reajuste pendente e envia alertas.
    Executar diariamente.

    Envia alertas quando:
    - Faltam 30 dias para o reajuste
    - Faltam 7 dias para o reajuste (urgente)
    - Boletos estão bloqueados por reajuste pendente
    """
    from .services.reajuste_service import ReajusteService

    logger.info("Verificando alertas de reajuste...")

    service = ReajusteService()
    contratos_pendentes = service.listar_contratos_reajuste_pendente(dias_antecedencia=30)

    alertas_enviados = 0
    contratos_urgentes = []
    contratos_bloqueados = []

    for item in contratos_pendentes:
        contrato = item['contrato']

        # Classificar por urgência
        if item['urgente']:
            contratos_urgentes.append(contrato)
        if item['bloqueado']:
            contratos_bloqueados.append(contrato)

        # Enviar notificação
        try:
            enviar_alerta_reajuste.delay(
                contrato_id=contrato.id,
                dias_restantes=item['dias_restantes'],
                urgente=item['urgente'],
                bloqueado=item['bloqueado']
            )
            alertas_enviados += 1
        except Exception as e:
            logger.error(f"Erro ao enviar alerta para contrato {contrato.numero_contrato}: {e}")

    resultado = {
        'total_pendentes': len(contratos_pendentes),
        'urgentes': len(contratos_urgentes),
        'bloqueados': len(contratos_bloqueados),
        'alertas_enviados': alertas_enviados
    }

    logger.info(f"Alertas de reajuste: {resultado}")

    return resultado


@shared_task
def enviar_alerta_reajuste(contrato_id, dias_restantes, urgente=False, bloqueado=False):
    """
    Envia alerta de reajuste pendente para administradores.
    """
    from django.core.mail import send_mail
    from django.conf import settings

    try:
        contrato = Contrato.objects.select_related('imobiliaria').get(id=contrato_id)

        assunto = f"{'[URGENTE] ' if urgente else ''}Reajuste Pendente - Contrato {contrato.numero_contrato}"

        if bloqueado:
            assunto = f"[BLOQUEADO] {assunto}"

        mensagem = f"""
Contrato: {contrato.numero_contrato}
Imobiliária: {contrato.imobiliaria.nome}
Comprador: {contrato.comprador.nome}

Status: {'URGENTE - ' if urgente else ''}{dias_restantes} dias para o reajuste
Boletos: {'BLOQUEADOS - Reajuste necessário para liberar' if bloqueado else 'Liberados'}

Índice configurado: {contrato.tipo_correcao}
Próximo reajuste: {contrato.data_proximo_reajuste}

Por favor, aplique o reajuste para liberar a geração de boletos.
        """

        # Buscar emails dos administradores da imobiliária
        emails_destino = []
        if hasattr(contrato.imobiliaria, 'email') and contrato.imobiliaria.email:
            emails_destino.append(contrato.imobiliaria.email)

        if emails_destino and hasattr(settings, 'DEFAULT_FROM_EMAIL'):
            send_mail(
                assunto,
                mensagem,
                settings.DEFAULT_FROM_EMAIL,
                emails_destino,
                fail_silently=True
            )
            logger.info(f"Alerta de reajuste enviado para contrato {contrato.numero_contrato}")
            return True

    except Exception as e:
        logger.error(f"Erro ao enviar alerta de reajuste: {e}")
        return False


@shared_task
def gerar_boletos_automaticos():
    """
    Gera boletos automaticamente para parcelas do próximo mês.
    Executar mensalmente (ex: dia 25 de cada mês).

    Respeita a regra de bloqueio por reajuste.
    """
    from .models import Parcela, StatusBoleto
    from contratos.models import StatusContrato

    logger.info("Iniciando geração automática de boletos...")

    # Calcular período: parcelas com vencimento no próximo mês
    hoje = timezone.now().date()
    primeiro_dia_proximo_mes = (hoje.replace(day=1) + timedelta(days=32)).replace(day=1)
    ultimo_dia_proximo_mes = (primeiro_dia_proximo_mes + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    # Buscar parcelas elegíveis
    parcelas = Parcela.objects.filter(
        contrato__status=StatusContrato.ATIVO,
        data_vencimento__gte=primeiro_dia_proximo_mes,
        data_vencimento__lte=ultimo_dia_proximo_mes,
        pago=False,
        status_boleto=StatusBoleto.NAO_GERADO
    ).select_related('contrato', 'contrato__imobiliaria')

    resultados = {
        'total': parcelas.count(),
        'gerados': 0,
        'bloqueados': 0,
        'erros': 0,
        'detalhes': []
    }

    for parcela in parcelas:
        contrato = parcela.contrato

        # Verificar bloqueio de reajuste
        pode_gerar, motivo = contrato.pode_gerar_boleto(parcela.numero_parcela)

        if not pode_gerar:
            resultados['bloqueados'] += 1
            resultados['detalhes'].append({
                'parcela': f"{contrato.numero_contrato}/{parcela.numero_parcela}",
                'status': 'bloqueado',
                'motivo': motivo
            })
            continue

        # Gerar boleto
        try:
            resultado = parcela.gerar_boleto(enviar_email=True)
            if resultado and resultado.get('sucesso'):
                resultados['gerados'] += 1
                resultados['detalhes'].append({
                    'parcela': f"{contrato.numero_contrato}/{parcela.numero_parcela}",
                    'status': 'gerado',
                    'nosso_numero': resultado.get('nosso_numero')
                })
            else:
                resultados['erros'] += 1
                resultados['detalhes'].append({
                    'parcela': f"{contrato.numero_contrato}/{parcela.numero_parcela}",
                    'status': 'erro',
                    'motivo': resultado.get('erro', 'Erro desconhecido') if resultado else 'Sem resposta'
                })
        except Exception as e:
            resultados['erros'] += 1
            resultados['detalhes'].append({
                'parcela': f"{contrato.numero_contrato}/{parcela.numero_parcela}",
                'status': 'erro',
                'motivo': str(e)
            })
            logger.error(f"Erro ao gerar boleto da parcela {parcela.id}: {e}")

    logger.info(
        f"Geração automática concluída: {resultados['gerados']} gerados, "
        f"{resultados['bloqueados']} bloqueados, {resultados['erros']} erros"
    )

    return resultados


@shared_task
def enviar_lembretes_vencimento():
    """
    Envia lembretes de vencimento para compradores.
    Executar diariamente.

    Envia lembretes para parcelas vencendo em:
    - 7 dias
    - 3 dias
    - 1 dia (amanhã)
    """
    from .models import Parcela

    logger.info("Enviando lembretes de vencimento...")

    hoje = timezone.now().date()
    lembretes_enviados = 0

    # Configurar dias de antecedência
    dias_lembrete = [7, 3, 1]

    for dias in dias_lembrete:
        data_vencimento = hoje + timedelta(days=dias)

        parcelas = Parcela.objects.filter(
            pago=False,
            data_vencimento=data_vencimento
        ).select_related('contrato', 'contrato__comprador')

        for parcela in parcelas:
            try:
                enviar_lembrete_parcela.delay(parcela.id, dias)
                lembretes_enviados += 1
            except Exception as e:
                logger.error(f"Erro ao agendar lembrete para parcela {parcela.id}: {e}")

    logger.info(f"Lembretes agendados: {lembretes_enviados}")

    return lembretes_enviados


@shared_task
def enviar_lembrete_parcela(parcela_id, dias_para_vencimento):
    """
    Envia lembrete de vencimento para uma parcela específica.
    """
    from .models import Parcela
    from django.core.mail import send_mail
    from django.conf import settings

    try:
        parcela = Parcela.objects.select_related(
            'contrato', 'contrato__comprador'
        ).get(id=parcela_id)

        comprador = parcela.contrato.comprador

        if not comprador.email:
            logger.warning(f"Comprador {comprador.nome} sem email cadastrado")
            return False

        if dias_para_vencimento == 1:
            titulo = "AMANHÃ"
        else:
            titulo = f"em {dias_para_vencimento} dias"

        assunto = f"Lembrete: Parcela vence {titulo} - Contrato {parcela.contrato.numero_contrato}"

        mensagem = f"""
Olá {comprador.nome},

Este é um lembrete de que a parcela {parcela.numero_parcela}/{parcela.contrato.numero_parcelas}
do contrato {parcela.contrato.numero_contrato} vence {titulo}.

Detalhes:
- Valor: R$ {parcela.valor_atual:,.2f}
- Vencimento: {parcela.data_vencimento.strftime('%d/%m/%Y')}

{'Seu boleto já está disponível no portal.' if parcela.tem_boleto else 'Acesse o portal para gerar seu boleto.'}

Atenciosamente,
{parcela.contrato.imobiliaria.nome}
        """

        if hasattr(settings, 'DEFAULT_FROM_EMAIL'):
            send_mail(
                assunto,
                mensagem,
                settings.DEFAULT_FROM_EMAIL,
                [comprador.email],
                fail_silently=True
            )
            logger.info(f"Lembrete enviado para parcela {parcela_id}")
            return True

    except Parcela.DoesNotExist:
        logger.error(f"Parcela {parcela_id} não encontrada")
    except Exception as e:
        logger.error(f"Erro ao enviar lembrete: {e}")

    return False


@shared_task
def processar_arquivos_retorno_pendentes():
    """
    Processa arquivos de retorno CNAB pendentes.
    Executar diariamente.
    """
    from .models import ArquivoRetorno, StatusArquivoRetorno
    from .services.cnab_service import CNABService

    logger.info("Processando arquivos de retorno pendentes...")

    arquivos = ArquivoRetorno.objects.filter(
        status=StatusArquivoRetorno.PENDENTE
    )

    processados = 0
    erros = 0

    for arquivo in arquivos:
        try:
            service = CNABService()
            resultado = service.processar_retorno(arquivo)

            if resultado.get('sucesso'):
                processados += 1
            else:
                erros += 1
                logger.error(f"Erro ao processar retorno {arquivo.id}: {resultado.get('erro')}")

        except Exception as e:
            erros += 1
            logger.error(f"Erro ao processar arquivo de retorno {arquivo.id}: {e}")

    logger.info(f"Retornos processados: {processados}, Erros: {erros}")

    return {'processados': processados, 'erros': erros}


@shared_task
def limpar_boletos_vencidos():
    """
    Atualiza status de boletos vencidos.
    Executar diariamente.
    """
    from .models import Parcela, StatusBoleto

    hoje = timezone.now().date()

    # Atualizar boletos vencidos
    parcelas_vencidas = Parcela.objects.filter(
        pago=False,
        data_vencimento__lt=hoje,
        status_boleto__in=[StatusBoleto.GERADO, StatusBoleto.REGISTRADO]
    )

    count = parcelas_vencidas.update(status_boleto=StatusBoleto.VENCIDO)

    logger.info(f"Status de {count} boletos atualizados para VENCIDO")

    return count


@shared_task
def gerar_relatorio_diario():
    """
    Gera relatório diário consolidado.
    Executar diariamente (final do dia).
    """
    from django.db.models import Sum, Count
    from .models import Parcela
    from contratos.models import Contrato, StatusContrato

    hoje = timezone.now().date()
    ontem = hoje - timedelta(days=1)

    # Estatísticas de pagamentos do dia
    pagamentos_dia = Parcela.objects.filter(
        pago=True,
        data_pagamento=ontem
    ).aggregate(
        total=Count('id'),
        valor=Sum('valor_pago')
    )

    # Boletos gerados no dia
    boletos_dia = Parcela.objects.filter(
        data_geracao_boleto__date=ontem
    ).count()

    # Parcelas vencendo hoje
    vencendo_hoje = Parcela.objects.filter(
        pago=False,
        data_vencimento=hoje
    ).aggregate(
        total=Count('id'),
        valor=Sum('valor_atual')
    )

    # Parcelas vencidas
    vencidas = Parcela.objects.filter(
        pago=False,
        data_vencimento__lt=hoje
    ).aggregate(
        total=Count('id'),
        valor=Sum('valor_atual')
    )

    # Contratos ativos
    contratos_ativos = Contrato.objects.filter(
        status=StatusContrato.ATIVO
    ).count()

    relatorio = {
        'data': str(ontem),
        'pagamentos': {
            'quantidade': pagamentos_dia['total'] or 0,
            'valor': float(pagamentos_dia['valor'] or 0)
        },
        'boletos_gerados': boletos_dia,
        'vencendo_hoje': {
            'quantidade': vencendo_hoje['total'] or 0,
            'valor': float(vencendo_hoje['valor'] or 0)
        },
        'vencidas': {
            'quantidade': vencidas['total'] or 0,
            'valor': float(vencidas['valor'] or 0)
        },
        'contratos_ativos': contratos_ativos
    }

    logger.info(f"Relatório diário gerado: {relatorio}")

    return relatorio
