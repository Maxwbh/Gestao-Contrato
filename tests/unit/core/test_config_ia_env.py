"""
Revisão de configuração (.env) — IA: precedência unificada da
ANTHROPIC_API_KEY (env → parâmetro legado no banco) e garantia de que a chave
não é sincronizada em texto claro para ParametroSistema.
"""
from unittest.mock import patch

import pytest


@pytest.mark.django_db
class TestChaveAnthropicPrecedencia:
    def test_importacao_usa_env_primeiro(self, settings):
        from contratos.services.importacao_ia import ImportacaoIA
        settings.ANTHROPIC_API_KEY = 'sk-env-123'
        svc = ImportacaoIA()
        assert svc.client.api_key == 'sk-env-123'

    def test_importacao_cai_para_parametro_do_banco(self, settings):
        from contratos.services.importacao_ia import ImportacaoIA
        settings.ANTHROPIC_API_KEY = ''
        with patch('core.parametros.get_param', return_value='sk-banco-456'):
            svc = ImportacaoIA()
            assert svc.client.api_key == 'sk-banco-456'

    def test_importacao_sem_chave_erro_claro(self, settings):
        from contratos.services.importacao_ia import ImportacaoIA
        settings.ANTHROPIC_API_KEY = ''
        with patch('core.parametros.get_param', return_value=''):
            with pytest.raises(RuntimeError, match='ANTHROPIC_API_KEY'):
                ImportacaoIA().client


class TestSyncNaoVazaChaveIA:
    def test_anthropic_api_key_fora_da_lista_de_sync(self):
        """A chave de IA não pode ser gravada em texto claro no banco."""
        import core.management.commands.sync_params_from_env as sync_mod
        import inspect
        fonte = inspect.getsource(sync_mod)
        # A tupla de parâmetro ('ANTHROPIC_API_KEY', grupo, tipo, ...) não deve
        # existir — só a menção em comentário explicando a decisão.
        assert "('ANTHROPIC_API_KEY'" not in fonte
        assert "('GEMINI_API_KEY'" not in fonte
