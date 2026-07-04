"""
Testes dos management commands do financeiro.

Cobre: processar_reajustes
"""
import pytest
from unittest.mock import patch
from io import StringIO
from django.core.management import call_command


@pytest.mark.django_db
class TestComandoProcessarReajustes:
    """Testes do comando processar_reajustes"""

    def test_comando_executa_sem_erro(self):
        """Comando executa e escreve saída de sucesso"""
        out = StringIO()
        patch_path = 'financeiro.management.commands.processar_reajustes.processar_reajustes_pendentes'
        with patch(patch_path, return_value={'processados': 0, 'reajustados': 0}):
            call_command('processar_reajustes', stdout=out)
        output = out.getvalue()
        assert 'Iniciando' in output or 'conclu' in output

    def test_comando_trata_excecao_graciosamente(self):
        """Exceção no task é capturada e reportada (re-raise)"""
        out = StringIO()
        patch_path = 'financeiro.management.commands.processar_reajustes.processar_reajustes_pendentes'
        with patch(patch_path, side_effect=Exception('Erro de teste')):
            with pytest.raises(Exception, match='Erro de teste'):
                call_command('processar_reajustes', stdout=out)


@pytest.mark.django_db
class TestComandoAuditNossoNumero:
    """Testes do comando audit_nosso_numero"""

    def test_comando_executa_sem_dados(self):
        """Comando executa sem erro em banco vazio."""
        out = StringIO()
        call_command('audit_nosso_numero', stdout=out)
        output = out.getvalue()
        assert 'Auditoria' in output or 'nosso_numero' in output or 'Fim' in output

    def test_comando_detecta_boleto_sem_nosso_numero(self):
        """Comando detecta parcela com boleto gerado mas nosso_numero em branco."""
        from tests.fixtures.factories import ParcelaFactory
        from financeiro.models import StatusBoleto

        parcela = ParcelaFactory(
            status_boleto=StatusBoleto.GERADO,
            nosso_numero='',
        )

        out = StringIO()
        call_command('audit_nosso_numero', stdout=out)
        output = out.getvalue()

        assert 'Boletos gerados sem nosso_numero' in output
