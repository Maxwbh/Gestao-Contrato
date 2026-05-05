"""
Management command: cria ou atualiza os templates HTML padrão de relatório.

Uso:
    python manage.py criar_templates_relatorio             # cria apenas se não existir
    python manage.py criar_templates_relatorio --forcar   # sobrescreve corpo_html existente
"""
from django.core.management.base import BaseCommand

from notificacoes.relatorio_templates import (
    HTML_SEMANAL, HTML_MENSAL, ASSUNTO_SEMANAL, ASSUNTO_MENSAL,
)

TEMPLATES = [
    # Códigos legados (fallback)
    ('RELATORIO_SEMANAL', 'Relatório Semanal (padrão)', ASSUNTO_SEMANAL, HTML_SEMANAL),
    ('RELATORIO_MENSAL', 'Relatório Mensal Consolidado (padrão)', ASSUNTO_MENSAL, HTML_MENSAL),
    # Códigos primários usados pelas APIs de tasks
    ('gestao-relatorio-semanal', 'gestao-relatorio-semanal', ASSUNTO_SEMANAL, HTML_SEMANAL),
    ('gestao-relatorio-mensal', 'gestao-relatorio-mensal', ASSUNTO_MENSAL, HTML_MENSAL),
]


class Command(BaseCommand):
    help = 'Cria ou atualiza os templates HTML padrão de Relatório Semanal e Mensal.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--forcar',
            action='store_true',
            help='Sobrescreve corpo_html mesmo que o template já exista.',
        )

    def handle(self, *args, **options):
        from notificacoes.models import TemplateNotificacao

        forcar = options['forcar']
        criados = 0
        atualizados = 0

        for codigo, nome, assunto, corpo_html in TEMPLATES:
            obj, criado = TemplateNotificacao.objects.get_or_create(
                codigo=codigo,
                imobiliaria=None,
                defaults=dict(nome=nome, assunto=assunto, corpo_html=corpo_html, ativo=True),
            )
            if criado:
                criados += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ Criado: {nome}'))
            elif forcar:
                obj.corpo_html = corpo_html
                obj.assunto = assunto
                obj.save(update_fields=['corpo_html', 'assunto'])
                atualizados += 1
                self.stdout.write(self.style.WARNING(f'  ↻ Atualizado: {nome}'))
            else:
                self.stdout.write(
                    f'  — Já existe (use --forcar para sobrescrever): {nome}'
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nConcluído: {criados} criado(s), {atualizados} atualizado(s).'
            )
        )
