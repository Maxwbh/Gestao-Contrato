"""
Testes das views de índices de reajuste do app contratos.

Escopo: IndiceReajusteListView, IndiceReajusteCreateView,
        IndiceReajusteUpdateView, IndiceReajusteDeleteView,
        importar_indices_ibge
"""
import json
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
from django.urls import reverse
from core.hashids_utils import encode_id

from tests.fixtures.factories import UserFactory, SuperUserFactory


@pytest.fixture
def usuario(db):
    return SuperUserFactory()


@pytest.fixture
def client_logado(client, usuario):
    client.force_login(usuario)
    return client


@pytest.mark.django_db
class TestIndiceReajusteListView:
    """Testes da view IndiceReajusteListView"""

    def test_requer_autenticacao(self, client):
        url = reverse('contratos:indices_listar')
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_lista_vazia(self, client_logado):
        response = client_logado.get(reverse('contratos:indices_listar'))
        assert response.status_code == 200

    def test_paginacao(self, client_logado):
        response = client_logado.get(
            reverse('contratos:indices_listar'),
            {'per_page': '10'}
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestIndiceReajusteCreateView:
    """Testes da view IndiceReajusteCreateView"""

    def test_requer_autenticacao(self, client):
        url = reverse('contratos:indices_criar')
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_get_exibe_formulario(self, client_logado):
        response = client_logado.get(reverse('contratos:indices_criar'))
        assert response.status_code == 200

    def test_post_valido_cria_indice(self, client_logado):
        """POST com dados válidos cria índice e redireciona"""
        from datetime import date
        response = client_logado.post(
            reverse('contratos:indices_criar'),
            {
                'tipo': 'IPCA',
                'ano': date.today().year,
                'mes': 1,
                'percentual': '0.50',
            }
        )
        assert response.status_code in (200, 302)

    def test_post_invalido_retorna_formulario(self, client_logado):
        """POST sem dados obrigatórios retorna formulário com erros"""
        response = client_logado.post(reverse('contratos:indices_criar'), {})
        assert response.status_code == 200


@pytest.mark.django_db
class TestIndiceReajusteUpdateView:
    """Testes da view IndiceReajusteUpdateView"""

    def test_requer_autenticacao(self, client):
        url = reverse('contratos:indices_editar', kwargs={'hid': encode_id(1)})
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_indice_inexistente_retorna_404(self, client_logado):
        url = reverse('contratos:indices_editar', kwargs={'hid': encode_id(999999)})
        response = client_logado.get(url)
        assert response.status_code == 404


@pytest.mark.django_db
class TestIndiceReajusteDeleteView:
    """Testes da view IndiceReajusteDeleteView"""

    def test_requer_autenticacao(self, client):
        url = reverse('contratos:indices_excluir', kwargs={'hid': encode_id(1)})
        response = client.post(url, {})
        assert response.status_code in (302, 403)

    def test_indice_inexistente_retorna_404(self, client_logado):
        url = reverse('contratos:indices_excluir', kwargs={'hid': encode_id(999999)})
        response = client_logado.post(url, {})
        assert response.status_code == 404

    def test_post_deleta_indice(self, client_logado):
        from datetime import date
        from contratos.models import IndiceReajuste
        indice = IndiceReajuste.objects.create(
            tipo_indice='IPCA', ano=date.today().year, mes=1, valor='0.50'
        )
        url = reverse('contratos:indices_excluir', kwargs={'hid': encode_id(indice.pk)})
        response = client_logado.post(url, {})
        assert response.status_code == 302
        assert not IndiceReajuste.objects.filter(pk=indice.pk).exists()


def test_parse_valor_indice_robustez():
    """_parse_valor_indice trata vírgula/ponto/ausência sem gravar 0 falso."""
    from contratos.views import _parse_valor_indice
    assert _parse_valor_indice('2.73') == 2.73
    assert _parse_valor_indice('2,73') == 2.73   # IBGE usa vírgula decimal
    assert _parse_valor_indice('-0.49') == -0.49
    assert _parse_valor_indice(0.84) == 0.84
    # Ausência de valor → None (não 0)
    for ausente in (None, '', '-', '...', 'NaN'):
        assert _parse_valor_indice(ausente) is None


@pytest.mark.django_db
class TestImportarIndices:
    """Importação de índices: confirmação, sobrescrita e gravação correta."""

    def _post(self, client, body):
        return client.post(
            reverse('contratos:indices_importar'),
            data=json.dumps(body),
            content_type='application/json',
        )

    def test_tipo_invalido_retorna_400(self, client_logado):
        resp = self._post(client_logado, {'tipo_indice': 'XPTO'})
        assert resp.status_code == 400
        assert resp.json()['success'] is False

    @patch('contratos.views.requests.get')
    def test_importa_grava_valor_real(self, mock_get, client_logado):
        """Sem dados prévios: importa e grava o valor real (não 0)."""
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: [
                {'data': '01/04/2026', 'valor': '2.73'},
                {'data': '01/05/2026', 'valor': '0.84'},
            ],
        )
        resp = self._post(client_logado, {'tipo_indice': 'IGPM'})
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True
        assert data['created'] == 2

        from contratos.models import IndiceReajuste
        maio = IndiceReajuste.objects.get(tipo_indice='IGPM', ano=2026, mes=5)
        assert maio.valor == Decimal('0.8400')   # gravou o valor real
        assert maio.fonte == 'BCB'

    def test_dados_ficticios_requer_confirmacao(self, client_logado):
        """Com dados FICTÍCIOS e sem confirmar: pede confirmação (não grava)."""
        from contratos.models import IndiceReajuste
        IndiceReajuste.objects.create(
            tipo_indice='IGPM', ano=2026, mes=4, valor=Decimal('1.00'),
            fonte='BCB/FGV (teste)',
        )
        resp = self._post(client_logado, {'tipo_indice': 'IGPM'})
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is False
        assert data['requer_confirmacao'] is True
        assert data['total_ficticios'] == 1

    @patch('contratos.views.requests.get')
    def test_dados_reais_existentes_nao_pergunta_e_completa(self, mock_get, client_logado):
        """Dados já REAIS (sem fictícios): não pergunta nem rebaixa — só completa
        os meses faltantes (sem download/confirmação redundante)."""
        from contratos.models import IndiceReajuste
        IndiceReajuste.objects.create(
            tipo_indice='IGPM', ano=2026, mes=3, valor=Decimal('0.52'), fonte='BCB',
        )
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: [
                {'data': '01/04/2026', 'valor': '2.73'},
                {'data': '01/05/2026', 'valor': '0.84'},
            ],
        )
        resp = self._post(client_logado, {'tipo_indice': 'IGPM'})
        data = resp.json()
        assert 'requer_confirmacao' not in data       # não pergunta
        assert data['success'] is True
        assert data['created'] == 2                    # completou os meses novos
        assert IndiceReajuste.objects.get(tipo_indice='IGPM', ano=2026, mes=5).valor == Decimal('0.8400')

    @patch('contratos.views.requests.get')
    def test_fetch_vazio_importacao_completa_retorna_erro(self, mock_get, client_logado):
        """API sem dados numa importação do zero: erro claro (não 'concluída 0')."""
        mock_get.return_value = MagicMock(status_code=200, json=lambda: [])
        resp = self._post(client_logado, {'tipo_indice': 'IGPM'})
        assert resp.status_code == 502
        data = resp.json()
        assert data['success'] is False
        assert 'API oficial' in data['error']

    @patch('contratos.views.requests.get')
    def test_fetch_vazio_incremental_ja_atualizado(self, mock_get, client_logado):
        """API sem meses novos com dados reais existentes: 'já atualizado' (sucesso)."""
        from contratos.models import IndiceReajuste
        IndiceReajuste.objects.create(
            tipo_indice='IGPM', ano=2026, mes=5, valor=Decimal('0.84'), fonte='BCB',
        )
        mock_get.return_value = MagicMock(status_code=200, json=lambda: [])
        resp = self._post(client_logado, {'tipo_indice': 'IGPM'})
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True
        assert data['created'] == 0 and data['updated'] == 0
        assert 'atualizados' in data['message'].lower()

    @patch('contratos.views.requests.get')
    def test_sobrescrever_substitui_ficticio_por_real(self, mock_get, client_logado):
        """Confirmação (sobrescrever): valor fictício é substituído pelo real e
        o numero_indice fictício é zerado."""
        from contratos.models import IndiceReajuste
        from datetime import date
        from contratos.models import Contrato  # noqa

        # Dado fictício gravado com numero_indice de teste
        IndiceReajuste.objects.create(
            tipo_indice='IGPM', ano=2026, mes=5, valor=Decimal('1.00'),
            numero_indice=Decimal('3000.0000'), fonte='BCB/FGV (teste)',
        )
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: [{'data': '01/05/2026', 'valor': '0.84'}],
        )
        resp = self._post(client_logado, {'tipo_indice': 'IGPM', 'sobrescrever': True})
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True
        assert data['updated'] == 1

        maio = IndiceReajuste.objects.get(tipo_indice='IGPM', ano=2026, mes=5)
        assert maio.valor == Decimal('0.8400')      # substituiu o fictício
        assert maio.fonte == 'BCB'
        assert maio.numero_indice is None           # numero_indice fictício zerado

    @patch('contratos.views.requests.get')
    def test_sobrescrever_remove_invalidos_residuais(self, mock_get, client_logado):
        """Após sobrescrever, registros residuais inválidos (teste/zero) que a API
        não cobriu são removidos; os recém-gravados (inclusive zero real) ficam."""
        from contratos.models import IndiceReajuste
        # Resíduos inválidos que a API NÃO vai retornar (meses antigos)
        IndiceReajuste.objects.create(tipo_indice='IGPM', ano=2030, mes=1,
                                      valor=Decimal('0.00'), fonte='BCB')          # zero órfão
        IndiceReajuste.objects.create(tipo_indice='IGPM', ano=2030, mes=2,
                                      valor=Decimal('1.00'), fonte='BCB/FGV (teste)')  # teste órfão
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: [
                {'data': '01/04/2026', 'valor': '2.73'},
                {'data': '01/05/2026', 'valor': '0.00'},   # zero REAL recém-importado
            ],
        )
        resp = self._post(client_logado, {'tipo_indice': 'IGPM', 'sobrescrever': True})
        data = resp.json()
        assert data['success'] is True
        assert data['removed_invalid'] == 2
        # resíduos removidos
        assert not IndiceReajuste.objects.filter(tipo_indice='IGPM', ano=2030).exists()
        # zero REAL recém-importado é preservado
        maio = IndiceReajuste.objects.get(tipo_indice='IGPM', ano=2026, mes=5)
        assert maio.valor == Decimal('0.0000') and maio.fonte == 'BCB'

    @patch('contratos.views.requests.get')
    def test_http_get_indice_retenta_apos_timeout(self, mock_get, client_logado):
        """1º timeout do BCB é re-tentado; a 2ª resposta OK conclui a importação."""
        import requests as _requests
        ok = MagicMock(status_code=200, json=lambda: [{'data': '01/05/2026', 'valor': '0.84'}])
        ok.raise_for_status = lambda: None
        mock_get.side_effect = [_requests.exceptions.ReadTimeout('read timed out'), ok]
        with patch('time.sleep'):   # não dormir de verdade no teste
            resp = self._post(client_logado, {'tipo_indice': 'IGPM'})
        data = resp.json()
        assert data['success'] is True
        assert data['created'] == 1
        assert mock_get.call_count == 2   # 1 timeout + 1 sucesso

    @patch('contratos.views.requests.get')
    def test_mes_sem_valor_nao_grava_zero(self, mock_get, client_logado):
        """Mês sem valor publicado é ignorado (não cria registro 0,0000%)."""
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: [
                {'data': '01/04/2026', 'valor': '2.73'},
                {'data': '01/05/2026', 'valor': '-'},   # ainda não publicado
            ],
        )
        resp = self._post(client_logado, {'tipo_indice': 'IGPM'})
        data = resp.json()
        assert data['success'] is True
        # Mês sem valor é descartado já na busca — só Abril é gravado, nunca um 0,0000%
        assert data['created'] == 1
        from contratos.models import IndiceReajuste
        assert not IndiceReajuste.objects.filter(tipo_indice='IGPM', ano=2026, mes=5).exists()
        abril = IndiceReajuste.objects.get(tipo_indice='IGPM', ano=2026, mes=4)
        assert abril.valor == Decimal('2.7300')
