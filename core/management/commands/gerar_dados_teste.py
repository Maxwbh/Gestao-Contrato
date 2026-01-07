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
import unicodedata
import re
from decimal import Decimal
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from faker import Faker

from core.models import Contabilidade, Imobiliaria, Imovel, Comprador, TipoImovel, ContaBancaria
from contratos.models import Contrato, TipoCorrecao, StatusContrato, IndiceReajuste, PrestacaoIntermediaria
from financeiro.models import Parcela, Reajuste
from portal_comprador.models import AcessoComprador
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Gera massa de dados de teste para o sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limpar',
            action='store_true',
            help='Limpa todos os dados antes de gerar novos',
        )

    def normalizar_email(self, texto):
        """Remove acentos e caracteres especiais para criar um email válido"""
        # Remove acentos
        texto = unicodedata.normalize('NFD', texto)
        texto = texto.encode('ascii', 'ignore').decode('utf-8')
        # Substitui espaços por pontos e remove caracteres inválidos
        texto = texto.lower().replace(' ', '.')
        texto = re.sub(r'[^a-z0-9.@]', '', texto)
        # Remove pontos consecutivos
        texto = re.sub(r'\.+', '.', texto)
        # Remove ponto no início ou fim do local part (antes do @)
        partes = texto.split('@')
        if len(partes) == 2:
            local = partes[0].strip('.')
            dominio = partes[1].strip('.')
            texto = f'{local}@{dominio}'
        return texto

    def handle(self, *args, **options):
        self.fake = Faker('pt_BR')
        Faker.seed(12345)  # Para dados consistentes
        random.seed(12345)

        if options['limpar']:
            self.stdout.write(self.style.WARNING('Limpando dados existentes...'))
            self.limpar_dados()

        self.stdout.write(self.style.SUCCESS('Iniciando geração de dados de teste...'))

        try:
            with transaction.atomic():
                # 1. Criar Contabilidade
                self.stdout.write('Criando Contabilidade...')
                contabilidade = self.criar_contabilidade()

                # 2. Criar 2 Imobiliárias
                self.stdout.write('Criando Imobiliárias...')
                imobiliarias = self.criar_imobiliarias(contabilidade, 2)

                # 2.1 Criar Contas Bancárias para cada imobiliária
                self.stdout.write('Criando Contas Bancárias...')
                contas_bancarias = self.criar_contas_bancarias(imobiliarias)

                # 3. Criar 2 Loteamentos com 30 Lotes cada
                self.stdout.write('Criando Loteamentos...')
                lotes = self.criar_loteamentos(imobiliarias, 2, 30)

                # 4. Criar 5 Terrenos
                self.stdout.write('Criando Terrenos...')
                terrenos = self.criar_terrenos(imobiliarias, 5)

                # 5. Criar 60 Compradores (80% PF, 20% PJ)
                self.stdout.write('Criando Compradores (PF e PJ)...')
                compradores = self.criar_compradores(60)

                # 6. Criar Contratos
                self.stdout.write('Criando Contratos...')
                imoveis = lotes + terrenos
                contratos = self.criar_contratos(imoveis, compradores, imobiliarias)

                # 7. Remover parcelas futuras (manter apenas até o mês atual)
                self.stdout.write('Removendo parcelas futuras...')
                parcelas_removidas = self.remover_parcelas_futuras()
                self.stdout.write(f'   {parcelas_removidas} parcelas futuras removidas')

                # 8. Marcar 90% das parcelas como pagas
                self.stdout.write('Marcando parcelas como pagas...')
                self.marcar_parcelas_pagas(contratos, 0.90)

                # 9. Gerar índices de reajuste
                self.stdout.write('Gerando índices de reajuste...')
                indices = self.gerar_indices_reajuste()

                # 10. Criar prestações intermediárias para alguns contratos
                self.stdout.write('Criando prestações intermediárias...')
                intermediarias = self.criar_prestacoes_intermediarias(contratos)

                # 11. Criar acessos ao portal para alguns compradores
                self.stdout.write('Criando acessos ao portal do comprador...')
                acessos = self.criar_acessos_portal(compradores)

                # 12. Criar reajustes aplicados para contratos antigos
                self.stdout.write('Criando reajustes aplicados...')
                reajustes = self.criar_reajustes_aplicados(contratos)

            # Contagem final
            pf_count = len([c for c in compradores if c.tipo_pessoa == 'PF'])
            pj_count = len([c for c in compradores if c.tipo_pessoa == 'PJ'])

            self.stdout.write(self.style.SUCCESS('\n✅ Dados gerados com sucesso!'))
            self.stdout.write(self.style.SUCCESS(f'   • 1 Contabilidade'))
            self.stdout.write(self.style.SUCCESS(f'   • 2 Imobiliárias'))
            self.stdout.write(self.style.SUCCESS(f'   • {len(contas_bancarias)} Contas Bancárias'))
            self.stdout.write(self.style.SUCCESS(f'   • {len(lotes)} Lotes'))
            self.stdout.write(self.style.SUCCESS(f'   • {len(terrenos)} Terrenos'))
            self.stdout.write(self.style.SUCCESS(f'   • {len(compradores)} Compradores ({pf_count} PF + {pj_count} PJ)'))
            self.stdout.write(self.style.SUCCESS(f'   • {len(contratos)} Contratos'))
            self.stdout.write(self.style.SUCCESS(f'   • {intermediarias} Prestações Intermediárias'))
            self.stdout.write(self.style.SUCCESS(f'   • {acessos} Acessos ao Portal'))
            self.stdout.write(self.style.SUCCESS(f'   • {reajustes} Reajustes Aplicados'))
            self.stdout.write(self.style.SUCCESS(f'   • {indices} Índices de Reajuste'))

        except Exception as e:
            import traceback
            self.stdout.write(self.style.ERROR('\n❌ ERRO NA GERAÇÃO DE DADOS'))
            self.stdout.write(self.style.ERROR('=' * 60))
            self.stdout.write(self.style.ERROR(f'Tipo: {type(e).__name__}'))
            self.stdout.write(self.style.ERROR(f'Mensagem: {str(e)}'))

            # Se for ValidationError, mostrar detalhes dos campos
            if hasattr(e, 'message_dict'):
                self.stdout.write(self.style.ERROR('\nErros de validação por campo:'))
                for field, errors in e.message_dict.items():
                    self.stdout.write(self.style.ERROR(f'  • {field}: {errors}'))

            # Mostrar traceback completo
            self.stdout.write(self.style.ERROR('\nTraceback completo:'))
            self.stdout.write(self.style.ERROR(traceback.format_exc()))
            self.stdout.write(self.style.ERROR('=' * 60))

            # Re-lançar a exceção para que seja capturada pela view
            raise

    def limpar_dados(self):
        """Limpa todos os dados de teste"""
        # Portal do Comprador
        AcessoComprador.objects.all().delete()
        User.objects.filter(username__startswith='comprador_').delete()

        # Financeiro
        Reajuste.objects.all().delete()
        Parcela.objects.all().delete()

        # Contratos
        PrestacaoIntermediaria.objects.all().delete()
        Contrato.objects.all().delete()
        IndiceReajuste.objects.all().delete()

        # Core
        Imovel.objects.all().delete()
        Comprador.objects.all().delete()
        ContaBancaria.objects.all().delete()
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
        """Cria Imobiliárias com endereço estruturado"""
        imobiliarias = []
        dados = [
            {
                'nome': 'Imobiliária Lagoa Real',
                'cep': '35700-000',
                'logradouro': 'Av. Prefeito Alberto Moura',
                'numero': '100',
                'bairro': 'Centro',
                'cidade': 'Sete Lagoas',
                'estado': 'MG'
            },
            {
                'nome': 'Imobiliária Sete Colinas',
                'cep': '35701-000',
                'logradouro': 'Rua Monsenhor Messias',
                'numero': '250',
                'bairro': 'Progresso',
                'cidade': 'Sete Lagoas',
                'estado': 'MG'
            }
        ]

        for i, d in enumerate(dados[:quantidade]):
            imobiliaria = Imobiliaria.objects.create(
                contabilidade=contabilidade,
                nome=d['nome'],
                razao_social=f'{d["nome"]} Negócios Imobiliários LTDA',
                cnpj=f'23.456.78{i}/0001-{10+i}',
                cep=d['cep'],
                logradouro=d['logradouro'],
                numero=d['numero'],
                bairro=d['bairro'],
                cidade=d['cidade'],
                estado=d['estado'],
                telefone=f'(31) 3773-{2000+i*100}',
                email=f'contato@{d["nome"].lower().replace(" ", "")}.com.br',
                responsavel_financeiro=self.fake.name(),
                banco='Banco do Brasil',
                agencia=f'{3000+i}',
                conta=f'{50000+i*1000}-{i}',
                pix=f'pix@{d["nome"].lower().replace(" ", "")}.com.br',
                ativo=True
            )
            imobiliarias.append(imobiliaria)

        return imobiliarias

    def criar_contas_bancarias(self, imobiliarias):
        """
        Cria Contas Bancárias para cada imobiliária.
        Configura os campos obrigatórios conforme documentação BRCobranca.
        """
        contas = []

        # Configuração apenas para BB, Sicoob e Bradesco
        bancos_config = [
            {
                'banco': '001',  # Banco do Brasil
                'descricao': 'Conta Principal BB',
                'agencia': '3073',
                'agencia_dv': '0',
                'conta': '12345678',
                'conta_dv': '9',
                'convenio': '1234567',  # 7 dígitos obrigatório
                'carteira': '18',
                'nosso_numero_atual': 1,
            },
            {
                'banco': '756',  # Sicoob
                'descricao': 'Conta Sicoob',
                'agencia': '3073',
                'agencia_dv': '0',
                'conta': '12345678',  # max 8 dígitos
                'conta_dv': '5',
                'convenio': '1234567',  # max 7 dígitos
                'carteira': '1',
                'nosso_numero_atual': 1,
            },
            {
                'banco': '237',  # Bradesco
                'descricao': 'Conta Bradesco',
                'agencia': '1234',
                'agencia_dv': '5',
                'conta': '1234567',  # max 7 dígitos
                'conta_dv': '0',
                'convenio': '',
                'carteira': '06',
                'nosso_numero_atual': 1,
            },
        ]

        for imobiliaria in imobiliarias:
            # Criar todas as 3 contas (BB, Sicoob, Bradesco) para cada imobiliária
            for i, config in enumerate(bancos_config):
                # Mesclar agencia_dv com agencia se fornecido
                agencia = config.get('agencia', '')
                agencia_dv = config.get('agencia_dv', '')
                if agencia and agencia_dv:
                    agencia_completa = f"{agencia}-{agencia_dv}"
                else:
                    agencia_completa = agencia

                # Mesclar conta_dv com conta se fornecido
                conta_numero = config.get('conta', '')
                conta_dv = config.get('conta_dv', '')
                if conta_numero and conta_dv:
                    conta_completa = f"{conta_numero}-{conta_dv}"
                else:
                    conta_completa = conta_numero

                conta = ContaBancaria.objects.create(
                    imobiliaria=imobiliaria,
                    banco=config['banco'],
                    descricao=f"{config['descricao']} - {imobiliaria.nome}",
                    principal=(i == 0),  # BB é a principal
                    agencia=agencia_completa,
                    conta=conta_completa,
                    convenio=config['convenio'],
                    carteira=config['carteira'],
                    nosso_numero_atual=config['nosso_numero_atual'],
                    cobranca_registrada=True,
                    prazo_baixa=30,
                    prazo_protesto=0,
                    layout_cnab='CNAB_240',
                    numero_remessa_cnab_atual=1,
                    ativo=True
                )
                contas.append(conta)

        return contas

    def criar_loteamentos(self, imobiliarias, num_loteamentos, lotes_por_loteamento):
        """
        Cria Loteamentos com Lotes.
        Últimos 20% dos lotes de cada loteamento ficam disponíveis (não vendidos).
        """
        lotes = []
        lotes_disponiveis = []
        nomes_loteamentos = [
            'Residencial Lagoa Dourada',
            'Condomínio Parque das Águas'
        ]

        # Quantidade de lotes que ficarão disponíveis (não vendidos) - 20%
        lotes_nao_vendidos = int(lotes_por_loteamento * 0.20)

        for i in range(num_loteamentos):
            imobiliaria = imobiliarias[i % len(imobiliarias)]
            nome_loteamento = nomes_loteamentos[i]

            for lote_num in range(1, lotes_por_loteamento + 1):
                quadra = (lote_num - 1) // 10 + 1
                lote_na_quadra = (lote_num - 1) % 10 + 1

                area = Decimal(random.randint(250, 500))
                valor_m2 = Decimal(random.randint(150, 350))
                valor_lote = area * valor_m2

                # Últimos lotes ficam disponíveis (não vendidos)
                disponivel = lote_num > (lotes_por_loteamento - lotes_nao_vendidos)

                lote = Imovel.objects.create(
                    imobiliaria=imobiliaria,
                    tipo=TipoImovel.LOTE,
                    identificacao=f'Quadra {quadra}, Lote {lote_na_quadra:02d}',
                    loteamento=nome_loteamento,
                    cep='35700-000',
                    logradouro=f'Rua {quadra}',
                    numero=str(lote_na_quadra),
                    bairro=nome_loteamento,
                    cidade='Sete Lagoas',
                    estado='MG',
                    endereco=f'Quadra {quadra}, Lote {lote_na_quadra:02d} - {nome_loteamento} - Sete Lagoas/MG',
                    area=area,
                    valor=valor_lote,
                    matricula=f'{20000+i*1000+lote_num}',
                    inscricao_municipal=f'{10000+i*1000+lote_num}',
                    disponivel=disponivel,
                    ativo=True
                )

                if disponivel:
                    lotes_disponiveis.append(lote)
                else:
                    lotes.append(lote)

        self.stdout.write(f'   → {len(lotes_disponiveis)} lotes disponíveis (não vendidos)')
        return lotes  # Retorna apenas os lotes vendidos para criar contratos

    def criar_terrenos(self, imobiliarias, quantidade):
        """
        Cria Terrenos com endereço estruturado.
        20% dos terrenos ficam disponíveis (não vendidos).
        """
        terrenos = []
        terrenos_disponiveis = []
        bairros = ['Centro', 'Progresso', 'Santa Luzia', 'Várzea', 'Canaan']
        ceps = ['35700-000', '35701-000', '35702-000', '35703-000']

        # 20% dos terrenos ficam disponíveis
        terrenos_nao_vendidos = int(quantidade * 0.20)

        for i in range(quantidade):
            imobiliaria = random.choice(imobiliarias)
            bairro = random.choice(bairros)
            area = Decimal(random.randint(400, 1000))
            valor_m2 = Decimal(random.randint(200, 450))
            valor_terreno = area * valor_m2
            rua = self.fake.street_name()
            numero = str(random.randint(100, 999))

            # Últimos terrenos ficam disponíveis
            disponivel = i >= (quantidade - terrenos_nao_vendidos)

            terreno = Imovel.objects.create(
                imobiliaria=imobiliaria,
                tipo=TipoImovel.TERRENO,
                identificacao=f'Terreno {i+1}',
                loteamento=f'Bairro {bairro}',
                cep=random.choice(ceps),
                logradouro=rua,
                numero=numero,
                bairro=bairro,
                cidade='Sete Lagoas',
                estado='MG',
                endereco=f'Rua {rua}, {numero} - {bairro} - Sete Lagoas/MG',
                area=area,
                valor=valor_terreno,
                matricula=f'{30000+i}',
                inscricao_municipal=f'{15000+i}',
                disponivel=disponivel,
                ativo=True
            )

            if disponivel:
                terrenos_disponiveis.append(terreno)
            else:
                terrenos.append(terreno)

        self.stdout.write(f'   → {len(terrenos_disponiveis)} terrenos disponíveis (não vendidos)')
        return terrenos  # Retorna apenas os terrenos vendidos para criar contratos

    def criar_compradores(self, quantidade):
        """Cria Compradores - 80% Pessoa Física, 20% Pessoa Jurídica"""
        compradores = []
        bairros = ['Centro', 'Progresso', 'Santa Luzia', 'Várzea', 'Canaan', 'Cidade Nova']
        ceps = ['35700-000', '35701-000', '35702-000', '35703-000']

        # 80% PF, 20% PJ
        qtd_pf = int(quantidade * 0.8)
        qtd_pj = quantidade - qtd_pf

        # Criar Pessoas Físicas
        for i in range(qtd_pf):
            nome = self.fake.name()
            cpf = self.gerar_cpf()
            bairro = random.choice(bairros)
            estado_civil = random.choice(['SOLTEIRO', 'CASADO', 'DIVORCIADO', 'VIUVO'])

            comprador = Comprador.objects.create(
                tipo_pessoa='PF',
                nome=nome,
                cpf=cpf,
                rg=f'{random.randint(10000000, 99999999)}',
                data_nascimento=self.fake.date_of_birth(minimum_age=25, maximum_age=65),
                estado_civil=estado_civil,
                profissao=self.fake.job()[:100],
                # Endereço estruturado
                cep=random.choice(ceps),
                logradouro=self.fake.street_name(),
                numero=str(random.randint(1, 999)),
                bairro=bairro,
                cidade='Sete Lagoas',
                estado='MG',
                # Contato
                telefone=f'(31) {random.randint(3000, 3999)}-{random.randint(1000, 9999)}',
                celular=f'(31) 9{random.randint(8000, 9999)}-{random.randint(1000, 9999)}',
                email=self.normalizar_email(f'{nome}@email.com')[:100],
                notificar_email=True,
                notificar_sms=random.choice([True, False]),
                notificar_whatsapp=random.choice([True, False]),
                # Cônjuge (se casado)
                conjuge_nome=self.fake.name() if estado_civil == 'CASADO' else '',
                conjuge_cpf=self.gerar_cpf() if estado_civil == 'CASADO' else '',
                ativo=True
            )
            compradores.append(comprador)

        # Criar Pessoas Jurídicas
        tipos_empresa = ['Construtora', 'Incorporadora', 'Investimentos', 'Participações', 'Holdings']
        for i in range(qtd_pj):
            razao_social = f'{self.fake.company()} {random.choice(tipos_empresa)} LTDA'
            nome_fantasia = razao_social.split()[0] + ' ' + razao_social.split()[1]
            cnpj = self.gerar_cnpj()
            bairro = random.choice(bairros)

            comprador = Comprador.objects.create(
                tipo_pessoa='PJ',
                nome=razao_social[:200],
                # Campos PF com valores para PJ (constraints do banco)
                cpf=self.gerar_cpf(),  # CPF fictício único (constraint UNIQUE no banco)
                rg='',
                data_nascimento=None,
                estado_civil='',
                profissao='',
                # Campos PJ
                cnpj=cnpj,
                nome_fantasia=nome_fantasia[:200],
                inscricao_estadual=f'{random.randint(100, 999)}.{random.randint(100, 999)}.{random.randint(100, 999)}',
                inscricao_municipal=f'{random.randint(10000, 99999)}',
                responsavel_legal=self.fake.name(),
                responsavel_cpf=self.gerar_cpf(),
                # Endereço estruturado
                cep=random.choice(ceps),
                logradouro=self.fake.street_name(),
                numero=str(random.randint(1, 999)),
                complemento=random.choice(['Sala 01', 'Sala 02', 'Loja', '', '']),
                bairro=bairro,
                cidade='Sete Lagoas',
                estado='MG',
                # Contato
                telefone=f'(31) {random.randint(3000, 3999)}-{random.randint(1000, 9999)}',
                celular=f'(31) 9{random.randint(8000, 9999)}-{random.randint(1000, 9999)}',
                email=self.normalizar_email(f'contato@{nome_fantasia}.com.br')[:100],
                notificar_email=True,
                notificar_sms=False,
                notificar_whatsapp=True,
                ativo=True
            )
            compradores.append(comprador)

        random.shuffle(compradores)
        return compradores

    def criar_contratos(self, imoveis, compradores, imobiliarias):
        """
        Cria Contratos com parcelas até a data de hoje.
        O número de parcelas é limitado para não ultrapassar a data atual.
        """
        contratos = []
        compradores_disponiveis = compradores.copy()
        random.shuffle(compradores_disponiveis)
        hoje = timezone.now().date()

        for i, imovel in enumerate(imoveis):
            if not compradores_disponiveis:
                break

            comprador = compradores_disponiveis.pop()

            # Contratos nos últimos 24 meses
            dias_atras = random.randint(60, 730)  # Mínimo 2 meses atrás
            data_contrato = hoje - timedelta(days=dias_atras)

            # Primeiro vencimento 30 dias após a compra
            data_primeiro_vencimento = data_contrato + timedelta(days=30)

            # Calcular quantas parcelas cabem até hoje
            meses_desde_contrato = (hoje.year - data_primeiro_vencimento.year) * 12 + \
                                   (hoje.month - data_primeiro_vencimento.month)

            # Limitar parcelas entre 6 e o máximo que cabe até hoje
            max_parcelas = max(6, min(meses_desde_contrato + 1, 48))
            numero_parcelas = random.randint(min(6, max_parcelas), max_parcelas)

            # Valor do imóvel baseado na área (garantir precisão decimal)
            area = Decimal(str(imovel.area)).quantize(Decimal('0.01'))
            valor_m2 = Decimal(str(random.randint(150, 350)))
            valor_total = (area * valor_m2).quantize(Decimal('0.01'))

            # Limitar valor_total a 9 dígitos inteiros (max 999,999,999.99)
            max_valor = Decimal('999999999.99')
            if valor_total > max_valor:
                valor_total = max_valor

            # Entrada de 10% a 30% (quantizado para 2 casas decimais)
            percentual = Decimal(str(random.randint(10, 30))) / Decimal('100')
            valor_entrada = (valor_total * percentual).quantize(Decimal('0.01'))

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
                tipo_correcao=random.choice([
                    TipoCorrecao.IPCA, TipoCorrecao.IGPM, TipoCorrecao.INCC,
                    TipoCorrecao.IGPDI, TipoCorrecao.INPC, TipoCorrecao.TR
                ]),
                prazo_reajuste_meses=12,
                status=StatusContrato.ATIVO,
                observacoes=f'Contrato gerado automaticamente para teste'
            )
            contratos.append(contrato)

        return contratos

    def remover_parcelas_futuras(self):
        """Remove parcelas com vencimento após o mês atual"""
        from dateutil.relativedelta import relativedelta

        # Último dia do mês atual
        hoje = timezone.now().date()
        ultimo_dia_mes = hoje.replace(day=1) + relativedelta(months=1) - relativedelta(days=1)

        # Deletar parcelas com vencimento futuro
        parcelas_futuras = Parcela.objects.filter(data_vencimento__gt=ultimo_dia_mes)
        count = parcelas_futuras.count()
        parcelas_futuras.delete()

        return count

    def marcar_parcelas_pagas(self, contratos, percentual=0.90):
        """Marca parcelas como pagas (somente parcelas vencidas até a data atual)"""
        hoje = timezone.now().date()

        for contrato in contratos:
            # Filtrar apenas parcelas com vencimento até hoje
            parcelas = list(contrato.parcelas.filter(
                data_vencimento__lte=hoje
            ).order_by('numero_parcela'))

            total_parcelas = len(parcelas)
            parcelas_a_pagar = int(total_parcelas * percentual)

            for i in range(parcelas_a_pagar):
                parcela = parcelas[i]

                # Data de pagamento entre vencimento e no máximo hoje
                dias_apos_vencimento = random.randint(0, 10)
                data_pagamento = parcela.data_vencimento + timedelta(days=dias_apos_vencimento)

                # Garantir que data de pagamento não ultrapasse hoje
                if data_pagamento > hoje:
                    data_pagamento = hoje

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

        soma = sum((10 - i) * cpf[i] for i in range(9))
        digito1 = (soma * 10 % 11) % 10
        cpf.append(digito1)

        soma = sum((11 - i) * cpf[i] for i in range(10))
        digito2 = (soma * 10 % 11) % 10
        cpf.append(digito2)

        return f'{cpf[0]}{cpf[1]}{cpf[2]}.{cpf[3]}{cpf[4]}{cpf[5]}.{cpf[6]}{cpf[7]}{cpf[8]}-{cpf[9]}{cpf[10]}'

    def gerar_cnpj(self):
        """Gera um CNPJ fictício formatado"""
        cnpj = [random.randint(0, 9) for _ in range(8)] + [0, 0, 0, 1]

        # Primeiro dígito verificador
        pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(cnpj[i] * pesos1[i] for i in range(12))
        resto = soma % 11
        digito1 = 0 if resto < 2 else 11 - resto
        cnpj.append(digito1)

        # Segundo dígito verificador
        pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(cnpj[i] * pesos2[i] for i in range(13))
        resto = soma % 11
        digito2 = 0 if resto < 2 else 11 - resto
        cnpj.append(digito2)

        return f'{cnpj[0]}{cnpj[1]}.{cnpj[2]}{cnpj[3]}{cnpj[4]}.{cnpj[5]}{cnpj[6]}{cnpj[7]}/{cnpj[8]}{cnpj[9]}{cnpj[10]}{cnpj[11]}-{cnpj[12]}{cnpj[13]}'

    def gerar_indices_reajuste(self):
        """
        Gera índices de reajuste mensais para os últimos 36 meses.
        Valores baseados em médias históricas reais.
        """
        count = 0
        hoje = timezone.now().date()

        # Configuração dos índices com médias históricas aproximadas
        indices_config = [
            ('IPCA', 0.30, 0.80, 'IBGE/SIDRA'),      # IPCA: 0.3% a 0.8%
            ('IGPM', 0.20, 1.00, 'BCB/FGV'),         # IGP-M: 0.2% a 1.0%
            ('INCC', 0.25, 0.70, 'BCB/FGV'),         # INCC: 0.25% a 0.7%
            ('IGPDI', 0.20, 0.90, 'BCB/FGV'),        # IGP-DI: 0.2% a 0.9%
            ('INPC', 0.25, 0.75, 'IBGE/SIDRA'),      # INPC: 0.25% a 0.75%
            ('TR', 0.00, 0.15, 'BCB'),               # TR: 0% a 0.15%
            ('SELIC', 0.80, 1.10, 'BCB'),            # SELIC: 0.8% a 1.1%
        ]

        # Gerar últimos 36 meses
        for meses_atras in range(36, 0, -1):
            data = hoje - timedelta(days=meses_atras * 30)
            ano = data.year
            mes = data.month

            for tipo, min_val, max_val, fonte in indices_config:
                # Gerar valor aleatório dentro da faixa
                valor = Decimal(str(round(random.uniform(min_val, max_val), 4)))

                # Calcular acumulado no ano (simplificado)
                acum_ano = None
                if mes > 1:
                    indices_ano = IndiceReajuste.objects.filter(
                        tipo_indice=tipo, ano=ano, mes__lt=mes
                    ).values_list('valor', flat=True)
                    if indices_ano:
                        acum = Decimal('1')
                        for v in indices_ano:
                            acum *= (1 + v / 100)
                        acum *= (1 + valor / 100)
                        acum_ano = (acum - 1) * 100

                IndiceReajuste.objects.update_or_create(
                    tipo_indice=tipo,
                    ano=ano,
                    mes=mes,
                    defaults={
                        'valor': valor,
                        'valor_acumulado_ano': acum_ano,
                        'valor_acumulado_12m': None,
                        'fonte': f'{fonte} (teste)',
                        'data_importacao': timezone.now(),
                    }
                )
                count += 1

        return count

    def criar_prestacoes_intermediarias(self, contratos):
        """
        Cria prestações intermediárias para alguns contratos.
        30% dos contratos terão entre 1 e 5 prestações intermediárias.
        """
        count = 0
        contratos_com_intermediarias = random.sample(
            contratos,
            k=int(len(contratos) * 0.30)
        )

        for contrato in contratos_com_intermediarias:
            # Número de intermediárias: 1 a 5
            num_intermediarias = random.randint(1, 5)

            # Atualizar campo do contrato
            if hasattr(contrato, 'quantidade_intermediarias'):
                contrato.quantidade_intermediarias = num_intermediarias
                contrato.save(update_fields=['quantidade_intermediarias'])

            for seq in range(1, num_intermediarias + 1):
                # Vencimento a cada 12 meses
                mes_vencimento = seq * 12

                # Valor: 5% a 15% do valor total do contrato
                percentual = Decimal(str(random.randint(5, 15))) / Decimal('100')
                valor_base = Decimal(str(contrato.valor_total)).quantize(Decimal('0.01'))
                valor = (valor_base * percentual).quantize(Decimal('0.01'))

                # 50% das intermediárias já estão pagas
                paga = random.choice([True, False])
                data_pagamento = None
                valor_pago = None

                if paga:
                    # Data de pagamento no mês do vencimento
                    from dateutil.relativedelta import relativedelta
                    data_base = contrato.data_primeiro_vencimento + relativedelta(months=mes_vencimento - 1)
                    if data_base <= timezone.now().date():
                        data_pagamento = data_base + timedelta(days=random.randint(0, 10))
                        if data_pagamento > timezone.now().date():
                            data_pagamento = timezone.now().date()
                        valor_pago = valor
                    else:
                        paga = False

                PrestacaoIntermediaria.objects.create(
                    contrato=contrato,
                    numero_sequencial=seq,
                    mes_vencimento=mes_vencimento,
                    valor=valor,
                    paga=paga,
                    data_pagamento=data_pagamento,
                    valor_pago=valor_pago,
                    observacoes=f'Prestação intermediária {seq} - gerada para teste'
                )
                count += 1

        return count

    def criar_acessos_portal(self, compradores):
        """
        Cria acessos ao portal do comprador para 20% dos compradores.
        Usa CPF ou CNPJ como username.
        """
        count = 0
        compradores_com_acesso = random.sample(
            compradores,
            k=int(len(compradores) * 0.20)
        )

        for comprador in compradores_com_acesso:
            # Determinar documento (CPF ou CNPJ)
            if comprador.tipo_pessoa == 'PF':
                documento = comprador.cpf.replace('.', '').replace('-', '')
            else:
                documento = comprador.cnpj.replace('.', '').replace('/', '').replace('-', '')

            username = f'comprador_{documento}'

            # Verificar se usuário já existe
            if User.objects.filter(username=username).exists():
                continue

            # Criar usuário
            user = User.objects.create_user(
                username=username,
                email=comprador.email or f'{documento}@teste.com',
                password='teste123',  # Senha padrão para testes
                first_name=comprador.nome.split()[0] if comprador.nome else '',
                last_name=' '.join(comprador.nome.split()[1:3]) if comprador.nome else ''
            )

            # Criar acesso
            AcessoComprador.objects.create(
                comprador=comprador,
                usuario=user,
                email_verificado=True,  # Já verificado para testes
                ativo=True
            )
            count += 1

        self.stdout.write(f'   → Senha padrão para acessos de teste: teste123')
        return count

    def criar_reajustes_aplicados(self, contratos):
        """
        Cria reajustes aplicados para contratos com mais de 12 meses.
        Simula o processo de reajuste anual.
        """
        count = 0
        hoje = timezone.now().date()

        for contrato in contratos:
            # Calcular quantos ciclos completos de 12 meses se passaram
            meses_desde_contrato = (hoje.year - contrato.data_contrato.year) * 12 + \
                                   (hoje.month - contrato.data_contrato.month)

            ciclos_completos = meses_desde_contrato // 12

            if ciclos_completos < 1:
                continue

            # Criar reajuste para cada ciclo completo
            for ciclo in range(1, ciclos_completos + 1):
                # Data do reajuste (12 meses após o início do ciclo anterior)
                from dateutil.relativedelta import relativedelta
                data_reajuste = contrato.data_contrato + relativedelta(months=ciclo * 12)

                if data_reajuste > hoje:
                    continue

                # Percentual de reajuste (baseado em índices)
                percentual = Decimal(str(round(random.uniform(3.0, 8.0), 2)))

                # Verificar se já existe reajuste para este ciclo
                if Reajuste.objects.filter(contrato=contrato, ciclo=ciclo).exists():
                    continue

                Reajuste.objects.create(
                    contrato=contrato,
                    data_reajuste=data_reajuste,
                    indice_aplicado=contrato.tipo_correcao,
                    percentual_aplicado=percentual,
                    ciclo=ciclo,
                    aplicado=True,
                    data_aplicacao=timezone.make_aware(
                        datetime.combine(data_reajuste, datetime.min.time())
                    ),
                    observacoes=f'Reajuste ciclo {ciclo} - gerado para teste'
                )
                count += 1

                # Atualizar ciclo atual do contrato
                if hasattr(contrato, 'ciclo_reajuste_atual'):
                    contrato.ciclo_reajuste_atual = ciclo + 1
                    contrato.save(update_fields=['ciclo_reajuste_atual'])

        return count
