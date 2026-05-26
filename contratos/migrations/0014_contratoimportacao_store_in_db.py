from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Substitui FileField (disco) por BinaryField + CharField (banco de dados).
    Render Free Tier não tem disco persistente — bytes do arquivo ficam no PostgreSQL.
    """

    dependencies = [
        ('contratos', '0013_add_contrato_importacao'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='contratoimportacao',
            name='arquivo',
        ),
        migrations.AddField(
            model_name='contratoimportacao',
            name='arquivo_bytes',
            field=models.BinaryField(
                blank=True,
                null=True,
                verbose_name='Arquivo (bytes)',
                help_text='Bytes do primeiro arquivo enviado — armazenado em BD (sem dependência de disco)',
            ),
        ),
        migrations.AddField(
            model_name='contratoimportacao',
            name='arquivo_nome',
            field=models.CharField(
                blank=True,
                max_length=255,
                verbose_name='Nome do arquivo original',
            ),
        ),
    ]
