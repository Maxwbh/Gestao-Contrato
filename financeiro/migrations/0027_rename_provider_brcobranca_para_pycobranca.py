"""
Rename do modo offline: `brcobranca` → `pycobranca` (dados do financeiro).

Converte `Parcela.provider` e `RecorrenciaPix.provider`. Atenção: em Parcela o
campo guarda o provider QUE EMITIU o boleto e fica **em branco** quando a
emissão saiu pelo fluxo CNAB antigo — esse branco é significativo (é o corte de
elegibilidade do CNAB) e por isso NÃO é preenchido aqui; só o valor legado
explícito é convertido.
"""
from django.db import migrations

LEGADO = 'brcobranca'
NOVO = 'pycobranca'


def para_pycobranca(apps, schema_editor):
    Parcela = apps.get_model('financeiro', 'Parcela')
    RecorrenciaPix = apps.get_model('financeiro', 'RecorrenciaPix')
    Parcela.objects.filter(provider=LEGADO).update(provider=NOVO)
    RecorrenciaPix.objects.filter(provider=LEGADO).update(provider=NOVO)


def para_brcobranca(apps, schema_editor):
    Parcela = apps.get_model('financeiro', 'Parcela')
    RecorrenciaPix = apps.get_model('financeiro', 'RecorrenciaPix')
    Parcela.objects.filter(provider=NOVO).update(provider=LEGADO)
    RecorrenciaPix.objects.filter(provider=NOVO).update(provider=LEGADO)


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0026_alter_parcela_provider_alter_recorrenciapix_provider'),
    ]

    operations = [
        migrations.RunPython(para_pycobranca, para_brcobranca),
    ]
