"""
34.6 P3 — Tarefas Celery do Portal do Comprador

Envia notificações push Web Push para compradores cadastrados.
"""
from celery import shared_task
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task
def enviar_push_comprador(acesso_comprador_id, titulo, corpo, url='/portal/'):
    """
    34.6.3 — Envia notificação push Web Push para todas as assinaturas ativas de um comprador.

    Requer pywebpush instalado e VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY nas settings.
    Desativa assinaturas com erro 410 (Gone — comprador cancelou no browser).
    """
    from .models import PushSubscriptionPortal

    subscriptions = list(
        PushSubscriptionPortal.objects.filter(
            acesso_comprador_id=acesso_comprador_id,
            ativo=True,
        )
    )
    if not subscriptions:
        logger.info('enviar_push_comprador: acesso %s sem assinaturas ativas.', acesso_comprador_id)
        return {'enviadas': 0, 'erros': 0}

    public_key = getattr(settings, 'VAPID_PUBLIC_KEY', '')
    private_key = getattr(settings, 'VAPID_PRIVATE_KEY', '')
    claims_email = getattr(settings, 'VAPID_CLAIMS_EMAIL', 'admin@example.com')

    if not public_key or not private_key:
        logger.warning('enviar_push_comprador: VAPID_PUBLIC_KEY ou VAPID_PRIVATE_KEY não configurados.')
        return {'enviadas': 0, 'erros': 0, 'motivo': 'vapid_nao_configurado'}

    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        logger.warning('pywebpush não instalado — notificações push desabilitadas.')
        return {'enviadas': 0, 'erros': 0, 'motivo': 'pywebpush_nao_instalado'}

    import json

    payload = json.dumps({
        'titulo': titulo,
        'corpo': corpo,
        'url': url,
        'icone': '/static/img/icon-192.png',
    }, ensure_ascii=False)

    enviadas = 0
    erros = 0
    desativadas = []

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    'endpoint': sub.endpoint,
                    'keys': {'p256dh': sub.p256dh, 'auth': sub.auth},
                },
                data=payload,
                vapid_private_key=private_key,
                vapid_claims={'sub': f'mailto:{claims_email}'},
            )
            enviadas += 1
        except WebPushException as exc:
            erros += 1
            if exc.response and exc.response.status_code == 410:
                desativadas.append(sub.pk)
                logger.info('Push sub %s desativada (410 Gone).', sub.pk)
            else:
                logger.warning('Erro ao enviar push sub %s: %s', sub.pk, exc)
        except Exception as exc:
            erros += 1
            logger.exception('Erro inesperado ao enviar push sub %s: %s', sub.pk, exc)

    if desativadas:
        PushSubscriptionPortal.objects.filter(pk__in=desativadas).update(ativo=False)

    logger.info(
        'Push comprador %s: %d enviadas, %d erros, %d desativadas.',
        acesso_comprador_id, enviadas, erros, len(desativadas),
    )
    return {'enviadas': enviadas, 'erros': erros, 'desativadas': len(desativadas)}


@shared_task
def notificar_push_vencimento_amanha():
    """
    34.6.3 — Envia push de lembrete para compradores com parcelas vencendo amanhã.
    Executar diariamente.
    """
    from django.utils import timezone
    from datetime import timedelta
    from financeiro.models import Parcela
    from .models import AcessoComprador

    amanha = timezone.now().date() + timedelta(days=1)
    parcelas = Parcela.objects.filter(
        pago=False,
        data_vencimento=amanha,
    ).select_related('contrato', 'contrato__comprador')

    enviados = 0
    for parcela in parcelas:
        comprador = parcela.contrato.comprador
        try:
            acesso = AcessoComprador.objects.get(comprador=comprador, ativo=True)
        except AcessoComprador.DoesNotExist:
            continue

        if not PushSubscriptionPortal.objects.filter(acesso_comprador=acesso, ativo=True).exists():
            continue

        enviar_push_comprador.delay(
            acesso_comprador_id=acesso.pk,
            titulo='Parcela vence amanhã',
            corpo=(
                f'Contrato {parcela.contrato.numero_contrato} — '
                f'Parcela {parcela.numero_parcela} vence amanhã. '
                f'Valor: R$ {float(parcela.valor_atual):,.2f}'
            ),
            url='/portal/boletos/',
        )
        enviados += 1

    logger.info('notificar_push_vencimento_amanha: %d compradores notificados.', enviados)
    return {'notificados': enviados}


# import circular seguro (models importados localmente acima)
from .models import PushSubscriptionPortal  # noqa: E402
