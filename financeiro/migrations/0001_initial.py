# Generated migration for financeiro app
# Includes Parcela, Reajuste and payment models with adjustment cycle support

from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.utils.timezone
from decimal import Decimal


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
        ('contratos', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Parcela - Installment model with type and cycle
        migrations.CreateModel(
            name='Parcela',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('numero_parcela', models.PositiveIntegerField(verbose_name='Número da Parcela')),
                ('data_vencimento', models.DateField(verbose_name='Data de Vencimento')),
                ('tipo_parcela', models.CharField(
                    choices=[
                        ('NORMAL', 'Normal'),
                        ('INTERMEDIARIA', 'Intermediária'),
                        ('ENTRADA', 'Entrada'),
                    ],
                    default='NORMAL',
                    max_length=15,
                    verbose_name='Tipo de Parcela'
                )),
                ('ciclo_reajuste', models.PositiveIntegerField(
                    default=1,
                    verbose_name='Ciclo de Reajuste',
                    help_text='Ciclo de reajuste da parcela (1 = meses 1-12, 2 = meses 13-24, etc.)'
                )),
                ('valor_original', models.DecimalField(
                    decimal_places=2,
                    max_digits=12,
                    validators=[django.core.validators.MinValueValidator(Decimal('0.01'))],
                    verbose_name='Valor Original'
                )),
                ('valor_atual', models.DecimalField(
                    decimal_places=2,
                    max_digits=12,
                    validators=[django.core.validators.MinValueValidator(Decimal('0.01'))],
                    verbose_name='Valor Atual'
                )),
                ('valor_juros', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('0.00'),
                    max_digits=12,
                    verbose_name='Valor de Juros'
                )),
                ('valor_multa', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('0.00'),
                    max_digits=12,
                    verbose_name='Valor de Multa'
                )),
                ('valor_desconto', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('0.00'),
                    max_digits=12,
                    verbose_name='Valor de Desconto'
                )),
                ('pago', models.BooleanField(default=False, verbose_name='Pago')),
                ('data_pagamento', models.DateField(blank=True, null=True, verbose_name='Data do Pagamento')),
                ('valor_pago', models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    max_digits=12,
                    null=True,
                    verbose_name='Valor Pago'
                )),
                ('observacoes', models.TextField(blank=True, verbose_name='Observações')),
                # Boleto fields
                ('nosso_numero', models.CharField(blank=True, max_length=30, verbose_name='Nosso Número')),
                ('numero_documento', models.CharField(blank=True, max_length=25, verbose_name='Número do Documento')),
                ('codigo_barras', models.CharField(blank=True, max_length=50, verbose_name='Código de Barras')),
                ('linha_digitavel', models.CharField(blank=True, max_length=60, verbose_name='Linha Digitável')),
                ('boleto_pdf', models.FileField(blank=True, null=True, upload_to='boletos/%Y/%m/', verbose_name='Boleto PDF')),
                ('boleto_url', models.URLField(blank=True, max_length=500, verbose_name='URL do Boleto')),
                ('status_boleto', models.CharField(
                    choices=[
                        ('NAO_GERADO', 'Não Gerado'),
                        ('GERADO', 'Gerado'),
                        ('REGISTRADO', 'Registrado no Banco'),
                        ('PAGO', 'Pago'),
                        ('VENCIDO', 'Vencido'),
                        ('CANCELADO', 'Cancelado'),
                        ('PROTESTADO', 'Protestado'),
                        ('BAIXADO', 'Baixado'),
                    ],
                    default='NAO_GERADO',
                    max_length=15,
                    verbose_name='Status do Boleto'
                )),
                ('data_geracao_boleto', models.DateTimeField(blank=True, null=True, verbose_name='Data de Geração')),
                ('data_registro_boleto', models.DateTimeField(blank=True, null=True, verbose_name='Data de Registro')),
                ('data_pagamento_boleto', models.DateTimeField(blank=True, null=True, verbose_name='Data Pagamento Boleto')),
                ('valor_boleto', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Valor do Boleto')),
                ('valor_pago_boleto', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Valor Pago via Boleto')),
                ('banco_pagador', models.CharField(blank=True, max_length=10, verbose_name='Banco Pagador')),
                ('agencia_pagadora', models.CharField(blank=True, max_length=10, verbose_name='Agência Pagadora')),
                ('motivo_rejeicao', models.CharField(blank=True, max_length=255, verbose_name='Motivo Rejeição/Baixa')),
                ('pix_copia_cola', models.TextField(blank=True, verbose_name='PIX Copia e Cola')),
                ('pix_qrcode', models.TextField(blank=True, verbose_name='PIX QR Code')),
                # Foreign Keys
                ('contrato', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='parcelas',
                    to='contratos.contrato',
                    verbose_name='Contrato'
                )),
                ('conta_bancaria', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='parcelas',
                    to='core.contabancaria',
                    verbose_name='Conta Bancária'
                )),
            ],
            options={
                'verbose_name': 'Parcela',
                'verbose_name_plural': 'Parcelas',
                'ordering': ['contrato', 'numero_parcela'],
                'unique_together': {('contrato', 'numero_parcela')},
            },
        ),

        # Reajuste - Adjustment model with cycle support
        migrations.CreateModel(
            name='Reajuste',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('data_reajuste', models.DateField(default=django.utils.timezone.now, verbose_name='Data do Reajuste')),
                ('indice_tipo', models.CharField(max_length=10, verbose_name='Tipo de Índice')),
                ('percentual', models.DecimalField(
                    decimal_places=4,
                    max_digits=8,
                    validators=[django.core.validators.MinValueValidator(Decimal('-100.0000'))],
                    verbose_name='Percentual (%)'
                )),
                ('parcela_inicial', models.PositiveIntegerField(verbose_name='Parcela Inicial')),
                ('parcela_final', models.PositiveIntegerField(verbose_name='Parcela Final')),
                ('ciclo', models.PositiveIntegerField(
                    default=1,
                    verbose_name='Ciclo de Reajuste',
                    help_text='Número do ciclo de reajuste (2 = reajuste após 12 meses, 3 = após 24 meses, etc.)'
                )),
                ('data_limite_boleto', models.DateField(
                    blank=True,
                    null=True,
                    verbose_name='Data Limite para Boleto'
                )),
                ('aplicado_manual', models.BooleanField(default=False, verbose_name='Aplicado Manualmente')),
                ('aplicado', models.BooleanField(default=False, verbose_name='Aplicado')),
                ('data_aplicacao', models.DateTimeField(blank=True, null=True, verbose_name='Data da Aplicação')),
                ('observacoes', models.TextField(blank=True, verbose_name='Observações')),
                ('contrato', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='reajustes',
                    to='contratos.contrato',
                    verbose_name='Contrato'
                )),
            ],
            options={
                'verbose_name': 'Reajuste',
                'verbose_name_plural': 'Reajustes',
                'ordering': ['-data_reajuste'],
            },
        ),

        # HistoricoPagamento - Payment history
        migrations.CreateModel(
            name='HistoricoPagamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('data_pagamento', models.DateField(verbose_name='Data do Pagamento')),
                ('valor_pago', models.DecimalField(
                    decimal_places=2,
                    max_digits=12,
                    validators=[django.core.validators.MinValueValidator(Decimal('0.01'))],
                    verbose_name='Valor Pago'
                )),
                ('valor_parcela', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Valor da Parcela')),
                ('valor_juros', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12, verbose_name='Valor de Juros')),
                ('valor_multa', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12, verbose_name='Valor de Multa')),
                ('valor_desconto', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12, verbose_name='Valor de Desconto')),
                ('forma_pagamento', models.CharField(
                    choices=[
                        ('DINHEIRO', 'Dinheiro'),
                        ('PIX', 'PIX'),
                        ('TRANSFERENCIA', 'Transferência Bancária'),
                        ('BOLETO', 'Boleto'),
                        ('CARTAO_CREDITO', 'Cartão de Crédito'),
                        ('CARTAO_DEBITO', 'Cartão de Débito'),
                        ('CHEQUE', 'Cheque'),
                    ],
                    default='DINHEIRO',
                    max_length=50,
                    verbose_name='Forma de Pagamento'
                )),
                ('comprovante', models.FileField(blank=True, null=True, upload_to='comprovantes/%Y/%m/', verbose_name='Comprovante')),
                ('observacoes', models.TextField(blank=True, verbose_name='Observações')),
                ('parcela', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='historico_pagamentos',
                    to='financeiro.parcela',
                    verbose_name='Parcela'
                )),
            ],
            options={
                'verbose_name': 'Histórico de Pagamento',
                'verbose_name_plural': 'Histórico de Pagamentos',
                'ordering': ['-data_pagamento'],
            },
        ),

        # ArquivoRemessa - CNAB remittance file
        migrations.CreateModel(
            name='ArquivoRemessa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('numero_remessa', models.PositiveIntegerField(verbose_name='Número da Remessa')),
                ('layout', models.CharField(
                    choices=[('CNAB_240', 'CNAB 240'), ('CNAB_400', 'CNAB 400')],
                    default='CNAB_240',
                    max_length=10,
                    verbose_name='Layout'
                )),
                ('arquivo', models.FileField(upload_to='cnab/remessa/%Y/%m/', verbose_name='Arquivo')),
                ('nome_arquivo', models.CharField(max_length=100, verbose_name='Nome do Arquivo')),
                ('status', models.CharField(
                    choices=[
                        ('GERADO', 'Gerado'),
                        ('ENVIADO', 'Enviado ao Banco'),
                        ('PROCESSADO', 'Processado'),
                        ('ERRO', 'Erro'),
                    ],
                    default='GERADO',
                    max_length=15,
                    verbose_name='Status'
                )),
                ('data_geracao', models.DateTimeField(auto_now_add=True, verbose_name='Data de Geração')),
                ('data_envio', models.DateTimeField(blank=True, null=True, verbose_name='Data de Envio ao Banco')),
                ('quantidade_boletos', models.PositiveIntegerField(default=0, verbose_name='Quantidade de Boletos')),
                ('valor_total', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=14, verbose_name='Valor Total')),
                ('observacoes', models.TextField(blank=True, verbose_name='Observações')),
                ('erro_mensagem', models.TextField(blank=True, verbose_name='Mensagem de Erro')),
                ('conta_bancaria', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='arquivos_remessa',
                    to='core.contabancaria',
                    verbose_name='Conta Bancária'
                )),
            ],
            options={
                'verbose_name': 'Arquivo de Remessa',
                'verbose_name_plural': 'Arquivos de Remessa',
                'ordering': ['-data_geracao'],
                'unique_together': {('conta_bancaria', 'numero_remessa')},
            },
        ),

        # ItemRemessa
        migrations.CreateModel(
            name='ItemRemessa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('nosso_numero', models.CharField(max_length=30, verbose_name='Nosso Número')),
                ('valor', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Valor')),
                ('data_vencimento', models.DateField(verbose_name='Data de Vencimento')),
                ('processado', models.BooleanField(default=False, verbose_name='Processado')),
                ('codigo_ocorrencia', models.CharField(blank=True, max_length=10, verbose_name='Código de Ocorrência')),
                ('descricao_ocorrencia', models.CharField(blank=True, max_length=255, verbose_name='Descrição da Ocorrência')),
                ('arquivo_remessa', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='itens',
                    to='financeiro.arquivoremessa',
                    verbose_name='Arquivo de Remessa'
                )),
                ('parcela', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='itens_remessa',
                    to='financeiro.parcela',
                    verbose_name='Parcela'
                )),
            ],
            options={
                'verbose_name': 'Item de Remessa',
                'verbose_name_plural': 'Itens de Remessa',
                'ordering': ['arquivo_remessa', 'id'],
                'unique_together': {('arquivo_remessa', 'parcela')},
            },
        ),

        # ArquivoRetorno
        migrations.CreateModel(
            name='ArquivoRetorno',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('arquivo', models.FileField(upload_to='cnab/retorno/%Y/%m/', verbose_name='Arquivo')),
                ('nome_arquivo', models.CharField(max_length=100, verbose_name='Nome do Arquivo')),
                ('layout', models.CharField(
                    choices=[('CNAB_240', 'CNAB 240'), ('CNAB_400', 'CNAB 400')],
                    default='CNAB_240',
                    max_length=10,
                    verbose_name='Layout'
                )),
                ('status', models.CharField(
                    choices=[
                        ('PENDENTE', 'Pendente de Processamento'),
                        ('PROCESSADO', 'Processado'),
                        ('PROCESSADO_PARCIAL', 'Processado Parcialmente'),
                        ('ERRO', 'Erro'),
                    ],
                    default='PENDENTE',
                    max_length=20,
                    verbose_name='Status'
                )),
                ('data_upload', models.DateTimeField(auto_now_add=True, verbose_name='Data de Upload')),
                ('data_processamento', models.DateTimeField(blank=True, null=True, verbose_name='Data de Processamento')),
                ('total_registros', models.PositiveIntegerField(default=0, verbose_name='Total de Registros')),
                ('registros_processados', models.PositiveIntegerField(default=0, verbose_name='Registros Processados')),
                ('registros_erro', models.PositiveIntegerField(default=0, verbose_name='Registros com Erro')),
                ('valor_total_pago', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=14, verbose_name='Valor Total Pago')),
                ('observacoes', models.TextField(blank=True, verbose_name='Observações')),
                ('erro_mensagem', models.TextField(blank=True, verbose_name='Mensagem de Erro')),
                ('conta_bancaria', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='arquivos_retorno',
                    to='core.contabancaria',
                    verbose_name='Conta Bancária'
                )),
                ('processado_por', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Processado por'
                )),
            ],
            options={
                'verbose_name': 'Arquivo de Retorno',
                'verbose_name_plural': 'Arquivos de Retorno',
                'ordering': ['-data_upload'],
            },
        ),

        # ItemRetorno
        migrations.CreateModel(
            name='ItemRetorno',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('nosso_numero', models.CharField(max_length=30, verbose_name='Nosso Número')),
                ('numero_documento', models.CharField(blank=True, max_length=25, verbose_name='Número do Documento')),
                ('codigo_ocorrencia', models.CharField(max_length=10, verbose_name='Código de Ocorrência')),
                ('descricao_ocorrencia', models.CharField(blank=True, max_length=255, verbose_name='Descrição da Ocorrência')),
                ('tipo_ocorrencia', models.CharField(
                    choices=[
                        ('ENTRADA', 'Entrada Confirmada'),
                        ('LIQUIDACAO', 'Liquidação/Pagamento'),
                        ('BAIXA', 'Baixa'),
                        ('REJEICAO', 'Rejeição'),
                        ('PROTESTO', 'Protesto'),
                        ('TARIFA', 'Tarifa/Taxa'),
                        ('OUTROS', 'Outros'),
                    ],
                    default='OUTROS',
                    max_length=20,
                    verbose_name='Tipo de Ocorrência'
                )),
                ('valor_titulo', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Valor do Título')),
                ('valor_pago', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Valor Pago')),
                ('valor_juros', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Valor de Juros')),
                ('valor_multa', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Valor de Multa')),
                ('valor_desconto', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Valor de Desconto')),
                ('valor_tarifa', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Valor de Tarifa')),
                ('data_ocorrencia', models.DateField(blank=True, null=True, verbose_name='Data da Ocorrência')),
                ('data_credito', models.DateField(blank=True, null=True, verbose_name='Data de Crédito')),
                ('processado', models.BooleanField(default=False, verbose_name='Processado')),
                ('erro_processamento', models.TextField(blank=True, verbose_name='Erro de Processamento')),
                ('arquivo_retorno', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='itens',
                    to='financeiro.arquivoretorno',
                    verbose_name='Arquivo de Retorno'
                )),
                ('parcela', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='itens_retorno',
                    to='financeiro.parcela',
                    verbose_name='Parcela'
                )),
            ],
            options={
                'verbose_name': 'Item de Retorno',
                'verbose_name_plural': 'Itens de Retorno',
                'ordering': ['arquivo_retorno', 'id'],
            },
        ),

        # Add indexes
        migrations.AddIndex(
            model_name='parcela',
            index=models.Index(fields=['contrato', 'numero_parcela'], name='financeiro_p_cont_num_idx'),
        ),
        migrations.AddIndex(
            model_name='parcela',
            index=models.Index(fields=['data_vencimento'], name='financeiro_p_venc_idx'),
        ),
        migrations.AddIndex(
            model_name='parcela',
            index=models.Index(fields=['pago'], name='financeiro_p_pago_idx'),
        ),
        migrations.AddIndex(
            model_name='parcela',
            index=models.Index(fields=['status_boleto'], name='financeiro_p_status_idx'),
        ),
        migrations.AddIndex(
            model_name='parcela',
            index=models.Index(fields=['nosso_numero'], name='financeiro_p_nosso_idx'),
        ),
        migrations.AddIndex(
            model_name='reajuste',
            index=models.Index(fields=['contrato', 'data_reajuste'], name='financeiro_r_cont_data_idx'),
        ),
        migrations.AddIndex(
            model_name='historicopagamento',
            index=models.Index(fields=['parcela', 'data_pagamento'], name='financeiro_h_parc_data_idx'),
        ),
        migrations.AddIndex(
            model_name='itemretorno',
            index=models.Index(fields=['nosso_numero'], name='financeiro_ir_nosso_idx'),
        ),
        migrations.AddIndex(
            model_name='itemretorno',
            index=models.Index(fields=['tipo_ocorrencia'], name='financeiro_ir_tipo_idx'),
        ),
    ]
