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
        logger.error(f"[{self.task_name}] {error}")

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
    from contratos.models import Contrato
    from financeiro.models import Parcela
    from contratos.services import IndiceEconomicoService, ReajusteService
    from decimal import Decimal
    from datetime import date

    result = TaskResult('processar_reajustes')

    try:
        hoje = date.today()

        # Buscar contratos que precisam de reajuste
        contratos = Contrato.objects.filter(
            ativo=True,
            tipo_reajuste__in=['IPCA', 'IGP-M', 'SELIC']
        ).select_related('imovel', 'comprador')

        result.add_message(f"Verificando {contratos.count()} contratos ativos")

        for contrato in contratos:
            try:
                # Verificar se é mês de reajuste
                meses_desde_inicio = (
                    (hoje.year - contrato.data_contrato.year) * 12 +
                    (hoje.month - contrato.data_contrato.month)
                )

                if meses_desde_inicio > 0 and meses_desde_inicio % contrato.periodicidade_reajuste == 0:
                    # Buscar índice atual
                    indice = IndiceEconomicoService.get_indice_atual(contrato.tipo_reajuste)

                    if indice:
                        # Aplicar reajuste às parcelas pendentes
                        parcelas_pendentes = contrato.parcelas.filter(
                            status='PENDENTE',
                            data_vencimento__gte=hoje
                        )

                        for parcela in parcelas_pendentes:
                            percentual = Decimal(str(indice.get('valor', 0)))
                            novo_valor = ReajusteService.calcular_reajuste(
                                parcela.valor_atual, percentual
                            )
                            parcela.valor_atual = novo_valor
                            parcela.save(update_fields=['valor_atual', 'atualizado_em'])
                            result.items_processed += 1

                        result.add_message(
                            f"Contrato {contrato.numero}: {parcelas_pendentes.count()} parcelas reajustadas"
                        )

            except Exception as e:
                result.add_error(f"Erro no contrato {contrato.numero}: {str(e)}")

        result.finish()

    except Exception as e:
        result.add_error(f"Erro geral: {str(e)}")
        result.finish(success=False)

    return result


def enviar_notificacoes_sync():
    """
    Envia notificações de vencimento de forma síncrona.
    Alternativa à task Celery para o Free tier.
    """
    from financeiro.models import Parcela
    from notificacoes.services import ServicoEmail
    from datetime import date, timedelta

    result = TaskResult('enviar_notificacoes')

    try:
        dias_antecedencia = getattr(settings, 'NOTIFICACAO_DIAS_ANTECEDENCIA', 5)
        data_limite = date.today() + timedelta(days=dias_antecedencia)

        # Buscar parcelas próximas do vencimento
        parcelas = Parcela.objects.filter(
            status='PENDENTE',
            data_vencimento__lte=data_limite,
            data_vencimento__gte=date.today()
        ).select_related(
            'contrato',
            'contrato__comprador',
            'contrato__imovel'
        )

        result.add_message(f"Encontradas {parcelas.count()} parcelas próximas do vencimento")

        for parcela in parcelas:
            try:
                comprador = parcela.contrato.comprador

                # Verificar preferências de notificação
                if comprador.notificar_email and comprador.email:
                    # Criar mensagem
                    assunto = f"Lembrete: Parcela {parcela.numero_parcela} vence em {parcela.data_vencimento.strftime('%d/%m/%Y')}"
                    mensagem = f"""
Olá {comprador.nome},

Lembramos que a parcela {parcela.numero_parcela} do seu contrato {parcela.contrato.numero}
vence em {parcela.data_vencimento.strftime('%d/%m/%Y')}.

Valor: R$ {parcela.valor_atual:,.2f}

Atenciosamente,
{parcela.contrato.imovel.imobiliaria.nome}
                    """.strip()

                    # Enviar email
                    ServicoEmail.enviar(
                        destinatario=comprador.email,
                        assunto=assunto,
                        mensagem=mensagem
                    )
                    result.items_processed += 1
                    result.add_message(f"Notificação enviada para {comprador.email}")

            except Exception as e:
                result.add_error(f"Erro ao notificar parcela {parcela.id}: {str(e)}")

        result.finish()

    except Exception as e:
        result.add_error(f"Erro geral: {str(e)}")
        result.finish(success=False)

    return result


def atualizar_status_parcelas_sync():
    """
    Atualiza status de parcelas vencidas.
    """
    from financeiro.models import Parcela
    from datetime import date

    result = TaskResult('atualizar_status_parcelas')

    try:
        hoje = date.today()

        # Marcar parcelas vencidas como ATRASADA
        parcelas_vencidas = Parcela.objects.filter(
            status='PENDENTE',
            data_vencimento__lt=hoje
        )

        count = parcelas_vencidas.update(status='ATRASADA')
        result.items_processed = count
        result.add_message(f"{count} parcelas marcadas como atrasadas")
        result.finish()

    except Exception as e:
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
    """Endpoint para enviar notificações."""
    result = enviar_notificacoes_sync()
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

    # 3. Enviar notificações
    results.append(enviar_notificacoes_sync().to_dict())

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
