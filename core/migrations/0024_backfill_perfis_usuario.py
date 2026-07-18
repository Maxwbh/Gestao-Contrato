"""
HU-28 — cria PerfilUsuario para os usuários já existentes.

superuser/staff → ADMIN (mantêm o poder de gerenciar usuários);
demais → COMUM. Compradores do portal também recebem perfil COMUM.
"""
from django.db import migrations


def criar_perfis(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    PerfilUsuario = apps.get_model('core', 'PerfilUsuario')
    for u in User.objects.all().iterator():
        papel = 'ADMIN' if (u.is_superuser or u.is_staff) else 'COMUM'
        PerfilUsuario.objects.get_or_create(usuario=u, defaults={'papel': papel})


def remover_perfis(apps, schema_editor):
    apps.get_model('core', 'PerfilUsuario').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_alter_logauditoria_acao_perfilusuario'),
    ]

    operations = [
        migrations.RunPython(criar_perfis, remover_perfis),
    ]
