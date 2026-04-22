"""
Testes dos management commands do app core.

Escopo: gerar_dados_teste (com e sem --limpar)
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
        # Deve criar pelo menos algumas imobiliárias ou compradores
        assert Imobiliaria.objects.count() > 0 or Comprador.objects.count() > 0


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
