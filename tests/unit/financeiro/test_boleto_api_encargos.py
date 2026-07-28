"""
Encargos enviados ao gateway na cobrança registrada (C6/Sicoob).

O gateway repassa multa/juros/desconto à API do banco como **dicts tipados**
({'tipo', 'valor', 'data_inicio'|'data_limite'}); antes o Django mandava só um
float de multa/juros e não mandava desconto — o banco cobrava o padrão dele, e
o boleto registrado divergia do boleto offline (CNAB) do mesmo contrato.
"""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

REG = 'financeiro.services.boleto_api_client.BoletoApiClient.registrar_cobranca'
CRED = 'financeiro.services.boleto_api_client.BoletoApiClient.criar_credenciais'


def _ok():
    return {
        'sucesso': True, 'cobranca_id': 'cob-enc', 'nosso_numero': '1',
        'nosso_numero_formatado': '1', 'nosso_numero_dv': '', 'linha_digitavel': 'L',
        'codigo_barras': 'C', 'pix_copia_cola': '', 'pix_qrcode': '',
        'valor': Decimal('1000.00'), 'pdf_content': None,
    }


@pytest.fixture
def cenario(db):
    """Contrato Sicoob com encargos próprios (não herda da imobiliária)."""
    from tests.fixtures.factories import (
        ImobiliariaFactory, ContaBancariaApiFactory, ImovelFactory, CompradorFactory,
    )
    from contratos.models import Contrato, StatusContrato, TipoAmortizacao, TipoCorrecao
    from financeiro.models import StatusBoleto, TipoParcela

    imob = ImobiliariaFactory()
    conta = ContaBancariaApiFactory(imobiliaria=imob, banco='756', provider='sicoob',
                                    principal=True)
    imovel = ImovelFactory(imobiliaria=imob, disponivel=False)
    contrato = Contrato.objects.create(
        imobiliaria=imob, imovel=imovel, comprador=CompradorFactory(),
        numero_contrato='CTR-ENC-1', data_contrato=date(2025, 1, 1),
        data_primeiro_vencimento=date(2025, 2, 1),
        valor_total=Decimal('60000.00'), valor_entrada=Decimal('10000.00'),
        numero_parcelas=6, dia_vencimento=1,
        tipo_amortizacao=TipoAmortizacao.PRICE, tipo_correcao=TipoCorrecao.FIXO,
        status=StatusContrato.ATIVO,
        usar_config_boleto_imobiliaria=False,
        tipo_valor_multa='PERCENTUAL', valor_multa_boleto=Decimal('2.00'),
        tipo_valor_juros='PERCENTUAL', valor_juros_boleto=Decimal('1.00'),
        dias_carencia_boleto=3,
        # Contrato usa PERCENTUAL/VALOR; Imobiliária usa PERCENTUAL/REAL —
        # ambos mapeiam para FIXO no gateway.
        tipo_valor_desconto='VALOR', valor_desconto_boleto=Decimal('50.00'),
        dias_desconto_boleto=5,
    )
    contrato.parcelas.filter(tipo_parcela=TipoParcela.NORMAL).update(
        status_boleto=StatusBoleto.NAO_GERADO, pago=False, conta_bancaria=conta,
        valor_boleto=Decimal('8333.33'),
    )
    return imob, conta, contrato


@pytest.mark.django_db
class TestEncargosNoPayload:
    def _emitir(self, conta, contrato):
        parcela = contrato.parcelas.first()
        with patch(CRED, return_value={'sucesso': True, 'bapi_token': 'bapi_x'}), \
             patch(REG, return_value=_ok()) as reg:
            parcela.gerar_boleto(conta_bancaria=conta, enviar_email=False)
        return parcela, reg.call_args.args[3]

    def test_multa_e_juros_sao_dicts_tipados(self, cenario):
        _, conta, contrato = cenario
        parcela, cob = self._emitir(conta, contrato)
        # carência 3 dias → encargos começam no 4º dia após o vencimento
        inicio = (parcela.data_vencimento + timedelta(days=4)).strftime('%Y-%m-%d')
        assert cob['multa'] == {'tipo': 'PERCENTUAL', 'valor': 2.0, 'data_inicio': inicio}
        assert cob['juros'] == {'tipo': 'PERCENTUAL', 'valor': 1.0, 'data_inicio': inicio}

    def test_desconto_com_data_limite(self, cenario):
        _, conta, contrato = cenario
        parcela, cob = self._emitir(conta, contrato)
        # REAL do sistema → FIXO no gateway; limite = vencimento - 5 dias
        limite = (parcela.data_vencimento - timedelta(days=5)).strftime('%Y-%m-%d')
        assert cob['desconto'] == {'tipo': 'FIXO', 'valor': 50.0, 'data_limite': limite}

    def test_vencimento_iso_e_valor(self, cenario):
        """Vencimento em ISO e valor da parcela (valor_boleto antes da emissão)."""
        _, conta, contrato = cenario
        esperado = float(contrato.parcelas.first().valor_boleto)
        parcela, cob = self._emitir(conta, contrato)
        assert cob['vencimento'] == parcela.data_vencimento.strftime('%Y-%m-%d')
        assert cob['valor'] == esperado

    def test_sem_encargos_configurados_nao_envia(self, cenario):
        """Zerados não vão no payload — o banco aplica o padrão da conta."""
        _, conta, contrato = cenario
        contrato.valor_multa_boleto = Decimal('0')
        contrato.valor_juros_boleto = Decimal('0')
        contrato.valor_desconto_boleto = Decimal('0')
        contrato.save(update_fields=['valor_multa_boleto', 'valor_juros_boleto',
                                     'valor_desconto_boleto'])
        _, cob = self._emitir(conta, contrato)
        assert 'multa' not in cob and 'juros' not in cob and 'desconto' not in cob


@pytest.mark.django_db
class TestRoteamentoPorProvider:
    """C6/Sicoob (provider próprio) registram individualmente no banco; contas
    offline (brcobranca) usam o multi. Os dois modos existem no gateway, e o
    `provider` da conta é o que decide o caminho."""

    URL = 'financeiro:boletos_painel_gerar'
    LOTE = 'financeiro.services.boleto_service.BoletoService.gerar_boletos_lote'

    def _post(self, cli, contrato):
        import json
        from django.urls import reverse
        return cli.post(reverse(self.URL),
                        data=json.dumps({'escopo': 'contratos',
                                         'contrato_ids': [contrato.pk],
                                         'quantidade': 2,
                                         'incluir_intermediarias': False}),
                        content_type='application/json')

    def test_provider_proprio_nao_usa_multi(self, cenario, client):
        from tests.fixtures.factories import SuperUserFactory
        _, conta, contrato = cenario  # conta sicoob
        client.force_login(SuperUserFactory())
        seq = {'n': 0}

        def _reg(*a, **kw):
            seq['n'] += 1
            r = _ok()
            # nosso_numero único por parcela (unique_nosso_numero_por_conta)
            r['nosso_numero'] = r['nosso_numero_formatado'] = f'{seq["n"]:08d}'
            return r

        with patch(self.LOTE) as lote, \
             patch(CRED, return_value={'sucesso': True, 'bapi_token': 'b'}), \
             patch(REG, side_effect=_reg) as reg, \
             patch('financeiro.services.geracao_boletos_service.GeracaoBoletosService.notificar_lote'):
            r = self._post(client, contrato)
        assert r.status_code == 200
        lote.assert_not_called()      # multi é só para conta offline
        assert reg.called             # registrou individualmente no banco

    def test_conta_offline_usa_multi(self, cenario, client):
        from tests.fixtures.factories import SuperUserFactory
        from financeiro.models import StatusBoleto
        _, conta, contrato = cenario
        conta.provider = 'brcobranca'
        conta.save(update_fields=['provider'])
        client.force_login(SuperUserFactory())

        def _lote(pares, tamanho_lote=None):
            for p, _c in pares:
                p.status_boleto = StatusBoleto.GERADO
                p.nosso_numero = f'NN{p.pk}'
                p.save(update_fields=['status_boleto', 'nosso_numero'])
            return {'gerados': len(pares), 'erros': []}

        with patch(self.LOTE, side_effect=_lote) as lote, \
             patch(REG) as reg, \
             patch('financeiro.services.geracao_boletos_service.GeracaoBoletosService.notificar_lote'):
            r = self._post(client, contrato)
        assert r.status_code == 200 and r.json()['total_gerados'] == 2
        lote.assert_called_once()
        reg.assert_not_called()       # não registra no banco no modo offline


@pytest.mark.django_db
class TestCnabSomenteOffline:
    """CNAB é exclusivo do modo offline. O corte usa o provider QUE GEROU o
    boleto (Parcela.provider), porque a conta pode trocar de modo depois."""

    def test_parcela_registrada_fora_da_elegibilidade(self, cenario):
        """Conta voltou para offline, mas o boleto saiu registrado → sem CNAB."""
        from core.models import Imobiliaria
        from financeiro.models import StatusBoleto
        from financeiro.services.cnab_service import CNABService
        imob, conta, contrato = cenario

        p = contrato.parcelas.first()
        p.status_boleto = StatusBoleto.GERADO
        p.nosso_numero = '99999999'
        p.provider = 'sicoob'          # emitido em cobrança registrada
        p.save(update_fields=['status_boleto', 'nosso_numero', 'provider'])
        conta.provider = 'brcobranca'  # conta migrou para offline depois
        conta.save(update_fields=['provider'])

        elegiveis = CNABService().obter_boletos_elegiveis_painel(
            imobiliarias=Imobiliaria.objects.filter(pk=imob.pk))
        assert p.pk not in {x.pk for x in elegiveis}

    def test_parcela_offline_entra_na_elegibilidade(self, cenario):
        from core.models import Imobiliaria
        from financeiro.models import StatusBoleto
        from financeiro.services.cnab_service import CNABService
        imob, conta, contrato = cenario
        conta.provider = 'brcobranca'
        conta.save(update_fields=['provider'])

        p = contrato.parcelas.first()
        p.status_boleto = StatusBoleto.GERADO
        p.nosso_numero = '88888888'
        p.provider = ''                # emitido no fluxo offline
        p.data_vencimento = date.today() + timedelta(days=15)  # RN-01: futuro
        p.save(update_fields=['status_boleto', 'nosso_numero', 'provider',
                              'data_vencimento'])

        elegiveis = CNABService().obter_boletos_elegiveis_painel(
            imobiliarias=Imobiliaria.objects.filter(pk=imob.pk))
        assert p.pk in {x.pk for x in elegiveis}

    def test_gerar_remessa_ignora_parcela_registrada(self, cenario):
        """Mesmo passada explicitamente, parcela registrada não entra no arquivo."""
        from financeiro.models import StatusBoleto
        from financeiro.services.cnab_service import CNABService
        _, conta, contrato = cenario
        conta.provider = 'brcobranca'
        conta.save(update_fields=['provider'])

        p = contrato.parcelas.first()
        p.status_boleto = StatusBoleto.GERADO
        p.nosso_numero = '77777777'
        p.provider = 'c6'
        p.save(update_fields=['status_boleto', 'nosso_numero', 'provider'])

        r = CNABService().gerar_remessa([p], conta)
        assert r['sucesso'] is False
        assert 'Nenhuma parcela valida' in r['erro']


@pytest.mark.django_db
class TestHelperEncargos:
    def test_desconto_sem_dias_usa_vencimento(self, cenario):
        from financeiro.models import _encargos_para_gateway
        _, _, contrato = cenario
        contrato.dias_desconto_boleto = 0
        contrato.save(update_fields=['dias_desconto_boleto'])
        venc = date(2026, 9, 10)
        enc = _encargos_para_gateway(contrato, venc)
        assert enc['desconto']['data_limite'] == '2026-09-10'

    def test_config_da_imobiliaria_quando_herda(self, cenario):
        """usar_config_boleto_imobiliaria=True → encargos vêm da imobiliária."""
        from financeiro.models import _encargos_para_gateway
        imob, _, contrato = cenario
        imob.percentual_multa_padrao = Decimal('5.00')
        imob.tipo_valor_multa = 'PERCENTUAL'
        imob.dias_para_encargos_padrao = 0
        imob.save(update_fields=['percentual_multa_padrao', 'tipo_valor_multa',
                                 'dias_para_encargos_padrao'])
        contrato.usar_config_boleto_imobiliaria = True
        contrato.save(update_fields=['usar_config_boleto_imobiliaria'])
        enc = _encargos_para_gateway(contrato, date(2026, 9, 10))
        assert enc['multa']['valor'] == 5.0
        assert enc['multa']['data_inicio'] == '2026-09-11'  # sem carência → D+1
