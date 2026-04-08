"""
Gerenciador de Tarefas para Render Free Tier

Como o Celery não está disponível no plano gratuito do Render,
este módulo fornece alternativas para execução de tarefas agendadas:

1. Endpoints HTTP protegidos para execução manual
2. Suporte a cron jobs externos (cron-job.org, EasyCron, etc.)
3. Execução via Django management commands

Uso:
    # Via endpoint HTTP (protegido por token)
    curl -X POST https://seu-app.onrender.com/api/tasks/processar-reajustes/ \
         -H "X-Task-Token: seu-token-secreto"

    # Via management command
    python manage.py executar_tarefas --task=reajustes

    # Via cron externo (configurar no cron-job.org)
    POST https://seu-app.onrender.com/api/tasks/run-all/
    Header: X-Task-Token: seu-token-secreto
"""
import logging
from datetime import datetime, timedelta
from functools import wraps
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)

# Token para autenticação de tarefas (configurar via env var)
TASK_TOKEN = getattr(settings, 'TASK_TOKEN', None)


def task_auth_required(view_func):
    """
    Decorator que verifica autenticação por token para endpoints de tarefas.

    O token deve ser enviado no header X-Task-Token ou como parâmetro 'token'.
    Configure TASK_TOKEN nas variáveis de ambiente.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Verificar se TASK_TOKEN está configurado
        if not TASK_TOKEN:
            logger.warning("TASK_TOKEN não configurado - tarefas desabilitadas")
            return JsonResponse({
                'status': 'error',
                'message': 'Tarefas não configuradas. Defina TASK_TOKEN nas variáveis de ambiente.'
            }, status=503)

        # Obter token do request
        token = request.headers.get('X-Task-Token') or request.GET.get('token')

        if not token:
            return JsonResponse({
                'status': 'error',
                'message': 'Token de autenticação não fornecido'
            }, status=401)

        if token != TASK_TOKEN:
            logger.warning(f"Tentativa de acesso com token inválido: {request.META.get('REMOTE_ADDR')}")
            return JsonResponse({
                'status': 'error',
                'message': 'Token inválido'
            }, status=403)

        return view_func(request, *args, **kwargs)
    return wrapper


class TaskResult:
    """Classe para padronizar resultados de tarefas."""

    def __init__(self, task_name: str):
        self.task_name = task_name
        self.started_at = datetime.now()
        self.finished_at = None
        self.success = False
        self.items_processed = 0
        self.errors = []
        self.messages = []

    def add_message(self, message: str):
        self.messages.append(message)
        logger.info(f"[{self.task_name}] {message}")

    def add_error(self, error: str):
        self.errors.append(error)
        logger.exception(f"[{self.task_name}] {error}")

    def finish(self, success: bool = True):
        self.finished_at = datetime.now()
        self.success = success and len(self.errors) == 0

    def to_dict(self) -> dict:
        return {
            'task': self.task_name,
            'success': self.success,
            'started_at': self.started_at.isoformat(),
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'duration_seconds': (self.finished_at - self.started_at).total_seconds() if self.finished_at else None,
            'items_processed': self.items_processed,
            'messages': self.messages,
            'errors': self.errors,
        }


def processar_reajustes_sync():
    """
    Processa reajustes pendentes de forma síncrona.
    Alternativa à task Celery para o Free tier.
    """
    from contratos.models import Contrato, StatusContrato
    from financeiro.models import Reajuste
    from contratos.services import IndiceEconomicoService, ReajusteService
    from decimal import Decimal
    from datetime import date

    result = TaskResult('processar_reajustes')

    try:
        hoje = date.today()

        # Buscar contratos ativos que usam índice econômico para reajuste
        contratos = Contrato.objects.filter(
            status=StatusContrato.ATIVO,
            tipo_correcao__in=['IPCA', 'IGPM', 'INCC', 'IGPDI', 'INPC', 'TR', 'SELIC']
        ).select_related('imobiliaria', 'comprador')

        result.add_message(f"Verificando {contratos.count()} contratos ativos")

        for contrato in contratos:
            try:
                # Verificar se há ciclo pendente de reajuste
                ciclo = Reajuste.calcular_ciclo_pendente(contrato)
                if not ciclo:
                    continue

                # Buscar índice atual para o tipo de correção do contrato
                indice = IndiceEconomicoService.get_indice_atual(contrato.tipo_correcao)

                if indice:
                    # Aplicar reajuste às parcelas pendentes
                    parcelas_pendentes = list(contrato.parcelas.filter(
                        pago=False,
                        data_vencimento__gte=hoje
                    ))

                    with transaction.atomic():
                        for parcela in parcelas_pendentes:
                            percentual = Decimal(str(indice.get('valor', 0)))
                            novo_valor = ReajusteService.calcular_reajuste(
                                parcela.valor_atual, percentual
                            )
                            parcela.valor_atual = novo_valor
                            parcela.save(update_fields=['valor_atual', 'atualizado_em'])
                            result.items_processed += 1

                    result.add_message(
                        f"Contrato {contrato.numero_contrato}: {len(parcelas_pendentes)} parcelas reajustadas"
                    )

            except Exception as e:
                logger.exception("Erro no contrato %s: %s", contrato.numero_contrato, e)
                result.add_error(f"Erro no contrato {contrato.numero_contrato}: {str(e)}")

        result.finish()

    except Exception as e:
        logger.exception("Erro geral em processar_reajustes: %s", e)
        result.add_error(f"Erro geral: {str(e)}")
        result.finish(success=False)

    return result


def _notificacao_ja_enviada_hoje(parcela, motivo_prefixo):
    """
    Verifica se já existe Notificacao registrada para esta parcela hoje
    com o dado motivo (verificado pelo prefixo do assunto).
    Evita duplicatas quando a task roda múltiplas vezes no mesmo dia.
    """
    from notificacoes.models import Notificacao, StatusNotificacao
    from datetime import date
    return Notificacao.objects.filter(
        parcela=parcela,
        assunto__startswith=motivo_prefixo,
        status__in=[StatusNotificacao.PENDENTE, StatusNotificacao.ENVIADA],
        data_agendamento__date=date.today(),
    ).exists()


def _registrar_notificacao(parcela, tipo, destinatario, assunto, mensagem):
    """Cria registro Notificacao e retorna o objeto criado."""
    from notificacoes.models import Notificacao, TipoNotificacao, StatusNotificacao
    return Notificacao.objects.create(
        parcela=parcela,
        tipo=tipo,
        destinatario=destinatario,
        assunto=assunto,
        mensagem=mensagem,
        status=StatusNotificacao.PENDENTE,
    )


def _get_destinatario(comprador, tipo_notificacao):
    """
    Retorna o endereço de destino para o canal informado, ou None se indisponível.
    """
    from notificacoes.models import TipoNotificacao
    if tipo_notificacao == TipoNotificacao.EMAIL:
        return comprador.email if (getattr(comprador, 'notificar_email', True) and comprador.email) else None
    if tipo_notificacao == TipoNotificacao.SMS:
        tel = getattr(comprador, 'celular', None) or getattr(comprador, 'telefone', None)
        return tel or None
    if tipo_notificacao == TipoNotificacao.WHATSAPP:
        tel = getattr(comprador, 'celular', None) or getattr(comprador, 'telefone', None)
        return f"whatsapp:{tel}" if tel else None
    return None


def _enviar_pelo_canal(tipo_notificacao, destinatario, assunto, mensagem):
    """Despacha a mensagem pelo canal correto e propaga exceções."""
    from notificacoes.models import TipoNotificacao
    from notificacoes.services import ServicoEmail, ServicoSMS, ServicoWhatsApp
    if tipo_notificacao == TipoNotificacao.EMAIL:
        ServicoEmail.enviar(destinatario=destinatario, assunto=assunto, mensagem=mensagem)
    elif tipo_notificacao == TipoNotificacao.SMS:
        ServicoSMS.enviar(destinatario=destinatario, mensagem=mensagem)
    elif tipo_notificacao == TipoNotificacao.WHATSAPP:
        ServicoWhatsApp.enviar(destinatario=destinatario, mensagem=mensagem)


def _processar_regra(regra, result):
    """
    N-03: Executa uma RegrarNotificacao: encontra as parcelas na data-alvo e envia.
    """
    from financeiro.models import Parcela
    from notificacoes.models import TipoGatilho
    from datetime import date, timedelta

    hoje = date.today()
    PREFIXO = f'[REGRA-{regra.id}]'

    if regra.tipo_gatilho == TipoGatilho.ANTES_VENCIMENTO:
        data_alvo = hoje + timedelta(days=regra.dias_offset)
        label = f"D-{regra.dias_offset}"
        parcelas = Parcela.objects.filter(
            pago=False, tipo_parcela='NORMAL', data_vencimento=data_alvo,
        ).select_related('contrato', 'contrato__comprador', 'contrato__imobiliaria')
    else:  # APOS_VENCIMENTO
        data_alvo = hoje - timedelta(days=regra.dias_offset)
        label = f"D+{regra.dias_offset}"
        parcelas = Parcela.objects.filter(
            pago=False, tipo_parcela='NORMAL', data_vencimento=data_alvo,
        ).select_related('contrato', 'contrato__comprador', 'contrato__imobiliaria')

    result.add_message(
        f"Regra '{regra.nome}' ({label}): {parcelas.count()} parcelas em {data_alvo}"
    )

    for parcela in parcelas:
        try:
            comprador = parcela.contrato.comprador
            destinatario = _get_destinatario(comprador, regra.tipo_notificacao)
            if not destinatario:
                continue

            if _notificacao_ja_enviada_hoje(parcela, PREFIXO):
                continue

            imob_nome = getattr(parcela.contrato.imobiliaria, 'nome', 'Gestão de Contratos')
            if regra.tipo_gatilho == TipoGatilho.ANTES_VENCIMENTO:
                dias_para_vencer = regra.dias_offset
                assunto = (
                    f"{PREFIXO} Parcela {parcela.numero_parcela} vence em "
                    f"{dias_para_vencer} dia(s) — {data_alvo.strftime('%d/%m/%Y')}"
                )
                mensagem = (
                    f"Olá {comprador.nome},\n\n"
                    f"Lembramos que a parcela {parcela.numero_parcela}/{parcela.contrato.numero_parcelas} "
                    f"do contrato {parcela.contrato.numero_contrato} vence em "
                    f"{data_alvo.strftime('%d/%m/%Y')}.\n\n"
                    f"Valor: R$ {parcela.valor_atual:,.2f}\n\n"
                    f"Por favor, efetue o pagamento até a data de vencimento.\n\n"
                    f"Atenciosamente,\n{imob_nome}"
                )
            else:
                dias_atraso = regra.dias_offset
                assunto = (
                    f"{PREFIXO} Parcela {parcela.numero_parcela} em atraso há "
                    f"{dias_atraso} dia(s) — {data_alvo.strftime('%d/%m/%Y')}"
                )
                mensagem = (
                    f"Olá {comprador.nome},\n\n"
                    f"A parcela {parcela.numero_parcela}/{parcela.contrato.numero_parcelas} "
                    f"do contrato {parcela.contrato.numero_contrato} encontra-se em atraso.\n\n"
                    f"Vencimento: {data_alvo.strftime('%d/%m/%Y')} ({dias_atraso} dia(s) em atraso)\n"
                    f"Valor original: R$ {parcela.valor_atual:,.2f}\n\n"
                    f"Por favor, regularize sua situação para evitar acréscimo de juros e multa.\n\n"
                    f"Atenciosamente,\n{imob_nome}"
                )

            # Se o template customizado estiver configurado, renderizar
            if regra.template:
                ctx = {
                    'NOMECOMPRADOR': comprador.nome,
                    'NUMEROPARCELA': parcela.numero_parcela,
                    'TOTALPARCELAS': parcela.contrato.numero_parcelas,
                    'VALORPARCELA': f"R$ {parcela.valor_atual:,.2f}",
                    'DATAVENCIMENTO': data_alvo.strftime('%d/%m/%Y'),
                    'NUMEROCONTRATO': parcela.contrato.numero_contrato,
                    'NOMEIMOBILIARIA': imob_nome,
                }
                subj_r, body_r, _ = regra.template.renderizar(ctx)
                if subj_r:
                    assunto = f"{PREFIXO} {subj_r}"
                if body_r:
                    mensagem = body_r

            notif = _registrar_notificacao(
                parcela, regra.tipo_notificacao, destinatario, assunto, mensagem
            )
            try:
                _enviar_pelo_canal(regra.tipo_notificacao, destinatario, assunto, mensagem)
                notif.marcar_como_enviada()
                result.items_processed += 1
                result.add_message(
                    f"  ✓ {regra.get_tipo_notificacao_display()} → {destinatario} (parcela {parcela.id})"
                )
            except Exception as e_send:
                notif.marcar_erro(str(e_send))
                result.add_error(f"Erro ao enviar regra {regra.id} parcela {parcela.id}: {e_send}")

        except Exception as e:
            logger.exception("Erro ao processar regra %s parcela %s: %s", regra.id, parcela.id, e)
            result.add_error(f"Erro parcela {parcela.id}: {str(e)}")


def enviar_notificacoes_sync():
    """
    N-01/N-03: Envia notificações de vencimento de forma síncrona.
    Se existirem RegraNotificacao ativas do tipo ANTES, usa a régua configurável.
    Caso contrário, usa o comportamento padrão (D-5 via settings).
    """
    from financeiro.models import Parcela
    from notificacoes.models import TipoNotificacao, StatusNotificacao, RegraNotificacao, TipoGatilho
    from notificacoes.services import ServicoEmail
    from datetime import date, timedelta

    result = TaskResult('enviar_notificacoes_vencimento')

    try:
        regras = list(RegraNotificacao.objects.filter(
            ativo=True, tipo_gatilho=TipoGatilho.ANTES_VENCIMENTO
        ))

        if regras:
            # N-03: régua configurável
            result.add_message(f"N-03: {len(regras)} regra(s) ANTES ativa(s)")
            for regra in regras:
                _processar_regra(regra, result)
        else:
            # Fallback N-01: D-5 padrão
            PREFIXO = '[VENCIMENTO]'
            dias_antecedencia = getattr(settings, 'NOTIFICACAO_DIAS_ANTECEDENCIA', 5)
            hoje = date.today()
            data_limite = hoje + timedelta(days=dias_antecedencia)

            parcelas = Parcela.objects.filter(
                pago=False,
                tipo_parcela='NORMAL',
                data_vencimento__gte=hoje,
                data_vencimento__lte=data_limite,
            ).select_related('contrato', 'contrato__comprador', 'contrato__imobiliaria')

            result.add_message(
                f"N-01 (padrão): {parcelas.count()} parcelas próximas do vencimento (D-{dias_antecedencia})"
            )

            for parcela in parcelas:
                try:
                    comprador = parcela.contrato.comprador
                    if not (getattr(comprador, 'notificar_email', True) and comprador.email):
                        continue
                    if _notificacao_ja_enviada_hoje(parcela, PREFIXO):
                        continue

                    hoje_local = date.today()
                    dias_para_vencer = (parcela.data_vencimento - hoje_local).days
                    assunto = (
                        f"{PREFIXO} Parcela {parcela.numero_parcela} vence em "
                        f"{dias_para_vencer} dia(s) — {parcela.data_vencimento.strftime('%d/%m/%Y')}"
                    )
                    imob_nome = getattr(parcela.contrato.imobiliaria, 'nome', 'Gestão de Contratos')
                    mensagem = (
                        f"Olá {comprador.nome},\n\n"
                        f"Lembramos que a parcela {parcela.numero_parcela}/{parcela.contrato.numero_parcelas} "
                        f"do contrato {parcela.contrato.numero_contrato} vence em "
                        f"{parcela.data_vencimento.strftime('%d/%m/%Y')}.\n\n"
                        f"Valor: R$ {parcela.valor_atual:,.2f}\n\n"
                        f"Por favor, efetue o pagamento até a data de vencimento.\n\n"
                        f"Atenciosamente,\n{imob_nome}"
                    )

                    notif = _registrar_notificacao(
                        parcela, TipoNotificacao.EMAIL, comprador.email, assunto, mensagem
                    )
                    try:
                        ServicoEmail.enviar(
                            destinatario=comprador.email, assunto=assunto, mensagem=mensagem,
                        )
                        notif.marcar_como_enviada()
                        result.items_processed += 1
                        result.add_message(f"Vencimento enviado → {comprador.email} (parcela {parcela.id})")
                    except Exception as e_send:
                        notif.marcar_erro(str(e_send))
                        result.add_error(f"Erro ao enviar vencimento parcela {parcela.id}: {e_send}")

                except Exception as e:
                    logger.exception("Erro ao processar parcela %s: %s", parcela.id, e)
                    result.add_error(f"Erro parcela {parcela.id}: {str(e)}")

        result.finish()

    except Exception as e:
        logger.exception("Erro geral em enviar_notificacoes_sync: %s", e)
        result.add_error(f"Erro geral: {str(e)}")
        result.finish(success=False)

    return result


def enviar_inadimplentes_sync():
    """
    N-02/N-03: Envia notificações de inadimplência de forma síncrona.
    Se existirem RegraNotificacao ativas do tipo APOS, usa a régua configurável.
    Caso contrário, usa o comportamento padrão (>= D+3 via settings).
    """
    from financeiro.models import Parcela
    from notificacoes.models import TipoNotificacao, StatusNotificacao, RegraNotificacao, TipoGatilho
    from notificacoes.services import ServicoEmail
    from datetime import date, timedelta

    result = TaskResult('enviar_inadimplentes')

    try:
        regras = list(RegraNotificacao.objects.filter(
            ativo=True, tipo_gatilho=TipoGatilho.APOS_VENCIMENTO
        ))

        if regras:
            # N-03: régua configurável
            result.add_message(f"N-03: {len(regras)} regra(s) APÓS ativa(s)")
            for regra in regras:
                _processar_regra(regra, result)
        else:
            # Fallback N-02: >= D+3 padrão
            PREFIXO = '[INADIMPLENCIA]'
            dias_carencia = getattr(settings, 'NOTIFICACAO_DIAS_INADIMPLENCIA', 3)
            hoje = date.today()
            data_corte = hoje - timedelta(days=dias_carencia)

            parcelas = Parcela.objects.filter(
                pago=False,
                tipo_parcela='NORMAL',
                data_vencimento__lte=data_corte,
            ).select_related('contrato', 'contrato__comprador', 'contrato__imobiliaria')

            result.add_message(
                f"N-02 (padrão): {parcelas.count()} parcelas em atraso (>= D+{dias_carencia})"
            )

            for parcela in parcelas:
                try:
                    comprador = parcela.contrato.comprador
                    if not (getattr(comprador, 'notificar_email', True) and comprador.email):
                        continue
                    if _notificacao_ja_enviada_hoje(parcela, PREFIXO):
                        continue

                    dias_atraso = (hoje - parcela.data_vencimento).days
                    assunto = (
                        f"{PREFIXO} Parcela {parcela.numero_parcela} em atraso há {dias_atraso} dia(s) "
                        f"— {parcela.data_vencimento.strftime('%d/%m/%Y')}"
                    )
                    imob_nome = getattr(parcela.contrato.imobiliaria, 'nome', 'Gestão de Contratos')
                    mensagem = (
                        f"Olá {comprador.nome},\n\n"
                        f"Verificamos que a parcela {parcela.numero_parcela}/{parcela.contrato.numero_parcelas} "
                        f"do contrato {parcela.contrato.numero_contrato} encontra-se em atraso.\n\n"
                        f"Vencimento: {parcela.data_vencimento.strftime('%d/%m/%Y')} "
                        f"({dias_atraso} dia(s) em atraso)\n"
                        f"Valor original: R$ {parcela.valor_atual:,.2f}\n\n"
                        f"Por favor, regularize sua situação o quanto antes para evitar "
                        f"acréscimo de juros e multa.\n\n"
                        f"Em caso de dúvidas, entre em contato conosco.\n\n"
                        f"Atenciosamente,\n{imob_nome}"
                    )

                    notif = _registrar_notificacao(
                        parcela, TipoNotificacao.EMAIL, comprador.email, assunto, mensagem
                    )
                    try:
                        ServicoEmail.enviar(
                            destinatario=comprador.email, assunto=assunto, mensagem=mensagem,
                        )
                        notif.marcar_como_enviada()
                        result.items_processed += 1
                        result.add_message(
                            f"Inadimplência enviada → {comprador.email} (parcela {parcela.id}, {dias_atraso}d)"
                        )
                    except Exception as e_send:
                        notif.marcar_erro(str(e_send))
                        result.add_error(f"Erro ao enviar inadimplência parcela {parcela.id}: {e_send}")

                except Exception as e:
                    logger.exception("Erro ao processar parcela inadimplente %s: %s", parcela.id, e)
                    result.add_error(f"Erro parcela {parcela.id}: {str(e)}")

        result.finish()

    except Exception as e:
        logger.exception("Erro geral em enviar_inadimplentes_sync: %s", e)
        result.add_error(f"Erro geral: {str(e)}")
        result.finish(success=False)

    return result


def atualizar_status_parcelas_sync():
    """
    Verifica parcelas vencidas e não pagas.
    Parcela usa pago=True/False — não há campo status a actualizar.
    Esta tarefa apenas emite um relatório de contagem.
    """
    from financeiro.models import Parcela
    from datetime import date

    result = TaskResult('atualizar_status_parcelas')

    try:
        hoje = date.today()

        # Contar parcelas vencidas e não pagas
        count = Parcela.objects.filter(
            pago=False,
            data_vencimento__lt=hoje
        ).count()

        result.items_processed = count
        result.add_message(f"{count} parcelas em atraso (vencidas e não pagas)")
        result.finish()

    except Exception as e:
        logger.exception("Erro em atualizar_status_parcelas: %s", e)
        result.add_error(f"Erro: {str(e)}")
        result.finish(success=False)

    return result


# =============================================================================
# VIEWS PARA EXECUÇÃO DE TAREFAS VIA HTTP
# =============================================================================

@require_http_methods(["POST"])
@task_auth_required
def task_processar_reajustes(request):
    """Endpoint para processar reajustes."""
    result = processar_reajustes_sync()
    status_code = 200 if result.success else 500
    return JsonResponse(result.to_dict(), status=status_code)


@require_http_methods(["POST"])
@task_auth_required
def task_enviar_notificacoes(request):
    """Endpoint para enviar notificações de vencimento (N-01: D-5)."""
    result = enviar_notificacoes_sync()
    status_code = 200 if result.success else 500
    return JsonResponse(result.to_dict(), status=status_code)


@require_http_methods(["POST"])
@task_auth_required
def task_enviar_inadimplentes(request):
    """Endpoint para enviar notificações de inadimplência (N-02: D+3)."""
    result = enviar_inadimplentes_sync()
    status_code = 200 if result.success else 500
    return JsonResponse(result.to_dict(), status=status_code)


@require_http_methods(["POST"])
@task_auth_required
def task_atualizar_parcelas(request):
    """Endpoint para atualizar status de parcelas."""
    result = atualizar_status_parcelas_sync()
    status_code = 200 if result.success else 500
    return JsonResponse(result.to_dict(), status=status_code)


@require_http_methods(["POST"])
@task_auth_required
def task_run_all(request):
    """
    Executa todas as tarefas agendadas.
    Ideal para cron jobs externos.
    """
    results = []

    # 1. Atualizar status de parcelas
    results.append(atualizar_status_parcelas_sync().to_dict())

    # 2. Processar reajustes
    results.append(processar_reajustes_sync().to_dict())

    # 3. Enviar notificações de vencimento (N-01)
    results.append(enviar_notificacoes_sync().to_dict())

    # 4. Enviar notificações de inadimplência (N-02)
    results.append(enviar_inadimplentes_sync().to_dict())

    all_success = all(r['success'] for r in results)

    return JsonResponse({
        'status': 'success' if all_success else 'partial_failure',
        'executed_at': datetime.now().isoformat(),
        'tasks': results
    }, status=200 if all_success else 207)


@require_http_methods(["GET"])
def task_status(request):
    """
    Retorna status das tarefas (não requer autenticação).
    Útil para verificar se o sistema de tarefas está configurado.
    """
    return JsonResponse({
        'tasks_enabled': bool(TASK_TOKEN),
        'available_tasks': [
            {
                'name': 'processar_reajustes',
                'endpoint': '/api/tasks/processar-reajustes/',
                'description': 'Processa reajustes pendentes de contratos'
            },
            {
                'name': 'enviar_notificacoes',
                'endpoint': '/api/tasks/enviar-notificacoes/',
                'description': 'Envia notificações de vencimento'
            },
            {
                'name': 'atualizar_parcelas',
                'endpoint': '/api/tasks/atualizar-parcelas/',
                'description': 'Atualiza status de parcelas vencidas'
            },
            {
                'name': 'run_all',
                'endpoint': '/api/tasks/run-all/',
                'description': 'Executa todas as tarefas'
            }
        ],
        'cron_setup': {
            'recommended_service': 'cron-job.org (gratuito)',
            'schedule': 'Diariamente às 08:00',
            'endpoint': '/api/tasks/run-all/',
            'method': 'POST',
            'header': 'X-Task-Token: <seu-token>'
        }
    })
