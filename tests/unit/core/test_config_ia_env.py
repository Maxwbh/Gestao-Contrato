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


@pytest.mark.django_db
class TestModelosClaudeConfiguraveis:
    def test_cascade_padrao_usa_sonnet_atual(self):
        from contratos.services.importacao_ia import _TIERS_CLAUDE
        assert 'claude-sonnet-5' in _TIERS_CLAUDE
        assert 'claude-sonnet-4-6' not in _TIERS_CLAUDE

    def test_cascade_le_parametro_csv(self):
        """Sem WorkflowIA ativo, o parâmetro IA_TIERS_CLAUDE define a cascade."""
        from contratos.services.importacao_ia import _carregar_tiers_workflow
        with patch('core.parametros.get_param',
                   return_value='claude-haiku-4-5-20251001, claude-opus-4-8'):
            tiers = _carregar_tiers_workflow()
        assert tiers == ('claude-haiku-4-5-20251001', 'claude-opus-4-8')

    def test_workflow_do_banco_tem_precedencia(self):
        from core.models import WorkflowIA, WorkflowIATier
        from contratos.services.importacao_ia import _carregar_tiers_workflow
        wf = WorkflowIA.objects.create(nome='WF', ativo=True)
        WorkflowIATier.objects.create(workflow=wf, modelo='claude-sonnet-5', ordem=1)
        with patch('core.parametros.get_param', return_value='claude-opus-4-8'):
            tiers = _carregar_tiers_workflow()
        assert tiers == ('claude-sonnet-5',)

    def test_gemini_model_le_parametro(self):
        from contratos.services.importacao_ia import _gemini_model
        with patch('core.parametros.get_param', return_value='gemini-2.5-flash'):
            assert _gemini_model() == 'gemini-2.5-flash'
        with patch('core.parametros.get_param', return_value=''):
            assert _gemini_model() == 'gemini-2.0-flash'

    def test_choices_do_workflow_incluem_sonnet5_e_marcam_legado(self):
        from core.models import WorkflowIATier
        valores = dict(WorkflowIATier.MODELO_CHOICES)
        assert 'claude-sonnet-5' in valores
        assert 'legado' in valores['claude-sonnet-4-6']

    def test_tabela_de_precos_cobre_sonnet5(self):
        from core.services.ia_monitor import _PRECOS
        assert _PRECOS['claude-sonnet-5'] == (3.00, 15.00)


class TestVersaoCanalHml:
    def _versao(self, canal):
        import core.version as v
        v._cached_version = None
        with patch.object(v, '_read_build_info',
                          return_value={'patch': '90', 'canal': canal}), \
             patch.object(v, '_read_base_version', return_value='3.2'):
            out = v.get_version()
        v._cached_version = None
        return out

    def test_build_da_main_gera_versao_oficial(self):
        assert self._versao('oficial') == '3.2.90'

    def test_build_de_hml_ganha_sufixo(self):
        """Versão oficial só na main: HML exibe 3.2.N-hml."""
        assert self._versao('hml') == '3.2.90-hml'


class TestVersaoSoAvancaComFonte:
    """Política de release: docs/infra não alteram o PATCH da versão."""

    def _git(self, cwd, *args):
        import subprocess
        subprocess.run(['git', '-C', str(cwd), *args], check=True,
                       capture_output=True)

    def test_commits_de_docs_nao_contam(self, tmp_path):
        import core.version as v
        self._git(tmp_path, 'init', '-q')
        self._git(tmp_path, 'config', 'user.email', 'ci@teste.local')
        self._git(tmp_path, 'config', 'user.name', 'CI Teste')

        (tmp_path / 'app.py').write_text('x = 1')
        self._git(tmp_path, 'add', '.')
        self._git(tmp_path, 'commit', '-q', '-m', 'fonte 1')

        (tmp_path / 'README.md').write_text('doc')
        self._git(tmp_path, 'add', '.')
        self._git(tmp_path, 'commit', '-q', '-m', 'so docs md')

        (tmp_path / 'docs').mkdir()
        (tmp_path / 'docs' / 'guia.txt').write_text('d')
        self._git(tmp_path, 'add', '.')
        self._git(tmp_path, 'commit', '-q', '-m', 'so pasta docs')

        (tmp_path / 'app.py').write_text('x = 2')
        (tmp_path / 'NOTAS.md').write_text('misto')
        self._git(tmp_path, 'add', '.')
        self._git(tmp_path, 'commit', '-q', '-m', 'fonte 2 + doc (conta)')

        # 4 commits no total; só os 2 que tocam fonte contam para o PATCH
        assert v._contar_commits_fonte(cwd=tmp_path) == 2


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
