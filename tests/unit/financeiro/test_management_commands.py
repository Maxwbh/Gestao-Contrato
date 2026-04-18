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
