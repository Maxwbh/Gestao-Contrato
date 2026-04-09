"""
Migration 0005: Template Unificado

Unifica os templates de notificação por canal separado em um único registro
por (codigo, imobiliaria) com campos distintos para cada canal:
  - assunto + corpo_html → E-mail
  - corpo               → SMS (máx. 255 caracteres)
  - corpo_whatsapp      → WhatsApp (novo campo)

O campo `tipo` passa a ser nullable (legado).
O unique_together muda de (codigo, imobiliaria, tipo) para (codigo, imobiliaria).
"""

from django.db import migrations, models


def merge_templates(apps, schema_editor):
    """Mescla registros EMAIL/SMS/WHATSAPP separados em um único por (codigo, imobiliaria)."""
    TemplateNotificacao = apps.get_model('notificacoes', 'TemplateNotificacao')

    all_templates = list(TemplateNotificacao.objects.all())

    from collections import defaultdict
    groups = defaultdict(list)
    for t in all_templates:
        key = (t.codigo, t.imobiliaria_id)
        groups[key].append(t)

    for (codigo, imob_id), group in groups.items():
        if len(group) <= 1:
            continue  # Nada a mesclar

        # Eleger o registro principal (preferir EMAIL)
        primary = next((t for t in group if t.tipo == 'EMAIL'), group[0])

        for t in group:
            if t.pk == primary.pk:
                continue
            # Copiar conteúdo SMS para o campo `corpo` do principal (se vazio)
            if t.tipo == 'SMS' and not primary.corpo:
                primary.corpo = t.corpo
            # Copiar conteúdo WhatsApp para `corpo_whatsapp` (se vazio)
            elif t.tipo == 'WHATSAPP' and not primary.corpo_whatsapp:
                primary.corpo_whatsapp = t.corpo
            t.delete()

        primary.save()


class Migration(migrations.Migration):

    dependencies = [
        ('notificacoes', '0004_add_whatsapp_providers'),
    ]

    operations = [
        # 1. Adicionar campo corpo_whatsapp
        migrations.AddField(
            model_name='templatenotificacao',
            name='corpo_whatsapp',
            field=models.TextField(blank=True, default='', verbose_name='Corpo WhatsApp'),
            preserve_default=False,
        ),

        # 2. Tornar `tipo` nullable
        migrations.AlterField(
            model_name='templatenotificacao',
            name='tipo',
            field=models.CharField(
                blank=True,
                max_length=20,
                null=True,
                choices=[('EMAIL', 'E-mail'), ('SMS', 'SMS'), ('WHATSAPP', 'WhatsApp')],
                verbose_name='Canal de Envio',
            ),
        ),

        # 3. Tornar `corpo` nullable/blank para templates só de email
        migrations.AlterField(
            model_name='templatenotificacao',
            name='corpo',
            field=models.TextField(
                blank=True,
                default='',
                verbose_name='Corpo SMS',
            ),
            preserve_default=False,
        ),

        # 4. Remover unique_together antigo
        migrations.AlterUniqueTogether(
            name='templatenotificacao',
            unique_together=set(),
        ),

        # 5. Migração de dados: mesclar registros separados por canal
        migrations.RunPython(merge_templates, migrations.RunPython.noop),

        # 6. Adicionar novo unique_together
        migrations.AlterUniqueTogether(
            name='templatenotificacao',
            unique_together={('codigo', 'imobiliaria')},
        ),
    ]
