import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_contrato.settings')

app = Celery('gestao_contrato')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


# Configuração de tarefas periódicas
app.conf.beat_schedule = {
    'processar-reajustes-diario': {
        'task': 'financeiro.tasks.processar_reajustes_pendentes',
        'schedule': crontab(hour=1, minute=0),  # Executa diariamente à 1h
    },
    'enviar-notificacoes-vencimento': {
        'task': 'notificacoes.tasks.enviar_notificacoes_vencimento',
        'schedule': crontab(hour=8, minute=0),  # Executa diariamente às 8h
    },
}
