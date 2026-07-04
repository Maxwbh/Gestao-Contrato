# Adiciona numero_indice ao IndiceReajuste para cálculo exato via IBGE/FGV.
# Fórmula: % Acumulado = C(MesFinal) / C(MesInicial) - 1
# Campo nullable — cálculos existentes via variação mensal continuam funcionando.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contratos", "0009_contrato_testemunhas_escritura"),
    ]

    operations = [
        migrations.AddField(
            model_name="indicereajuste",
            name="numero_indice",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text=(
                    "Número índice acumulado publicado pelo IBGE (IPCA) ou FGV (IGPM). "
                    "Permite cálculo exato: acumulado = C(fim) / C(mês anterior ao início) − 1. "
                    "Quando disponível, tem prioridade sobre o produto das variações mensais."
                ),
                max_digits=12,
                null=True,
                verbose_name="Número Índice (IBGE/FGV)",
            ),
        ),
    ]
