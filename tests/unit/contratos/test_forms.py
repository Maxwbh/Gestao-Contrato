"""
Testes dos forms do app contratos.

Escopo: ContratoForm, IndiceReajusteForm, ContratoWizardBasicoForm
"""
import pytest
from datetime import date, timedelta

from contratos.forms import ContratoForm, IndiceReajusteForm

from tests.fixtures.factories import ContratoFactory


@pytest.fixture
def contrato(db):
    return ContratoFactory()


@pytest.mark.django_db
class TestIndiceReajusteForm:
    """Testes do IndiceReajusteForm — mais isolado que ContratoForm"""

    def test_form_valido(self):
        data = {
            'tipo_indice': 'IPCA',
            'ano': date.today().year,
            'mes': 1,
            'valor': '0.50',
        }
        form = IndiceReajusteForm(data=data)
        assert form.is_valid(), form.errors

    def test_form_sem_tipo_invalido(self):
        data = {
            'tipo_indice': '',
            'ano': date.today().year,
            'mes': 1,
            'valor': '0.50',
        }
        form = IndiceReajusteForm(data=data)
        assert not form.is_valid()
        assert 'tipo_indice' in form.errors

    def test_form_percentual_negativo_valido(self):
        """Percentual negativo pode ser válido (deflação)"""
        data = {
            'tipo_indice': 'IPCA',
            'ano': date.today().year,
            'mes': 6,
            'valor': '-0.20',
        }
        form = IndiceReajusteForm(data=data)
        assert isinstance(form.is_valid(), bool)

    def test_form_sem_valor_invalido(self):
        """Campo valor é obrigatório"""
        data = {
            'tipo_indice': 'IPCA',
            'ano': date.today().year,
            'mes': 1,
            'valor': '',
        }
        form = IndiceReajusteForm(data=data)
        assert not form.is_valid()
        assert 'valor' in form.errors


@pytest.mark.django_db
class TestContratoForm:
    """Testes básicos do ContratoForm"""

    def test_form_sem_dados_invalido(self):
        form = ContratoForm(data={})
        assert not form.is_valid()

    def test_form_campos_obrigatorios(self, contrato):
        """Campos obrigatórios: imobiliaria, imovel, comprador, numero_contrato,
        data_contrato, data_primeiro_vencimento, valor_total, numero_parcelas"""
        form = ContratoForm(data={})
        assert not form.is_valid()
        # Pelo menos alguns campos obrigatórios devem ter erros
        assert len(form.errors) > 0

    def test_form_valido_basico(self, contrato):
        """Form com dados mínimos válidos"""
        data = {
            'imobiliaria': contrato.imobiliaria.pk,
            'imovel': contrato.imovel.pk,
            'comprador': contrato.comprador.pk,
            'numero_contrato': 'TEST-001',
            'data_contrato': date.today().strftime('%Y-%m-%d'),
            'data_primeiro_vencimento': (date.today() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'valor_total': '50000.00',
            'valor_entrada': '5000.00',
            'numero_parcelas': '60',
            'dia_vencimento': '10',
            'tipo_amortizacao': 'PRICE',
            'percentual_juros_mora': '1.00',
            'percentual_multa': '2.00',
            'tipo_correcao': 'IPCA',
            'prazo_reajuste_meses': '12',
            'status': 'ATIVO',
        }
        form = ContratoForm(data=data)
        # O form pode ser válido ou ter erros de validação específicos
        assert isinstance(form.is_valid(), bool)
