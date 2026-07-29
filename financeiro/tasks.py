"""
Tarefas assíncronas para o app Financeiro (Celery)

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import logging

from contratos.models import Contrato, TipoCorrecao, StatusContrato
from .models import Reajuste

logger = logging.getLogger(__name__)


@shared_task
def processar_reajustes_pendentes():
    """
    Tarefa agendada para processar reajustes automáticos de todos os contratos ativos.

    Identifica contratos com ciclo pendente usando Reajuste.calcular_ciclo_pendente()
    e aplica cada ciclo usando Reajuste.preview_reajuste() + aplicar_reajuste().

    Recomendado: executar mensalmente no primeiro dia do mês.
    """
    logger.info("Iniciando processamento automático de reajustes pendentes...")

    contratos = Contrato.objects.filter(status=StatusContrato.ATIVO).select_related('comprador', 'imobiliaria')
    processados = 0
    reajustados = 0
    erros = 0

    for contrato in contratos:
        processados += 1
        ciclo = Reajuste.calcular_ciclo_pendente(contrato)
        if ciclo is None:
            continue
        try:
            resultado = aplicar_reajuste_automatico(contrato.id, ciclo)
            if resultado:
                reajustados += 1
        except Exception as e:
            erros += 1
            logger.exception("Erro no reajuste automático do contrato %s: %s", contrato.numero_contrato, e)

    logger.info(
        f"Reajustes automáticos: {processados} contratos verificados, "
        f"{reajustados} reajustados, {erros} erros."
    )
    return {'processados': processados, 'reajustados': reajustados, 'erros': erros}


@shared_task
def aplicar_reajuste_automatico(contrato_id, ciclo=None):
    """
    Aplica reajuste automático no ciclo correto de um contrato específico.

    Usa Reajuste.calcular_ciclo_pendente() para determinar o ciclo e
    Reajuste.preview_reajuste() para calcular o percentual acumulado do índice.

    Args:
        contrato_id: ID do contrato.
        ciclo: Número do ciclo a aplicar; se None, usa o ciclo pendente calculado.

    Returns:
        dict com resultado ou False em caso de erro/não aplicável.
    """
    try:
        contrato = Contrato.objects.select_related('comprador', 'imobiliaria').get(id=contrato_id)
    except Contrato.DoesNotExist:
        logger.exception(f"Contrato {contrato_id} não encontrado para reajuste automático.")
        return False

    if contrato.tipo_correcao == TipoCorrecao.FIXO:
        logger.info(f"Contrato {contrato.numero_contrato}: tipo FIXO, sem reajuste.")
        return False

    if ciclo is None:
        ciclo = Reajuste.calcular_ciclo_pendente(contrato)

    if ciclo is None:
        logger.info(f"Contrato {contrato.numero_contrato}: nenhum ciclo pendente.")
        return False

    try:
        preview = Reajuste.preview_reajuste(contrato, ciclo)
    except Exception as e:
        logger.exception("Contrato %s: erro ao calcular preview ciclo %s: %s", contrato.numero_contrato, ciclo, e)
        return False

    if 'erro' in preview:
        logger.warning(
            f"Contrato {contrato.numero_contrato} ciclo {ciclo}: índice não disponível — {preview['erro']}"
        )
        return False

    if not contrato.parcelas.filter(
        numero_parcela__gte=preview['parcela_inicial'],
        numero_parcela__lte=preview['parcela_final'],
        pago=False,
    ).exists():
        logger.info(f"Contrato {contrato.numero_contrato} ciclo {ciclo}: sem parcelas pendentes no intervalo.")
        return False

    reajuste = Reajuste.objects.create(
        contrato=contrato,
        data_reajuste=timezone.now().date(),
        indice_tipo=preview['indice_tipo'],
        percentual=preview['percentual_final'],
        percentual_bruto=preview['percentual_bruto'],
        spread_aplicado=preview['spread'] if preview['spread'] else None,
        piso_aplicado=preview['piso'],
        teto_aplicado=preview['teto'],
        parcela_inicial=preview['parcela_inicial'],
        parcela_final=preview['parcela_final'],
        ciclo=ciclo,
        periodo_referencia_inicio=preview['periodo_referencia_inicio'],
        periodo_referencia_fim=preview['periodo_referencia_fim'],
        aplicado_manual=False,
        observacoes=f'Reajuste automático (Celery) — ciclo {ciclo}, {preview["indice_tipo"]} {preview["percentual_final"]:.4f}%',
    )

    resultado = reajuste.aplicar_reajuste()

    logger.info(
        f"Contrato {contrato.numero_contrato}: reajuste automático ciclo {ciclo} "
        f"({preview['percentual_final']:.4f}%) aplicado em "
        f"{resultado.get('parcelas_reajustadas', 0)} parcelas."
    )

    # Notificar gestor da imobiliária
    try:
        enviar_alerta_reajuste.delay(
            contrato_id=contrato.id,
            dias_restantes=0,
            urgente=False,
            bloqueado=False,
        )
    except Exception:
        pass

    return resultado


@shared_task
def atualizar_juros_multa_parcelas_vencidas():
    """
    Atualiza juros e multa de todas as parcelas vencidas e não pagas
    """
    from .models import Parcela

    logger.info("Iniciando atualização de juros e multa de parcelas vencidas...")

    hoje = timezone.now().date()
    parcelas_vencidas = list(
        Parcela.objects.filter(pago=False, data_vencimento__lt=hoje)
        .select_related('contrato')
    )

    to_update = []
    for parcela in parcelas_vencidas:
        juros, multa = parcela.calcular_juros_multa(hoje)
        parcela.valor_juros = juros
        parcela.valor_multa = multa
        to_update.append(parcela)

    if to_update:
        Parcela.objects.bulk_update(to_update, ['valor_juros', 'valor_multa'])

    count = len(to_update)
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
            logger.exception("Erro ao buscar índice %s: %s", tipo, e)
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
            logger.exception("Erro ao enviar alerta para contrato %s: %s", contrato.numero_contrato, e)

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
        logger.exception("Erro ao enviar alerta de reajuste: %s", e)
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
    parcelas = list(Parcela.objects.filter(
        contrato__status=StatusContrato.ATIVO,
        data_vencimento__gte=primeiro_dia_proximo_mes,
        data_vencimento__lte=ultimo_dia_proximo_mes,
        pago=False,
        status_boleto=StatusBoleto.NAO_GERADO
    ).select_related(
        'contrato',
        'contrato__comprador',
        'contrato__imovel__imobiliaria',
        'contrato__imobiliaria',
        'conta_bancaria',
    ))

    resultados = {
        'total': len(parcelas),
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
            logger.exception(f"Erro ao gerar boleto da parcela {parcela.id}: {e}")

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

    dias_lembrete = [7, 3, 1]
    datas_lembrete = [hoje + timedelta(days=d) for d in dias_lembrete]

    parcelas = Parcela.objects.filter(
        pago=False,
        data_vencimento__in=datas_lembrete
    ).select_related('contrato', 'contrato__comprador')

    for parcela in parcelas:
        dias = (parcela.data_vencimento - hoje).days
        try:
            enviar_lembrete_parcela.delay(parcela.id, dias)
            lembretes_enviados += 1
        except Exception as e:
            logger.exception("Erro ao agendar lembrete para parcela %s: %s", parcela.id, e)

    logger.info(f"Lembretes agendados: {lembretes_enviados}")

    return lembretes_enviados


@shared_task
def enviar_lembrete_parcela(parcela_id, dias_para_vencimento):
    """
    Envia lembrete de vencimento para uma parcela específica.
    """
    from .models import Parcela
    from django.core.mail import send_mail

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
        logger.exception(f"Parcela {parcela_id} não encontrada")
    except Exception as e:
        logger.exception("Erro ao enviar lembrete: %s", e)

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

    service = CNABService()
    for arquivo in arquivos:
        try:
            resultado = service.processar_retorno(arquivo)

            if resultado.get('sucesso'):
                processados += 1
            else:
                erros += 1
                logger.error(f"Erro ao processar retorno {arquivo.id}: {resultado.get('erro')}")

        except Exception as e:
            erros += 1
            logger.exception(f"Erro ao processar arquivo de retorno {arquivo.id}: {e}")

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
    from django.db.models import Sum, Count, Q
    from .models import Parcela
    from contratos.models import Contrato, StatusContrato

    hoje = timezone.now().date()
    ontem = hoje - timedelta(days=1)

    agg = Parcela.objects.aggregate(
        pag_total=Count('id', filter=Q(pago=True, data_pagamento=ontem)),
        pag_valor=Sum('valor_pago', filter=Q(pago=True, data_pagamento=ontem)),
        boletos_dia=Count('id', filter=Q(data_geracao_boleto__date=ontem)),
        venc_hoje_total=Count('id', filter=Q(pago=False, data_vencimento=hoje)),
        venc_hoje_valor=Sum('valor_atual', filter=Q(pago=False, data_vencimento=hoje)),
        vencidas_total=Count('id', filter=Q(pago=False, data_vencimento__lt=hoje)),
        vencidas_valor=Sum('valor_atual', filter=Q(pago=False, data_vencimento__lt=hoje)),
    )

    contratos_ativos = Contrato.objects.filter(status=StatusContrato.ATIVO).count()

    relatorio = {
        'data': str(ontem),
        'pagamentos': {
            'quantidade': agg['pag_total'] or 0,
            'valor': float(agg['pag_valor'] or 0)
        },
        'boletos_gerados': agg['boletos_dia'] or 0,
        'vencendo_hoje': {
            'quantidade': agg['venc_hoje_total'] or 0,
            'valor': float(agg['venc_hoje_valor'] or 0)
        },
        'vencidas': {
            'quantidade': agg['vencidas_total'] or 0,
            'valor': float(agg['vencidas_valor'] or 0)
        },
        'contratos_ativos': contratos_ativos
    }

    logger.info(f"Relatório diário gerado: {relatorio}")

    return relatorio


# =============================================================================
# 34.5 P3 — Relatórios Agendados e Exportação para BI
# =============================================================================

@shared_task
def enviar_relatorio_inadimplencia(frequencia='diario'):
    """
    34.5.1 — Envia relatório de inadimplência por e-mail.

    frequencia: 'diario' (padrão) ou 'semanal'
    Destinatários: settings.RELATORIO_INADIMPLENCIA_EMAILS
    """
    from django.core.mail import EmailMultiAlternatives
    from django.db.models import Sum, Count, Q
    from django.template.loader import render_to_string
    from .models import Parcela
    from contratos.models import StatusContrato

    emails_destino = getattr(settings, 'RELATORIO_INADIMPLENCIA_EMAILS', [])
    if not emails_destino:
        logger.info('enviar_relatorio_inadimplencia: nenhum destinatário configurado (RELATORIO_INADIMPLENCIA_EMAILS).')
        return {'enviado': False, 'motivo': 'sem_destinatarios'}

    hoje = timezone.now().date()
    limiar_dias = 1 if frequencia == 'diario' else 7

    # Parcelas vencidas (>0 dias) e não pagas
    vencidas_qs = Parcela.objects.filter(
        pago=False,
        data_vencimento__lt=hoje,
        contrato__status=StatusContrato.ATIVO,
    ).select_related('contrato', 'contrato__comprador', 'contrato__imobiliaria')

    agg = vencidas_qs.aggregate(
        total=Count('id'),
        valor_total=Sum('valor_atual'),
        vencidas_30d=Count('id', filter=Q(data_vencimento__lte=hoje - timedelta(days=30))),
        vencidas_60d=Count('id', filter=Q(data_vencimento__lte=hoje - timedelta(days=60))),
        vencidas_90d=Count('id', filter=Q(data_vencimento__lte=hoje - timedelta(days=90))),
    )

    # Top 20 parcelas mais antigas
    top_inadimplentes = list(
        vencidas_qs.order_by('data_vencimento')[:20].values(
            'contrato__numero_contrato',
            'contrato__comprador__nome',
            'contrato__imobiliaria__nome',
            'numero_parcela',
            'data_vencimento',
            'valor_atual',
        )
    )

    contexto = {
        'data_referencia': hoje,
        'frequencia': frequencia,
        'agg': agg,
        'top_inadimplentes': top_inadimplentes,
        'valor_total': agg['valor_total'] or 0,
    }

    titulo = f"[{'Diário' if frequencia == 'diario' else 'Semanal'}] Relatório de Inadimplência — {hoje.strftime('%d/%m/%Y')}"

    html_body = _render_relatorio_inadimplencia_html(contexto)
    text_body = _render_relatorio_inadimplencia_text(contexto)

    msg = EmailMultiAlternatives(
        subject=titulo,
        body=text_body,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
        to=list(emails_destino),
    )
    msg.attach_alternative(html_body, 'text/html')

    try:
        msg.send()
        logger.info('Relatório de inadimplência enviado para %s destinatários.', len(emails_destino))
        return {'enviado': True, 'destinatarios': len(emails_destino), 'total_vencidas': agg['total']}
    except Exception as exc:
        logger.exception('Erro ao enviar relatório de inadimplência: %s', exc)
        return {'enviado': False, 'erro': str(exc)}


def _render_relatorio_inadimplencia_html(ctx):
    hoje = ctx['data_referencia']
    agg = ctx['agg']
    top = ctx['top_inadimplentes']
    linhas = ''
    for row in top:
        linhas += (
            f'<tr>'
            f'<td>{row["contrato__numero_contrato"]}</td>'
            f'<td>{row["contrato__comprador__nome"]}</td>'
            f'<td>{(row["contrato__imobiliaria__nome"] or "")[:25]}</td>'
            f'<td>{row["numero_parcela"]}</td>'
            f'<td>{row["data_vencimento"].strftime("%d/%m/%Y")}</td>'
            f'<td>R$ {float(row["valor_atual"]):,.2f}</td>'
            f'</tr>'
        )
    return f"""
<html><body style="font-family:Arial,sans-serif;font-size:14px;">
<h2 style="color:#c62828;">Relatório de Inadimplência — {hoje.strftime('%d/%m/%Y')}</h2>
<table cellspacing="4" style="border-collapse:collapse;">
  <tr><td style="padding:4px 12px;"><strong>Total vencidas:</strong></td><td>{agg['total'] or 0}</td></tr>
  <tr><td style="padding:4px 12px;"><strong>Valor total:</strong></td><td>R$ {float(agg['valor_total'] or 0):,.2f}</td></tr>
  <tr><td style="padding:4px 12px;"><strong>Venc. >30 dias:</strong></td><td>{agg['vencidas_30d'] or 0}</td></tr>
  <tr><td style="padding:4px 12px;"><strong>Venc. >60 dias:</strong></td><td>{agg['vencidas_60d'] or 0}</td></tr>
  <tr><td style="padding:4px 12px;"><strong>Venc. >90 dias:</strong></td><td>{agg['vencidas_90d'] or 0}</td></tr>
</table>
<br>
<h3>Top inadimplentes (mais antigas)</h3>
<table border="1" cellspacing="0" cellpadding="6" style="border-collapse:collapse;font-size:13px;">
<thead style="background:#ffebee;">
  <tr><th>Contrato</th><th>Comprador</th><th>Imobiliária</th><th>Parcela</th><th>Vencimento</th><th>Valor</th></tr>
</thead>
<tbody>{linhas}</tbody>
</table>
</body></html>"""


def _render_relatorio_inadimplencia_text(ctx):
    agg = ctx['agg']
    hoje = ctx['data_referencia']
    linhas = [f"Relatório de Inadimplência — {hoje.strftime('%d/%m/%Y')}",
              f"Total vencidas: {agg['total'] or 0}",
              f"Valor total: R$ {float(agg['valor_total'] or 0):,.2f}",
              f"Venc. >30 dias: {agg['vencidas_30d'] or 0}",
              f"Venc. >60 dias: {agg['vencidas_60d'] or 0}",
              f"Venc. >90 dias: {agg['vencidas_90d'] or 0}", '']
    for row in ctx['top_inadimplentes']:
        linhas.append(
            f"{row['contrato__numero_contrato']} | {row['contrato__comprador__nome'][:30]} | "
            f"Parc.{row['numero_parcela']} | {row['data_vencimento'].strftime('%d/%m/%Y')} | "
            f"R$ {float(row['valor_atual'] or 0):,.2f}"
        )
    return '\n'.join(linhas)


@shared_task
def enviar_relatorio_posicao_contratos(formato='excel'):
    """
    34.5.2 — Gera e envia por e-mail o relatório de posição de contratos.

    formato: 'excel' (padrão) ou 'pdf'
    Destinatários: settings.RELATORIO_POSICAO_EMAILS
    """
    from django.core.mail import EmailMessage
    from .services import RelatorioService, FiltroRelatorio

    emails_destino = getattr(settings, 'RELATORIO_POSICAO_EMAILS', [])
    if not emails_destino:
        logger.info('enviar_relatorio_posicao_contratos: nenhum destinatário configurado.')
        return {'enviado': False, 'motivo': 'sem_destinatarios'}

    hoje = timezone.now().date()
    service = RelatorioService()
    filtro = FiltroRelatorio()
    relatorio = service.gerar_relatorio_posicao_contratos(filtro)

    if formato == 'pdf':
        try:
            conteudo = service.exportar_para_pdf(relatorio)
            mime = 'application/pdf'
            ext = 'pdf'
        except Exception:
            conteudo = service.exportar_para_excel(relatorio)
            mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ext = 'xlsx'
    else:
        conteudo = service.exportar_para_excel(relatorio)
        mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ext = 'xlsx'

    total = relatorio['totalizadores']['total_contratos']
    titulo = f"Posição de Contratos — {hoje.strftime('%d/%m/%Y')} ({total} contratos)"

    msg = EmailMessage(
        subject=titulo,
        body=(
            f"Relatório de posição de contratos em anexo.\n\n"
            f"Total de contratos ativos: {total}\n"
            f"Saldo devedor total: R$ {float(relatorio['totalizadores']['total_saldo_devedor'] or 0):,.2f}\n"
            f"Total pago: R$ {float(relatorio['totalizadores']['total_pago'] or 0):,.2f}\n"
        ),
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
        to=list(emails_destino),
    )
    msg.attach(f'posicao_contratos_{hoje.isoformat()}.{ext}', conteudo, mime)

    try:
        msg.send()
        logger.info('Relatório de posição enviado para %s destinatários.', len(emails_destino))
        return {'enviado': True, 'destinatarios': len(emails_destino), 'total_contratos': total}
    except Exception as exc:
        logger.exception('Erro ao enviar relatório de posição: %s', exc)
        return {'enviado': False, 'erro': str(exc)}


# =============================================================================
# Boleto-API — Agendadores (Fase 7): polling, conciliação Pix e fila 409/CIP
# =============================================================================

@shared_task
def polling_boletos_sicoob():
    """
    Sicoob não envia webhook de boleto: consulta GET /cobranca/{id} das parcelas
    Sicoob em aberto e baixa as que estiverem liquidadas. Rodar diariamente.
    """
    from core.models import ProviderBoleto
    from .models import Parcela
    from .services.boleto_api_client import BoletoApiClient
    from .services.boleto_api_conciliacao import baixar_por_conciliacao

    parcelas = (Parcela.objects
                .filter(provider=ProviderBoleto.SICOOB, pago=False)
                .exclude(cobranca_id='')
                .select_related('conta_bancaria'))
    client = BoletoApiClient()
    baixadas = 0
    for p in parcelas:
        conta = p.conta_bancaria
        r = client.consultar_cobranca(
            p.cobranca_id, getattr(conta, 'tenant_id', '') or '', p.provider,
            bapi_token=(getattr(conta, 'bapi_token', '') or None))
        if r.get('sucesso') and str(r.get('status', '')).lower() in ('liquidado', 'pago'):
            baixar_por_conciliacao(p, valor=r.get('valor'), origem='polling-sicoob')
            baixadas += 1
    logger.info('[BoletoAPI] polling Sicoob: %d parcela(s) baixada(s)', baixadas)
    return {'baixadas': baixadas}


@shared_task
def conciliar_pix_recebidos(dias=1):
    """
    Rede de segurança do webhook Pix: lista GET /pix/recebidos do período e baixa
    as parcelas casadas por txid ainda não pagas. Rodar diariamente.
    """
    from core.models import ProviderBoleto, ContaBancaria
    from .models import Parcela
    from .services.boleto_api_client import BoletoApiClient
    from .services.boleto_api_conciliacao import baixar_por_conciliacao

    fim = timezone.now().date()
    inicio = fim - timedelta(days=dias)
    client = BoletoApiClient()
    baixadas = 0
    contas = ContaBancaria.objects.filter(
        provider__in=[ProviderBoleto.C6, ProviderBoleto.SICOOB], ativo=True)
    for conta in contas:
        r = client.listar_pix_recebidos(
            inicio.isoformat(), fim.isoformat(), conta.tenant_id, conta.provider,
            bapi_token=(conta.bapi_token or None))
        if not r.get('sucesso'):
            continue
        for item in r.get('itens', []):
            txid = str(item.get('txid') or '')
            if not txid:
                continue
            p = Parcela.objects.filter(pix_txid=txid, pago=False).first()
            if p:
                baixar_por_conciliacao(p, valor=item.get('valor'), origem='pix')
                baixadas += 1
    logger.info('[BoletoAPI] conciliação Pix: %d parcela(s) baixada(s)', baixadas)
    return {'baixadas': baixadas}


@shared_task
def reprocessar_fila_cip():
    """
    Reprocessa cobranças que ficaram AGUARDANDO_CIP (409 na emissão): tenta emitir
    de novo. Ao ter sucesso, a própria emissão atualiza o status. Rodar por evento
    ou diariamente.
    """
    from .models import Parcela, StatusCobranca

    parcelas = (Parcela.objects
                .filter(status_cobranca=StatusCobranca.AGUARDANDO_CIP, pago=False)
                .select_related('conta_bancaria'))
    reprocessadas = 0
    for p in parcelas:
        conta = p.conta_bancaria
        if not conta:
            continue
        r = p.gerar_boleto(conta_bancaria=conta, force=True, enviar_email=False)
        if r.get('sucesso'):
            reprocessadas += 1
    logger.info('[BoletoAPI] fila CIP: %d cobrança(s) reprocessada(s)', reprocessadas)
    return {'reprocessadas': reprocessadas}


@shared_task
def agendar_cobrancas_pix_automatico(dias_antecedencia=2):
    """
    Pix Automático (Fase 8): para cada contrato com recorrência APROVADA e parcela
    vencendo em D+`dias_antecedencia`, agenda a cobrança do ciclo
    (PUT /pix-automatico/cobrancas/{txid}). Rodar diariamente.
    """
    from core.models import MetodoCobranca
    from .models import RecorrenciaPix, RecStatusPA, StatusCobranca
    from .services.boleto_api_client import BoletoApiClient

    alvo = timezone.now().date() + timedelta(days=dias_antecedencia)
    recs = (RecorrenciaPix.objects
            .filter(status=RecStatusPA.APROVADA)
            .select_related('contrato'))
    client = BoletoApiClient()
    agendadas = 0
    for rec in recs:
        contrato = rec.contrato
        conta = contrato.get_conta_bancaria()
        parcela = contrato.parcelas.filter(data_vencimento=alvo, pago=False).first()
        if not parcela:
            continue
        txid = f'CT{contrato.id:07d}{alvo.strftime("%Y%m")}'
        r = client.agendar_cobranca_pa(
            txid, getattr(conta, 'tenant_id', '') or '', rec.provider,
            {'valor': float(parcela.valor_atual or 0), 'vencimento': alvo.isoformat()},
            bapi_token=(getattr(conta, 'bapi_token', '') or None))
        if r.get('sucesso'):
            parcela.registrar_emissao(
                provider=rec.provider, metodo=MetodoCobranca.PIX_AUTOMATICO,
                status=StatusCobranca.REGISTRADA, txid=txid)
            parcela.save(update_fields=['pix_txid', 'provider', 'metodo_cobranca', 'status_cobranca'])
            agendadas += 1
    logger.info('[BoletoAPI] Pix Automático: %d cobrança(s) agendada(s) p/ %s', agendadas, alvo)
    return {'agendadas': agendadas}


@shared_task
def retentar_cobrancas_pix_automatico(janela_dias=7):
    """
    Pix Automático (BAPI-36): retenta cobranças do ciclo vencidas e não pagas
    de recorrências APROVADAS (POST /pix-automatico/cobrancas/{txid}/
    retentativa/{data}). Janela limitada evita retentativa eterna. Rodar
    diariamente.
    """
    from core.models import MetodoCobranca
    from .models import Parcela, RecorrenciaPix, RecStatusPA, StatusCobranca
    from .services.boleto_api_client import BoletoApiClient

    hoje = timezone.now().date()
    parcelas = (Parcela.objects
                .filter(metodo_cobranca=MetodoCobranca.PIX_AUTOMATICO,
                        status_cobranca=StatusCobranca.REGISTRADA,
                        pago=False,
                        data_vencimento__lt=hoje,
                        data_vencimento__gte=hoje - timedelta(days=janela_dias))
                .exclude(pix_txid='')
                .select_related('contrato'))
    client = BoletoApiClient()
    retentadas = 0
    for p in parcelas:
        rec = RecorrenciaPix.objects.filter(
            contrato=p.contrato, status=RecStatusPA.APROVADA).first()
        if not rec:
            continue
        tenant_id, bapi_token = p._bapi_ctx()
        r = client.retentar_cobranca_pa(
            p.pix_txid, (hoje + timedelta(days=1)).isoformat(),
            tenant_id, p.provider, bapi_token=bapi_token)
        if r.get('sucesso'):
            retentadas += 1
    logger.info('[BoletoAPI] Pix Automático: %d retentativa(s) agendada(s)', retentadas)
    return {'retentadas': retentadas}
