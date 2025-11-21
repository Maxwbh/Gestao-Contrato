"""
Django Management Command para gerar dados de teste

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA

Uso:
    python manage.py gerar_dados_teste
    python manage.py gerar_dados_teste --limpar  # Limpa dados antes
"""
import random
from decimal import Decimal
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from faker import Faker

from core.models import Contabilidade, Imobiliaria, Imovel, Comprador, TipoImovel
from contratos.models import Contrato, TipoCorrecao, StatusContrato
from financeiro.models import Parcela


class Command(BaseCommand):
    help = 'Gera massa de dados de teste para o sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limpar',
            action='store_true',
            help='Limpa todos os dados antes de gerar novos',
        )

    def handle(self, *args, **options):
        self.fake = Faker('pt_BR')
        Faker.seed(12345)  # Para dados consistentes
        random.seed(12345)

        if options['limpar']:
            self.stdout.write(self.style.WARNING('Limpando dados existentes...'))
            self.limpar_dados()

        self.stdout.write(self.style.SUCCESS('Iniciando geração de dados de teste...'))

        with transaction.atomic():
            # 1. Criar Contabilidade
            self.stdout.write('Criando Contabilidade...')
            contabilidade = self.criar_contabilidade()

            # 2. Criar 2 Imobiliárias
            self.stdout.write('Criando Imobiliárias...')
            imobiliarias = self.criar_imobiliarias(contabilidade, 2)

            # 3. Criar 2 Loteamentos com 30 Lotes cada
            self.stdout.write('Criando Loteamentos...')
            lotes = self.criar_loteamentos(imobiliarias, 2, 30)

            # 4. Criar 5 Terrenos
            self.stdout.write('Criando Terrenos...')
            terrenos = self.criar_terrenos(imobiliarias, 5)

            # 5. Criar 60 Compradores
            self.stdout.write('Criando Compradores...')
            compradores = self.criar_compradores(60)

            # 6. Criar Contratos
            self.stdout.write('Criando Contratos...')
            imoveis = lotes + terrenos
            contratos = self.criar_contratos(imoveis, compradores, imobiliarias)

            # 7. Marcar 90% das parcelas como pagas
            self.stdout.write('Marcando parcelas como pagas...')
            self.marcar_parcelas_pagas(contratos, 0.90)

        self.stdout.write(self.style.SUCCESS('\n✅ Dados gerados com sucesso!'))
        self.stdout.write(self.style.SUCCESS(f'   • 1 Contabilidade'))
        self.stdout.write(self.style.SUCCESS(f'   • 2 Imobiliárias'))
        self.stdout.write(self.style.SUCCESS(f'   • {len(lotes)} Lotes'))
        self.stdout.write(self.style.SUCCESS(f'   • {len(terrenos)} Terrenos'))
        self.stdout.write(self.style.SUCCESS(f'   • {len(compradores)} Compradores'))
        self.stdout.write(self.style.SUCCESS(f'   • {len(contratos)} Contratos'))

    def limpar_dados(self):
        """Limpa todos os dados de teste"""
        Parcela.objects.all().delete()
        Contrato.objects.all().delete()
        Imovel.objects.all().delete()
        Comprador.objects.all().delete()
        Imobiliaria.objects.all().delete()
        Contabilidade.objects.all().delete()

    def criar_contabilidade(self):
        """Cria 1 Contabilidade"""
        return Contabilidade.objects.create(
            nome='Contabilidade Sete Lagoas',
            razao_social='M&S Contabilidade e Consultoria LTDA',
            cnpj='12.345.678/0001-90',
            endereco='Rua Principal, 123 - Centro - Sete Lagoas/MG - CEP: 35700-000',
            telefone='(31) 3773-1234',
            email='contato@msbrasil.inf.br',
            responsavel='Maxwell da Silva Oliveira',
            ativo=True
        )

    def criar_imobiliarias(self, contabilidade, quantidade):
        """Cria Imobiliárias"""
        imobiliarias = []
        nomes = [
            'Imobiliária Lagoa Real',
            'Imobiliária Sete Colinas'
        ]

        for i in range(quantidade):
            imobiliaria = Imobiliaria.objects.create(
                contabilidade=contabilidade,
                nome=nomes[i],
                razao_social=f'{nomes[i]} Negócios Imobiliários LTDA',
                cnpj=f'23.456.78{i}/0001-{10+i}',
                endereco=f'Av. Prefeito Alberto Moura, {100+i*50} - Centro - Sete Lagoas/MG',
                telefone=f'(31) 3773-{2000+i*100}',
                email=f'contato@{nomes[i].lower().replace(" ", "")}.com.br',
                responsavel_financeiro=self.fake.name(),
                banco='Banco do Brasil',
                agencia=f'{3000+i}',
                conta=f'{50000+i*1000}-{i}',
                pix=f'pix@{nomes[i].lower().replace(" ", "")}.com.br',
                ativo=True
            )
            imobiliarias.append(imobiliaria)

        return imobiliarias

    def criar_loteamentos(self, imobiliarias, num_loteamentos, lotes_por_loteamento):
        """Cria Loteamentos com Lotes"""
        lotes = []
        nomes_loteamentos = [
            'Residencial Lagoa Dourada',
            'Condomínio Parque das Águas'
        ]

        for i in range(num_loteamentos):
            imobiliaria = imobiliarias[i % len(imobiliarias)]
            nome_loteamento = nomes_loteamentos[i]

            for lote_num in range(1, lotes_por_loteamento + 1):
                quadra = (lote_num - 1) // 10 + 1
                lote_na_quadra = (lote_num - 1) % 10 + 1

                area = Decimal(random.randint(250, 500))

                lote = Imovel.objects.create(
                    imobiliaria=imobiliaria,
                    tipo=TipoImovel.LOTE,
                    identificacao=f'Quadra {quadra}, Lote {lote_na_quadra:02d}',
                    loteamento=nome_loteamento,
                    endereco=f'Quadra {quadra}, Lote {lote_na_quadra:02d} - {nome_loteamento} - Sete Lagoas/MG',
                    area=area,
                    matricula=f'{20000+i*1000+lote_num}',
                    inscricao_municipal=f'{10000+i*1000+lote_num}',
                    disponivel=False,  # Será vendido
                    ativo=True
                )
                lotes.append(lote)

        return lotes

    def criar_terrenos(self, imobiliarias, quantidade):
        """Cria Terrenos"""
        terrenos = []
        bairros = ['Centro', 'Progresso', 'Santa Luzia', 'Várzea', 'Canaan']

        for i in range(quantidade):
            imobiliaria = random.choice(imobiliarias)
            bairro = random.choice(bairros)
            area = Decimal(random.randint(400, 1000))

            terreno = Imovel.objects.create(
                imobiliaria=imobiliaria,
                tipo=TipoImovel.TERRENO,
                identificacao=f'Terreno {i+1}',
                loteamento=f'Bairro {bairro}',
                endereco=f'Rua {self.fake.street_name()}, {random.randint(100, 999)} - {bairro} - Sete Lagoas/MG',
                area=area,
                matricula=f'{30000+i}',
                inscricao_municipal=f'{15000+i}',
                disponivel=False,
                ativo=True
            )
            terrenos.append(terreno)

        return terrenos

    def criar_compradores(self, quantidade):
        """Cria Compradores"""
        compradores = []

        for i in range(quantidade):
            nome = self.fake.name()
            cpf = self.gerar_cpf()

            comprador = Comprador.objects.create(
                nome=nome,
                cpf=cpf,
                rg=f'{random.randint(10000000, 99999999)}',
                data_nascimento=self.fake.date_of_birth(minimum_age=25, maximum_age=65),
                estado_civil=random.choice(['SOLTEIRO', 'CASADO', 'DIVORCIADO', 'VIUVO']),
                profissao=self.fake.job(),
                endereco=f'{self.fake.street_address()} - {random.choice(["Centro", "Progresso", "Canaan"])} - Sete Lagoas/MG',
                telefone=f'(31) {random.randint(3000, 3999)}-{random.randint(1000, 9999)}',
                celular=f'(31) {random.randint(90000, 99999)}-{random.randint(1000, 9999)}',
                email=f'{nome.lower().replace(" ", ".")}@email.com',
                notificar_email=True,
                notificar_sms=random.choice([True, False]),
                notificar_whatsapp=random.choice([True, False]),
                ativo=True
            )
            compradores.append(comprador)

        return compradores

    def criar_contratos(self, imoveis, compradores, imobiliarias):
        """Cria Contratos de 180 a 300 meses"""
        contratos = []
        compradores_disponiveis = compradores.copy()
        random.shuffle(compradores_disponiveis)

        for i, imovel in enumerate(imoveis):
            if not compradores_disponiveis:
                break

            comprador = compradores_disponiveis.pop()

            # Contratos nos últimos 24 meses
            dias_atras = random.randint(0, 730)  # 0 a 24 meses
            data_contrato = timezone.now().date() - timedelta(days=dias_atras)

            # 180 a 300 meses
            numero_parcelas = random.randint(180, 300)

            # Valor do imóvel baseado na área
            valor_m2 = Decimal(random.randint(150, 350))
            valor_total = imovel.area * valor_m2

            # Entrada de 10% a 30%
            valor_entrada = valor_total * Decimal(random.randint(10, 30) / 100)

            # Primeiro vencimento 30 dias após a compra
            data_primeiro_vencimento = data_contrato + timedelta(days=30)

            contrato = Contrato.objects.create(
                imovel=imovel,
                comprador=comprador,
                imobiliaria=imovel.imobiliaria,
                numero_contrato=f'CTR-{data_contrato.year}-{i+1:04d}',
                data_contrato=data_contrato,
                data_primeiro_vencimento=data_primeiro_vencimento,
                valor_total=valor_total,
                valor_entrada=valor_entrada,
                numero_parcelas=numero_parcelas,
                dia_vencimento=random.choice([5, 10, 15, 20, 25]),
                percentual_juros_mora=Decimal('1.00'),
                percentual_multa=Decimal('2.00'),
                tipo_correcao=random.choice([TipoCorrecao.IPCA, TipoCorrecao.IGPM, TipoCorrecao.SELIC]),
                prazo_reajuste_meses=12,
                status=StatusContrato.ATIVO,
                observacoes=f'Contrato gerado automaticamente para teste'
            )
            contratos.append(contrato)

        return contratos

    def marcar_parcelas_pagas(self, contratos, percentual=0.90):
        """Marca 90% das parcelas como pagas"""
        for contrato in contratos:
            parcelas = list(contrato.parcelas.all().order_by('numero_parcela'))
            total_parcelas = len(parcelas)
            parcelas_a_pagar = int(total_parcelas * percentual)

            # Pagar as primeiras X parcelas
            for i in range(parcelas_a_pagar):
                parcela = parcelas[i]

                # Data de pagamento entre vencimento e 10 dias depois
                dias_apos_vencimento = random.randint(0, 10)
                data_pagamento = parcela.data_vencimento + timedelta(days=dias_apos_vencimento)

                # Calcular juros e multa se pago com atraso
                if data_pagamento > parcela.data_vencimento:
                    juros, multa = parcela.calcular_juros_multa(data_pagamento)
                    parcela.valor_juros = juros
                    parcela.valor_multa = multa

                valor_pago = parcela.valor_atual + parcela.valor_juros + parcela.valor_multa

                parcela.registrar_pagamento(
                    valor_pago=valor_pago,
                    data_pagamento=data_pagamento,
                    observacoes='Pagamento gerado automaticamente para teste'
                )

    def gerar_cpf(self):
        """Gera um CPF fictício formatado"""
        cpf = [random.randint(0, 9) for _ in range(9)]

        # Calcular primeiro dígito verificador
        soma = sum((10 - i) * cpf[i] for i in range(9))
        digito1 = (soma * 10 % 11) % 10
        cpf.append(digito1)

        # Calcular segundo dígito verificador
        soma = sum((11 - i) * cpf[i] for i in range(10))
        digito2 = (soma * 10 % 11) % 10
        cpf.append(digito2)

        return f'{cpf[0]}{cpf[1]}{cpf[2]}.{cpf[3]}{cpf[4]}{cpf[5]}.{cpf[6]}{cpf[7]}{cpf[8]}-{cpf[9]}{cpf[10]}'
