# Generated migration for contratos app
# Includes all contract models with 360 months support and intermediary payments

from django.db import migrations, models
import django.core.validators
import django.utils.timezone
from decimal import Decimal


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
        ('financeiro', '0001_initial'),
    ]

    operations = [
        # IndiceReajuste - Economic indices for monetary correction
        migrations.CreateModel(
            name='IndiceReajuste',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tipo_indice', models.CharField(
                    choices=[
                        ('IPCA', 'IPCA - Índice de Preços ao Consumidor Amplo'),
                        ('IGPM', 'IGP-M - Índice Geral de Preços do Mercado'),
                        ('INCC', 'INCC - Índice Nacional de Custo da Construção'),
                        ('IGPDI', 'IGP-DI - Índice Geral de Preços - Disponibilidade Interna'),
                        ('INPC', 'INPC - Índice Nacional de Preços ao Consumidor'),
                        ('TR', 'TR - Taxa Referencial'),
                        ('SELIC', 'SELIC - Taxa Básica de Juros'),
                    ],
                    max_length=10,
                    verbose_name='Tipo de Índice'
                )),
                ('ano', models.PositiveIntegerField(
                    validators=[
                        django.core.validators.MinValueValidator(1990),
                        django.core.validators.MaxValueValidator(2100)
                    ],
                    verbose_name='Ano'
                )),
                ('mes', models.PositiveIntegerField(
                    validators=[
                        django.core.validators.MinValueValidator(1),
                        django.core.validators.MaxValueValidator(12)
                    ],
                    verbose_name='Mês'
                )),
                ('valor', models.DecimalField(
                    decimal_places=4,
                    max_digits=8,
                    verbose_name='Valor (%)',
                    help_text='Valor percentual do índice no mês'
                )),
                ('valor_acumulado_ano', models.DecimalField(
                    blank=True,
                    decimal_places=4,
                    max_digits=10,
                    null=True,
                    verbose_name='Acumulado no Ano (%)'
                )),
                ('valor_acumulado_12m', models.DecimalField(
                    blank=True,
                    decimal_places=4,
                    max_digits=10,
                    null=True,
                    verbose_name='Acumulado 12 meses (%)'
                )),
                ('fonte', models.CharField(
                    blank=True,
                    default='',
                    max_length=100,
                    verbose_name='Fonte'
                )),
                ('data_importacao', models.DateTimeField(
                    blank=True,
                    null=True,
                    verbose_name='Data de Importação'
                )),
            ],
            options={
                'verbose_name': 'Índice de Reajuste',
                'verbose_name_plural': 'Índices de Reajuste',
                'ordering': ['-ano', '-mes', 'tipo_indice'],
                'unique_together': {('tipo_indice', 'ano', 'mes')},
            },
        ),

        # Contrato - Main contract model (supports up to 360 months)
        migrations.CreateModel(
            name='Contrato',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('numero_contrato', models.CharField(
                    max_length=50,
                    unique=True,
                    verbose_name='Número do Contrato'
                )),
                ('data_contrato', models.DateField(
                    default=django.utils.timezone.now,
                    verbose_name='Data do Contrato'
                )),
                ('data_primeiro_vencimento', models.DateField(
                    verbose_name='Data do Primeiro Vencimento'
                )),
                ('valor_total', models.DecimalField(
                    decimal_places=2,
                    max_digits=12,
                    validators=[django.core.validators.MinValueValidator(Decimal('0.01'))],
                    verbose_name='Valor Total do Contrato'
                )),
                ('valor_entrada', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('0.00'),
                    max_digits=12,
                    validators=[django.core.validators.MinValueValidator(Decimal('0.00'))],
                    verbose_name='Valor de Entrada'
                )),
                ('numero_parcelas', models.PositiveIntegerField(
                    validators=[
                        django.core.validators.MinValueValidator(1),
                        django.core.validators.MaxValueValidator(360)
                    ],
                    verbose_name='Número de Parcelas',
                    help_text='Quantidade total de parcelas do contrato (máximo 360 meses = 30 anos)'
                )),
                ('dia_vencimento', models.PositiveIntegerField(
                    validators=[
                        django.core.validators.MinValueValidator(1),
                        django.core.validators.MaxValueValidator(31)
                    ],
                    verbose_name='Dia de Vencimento'
                )),
                ('quantidade_intermediarias', models.PositiveIntegerField(
                    default=0,
                    validators=[
                        django.core.validators.MinValueValidator(0),
                        django.core.validators.MaxValueValidator(30)
                    ],
                    verbose_name='Quantidade de Intermediárias',
                    help_text='Quantidade de prestações intermediárias (máximo 30)'
                )),
                ('ciclo_reajuste_atual', models.PositiveIntegerField(
                    default=1,
                    verbose_name='Ciclo de Reajuste Atual'
                )),
                ('ultimo_mes_boleto_gerado', models.PositiveIntegerField(
                    default=0,
                    verbose_name='Último Mês com Boleto Gerado'
                )),
                ('bloqueio_boleto_reajuste', models.BooleanField(
                    default=False,
                    verbose_name='Boleto Bloqueado por Reajuste'
                )),
                ('percentual_juros_mora', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('1.00'),
                    max_digits=5,
                    verbose_name='Juros de Mora (%)'
                )),
                ('percentual_multa', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('2.00'),
                    max_digits=5,
                    verbose_name='Multa (%)'
                )),
                ('tipo_correcao', models.CharField(
                    choices=[
                        ('IPCA', 'IPCA - Índice de Preços ao Consumidor Amplo'),
                        ('IGPM', 'IGP-M - Índice Geral de Preços do Mercado'),
                        ('INCC', 'INCC - Índice Nacional de Custo da Construção'),
                        ('IGPDI', 'IGP-DI - Índice Geral de Preços - Disponibilidade Interna'),
                        ('INPC', 'INPC - Índice Nacional de Preços ao Consumidor'),
                        ('TR', 'TR - Taxa Referencial'),
                        ('SELIC', 'SELIC - Taxa Básica de Juros'),
                        ('FIXO', 'Valor Fixo (sem correção)'),
                    ],
                    default='IPCA',
                    max_length=10,
                    verbose_name='Tipo de Correção'
                )),
                ('prazo_reajuste_meses', models.PositiveIntegerField(
                    default=12,
                    validators=[
                        django.core.validators.MinValueValidator(1),
                        django.core.validators.MaxValueValidator(120)
                    ],
                    verbose_name='Prazo para Reajuste (meses)'
                )),
                ('data_ultimo_reajuste', models.DateField(
                    blank=True,
                    null=True,
                    verbose_name='Data do Último Reajuste'
                )),
                ('status', models.CharField(
                    choices=[
                        ('ATIVO', 'Ativo'),
                        ('QUITADO', 'Quitado'),
                        ('CANCELADO', 'Cancelado'),
                        ('SUSPENSO', 'Suspenso'),
                    ],
                    default='ATIVO',
                    max_length=20,
                    verbose_name='Status'
                )),
                ('usar_config_boleto_imobiliaria', models.BooleanField(
                    default=True,
                    verbose_name='Usar Configurações da Imobiliária'
                )),
                ('valor_financiado', models.DecimalField(
                    decimal_places=2,
                    editable=False,
                    max_digits=12,
                    verbose_name='Valor Financiado'
                )),
                ('valor_parcela_original', models.DecimalField(
                    decimal_places=2,
                    editable=False,
                    max_digits=12,
                    verbose_name='Valor Original da Parcela'
                )),
                ('observacoes', models.TextField(
                    blank=True,
                    verbose_name='Observações'
                )),
                # Foreign Keys
                ('imovel', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='contratos',
                    to='core.imovel',
                    verbose_name='Imóvel'
                )),
                ('comprador', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='contratos',
                    to='core.comprador',
                    verbose_name='Comprador'
                )),
                ('imobiliaria', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='contratos',
                    to='core.imobiliaria',
                    verbose_name='Imobiliária/Beneficiário'
                )),
                ('conta_bancaria_padrao', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='contratos',
                    to='core.contabancaria',
                    verbose_name='Conta Bancária Padrão'
                )),
            ],
            options={
                'verbose_name': 'Contrato',
                'verbose_name_plural': 'Contratos',
                'ordering': ['-data_contrato', 'numero_contrato'],
            },
        ),

        # PrestacaoIntermediaria - Intermediate payments (up to 30)
        migrations.CreateModel(
            name='PrestacaoIntermediaria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('numero_sequencial', models.PositiveIntegerField(
                    validators=[
                        django.core.validators.MinValueValidator(1),
                        django.core.validators.MaxValueValidator(30)
                    ],
                    verbose_name='Número Sequencial'
                )),
                ('mes_vencimento', models.PositiveIntegerField(
                    validators=[
                        django.core.validators.MinValueValidator(1),
                        django.core.validators.MaxValueValidator(360)
                    ],
                    verbose_name='Mês de Vencimento'
                )),
                ('valor', models.DecimalField(
                    decimal_places=2,
                    max_digits=12,
                    validators=[django.core.validators.MinValueValidator(Decimal('0.01'))],
                    verbose_name='Valor'
                )),
                ('paga', models.BooleanField(default=False, verbose_name='Paga')),
                ('data_pagamento', models.DateField(blank=True, null=True, verbose_name='Data de Pagamento')),
                ('valor_pago', models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    max_digits=12,
                    null=True,
                    verbose_name='Valor Pago'
                )),
                ('valor_reajustado', models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    max_digits=12,
                    null=True,
                    verbose_name='Valor Reajustado'
                )),
                ('observacoes', models.TextField(blank=True, verbose_name='Observações')),
                ('contrato', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='intermediarias',
                    to='contratos.contrato',
                    verbose_name='Contrato'
                )),
                ('parcela_vinculada', models.OneToOneField(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='intermediaria_origem',
                    to='financeiro.parcela',
                    verbose_name='Parcela Vinculada'
                )),
            ],
            options={
                'verbose_name': 'Prestação Intermediária',
                'verbose_name_plural': 'Prestações Intermediárias',
                'ordering': ['contrato', 'numero_sequencial'],
                'unique_together': {('contrato', 'numero_sequencial')},
            },
        ),

        # Add indexes
        migrations.AddIndex(
            model_name='indicereajuste',
            index=models.Index(fields=['tipo_indice', 'ano', 'mes'], name='contratos_i_tipo_in_idx'),
        ),
        migrations.AddIndex(
            model_name='indicereajuste',
            index=models.Index(fields=['ano', 'mes'], name='contratos_i_ano_mes_idx'),
        ),
        migrations.AddIndex(
            model_name='contrato',
            index=models.Index(fields=['numero_contrato'], name='contratos_c_numero_idx'),
        ),
        migrations.AddIndex(
            model_name='contrato',
            index=models.Index(fields=['status'], name='contratos_c_status_idx'),
        ),
        migrations.AddIndex(
            model_name='contrato',
            index=models.Index(fields=['data_contrato'], name='contratos_c_data_idx'),
        ),
        migrations.AddIndex(
            model_name='prestacaointermediaria',
            index=models.Index(fields=['contrato', 'mes_vencimento'], name='contratos_p_mes_idx'),
        ),
        migrations.AddIndex(
            model_name='prestacaointermediaria',
            index=models.Index(fields=['paga'], name='contratos_p_paga_idx'),
        ),
    ]
