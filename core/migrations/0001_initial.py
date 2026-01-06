# Generated migration for core app
# Includes base models: Contabilidade, Imobiliaria, ContaBancaria, Imovel, Comprador, AcessoUsuario
#
# Desenvolvedor: Maxwell da Silva Oliveira
# Email: maxwbh@gmail.com

from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Contabilidade
        migrations.CreateModel(
            name='Contabilidade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('nome', models.CharField(max_length=200, verbose_name='Nome da Contabilidade')),
                ('razao_social', models.CharField(max_length=200, verbose_name='Razão Social')),
                ('cnpj', models.CharField(blank=True, help_text='Opcional. Suporta formato numérico atual e alfanumérico (preparado para 2026)', max_length=20, null=True, unique=True, verbose_name='CNPJ')),
                ('endereco', models.TextField(verbose_name='Endereço')),
                ('telefone', models.CharField(max_length=20, verbose_name='Telefone')),
                ('email', models.EmailField(max_length=254, validators=[django.core.validators.EmailValidator()], verbose_name='E-mail')),
                ('responsavel', models.CharField(max_length=200, verbose_name='Responsável')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
            ],
            options={
                'verbose_name': 'Contabilidade',
                'verbose_name_plural': 'Contabilidades',
                'ordering': ['nome'],
            },
        ),

        # Imobiliaria
        migrations.CreateModel(
            name='Imobiliaria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('nome', models.CharField(max_length=200, verbose_name='Nome da Imobiliária')),
                ('razao_social', models.CharField(max_length=200, verbose_name='Razão Social')),
                ('cnpj', models.CharField(help_text='Suporta formato numérico atual e alfanumérico (preparado para 2026)', max_length=20, unique=True, verbose_name='CNPJ')),
                ('cep', models.CharField(blank=True, help_text='Formato: 99999-999', max_length=9, verbose_name='CEP')),
                ('logradouro', models.CharField(blank=True, max_length=200, verbose_name='Logradouro')),
                ('numero', models.CharField(blank=True, max_length=10, verbose_name='Número')),
                ('complemento', models.CharField(blank=True, max_length=100, verbose_name='Complemento')),
                ('bairro', models.CharField(blank=True, max_length=100, verbose_name='Bairro')),
                ('cidade', models.CharField(blank=True, max_length=100, verbose_name='Cidade')),
                ('estado', models.CharField(blank=True, choices=[('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'), ('AM', 'Amazonas'), ('BA', 'Bahia'), ('CE', 'Ceará'), ('DF', 'Distrito Federal'), ('ES', 'Espírito Santo'), ('GO', 'Goiás'), ('MA', 'Maranhão'), ('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul'), ('MG', 'Minas Gerais'), ('PA', 'Pará'), ('PB', 'Paraíba'), ('PR', 'Paraná'), ('PE', 'Pernambuco'), ('PI', 'Piauí'), ('RJ', 'Rio de Janeiro'), ('RN', 'Rio Grande do Norte'), ('RS', 'Rio Grande do Sul'), ('RO', 'Rondônia'), ('RR', 'Roraima'), ('SC', 'Santa Catarina'), ('SP', 'São Paulo'), ('SE', 'Sergipe'), ('TO', 'Tocantins')], max_length=2, verbose_name='UF')),
                ('endereco', models.TextField(blank=True, help_text='Campo legado - use os campos separados acima', verbose_name='Endereço Completo (legacy)')),
                ('telefone', models.CharField(max_length=20, verbose_name='Telefone')),
                ('email', models.EmailField(max_length=254, validators=[django.core.validators.EmailValidator()], verbose_name='E-mail')),
                ('responsavel_financeiro', models.CharField(max_length=200, verbose_name='Responsável Financeiro')),
                ('banco', models.CharField(blank=True, max_length=100, verbose_name='Banco')),
                ('agencia', models.CharField(blank=True, max_length=20, verbose_name='Agência')),
                ('conta', models.CharField(blank=True, max_length=20, verbose_name='Conta')),
                ('pix', models.CharField(blank=True, max_length=100, verbose_name='Chave PIX')),
                ('tipo_valor_multa', models.CharField(choices=[('PERCENTUAL', 'Percentual (%)'), ('REAL', 'Valor em Reais (R$)')], default='PERCENTUAL', max_length=10, verbose_name='Tipo de Multa')),
                ('percentual_multa_padrao', models.DecimalField(decimal_places=2, default=0, help_text='Valor em percentual ou reais conforme tipo', max_digits=10, verbose_name='Multa Padrão')),
                ('tipo_valor_juros', models.CharField(choices=[('PERCENTUAL', 'Percentual (%)'), ('REAL', 'Valor em Reais (R$)')], default='PERCENTUAL', max_length=10, verbose_name='Tipo de Juros')),
                ('percentual_juros_padrao', models.DecimalField(decimal_places=4, default=0, help_text='Valor em percentual (0,0333 = 1% ao mês) ou reais', max_digits=10, verbose_name='Juros ao Dia Padrão')),
                ('dias_para_encargos_padrao', models.IntegerField(default=0, help_text='Dias sem cobrar multa/juros após vencimento', verbose_name='Dias sem Encargos')),
                ('boleto_sem_valor', models.BooleanField(default=False, verbose_name='Permite Boleto sem Valor')),
                ('parcela_no_documento', models.BooleanField(default=False, help_text='Incluir número da parcela no campo Documento', verbose_name='Parcela no Documento')),
                ('campo_desconto_abatimento_pdf', models.BooleanField(default=False, help_text='Mostrar desconto no campo "Desconto/Abatimento" do boleto', verbose_name='Desconto no PDF')),
                ('tipo_valor_desconto', models.CharField(choices=[('PERCENTUAL', 'Percentual (%)'), ('REAL', 'Valor em Reais (R$)')], default='PERCENTUAL', max_length=10, verbose_name='Tipo de Desconto')),
                ('percentual_desconto_padrao', models.DecimalField(decimal_places=2, default=0, help_text='Valor em percentual ou reais conforme tipo', max_digits=10, verbose_name='Desconto Padrão')),
                ('dias_para_desconto_padrao', models.IntegerField(default=0, help_text='Dias para conceder desconto até vencimento', verbose_name='Dias para Desconto')),
                ('tipo_valor_desconto2', models.CharField(choices=[('PERCENTUAL', 'Percentual (%)'), ('REAL', 'Valor em Reais (R$)')], default='PERCENTUAL', max_length=10, verbose_name='Tipo de 2º Desconto')),
                ('desconto2_padrao', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='2º Desconto Padrão')),
                ('dias_para_desconto2_padrao', models.IntegerField(default=0, verbose_name='Dias para 2º Desconto')),
                ('tipo_valor_desconto3', models.CharField(choices=[('PERCENTUAL', 'Percentual (%)'), ('REAL', 'Valor em Reais (R$)')], default='PERCENTUAL', max_length=10, verbose_name='Tipo de 3º Desconto')),
                ('desconto3_padrao', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='3º Desconto Padrão')),
                ('dias_para_desconto3_padrao', models.IntegerField(default=0, verbose_name='Dias para 3º Desconto')),
                ('instrucao_padrao', models.CharField(blank=True, help_text='Uma linha no espaço instrução ao caixa', max_length=255, verbose_name='Instrução Padrão')),
                ('tipo_titulo', models.CharField(choices=[('AP', 'AP - Apólice de Seguro'), ('BDP', 'BDP - Boleto de Proposta'), ('CC', 'CC - Cartão de Crédito'), ('CH', 'CH - Cheque'), ('CPR', 'CPR - Cédula de Produto Rural'), ('DAE', 'DAE - Dívida Ativa de Estado'), ('DAM', 'DAM - Dívida Ativa de Município'), ('DAU', 'DAU - Dívida Ativa da União'), ('DD', 'DD - Documento de Dívida'), ('DM', 'DM - Duplicata Mercantil'), ('DMI', 'DMI - Duplicata Mercantil para Indicação'), ('DR', 'DR - Duplicata Rural'), ('DS', 'DS - Duplicata de Serviço'), ('DSI', 'DSI - Duplicata de Serviço para Indicação'), ('EC', 'EC - Encargos Condominiais'), ('FAT', 'FAT - Fatura'), ('LC', 'LC - Letra de Câmbio'), ('ME', 'ME - Mensalidade Escolar'), ('NCC', 'NCC - Nota de Crédito Comercial'), ('NCE', 'NCE - Nota de Crédito à Exportação'), ('NCI', 'NCI - Nota de Crédito Industrial'), ('NCR', 'NCR - Nota de Crédito Rural'), ('ND', 'ND - Nota de Débito'), ('NF', 'NF - Nota Fiscal'), ('NP', 'NP - Nota Promissória'), ('NPR', 'NPR - Nota Promissória Rural'), ('NS', 'NS - Nota de Seguro'), ('O', 'O - Outros'), ('PC', 'PC - Parcela de Consórcio'), ('RC', 'RC - Recibo'), ('TM', 'TM - Triplicata Mercantil'), ('TS', 'TS - Triplicata de Serviço'), ('W', 'W - Warrant')], default='RC', help_text='Tipo de título para emissão de boletos', max_length=5, verbose_name='Tipo do Título')),
                ('aceite', models.BooleanField(default=False, verbose_name='Aceite')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('contabilidade', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='imobiliarias', to='core.contabilidade', verbose_name='Contabilidade')),
            ],
            options={
                'verbose_name': 'Imobiliária',
                'verbose_name_plural': 'Imobiliárias',
                'ordering': ['nome'],
            },
        ),

        # ContaBancaria
        migrations.CreateModel(
            name='ContaBancaria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('banco', models.CharField(choices=[('001', '001 - Banco do Brasil'), ('004', '004 - Banco do Nordeste - BNB'), ('021', '021 - Banestes'), ('033', '033 - Santander'), ('041', '041 - Banrisul'), ('070', '070 - BRB - Banco de Brasília'), ('077', '077 - Banco Inter'), ('084', '084 - Sisprime'), ('085', '085 - Cecred / Ailos'), ('089', '089 - Credisan'), ('104', '104 - Caixa Econômica Federal'), ('133', '133 - Cresol'), ('136', '136 - Unicred'), ('208', '208 - BTG Pactual'), ('213', '213 - Banco Arbi'), ('237', '237 - Bradesco'), ('246', '246 - ABC Brasil'), ('274', '274 - BMP'), ('336', '336 - C6 Bank'), ('341', '341 - Itaú'), ('389', '389 - Mercantil do Brasil'), ('399', '399 - HSBC'), ('422', '422 - Safra'), ('756', '756 - Sicoob / Bancoob'), ('748', '748 - Sicredi'), ('637', '637 - Sofisa'), ('707', '707 - Daycoval'), ('260', '260 - Nubank'), ('290', '290 - PagBank / PagSeguro'), ('323', '323 - Mercado Pago'), ('197', '197 - Stone'), ('461', '461 - Asaas'), ('000', '000 - Outros')], max_length=3, verbose_name='Banco')),
                ('descricao', models.CharField(help_text='Identificação da conta (ex: Conta Principal, Conta Boletos)', max_length=150, verbose_name='Descrição')),
                ('principal', models.BooleanField(default=False, help_text='Marque se esta é a conta principal', verbose_name='Conta Principal')),
                ('agencia', models.CharField(help_text='Número da agência com dígito', max_length=10, verbose_name='Agência')),
                ('conta', models.CharField(help_text='Número da conta com dígito', max_length=20, verbose_name='Conta')),
                ('convenio', models.CharField(blank=True, help_text='Código do convênio para emissão de boletos', max_length=20, verbose_name='Convênio / Código do Cliente')),
                ('carteira', models.CharField(blank=True, help_text='Número da carteira de cobrança', max_length=5, verbose_name='Carteira')),
                ('nosso_numero_atual', models.IntegerField(default=0, help_text='Sequencial atual do nosso número', verbose_name='Nosso Número Atual')),
                ('modalidade', models.CharField(blank=True, max_length=5, verbose_name='Modalidade')),
                ('tipo_pix', models.CharField(blank=True, choices=[('CPF', 'CPF'), ('CNPJ', 'CNPJ'), ('EMAIL', 'E-mail'), ('TELEFONE', 'Telefone'), ('ALEATORIA', 'Chave Aleatória')], max_length=20, verbose_name='Tipo de Chave PIX')),
                ('chave_pix', models.CharField(blank=True, max_length=100, verbose_name='Chave PIX')),
                ('cobranca_registrada', models.BooleanField(default=True, verbose_name='Cobrança Registrada')),
                ('prazo_baixa', models.IntegerField(default=0, help_text='Prazo em dias para baixa/devolução do título após vencimento', verbose_name='Prazo para Baixa (dias)')),
                ('prazo_protesto', models.IntegerField(default=0, help_text='Prazo em dias para protesto. 0 = não protestar', verbose_name='Prazo para Protesto (dias)')),
                ('layout_cnab', models.CharField(choices=[('CNAB_240', 'Layout 240'), ('CNAB_400', 'Layout 400'), ('CNAB_444', 'Layout 444 (CNAB 400 + Chave NFE)')], default='CNAB_240', help_text='Layout dos arquivos CNAB', max_length=10, verbose_name='Layout CNAB')),
                ('numero_remessa_cnab_atual', models.IntegerField(default=0, help_text='Número sequencial da remessa CNAB', verbose_name='Sequencial Remessa')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('imobiliaria', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contas_bancarias', to='core.imobiliaria', verbose_name='Imobiliária')),
            ],
            options={
                'verbose_name': 'Conta Bancária',
                'verbose_name_plural': 'Contas Bancárias',
                'ordering': ['-principal', 'banco', 'descricao'],
            },
        ),

        # Imovel
        migrations.CreateModel(
            name='Imovel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('tipo', models.CharField(choices=[('LOTE', 'Lote'), ('TERRENO', 'Terreno'), ('CASA', 'Casa'), ('APARTAMENTO', 'Apartamento'), ('COMERCIAL', 'Comercial')], default='LOTE', max_length=20, verbose_name='Tipo de Imóvel')),
                ('identificacao', models.CharField(help_text='Ex: Quadra 1, Lote 15', max_length=100, verbose_name='Identificação')),
                ('loteamento', models.CharField(blank=True, help_text='Opcional. Nome do loteamento ou empreendimento', max_length=200, verbose_name='Loteamento/Empreendimento')),
                ('cep', models.CharField(blank=True, help_text='Formato: 99999-999', max_length=9, verbose_name='CEP')),
                ('logradouro', models.CharField(blank=True, max_length=200, verbose_name='Logradouro')),
                ('numero', models.CharField(blank=True, max_length=10, verbose_name='Número')),
                ('complemento', models.CharField(blank=True, max_length=100, verbose_name='Complemento')),
                ('bairro', models.CharField(blank=True, max_length=100, verbose_name='Bairro')),
                ('cidade', models.CharField(blank=True, max_length=100, verbose_name='Cidade')),
                ('estado', models.CharField(blank=True, choices=[('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'), ('AM', 'Amazonas'), ('BA', 'Bahia'), ('CE', 'Ceará'), ('DF', 'Distrito Federal'), ('ES', 'Espírito Santo'), ('GO', 'Goiás'), ('MA', 'Maranhão'), ('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul'), ('MG', 'Minas Gerais'), ('PA', 'Pará'), ('PB', 'Paraíba'), ('PR', 'Paraná'), ('PE', 'Pernambuco'), ('PI', 'Piauí'), ('RJ', 'Rio de Janeiro'), ('RN', 'Rio Grande do Norte'), ('RS', 'Rio Grande do Sul'), ('RO', 'Rondônia'), ('RR', 'Roraima'), ('SC', 'Santa Catarina'), ('SP', 'São Paulo'), ('SE', 'Sergipe'), ('TO', 'Tocantins')], max_length=2, verbose_name='UF')),
                ('endereco', models.TextField(blank=True, help_text='Campo legado - use os campos estruturados acima', verbose_name='Endereço Completo')),
                ('latitude', models.DecimalField(blank=True, decimal_places=7, help_text='Coordenada de latitude (ex: -23.5505199)', max_digits=10, null=True, verbose_name='Latitude')),
                ('longitude', models.DecimalField(blank=True, decimal_places=7, help_text='Coordenada de longitude (ex: -46.6333094)', max_digits=10, null=True, verbose_name='Longitude')),
                ('area', models.DecimalField(decimal_places=2, help_text='Área em metros quadrados', max_digits=10, verbose_name='Área (m²)')),
                ('valor', models.DecimalField(blank=True, decimal_places=2, help_text='Valor do imóvel', max_digits=12, null=True, verbose_name='Valor (R$)')),
                ('matricula', models.CharField(blank=True, help_text='Número da matrícula do imóvel', max_length=100, verbose_name='Matrícula')),
                ('inscricao_municipal', models.CharField(blank=True, max_length=100, verbose_name='Inscrição Municipal')),
                ('observacoes', models.TextField(blank=True, verbose_name='Observações')),
                ('disponivel', models.BooleanField(default=True, verbose_name='Disponível para Venda')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('imobiliaria', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='imoveis', to='core.imobiliaria', verbose_name='Imobiliária')),
            ],
            options={
                'verbose_name': 'Imóvel',
                'verbose_name_plural': 'Imóveis',
                'ordering': ['loteamento', 'identificacao'],
            },
        ),
        migrations.AddIndex(
            model_name='imovel',
            index=models.Index(fields=['disponivel', 'ativo'], name='core_imovel_disponi_57a3c5_idx'),
        ),
        migrations.AddIndex(
            model_name='imovel',
            index=models.Index(fields=['loteamento'], name='core_imovel_loteame_e88d07_idx'),
        ),

        # Comprador
        migrations.CreateModel(
            name='Comprador',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('tipo_pessoa', models.CharField(choices=[('PF', 'Pessoa Física'), ('PJ', 'Pessoa Jurídica')], default='PF', help_text='Pessoa Física ou Pessoa Jurídica', max_length=2, verbose_name='Tipo de Pessoa')),
                ('nome', models.CharField(help_text='Nome completo para PF ou Razão Social para PJ', max_length=200, verbose_name='Nome Completo / Razão Social')),
                ('cpf', models.CharField(blank=True, help_text='Obrigatório para Pessoa Física', max_length=14, null=True, validators=[django.core.validators.RegexValidator(message='CPF deve estar no formato XXX.XXX.XXX-XX', regex='^\\d{3}\\.\\d{3}\\.\\d{3}-\\d{2}$')], verbose_name='CPF')),
                ('rg', models.CharField(blank=True, help_text='Apenas para Pessoa Física', max_length=20, verbose_name='RG')),
                ('data_nascimento', models.DateField(blank=True, help_text='Apenas para Pessoa Física', null=True, verbose_name='Data de Nascimento')),
                ('estado_civil', models.CharField(blank=True, choices=[('SOLTEIRO', 'Solteiro(a)'), ('CASADO', 'Casado(a)'), ('DIVORCIADO', 'Divorciado(a)'), ('VIUVO', 'Viúvo(a)'), ('UNIAO_ESTAVEL', 'União Estável')], help_text='Apenas para Pessoa Física', max_length=50, verbose_name='Estado Civil')),
                ('profissao', models.CharField(blank=True, help_text='Apenas para Pessoa Física', max_length=100, verbose_name='Profissão')),
                ('cnpj', models.CharField(blank=True, help_text='Obrigatório para PJ. Suporta formato alfanumérico (preparado para 2026)', max_length=20, null=True, verbose_name='CNPJ')),
                ('nome_fantasia', models.CharField(blank=True, help_text='Apenas para Pessoa Jurídica', max_length=200, verbose_name='Nome Fantasia')),
                ('inscricao_estadual', models.CharField(blank=True, help_text='Apenas para Pessoa Jurídica', max_length=20, verbose_name='Inscrição Estadual')),
                ('inscricao_municipal', models.CharField(blank=True, help_text='Apenas para Pessoa Jurídica', max_length=20, verbose_name='Inscrição Municipal')),
                ('responsavel_legal', models.CharField(blank=True, help_text='Nome do representante legal da empresa (apenas PJ)', max_length=200, verbose_name='Responsável Legal')),
                ('responsavel_cpf', models.CharField(blank=True, help_text='CPF do representante legal (apenas PJ)', max_length=14, verbose_name='CPF do Responsável')),
                ('cep', models.CharField(blank=True, help_text='Formato: 99999-999', max_length=9, verbose_name='CEP')),
                ('logradouro', models.CharField(blank=True, max_length=200, verbose_name='Logradouro')),
                ('numero', models.CharField(blank=True, max_length=10, verbose_name='Número')),
                ('complemento', models.CharField(blank=True, max_length=100, verbose_name='Complemento')),
                ('bairro', models.CharField(blank=True, max_length=100, verbose_name='Bairro')),
                ('cidade', models.CharField(blank=True, max_length=100, verbose_name='Cidade')),
                ('estado', models.CharField(blank=True, choices=[('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'), ('AM', 'Amazonas'), ('BA', 'Bahia'), ('CE', 'Ceará'), ('DF', 'Distrito Federal'), ('ES', 'Espírito Santo'), ('GO', 'Goiás'), ('MA', 'Maranhão'), ('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul'), ('MG', 'Minas Gerais'), ('PA', 'Pará'), ('PB', 'Paraíba'), ('PR', 'Paraná'), ('PE', 'Pernambuco'), ('PI', 'Piauí'), ('RJ', 'Rio de Janeiro'), ('RN', 'Rio Grande do Norte'), ('RS', 'Rio Grande do Sul'), ('RO', 'Rondônia'), ('RR', 'Roraima'), ('SC', 'Santa Catarina'), ('SP', 'São Paulo'), ('SE', 'Sergipe'), ('TO', 'Tocantins')], max_length=2, verbose_name='UF')),
                ('endereco', models.TextField(blank=True, help_text='Campo legado - use os campos separados acima', verbose_name='Endereço Completo (legacy)')),
                ('telefone', models.CharField(max_length=20, verbose_name='Telefone')),
                ('celular', models.CharField(max_length=20, verbose_name='Celular')),
                ('email', models.EmailField(help_text='E-mail para envio de notificações', max_length=254, validators=[django.core.validators.EmailValidator()], verbose_name='E-mail')),
                ('notificar_email', models.BooleanField(default=True, verbose_name='Notificar por E-mail')),
                ('notificar_sms', models.BooleanField(default=False, verbose_name='Notificar por SMS')),
                ('notificar_whatsapp', models.BooleanField(default=False, verbose_name='Notificar por WhatsApp')),
                ('conjuge_nome', models.CharField(blank=True, max_length=200, verbose_name='Nome do Cônjuge')),
                ('conjuge_cpf', models.CharField(blank=True, max_length=14, validators=[django.core.validators.RegexValidator(message='CPF deve estar no formato XXX.XXX.XXX-XX', regex='^\\d{3}\\.\\d{3}\\.\\d{3}-\\d{2}$')], verbose_name='CPF do Cônjuge')),
                ('conjuge_rg', models.CharField(blank=True, max_length=20, verbose_name='RG do Cônjuge')),
                ('observacoes', models.TextField(blank=True, verbose_name='Observações')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
            ],
            options={
                'verbose_name': 'Comprador',
                'verbose_name_plural': 'Compradores',
                'ordering': ['nome'],
            },
        ),
        migrations.AddIndex(
            model_name='comprador',
            index=models.Index(fields=['tipo_pessoa'], name='core_compra_tipo_pe_f08b3c_idx'),
        ),
        migrations.AddIndex(
            model_name='comprador',
            index=models.Index(fields=['cpf'], name='core_compra_cpf_eeffd1_idx'),
        ),
        migrations.AddIndex(
            model_name='comprador',
            index=models.Index(fields=['cnpj'], name='core_compra_cnpj_7c3db1_idx'),
        ),

        # AcessoUsuario
        migrations.CreateModel(
            name='AcessoUsuario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('pode_editar', models.BooleanField(default=True, help_text='Permite criar/editar registros', verbose_name='Pode Editar')),
                ('pode_excluir', models.BooleanField(default=False, help_text='Permite excluir registros', verbose_name='Pode Excluir')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('contabilidade', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='acessos_usuarios', to='core.contabilidade', verbose_name='Contabilidade')),
                ('imobiliaria', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='acessos_usuarios', to='core.imobiliaria', verbose_name='Imobiliária')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='acessos', to=settings.AUTH_USER_MODEL, verbose_name='Usuário')),
            ],
            options={
                'verbose_name': 'Acesso de Usuário',
                'verbose_name_plural': 'Acessos de Usuários',
                'ordering': ['usuario__username', 'contabilidade__nome', 'imobiliaria__nome'],
                'unique_together': {('usuario', 'contabilidade', 'imobiliaria')},
            },
        ),
        migrations.AddIndex(
            model_name='acessousuario',
            index=models.Index(fields=['usuario', 'ativo'], name='core_acesso_usuario_9b9817_idx'),
        ),
        migrations.AddIndex(
            model_name='acessousuario',
            index=models.Index(fields=['contabilidade', 'ativo'], name='core_acesso_contabi_7c94f7_idx'),
        ),
        migrations.AddIndex(
            model_name='acessousuario',
            index=models.Index(fields=['imobiliaria', 'ativo'], name='core_acesso_imobili_df4b56_idx'),
        ),
    ]
