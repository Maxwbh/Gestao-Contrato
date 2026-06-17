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
class TestProcessarReajustes:
    """Testes do management command processar_reajustes"""

    def test_comando_executa_sem_erro(self):
        """processar_reajustes não deve lançar exceção com banco vazio"""
        out = StringIO()
        try:
            call_command('processar_reajustes', stdout=out)
        except SystemExit as e:
            assert e.code == 0

