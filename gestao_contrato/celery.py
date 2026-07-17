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
    # ── Boleto-API: conciliação e agendadores (Fases 7–8) ──────────────────
    'boleto-api-polling-sicoob': {
        'task': 'financeiro.tasks.polling_boletos_sicoob',
        'schedule': crontab(minute=15),  # a cada hora (Sicoob não tem webhook de boleto)
    },
    'boleto-api-conciliar-pix': {
        'task': 'financeiro.tasks.conciliar_pix_recebidos',
        'schedule': crontab(hour=6, minute=0),  # diário — rede de segurança do webhook
    },
    'boleto-api-reprocessar-cip': {
        'task': 'financeiro.tasks.reprocessar_fila_cip',
        'schedule': crontab(minute='*/30'),  # CIP libera em minutos/horas
    },
    'boleto-api-pix-automatico-d2': {
        'task': 'financeiro.tasks.agendar_cobrancas_pix_automatico',
        'schedule': crontab(hour=7, minute=0),  # diário — agenda cobranças D-2
    },
    'boleto-api-pix-automatico-retentativa': {
        'task': 'financeiro.tasks.retentar_cobrancas_pix_automatico',
        'schedule': crontab(hour=9, minute=0),  # diário — retenta PA vencido não pago
    },
}
