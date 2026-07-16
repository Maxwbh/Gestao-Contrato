"""
Fase 9 Boleto-API — painel de conciliação da cobrança registrada: agrega
% conciliado, distribuição por status, recebido por origem e recorrências.

Cobre também a correção pós-revisão visual: o filtro por imobiliária deve
valer para TODOS os blocos (status, origem e recorrências), e o KPI de
eventos órfãos (sem parcela) só é exposto a quem tem permissão total.
"""
import pytest
from django.urls import reverse

from financeiro.models import (StatusCobranca as S, RecorrenciaPix, RecStatusPA,
                               EventoCobrancaApi)

URL = 'financeiro:painel_conciliacao_boleto_api'


@pytest.mark.django_db
class TestPainelConciliacao:
    def _login(self, client):
        from tests.fixtures.factories import SuperUserFactory
        user = SuperUserFactory()
        client.force_login(user)
        return user

    def test_painel_200_e_pct_conciliado(self, client):
        from tests.fixtures.factories import ParcelaFactory
        self._login(client)
        ParcelaFactory(status_cobranca=S.LIQUIDADA, provider='c6')
        ParcelaFactory(status_cobranca=S.REGISTRADA, provider='c6')
        r = client.get(reverse(URL))
        assert r.status_code == 200
        assert r.context['total'] == 2
        assert r.context['pct_conciliado'] == 50.0
        assert ('Liquidada', 1) in r.context['status_rows']

    def test_painel_sem_dados(self, client):
        self._login(client)
        r = client.get(reverse(URL))
        assert r.status_code == 200
        assert r.context['total'] == 0 and r.context['pct_conciliado'] == 0.0

    def test_recorrencias_no_contexto(self, client):
        from tests.fixtures.factories import ContratoFactory
        self._login(client)
        RecorrenciaPix.objects.create(contrato=ContratoFactory(), id_rec='R', provider='c6',
                                      status=RecStatusPA.APROVADA)
        r = client.get(reverse(URL))
        assert ('Aprovada', 1) in r.context['recorrencia_rows']

    def test_exige_login(self, client):
        r = client.get(reverse(URL))
        assert r.status_code in (302, 301)  # redireciona para login

    # ------------------------------------------------------------------
    # Correções pós-revisão visual
    # ------------------------------------------------------------------
    def test_filtro_imob_aplica_em_todos_os_blocos(self, client):
        """Selecionar uma imobiliária filtra status, origem E recorrências."""
        from tests.fixtures.factories import (ImobiliariaFactory, ContratoFactory,
                                              ParcelaFactory)
        self._login(client)
        imob_a = ImobiliariaFactory()
        imob_b = ImobiliariaFactory()

        # imob A: 1 liquidada + baixa por webhook + 1 recorrência aprovada
        pa = ParcelaFactory(contrato__imovel__imobiliaria=imob_a,
                            status_cobranca=S.LIQUIDADA, provider='c6')
        EventoCobrancaApi.objects.create(event_id='a1', event='webhook',
                                         status='baixado', parcela=pa)
        RecorrenciaPix.objects.create(contrato=ContratoFactory(imovel__imobiliaria=imob_a),
                                      id_rec='RA', provider='c6', status=RecStatusPA.APROVADA)

        # imob B: 1 liquidada + baixa por polling + 1 recorrência cancelada
        pb = ParcelaFactory(contrato__imovel__imobiliaria=imob_b,
                            status_cobranca=S.LIQUIDADA, provider='sicoob')
        EventoCobrancaApi.objects.create(event_id='b1', event='polling_sicoob',
                                         status='baixado', parcela=pb)
        RecorrenciaPix.objects.create(contrato=ContratoFactory(imovel__imobiliaria=imob_b),
                                      id_rec='RB', provider='sicoob', status=RecStatusPA.CANCELADA)

        # Sem filtro: vê os dois
        r = client.get(reverse(URL))
        assert r.context['total'] == 2
        assert ('Webhook', 1) in r.context['origem_rows']
        assert ('Polling Sicoob', 1) in r.context['origem_rows']
        assert ('Aprovada', 1) in r.context['recorrencia_rows']
        assert ('Cancelada', 1) in r.context['recorrencia_rows']

        # Com filtro imob A: origem e recorrências também restringem
        r = client.get(reverse(URL), {'imobiliaria': imob_a.id})
        assert r.context['total'] == 1
        assert ('Webhook', 1) in r.context['origem_rows']
        assert ('Polling Sicoob', 1) not in r.context['origem_rows']
        assert ('Aprovada', 1) in r.context['recorrencia_rows']
        assert ('Cancelada', 0) in r.context['recorrencia_rows']

    def test_origem_label_humanizado(self, client):
        """Slugs de origem viram rótulos legíveis ao operador."""
        from tests.fixtures.factories import ParcelaFactory
        self._login(client)
        p = ParcelaFactory(status_cobranca=S.LIQUIDADA, provider='c6')
        EventoCobrancaApi.objects.create(event_id='e1', event='conciliacao_pix',
                                         status='baixado', parcela=p)
        r = client.get(reverse(URL))
        assert ('Conciliação Pix', 1) in r.context['origem_rows']

    def test_sem_parcela_apenas_para_permissao_total(self, client):
        """Órfãos (sem parcela) são métrica global só para superuser/staff."""
        EventoCobrancaApi.objects.create(event_id='o1', event='webhook', status='sem_parcela')
        EventoCobrancaApi.objects.create(event_id='o2', event='webhook', status='sem_parcela')

        # Superuser: vê a contagem global
        self._login(client)
        r = client.get(reverse(URL))
        assert r.context['sem_parcela'] == 2

    def test_usuario_restrito_nao_ve_orfaos_nem_imob_de_terceiro(self, client):
        """Usuário com escopo restrito: órfãos=0 e filtro de imob alheia é ignorado."""
        from tests.fixtures.factories import (UserFactory, ImobiliariaFactory,
                                              AcessoUsuarioFactory, ParcelaFactory)
        imob_a = ImobiliariaFactory()
        imob_b = ImobiliariaFactory()
        user = UserFactory()
        AcessoUsuarioFactory(usuario=user, imobiliaria=imob_a,
                             contabilidade=imob_a.contabilidade)
        client.force_login(user)

        ParcelaFactory(contrato__imovel__imobiliaria=imob_a, status_cobranca=S.LIQUIDADA,
                       provider='c6')
        ParcelaFactory(contrato__imovel__imobiliaria=imob_b, status_cobranca=S.LIQUIDADA,
                       provider='c6')
        EventoCobrancaApi.objects.create(event_id='o1', event='webhook', status='sem_parcela')

        # Sem filtro: só a imob A
        r = client.get(reverse(URL))
        assert r.context['total'] == 1
        assert r.context['sem_parcela'] == 0  # órfão global não vaza para escopo restrito

        # Tentando filtrar por imob B (fora do escopo): ignora e mantém escopo próprio
        r = client.get(reverse(URL), {'imobiliaria': imob_b.id})
        assert r.context['total'] == 1
        assert r.context['imob_filtro'] == ''  # filtro alheio descartado
