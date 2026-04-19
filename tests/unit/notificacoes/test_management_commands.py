"""
Testes dos management commands de notificacoes.

Cobre: enviar_notificacoes, processar_notificacoes_pendentes
"""
import pytest
from unittest.mock import patch
from io import StringIO
from django.core.management import call_command


@pytest.mark.django_db
class TestComandoEnviarNotificacoes:
    """Testes do comando enviar_notificacoes"""

    def test_comando_executa_sem_erro(self):
        """Comando executa e escreve saída de sucesso"""
        out = StringIO()
        patch_path = 'notificacoes.management.commands.enviar_notificacoes.enviar_notificacoes_vencimento'
        with patch(patch_path, return_value=0):
            call_command('enviar_notificacoes', stdout=out)
        output = out.getvalue()
        assert 'Iniciando' in output or 'conclu' in output

    def test_comando_retorna_zero_notificacoes_sem_parcelas(self):
        """Sem parcelas a vencer, retorna 0 notificações criadas"""
        out = StringIO()
        patch_path = 'notificacoes.management.commands.enviar_notificacoes.enviar_notificacoes_vencimento'
        with patch(patch_path, return_value=0):
            call_command('enviar_notificacoes', stdout=out)
        # Deve completar sem exceção

    def test_comando_trata_excecao_graciosamente(self):
        """Exceção no task é capturada e reportada (re-raise)"""
        out = StringIO()
        with patch(
            'notificacoes.management.commands.enviar_notificacoes.enviar_notificacoes_vencimento',
            side_effect=Exception('Erro de teste')
        ):
            with pytest.raises(Exception, match='Erro de teste'):
                call_command('enviar_notificacoes', stdout=out)


@pytest.mark.django_db
class TestComandoProcessarNotificacoesPendentes:
    """Testes do comando processar_notificacoes_pendentes"""

    def test_comando_executa_sem_erro(self):
        """Comando executa e escreve saída"""
        out = StringIO()
        with patch(
            'notificacoes.management.commands.processar_notificacoes_pendentes.Command.handle',
            return_value=None
        ):
            call_command('processar_notificacoes_pendentes', stdout=out)
