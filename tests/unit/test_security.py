"""
Testes de segurança — CSRF, autenticação obrigatória, input injection.

Verifica que views sensíveis exigem autenticação e que inputs maliciosos
não causam erros inesperados nem exposição de dados.
"""
import re
import subprocess
from pathlib import Path

import pytest
from django.urls import reverse
from core.hashids_utils import encode_id
from tests.fixtures.factories import UserFactory, ContratoFactory


@pytest.fixture
def usuario(db):
    return UserFactory()


@pytest.fixture
def client_logado(client, usuario):
    client.force_login(usuario)
    return client


@pytest.fixture
def contrato(db):
    return ContratoFactory()


# =============================================================================
# AUTENTICAÇÃO OBRIGATÓRIA
# =============================================================================

@pytest.mark.django_db
class TestAutenticacaoObrigatoria:
    """Views que requerem login devem redirecionar usuário anônimo"""

    def test_dashboard_exige_login(self, client):
        url = reverse('financeiro:dashboard')
        resp = client.get(url)
        assert resp.status_code == 302
        assert '/login' in resp.url or '/accounts/login' in resp.url

    def test_listar_contratos_exige_login(self, client):
        url = reverse('contratos:listar')
        resp = client.get(url)
        assert resp.status_code == 302

    def test_listar_parcelas_exige_login(self, client):
        url = reverse('financeiro:listar_parcelas')
        resp = client.get(url)
        assert resp.status_code == 302

    def test_dashboard_contabilidade_exige_login(self, client):
        url = reverse('financeiro:dashboard_contabilidade')
        resp = client.get(url)
        assert resp.status_code == 302

    def test_gerar_boleto_exige_login(self, client, contrato):
        parcela = contrato.parcelas.order_by('numero_parcela').first()
        url = reverse('financeiro:gerar_boleto', kwargs={'hid': encode_id(parcela.pk)})
        resp = client.get(url)
        assert resp.status_code == 302

    def test_api_contratos_exige_login(self, client):
        url = reverse('financeiro:api_contratos')
        resp = client.get(url)
        assert resp.status_code == 302

    def test_api_parcelas_exige_login(self, client):
        url = reverse('financeiro:api_parcelas')
        resp = client.get(url)
        assert resp.status_code == 302


# =============================================================================
# PARÂMETROS INVÁLIDOS — SEM CRASH
# =============================================================================

@pytest.mark.django_db
class TestParametrosInvalidos:
    """IDs inexistentes devem retornar 404, não 500"""

    def test_detalhe_contrato_inexistente_retorna_404(self, client_logado):
        url = reverse('contratos:detalhe', kwargs={'hid': encode_id(999999)})
        resp = client_logado.get(url)
        assert resp.status_code == 404

    def test_detalhe_parcela_inexistente_retorna_404(self, client_logado):
        url = reverse('financeiro:detalhe_parcela', kwargs={'hid': encode_id(999999)})
        resp = client_logado.get(url)
        assert resp.status_code == 404

    def test_download_boleto_inexistente_retorna_302_ou_404(self, client_logado):
        url = reverse('financeiro:download_boleto', kwargs={'hid': encode_id(999999)})
        resp = client_logado.get(url)
        assert resp.status_code in (302, 404)

    def test_api_boleto_inexistente_retorna_404(self, client_logado):
        url = reverse('financeiro:api_boleto_detalhe', kwargs={'parcela_id': 999999})
        resp = client_logado.get(url)
        assert resp.status_code == 404


# =============================================================================
# PORTAL — ISOLAMENTO DE DADOS
# =============================================================================

@pytest.mark.django_db
class TestIsolamentoDadosPortal:
    """Portal comprador não deve expor dados de outros compradores"""

    def test_portal_exige_autenticacao(self, client):
        url = reverse('portal_comprador:dashboard')
        resp = client.get(url)
        assert resp.status_code == 302

    def test_portal_login_exige_autenticacao(self, client):
        url = reverse('portal_comprador:meus_contratos')
        resp = client.get(url)
        assert resp.status_code == 302

    def test_portal_boletos_exige_autenticacao(self, client):
        url = reverse('portal_comprador:meus_boletos')
        resp = client.get(url)
        assert resp.status_code == 302


# =============================================================================
# SEM SEGREDOS HARDCODED — proteção contra vazamento de credenciais
# =============================================================================

# Chaves sensíveis que nunca devem receber um valor literal real no código.
_SECRET_KEYS = (
    'EMAIL_HOST_PASSWORD', 'EMAIL_PASSWORD', 'SMTP_PASSWORD',
    'BOUNCE_IMAP_PASSWORD', 'TWILIO_AUTH_TOKEN', 'SECRET_KEY',
    'TASK_TOKEN', 'GEMINI_API_KEY', 'AWS_SECRET_ACCESS_KEY',
)

# Valores de exemplo aceitos (não são segredos reais).
_PLACEHOLDER = re.compile(
    r'sua-senha|sua_senha|your-|your_|change|placeholder|example|'
    r'exemplo|xxxx|senha-de-app|senha-de-apl|senha-imap|token-secreto|min-[0-9]|'
    r'seu-email|test|teste|fake|dummy|redacted|senha_teste|dev-secret|dev-key|'
    r'localhost|local-|<[^>]+>|\{\{',
    re.IGNORECASE,
)

# Atribuição de credencial conhecida a um literal de 8+ caracteres.
_ASSIGN = re.compile(
    r'(' + '|'.join(_SECRET_KEYS) + r')\s*[:=]\s*[\'"]?([A-Za-z0-9/+=_.:@-]{8,})[\'"]?'
)

# Trechos que indicam leitura dinâmica (não um segredo embutido).
_DYNAMIC = re.compile(
    r'config\(|os\.|getenv|env\(|getattr|environ|=\s*(config|env|os|self|request|settings)\b'
)

_PRIVATE_KEY = re.compile(r'BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY')
_AWS_KEY = re.compile(r'AKIA[0-9A-Z]{16}')


def _tracked_source_files():
    """Arquivos versionados que devem estar livres de segredos.

    Exclui tests/ e docs/ (contêm placeholders e exemplos propositais) e
    arquivos de template de ambiente (.env.example)."""
    root = Path(__file__).resolve().parents[2]
    try:
        out = subprocess.run(
            ['git', 'ls-files', '-z'],
            cwd=root, capture_output=True, text=True, check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip('git indisponível — varredura de segredos ignorada')

    exts = {'.py', '.yaml', '.yml', '.sh', '.cfg', '.ini', '.toml', '.json'}
    for rel in filter(None, out.split('\0')):
        p = Path(rel)
        if p.parts and p.parts[0] in {'tests', 'docs'}:
            continue
        if p.name.endswith('.example') or p.name in {'.env.example'}:
            continue
        # A própria varredura (este arquivo) contém os padrões literais.
        if p.name == 'test_security.py':
            continue
        if p.suffix.lower() in exts:
            yield root / p


def test_nenhum_segredo_hardcoded_no_codigo():
    """Nenhum arquivo versionado deve conter credenciais SMTP/tokens embutidos.

    Barreira em CI contra vazamentos como o detectado pelo GitGuardian.
    O hook scripts/hooks/pre-commit aplica a mesma regra localmente.
    """
    ofensores = []
    for path in _tracked_source_files():
        try:
            texto = path.read_text(encoding='utf-8', errors='ignore')
        except OSError:
            continue
        for num, linha in enumerate(texto.splitlines(), start=1):
            if _PRIVATE_KEY.search(linha) or _AWS_KEY.search(linha):
                ofensores.append(f'{path.name}:{num}: {linha.strip()[:80]}')
                continue
            m = _ASSIGN.search(linha)
            if not m:
                continue
            valor = m.group(2)
            if _PLACEHOLDER.search(linha) or _PLACEHOLDER.search(valor):
                continue
            if _DYNAMIC.search(linha) or valor in ('', 'None'):
                continue
            ofensores.append(f'{path.name}:{num}: {linha.strip()[:80]}')

    assert not ofensores, (
        'Credenciais aparentemente hardcoded encontradas:\n  '
        + '\n  '.join(ofensores)
    )
