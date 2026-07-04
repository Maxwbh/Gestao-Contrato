"""
Testes das máscaras de entrada e do banner de rascunho do wizard.

F2-01 / F2-04 / F2-05: classes mask-* nos campos e elemento draft-banner no step1.
"""
import pytest
from django.test import Client
from django.urls import reverse

from tests.fixtures.factories import SuperUserFactory

pytestmark = pytest.mark.django_db


def staff_client():
    c = Client(enforce_csrf_checks=False)
    c.force_login(SuperUserFactory())
    return c


class TestMaskClassesComprador:

    def test_cpf_tem_classe_mask_cpf(self):
        r = staff_client().get(reverse('core:criar_comprador'), secure=True)
        assert r.status_code == 200
        html = r.content.decode('utf-8')
        assert 'mask-cpf' in html

    def test_celular_tem_classe_mask_phone(self):
        r = staff_client().get(reverse('core:criar_comprador'), secure=True)
        html = r.content.decode('utf-8')
        assert 'mask-phone' in html


class TestMaskClassesImobiliaria:

    def test_cnpj_tem_classe_mask_cnpj(self):
        r = staff_client().get(reverse('core:criar_imobiliaria'), secure=True)
        assert r.status_code == 200
        html = r.content.decode('utf-8')
        assert 'mask-cnpj' in html

    def test_cep_tem_classe_mask_cep(self):
        r = staff_client().get(reverse('core:criar_imobiliaria'), secure=True)
        html = r.content.decode('utf-8')
        assert 'mask-cep' in html


class TestWizardDraftBanner:

    def test_step1_tem_draft_banner(self):
        r = staff_client().get(
            reverse('contratos:wizard', kwargs={'step': 'basico'}), secure=True
        )
        assert r.status_code == 200
        html = r.content.decode('utf-8')
        assert 'draft-banner' in html

    def test_step1_tem_botao_retomar(self):
        r = staff_client().get(
            reverse('contratos:wizard', kwargs={'step': 'basico'}), secure=True
        )
        html = r.content.decode('utf-8')
        assert 'resumeDraft' in html

    def test_step1_tem_botao_descartar(self):
        r = staff_client().get(
            reverse('contratos:wizard', kwargs={'step': 'basico'}), secure=True
        )
        html = r.content.decode('utf-8')
        assert 'discardDraft' in html

    def test_imobiliaria_form_tem_accordion_boleto(self):
        r = staff_client().get(reverse('core:criar_imobiliaria'), secure=True)
        html = r.content.decode('utf-8')
        assert 'acc-boleto' in html
        assert 'toggleAccordion' in html
