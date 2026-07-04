"""
Data migration: cria templates com códigos gestao-relatorio-semanal e
gestao-relatorio-mensal, usados pela API de tasks como lookup primário.
"""
from django.db import migrations

from notificacoes.relatorio_templates import (
    HTML_SEMANAL, HTML_MENSAL, ASSUNTO_SEMANAL, ASSUNTO_MENSAL,
)


def criar_templates(apps, schema_editor):
    TemplateNotificacao = apps.get_model('notificacoes', 'TemplateNotificacao')

    TemplateNotificacao.objects.get_or_create(
        codigo='gestao-relatorio-semanal',
        imobiliaria=None,
        defaults=dict(
            nome='gestao-relatorio-semanal',
            assunto=ASSUNTO_SEMANAL,
            corpo_html=HTML_SEMANAL,
            ativo=True,
        ),
    )

    TemplateNotificacao.objects.get_or_create(
        codigo='gestao-relatorio-mensal',
        imobiliaria=None,
        defaults=dict(
            nome='gestao-relatorio-mensal',
            assunto=ASSUNTO_MENSAL,
            corpo_html=HTML_MENSAL,
            ativo=True,
        ),
    )


def remover_templates(apps, schema_editor):
    TemplateNotificacao = apps.get_model('notificacoes', 'TemplateNotificacao')
    TemplateNotificacao.objects.filter(
        codigo__in=['gestao-relatorio-semanal', 'gestao-relatorio-mensal'],
        imobiliaria=None,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('notificacoes', '0011_add_gestao_relatorio_template_choices'),
    ]

    operations = [
        migrations.RunPython(criar_templates, remover_templates),
    ]
