"""
Rename do modo offline: `brcobranca` → `pycobranca`.

O motor offline do gateway deixou de ser o BRCobrança (Ruby) e passou a ser o
pyCobrança (Python). Esta migration converte os dados já gravados:

  • core.ContaBancaria.provider
  • core.ParametroSistema.grupo  (grupo de configuração do motor offline)

A conversão é reversível (pycobranca → brcobranca) para permitir rollback.
"""
from django.db import migrations

LEGADO = 'brcobranca'
NOVO = 'pycobranca'


def para_pycobranca(apps, schema_editor):
    ContaBancaria = apps.get_model('core', 'ContaBancaria')
    ParametroSistema = apps.get_model('core', 'ParametroSistema')
    ContaBancaria.objects.filter(provider=LEGADO).update(provider=NOVO)
    # Conta sem provider definido também passa a apontar explicitamente para o
    # modo offline (o default do campo).
    ContaBancaria.objects.filter(provider='').update(provider=NOVO)
    ParametroSistema.objects.filter(grupo=LEGADO).update(grupo=NOVO)


def para_brcobranca(apps, schema_editor):
    ContaBancaria = apps.get_model('core', 'ContaBancaria')
    ParametroSistema = apps.get_model('core', 'ParametroSistema')
    ContaBancaria.objects.filter(provider=NOVO).update(provider=LEGADO)
    ParametroSistema.objects.filter(grupo=NOVO).update(grupo=LEGADO)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0026_alter_contabancaria_provider_and_more'),
    ]

    operations = [
        migrations.RunPython(para_pycobranca, para_brcobranca),
    ]
