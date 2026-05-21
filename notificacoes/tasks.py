"""
Tarefas assíncronas para envio de notificações (Celery)

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import logging

from financeiro.models import Parcela
from .models import Notificacao, TemplateNotificacao, TipoNotificacao, StatusNotificacao
from .services import enviar_notificacao

logger = logging.getLogger(__name__)


@shared_task
def enviar_notificacoes_vencimento():
    """
    Tarefa agendada para enviar notificações de parcelas a vencer
    Executa diariamente e envia notificações com base na configuração
    """
    logger.info("Iniciando envio de notificações de vencimento...")

    dias_antecedencia = settings.NOTIFICACAO_DIAS_ANTECEDENCIA
    data_limite = timezone.now().date() + timedelta(days=dias_antecedencia)

    # Buscar parcelas a vencer nos próximos X dias (não pagas)
    parcelas_a_vencer = Parcela.objects.filter(
        pago=False,
        data_vencimento__lte=data_limite,
        data_vencimento__gte=timezone.now().date()
    ).select_related('contrato', 'contrato__comprador')

    # Pre-fetch parcela IDs que já têm notificação pendente/enviada — 1 query
    parcelas_a_vencer = list(parcelas_a_vencer)
    parcela_ids = [p.id for p in parcelas_a_vencer]
    ja_notificadas = set(
        Notificacao.objects.filter(
            parcela_id__in=parcela_ids,
            status__in=[StatusNotificacao.PENDENTE, StatusNotificacao.ENVIADA],
        ).values_list('parcela_id', flat=True)
    )

    # Pre-fetch templates ativos por tipo — 1 query em vez de N×3
    templates_cache = {}
    for t in TemplateNotificacao.objects.filter(ativo=True):
        if t.tipo not in templates_cache:
            templates_cache[t.tipo] = t

    notificacoes_to_create = []

    for parcela in parcelas_a_vencer:
        if parcela.id in ja_notificadas:
            continue

        comprador = parcela.contrato.comprador

        for tipo, attr in [
            (TipoNotificacao.EMAIL, 'notificar_email'),
            (TipoNotificacao.SMS, 'notificar_sms'),
            (TipoNotificacao.WHATSAPP, 'notificar_whatsapp'),
        ]:
            if getattr(comprador, attr, False):
                notif = _preparar_notificacao_vencimento(
                    parcela, tipo, templates_cache.get(tipo)
                )
                if notif:
                    notificacoes_to_create.append(notif)

    if notificacoes_to_create:
        Notificacao.objects.bulk_create(notificacoes_to_create)

    notificacoes_criadas = len(notificacoes_to_create)
    logger.info(f"{notificacoes_criadas} notificações criadas.")

    # Processar notificações pendentes
    processar_notificacoes_pendentes.delay()

    return notificacoes_criadas


def _preparar_notificacao_vencimento(parcela, tipo_notificacao, template=None):
    """
    Prepara (sem salvar) um objeto Notificacao de vencimento para bulk_create.
    Retorna None se não houver destinatário válido.
    """
    comprador = parcela.contrato.comprador

    if template is None:
        template = TemplateNotificacao.objects.filter(
            tipo=tipo_notificacao,
            ativo=True
        ).first()

    contexto = {
        'comprador': comprador.nome,
        'numero_parcela': parcela.numero_parcela,
        'total_parcelas': parcela.contrato.numero_parcelas,
        'valor': f"R$ {parcela.valor_atual:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
        'vencimento': parcela.data_vencimento.strftime('%d/%m/%Y'),
        'contrato': parcela.contrato.numero_contrato,
        'imovel': str(parcela.contrato.imovel),
    }

    if template:
        assunto, mensagem, _ = template.renderizar(contexto)
    else:
        assunto = f"Parcela {parcela.numero_parcela}/{parcela.contrato.numero_parcelas} a vencer"
        mensagem = (
            f"Olá {comprador.nome},\n\n"
            f"Lembramos que a parcela {parcela.numero_parcela}/{parcela.contrato.numero_parcelas} "
            f"do contrato {parcela.contrato.numero_contrato} vence em {parcela.data_vencimento.strftime('%d/%m/%Y')}.\n\n"
            f"Valor: {contexto['valor']}\n"
            f"Imóvel: {parcela.contrato.imovel}\n\n"
            f"Atenciosamente,\n"
            f"Equipe de Gestão de Contratos"
        )

    if tipo_notificacao == TipoNotificacao.EMAIL:
        destinatario = comprador.email
    elif tipo_notificacao == TipoNotificacao.SMS:
        destinatario = comprador.celular
    elif tipo_notificacao == TipoNotificacao.WHATSAPP:
        numero = comprador.celular.replace('(', '').replace(')', '').replace('-', '').replace(' ', '')
        if not numero.startswith('+'):
            numero = f'+55{numero}'
        destinatario = numero
    else:
        return None

    if not destinatario:
        return None

    return Notificacao(
        parcela=parcela,
        tipo=tipo_notificacao,
        destinatario=destinatario,
        assunto=assunto,
        mensagem=mensagem,
        status=StatusNotificacao.PENDENTE,
    )


def criar_notificacao_vencimento(parcela, tipo_notificacao):
    """Cria uma notificação de vencimento para uma parcela (compatibilidade)."""
    notif = _preparar_notificacao_vencimento(parcela, tipo_notificacao)
    if notif:
        notif.save()


@shared_task
def processar_notificacoes_pendentes():
    """
    Processa e envia todas as notificações pendentes
    """
    logger.info("Processando notificações pendentes...")

    notificacoes = Notificacao.objects.filter(
        status=StatusNotificacao.PENDENTE,
        data_agendamento__lte=timezone.now()
    )

    enviadas = 0
    erros = 0

    for notificacao in notificacoes:
        try:
            sucesso, external_id = enviar_notificacao(
                tipo=notificacao.tipo,
                destinatario=notificacao.destinatario,
                assunto=notificacao.assunto,
                mensagem=notificacao.mensagem
            )

            if sucesso:
                notificacao.marcar_como_enviada(external_id=external_id)
                enviadas += 1
            else:
                notificacao.marcar_erro("Erro ao enviar notificação")
                erros += 1

        except Exception as e:
            logger.exception("Erro ao processar notificação %s: %s", notificacao.id, e)
            notificacao.marcar_erro(str(e))
            erros += 1

    logger.info(f"Processamento concluído. {enviadas} enviadas, {erros} erros.")

    return {
        'enviadas': enviadas,
        'erros': erros
    }


@shared_task
def reenviar_notificacao(notificacao_id):
    """
    Reenvia uma notificação específica

    Args:
        notificacao_id: ID da notificação a ser reenviada
    """
    try:
        notificacao = Notificacao.objects.get(id=notificacao_id)

        sucesso, external_id = enviar_notificacao(
            tipo=notificacao.tipo,
            destinatario=notificacao.destinatario,
            assunto=notificacao.assunto,
            mensagem=notificacao.mensagem
        )

        if sucesso:
            notificacao.marcar_como_enviada(external_id=external_id)
            logger.info("Notificação %s reenviada com sucesso (ext_id=%s)", notificacao_id, external_id)
            return True
        else:
            notificacao.marcar_erro("Erro ao reenviar notificação")
            logger.error("Erro ao reenviar notificação %s", notificacao_id)
            return False

    except Notificacao.DoesNotExist:
        logger.exception(f"Notificação {notificacao_id} não encontrada")
        return False
    except Exception as e:
        logger.exception("Erro ao reenviar notificação %s: %s", notificacao_id, e)
        return False
