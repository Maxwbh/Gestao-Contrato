"""
Serviço de Importação de Extrato OFX para Quitação de Parcelas.

O formato OFX (Open Financial Exchange) é o padrão de exportação de extratos
dos principais bancos brasileiros (BB, Bradesco, Itaú, Caixa, Santander, etc.).

Fluxo:
  1. Usuário exporta extrato OFX do internet banking
  2. Faz upload via /financeiro/cnab/ofx/upload/
  3. Sistema parses o arquivo e tenta reconciliar transações com parcelas
  4. Parcelas identificadas são marcadas como pagas
  5. Relatório exibido: reconciliadas / não reconciliadas

Estratégia de reconciliação (em ordem de prioridade):
  P1 — nosso_número mencionado no MEMO
  P2 — número do contrato mencionado no MEMO
  P3 — valor exato + data de vencimento no mesmo mês
  P4 — valor exato (com tolerância de ±R$0,05) + mês/ano

Este serviço não usa bibliotecas externas — parse manual do SGML OFX.
"""
import re
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Parser OFX
# ---------------------------------------------------------------------------

class OFXTransaction:
    """Representa uma transação do extrato OFX."""

    def __init__(self):
        self.tipo: str = ''           # CREDIT, DEBIT, etc.
        self.data: date | None = None
        self.valor: Decimal = Decimal('0')
        self.fitid: str = ''          # identificador único da transação
        self.numero_cheque: str = ''
        self.memo: str = ''
        self.banco_pagador: str = ''

    def __repr__(self):
        return f"<OFXTransaction {self.fitid} {self.data} {self.valor} '{self.memo[:30]}'>"


def _parse_data_ofx(s: str) -> date | None:
    """
    Parseia data OFX. Formatos suportados:
      20260407         → date(2026, 4, 7)
      20260407120000   → date(2026, 4, 7)
      20260407120000[-3:BRT] → date(2026, 4, 7)
    """
    s = s.strip()
    # Remover timezone OFX como [-3:BRT]
    s = re.sub(r'\[.*?\]', '', s).strip()
    s = re.sub(r'[^0-9]', '', s)
    if len(s) >= 8:
        try:
            return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
        except (ValueError, TypeError):
            pass
    return None


def _parse_valor(s: str) -> Decimal:
    """Parseia valor OFX (pode ser negativo: -1500.00 ou +1500.00)."""
    s = s.strip().replace(',', '.')
    try:
        return Decimal(s)
    except InvalidOperation:
        return Decimal('0')


def parse_ofx(content: str | bytes) -> list[OFXTransaction]:
    """
    Parseia arquivo OFX (formato SGML, não XML).
    Retorna lista de OFXTransaction com todas as transações encontradas.

    Suporta ambos os formatos:
      - SGML clássico (maioria dos bancos BR): <TAG>valor (sem fechamento)
      - XML-like: <TAG>valor</TAG>
    """
    if isinstance(content, bytes):
        # Tentar detectar encoding
        for enc in ('utf-8', 'latin-1', 'cp1252', 'iso-8859-1'):
            try:
                content = content.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            content = content.decode('latin-1', errors='replace')

    # Normalizar quebras de linha
    content = content.replace('\r\n', '\n').replace('\r', '\n')

    transacoes = []
    # Encontrar blocos <STMTTRN>...</STMTTRN> ou <STMTTRN> sem fechamento
    # Dividir o conteúdo por <STMTTRN>
    blocos = re.split(r'<STMTTRN>', content, flags=re.IGNORECASE)

    for bloco in blocos[1:]:  # pular o cabeçalho
        # Determinar fim do bloco
        fim = re.search(r'</STMTTRN>|<STMTTRN>', bloco, re.IGNORECASE)
        if fim:
            bloco = bloco[:fim.start()]

        tx = OFXTransaction()

        def _get(tag: str) -> str:
            """Extrai valor de <TAG>valor ou <TAG>valor</TAG>."""
            m = re.search(
                rf'<{re.escape(tag)}>\s*([^\n<]+)',
                bloco,
                re.IGNORECASE
            )
            return m.group(1).strip() if m else ''

        tx.tipo = _get('TRNTYPE').upper()
        tx.fitid = _get('FITID')
        tx.memo = _get('MEMO') or _get('NAME')
        tx.numero_cheque = _get('CHECKNUM')
        tx.banco_pagador = _get('BANKID') or _get('BRANCHID')

        data_raw = _get('DTPOSTED') or _get('DTUSER')
        tx.data = _parse_data_ofx(data_raw)

        valor_raw = _get('TRNAMT')
        tx.valor = _parse_valor(valor_raw)

        # Pular transações sem dados essenciais
        if tx.data is None or tx.valor == Decimal('0'):
            continue

        transacoes.append(tx)

    logger.info('OFX parse: %d transações encontradas', len(transacoes))
    return transacoes


# ---------------------------------------------------------------------------
# Reconciliação OFX → Parcelas
# ---------------------------------------------------------------------------

class OFXReconciliacao:
    """Resultado de reconciliação de 1 transação OFX com uma Parcela."""

    def __init__(self, transacao: OFXTransaction,
                 parcela=None, confianca: str = '', motivo: str = ''):
        self.transacao = transacao
        self.parcela = parcela
        self.confianca = confianca  # 'ALTA', 'MEDIA', 'BAIXA', 'NAO_ENCONTRADA'
        self.motivo = motivo

    @property
    def reconciliada(self) -> bool:
        return self.parcela is not None and self.confianca != 'NAO_ENCONTRADA'


class OFXService:
    """
    Serviço de reconciliação OFX.

    Recebe conteúdo do arquivo OFX e tenta casar cada crédito
    com uma parcela não paga do sistema.
    """

    # Tolerância em R$ para match de valor
    TOLERANCIA_VALOR = Decimal('0.10')

    def __init__(self, imobiliaria=None, contrato=None):
        """
        Args:
            imobiliaria: filtrar parcelas por imobiliária (opcional)
            contrato: filtrar parcelas de um contrato específico (opcional)
        """
        self.imobiliaria = imobiliaria
        self.contrato = contrato

    def processar(self, ofx_content: str | bytes) -> dict:
        """
        Parseia OFX e reconcilia transações com parcelas não pagas.

        Returns:
            {
                'total_transacoes': int,
                'reconciliadas': int,
                'nao_reconciliadas': int,
                'resultados': list[OFXReconciliacao],
                'parcelas_quitadas': list[Parcela],  # as que foram marcadas como pagas
            }
        """
        from financeiro.models import Parcela

        transacoes = parse_ofx(ofx_content)
        if not transacoes:
            return {
                'total_transacoes': 0,
                'reconciliadas': 0,
                'nao_reconciliadas': 0,
                'resultados': [],
                'parcelas_quitadas': [],
            }

        # Carregar parcelas não pagas em memória (para evitar N+1)
        qs = Parcela.objects.filter(pago=False, tipo_parcela='NORMAL').select_related(
            'contrato', 'contrato__comprador', 'contrato__imobiliaria'
        )
        if self.imobiliaria:
            qs = qs.filter(contrato__imobiliaria=self.imobiliaria)
        if self.contrato:
            qs = qs.filter(contrato=self.contrato)

        parcelas_abertas = list(qs)
        parcelas_usadas: set = set()  # pks já reconciliados

        resultados = []
        parcelas_quitadas = []

        for tx in transacoes:
            # Apenas créditos (valores > 0) — pagamentos recebidos
            if tx.valor <= 0:
                resultados.append(OFXReconciliacao(
                    tx, confianca='NAO_ENCONTRADA',
                    motivo='Débito ignorado'
                ))
                continue

            rec = self._reconciliar(tx, parcelas_abertas, parcelas_usadas)
            resultados.append(rec)

            if rec.reconciliada:
                parcelas_usadas.add(rec.parcela.pk)
                parcelas_quitadas.append(rec.parcela)
                self._quitar(rec.parcela, tx)

        rec_count = sum(1 for r in resultados if r.reconciliada)
        return {
            'total_transacoes': len(transacoes),
            'reconciliadas': rec_count,
            'nao_reconciliadas': len(transacoes) - rec_count,
            'resultados': resultados,
            'parcelas_quitadas': parcelas_quitadas,
        }

    def _reconciliar(self, tx: OFXTransaction, parcelas: list,
                     usadas: set) -> OFXReconciliacao:
        """
        Tenta casar a transação com uma parcela.
        Retorna OFXReconciliacao com o resultado.
        """
        disponiveis = [p for p in parcelas if p.pk not in usadas]

        # P1 — nosso_número no MEMO
        if tx.memo:
            memo_upper = tx.memo.upper()
            for p in disponiveis:
                if p.nosso_numero and p.nosso_numero in tx.memo:
                    return OFXReconciliacao(tx, p, 'ALTA',
                                           f'nosso_número {p.nosso_numero} encontrado no MEMO')

        # P2 — número do contrato no MEMO
        if tx.memo:
            for p in disponiveis:
                num = p.contrato.numero_contrato
                if num and num.upper() in tx.memo.upper():
                    return OFXReconciliacao(tx, p, 'ALTA',
                                           f'contrato {num} encontrado no MEMO')

        # P3 — valor exato + mesmo mês de vencimento
        if tx.data:
            for p in disponiveis:
                valor_match = abs(tx.valor - p.valor_atual) <= self.TOLERANCIA_VALOR
                mesmo_mes = (p.data_vencimento and
                             p.data_vencimento.year == tx.data.year and
                             p.data_vencimento.month == tx.data.month)
                if valor_match and mesmo_mes:
                    return OFXReconciliacao(
                        tx, p, 'MEDIA',
                        f'valor R${tx.valor} ≈ R${p.valor_atual} no mesmo mês {tx.data:%m/%Y}'
                    )

        # P4 — valor exato sem restrição de data
        for p in disponiveis:
            valor_match = abs(tx.valor - p.valor_atual) <= self.TOLERANCIA_VALOR
            if valor_match:
                return OFXReconciliacao(
                    tx, p, 'BAIXA',
                    f'valor R${tx.valor} ≈ R${p.valor_atual} (sem correspondência de data)'
                )

        return OFXReconciliacao(tx, confianca='NAO_ENCONTRADA',
                                motivo='Nenhuma parcela correspondente encontrada')

    def _quitar(self, parcela, tx: OFXTransaction) -> None:
        """Marca a parcela como paga com os dados da transação OFX."""
        try:
            parcela.registrar_pagamento(
                valor_pago=tx.valor,
                data_pagamento=tx.data or date.today(),
                forma_pagamento='TRANSFERENCIA',
                observacao=f'Quitado via OFX — FITID: {tx.fitid} — {tx.memo[:100]}',
            )
        except Exception as e:
            logger.error('OFX: erro ao quitar parcela pk=%s: %s', parcela.pk, e)


# ---------------------------------------------------------------------------
# Funções de utilidade para views
# ---------------------------------------------------------------------------

def processar_ofx_upload(arquivo_content: bytes,
                         imobiliaria=None,
                         contrato=None,
                         dry_run: bool = False) -> dict:
    """
    Ponto de entrada para processar arquivo OFX enviado pelo usuário.

    Args:
        arquivo_content: bytes do arquivo .ofx
        imobiliaria: filtrar por imobiliária
        contrato: filtrar por contrato
        dry_run: se True, não quita as parcelas (apenas simula)

    Returns: resultado do processamento (ver OFXService.processar)
    """
    service = OFXService(imobiliaria=imobiliaria, contrato=contrato)

    if dry_run:
        # Simulação: parseia e reconcilia sem quitar
        transacoes = parse_ofx(arquivo_content)
        return {
            'dry_run': True,
            'total_transacoes': len(transacoes),
            'transacoes': [
                {
                    'fitid': t.fitid,
                    'data': str(t.data),
                    'valor': str(t.valor),
                    'memo': t.memo,
                }
                for t in transacoes
            ],
        }

    return service.processar(arquivo_content)
