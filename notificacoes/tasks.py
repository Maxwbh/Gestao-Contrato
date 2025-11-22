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

    notificacoes_criadas = 0

    for parcela in parcelas_a_vencer:
        comprador = parcela.contrato.comprador

        # Verificar se já existe notificação pendente ou enviada para esta parcela
        notificacao_existente = Notificacao.objects.filter(
            parcela=parcela,
            status__in=[StatusNotificacao.PENDENTE, StatusNotificacao.ENVIADA]
        ).exists()

        if notificacao_existente:
            continue

        # Criar notificações baseadas nas preferências do comprador
        if comprador.notificar_email:
            criar_notificacao_vencimento(parcela, TipoNotificacao.EMAIL)
            notificacoes_criadas += 1

        if comprador.notificar_sms:
            criar_notificacao_vencimento(parcela, TipoNotificacao.SMS)
            notificacoes_criadas += 1

        if comprador.notificar_whatsapp:
            criar_notificacao_vencimento(parcela, TipoNotificacao.WHATSAPP)
            notificacoes_criadas += 1

    logger.info(f"{notificacoes_criadas} notificações criadas.")

    # Processar notificações pendentes
    processar_notificacoes_pendentes.delay()

    return notificacoes_criadas


def criar_notificacao_vencimento(parcela, tipo_notificacao):
    """
    Cria uma notificação de vencimento para uma parcela

    Args:
        parcela: Objeto Parcela
        tipo_notificacao: Tipo da notificação (EMAIL, SMS, WHATSAPP)
    """
    comprador = parcela.contrato.comprador

    # Buscar template ativo para o tipo de notificação
    template = TemplateNotificacao.objects.filter(
        tipo=tipo_notificacao,
        ativo=True
    ).first()

    # Preparar contexto para renderização do template
    contexto = {
        'comprador': comprador.nome,
        'numero_parcela': parcela.numero_parcela,
        'total_parcelas': parcela.contrato.numero_parcelas,
        'valor': f"R$ {parcela.valor_atual:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
        'vencimento': parcela.data_vencimento.strftime('%d/%m/%Y'),
        'contrato': parcela.contrato.numero_contrato,
        'imovel': str(parcela.contrato.imovel),
    }

    # Renderizar template ou usar mensagem padrão
    if template:
        assunto, mensagem = template.renderizar(contexto)
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

    # Determinar destinatário
    if tipo_notificacao == TipoNotificacao.EMAIL:
        destinatario = comprador.email
    elif tipo_notificacao == TipoNotificacao.SMS:
        destinatario = comprador.celular
    elif tipo_notificacao == TipoNotificacao.WHATSAPP:
        # Formatar número para WhatsApp (adicionar +55 se necessário)
        numero = comprador.celular.replace('(', '').replace(')', '').replace('-', '').replace(' ', '')
        if not numero.startswith('+'):
            numero = f'+55{numero}'
        destinatario = numero
    else:
        return

    # Criar notificação
    Notificacao.objects.create(
        parcela=parcela,
        tipo=tipo_notificacao,
        destinatario=destinatario,
        assunto=assunto,
        mensagem=mensagem,
        status=StatusNotificacao.PENDENTE
    )


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
            sucesso = enviar_notificacao(
                tipo=notificacao.tipo,
                destinatario=notificacao.destinatario,
                assunto=notificacao.assunto,
                mensagem=notificacao.mensagem
            )

            if sucesso:
                notificacao.marcar_como_enviada()
                enviadas += 1
            else:
                notificacao.marcar_erro("Erro ao enviar notificação")
                erros += 1

        except Exception as e:
            logger.error(f"Erro ao processar notificação {notificacao.id}: {str(e)}")
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

        sucesso = enviar_notificacao(
            tipo=notificacao.tipo,
            destinatario=notificacao.destinatario,
            assunto=notificacao.assunto,
            mensagem=notificacao.mensagem
        )

        if sucesso:
            notificacao.marcar_como_enviada()
            logger.info(f"Notificação {notificacao_id} reenviada com sucesso")
            return True
        else:
            notificacao.marcar_erro("Erro ao reenviar notificação")
            logger.error(f"Erro ao reenviar notificação {notificacao_id}")
            return False

    except Notificacao.DoesNotExist:
        logger.error(f"Notificação {notificacao_id} não encontrada")
        return False
    except Exception as e:
        logger.error(f"Erro ao reenviar notificação {notificacao_id}: {str(e)}")
        return False
