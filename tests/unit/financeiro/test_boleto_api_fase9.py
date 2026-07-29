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

        # imob A: 1 liquidada + baixa por webhook (evento do gateway) + 1 recorrência
        pa = ParcelaFactory(contrato__imovel__imobiliaria=imob_a,
                            status_cobranca=S.LIQUIDADA, provider='c6')
        EventoCobrancaApi.objects.create(event_id='a1', event='liquidado',
                                         status='baixado', parcela=pa)
        RecorrenciaPix.objects.create(contrato=ContratoFactory(imovel__imobiliaria=imob_a),
                                      id_rec='RA', provider='c6', status=RecStatusPA.APROVADA)

        # imob B: 1 liquidada + baixa por polling + 1 recorrência cancelada
        pb = ParcelaFactory(contrato__imovel__imobiliaria=imob_b,
                            status_cobranca=S.LIQUIDADA, provider='sicoob')
        EventoCobrancaApi.objects.create(event_id='b1', event='conciliacao.polling-sicoob',
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

    def test_totais_nos_rodapes(self, client):
        """Rodapés dos cards expõem os totais (polish visual)."""
        from tests.fixtures.factories import ParcelaFactory, ContratoFactory
        self._login(client)
        p1 = ParcelaFactory(status_cobranca=S.LIQUIDADA, provider='c6')
        ParcelaFactory(status_cobranca=S.REGISTRADA, provider='c6')
        EventoCobrancaApi.objects.create(event_id='b1', event='liquidado',
                                         status='baixado', parcela=p1)
        EventoCobrancaApi.objects.create(event_id='b2', event='conciliacao.polling-sicoob',
                                         status='baixado', parcela=p1)
        RecorrenciaPix.objects.create(contrato=ContratoFactory(), id_rec='R1', provider='c6',
                                      status=RecStatusPA.APROVADA)
        r = client.get(reverse(URL))
        assert r.context['total'] == 2
        assert r.context['total_baixas'] == 2
        assert r.context['total_recorrencias'] == 1

    def test_origem_agrega_valores_reais_de_producao(self, client):
        """
        Origem agrega pelos valores que produção grava em EventoCobrancaApi.event:
        eventos do gateway (liquidado, pago, pix.recebido…) → Webhook;
        'conciliacao.polling-sicoob' → Polling Sicoob;
        'conciliacao.pix' (e o legado 'conciliacao.conciliacao-pix') → Conciliação Pix.
        """
        from tests.fixtures.factories import ParcelaFactory
        self._login(client)
        p = ParcelaFactory(status_cobranca=S.LIQUIDADA, provider='c6')
        for eid, ev in [('e1', 'liquidado'), ('e2', 'pix.recebido'),
                        ('e3', 'conciliacao.polling-sicoob'),
                        ('e4', 'conciliacao.pix'),
                        ('e5', 'conciliacao.conciliacao-pix')]:
            EventoCobrancaApi.objects.create(event_id=eid, event=ev,
                                             status='baixado', parcela=p)
        r = client.get(reverse(URL))
        rows = dict(r.context['origem_rows'])
        assert rows == {'Webhook': 2, 'Polling Sicoob': 1, 'Conciliação Pix': 2}

    def test_baixa_manual_transiciona_e_aparece_no_painel(self, client):
        """Baixa manual de cobrança API → LIQUIDADA + origem 'Baixa manual'."""
        from tests.fixtures.factories import ParcelaFactory
        self._login(client)
        p = ParcelaFactory(status_cobranca=S.REGISTRADA, provider='c6')
        p.registrar_pagamento(valor_pago=100)
        p.refresh_from_db()
        assert p.status_cobranca == S.LIQUIDADA
        assert EventoCobrancaApi.objects.filter(
            parcela=p, event='conciliacao.manual', status='baixado').count() == 1
        r = client.get(reverse(URL))
        assert ('Baixa manual', 1) in r.context['origem_rows']
        assert r.context['pct_conciliado'] == 100.0

    def test_baixa_via_banco_nao_gera_evento_manual(self):
        """Webhook/polling transicionam antes de pagar → sem evento 'manual'."""
        from tests.fixtures.factories import ParcelaFactory
        p = ParcelaFactory(status_cobranca=S.REGISTRADA, provider='c6')
        p.transicionar_cobranca(S.LIQUIDADA)  # ordem dos fluxos do banco
        p.registrar_pagamento(valor_pago=100)
        assert not EventoCobrancaApi.objects.filter(event='conciliacao.manual').exists()

    def test_baixa_manual_parcela_legado_sem_efeito(self):
        """Parcela BRCobrança/CNAB (sem status_cobranca) não entra no trilho API."""
        from tests.fixtures.factories import ParcelaFactory
        p = ParcelaFactory()  # status_cobranca=''
        p.registrar_pagamento(valor_pago=100)
        p.refresh_from_db()
        assert p.status_cobranca == ''
        assert not EventoCobrancaApi.objects.exists()

    def test_baixa_manual_nao_forca_transicao_ilegal(self):
        """AGUARDANDO_CIP→LIQUIDADA é ilegal: paga, mas não transiciona nem loga."""
        from tests.fixtures.factories import ParcelaFactory
        p = ParcelaFactory(status_cobranca=S.AGUARDANDO_CIP, provider='c6')
        p.registrar_pagamento(valor_pago=100)
        p.refresh_from_db()
        assert p.pago and p.status_cobranca == S.AGUARDANDO_CIP
        assert not EventoCobrancaApi.objects.filter(event='conciliacao.manual').exists()

    def test_jobs_boleto_api_agendados_no_beat(self):
        """Os 4 jobs de conciliação/agendamento estão no beat schedule."""
        from gestao_contrato.celery import app
        tasks = {e['task'] for e in app.conf.beat_schedule.values()}
        assert {'financeiro.tasks.polling_boletos_sicoob',
                'financeiro.tasks.conciliar_pix_recebidos',
                'financeiro.tasks.reprocessar_fila_cip',
                'financeiro.tasks.agendar_cobrancas_pix_automatico'} <= tasks

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
