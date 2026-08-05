"""
Disponibilidade de métodos de cobrança por Banco/Provider (dupla) no cadastro
da imobiliária: só habilita métodos suportados pelas contas cadastradas.
"""
import pytest

from core.models import MetodoCobranca as M


@pytest.mark.django_db
class TestMetodosDisponiveis:
    def _imob(self):
        from tests.fixtures.factories import ImobiliariaFactory
        return ImobiliariaFactory()

    def _conta(self, imob, provider, banco):
        from tests.fixtures.factories import ContaBancariaApiFactory
        return ContaBancariaApiFactory(imobiliaria=imob, provider=provider,
                                       banco=banco, ativo=True)

    def test_sem_conta_api_so_boleto_e_carne(self):
        imob = self._imob()
        disp = imob.metodos_disponiveis()
        assert disp == {M.BOLETO, M.CARNE}

    def test_conta_c6_habilita_bolepix_pixauto_checkout(self):
        imob = self._imob()
        self._conta(imob, 'c6', '336')
        disp = imob.metodos_disponiveis()
        assert M.BOLETO_PIX in disp
        assert M.PIX_AUTOMATICO in disp
        assert M.CHECKOUT in disp

    def test_conta_sicoob_online_habilita_bolepix_checkout(self):
        imob = self._imob()
        self._conta(imob, 'sicoob', '756')
        disp = imob.metodos_disponiveis()
        assert M.CHECKOUT in disp
        assert M.PIX_AUTOMATICO in disp
        assert M.BOLETO_PIX in disp       # BoletoPix exige provider online (C6/Sicoob)

    def test_conta_inativa_nao_conta(self):
        imob = self._imob()
        c = self._conta(imob, 'c6', '336')
        c.ativo = False
        c.save()
        assert imob.metodos_disponiveis() == {M.BOLETO, M.CARNE}


@pytest.mark.django_db
class TestMetodosPorConta:
    """Métodos ficam DENTRO da conta (metodos_habilitados), saneados por provider."""

    def _conta(self, provider, banco, metodos=None):
        from tests.fixtures.factories import ContaBancariaApiFactory
        return ContaBancariaApiFactory(provider=provider, banco=banco,
                                       metodos_habilitados=metodos if metodos is not None else [])

    def test_provider_inter_online(self):
        from core.models import METODOS_POR_PROVIDER, ProviderBoleto
        s = METODOS_POR_PROVIDER[ProviderBoleto.INTER]
        assert M.BOLETO_PIX in s and M.CHECKOUT in s and M.PIX_AUTOMATICO in s

    def test_default_offline_boleto_carne(self):
        c = self._conta('pycobranca', '001')
        assert set(c.metodos_habilitados) == {'boleto', 'carne'}

    def test_default_online_bolepix(self):
        c = self._conta('c6', '336')
        assert c.metodos_habilitados == ['bolepix']

    def test_sanear_remove_metodo_nao_suportado(self):
        # checkout não existe no offline → é removido; boleto puxa carnê.
        c = self._conta('pycobranca', '001', metodos=['boleto', 'checkout'])
        assert set(c.metodos_habilitados) == {'boleto', 'carne'}

    def test_boleto_puxa_carne(self):
        c = self._conta('pycobranca', '001', metodos=['boleto'])
        assert 'carne' in c.metodos_habilitados

    def test_metodos_oferecidos_uniao_das_contas(self):
        from tests.fixtures.factories import ImobiliariaFactory, ContaBancariaApiFactory
        imob = ImobiliariaFactory()
        ContaBancariaApiFactory(imobiliaria=imob, provider='pycobranca', banco='001',
                                metodos_habilitados=['boleto'])
        ContaBancariaApiFactory(imobiliaria=imob, provider='c6', banco='336',
                                metodos_habilitados=['bolepix', 'checkout'])
        assert imob.metodos_oferecidos() == {'boleto', 'carne', 'bolepix', 'checkout'}

    def test_inter_habilita_checkout(self):
        from tests.fixtures.factories import ImobiliariaFactory, ContaBancariaApiFactory
        imob = ImobiliariaFactory()
        ContaBancariaApiFactory(imobiliaria=imob, provider='inter', banco='077',
                                metodos_habilitados=['bolepix', 'checkout'])
        assert imob.metodo_habilitado('checkout') is True


@pytest.mark.django_db
class TestFormValidaMetodosPorConta:
    def _form_data(self, imob, metodos):
        # campos mínimos exigidos pelo ImobiliariaForm
        return {
            'contabilidade': imob.contabilidade_id or '',
            'nome': imob.nome, 'razao_social': imob.razao_social or 'RS',
            'cnpj': imob.cnpj, 'metodos_cobranca': metodos,
            'checkout_juros_por': 'emissor', 'checkout_max_parcelas': 12,
            'checkout_valor_minimo_parcela': '0.00',
        }

    def test_rejeita_metodo_sem_conta_compativel(self):
        from core.forms import ImobiliariaForm
        from tests.fixtures.factories import ImobiliariaFactory
        imob = ImobiliariaFactory()  # sem conta API
        form = ImobiliariaForm(data=self._form_data(imob, ['boleto', 'checkout']),
                               instance=imob)
        assert not form.is_valid()
        assert 'metodos_cobranca' in form.errors

    def test_aceita_metodo_com_conta_compativel(self):
        from core.forms import ImobiliariaForm
        from tests.fixtures.factories import ImobiliariaFactory, ContaBancariaApiFactory
        imob = ImobiliariaFactory()
        ContaBancariaApiFactory(imobiliaria=imob, provider='c6', banco='336', ativo=True)
        form = ImobiliariaForm(data=self._form_data(imob, ['boleto', 'checkout']),
                               instance=imob)
        # metodos_cobranca não deve acusar erro (outros campos podem, ignoramos)
        form.is_valid()
        assert 'metodos_cobranca' not in form.errors

    def test_json_do_mapa_exposto(self):
        from core.forms import ImobiliariaForm
        import json
        form = ImobiliariaForm()
        mapa = json.loads(form.metodos_por_provider_json)
        valores = lambda prov: {d['value'] for d in mapa[prov]}
        # Cada item é {value, label} para o front montar os checkboxes por conta.
        assert 'checkout' in valores('c6')
        assert 'bolepix' in valores('sicoob')          # BoletoPix é online (C6/Sicoob)
        assert valores('pycobranca') == {'boleto'}     # offline: Boleto/Carnê (carnê omitido)
        rot = {d['value']: d['label'] for d in mapa['c6']}
        assert rot['bolepix'] == 'Boleto on-line (BoletoPix)'
