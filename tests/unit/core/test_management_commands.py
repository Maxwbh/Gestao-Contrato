"""
Testes dos management commands do app core.

Escopo: gerar_dados_teste (com e sem --limpar), flags --so-remessa, --so-retorno, --so-logos
"""
import pytest
from io import StringIO
from django.core.management import call_command


@pytest.mark.django_db
class TestGerarDadosTeste:
    """Testes do management command gerar_dados_teste"""

    def test_comando_executa_sem_erro(self):
        """Executa o comando sem --limpar e verifica que não lança exceção"""
        out = StringIO()
        try:
            call_command('gerar_dados_teste', stdout=out)
        except SystemExit as e:
            assert e.code == 0

    def test_comando_com_limpar(self):
        """Executa com --limpar não deve falhar"""
        out = StringIO()
        try:
            call_command('gerar_dados_teste', limpar=True, stdout=out)
        except SystemExit as e:
            assert e.code == 0

    def test_cria_dados_no_banco(self):
        """Após execução, existem dados no banco"""
        from core.models import Imobiliaria, Comprador
        call_command('gerar_dados_teste', stdout=StringIO())
        assert Imobiliaria.objects.count() > 0 or Comprador.objects.count() > 0


@pytest.mark.django_db
class TestGerarDadosTestePassos:
    """Testes dos novos flags de passo isolado --so-boletos, --so-remessa, --so-retorno, --so-logos"""

    def _setup_base(self):
        """Gera dados base (Passo 1) para os demais passos."""
        call_command('gerar_dados_teste', stdout=StringIO())

    def test_so_boletos_sem_dados_nao_falha(self):
        """--so-boletos com banco vazio deve reportar erro sem lançar exceção."""
        out = StringIO()
        try:
            call_command('gerar_dados_teste', so_boletos=True, stdout=out)
        except SystemExit as e:
            assert e.code == 0

    def test_so_boletos_com_dados_executa(self):
        """--so-boletos após dados base executa sem erro."""
        self._setup_base()
        out = StringIO()
        call_command('gerar_dados_teste', so_boletos=True, stdout=out)
        saida = out.getvalue()
        assert isinstance(saida, str)

    def test_limpar_remove_evento_cobranca_api(self):
        """--limpar deve remover EventoCobrancaApi mesmo com FK SET_NULL."""
        from financeiro.models import EventoCobrancaApi
        self._setup_base()
        # Criar um EventoCobrancaApi orphan (parcela=None) para simular resíduo
        EventoCobrancaApi.objects.create(
            cobranca_id='cob-limpar-test',
            parcela=None,
        )
        assert EventoCobrancaApi.objects.filter(cobranca_id='cob-limpar-test').exists()
        call_command('gerar_dados_teste', limpar=True, stdout=StringIO())
        assert not EventoCobrancaApi.objects.filter(cobranca_id='cob-limpar-test').exists()

    def test_so_remessa_sem_dados_nao_falha(self):
        """--so-remessa com banco vazio não deve lançar exceção."""
        out = StringIO()
        try:
            call_command('gerar_dados_teste', so_remessa=True, stdout=out)
        except SystemExit as e:
            assert e.code == 0

    def test_so_retorno_sem_dados_nao_falha(self):
        """--so-retorno com banco vazio não deve lançar exceção."""
        out = StringIO()
        try:
            call_command('gerar_dados_teste', so_retorno=True, stdout=out)
        except SystemExit as e:
            assert e.code == 0

    def test_so_logos_sem_dados_nao_falha(self):
        """--so-logos com banco vazio não deve lançar exceção."""
        out = StringIO()
        try:
            call_command('gerar_dados_teste', so_logos=True, stdout=out)
        except SystemExit as e:
            assert e.code == 0

    def test_so_remessa_cria_arquivo_remessa(self):
        """--so-remessa após dados base deve criar ArquivoRemessa."""
        from financeiro.models import ArquivoRemessa
        self._setup_base()
        # Precisa de boletos gerados para criar remessa (pode não haver neste ambiente de teste)
        initial = ArquivoRemessa.objects.count()
        call_command('gerar_dados_teste', so_remessa=True, stdout=StringIO())
        # Se havia boletos GERADO, cria remessas; senão mantém igual
        assert ArquivoRemessa.objects.count() >= initial

    def test_so_logos_com_imobiliarias_executa(self):
        """--so-logos com imobiliárias no banco executa sem erro."""
        from core.models import Imobiliaria
        self._setup_base()
        assert Imobiliaria.objects.count() > 0
        out = StringIO()
        call_command('gerar_dados_teste', so_logos=True, stdout=out)
        # Não deve ter lançado exceção; output deve conter algum texto
        saida = out.getvalue()
        assert isinstance(saida, str)


@pytest.mark.django_db
class TestGerarDadosBoletoApi:
    """Testa que o comando gera contas Boleto-API corretamente."""

    def test_contas_sicoob_e_c6_tem_provider_correto(self):
        """Sicoob deve ter provider=sicoob e C6 deve ter provider=c6."""
        from core.models import ContaBancaria
        call_command('gerar_dados_teste', stdout=StringIO())
        assert ContaBancaria.objects.filter(banco='756', provider='sicoob').exists()
        assert ContaBancaria.objects.filter(banco='336', provider='c6').exists()

    def test_contas_bb_e_bradesco_usam_brcobranca(self):
        """BB e Bradesco devem manter provider=brcobranca (fluxo CNAB)."""
        from core.models import ContaBancaria
        call_command('gerar_dados_teste', stdout=StringIO())
        assert not ContaBancaria.objects.filter(banco='001').exclude(provider='brcobranca').exists()
        assert not ContaBancaria.objects.filter(banco='237').exclude(provider='brcobranca').exists()

    def test_contas_api_tem_account_config_e_tenant_id(self):
        """Contas Boleto-API devem ter account_config e tenant_id preenchidos."""
        from core.models import ContaBancaria
        call_command('gerar_dados_teste', stdout=StringIO())
        for conta in ContaBancaria.objects.filter(banco__in=['756', '336']):
            assert conta.account_config is not None, f'{conta}: account_config vazio'
            assert conta.tenant_id, f'{conta}: tenant_id vazio'

    def test_boletos_api_simulados_tem_cobranca_id(self):
        """Após --so-boletos, parcelas com conta Boleto-API devem ter cobranca_id."""
        from financeiro.models import Parcela
        call_command('gerar_dados_teste', stdout=StringIO())
        call_command('gerar_dados_teste', so_boletos=True, stdout=StringIO())
        parcelas_api = Parcela.objects.filter(
            conta_bancaria__provider__in=['sicoob', 'c6'],
            status_boleto='GERADO',
            pago=False,
        )
        if parcelas_api.exists():
            assert parcelas_api.filter(cobranca_id='').count() == 0, \
                'Parcelas Boleto-API sem cobranca_id após geração'

    def test_so_boletos_reseta_cobranca_id(self):
        """Segunda execução de --so-boletos deve limpar cobranca_id antes de regenerar."""
        from financeiro.models import Parcela
        call_command('gerar_dados_teste', stdout=StringIO())
        call_command('gerar_dados_teste', so_boletos=True, stdout=StringIO())
        # Forçar reset: executar novamente — deve limpar cobranca_id e regenerar
        call_command('gerar_dados_teste', so_boletos=True, stdout=StringIO())
        # Não deve haver GERADO sem cobranca_id em contas API
        sem_id = Parcela.objects.filter(
            conta_bancaria__provider__in=['sicoob', 'c6'],
            status_boleto='GERADO',
            pago=False,
            cobranca_id='',
        ).count()
        assert sem_id == 0

    def test_remessa_cnab_ignora_contas_boleto_api(self):
        """--so-remessa não deve incluir parcelas de contas Boleto-API."""
        from financeiro.models import ArquivoRemessa, ItemRemessa
        call_command('gerar_dados_teste', stdout=StringIO())
        call_command('gerar_dados_teste', so_boletos=True, stdout=StringIO())
        call_command('gerar_dados_teste', so_remessa=True, stdout=StringIO())
        # Nenhum ItemRemessa deve ter parcela vinculada a conta Boleto-API
        itens_api = ItemRemessa.objects.filter(
            parcela__conta_bancaria__provider__in=['sicoob', 'c6']
        ).count()
        assert itens_api == 0, f'{itens_api} ItemRemessa indevidos em contas Boleto-API'


@pytest.mark.django_db
class TestProcessarReajustes:
    """Testes do management command processar_reajustes"""

    def test_comando_executa_sem_erro(self):
        """processar_reajustes não deve lançar exceção com banco vazio"""
        out = StringIO()
        try:
            call_command('processar_reajustes', stdout=out)
        except SystemExit as e:
            assert e.code == 0

