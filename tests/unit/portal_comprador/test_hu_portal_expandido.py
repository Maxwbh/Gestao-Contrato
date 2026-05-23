"""
HU Portal Expandido — Roadmap 34.4 P2
======================================

Cobre as novas features do portal do comprador:
  - Upload de comprovante de pagamento
  - Aprovação/rejeição de comprovante (admin)
  - Histórico unificado
  - Simulador de antecipação read-only
"""

import pytest
from decimal import Decimal
from datetime import date
from io import BytesIO

from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from portal_comprador.models import AcessoComprador, ComprovantePagamentoUpload
from tests.fixtures.factories import (
    UserFactory, CompradorFactory, ImobiliariaFactory,
    ContaBancariaFactory, ImovelFactory,
)


@pytest.fixture
def comprador_com_contrato(db, client):
    """Comprador logado com 1 contrato e parcelas geradas."""
    from contratos.models import Contrato, TipoAmortizacao, TipoCorrecao, StatusContrato

    imob = ImobiliariaFactory(nome='Imob Portal Expandido')
    ContaBancariaFactory(imobiliaria=imob, principal=True, ativo=True)
    imovel = ImovelFactory(imobiliaria=imob, disponivel=False)
    comprador = CompradorFactory(nome='Comprador Portal')
    usuario = UserFactory()
    acesso = AcessoComprador.objects.create(
        comprador=comprador, usuario=usuario, ativo=True,
    )
    contrato = Contrato.objects.create(
        imobiliaria=imob, imovel=imovel, comprador=comprador,
        numero_contrato='CTR-PORTAL-EXP-001',
        data_contrato=date(2025, 1, 1),
        data_primeiro_vencimento=date(2025, 2, 1),
        valor_total=Decimal('12000.00'),
        valor_entrada=Decimal('2000.00'),
        numero_parcelas=10, dia_vencimento=1,
        tipo_amortizacao=TipoAmortizacao.PRICE,
        tipo_correcao=TipoCorrecao.IPCA, prazo_reajuste_meses=12,
        status=StatusContrato.ATIVO,
    )
    client.force_login(usuario)
    return {
        'client': client, 'comprador': comprador, 'usuario': usuario,
        'acesso': acesso, 'contrato': contrato,
    }


def _arquivo_pdf_falso(nome='comprovante.pdf'):
    """SimpleUploadedFile com conteúdo minimal de PDF."""
    return SimpleUploadedFile(
        nome, b'%PDF-1.4\nfake comprovante content', content_type='application/pdf',
    )


# ---------------------------------------------------------------------------
# Upload de Comprovante
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUploadComprovante:
    def test_get_exige_autenticacao(self, client):
        url = reverse('portal_comprador:upload_comprovante', args=[1])
        resp = client.get(url)
        assert resp.status_code == 302

    def test_get_renderiza_formulario(self, comprador_com_contrato):
        ctx = comprador_com_contrato
        parcela = ctx['contrato'].parcelas.order_by('numero_parcela').first()
        url = reverse('portal_comprador:upload_comprovante', args=[parcela.pk])
        resp = ctx['client'].get(url)
        assert resp.status_code == 200

    def test_parcela_de_outro_comprador_retorna_404(self, comprador_com_contrato):
        ctx = comprador_com_contrato
        outro = CompradorFactory()
        from contratos.models import Contrato, TipoAmortizacao, TipoCorrecao, StatusContrato
        contrato_outro = Contrato.objects.create(
            imobiliaria=ctx['contrato'].imobiliaria,
            imovel=ImovelFactory(imobiliaria=ctx['contrato'].imobiliaria, disponivel=False),
            comprador=outro,
            numero_contrato='OUTRO',
            data_contrato=date(2025, 1, 1),
            data_primeiro_vencimento=date(2025, 2, 1),
            valor_total=Decimal('1000.00'), valor_entrada=Decimal('100.00'),
            numero_parcelas=2, dia_vencimento=1,
            tipo_amortizacao=TipoAmortizacao.PRICE,
            tipo_correcao=TipoCorrecao.IPCA, prazo_reajuste_meses=12,
            status=StatusContrato.ATIVO,
        )
        parcela_outro = contrato_outro.parcelas.first()
        url = reverse('portal_comprador:upload_comprovante', args=[parcela_outro.pk])
        resp = ctx['client'].get(url)
        assert resp.status_code == 404

    def test_parcela_ja_paga_retorna_404(self, comprador_com_contrato):
        ctx = comprador_com_contrato
        parcela = ctx['contrato'].parcelas.first()
        parcela.pago = True
        parcela.valor_pago = Decimal('1000.00')
        parcela.data_pagamento = date(2025, 2, 1)
        parcela.save()
        url = reverse('portal_comprador:upload_comprovante', args=[parcela.pk])
        resp = ctx['client'].get(url)
        assert resp.status_code == 404

    def test_post_cria_comprovante_pendente(self, comprador_com_contrato):
        ctx = comprador_com_contrato
        parcela = ctx['contrato'].parcelas.first()
        url = reverse('portal_comprador:upload_comprovante', args=[parcela.pk])
        resp = ctx['client'].post(url, data={
            'valor_informado': '1000.00',
            'data_pagamento_informada': '2025-02-01',
            'forma_pagamento': 'PIX',
            'comprovante': _arquivo_pdf_falso(),
            'observacoes_comprador': 'Pagamento via PIX',
        })
        assert resp.status_code == 302
        comp = ComprovantePagamentoUpload.objects.filter(parcela=parcela).first()
        assert comp is not None
        assert comp.status == ComprovantePagamentoUpload.STATUS_PENDENTE
        assert comp.valor_informado == Decimal('1000.00')
        assert comp.acesso_comprador == ctx['acesso']

    def test_arquivo_muito_grande_rejeitado(self, comprador_com_contrato):
        ctx = comprador_com_contrato
        parcela = ctx['contrato'].parcelas.first()
        arquivo_grande = SimpleUploadedFile(
            'big.pdf', b'x' * (11 * 1024 * 1024), content_type='application/pdf',
        )
        url = reverse('portal_comprador:upload_comprovante', args=[parcela.pk])
        resp = ctx['client'].post(url, data={
            'valor_informado': '1000.00',
            'data_pagamento_informada': '2025-02-01',
            'forma_pagamento': 'PIX',
            'comprovante': arquivo_grande,
        })
        assert resp.status_code == 200
        assert not ComprovantePagamentoUpload.objects.filter(parcela=parcela).exists()

    def test_formato_invalido_rejeitado(self, comprador_com_contrato):
        ctx = comprador_com_contrato
        parcela = ctx['contrato'].parcelas.first()
        arquivo_exe = SimpleUploadedFile(
            'virus.exe', b'MZ', content_type='application/octet-stream',
        )
        url = reverse('portal_comprador:upload_comprovante', args=[parcela.pk])
        resp = ctx['client'].post(url, data={
            'valor_informado': '1000.00',
            'data_pagamento_informada': '2025-02-01',
            'forma_pagamento': 'PIX',
            'comprovante': arquivo_exe,
        })
        assert resp.status_code == 200
        assert not ComprovantePagamentoUpload.objects.filter(parcela=parcela).exists()


# ---------------------------------------------------------------------------
# Aprovação / Rejeição de Comprovante
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAprovacaoComprovante:
    def test_aprovar_marca_parcela_como_paga(self, comprador_com_contrato):
        ctx = comprador_com_contrato
        parcela = ctx['contrato'].parcelas.first()
        admin_user = UserFactory()
        comp = ComprovantePagamentoUpload.objects.create(
            parcela=parcela,
            acesso_comprador=ctx['acesso'],
            comprovante=_arquivo_pdf_falso(),
            valor_informado=Decimal('1000.00'),
            data_pagamento_informada=date(2025, 2, 1),
            forma_pagamento='PIX',
        )
        ok = comp.aprovar(admin_user)
        assert ok is True
        parcela.refresh_from_db()
        assert parcela.pago is True
        assert parcela.valor_pago == Decimal('1000.00')
        comp.refresh_from_db()
        assert comp.status == ComprovantePagamentoUpload.STATUS_APROVADO
        assert comp.validado_por == admin_user

    def test_aprovar_cria_historico_pagamento(self, comprador_com_contrato):
        from financeiro.models import HistoricoPagamento
        ctx = comprador_com_contrato
        parcela = ctx['contrato'].parcelas.first()
        admin_user = UserFactory()
        comp = ComprovantePagamentoUpload.objects.create(
            parcela=parcela,
            comprovante=_arquivo_pdf_falso(),
            valor_informado=Decimal('1000.00'),
            data_pagamento_informada=date(2025, 2, 1),
            forma_pagamento='PIX',
        )
        comp.aprovar(admin_user)
        hp = HistoricoPagamento.objects.filter(
            parcela=parcela, origem_pagamento='PORTAL_UPLOAD'
        ).first()
        assert hp is not None
        assert hp.valor_pago == Decimal('1000.00')

    def test_aprovar_duas_vezes_e_idempotente(self, comprador_com_contrato):
        ctx = comprador_com_contrato
        parcela = ctx['contrato'].parcelas.first()
        admin_user = UserFactory()
        comp = ComprovantePagamentoUpload.objects.create(
            parcela=parcela,
            comprovante=_arquivo_pdf_falso(),
            valor_informado=Decimal('1000.00'),
            data_pagamento_informada=date(2025, 2, 1),
            forma_pagamento='PIX',
        )
        assert comp.aprovar(admin_user) is True
        assert comp.aprovar(admin_user) is False

    def test_rejeitar_registra_motivo(self, comprador_com_contrato):
        ctx = comprador_com_contrato
        parcela = ctx['contrato'].parcelas.first()
        admin_user = UserFactory()
        comp = ComprovantePagamentoUpload.objects.create(
            parcela=parcela,
            comprovante=_arquivo_pdf_falso(),
            valor_informado=Decimal('1000.00'),
            data_pagamento_informada=date(2025, 2, 1),
            forma_pagamento='PIX',
        )
        comp.rejeitar(admin_user, 'Comprovante ilegível')
        comp.refresh_from_db()
        assert comp.status == ComprovantePagamentoUpload.STATUS_REJEITADO
        assert 'ilegível' in comp.motivo_rejeicao

    def test_aprovar_de_parcela_ja_paga_rejeita_automaticamente(self, comprador_com_contrato):
        ctx = comprador_com_contrato
        parcela = ctx['contrato'].parcelas.first()
        parcela.pago = True
        parcela.valor_pago = Decimal('1000.00')
        parcela.data_pagamento = date(2025, 2, 1)
        parcela.save()
        admin_user = UserFactory()
        comp = ComprovantePagamentoUpload.objects.create(
            parcela=parcela,
            comprovante=_arquivo_pdf_falso(),
            valor_informado=Decimal('1000.00'),
            data_pagamento_informada=date(2025, 2, 1),
            forma_pagamento='PIX',
        )
        assert comp.aprovar(admin_user) is False
        comp.refresh_from_db()
        assert comp.status == ComprovantePagamentoUpload.STATUS_REJEITADO


# ---------------------------------------------------------------------------
# Histórico Unificado
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestHistoricoUnificado:
    def test_exige_autenticacao(self, client):
        url = reverse('portal_comprador:historico_unificado')
        resp = client.get(url)
        assert resp.status_code == 302

    def test_retorna_200_para_comprador_autenticado(self, comprador_com_contrato):
        ctx = comprador_com_contrato
        url = reverse('portal_comprador:historico_unificado')
        resp = ctx['client'].get(url)
        assert resp.status_code == 200

    def test_lista_apenas_dados_do_comprador(self, comprador_com_contrato):
        from financeiro.models import HistoricoPagamento
        ctx = comprador_com_contrato
        parcela = ctx['contrato'].parcelas.first()
        HistoricoPagamento.objects.create(
            parcela=parcela,
            data_pagamento=date(2025, 2, 1),
            valor_pago=Decimal('1000.00'),
            valor_parcela=parcela.valor_atual,
            forma_pagamento='PIX',
            origem_pagamento='MANUAL',
        )
        url = reverse('portal_comprador:historico_unificado')
        resp = ctx['client'].get(url)
        assert resp.status_code == 200
        assert b'PIX' in resp.content


# ---------------------------------------------------------------------------
# Simulador de Antecipação Portal
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSimuladorAntecipacaoPortal:
    def test_exige_autenticacao(self, client, comprador_com_contrato):
        ctx = comprador_com_contrato
        ctx['client'].logout()
        url = reverse('portal_comprador:simulador_antecipacao', args=[ctx['contrato'].id])
        resp = ctx['client'].get(url)
        assert resp.status_code == 302

    def test_get_renderiza(self, comprador_com_contrato):
        ctx = comprador_com_contrato
        url = reverse('portal_comprador:simulador_antecipacao', args=[ctx['contrato'].id])
        resp = ctx['client'].get(url)
        assert resp.status_code == 200

    def test_contrato_de_outro_comprador_retorna_404(self, comprador_com_contrato):
        ctx = comprador_com_contrato
        outro = CompradorFactory()
        from contratos.models import Contrato, TipoAmortizacao, TipoCorrecao, StatusContrato
        outro_contrato = Contrato.objects.create(
            imobiliaria=ctx['contrato'].imobiliaria,
            imovel=ImovelFactory(imobiliaria=ctx['contrato'].imobiliaria, disponivel=False),
            comprador=outro,
            numero_contrato='OUTRO-SIM',
            data_contrato=date(2025, 1, 1),
            data_primeiro_vencimento=date(2025, 2, 1),
            valor_total=Decimal('1000.00'), valor_entrada=Decimal('100.00'),
            numero_parcelas=2, dia_vencimento=1,
            tipo_amortizacao=TipoAmortizacao.PRICE,
            tipo_correcao=TipoCorrecao.IPCA, prazo_reajuste_meses=12,
            status=StatusContrato.ATIVO,
        )
        url = reverse('portal_comprador:simulador_antecipacao', args=[outro_contrato.id])
        resp = ctx['client'].get(url)
        assert resp.status_code == 404

    def test_post_simula_economia(self, comprador_com_contrato):
        ctx = comprador_com_contrato
        parcelas = list(ctx['contrato'].parcelas.order_by('numero_parcela')[:2])
        url = reverse('portal_comprador:simulador_antecipacao', args=[ctx['contrato'].id])
        resp = ctx['client'].post(url, data={
            'parcelas': [str(parcelas[0].id), str(parcelas[1].id)],
            'desconto': '5',
        })
        assert resp.status_code == 200
        # Não deve aplicar — parcelas permanecem não pagas
        parcelas[0].refresh_from_db()
        assert parcelas[0].pago is False

    def test_simulador_nao_aplica_pagamento(self, comprador_com_contrato):
        """Simulador deve ser sempre read-only — nunca marca parcelas como pagas."""
        ctx = comprador_com_contrato
        parcela = ctx['contrato'].parcelas.first()
        url = reverse('portal_comprador:simulador_antecipacao', args=[ctx['contrato'].id])
        ctx['client'].post(url, data={
            'parcelas': [str(parcela.id)],
            'desconto': '10',
            'action': 'aplicar',  # mesmo se enviado, view ignora
        })
        parcela.refresh_from_db()
        assert parcela.pago is False
