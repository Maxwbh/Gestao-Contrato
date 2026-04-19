"""
Testes das tasks Celery do app notificacoes

Desenvolvedor: Maxwell da Silva Oliveira <maxwbh@gmail.com>
"""

import pytest
from unittest.mock import patch
from django.utils import timezone
from datetime import timedelta

from notificacoes.models import Notificacao, TipoNotificacao, StatusNotificacao
from notificacoes.tasks import (
    processar_notificacoes_pendentes,
    reenviar_notificacao,
)


# =============================================================================
# TESTES DE PROCESSAR NOTIFICACOES PENDENTES
# =============================================================================

@pytest.mark.django_db
class TestProcessarNotificacoesPendentes:
    """Testes da task processar_notificacoes_pendentes"""

    @patch('notificacoes.tasks.enviar_notificacao')
    def test_processar_notificacoes_pendentes_sucesso(self, mock_enviar):
        """Processa e envia notificações pendentes com sucesso"""
        mock_enviar.return_value = (True, '')

        # Criar notificação pendente
        notif = Notificacao.objects.create(
            tipo=TipoNotificacao.EMAIL,
            destinatario='teste@email.com',
            assunto='Teste',
            mensagem='Mensagem teste',
            status=StatusNotificacao.PENDENTE,
            data_agendamento=timezone.now() - timedelta(minutes=5)
        )

        resultado = processar_notificacoes_pendentes()

        notif.refresh_from_db()
        assert notif.status == StatusNotificacao.ENVIADA
        assert resultado['enviadas'] == 1
        assert resultado['erros'] == 0

    @patch('notificacoes.tasks.enviar_notificacao')
    def test_processar_notificacoes_pendentes_erro(self, mock_enviar):
        """Marca notificação com erro quando envio falha"""
        mock_enviar.return_value = (False, '')

        notif = Notificacao.objects.create(
            tipo=TipoNotificacao.EMAIL,
            destinatario='teste@email.com',
            mensagem='Mensagem teste',
            status=StatusNotificacao.PENDENTE,
            data_agendamento=timezone.now() - timedelta(minutes=5)
        )

        resultado = processar_notificacoes_pendentes()

        notif.refresh_from_db()
        assert notif.status == StatusNotificacao.ERRO
        assert resultado['enviadas'] == 0
        assert resultado['erros'] == 1

    @patch('notificacoes.tasks.enviar_notificacao')
    def test_processar_notificacoes_pendentes_excecao(self, mock_enviar):
        """Trata exceção durante envio"""
        mock_enviar.side_effect = Exception('Erro de conexão')

        notif = Notificacao.objects.create(
            tipo=TipoNotificacao.EMAIL,
            destinatario='teste@email.com',
            mensagem='Mensagem teste',
            status=StatusNotificacao.PENDENTE,
            data_agendamento=timezone.now() - timedelta(minutes=5)
        )

        processar_notificacoes_pendentes()

        notif.refresh_from_db()
        assert notif.status == StatusNotificacao.ERRO
        assert 'Erro de conexão' in notif.erro_mensagem

    def test_processar_sem_notificacoes_pendentes(self):
        """Retorna zeros quando não há notificações pendentes"""
        resultado = processar_notificacoes_pendentes()

        assert resultado['enviadas'] == 0
        assert resultado['erros'] == 0

    def test_nao_processa_notificacoes_agendadas_futuro(self):
        """Não processa notificações agendadas para o futuro"""
        Notificacao.objects.create(
            tipo=TipoNotificacao.EMAIL,
            destinatario='teste@email.com',
            mensagem='Mensagem teste',
            status=StatusNotificacao.PENDENTE,
            data_agendamento=timezone.now() + timedelta(hours=1)
        )

        resultado = processar_notificacoes_pendentes()

        assert resultado['enviadas'] == 0


# =============================================================================
# TESTES DE REENVIAR NOTIFICACAO
# =============================================================================

@pytest.mark.django_db
class TestReenviarNotificacao:
    """Testes da task reenviar_notificacao"""

    @patch('notificacoes.tasks.enviar_notificacao')
    def test_reenviar_notificacao_sucesso(self, mock_enviar):
        """Reenvia notificação com sucesso"""
        mock_enviar.return_value = (True, '')

        notif = Notificacao.objects.create(
            tipo=TipoNotificacao.EMAIL,
            destinatario='teste@email.com',
            mensagem='Mensagem teste',
            status=StatusNotificacao.ERRO
        )

        resultado = reenviar_notificacao(notif.id)

        notif.refresh_from_db()
        assert resultado is True
        assert notif.status == StatusNotificacao.ENVIADA

    @patch('notificacoes.tasks.enviar_notificacao')
    def test_reenviar_notificacao_falha(self, mock_enviar):
        """Marca erro quando reenvio falha"""
        mock_enviar.return_value = (False, '')

        notif = Notificacao.objects.create(
            tipo=TipoNotificacao.EMAIL,
            destinatario='teste@email.com',
            mensagem='Mensagem teste',
            status=StatusNotificacao.ERRO
        )

        resultado = reenviar_notificacao(notif.id)

        notif.refresh_from_db()
        assert resultado is False
        assert notif.status == StatusNotificacao.ERRO

    def test_reenviar_notificacao_inexistente(self):
        """Retorna False para notificação inexistente"""
        resultado = reenviar_notificacao(99999)
        assert resultado is False
