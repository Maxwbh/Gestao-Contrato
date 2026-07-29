"""
Correções da listagem de contratos e do formulário:

  • contrato 100% pago passa a QUITADO (antes ficava "100.0% pago" com Ativo);
  • contrato 100% pago sai da régua de reajuste (sem saldo, nada a corrigir);
  • um imóvel não aceita dois contratos em vigor (origem dos contratos
    duplicados vistos na listagem);
  • o select "Método de Cobrança" oferece só os métodos habilitados na
    imobiliária (antes listava todos e só acusava erro depois de salvar).
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError


def _contrato(imob, numero='CTR-QUIT-1', parcelas=3, **kw):
    from tests.fixtures.factories import ImovelFactory, CompradorFactory
    from contratos.models import (Contrato, StatusContrato, TipoAmortizacao,
                                  TipoCorrecao)
    return Contrato.objects.create(
        imobiliaria=imob,
        imovel=kw.pop('imovel', None) or ImovelFactory(imobiliaria=imob, disponivel=False),
        comprador=CompradorFactory(),
        numero_contrato=numero,
        data_contrato=date(2025, 1, 1),
        data_primeiro_vencimento=date(2025, 2, 1),
        valor_total=Decimal('30000.00'), valor_entrada=Decimal('6000.00'),
        numero_parcelas=parcelas, dia_vencimento=1,
        tipo_amortizacao=TipoAmortizacao.PRICE,
        tipo_correcao=kw.pop('tipo_correcao', TipoCorrecao.FIXO),
        status=kw.pop('status', StatusContrato.ATIVO),
        **kw,
    )


@pytest.mark.django_db
class TestQuitacaoAutomatica:
    def test_pagar_ultima_parcela_quita_o_contrato(self, db):
        from tests.fixtures.factories import ImobiliariaFactory
        from contratos.models import StatusContrato
        contrato = _contrato(ImobiliariaFactory())
        parcelas = list(contrato.parcelas.all())
        assert parcelas, 'contrato deve gerar parcelas'

        for i, p in enumerate(parcelas, start=1):
            p.registrar_pagamento(valor_pago=p.valor_atual, validar_minimo=False)
            contrato.refresh_from_db()
            esperado = (StatusContrato.QUITADO if i == len(parcelas)
                        else StatusContrato.ATIVO)
            assert contrato.status == esperado, f'após {i}/{len(parcelas)} parcelas'

    def test_esta_totalmente_pago(self, db):
        from tests.fixtures.factories import ImobiliariaFactory
        contrato = _contrato(ImobiliariaFactory(), numero='CTR-QUIT-2')
        assert contrato.esta_totalmente_pago is False
        for p in contrato.parcelas.all():
            p.registrar_pagamento(valor_pago=p.valor_atual, validar_minimo=False)
        contrato.refresh_from_db()
        assert contrato.esta_totalmente_pago is True

    def test_cancelar_pagamento_reverte_quitacao(self, db):
        from tests.fixtures.factories import ImobiliariaFactory
        from contratos.models import StatusContrato
        contrato = _contrato(ImobiliariaFactory(), numero='CTR-QUIT-3')
        for p in contrato.parcelas.all():
            p.registrar_pagamento(valor_pago=p.valor_atual, validar_minimo=False)
        contrato.refresh_from_db()
        assert contrato.status == StatusContrato.QUITADO

        contrato.parcelas.first().cancelar_pagamento()
        contrato.refresh_from_db()
        assert contrato.status == StatusContrato.ATIVO

    def test_comando_sincroniza_base_existente(self, db):
        """Contratos que ficaram 100% pagos antes da mudança são reconciliados."""
        from django.core.management import call_command
        from tests.fixtures.factories import ImobiliariaFactory
        from contratos.models import Contrato, StatusContrato
        contrato = _contrato(ImobiliariaFactory(), numero='CTR-QUIT-4')
        # paga tudo direto no banco, sem passar pelo registrar_pagamento
        contrato.parcelas.all().update(pago=True, data_pagamento=date.today())
        Contrato.objects.filter(pk=contrato.pk).update(status=StatusContrato.ATIVO)

        call_command('sincronizar_quitacao', verbosity=0)
        contrato.refresh_from_db()
        assert contrato.status == StatusContrato.QUITADO


@pytest.mark.django_db
class TestReajusteNaoIncideEmQuitado:
    def test_contrato_pago_sai_da_regua(self, client, db):
        from django.urls import reverse
        from tests.fixtures.factories import ImobiliariaFactory, SuperUserFactory
        from contratos.models import TipoCorrecao, StatusContrato, Contrato

        imob = ImobiliariaFactory()
        # contrato IPCA vencido de reajuste, mas com tudo pago
        contrato = _contrato(imob, numero='CTR-REAJ-1',
                             tipo_correcao=TipoCorrecao.IPCA,
                             prazo_reajuste_meses=12)
        Contrato.objects.filter(pk=contrato.pk).update(
            data_contrato=date.today() - timedelta(days=800))
        contrato.parcelas.all().update(pago=True, data_pagamento=date.today())

        client.force_login(SuperUserFactory())
        resp = client.get(reverse('contratos:listar'))
        assert resp.status_code == 200
        pendentes = {i['contrato'].pk for i in resp.context['contratos_reajuste']}
        assert contrato.pk not in pendentes, 'contrato 100% pago não deve pedir reajuste'


@pytest.mark.django_db
class TestUmContratoPorImovel:
    def test_segundo_contrato_vigente_no_mesmo_imovel_e_rejeitado(self, db):
        from tests.fixtures.factories import ImobiliariaFactory, ImovelFactory
        imob = ImobiliariaFactory()
        imovel = ImovelFactory(imobiliaria=imob, disponivel=False)
        _contrato(imob, numero='CTR-DUP-1', imovel=imovel)

        from contratos.models import Contrato, StatusContrato, TipoAmortizacao, TipoCorrecao
        from tests.fixtures.factories import CompradorFactory
        segundo = Contrato(
            imobiliaria=imob, imovel=imovel, comprador=CompradorFactory(),
            numero_contrato='CTR-DUP-2', data_contrato=date(2025, 6, 1),
            data_primeiro_vencimento=date(2025, 7, 1),
            valor_total=Decimal('30000.00'), valor_entrada=Decimal('6000.00'),
            numero_parcelas=3, dia_vencimento=1,
            tipo_amortizacao=TipoAmortizacao.PRICE, tipo_correcao=TipoCorrecao.FIXO,
            status=StatusContrato.ATIVO,
        )
        with pytest.raises(ValidationError) as exc:
            segundo.full_clean()
        assert 'imovel' in exc.value.message_dict

    def test_imovel_quitado_pode_ser_revendido(self, db):
        """Depois de quitado/cancelado, o mesmo imóvel aceita novo contrato."""
        from tests.fixtures.factories import ImobiliariaFactory, ImovelFactory
        from contratos.models import Contrato, StatusContrato
        imob = ImobiliariaFactory()
        imovel = ImovelFactory(imobiliaria=imob, disponivel=False)
        primeiro = _contrato(imob, numero='CTR-REV-1', imovel=imovel)
        Contrato.objects.filter(pk=primeiro.pk).update(status=StatusContrato.QUITADO)

        segundo = _contrato(imob, numero='CTR-REV-2', imovel=imovel)
        segundo.full_clean()  # não deve levantar
        assert segundo.pk is not None


@pytest.mark.django_db
class TestMetodoCobrancaFiltrado:
    def test_select_mostra_so_habilitados(self, db):
        from tests.fixtures.factories import ImobiliariaFactory
        from contratos.forms import ContratoForm
        imob = ImobiliariaFactory()
        imob.metodos_cobranca = ['boleto', 'carne']
        imob.save(update_fields=['metodos_cobranca'])

        form = ContratoForm(initial={'imobiliaria': imob.pk})
        valores = [v for v, _ in form.fields['metodo_cobranca'].choices if v]
        assert set(valores) == {'boleto', 'carne'}
        assert 'bolepix' not in valores

    def test_metodo_atual_e_preservado_na_edicao(self, db):
        """Método já gravado continua na lista mesmo se foi desabilitado."""
        from tests.fixtures.factories import ImobiliariaFactory
        from contratos.forms import ContratoForm
        from contratos.models import Contrato
        imob = ImobiliariaFactory()
        imob.metodos_cobranca = ['boleto', 'bolepix']  # bolepix ainda habilitado
        imob.save(update_fields=['metodos_cobranca'])
        contrato = _contrato(imob, numero='CTR-MET-1', metodo_cobranca='bolepix')
        # depois a imobiliária desabilita o bolepix (update evita revalidar)
        imob.metodos_cobranca = ['boleto']
        imob.save(update_fields=['metodos_cobranca'])
        contrato = Contrato.objects.get(pk=contrato.pk)

        form = ContratoForm(instance=contrato)
        valores = [v for v, _ in form.fields['metodo_cobranca'].choices if v]
        assert 'bolepix' in valores and 'boleto' in valores

    def test_sem_restricao_mantem_todos(self, db):
        from tests.fixtures.factories import ImobiliariaFactory
        from contratos.forms import ContratoForm
        imob = ImobiliariaFactory()
        imob.metodos_cobranca = []
        imob.save(update_fields=['metodos_cobranca'])
        form = ContratoForm(initial={'imobiliaria': imob.pk})
        valores = [v for v, _ in form.fields['metodo_cobranca'].choices if v]
        assert len(valores) >= 4
