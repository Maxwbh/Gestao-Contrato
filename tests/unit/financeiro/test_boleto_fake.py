"""
Boleto Fake — testes do gerador de dados de boleto/Pix para testes (CT-09,
CENARIOS_TESTE_BOLETO_API.md §3). Nenhum acesso a rede ou banco de dados:
valida os algoritmos reais de DV (mod-10/mod-11 FEBRABAN), o CRC16 do BR Code
e o contrato de retorno usado pelos simuladores.
"""
from datetime import date
from decimal import Decimal

import pytest

from financeiro.services.boleto_fake import (
    crc16_ccitt,
    fator_vencimento,
    gerar_codigo_barras_fake,
    gerar_linha_digitavel,
    gerar_pdf_boleto_fake,
    gerar_pix_copia_cola_fake,
    modulo10,
    modulo11_barras,
    montar_boleto_fake,
)


class TestCodigoBarras:
    def test_tem_44_digitos_numericos(self):
        cb = gerar_codigo_barras_fake('336', '1234.56', date(2026, 8, 10),
                                      nosso_numero='000000042', carteira='10')
        assert len(cb) == 44 and cb.isdigit()

    def test_estrutura_banco_moeda_valor(self):
        cb = gerar_codigo_barras_fake('756', '500.00', date(2026, 9, 5),
                                      nosso_numero='000000001')
        assert cb[0:3] == '756'
        assert cb[3] == '9'  # moeda BRL
        assert cb[9:19] == f'{50000:010d}'  # R$ 500,00 em centavos

    def test_dv_geral_mod11_confere(self):
        cb = gerar_codigo_barras_fake('336', '99.90', date(2026, 7, 20),
                                      nosso_numero='000000007')
        sem_dv = cb[0:4] + cb[5:]
        assert int(cb[4]) == modulo11_barras(sem_dv)

    def test_fator_vencimento_pos_reset_2025(self):
        # 22/02/2025 é o dia do reinício FEBRABAN: fator = 1000
        assert fator_vencimento(date(2025, 2, 22)) == '1000'
        assert fator_vencimento(date(2025, 2, 23)) == '1001'

    def test_fator_vencimento_pre_reset(self):
        # Tabela FEBRABAN clássica: 03/07/2000 → 1000 + (dias desde 07/10/1997)
        assert fator_vencimento(date(2000, 7, 3)) == '1000'


class TestLinhaDigitavel:
    def test_tem_47_digitos(self):
        cb = gerar_codigo_barras_fake('336', '1234.56', date(2026, 8, 10),
                                      nosso_numero='000000042', carteira='10')
        linha = gerar_linha_digitavel(cb)
        digitos = linha.replace('.', '').replace(' ', '')
        assert len(digitos) == 47 and digitos.isdigit()

    def test_dvs_mod10_dos_tres_campos(self):
        cb = gerar_codigo_barras_fake('756', '500.00', date(2026, 9, 5),
                                      nosso_numero='000000001')
        digitos = gerar_linha_digitavel(cb).replace('.', '').replace(' ', '')
        campo1, campo2, campo3 = digitos[0:10], digitos[10:21], digitos[21:32]
        assert int(campo1[-1]) == modulo10(campo1[:-1])
        assert int(campo2[-1]) == modulo10(campo2[:-1])
        assert int(campo3[-1]) == modulo10(campo3[:-1])

    def test_espelha_codigo_barras(self):
        cb = gerar_codigo_barras_fake('336', '77.10', date(2026, 10, 1),
                                      nosso_numero='000000123')
        digitos = gerar_linha_digitavel(cb).replace('.', '').replace(' ', '')
        # Reconstrução: banco+moeda, campo livre, DV geral, fator+valor
        assert digitos[0:4] == cb[0:4]
        assert digitos[4:9] == cb[19:24]
        assert digitos[10:20] == cb[24:34]
        assert digitos[21:31] == cb[34:44]
        assert digitos[32] == cb[4]
        assert digitos[33:47] == cb[5:19]

    def test_rejeita_codigo_invalido(self):
        with pytest.raises(ValueError):
            gerar_linha_digitavel('123')


class TestPixCopiaCola:
    def test_crc16_valido(self):
        pix = gerar_pix_copia_cola_fake('fake@teste.com', 'GESTAO',
                                        'SETE LAGOAS', '1234.56', 'TX1')
        assert pix[-8:-4] == '6304'
        assert pix[-4:] == crc16_ccitt(pix[:-4])

    def test_contem_txid_e_valor(self):
        pix = gerar_pix_copia_cola_fake('fake@teste.com', 'GESTAO',
                                        'SETE LAGOAS', '99.90', 'GC0000001P0001')
        assert 'GC0000001P0001' in pix
        assert '99.90' in pix
        assert 'br.gov.bcb.pix' in pix


class TestPdfFake:
    def test_pdf_minimo_valido(self):
        pdf = gerar_pdf_boleto_fake('BOLETO FAKE', ['linha 1', 'linha 2'])
        assert pdf.startswith(b'%PDF-1.4')
        assert pdf.rstrip().endswith(b'%%EOF')
        assert b'BOLETO FAKE' in pdf


class TestMontarBoletoFake:
    def test_contrato_de_retorno_igual_ao_cliente(self):
        """Chaves idênticas às de BoletoApiClient._normalizar_cobranca (+ext_ref)."""
        r = montar_boleto_fake(
            banco='756', valor='500.00', vencimento=date(2026, 9, 5),
            nosso_numero='000000001', cobranca_id='sim-756-1-000000001')
        for chave in ('sucesso', 'cobranca_id', 'status', 'nosso_numero',
                      'nosso_numero_formatado', 'nosso_numero_dv',
                      'linha_digitavel', 'codigo_barras', 'pix_copia_cola',
                      'pix_qrcode', 'valor', 'pdf_content', 'raw', 'ext_ref'):
            assert chave in r
        assert r['sucesso'] is True
        assert r['status'] == 'registrado'
        assert r['valor'] == Decimal('500.00')
        assert r['raw'] == {'fake': True}

    def test_bolepix_tem_pix_e_ext_ref(self):
        r = montar_boleto_fake(
            banco='336', valor='250.00', vencimento=date(2026, 8, 1),
            nosso_numero='000000002', metodo='bolepix', txid='TX2',
            cobranca_id='sim-336-1-000000002', ext_ref='bp-336-1-000000002')
        assert r['ext_ref'] == 'bp-336-1-000000002'
        assert r['pix_copia_cola'][-4:] == crc16_ccitt(r['pix_copia_cola'][:-4])

    def test_boleto_simples_nao_tem_pix(self):
        r = montar_boleto_fake(
            banco='756', valor='100.00', vencimento=date(2026, 8, 1),
            nosso_numero='000000003', metodo='boleto')
        assert r['pix_copia_cola'] == ''
        assert r['ext_ref'] == ''

    def test_pdf_opcional(self):
        r = montar_boleto_fake(
            banco='756', valor='100.00', vencimento=date(2026, 8, 1),
            nosso_numero='000000004', com_pdf=False)
        assert r['pdf_content'] is None
