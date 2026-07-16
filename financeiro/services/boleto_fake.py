"""
Boleto Fake — gerador de dados de boleto/Pix para testes e demonstração.

Monta um boleto completo SEM chamar a API do banco nem o gateway Boleto-API:
código de barras FEBRABAN (44 dígitos, DV mod-11), linha digitável (47 dígitos,
DVs mod-10), Pix copia-e-cola no padrão EMV/BR Code (CRC16-CCITT) e um PDF
mínimo de demonstração. Os algoritmos de dígito verificador são os reais, então
os campos passam por validações de formato — mas os dados são FICTÍCIOS e não
registram nada em banco algum.

Uso principal: `gerar_dados_teste` (cenários das HUs BAPI) e testes automatizados.
"""
from datetime import date
from decimal import Decimal


# Data-base do fator de vencimento (FEBRABAN). Em 22/02/2025 o fator estourou
# 9999 e reiniciou em 1000 (circular FEBRABAN de 2023).
_BASE_FATOR = date(1997, 10, 7)
_RESET_FATOR = date(2025, 2, 22)  # neste dia o fator volta a valer 1000


def modulo10(sequencia: str) -> int:
    """DV módulo 10 (campos da linha digitável), pesos 2/1 da direita p/ esquerda."""
    soma = 0
    peso = 2
    for digito in reversed(sequencia):
        parcial = int(digito) * peso
        if parcial > 9:
            parcial = parcial // 10 + parcial % 10
        soma += parcial
        peso = 1 if peso == 2 else 2
    resto = soma % 10
    return 0 if resto == 0 else 10 - resto


def modulo11_barras(sequencia43: str) -> int:
    """DV geral do código de barras (mod 11, pesos 2..9; resto 0/1/10 → DV 1)."""
    soma = 0
    peso = 2
    for digito in reversed(sequencia43):
        soma += int(digito) * peso
        peso = 2 if peso == 9 else peso + 1
    resto = soma % 11
    dv = 11 - resto
    return 1 if dv in (0, 1, 10, 11) else dv


def fator_vencimento(vencimento: date) -> str:
    """Fator de vencimento (4 dígitos) com o reinício de 22/02/2025."""
    if vencimento >= _RESET_FATOR:
        fator = 1000 + (vencimento - _RESET_FATOR).days
        # Após novo estouro (improvável em dados de teste), reinicia de novo
        fator = 1000 + (fator - 1000) % 9000
    else:
        fator = (vencimento - _BASE_FATOR).days
    return f'{fator:04d}'


def gerar_codigo_barras_fake(banco: str, valor, vencimento: date,
                             nosso_numero: str = '', carteira: str = '') -> str:
    """
    Código de barras FEBRABAN fake (44 dígitos):
    banco(3) + moeda(1)=9 + DV(1) + fator(4) + valor(10) + campo livre(25).
    O campo livre é sintético (carteira + nosso número), suficiente para telas,
    remessa de demonstração e validação de formato.
    """
    valor_centavos = int((Decimal(str(valor)) * 100).quantize(Decimal('1')))
    campo_livre = (f'{carteira:0>3.3}'[:3] + f'{nosso_numero:0>22.22}'[:22])
    campo_livre = ''.join(c if c.isdigit() else '0' for c in campo_livre)[:25].ljust(25, '0')
    parcial = f'{banco:0>3.3}' + '9' + fator_vencimento(vencimento) + f'{valor_centavos:010d}' + campo_livre
    dv = modulo11_barras(parcial)
    return parcial[:4] + str(dv) + parcial[4:]


def gerar_linha_digitavel(codigo_barras: str) -> str:
    """
    Converte o código de barras (44 dígitos) na linha digitável formatada
    (47 dígitos): AAABC.CCCCX DDDDD.DDDDDY EEEEE.EEEEEZ K UUUUVVVVVVVVVV.
    """
    if len(codigo_barras) != 44 or not codigo_barras.isdigit():
        raise ValueError('Código de barras deve ter 44 dígitos numéricos')
    banco_moeda = codigo_barras[0:4]
    dv_geral = codigo_barras[4]
    fator_valor = codigo_barras[5:19]
    campo_livre = codigo_barras[19:44]

    campo1 = banco_moeda + campo_livre[0:5]
    campo2 = campo_livre[5:15]
    campo3 = campo_livre[15:25]

    c1 = f'{campo1}{modulo10(campo1)}'
    c2 = f'{campo2}{modulo10(campo2)}'
    c3 = f'{campo3}{modulo10(campo3)}'
    return (f'{c1[0:5]}.{c1[5:10]} {c2[0:5]}.{c2[5:11]} '
            f'{c3[0:5]}.{c3[5:11]} {dv_geral} {fator_valor}')


def crc16_ccitt(payload: str) -> str:
    """CRC16-CCITT (poly 0x1021, init 0xFFFF) usado no BR Code Pix."""
    crc = 0xFFFF
    for byte in payload.encode('utf-8'):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if (crc & 0x8000) else (crc << 1)
            crc &= 0xFFFF
    return f'{crc:04X}'


def _emv(tag: str, valor: str) -> str:
    return f'{tag}{len(valor):02d}{valor}'


def gerar_pix_copia_cola_fake(chave: str, nome: str, cidade: str,
                              valor, txid: str) -> str:
    """
    Pix copia-e-cola fake no padrão EMV/BR Code estático com valor.
    CRC real (o payload passa em validadores de formato), chave fictícia.
    """
    merchant_account = _emv('00', 'br.gov.bcb.pix') + _emv('01', chave[:77])
    payload = (
        _emv('00', '01') +                                  # Payload Format
        _emv('26', merchant_account) +                       # Merchant Account (Pix)
        _emv('52', '0000') +                                 # MCC
        _emv('53', '986') +                                  # Moeda BRL
        _emv('54', f'{Decimal(str(valor)):.2f}') +           # Valor
        _emv('58', 'BR') +
        _emv('59', (nome or 'TESTE')[:25]) +
        _emv('60', (cidade or 'SETE LAGOAS')[:15]) +
        _emv('62', _emv('05', (txid or '***')[:25])) +       # txid
        '6304'                                               # CRC placeholder
    )
    return payload + crc16_ccitt(payload)


def gerar_pdf_boleto_fake(titulo: str, linhas) -> bytes:
    """
    PDF mínimo de uma página (sem dependências) com o texto do boleto fake.
    Serve para exercitar 2ª via / download / envio por e-mail nas telas.
    """
    conteudo = ['BT /F1 14 Tf 40 800 Td (%s) Tj ET' % _pdf_escape(titulo)]
    y = 770
    for linha in linhas:
        conteudo.append('BT /F1 10 Tf 40 %d Td (%s) Tj ET' % (y, _pdf_escape(str(linha))))
        y -= 18
    stream = '\n'.join(conteudo).encode('latin-1', 'replace')

    objetos = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] '
        b'/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length %d >>\nstream\n%s\nendstream' % (len(stream), stream),
    ]
    saida = bytearray(b'%PDF-1.4\n')
    offsets = []
    for i, corpo in enumerate(objetos, start=1):
        offsets.append(len(saida))
        saida += b'%d 0 obj\n%s\nendobj\n' % (i, corpo)
    xref_pos = len(saida)
    saida += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objetos) + 1)
    for off in offsets:
        saida += b'%010d 00000 n \n' % off
    saida += (b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n'
              % (len(objetos) + 1, xref_pos))
    return bytes(saida)


def _pdf_escape(texto: str) -> str:
    texto = texto.replace('\\', r'\\').replace('(', r'\(').replace(')', r'\)')
    return texto.encode('latin-1', 'replace').decode('latin-1')


def montar_boleto_fake(*, banco: str, valor, vencimento: date, nosso_numero: str,
                       carteira: str = '', pagador: str = '', contrato: str = '',
                       metodo: str = 'boleto', txid: str = '',
                       cobranca_id: str = '', ext_ref: str = '',
                       com_pdf: bool = True) -> dict:
    """
    Monta o resultado de emissão FAKE no mesmo formato que
    BoletoApiClient._normalizar_cobranca devolve (CobrancaOut normalizado),
    para os simuladores usarem o mesmo caminho de persistência da emissão real
    (Parcela.registrar_emissao + campos do boleto) sem tocar rede.
    """
    codigo_barras = gerar_codigo_barras_fake(
        banco, valor, vencimento, nosso_numero=nosso_numero, carteira=carteira)
    linha = gerar_linha_digitavel(codigo_barras)
    pix = ''
    if metodo in ('bolepix', 'pix', 'pix_automatico'):
        pix = gerar_pix_copia_cola_fake(
            chave=f'fake-{banco}@teste.gestaocontrato.com.br',
            nome=pagador or 'GESTAO CONTRATO TESTE',
            cidade='SETE LAGOAS',
            valor=valor,
            txid=txid,
        )
    pdf = b''
    if com_pdf:
        pdf = gerar_pdf_boleto_fake(
            'BOLETO FAKE — DADOS DE TESTE (sem registro no banco)',
            [
                f'Contrato: {contrato}   Pagador: {pagador}',
                f'Banco: {banco}   Vencimento: {vencimento:%d/%m/%Y}   Valor: R$ {Decimal(str(valor)):.2f}',
                f'Nosso numero: {nosso_numero}',
                f'Linha digitavel: {linha}',
                f'Codigo de barras: {codigo_barras}',
            ] + ([f'Pix copia-e-cola: {pix[:70]}...'] if pix else []),
        )
    return {
        'sucesso': True,
        'cobranca_id': cobranca_id,
        'status': 'registrado',
        'nosso_numero': nosso_numero,
        'nosso_numero_formatado': nosso_numero,
        'nosso_numero_dv': '',
        'linha_digitavel': linha,
        'codigo_barras': codigo_barras,
        'pix_copia_cola': pix,
        'pix_qrcode': '',
        'valor': Decimal(str(valor)),
        'ext_ref': ext_ref,
        'pdf_content': pdf or None,
        'raw': {'fake': True},
    }
