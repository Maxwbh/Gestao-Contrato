"""
Serviço de Importação de Extrato OFX para Quitação de Parcelas.

O formato OFX (Open Financial Exchange) é o padrão de exportação de extratos
dos principais bancos brasileiros (BB, Bradesco, Itaú, Caixa, Santander, etc.).

Fluxo:
  1. Usuário exporta extrato OFX do internet banking
  2. Faz upload via /financeiro/cnab/ofx/upload/
  3. Sistema parseia o arquivo via BRCobrança e reconcilia transações com parcelas
  4. Parcelas identificadas são marcadas como pagas
  5. Relatório exibido: reconciliadas / não reconciliadas

Estratégia de reconciliação (em ordem de prioridade):
  P1a — nosso_número extraído via BRCobrança (bank-specific) na parcela
  P1b — nosso_número da parcela encontrado no MEMO (regex simples)
  P2  — número do contrato mencionado no MEMO
  P3  — valor ±R$0,10 + data de vencimento no mesmo mês
  P4  — valor ±R$0,10 sem restrição de data

Parse:
  POST /api/ofx/parse no boleto_cnab_api (gem Ruby `ofx`, OFX v1/v2, bank-specific)
  Se a API estiver indisponível, RuntimeError é levantado.
"""
import io
import logging
from datetime import date
from decimal import Decimal, InvalidOperation

import requests

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OFXTransaction
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
        # Preenchido quando o parse é feito via BRCobrança (extração bank-specific)
        self.nosso_numero_extraido: str | None = None

    def __repr__(self):
        return f"<OFXTransaction {self.fitid} {self.data} {self.valor} '{self.memo[:30]}'>"


# ---------------------------------------------------------------------------
# Parse via BRCobrança API (primário — usa gem Ruby `ofx`)
# ---------------------------------------------------------------------------

def _parse_via_brcobranca(content: bytes, brcobranca_url: str) -> list[OFXTransaction] | None:
    """
    Parseia arquivo OFX usando POST /api/ofx/parse no boleto_cnab_api.

    Vantagens vs parser Python:
    - Suporte completo a OFX v1 (SGML) e v2 (XML)
    - Detecção de encoding robusta (UTF-8 e Latin-1)
    - `nosso_numero_extraido`: extração bank-specific por banco (Sicoob, Itaú, BB...)

    Retorna lista de OFXTransaction (com nosso_numero_extraido preenchido) ou
    None em caso de falha (timeout, API indisponível, resposta inválida).
    """
    url = f'{brcobranca_url}/api/ofx/parse'
    try:
        resp = requests.post(
            url,
            files={'file': ('extrato.ofx', io.BytesIO(content), 'application/octet-stream')},
            data={'somente_creditos': 'false'},
            timeout=15,
        )
    except requests.exceptions.ConnectionError:
        logger.warning(
            'OFX BRCobrança: serviço indisponível em %s — verifique o container/serviço',
            brcobranca_url
        )
        return None
    except requests.exceptions.Timeout:
        logger.warning('OFX BRCobrança: timeout em %s', brcobranca_url)
        return None
    except Exception as e:
        logger.warning('OFX BRCobrança: erro inesperado — %s', e)
        return None

    if resp.status_code != 200:
        logger.warning('OFX BRCobrança: status %s — resposta: %s', resp.status_code, resp.text[:200])
        return None

    try:
        dados = resp.json()
    except Exception:
        logger.warning('OFX BRCobrança: resposta não é JSON — %s', resp.text[:200])
        return None

    transacoes_raw = dados.get('transacoes') or []
    transacoes: list[OFXTransaction] = []
    for item in transacoes_raw:
        tx = OFXTransaction()
        tx.fitid = str(item.get('fitid') or '')
        tx.tipo = str(item.get('tipo') or '').upper()
        tx.memo = str(item.get('memo') or item.get('name') or '')
        tx.numero_cheque = str(item.get('checknum') or '')
        tx.nosso_numero_extraido = item.get('nosso_numero_extraido') or None

        data_str = item.get('data') or ''
        if data_str:
            try:
                parts = data_str.split('-')
                tx.data = date(int(parts[0]), int(parts[1]), int(parts[2]))
            except (ValueError, IndexError):
                pass

        valor_raw = item.get('valor')
        try:
            tx.valor = Decimal(str(valor_raw)) if valor_raw is not None else Decimal('0')
        except InvalidOperation:
            tx.valor = Decimal('0')

        # Débitos ficam negativos internamente (BRCobrança retorna valor absoluto + tipo)
        if tx.tipo == 'DEBIT':
            tx.valor = -abs(tx.valor)

        if tx.valor == Decimal('0') and tx.data is None:
            continue  # pular transação sem dados essenciais

        transacoes.append(tx)

    logger.info('OFX BRCobrança: %d transações parseadas', len(transacoes))
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

    Parse: POST /api/ofx/parse no boleto_cnab_api (obrigatório).
    Se a API estiver indisponível, RuntimeError é levantado.
    """

    # Tolerância em R$ para match de valor
    TOLERANCIA_VALOR = Decimal('0.10')

    def __init__(self, imobiliaria=None, contrato=None, brcobranca_url=None):
        """
        Args:
            imobiliaria: filtrar parcelas por imobiliária (opcional)
            contrato: filtrar parcelas de um contrato específico (opcional)
            brcobranca_url: URL da API BRCobrança (padrão: settings.BRCOBRANCA_URL)
        """
        from django.conf import settings
        self.imobiliaria = imobiliaria
        self.contrato = contrato
        self.brcobranca_url = brcobranca_url or getattr(
            settings, 'BRCOBRANCA_URL', 'http://localhost:9292'
        )

    def processar(self, ofx_content: str | bytes) -> dict:
        """
        Parseia OFX via BRCobrança e reconcilia transações com parcelas não pagas.
        Levanta RuntimeError se a API BRCobrança estiver indisponível.

        Returns:
            {
                'total_transacoes': int,
                'reconciliadas': int,
                'nao_reconciliadas': int,
                'resultados': list[OFXReconciliacao],
                'parcelas_quitadas': list[Parcela],
                'parser': 'brcobranca',
            }
        """
        from financeiro.models import Parcela

        # Garantir bytes para BRCobrança (multipart upload)
        content_bytes = (
            ofx_content if isinstance(ofx_content, bytes)
            else ofx_content.encode('utf-8')
        )

        transacoes = _parse_via_brcobranca(content_bytes, self.brcobranca_url)
        if transacoes is None:
            logger.error(
                "[OFX] API BRCobrança indisponível em %s\n"
                "  → Verifique se o container/serviço BRCobrança está rodando.",
                self.brcobranca_url,
            )
            raise RuntimeError(
                'Não foi possível processar o arquivo OFX: API BRCobrança indisponível. '
                'Verifique os logs do servidor.'
            )
        parser_usado = 'brcobranca'
        if not transacoes:
            return {
                'total_transacoes': 0,
                'reconciliadas': 0,
                'nao_reconciliadas': 0,
                'resultados': [],
                'parcelas_quitadas': [],
                'parser': parser_usado,
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
            'parser': parser_usado,
        }

    def _reconciliar(self, tx: OFXTransaction, parcelas: list,
                     usadas: set) -> OFXReconciliacao:
        """
        Tenta casar a transação com uma parcela.
        Retorna OFXReconciliacao com o resultado.
        """
        disponiveis = [p for p in parcelas if p.pk not in usadas]

        # P1a — nosso_número extraído via BRCobrança (bank-specific, mais preciso)
        if tx.nosso_numero_extraido:
            for p in disponiveis:
                if p.nosso_numero and p.nosso_numero == tx.nosso_numero_extraido:
                    return OFXReconciliacao(
                        tx, p, 'ALTA',
                        f'nosso_número {p.nosso_numero} extraído via BRCobrança'
                    )

        # P1b — nosso_número da parcela encontrado literalmente no MEMO
        if tx.memo:
            for p in disponiveis:
                if p.nosso_numero and p.nosso_numero in tx.memo:
                    return OFXReconciliacao(
                        tx, p, 'ALTA',
                        f'nosso_número {p.nosso_numero} encontrado no MEMO')

        # P2 — número do contrato no MEMO
        if tx.memo:
            for p in disponiveis:
                num = p.contrato.numero_contrato
                if num and num.upper() in tx.memo.upper():
                    return OFXReconciliacao(
                        tx, p, 'ALTA',
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
        """Marca a parcela como paga com os dados da transação OFX e cria HistoricoPagamento."""
        from financeiro.models import HistoricoPagamento

        # Deduplicação: não quitar se já existe histórico com mesmo FITID
        if tx.fitid and HistoricoPagamento.objects.filter(fitid_ofx=tx.fitid).exists():
            logger.warning('OFX: FITID %s já processado — parcela pk=%s ignorada', tx.fitid, parcela.pk)
            return

        try:
            data_pgto = tx.data or date.today()
            obs = f'Quitado via OFX — FITID: {tx.fitid} — {tx.memo[:100] if tx.memo else ""}'

            parcela.registrar_pagamento(
                valor_pago=tx.valor,
                data_pagamento=data_pgto,
                observacoes=obs,
            )

            # Criar registro de histórico com rastreamento de origem
            HistoricoPagamento.objects.create(
                parcela=parcela,
                data_pagamento=data_pgto,
                valor_pago=tx.valor,
                valor_parcela=parcela.valor_atual,
                valor_juros=parcela.valor_juros or 0,
                valor_multa=parcela.valor_multa or 0,
                forma_pagamento='TRANSFERENCIA',
                observacoes=obs,
                origem_pagamento='OFX',
                fitid_ofx=tx.fitid or '',
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
        from django.conf import settings
        brcobranca_url = getattr(settings, 'BRCOBRANCA_URL', 'http://localhost:9292')
        transacoes = _parse_via_brcobranca(arquivo_content, brcobranca_url)
        if transacoes is None:
            raise RuntimeError(
                'Não foi possível processar o arquivo OFX: API BRCobrança indisponível. '
                'Verifique os logs do servidor.'
            )
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
