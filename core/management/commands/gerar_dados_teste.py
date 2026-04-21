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
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from faker import Faker

from core.models import Contabilidade, Imobiliaria, Imovel, Comprador, TipoImovel, ContaBancaria
from contratos.models import Contrato, TipoCorrecao, StatusContrato, IndiceReajuste, PrestacaoIntermediaria, TabelaJurosContrato
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

                # 6b. Criar contratos de cenários HU (determinísticos, para testes)
                self.stdout.write('Criando contratos de cenários HU (parcelas + reajuste + saldo devedor)...')
                contratos_cenarios = self.criar_contratos_cenarios_hu(imobiliarias, compradores)
                contratos += contratos_cenarios
                self.stdout.write(f'   {len(contratos_cenarios)} contratos de cenário criados')

                tabela_juros_count = TabelaJurosContrato.objects.count()

                # 7. Marcar 90% das parcelas VENCIDAS como pagas
                self.stdout.write('Marcando parcelas como pagas...')
                self.marcar_parcelas_pagas(contratos, 0.90)

                # 9. Simular boletos gerados para demonstração da remessa
                self.stdout.write('Simulando boletos gerados (para demo de remessa)...')
                boletos_simulados = self.simular_boletos_gerados(contratos, contas_bancarias)
                self.stdout.write(f'   {boletos_simulados} boletos simulados')

                # 10. Gerar índices de reajuste
                self.stdout.write('Gerando índices de reajuste...')
                indices = self.gerar_indices_reajuste()

                # 11. Criar prestações intermediárias para alguns contratos
                self.stdout.write('Criando prestações intermediárias...')
                intermediarias = self.criar_prestacoes_intermediarias(contratos)

                # 12. Criar acessos ao portal para alguns compradores
                self.stdout.write('Criando acessos ao portal do comprador...')
                acessos = self.criar_acessos_portal(compradores)

                # 13. Criar reajustes aplicados para contratos antigos
                self.stdout.write('Criando reajustes aplicados...')
                reajustes = self.criar_reajustes_aplicados(contratos)

                # 13b. Popular índices reais (IPCA e IGPM históricos das planilhas)
                self.stdout.write('Populando índices reais IPCA/IGPM (planilhas)...')
                indices_reais = self.popular_indices_reais()
                self.stdout.write(f'   {indices_reais} índices reais inseridos/atualizados')

                # 13c. Criar contratos reais (Uanda Silva + Henry Magno)
                self.stdout.write('Criando contratos reais (planilhas Uanda + Henry)...')
                contratos_reais = self.criar_contratos_reais(imobiliarias)
                self.stdout.write(f'   {len(contratos_reais)} contrato(s) real(is) criado(s)')

                # 14. Verificar dados para boleto e remessa
                self.stdout.write('Verificando integridade dos dados para boleto/remessa...')
                self.verificar_dados_boleto_remessa(contratos, contas_bancarias)

                # 15. Criar templates padrão de notificação (Email + SMS + WhatsApp)
                self.stdout.write('Criando templates padrão de notificação...')
                templates_criados = self.criar_templates_notificacao()
                self.stdout.write(f'   {templates_criados} templates criados/verificados')

                # 16. Gerar arquivo remessa CNAB para boletos simulados
                self.stdout.write('Gerando arquivos de remessa CNAB...')
                remessas_geradas = self.gerar_remessas_cnab()
                self.stdout.write(f'   {remessas_geradas} arquivo(s) de remessa gerado(s)')

                # 17. Simular retornos CNAB para dashboard de Conciliação Bancária
                self.stdout.write('Simulando retornos CNAB (dashboard Conciliação Bancária)...')
                retornos_cnab = self.simular_historico_conciliacao(contas_bancarias)

            # Contagem final
            pf_count = len([c for c in compradores if c.tipo_pessoa == 'PF'])
            pj_count = len([c for c in compradores if c.tipo_pessoa == 'PJ'])

            self.stdout.write(self.style.SUCCESS('\n✅ Dados gerados com sucesso!'))
            self.stdout.write(self.style.SUCCESS('   • 1 Contabilidade'))
            self.stdout.write(self.style.SUCCESS('   • 2 Imobiliárias'))
            self.stdout.write(self.style.SUCCESS(f'   • {len(contas_bancarias)} Contas Bancárias'))
            self.stdout.write(self.style.SUCCESS(f'   • {len(lotes)} Lotes'))
            self.stdout.write(self.style.SUCCESS(f'   • {len(terrenos)} Terrenos'))
            self.stdout.write(self.style.SUCCESS(f'   • {len(compradores)} Compradores ({pf_count} PF + {pj_count} PJ)'))
            self.stdout.write(self.style.SUCCESS(f'   • {len(contratos)} Contratos'))
            self.stdout.write(self.style.SUCCESS(f'   • {tabela_juros_count} Faixas de Juros Escalantes (TabelaJurosContrato)'))
            self.stdout.write(self.style.SUCCESS(f'   • {boletos_simulados} Boletos Simulados (prontos para remessa)'))
            self.stdout.write(self.style.SUCCESS(f'   • {remessas_geradas} Arquivos de Remessa CNAB gerados'))
            self.stdout.write(self.style.SUCCESS(f'   • {intermediarias} Prestações Intermediárias'))
            self.stdout.write(self.style.SUCCESS(f'   • {acessos} Acessos ao Portal'))
            self.stdout.write(self.style.SUCCESS(f'   • {reajustes} Reajustes Aplicados'))
            self.stdout.write(self.style.SUCCESS(f'   • {indices} Índices de Reajuste (gerados)'))
            self.stdout.write(self.style.SUCCESS(f'   • {indices_reais} Índices Reais IPCA/IGPM (planilhas)'))
            self.stdout.write(self.style.SUCCESS(f'   • {len(contratos_reais)} Contratos Reais (Uanda + Henry)'))
            self.stdout.write(self.style.SUCCESS(f'   • {templates_criados} Templates de Notificação (Email+SMS+WhatsApp)'))
            self.stdout.write(self.style.SUCCESS(f'   • {retornos_cnab} Arquivos de Retorno CNAB (conciliação bancária)'))

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
        """Limpa todos os dados de teste (tolerante a tabelas ausentes)."""
        from django.db import transaction as _tx, ProgrammingError, OperationalError

        def _safe_delete(model_class, label=''):
            """Apaga todos os registros usando savepoint — ignora tabela inexistente."""
            try:
                with _tx.atomic():  # savepoint: rollback só desta operação se falhar
                    model_class.objects.all().delete()
            except (ProgrammingError, OperationalError) as exc:
                if 'does not exist' in str(exc) or 'no such table' in str(exc):
                    self.stdout.write(
                        self.style.WARNING(f'  ⚠ Tabela {label or model_class.__name__} não existe — pulando.')
                    )
                else:
                    raise

        # CNAB (tabelas criadas por migration 0006 — podem não existir ainda)
        from financeiro.models import ArquivoRemessa, ArquivoRetorno
        _safe_delete(ArquivoRemessa, 'financeiro_arquivoremessa')
        _safe_delete(ArquivoRetorno, 'financeiro_arquivoretorno')

        # Notificações (registros de envio + templates padrão)
        try:
            from notificacoes.models import Notificacao, TemplateNotificacao
            _safe_delete(Notificacao, 'notificacoes_notificacao')
            # Remove apenas templates globais (sem imobiliária) para recriar os padrões
            TemplateNotificacao.objects.filter(imobiliaria__isnull=True).delete()
        except ImportError:
            pass

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
        """Cria 1 Contabilidade (get_or_create — idempotente)"""
        obj, created = Contabilidade.objects.get_or_create(
            cnpj='12.345.678/0001-90',
            defaults={
                'nome': 'Contabilidade Sete Lagoas',
                'razao_social': 'M&S Contabilidade e Consultoria LTDA',
                'endereco': 'Rua Principal, 123 - Centro - Sete Lagoas/MG - CEP: 35700-000',
                'telefone': '(31) 3773-1234',
                'email': 'contato@msbrasil.inf.br',
                'responsavel': 'Maxwell da Silva Oliveira',
                'ativo': True,
            }
        )
        if not created:
            self.stdout.write('   → Contabilidade já existe, reutilizando.')
        return obj

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
            cnpj = f'23.456.78{i}/0001-{10+i:02d}'
            imobiliaria, created = Imobiliaria.objects.get_or_create(
                cnpj=cnpj,
                defaults={
                    'contabilidade': contabilidade,
                    'tipo_pessoa': 'PJ',
                    'nome': d['nome'],
                    'razao_social': f'{d["nome"]} Negócios Imobiliários LTDA',
                    'cep': d['cep'],
                    'logradouro': d['logradouro'],
                    'numero': d['numero'],
                    'bairro': d['bairro'],
                    'cidade': d['cidade'],
                    'estado': d['estado'],
                    'telefone': f'(31) 3773-{2000+i*100}',
                    'email': f'contato@{d["nome"].lower().replace(" ", "")}.com.br',
                    'responsavel_financeiro': self.fake.name(),
                    'banco': 'Banco do Brasil',
                    'agencia': f'{3000+i}',
                    'conta': f'{50000+i*1000}-{i}',
                    'pix': f'pix@{d["nome"].lower().replace(" ", "")}.com.br',
                    'ativo': True,
                }
            )
            if not created:
                self.stdout.write(f'   → Imobiliária "{d["nome"]}" já existe, reutilizando.')
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
                'convenio': '12345678',  # 8 dígitos — BB: convenio(8) + seq(9) = 17
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

                conta, _ = ContaBancaria.objects.get_or_create(
                    imobiliaria=imobiliaria,
                    banco=config['banco'],
                    defaults=dict(
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
                        ativo=True,
                    )
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

        # Offset global para evitar colisão com contratos já existentes no banco
        seq_global = Contrato.objects.count()

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

            # 5% dos contratos são longos (120-360 parcelas) — representam loteamentos
            # Para esses, a data do contrato é recuada para caber mais parcelas
            if random.random() < 0.05:
                numero_parcelas = random.choice([120, 180, 240, 360])
                # Recua a data do contrato para ter pelo menos 24 meses decorridos
                dias_atras = random.randint(730, 1460)
                data_contrato = hoje - timedelta(days=dias_atras)
                data_primeiro_vencimento = data_contrato + timedelta(days=30)
            else:
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
                numero_contrato=f'CTR-{data_contrato.year}-{seq_global + i + 1:04d}',
                data_contrato=data_contrato,
                data_primeiro_vencimento=data_primeiro_vencimento,
                valor_total=valor_total,
                valor_entrada=valor_entrada,
                numero_parcelas=numero_parcelas,
                dia_vencimento=random.choice([5, 10, 15, 20, 25]),
                percentual_juros_mora=Decimal('1.00'),
                percentual_multa=Decimal('2.00'),
                tipo_correcao=random.choices(
                    [TipoCorrecao.IPCA, TipoCorrecao.IGPM, TipoCorrecao.INCC,
                     TipoCorrecao.IGPDI, TipoCorrecao.INPC, TipoCorrecao.TR,
                     TipoCorrecao.FIXO],
                    weights=[25, 20, 15, 10, 10, 10, 10], k=1
                )[0],
                prazo_reajuste_meses=12,
                # 30% dos contratos têm spread (0.5 a 2 p.p.)
                spread_reajuste=Decimal(str(round(random.uniform(0.5, 2.0), 4))) if random.random() < 0.3 else None,
                # 20% têm piso (0%)
                reajuste_piso=Decimal('0.0000') if random.random() < 0.2 else None,
                # 15% têm teto (entre 10% e 15%)
                reajuste_teto=Decimal(str(round(random.uniform(10.0, 15.0), 4))) if random.random() < 0.15 else None,
                # Fallback INPC para contratos com IGPM (20% de chance)
                tipo_correcao_fallback='INPC' if random.random() < 0.2 else '',
                # Cláusulas padrão
                percentual_fruicao=Decimal('0.5000'),
                percentual_multa_rescisao_penal=Decimal('10.0000'),
                percentual_multa_rescisao_adm=Decimal('12.0000'),
                percentual_cessao=Decimal('3.0000'),
                intermediarias_reduzem_pmt=random.random() < 0.3,
                intermediarias_reajustadas=random.random() < 0.7,
                tipo_amortizacao='SAC' if random.random() < 0.25 else 'PRICE',
                status=StatusContrato.ATIVO,
                observacoes='Contrato gerado automaticamente para teste'
            )
            contratos.append(contrato)

            # TabelaJurosContrato:
            # - FIXO: SEMPRE tem tabela com taxa pré-fixada realista (0.3% a 1.2% a.m.)
            # - Outros: 15% têm juros escalantes por ciclo
            eh_fixo = contrato.tipo_correcao == TipoCorrecao.FIXO
            tem_tabela_juros = eh_fixo or (random.random() < 0.15 and numero_parcelas >= 24)
            if tem_tabela_juros:
                if eh_fixo:
                    # Contrato pré-fixado: taxa única do início ao fim
                    taxa_fixa = Decimal(str(round(random.uniform(0.30, 1.20), 4)))
                    TabelaJurosContrato.objects.create(
                        contrato=contrato,
                        ciclo_inicio=1,
                        ciclo_fim=None,
                        juros_mensal=taxa_fixa,
                        observacoes='Taxa pré-fixada — gerado por dados de teste'
                    )
                else:
                    # Pós-fixado com juros escalantes por ciclo
                    faixas = [
                        (1, 1, Decimal('0.0000')),    # Ano 1: sem juros adicionais
                        (2, 2, Decimal('0.6000')),
                        (3, 3, Decimal('0.6500')),
                        (4, 4, Decimal('0.7000')),
                        (5, 5, Decimal('0.7500')),
                        (6, 6, Decimal('0.8000')),
                        (7, None, Decimal('0.8500')),  # Ano 7 em diante
                    ]
                    for ciclo_ini, ciclo_fim, juros in faixas:
                        TabelaJurosContrato.objects.create(
                            contrato=contrato,
                            ciclo_inicio=ciclo_ini,
                            ciclo_fim=ciclo_fim,
                            juros_mensal=juros,
                            observacoes='Gerado por dados de teste'
                        )
                # Recalcula parcelas com sistema correto (Price ou SAC) após TabelaJuros
                contrato.recalcular_amortizacao()

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

                # Variar origem de pagamento para testar conciliação
                origens_variaveis = ['MANUAL', 'MANUAL', 'CNAB', 'OFX', 'MANUAL']
                origem = origens_variaveis[i % len(origens_variaveis)]

                parcela.registrar_pagamento(
                    valor_pago=valor_pago,
                    data_pagamento=data_pagamento,
                    observacoes=f'Pagamento gerado automaticamente para teste ({origem})'
                )

                # Atualizar origem_pagamento no HistoricoPagamento recém criado
                from financeiro.models import HistoricoPagamento
                hist = HistoricoPagamento.objects.filter(parcela=parcela).order_by('-id').first()
                if hist and origem != 'MANUAL':
                    hist.origem_pagamento = origem
                    if origem == 'OFX':
                        hist.fitid_ofx = f'OFX{data_pagamento.strftime("%Y%m%d")}{parcela.pk:06d}'
                    hist.save(update_fields=['origem_pagamento', 'fitid_ofx'])

    def simular_boletos_gerados(self, contratos, contas_bancarias):
        """
        Gera boletos para parcelas VENCIDAS e pendentes, distribuindo entre TODAS
        as contas bancárias disponíveis (BB, Sicoob, Bradesco) de cada imobiliária.

        Estratégia:
          • API BRCobrança disponível → boletos REAIS via /api/boleto/multi em lotes
            de 10-20 registros (1 chamada à API por lote → PDFs reais armazenados).
          • API indisponível → fallback: popula campos sem PDF (dados suficientes
            para remessa CNAB e testes).

        Parcelas PAGAS não recebem boleto (não entram em remessa).
        """
        from financeiro.models import StatusBoleto
        from django.utils import timezone as tz

        hoje_date = tz.now().date()

        # ── Fase 1: Selecionar parcelas e atribuir contas (round-robin) ──────
        contas_por_imob: dict = {}
        for cb in contas_bancarias:
            contas_por_imob.setdefault(cb.imobiliaria_id, []).append(cb)
        for contas in contas_por_imob.values():
            contas.sort(key=lambda c: (not c.principal, c.banco))

        pares = []   # list of (parcela, conta)
        for idx, contrato in enumerate(contratos):
            contas_imob = contas_por_imob.get(contrato.imobiliaria_id)
            if not contas_imob:
                continue

            conta = contas_imob[idx % len(contas_imob)]

            parcelas_vencidas = list(
                contrato.parcelas.filter(
                    pago=False,
                    data_vencimento__lt=hoje_date,
                    status_boleto=StatusBoleto.NAO_GERADO,
                ).order_by('data_vencimento')[:5]
            )
            parcelas_a_vencer = list(
                contrato.parcelas.filter(
                    pago=False,
                    data_vencimento__gte=hoje_date,
                    status_boleto=StatusBoleto.NAO_GERADO,
                ).order_by('data_vencimento')[:2]
            )
            for parcela in (parcelas_vencidas or parcelas_a_vencer):
                if not parcela.pago:
                    pares.append((parcela, conta))

        if not pares:
            self.stdout.write('   Nenhuma parcela elegível para boleto.')
            return 0

        # ── Fase 2: Geração real ou simulada ─────────────────────────────────
        from financeiro.services.boleto_service import BoletoService
        service = BoletoService()

        if service.verificar_api_disponivel():
            self.stdout.write(
                f'   → API BRCobrança disponível — gerando {len(pares)} boletos reais '
                f'em lotes de 15 ({(len(pares) + 14) // 15} chamadas)...'
            )
            resultado = service.gerar_boletos_lote(pares, tamanho_lote=15)
            count = resultado['gerados']
            for e in resultado['erros']:
                self.stdout.write(self.style.WARNING(f'   ⚠ {e}'))
        else:
            self.stdout.write(
                f'   → API BRCobrança indisponível — simulando {len(pares)} boletos localmente...'
            )
            count = self._gerar_boletos_simulados(pares)

        # ── Fase 3: Estatísticas por banco ────────────────────────────────────
        from financeiro.models import Parcela, StatusBoleto as SB
        for cb in contas_bancarias:
            qtd = Parcela.objects.filter(
                conta_bancaria=cb, status_boleto=SB.GERADO, pago=False
            ).count()
            if qtd > 0:
                label = 'boletos reais' if service.verificar_api_disponivel() else 'boletos simulados'
                self.stdout.write(f'   → {cb.get_banco_display()} ({cb.banco}): {qtd} {label}')

        return count

    def _gerar_boletos_simulados(self, pares):
        """
        Fallback quando a API BRCobrança está indisponível.
        Popula os campos de boleto sem gerar PDF — dados suficientes para remessa CNAB.
        """
        from financeiro.models import StatusBoleto
        from django.utils import timezone as tz

        hoje = tz.now()
        count = 0
        contas_modificadas: dict = {}

        for parcela, conta in pares:
            if parcela.pago:
                continue

            conta.nosso_numero_atual += 1
            seq_str = str(conta.nosso_numero_atual).zfill(9)

            if conta.banco == '001' and conta.convenio:
                nosso_numero_fmt = str(conta.convenio).zfill(8) + seq_str
            else:
                nosso_numero_fmt = seq_str.zfill(10)

            parcela.conta_bancaria = conta
            parcela.status_boleto = StatusBoleto.GERADO
            parcela.nosso_numero = nosso_numero_fmt
            parcela.nosso_numero_formatado = nosso_numero_fmt
            parcela.nosso_numero_dv = ''
            parcela.numero_documento = parcela.gerar_numero_documento()
            parcela.data_geracao_boleto = hoje
            parcela.save(update_fields=[
                'conta_bancaria', 'status_boleto', 'nosso_numero',
                'nosso_numero_formatado', 'nosso_numero_dv',
                'numero_documento', 'data_geracao_boleto',
            ])
            count += 1
            contas_modificadas[conta.pk] = conta

        for conta_mod in contas_modificadas.values():
            conta_mod.save(update_fields=['nosso_numero_atual'])

        return count

    def verificar_dados_boleto_remessa(self, contratos, contas_bancarias):
        """
        Verifica se os dados gerados estão completos para emissão de boleto
        e geração de arquivo remessa, reportando problemas encontrados.

        Regras verificadas (conforme BRCobranca):
        - Conta bancária: agencia, conta, convenio (se obrigatório), posto/byte_idt (Sicredi), emissao (Caixa)
        - Imobiliária: CNPJ preenchido (cedente do boleto)
        - Comprador: CPF ou CNPJ preenchido, endereço, nome
        - Parcela com boleto: nosso_numero, numero_documento, conta_bancaria
        - Parcelas PAGAS não devem ter boleto gerado (não entram em remessa)
        """
        from financeiro.models import Parcela, StatusBoleto

        CAMPOS_OBRIG_BANCO = {
            '001': {'convenio': 'Convênio (4-8 dígitos)'},
            '033': {'convenio': 'Convênio (7 dígitos)'},
            '104': {'convenio': 'Convênio (6 dígitos)', 'emissao': 'Emissão (1 dígito)', 'codigo_beneficiario': 'Código Beneficiário'},
            '748': {'convenio': 'Convênio', 'posto': 'Posto (2 dígitos)', 'byte_idt': 'Byte IDT (1 dígito)'},
            '756': {'convenio': 'Convênio'},
        }

        alertas = []
        ok_count = 0

        # 1. Verificar contas bancárias
        for cb in contas_bancarias:
            problemas_cb = []
            if not cb.agencia:
                problemas_cb.append('Agência vazia')
            if not cb.conta:
                problemas_cb.append('Conta vazia')
            campos_req = CAMPOS_OBRIG_BANCO.get(cb.banco, {})
            for campo, label in campos_req.items():
                valor = getattr(cb, campo, '') or ''
                if not valor.strip():
                    problemas_cb.append(f'{label} vazio')
            if problemas_cb:
                alertas.append(f'Conta {cb.get_banco_display()} ({cb}): {", ".join(problemas_cb)}')
            else:
                ok_count += 1

        # 2. Verificar imobiliárias
        for contrato in contratos[:10]:  # Amostra
            imob = contrato.imobiliaria
            if not imob.cnpj and not getattr(imob, 'cpf', None):
                alertas.append(f'Imobiliária "{imob.nome}" sem CNPJ/CPF (necessário para cedente do boleto)')

        # 3. Verificar compradores
        sem_doc = 0
        sem_end = 0
        for contrato in contratos:
            c = contrato.comprador
            if not c.cpf and not c.cnpj:
                sem_doc += 1
            if not c.nome:
                alertas.append(f'Comprador ID {c.pk} sem nome')
            if not (getattr(c, 'logradouro', '') or getattr(c, 'endereco', '')):
                sem_end += 1
        if sem_doc:
            alertas.append(f'{sem_doc} comprador(es) sem CPF/CNPJ (campo sacado_documento do boleto)')
        if sem_end:
            alertas.append(f'{sem_end} comprador(es) sem endereço (campo sacado_endereco do boleto)')

        # 4. Verificar parcelas com boleto gerado
        parcelas_boleto = Parcela.objects.filter(status_boleto=StatusBoleto.GERADO)
        sem_nosso_num = parcelas_boleto.filter(nosso_numero='').count()
        sem_num_doc = parcelas_boleto.filter(numero_documento='').count()
        sem_conta = parcelas_boleto.filter(conta_bancaria__isnull=True).count()
        pagas_com_boleto = parcelas_boleto.filter(pago=True).count()

        if sem_nosso_num:
            alertas.append(f'{sem_nosso_num} boleto(s) sem nosso_numero')
        if sem_num_doc:
            alertas.append(f'{sem_num_doc} boleto(s) sem numero_documento')
        if sem_conta:
            alertas.append(f'{sem_conta} boleto(s) sem conta_bancária vinculada')
        if pagas_com_boleto:
            alertas.append(
                f'⚠ {pagas_com_boleto} parcela(s) PAGA(S) ainda com status GERADO '
                f'— não entrarão em remessa (correto), mas status deveria ser PAGO'
            )

        # 5. Resumo por banco
        for cb in contas_bancarias:
            qtd = parcelas_boleto.filter(conta_bancaria=cb, pago=False).count()
            self.stdout.write(f'   [OK] {cb.get_banco_display():20s} — {qtd} boletos prontos para remessa')

        # 6. Exibir resultado
        if alertas:
            self.stdout.write(self.style.WARNING(f'\n⚠ {len(alertas)} problema(s) encontrado(s):'))
            for a in alertas:
                self.stdout.write(self.style.WARNING(f'   • {a}'))
        else:
            self.stdout.write(self.style.SUCCESS('   Todos os dados verificados sem problemas.'))

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
        Popula numero_indice para exercitar o caminho de cálculo exato
        em IndiceReajuste.get_acumulado_periodo() (Método 1).
        """
        count = 0
        hoje = timezone.now().date()

        # Configuração: (tipo, min_var%, max_var%, fonte, numero_indice_base)
        # Bases aproximadas de valores reais publicados (referência: jan 36 meses atrás)
        indices_config = [
            ('IPCA',  0.30, 0.80, 'IBGE/SIDRA', Decimal('6000.0000')),
            ('IGPM',  0.20, 1.00, 'BCB/FGV',    Decimal('3000.0000')),
            ('INCC',  0.25, 0.70, 'BCB/FGV',    Decimal('2000.0000')),
            ('IGPDI', 0.20, 0.90, 'BCB/FGV',    Decimal('2500.0000')),
            ('INPC',  0.25, 0.75, 'IBGE/SIDRA', Decimal('5500.0000')),
            ('TR',    0.00, 0.15, 'BCB',         Decimal('3.0000')),
            ('SELIC', 0.80, 1.10, 'BCB',         Decimal('100.0000')),
        ]

        # numero_indice corrente por tipo (começa um mês antes do período)
        numero_indice_atual = {tipo: base for tipo, *_, base in indices_config}

        # Gerar últimos 36 meses (usa relativedelta para datas precisas)
        from dateutil.relativedelta import relativedelta
        for meses_atras in range(36, 0, -1):
            data = hoje - relativedelta(months=meses_atras)
            ano = data.year
            mes = data.month

            for tipo, min_val, max_val, fonte, _ in indices_config:
                valor = Decimal(str(round(random.uniform(min_val, max_val), 4)))

                # Avançar numero_indice: C(t) = C(t-1) × (1 + valor/100)
                numero_indice_atual[tipo] = (
                    numero_indice_atual[tipo] * (1 + valor / 100)
                ).quantize(Decimal('0.0001'))

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
                        'numero_indice': numero_indice_atual[tipo],
                        'fonte': f'{fonte} (teste)',
                        'data_importacao': timezone.now(),
                    }
                )
                count += 1

        return count

    def criar_contratos_cenarios_hu(self, imobiliarias, compradores):
        """
        Cria contratos determinísticos que cobrem todos os cenários da HU:
        Geração de Parcelas, Correção Monetária e Saldo Devedor.

        Cenários criados:
          A — FIXO + Price + TabelaJuros (contrato pré-fixado padrão)
          B — FIXO + SAC + TabelaJuros (pré-fixado amortização constante)
          C — IPCA + Price + sem TabelaJuros + reajuste aplicado (modo SIMPLES)
          D — IPCA + Price + TabelaJuros escalante + reajuste aplicado (modo TABELA PRICE)
          E — IGPM + Price + intermediarias_reduzem_pmt + sem TabelaJuros
        """
        from dateutil.relativedelta import relativedelta
        from contratos.models import IndiceReajuste
        from django.db.models import Sum

        hoje = timezone.now().date()
        imob = imobiliarias[0]
        seq = Contrato.objects.count()
        contratos_criados = []

        # Usar compradores disponíveis (últimos da lista, não usados nos contratos aleatórios)
        pool = list(compradores[-5:]) if len(compradores) >= 5 else list(compradores)

        def _imovel(sufixo, area='300.00'):
            return Imovel.objects.create(
                imobiliaria=imob,
                tipo=TipoImovel.LOTE,
                identificacao=f'Cenário {sufixo}',
                area=Decimal(area),
                logradouro='Rua dos Cenários',
                numero=sufixo,
                bairro='Distrito de Testes',
                cidade='Sete Lagoas',
                estado='MG',
                disponivel=False,
                observacoes=f'Imóvel de cenário de teste HU {sufixo}',
            )

        def _comprador(idx):
            return pool[idx % len(pool)]

        # ── CENÁRIO A: FIXO + Price + TabelaJuros ────────────────────────────
        data_a = hoje - relativedelta(months=18)
        imovel_a = _imovel('HU-A')
        ctr_a = Contrato.objects.create(
            imobiliaria=imob,
            imovel=imovel_a,
            comprador=_comprador(0),
            numero_contrato=f'HU-A-{seq+1:04d}',
            data_contrato=data_a,
            data_primeiro_vencimento=data_a + relativedelta(months=1),
            valor_total=Decimal('130000.00'),
            valor_entrada=Decimal('10000.00'),
            numero_parcelas=24,
            dia_vencimento=15,
            tipo_correcao=TipoCorrecao.FIXO,
            tipo_amortizacao='PRICE',
            prazo_reajuste_meses=12,
            percentual_juros_mora=Decimal('1.00'),
            percentual_multa=Decimal('2.00'),
            status=StatusContrato.ATIVO,
            observacoes='CENÁRIO HU-A: FIXO + Price + TabelaJuros 0.6% a.m.',
        )
        TabelaJurosContrato.objects.create(
            contrato=ctr_a, ciclo_inicio=1, ciclo_fim=None,
            juros_mensal=Decimal('0.6000'),
            observacoes='Taxa pré-fixada cenário HU-A'
        )
        ctr_a.recalcular_amortizacao()
        contratos_criados.append(ctr_a)

        # ── CENÁRIO B: FIXO + SAC + TabelaJuros ──────────────────────────────
        data_b = hoje - relativedelta(months=18)
        imovel_b = _imovel('HU-B')
        ctr_b = Contrato.objects.create(
            imobiliaria=imob,
            imovel=imovel_b,
            comprador=_comprador(1),
            numero_contrato=f'HU-B-{seq+2:04d}',
            data_contrato=data_b,
            data_primeiro_vencimento=data_b + relativedelta(months=1),
            valor_total=Decimal('130000.00'),
            valor_entrada=Decimal('10000.00'),
            numero_parcelas=24,
            dia_vencimento=10,
            tipo_correcao=TipoCorrecao.FIXO,
            tipo_amortizacao='SAC',
            prazo_reajuste_meses=12,
            percentual_juros_mora=Decimal('1.00'),
            percentual_multa=Decimal('2.00'),
            status=StatusContrato.ATIVO,
            observacoes='CENÁRIO HU-B: FIXO + SAC + TabelaJuros 0.6% a.m.',
        )
        TabelaJurosContrato.objects.create(
            contrato=ctr_b, ciclo_inicio=1, ciclo_fim=None,
            juros_mensal=Decimal('0.6000'),
            observacoes='Taxa pré-fixada cenário HU-B'
        )
        ctr_b.recalcular_amortizacao()
        contratos_criados.append(ctr_b)

        # ── CENÁRIO C: IPCA + Price + sem TabelaJuros + reajuste SIMPLES ─────
        data_c = hoje - relativedelta(months=20)
        imovel_c = _imovel('HU-C')
        ctr_c = Contrato.objects.create(
            imobiliaria=imob,
            imovel=imovel_c,
            comprador=_comprador(2),
            numero_contrato=f'HU-C-{seq+3:04d}',
            data_contrato=data_c,
            data_primeiro_vencimento=data_c + relativedelta(months=1),
            valor_total=Decimal('96000.00'),
            valor_entrada=Decimal('6000.00'),
            numero_parcelas=36,
            dia_vencimento=5,
            tipo_correcao=TipoCorrecao.IPCA,
            tipo_amortizacao='PRICE',
            prazo_reajuste_meses=12,
            spread_reajuste=Decimal('0.5000'),
            percentual_juros_mora=Decimal('1.00'),
            percentual_multa=Decimal('2.00'),
            status=StatusContrato.ATIVO,
            observacoes='CENÁRIO HU-C: IPCA + Price + sem TabelaJuros (modo SIMPLES)',
        )
        contratos_criados.append(ctr_c)
        # Aplicar reajuste ciclo 2 se índice disponível
        periodo_inicio = data_c
        periodo_fim = data_c + relativedelta(months=12) - relativedelta(days=1)
        perc_c = IndiceReajuste.get_acumulado_periodo(
            'IPCA', periodo_inicio.year, periodo_inicio.month,
            periodo_fim.year, periodo_fim.month
        )
        if perc_c is not None:
            perc_final_c = perc_c + Decimal('0.5000')
            reajuste_c = Reajuste.objects.create(
                contrato=ctr_c, ciclo=2, data_reajuste=data_c + relativedelta(months=12),
                indice_tipo='IPCA', percentual=perc_final_c, percentual_bruto=perc_c,
                spread_aplicado=Decimal('0.5000'),
                parcela_inicial=13, parcela_final=min(24, 36),
                periodo_referencia_inicio=periodo_inicio, periodo_referencia_fim=periodo_fim,
                aplicado_manual=True,
            )
            reajuste_c.aplicar_reajuste()

        # ── CENÁRIO D: IPCA + Price + TabelaJuros + reajuste TABELA PRICE ────
        data_d = hoje - relativedelta(months=20)
        imovel_d = _imovel('HU-D')
        ctr_d = Contrato.objects.create(
            imobiliaria=imob,
            imovel=imovel_d,
            comprador=_comprador(3),
            numero_contrato=f'HU-D-{seq+4:04d}',
            data_contrato=data_d,
            data_primeiro_vencimento=data_d + relativedelta(months=1),
            valor_total=Decimal('96000.00'),
            valor_entrada=Decimal('6000.00'),
            numero_parcelas=36,
            dia_vencimento=20,
            tipo_correcao=TipoCorrecao.IPCA,
            tipo_amortizacao='PRICE',
            prazo_reajuste_meses=12,
            percentual_juros_mora=Decimal('1.00'),
            percentual_multa=Decimal('2.00'),
            status=StatusContrato.ATIVO,
            observacoes='CENÁRIO HU-D: IPCA + Price + TabelaJuros (modo TABELA PRICE)',
        )
        TabelaJurosContrato.objects.create(
            contrato=ctr_d, ciclo_inicio=1, ciclo_fim=1, juros_mensal=Decimal('0.0000'),
            observacoes='Ciclo 1 sem juros HU-D'
        )
        TabelaJurosContrato.objects.create(
            contrato=ctr_d, ciclo_inicio=2, ciclo_fim=None, juros_mensal=Decimal('0.6000'),
            observacoes='Ciclo 2+ taxa 0.6% HU-D'
        )
        ctr_d.recalcular_amortizacao()
        contratos_criados.append(ctr_d)
        # Aplicar reajuste ciclo 2 se índice disponível
        perc_d = IndiceReajuste.get_acumulado_periodo(
            'IPCA', data_d.year, data_d.month,
            (data_d + relativedelta(months=12) - relativedelta(days=1)).year,
            (data_d + relativedelta(months=12) - relativedelta(days=1)).month,
        )
        if perc_d is not None:
            fim_ref_d = data_d + relativedelta(months=12) - relativedelta(days=1)
            reajuste_d = Reajuste.objects.create(
                contrato=ctr_d, ciclo=2, data_reajuste=data_d + relativedelta(months=12),
                indice_tipo='IPCA', percentual=perc_d, percentual_bruto=perc_d,
                parcela_inicial=13, parcela_final=min(24, 36),
                periodo_referencia_inicio=data_d, periodo_referencia_fim=fim_ref_d,
                aplicado_manual=True,
            )
            reajuste_d.aplicar_reajuste()

        # ── CENÁRIO E: IGPM + Price + intermediarias_reduzem_pmt ─────────────
        data_e = hoje - relativedelta(months=15)
        imovel_e = _imovel('HU-E')
        ctr_e = Contrato.objects.create(
            imobiliaria=imob,
            imovel=imovel_e,
            comprador=_comprador(4),
            numero_contrato=f'HU-E-{seq+5:04d}',
            data_contrato=data_e,
            data_primeiro_vencimento=data_e + relativedelta(months=1),
            valor_total=Decimal('100000.00'),
            valor_entrada=Decimal('10000.00'),
            numero_parcelas=24,
            dia_vencimento=25,
            tipo_correcao=TipoCorrecao.IGPM,
            tipo_amortizacao='PRICE',
            prazo_reajuste_meses=12,
            intermediarias_reduzem_pmt=True,
            intermediarias_reajustadas=True,
            percentual_juros_mora=Decimal('1.00'),
            percentual_multa=Decimal('2.00'),
            status=StatusContrato.ATIVO,
            observacoes='CENÁRIO HU-E: IGPM + Price + intermediarias_reduzem_pmt=True',
        )
        # Criar intermediárias ANTES do recalcular_amortizacao (correto)
        PrestacaoIntermediaria.objects.create(
            contrato=ctr_e, numero_sequencial=1, mes_vencimento=6,
            valor=Decimal('5000.00'),
            observacoes='Intermediária cenário HU-E mês 6'
        )
        PrestacaoIntermediaria.objects.create(
            contrato=ctr_e, numero_sequencial=2, mes_vencimento=12,
            valor=Decimal('5000.00'),
            observacoes='Intermediária cenário HU-E mês 12'
        )
        # base_pv = valor_financiado - soma_intermediarias = 90.000 - 10.000 = 80.000
        soma_inter_e = ctr_e.intermediarias.aggregate(total=Sum('valor'))['total'] or Decimal('0')
        base_pv_e = max(ctr_e.valor_financiado - soma_inter_e, Decimal('0.01'))
        ctr_e.recalcular_amortizacao(base_pv=base_pv_e)
        contratos_criados.append(ctr_e)

        return contratos_criados

    def criar_prestacoes_intermediarias(self, contratos):
        """
        Cria prestações intermediárias para alguns contratos.
        30% dos contratos (com prazo >= 24 meses) terão prestações intermediárias.
        """
        count = 0

        # Filtrar apenas contratos com prazo suficiente para intermediárias
        contratos_longos = [c for c in contratos if c.numero_parcelas >= 24]

        if not contratos_longos:
            self.stdout.write('   → Nenhum contrato com prazo >= 24 meses para intermediárias')
            return 0

        contratos_com_intermediarias = random.sample(
            contratos_longos,
            k=min(int(len(contratos_longos) * 0.30), len(contratos_longos))
        )

        for contrato in contratos_com_intermediarias:
            # Pular contratos que já têm intermediárias (ex: cenários HU configurados manualmente)
            if contrato.intermediarias.exists():
                continue

            # Intervalo: 50% usa a cada 6 meses, 50% a cada 12 meses
            intervalo = random.choice([6, 12])
            max_intermediarias = contrato.numero_parcelas // intervalo

            if max_intermediarias < 1:
                continue

            # Número de intermediárias: 1 até o máximo permitido
            num_intermediarias = random.randint(1, min(10, max_intermediarias))

            # Atualizar campo do contrato
            if hasattr(contrato, 'quantidade_intermediarias'):
                contrato.quantidade_intermediarias = num_intermediarias
                contrato.save(update_fields=['quantidade_intermediarias'])

            for seq in range(1, num_intermediarias + 1):
                # Vencimento a cada `intervalo` meses
                mes_vencimento = seq * intervalo
                if mes_vencimento > contrato.numero_parcelas:
                    break

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

        self.stdout.write('   → Senha padrão para acessos de teste: teste123')
        return count

    def criar_reajustes_aplicados(self, contratos):
        """
        Cria e aplica reajustes para contratos com mais de 12 meses.

        Regra correta:
        - Ciclo 1 (parcelas 1-12): isento.
        - Ciclo N (parcelas 13-24, 25-36, …): usa o acumulado do índice
          nos 12 meses do ciclo anterior (período de referência correto).
        - Busca o índice real da base; se não disponível, usa percentual
          aleatório realista para não bloquear os dados de teste.
        """
        from dateutil.relativedelta import relativedelta
        from contratos.models import IndiceReajuste, TabelaJurosContrato

        count = 0
        hoje = timezone.now().date()

        for contrato in contratos:
            # FIXO não tem reajuste
            if contrato.tipo_correcao == TipoCorrecao.FIXO:
                continue

            prazo = contrato.prazo_reajuste_meses
            meses_decorridos = (hoje.year - contrato.data_contrato.year) * 12 + \
                               (hoje.month - contrato.data_contrato.month)
            ciclos_completos = meses_decorridos // prazo

            if ciclos_completos < 1:
                continue

            # Aplicar cada ciclo pendente sequencialmente (ciclo 2, 3, …)
            for ciclo in range(2, ciclos_completos + 2):
                data_inicio_ciclo = contrato.data_contrato + relativedelta(months=(ciclo - 1) * prazo)
                if data_inicio_ciclo > hoje:
                    break

                if Reajuste.objects.filter(contrato=contrato, ciclo=ciclo).exists():
                    continue

                parcela_inicial = (ciclo - 1) * prazo + 1
                parcela_final = min(ciclo * prazo, contrato.numero_parcelas)

                if parcela_inicial > contrato.numero_parcelas:
                    break

                # Período de referência: os 12 meses do ciclo anterior
                inicio_ref = contrato.data_contrato + relativedelta(months=(ciclo - 2) * prazo)
                fim_ref = data_inicio_ciclo - relativedelta(days=1)

                # Buscar acumulado real do índice; fallback: percentual aleatório
                percentual_bruto = IndiceReajuste.get_acumulado_periodo(
                    contrato.tipo_correcao,
                    inicio_ref.year, inicio_ref.month,
                    fim_ref.year, fim_ref.month,
                )
                if percentual_bruto is None:
                    percentual_bruto = Decimal(str(round(random.uniform(3.5, 6.5), 4)))

                # Aplicar spread do contrato (índice composto).
                # Em modo TABELA PRICE (TabelaJurosContrato presente), spread NÃO é adicionado
                # ao índice — a taxa de financiamento vem da tabela, não do spread_reajuste.
                tem_tabela = TabelaJurosContrato.objects.filter(contrato=contrato).exists()
                spread = Decimal('0') if tem_tabela else (contrato.spread_reajuste or Decimal('0'))
                percentual_com_spread = percentual_bruto + spread

                # Aplicar teto e piso configurados no contrato
                percentual_final = percentual_com_spread
                if contrato.reajuste_piso is not None:
                    percentual_final = max(contrato.reajuste_piso, percentual_final)
                if contrato.reajuste_teto is not None:
                    percentual_final = min(contrato.reajuste_teto, percentual_final)

                reajuste = Reajuste.objects.create(
                    contrato=contrato,
                    data_reajuste=data_inicio_ciclo,
                    indice_tipo=contrato.tipo_correcao,
                    percentual=percentual_final,
                    percentual_bruto=percentual_bruto,
                    spread_aplicado=spread if spread else None,
                    piso_aplicado=contrato.reajuste_piso,
                    teto_aplicado=contrato.reajuste_teto,
                    parcela_inicial=parcela_inicial,
                    parcela_final=parcela_final,
                    ciclo=ciclo,
                    periodo_referencia_inicio=inicio_ref,
                    periodo_referencia_fim=fim_ref,
                    aplicado_manual=False,
                )

                reajuste.aplicar_reajuste()
                count += 1

        return count

    def criar_templates_notificacao(self):
        """
        Garante que os templates padrão de notificação existam no banco.
        Usa o modelo unificado Email + SMS + WhatsApp por tipo de evento.
        Retorna o número de templates criados.
        """
        try:
            from notificacoes.boleto_notificacao import criar_templates_padrao
            criados = criar_templates_padrao()
            return criados
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'   ⚠ Erro ao criar templates: {e}'))
            return 0

    def gerar_remessas_cnab(self):
        """
        Gera arquivos de remessa CNAB para os boletos simulados.
        Agrupa por conta bancária e chama CNABService.gerar_remessa()
        agrupando por layout_cnab configurado em cada ContaBancaria.
        Retorna o número de remessas geradas.
        """
        from financeiro.models import Parcela, StatusBoleto
        from financeiro.services.cnab_service import CNABService

        service = CNABService()
        count = 0

        # Coletar IDs de boletos GERADO não pagos ainda sem remessa
        parcela_ids = list(
            Parcela.objects.filter(
                status_boleto=StatusBoleto.GERADO,
                pago=False,
                nosso_numero__gt='',
            ).exclude(
                itens_remessa__isnull=False
            ).values_list('pk', flat=True)
        )

        if not parcela_ids:
            self.stdout.write('   Nenhum boleto disponível para remessa — pulando.')
            return 0

        try:
            # Agrupar por layout configurado na conta para não misturar CNAB_240 e CNAB_400
            from financeiro.models import Parcela as _Parcela
            from collections import defaultdict
            grupos_layout = defaultdict(list)
            for pid in parcela_ids:
                p = _Parcela.objects.select_related('conta_bancaria').get(pk=pid)
                layout = getattr(p.conta_bancaria, 'layout_cnab', 'CNAB_400') or 'CNAB_400'
                grupos_layout[layout].append(pid)

            for layout, ids in grupos_layout.items():
                resultado = service.gerar_remessas_por_escopo(
                    parcela_ids=ids,
                    layout=layout,
                )
                for r in resultado.get('remessas_geradas', []):
                    count += 1
                    self.stdout.write(
                        f"   → Remessa #{r.get('numero_remessa')} "
                        f"[{layout}] ({r.get('quantidade_boletos', 0)} boletos)"
                    )
                for e in resultado.get('erros', []):
                    self.stdout.write(self.style.WARNING(f'   ⚠ {e}'))
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f'   ⚠ Erro ao gerar remessa: {exc}'))

        return count

    def simular_historico_conciliacao(self, contas_bancarias):
        """
        Cria ArquivoRetorno + ItemRetorno simulados para demonstrar o
        dashboard de Conciliação Bancária com dados realistas.

        - 1 ArquivoRetorno CNAB400 por conta bancária que tiver boletos GERADO
        - ItemRetorno com tipo_ocorrencia LIQUIDACAO para 50% dos boletos com nosso_numero
        - HistoricoPagamento.origem_pagamento atualizado para 'CNAB' nos pagamentos vinculados
        """
        from financeiro.models import (
            ArquivoRetorno, ItemRetorno, Parcela, HistoricoPagamento, StatusBoleto,
        )
        from django.utils import timezone as tz

        hoje = tz.now()
        retornos_criados = 0
        itens_criados = 0

        for conta in contas_bancarias:
            # Boletos GERADO com nosso_numero para simular retorno bancário
            boletos = list(
                Parcela.objects.filter(
                    conta_bancaria=conta,
                    status_boleto=StatusBoleto.GERADO,
                    pago=False,
                    nosso_numero__gt='',
                ).order_by('data_vencimento')[:10]
            )
            if not boletos:
                continue

            from financeiro.models import StatusArquivoRetorno
            # Criar ArquivoRetorno simulado
            arquivo = ArquivoRetorno.objects.create(
                conta_bancaria=conta,
                nome_arquivo=f'RET_{conta.banco}_{hoje.strftime("%Y%m%d")}.RET',
                data_upload=hoje,
                status=StatusArquivoRetorno.PROCESSADO,
                total_registros=len(boletos),
                registros_processados=0,
                registros_erro=0,
                valor_total_pago=0,
                data_processamento=hoje,
            )
            retornos_criados += 1

            valor_total = 0
            processados = 0

            # Metade dos boletos: LIQUIDACAO (pago pelo banco)
            for parcela in boletos[:len(boletos) // 2]:
                data_ocorrencia = parcela.data_vencimento + timedelta(days=random.randint(0, 5))
                if data_ocorrencia > hoje.date():
                    data_ocorrencia = hoje.date()

                valor_pago = float(parcela.valor_atual)

                # CNAB retorna o nosso_numero formatado (completo, como impresso no boleto)
                nn_cnab = parcela.nosso_numero_formatado or parcela.nosso_numero
                item = ItemRetorno.objects.create(
                    arquivo_retorno=arquivo,
                    nosso_numero=nn_cnab,
                    parcela=parcela,
                    codigo_ocorrencia='06',
                    descricao_ocorrencia='Liquidação normal',
                    tipo_ocorrencia='LIQUIDACAO',
                    valor_titulo=valor_pago,
                    valor_pago=valor_pago,
                    data_ocorrencia=hoje.replace(
                        year=data_ocorrencia.year,
                        month=data_ocorrencia.month,
                        day=data_ocorrencia.day,
                    ),
                    data_credito=hoje.replace(
                        year=data_ocorrencia.year,
                        month=data_ocorrencia.month,
                        day=data_ocorrencia.day,
                    ),
                    processado=True,
                )
                itens_criados += 1

                # Registrar pagamento via CNAB
                parcela.registrar_pagamento_boleto(
                    valor_pago=Decimal(str(valor_pago)),
                    data_pagamento=data_ocorrencia,
                    banco_pagador=conta.banco,
                    validar_minimo=False,
                )

                # Vincular ItemRetorno ao HistoricoPagamento criado
                hist = HistoricoPagamento.objects.filter(parcela=parcela).order_by('-id').first()
                if hist:
                    hist.origem_pagamento = 'CNAB'
                    hist.item_retorno = item
                    hist.save(update_fields=['origem_pagamento', 'item_retorno'])

                valor_total += valor_pago
                processados += 1

            # Demais boletos: OUTROS (entrada de registro, sem baixa)
            for parcela in boletos[len(boletos) // 2:]:
                ItemRetorno.objects.create(
                    arquivo_retorno=arquivo,
                    nosso_numero=parcela.nosso_numero_formatado or parcela.nosso_numero,
                    parcela=parcela,
                    codigo_ocorrencia='02',
                    descricao_ocorrencia='Entrada confirmada',
                    tipo_ocorrencia='OUTROS',
                    valor_titulo=float(parcela.valor_atual),
                    valor_pago=None,
                    data_ocorrencia=hoje,
                    processado=True,
                )
                itens_criados += 1

            # Atualizar totais no arquivo
            arquivo.registros_processados = processados
            arquivo.valor_total_pago = Decimal(str(valor_total))
            arquivo.save(update_fields=['registros_processados', 'valor_total_pago'])

        if retornos_criados:
            self.stdout.write(
                f'   → {retornos_criados} arquivos de retorno CNAB · {itens_criados} itens criados'
            )
        return retornos_criados

    # ── ÍNDICES REAIS ────────────────────────────────────────────────────────

    def popular_indices_reais(self):
        """
        Insere/atualiza IndiceReajuste com dados reais das planilhas:
        - IPCA (IBGE): MAR/2021 → NOV/2025
        - IGPM (FGV/IBRE): JUN/2020 → FEV/2025
        Usa número-índice para calcular variação mensal exata.
        """
        # (year, month, numero_indice)
        _IPCA = [
            (2021,  3, '5674.7200'), (2021,  4, '5692.3100'), (2021,  5, '5739.5600'),
            (2021,  6, '5769.9800'), (2021,  7, '5825.3700'), (2021,  8, '5876.0500'),
            (2021,  9, '5944.2100'), (2021, 10, '6018.5100'), (2021, 11, '6075.6900'),
            (2021, 12, '6120.0400'), (2022,  1, '6153.0900'), (2022,  2, '6215.2400'),
            (2022,  3, '6315.9300'), (2022,  4, '6382.8800'), (2022,  5, '6412.8800'),
            (2022,  6, '6455.8500'), (2022,  7, '6411.9500'), (2022,  8, '6388.8700'),
            (2022,  9, '6370.3400'), (2022, 10, '6407.9300'), (2022, 11, '6434.2000'),
            (2022, 12, '6474.0900'), (2023,  1, '6508.4000'), (2023,  2, '6563.0700'),
            (2023,  3, '6609.6700'), (2023,  4, '6649.9900'), (2023,  5, '6665.2800'),
            (2023,  6, '6659.9500'), (2023,  7, '6667.9400'), (2023,  8, '6683.2800'),
            (2023,  9, '6700.6600'), (2023, 10, '6716.7400'), (2023, 11, '6735.5500'),
            (2023, 12, '6773.2700'), (2024,  1, '6801.7200'), (2024,  2, '6858.1700'),
            (2024,  3, '6869.1400'), (2024,  4, '6895.2400'), (2024,  5, '6926.9600'),
            (2024,  6, '6941.5100'), (2024,  7, '6967.8900'), (2024,  8, '6966.5000'),
            (2024,  9, '6997.1500'), (2024, 10, '7036.3300'), (2024, 11, '7063.7700'),
            (2024, 12, '7100.5000'), (2025,  1, '7111.8600'), (2025,  2, '7205.0300'),
            (2025,  3, '7245.3800'), (2025,  4, '7276.5300'), (2025,  5, '7295.4500'),
            (2025,  6, '7312.9600'), (2025,  7, '7331.9700'), (2025,  8, '7323.9100'),
            (2025,  9, '7359.0600'), (2025, 10, '7365.6900'), (2025, 11, '7378.9400'),
        ]
        _IGPM = [
            (2020,  6, '792.4290'),  (2020,  7, '810.0830'),  (2020,  8, '832.3130'),
            (2020,  9, '868.4420'),  (2020, 10, '896.5050'),  (2020, 11, '925.8870'),
            (2020, 12, '934.7580'),  (2021,  1, '958.8440'),  (2021,  2, '983.0630'),
            (2021,  3, '1011.9480'), (2021,  4, '1027.2110'), (2021,  5, '1069.2890'),
            (2021,  6, '1075.7330'), (2021,  7, '1084.0950'), (2021,  8, '1091.2900'),
            (2021,  9, '1084.3120'), (2021, 10, '1091.2830'), (2021, 11, '1091.4830'),
            (2021, 12, '1100.9880'), (2022,  1, '1120.9990'), (2022,  2, '1141.5460'),
            (2022,  3, '1161.4180'), (2022,  4, '1177.8090'), (2022,  5, '1183.9530'),
            (2022,  6, '1190.8820'), (2022,  7, '1193.3370'), (2022,  8, '1185.0040'),
            (2022,  9, '1173.7930'), (2022, 10, '1162.3910'), (2022, 11, '1155.8290'),
            (2022, 12, '1161.0060'), (2023,  1, '1163.4650'), (2023,  2, '1162.7610'),
            (2023,  3, '1163.3590'), (2023,  4, '1152.3070'), (2023,  5, '1131.0580'),
            (2023,  6, '1109.2300'), (2023,  7, '1101.2040'), (2023,  8, '1099.7100'),
            (2023,  9, '1103.7400'), (2023, 10, '1109.2360'), (2023, 11, '1115.8150'),
            (2023, 12, '1124.0720'), (2024,  1, '1124.8790'), (2024,  2, '1119.0610'),
            (2024,  3, '1113.8370'), (2024,  4, '1117.2800'), (2024,  5, '1127.2330'),
            (2024,  6, '1136.4090'), (2024,  7, '1143.3130'), (2024,  8, '1146.5750'),
            (2024,  9, '1153.7180'), (2024, 10, '1171.2720'), (2024, 11, '1186.4620'),
            (2024, 12, '1197.6150'), (2025,  1, '1200.8480'), (2025,  2, '1213.5770'),
        ]

        count = 0
        for tipo, serie, fonte in [('IPCA', _IPCA, 'IBGE'), ('IGPM', _IGPM, 'FGV/IBRE')]:
            prev_ni = None
            for year, month, ni_str in serie:
                ni = Decimal(ni_str)
                if prev_ni is not None:
                    valor = ((ni / prev_ni) - 1) * 100
                    valor = valor.quantize(Decimal('0.0001'))
                else:
                    valor = Decimal('0.0000')
                prev_ni = ni

                IndiceReajuste.objects.update_or_create(
                    tipo_indice=tipo,
                    ano=year,
                    mes=month,
                    defaults={
                        'valor': valor,
                        'numero_indice': ni,
                        'valor_acumulado_12m': None,
                        'fonte': f'{fonte} (planilha real)',
                        'data_importacao': timezone.now(),
                    }
                )
                count += 1
        return count

    # ── CONTRATOS REAIS ──────────────────────────────────────────────────────

    def criar_contratos_reais(self, imobiliarias):
        """
        Cria 2 contratos baseados em planilhas reais:
          1. UANDA SILVA CARVALHO — IPCA + 0,85% a.m., lote 16 Qd D (24/03/2021)
          2. HENRY MAGNO DE OLIVEIRA SILVA — IGPM + juros escalantes, lote 13 Qd C (22/07/2020)
        Aplica reajustes reais ciclo a ciclo e registra pagamentos históricos.
        """
        hoje = timezone.now().date()
        imob = imobiliarias[0]
        contratos_criados = []

        # ── helper: marcar N parcelas como pagas sequencialmente ────────────
        def _pagar(parcelas_qs, ate_numero):
            """Registra pagamento para parcelas 1..ate_numero (não pagas, vencidas)."""
            for p in parcelas_qs.filter(numero_parcela__lte=ate_numero, pago=False).order_by('numero_parcela'):
                if p.data_vencimento > hoje:
                    break
                data_pag = min(p.data_vencimento + timedelta(days=random.randint(0, 3)), hoje)
                p.registrar_pagamento(
                    valor_pago=p.valor_atual,
                    data_pagamento=data_pag,
                    observacoes='Pagamento real — planilha de controle',
                    validar_minimo=False,
                )

        # ── helper: aplicar reajuste com percentual fixo ─────────────────────
        def _reajuste(contrato, ciclo, data_r, p_ini, p_fim, bruto, final, ref_ini, ref_fim):
            if Reajuste.objects.filter(contrato=contrato, ciclo=ciclo).exists():
                return
            r = Reajuste(
                contrato=contrato,
                ciclo=ciclo,
                data_reajuste=data_r,
                indice_tipo=contrato.tipo_correcao,
                percentual=Decimal(str(final)),
                percentual_bruto=Decimal(str(bruto)),
                parcela_inicial=p_ini,
                parcela_final=p_fim,
                periodo_referencia_inicio=ref_ini,
                periodo_referencia_fim=ref_fim,
                aplicado_manual=True,
                aplicado=False,
            )
            r.save()
            r.aplicar_reajuste()

        # ══════════════════════════════════════════════════════════════════════
        # CONTRATO 1 — UANDA SILVA CARVALHO (IPCA + 0,85% a.m.)
        # ══════════════════════════════════════════════════════════════════════
        comprador_u, _ = Comprador.objects.get_or_create(
            cpf='066.128.216-39',
            defaults=dict(
                tipo_pessoa='PF',
                nome='UANDA SILVA CARVALHO',
                rg='2345678',
                data_nascimento=date(1985, 6, 15),
                estado_civil='CASADO',
                profissao='Professora',
                cep='35700-000',
                logradouro='Rua das Acácias',
                numero='215',
                bairro='Várzea',
                cidade='Sete Lagoas',
                estado='MG',
                telefone='(31) 3773-9001',
                celular='(31) 99901-0001',
                email='uanda.silva.carvalho@email.com.br',
                notificar_email=True,
                notificar_whatsapp=True,
                ativo=True,
            )
        )

        imovel_u, _ = Imovel.objects.get_or_create(
            imobiliaria=imob,
            identificacao='Lote 16, Quadra D',
            loteamento='Res. Parque das Nogueiras',
            defaults=dict(
                tipo=TipoImovel.LOTE,
                area=Decimal('300.00'),
                cep='35700-000',
                logradouro='Rua Parque das Nogueiras',
                numero='16',
                bairro='Parque das Nogueiras',
                cidade='Sete Lagoas',
                estado='MG',
                matricula='45016',
                inscricao_municipal='10016',
                disponivel=False,
                ativo=True,
            )
        )

        if not Contrato.objects.filter(numero_contrato='CTR-L16-QD-2021').exists():
            ctr_u = Contrato.objects.create(
                imobiliaria=imob,
                imovel=imovel_u,
                comprador=comprador_u,
                numero_contrato='CTR-L16-QD-2021',
                data_contrato=date(2021, 3, 24),
                data_primeiro_vencimento=date(2021, 4, 10),
                valor_total=Decimal('235695.82'),
                valor_entrada=Decimal('23569.58'),
                numero_parcelas=120,
                dia_vencimento=10,
                tipo_correcao=TipoCorrecao.IPCA,
                tipo_amortizacao='PRICE',
                prazo_reajuste_meses=12,
                intermediarias_reduzem_pmt=True,
                intermediarias_reajustadas=False,
                percentual_juros_mora=Decimal('1.00'),
                percentual_multa=Decimal('2.00'),
                percentual_fruicao=Decimal('0.5000'),
                percentual_multa_rescisao_penal=Decimal('10.0000'),
                percentual_multa_rescisao_adm=Decimal('12.0000'),
                percentual_cessao=Decimal('3.0000'),
                status=StatusContrato.ATIVO,
                observacoes=(
                    'Contrato real — Lote 16 Qd D, Res. Parque das Nogueiras | '
                    'IPCA + 0,85% a.m. | Entrada R$23.569,58 + 120×mensal + 10×anual'
                ),
            )

            # 10 parcelas anuais de R$5.000 (saldo remanescente — cláusula 2.2.2)
            for seq in range(1, 11):
                PrestacaoIntermediaria.objects.create(
                    contrato=ctr_u,
                    numero_sequencial=seq,
                    mes_vencimento=min(12 * seq + 1, 120),
                    valor=Decimal('5000.00'),
                    observacoes=f'Saldo remanescente anual parcela {seq}/10 — cláusula 2.2.2',
                )

            # Base PMT = saldo excluindo anuais: 235.695,82 - 23.569,58 - 50.000 = 162.126,24
            ctr_u.recalcular_amortizacao(base_pv=Decimal('162126.24'))

            # Ciclo 1 (1-12): pagar → 1.351,05/parc
            _pagar(ctr_u.parcelas, 12)

            # Ciclo 2 (ABR/22-MAR/23): IPCA 11,30% + juros comp 10,69% = +23,20%
            _reajuste(ctr_u, 2, date(2022, 4, 1), 13, 24,
                      bruto=11.2994, final=23.1980,
                      ref_ini=date(2021, 3, 24), ref_fim=date(2022, 3, 23))
            _pagar(ctr_u.parcelas, 24)

            # Ciclo 3 (ABR/23-MAR/24): IPCA 4,65% + juros comp 10,69% = +15,84%
            _reajuste(ctr_u, 3, date(2023, 4, 1), 25, 36,
                      bruto=4.6508, final=15.8386,
                      ref_ini=date(2022, 3, 24), ref_fim=date(2023, 3, 23))
            _pagar(ctr_u.parcelas, 28)   # pagou até JUL/2023 (parc 28)

            # Ciclo 4 (ABR/24-MAR/25): IPCA 3,93% + juros comp 10,69% = +15,04%
            _reajuste(ctr_u, 4, date(2024, 4, 1), 37, 48,
                      bruto=3.9256, final=15.0359,
                      ref_ini=date(2023, 3, 24), ref_fim=date(2024, 3, 23))

            # Ciclo 5 (ABR/25-MAR/26): IPCA 5,48% + juros comp 10,69% = +16,75%
            _reajuste(ctr_u, 5, date(2025, 4, 1), 49, 60,
                      bruto=5.4773, final=16.7534,
                      ref_ini=date(2024, 3, 24), ref_fim=date(2025, 3, 23))
            # Ciclo 6 pendente (APR/2026 = mês do aniversário) — deixa sem aplicar

            self.stdout.write('   ✓ Uanda Silva Carvalho — CTR-L16-QD-2021 criado')
            contratos_criados.append(ctr_u)
        else:
            self.stdout.write('   → CTR-L16-QD-2021 já existe, reutilizando.')
            contratos_criados.append(
                Contrato.objects.get(numero_contrato='CTR-L16-QD-2021')
            )

        # ══════════════════════════════════════════════════════════════════════
        # CONTRATO 2 — HENRY MAGNO DE OLIVEIRA SILVA (IGPM + juros escalantes)
        # ══════════════════════════════════════════════════════════════════════
        comprador_h, _ = Comprador.objects.get_or_create(
            cpf='074.927.647-90',
            defaults=dict(
                tipo_pessoa='PF',
                nome='HENRY MAGNO DE OLIVEIRA SILVA',
                rg='3456789',
                data_nascimento=date(1978, 11, 3),
                estado_civil='CASADO',
                profissao='Engenheiro Civil',
                cep='35700-000',
                logradouro='Av. Presidente Vargas',
                numero='880',
                complemento='Apto 302',
                bairro='Centro',
                cidade='Sete Lagoas',
                estado='MG',
                telefone='(31) 3773-9002',
                celular='(31) 99902-0002',
                email='henry.magno.oliveira@email.com.br',
                notificar_email=True,
                notificar_whatsapp=False,
                ativo=True,
            )
        )

        imovel_h, _ = Imovel.objects.get_or_create(
            imobiliaria=imob,
            identificacao='Lote 13, Quadra C',
            loteamento='Res. Parque das Nogueiras',
            defaults=dict(
                tipo=TipoImovel.LOTE,
                area=Decimal('360.00'),
                cep='35700-000',
                logradouro='Rua Parque das Nogueiras',
                numero='13',
                bairro='Parque das Nogueiras',
                cidade='Sete Lagoas',
                estado='MG',
                matricula='45013',
                inscricao_municipal='10013',
                disponivel=False,
                ativo=True,
            )
        )

        if not Contrato.objects.filter(numero_contrato='CTR-L13-QC-2020').exists():
            ctr_h = Contrato.objects.create(
                imobiliaria=imob,
                imovel=imovel_h,
                comprador=comprador_h,
                numero_contrato='CTR-L13-QC-2020',
                data_contrato=date(2020, 7, 22),
                data_primeiro_vencimento=date(2020, 8, 10),
                valor_total=Decimal('186334.81'),
                valor_entrada=Decimal('100000.00'),
                numero_parcelas=120,
                dia_vencimento=10,
                tipo_correcao=TipoCorrecao.IGPM,
                tipo_amortizacao='PRICE',
                prazo_reajuste_meses=12,
                intermediarias_reduzem_pmt=False,
                intermediarias_reajustadas=False,
                percentual_juros_mora=Decimal('1.00'),
                percentual_multa=Decimal('2.00'),
                percentual_fruicao=Decimal('0.5000'),
                percentual_multa_rescisao_penal=Decimal('10.0000'),
                percentual_multa_rescisao_adm=Decimal('12.0000'),
                percentual_cessao=Decimal('3.0000'),
                status=StatusContrato.ATIVO,
                observacoes=(
                    'Contrato real — Lote 13 Qd C, Res. Parque das Nogueiras | '
                    'IGPM + juros escalantes (0% → 0,85% a.m.) | Entrada R$100.000'
                ),
            )

            # Ciclo 1 (1-12): 0% → PMT = 86.334,81 / 120 = 719,46
            _pagar(ctr_h.parcelas, 12)

            # Ciclo 2 (AGO/21): IGPM JUL/20→JUL/21 = 33,83% + juros 0,6%/m (7,44%) = +43,78%
            _reajuste(ctr_h, 2, date(2021, 8, 1), 13, 24,
                      bruto=33.8252, final=43.7850,
                      ref_ini=date(2020, 7, 1), ref_fim=date(2021, 7, 31))
            _pagar(ctr_h.parcelas, 24)

            # Ciclo 3 (AGO/22): IGPM JUL/21→JUL/22 = 10,08% + juros 0,65%/m (8,08%) = +18,98%
            _reajuste(ctr_h, 3, date(2022, 8, 1), 25, 36,
                      bruto=10.0768, final=18.9765,
                      ref_ini=date(2021, 7, 1), ref_fim=date(2022, 7, 31))
            _pagar(ctr_h.parcelas, 36)

            # Ciclo 4 (AGO/23): IGPM JUL/22→JUL/23 = -7,72% + juros 0,70%/m (8,73%) = +0,34%
            _reajuste(ctr_h, 4, date(2023, 8, 1), 37, 48,
                      bruto=-7.7206, final=0.3364,
                      ref_ini=date(2022, 7, 1), ref_fim=date(2023, 7, 31))
            _pagar(ctr_h.parcelas, 48)

            # Ciclo 5 (AGO/24): IGPM JUL/23→JUL/24 = 3,82% + juros 0,75%/m (9,38%) = +13,56%
            _reajuste(ctr_h, 5, date(2024, 8, 1), 49, 60,
                      bruto=3.8239, final=13.5633,
                      ref_ini=date(2023, 7, 1), ref_fim=date(2024, 7, 31))
            _pagar(ctr_h.parcelas, 60)

            # Ciclo 6 (AGO/25): IGPM JUL/24→JUL/25 ≈ 2,96% + juros 0,80%/m (10,03%) = +13,29%
            _reajuste(ctr_h, 6, date(2025, 8, 1), 61, 72,
                      bruto=2.9580, final=13.2886,
                      ref_ini=date(2024, 7, 1), ref_fim=date(2025, 7, 31))
            # Pagou AGO/25 a JAN/26 (parcelas 61-66)
            _pagar(ctr_h.parcelas, 66)
            # Ciclo 7 pendente (AGO/2026) — deixa sem aplicar

            self.stdout.write('   ✓ Henry Magno de Oliveira Silva — CTR-L13-QC-2020 criado')
            contratos_criados.append(ctr_h)
        else:
            self.stdout.write('   → CTR-L13-QC-2020 já existe, reutilizando.')
            contratos_criados.append(
                Contrato.objects.get(numero_contrato='CTR-L13-QC-2020')
            )

        # ── Portal: acesso para ambos os compradores ─────────────────────────
        for comprador, documento in [
            (comprador_u, '06612821639'),
            (comprador_h, '07492764790'),
        ]:
            username = f'comprador_{documento}'
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    email=comprador.email,
                    password='teste123',
                    first_name=comprador.nome.split()[0],
                    last_name=' '.join(comprador.nome.split()[1:3]),
                )
                AcessoComprador.objects.create(
                    comprador=comprador,
                    usuario=user,
                    email_verificado=True,
                    ativo=True,
                )
                self.stdout.write(f'   ✓ Acesso portal criado: {username} / teste123')

        return contratos_criados
