"""
Gerenciador de Tarefas para Render Free Tier

Como o Celery não está disponível no plano gratuito do Render,
este módulo fornece alternativas para execução de tarefas agendadas:

1. Endpoints HTTP protegidos para execução manual
2. Suporte a cron jobs externos (cron-job.org, EasyCron, etc.)
3. Execução via Django management commands

Uso:
    # Via endpoint HTTP (protegido por token)
    curl -X POST https://seu-app.onrender.com/api/tasks/processar-reajustes/ \
         -H "X-Task-Token: seu-token-secreto"

    # Via management command
    python manage.py executar_tarefas --task=reajustes

    # Via cron externo (configurar no cron-job.org)
    POST https://seu-app.onrender.com/api/tasks/run-all/
    Header: X-Task-Token: seu-token-secreto
"""
import logging
from datetime import datetime, timedelta
from functools import wraps
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.db import transaction
from core.permissions import task_api_rate_limit
from core.parametros import get_param
from notificacoes.services import _destinatario_email_teste

logger = logging.getLogger(__name__)


def task_auth_required(view_func):
    """
    Decorator que verifica autenticação por token para endpoints de tarefas.
    O token é lido de ParametroSistema a cada chamada (sem cache de módulo).
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        task_token = get_param('TASK_TOKEN')
        if not task_token:
            logger.warning("TASK_TOKEN não configurado - tarefas desabilitadas")
            return JsonResponse({
                'status': 'error',
                'message': 'Tarefas não configuradas. Defina TASK_TOKEN em Parâmetros do Sistema.'
            }, status=503)

        token = request.headers.get('X-Task-Token') or request.GET.get('token')

        if not token:
            return JsonResponse({
                'status': 'error',
                'message': 'Token de autenticação não fornecido'
            }, status=401)

        if token != task_token:
            logger.warning(f"Tentativa de acesso com token inválido: {request.META.get('REMOTE_ADDR')}")
            return JsonResponse({
                'status': 'error',
                'message': 'Token inválido'
            }, status=403)

        return view_func(request, *args, **kwargs)
    wrapper.csrf_exempt = True
    return wrapper


class TaskResult:
    """Classe para padronizar resultados de tarefas."""

    def __init__(self, task_name: str):
        self.task_name = task_name
        self.started_at = datetime.now()
        self.finished_at = None
        self.success = False
        self.items_processed = 0
        self.errors = []
        self.messages = []

    def add_message(self, message: str):
        self.messages.append(message)
        logger.info(f"[{self.task_name}] {message}")

    def add_error(self, error: str):
        self.errors.append(error)
        logger.exception(f"[{self.task_name}] {error}")

    def finish(self, success: bool = True):
        self.finished_at = datetime.now()
        self.success = success and len(self.errors) == 0

    def to_dict(self) -> dict:
        return {
            'task': self.task_name,
            'success': self.success,
            'started_at': self.started_at.isoformat(),
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'duration_seconds': (self.finished_at - self.started_at).total_seconds() if self.finished_at else None,
            'items_processed': self.items_processed,
            'messages': self.messages,
            'errors': self.errors,
        }


def processar_reajustes_sync():
    """
    Processa reajustes pendentes de forma síncrona.
    Alternativa à task Celery para o Free tier.
    """
    from contratos.models import Contrato, StatusContrato
    from financeiro.models import Reajuste
    from contratos.services import IndiceEconomicoService, ReajusteService
    from decimal import Decimal
    from datetime import date

    result = TaskResult('processar_reajustes')

    try:
        hoje = date.today()

        # Buscar contratos ativos que usam índice econômico para reajuste
        contratos = Contrato.objects.filter(
            status=StatusContrato.ATIVO,
            tipo_correcao__in=['IPCA', 'IGPM', 'INCC', 'IGPDI', 'INPC', 'TR', 'SELIC']
        ).select_related('imobiliaria', 'comprador')

        result.add_message(f"Verificando {contratos.count()} contratos ativos")

        for contrato in contratos:
            try:
                # Verificar se há ciclo pendente de reajuste
                ciclo = Reajuste.calcular_ciclo_pendente(contrato)
                if not ciclo:
                    continue

                # Buscar índice atual para o tipo de correção do contrato
                indice = IndiceEconomicoService.get_indice_atual(contrato.tipo_correcao)

                if indice:
                    # Aplicar reajuste às parcelas pendentes
                    parcelas_pendentes = list(contrato.parcelas.filter(
                        pago=False,
                        data_vencimento__gte=hoje
                    ))

                    with transaction.atomic():
                        for parcela in parcelas_pendentes:
                            percentual = Decimal(str(indice.get('valor', 0)))
                            novo_valor = ReajusteService.calcular_reajuste(
                                parcela.valor_atual, percentual
                            )
                            parcela.valor_atual = novo_valor
                            parcela.save(update_fields=['valor_atual', 'atualizado_em'])
                            result.items_processed += 1

                    result.add_message(
                        f"Contrato {contrato.numero_contrato}: {len(parcelas_pendentes)} parcelas reajustadas"
                    )

            except Exception as e:
                logger.exception("Erro no contrato %s: %s", contrato.numero_contrato, e)
                result.add_error(f"Erro no contrato {contrato.numero_contrato}: {str(e)}")

        result.finish()

    except Exception as e:
        logger.exception("Erro geral em processar_reajustes: %s", e)
        result.add_error(f"Erro geral: {str(e)}")
        result.finish(success=False)

    return result


def _notificacao_ja_enviada_hoje(parcela, motivo_prefixo):
    """
    Verifica se já existe Notificacao registrada para esta parcela hoje.
    Evita duplicatas quando a task roda múltiplas vezes no mesmo dia.
    """
    from notificacoes.models import Notificacao, StatusNotificacao
    from datetime import date
    return Notificacao.objects.filter(
        parcela=parcela,
        assunto__startswith=motivo_prefixo,
        status__in=[StatusNotificacao.PENDENTE, StatusNotificacao.ENVIADA],
        data_agendamento__date=date.today(),
    ).exists()


def _notificacao_ja_enviada(parcela, motivo_prefixo):
    """
    Verifica se já existe Notificacao registrada para esta parcela em qualquer data.
    Usado por N-02 fallback: como disparamos uma única vez (data exata D+N),
    esta verificação garante que mesmo em caso de re-execução ou bug na query
    a parcela não receba a mesma notificação duas vezes.
    """
    from notificacoes.models import Notificacao, StatusNotificacao
    return Notificacao.objects.filter(
        parcela=parcela,
        assunto__startswith=motivo_prefixo,
        status__in=[StatusNotificacao.PENDENTE, StatusNotificacao.ENVIADA],
    ).exists()


def _registrar_notificacao(parcela, tipo, destinatario, assunto, mensagem):
    """Cria registro Notificacao e retorna o objeto criado."""
    from notificacoes.models import Notificacao, StatusNotificacao
    return Notificacao.objects.create(
        parcela=parcela,
        tipo=tipo,
        destinatario=destinatario,
        assunto=assunto,
        mensagem=mensagem,
        status=StatusNotificacao.PENDENTE,
    )


def _html_email(titulo, cor_header, icone, subtitulo, linhas_info, rodape_nome,
                rodape_tel='', rodape_email='', aviso='', cor_aviso='#e67e22'):
    """
    Gera HTML transacional responsivo para e-mails de notificação.
    Usa table-layout para máxima compatibilidade com clientes de e-mail.
    """
    linhas_html = ''.join(
        f'<tr>'
        f'<td style="padding:8px 0;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;">'
        f'<strong>{label}</strong></td>'
        f'<td style="padding:8px 0;color:#222;font-size:14px;border-bottom:1px solid #f0f0f0;'
        f'text-align:right;">{valor}</td>'
        f'</tr>'
        for label, valor in linhas_info
    )
    aviso_html = (
        f'<div style="background:{cor_aviso};color:#fff;padding:12px 16px;'
        f'border-radius:6px;margin:20px 0;font-size:13px;">'
        f'{aviso}</div>'
    ) if aviso else ''

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f8;padding:30px 0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0"
           style="max-width:600px;width:100%;background:#ffffff;border-radius:8px;
                  overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">

      <!-- CABEÇALHO -->
      <tr>
        <td style="background:{cor_header};padding:28px 32px;text-align:center;">
          <div style="font-size:32px;margin-bottom:8px;">{icone}</div>
          <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:700;">{titulo}</h1>
          <p style="margin:6px 0 0;color:rgba(255,255,255,.85);font-size:14px;">{subtitulo}</p>
        </td>
      </tr>

      <!-- CORPO -->
      <tr>
        <td style="padding:28px 32px;">
          <table width="100%" cellpadding="0" cellspacing="0"
                 style="border:1px solid #e8eaed;border-radius:6px;overflow:hidden;">
            <tr>
              <td style="background:#f8f9fa;padding:12px 16px;" colspan="2">
                <span style="font-size:12px;font-weight:700;color:#888;text-transform:uppercase;
                             letter-spacing:.5px;">Detalhes</span>
              </td>
            </tr>
            {linhas_html}
          </table>
          {aviso_html}
        </td>
      </tr>

      <!-- RODAPÉ -->
      <tr>
        <td style="background:#f8f9fa;padding:16px 32px;text-align:center;
                   border-top:1px solid #e8eaed;">
          <p style="margin:0;font-size:13px;font-weight:700;color:#444;">{rodape_nome}</p>
          <p style="margin:4px 0 0;font-size:12px;color:#888;">
            {f'{rodape_tel} &nbsp;|&nbsp; ' if rodape_tel else ''}{rodape_email}
          </p>
          <p style="margin:8px 0 0;font-size:11px;color:#bbb;">
            Você recebe este e-mail por ter uma parcela em aberto.
          </p>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""


def _get_destinatario(comprador, tipo_notificacao):
    """
    Retorna o endereço de destino para o canal informado, ou None se indisponível.
    Respeita os flags notificar_email / notificar_whatsapp do comprador.
    """
    from notificacoes.models import TipoNotificacao
    if tipo_notificacao == TipoNotificacao.EMAIL:
        return comprador.email if (getattr(comprador, 'notificar_email', True) and comprador.email) else None
    if tipo_notificacao == TipoNotificacao.SMS:
        if not getattr(comprador, 'notificar_sms', False):
            return None
        tel = getattr(comprador, 'celular', None) or getattr(comprador, 'telefone', None)
        return tel or None
    if tipo_notificacao == TipoNotificacao.WHATSAPP:
        if not getattr(comprador, 'notificar_whatsapp', False):
            return None
        tel = getattr(comprador, 'celular', None) or getattr(comprador, 'telefone', None)
        return f"whatsapp:{tel}" if tel else None
    return None


def _enviar_pelo_canal(tipo_notificacao, destinatario, assunto, mensagem):
    """Despacha a mensagem pelo canal correto e propaga exceções."""
    from notificacoes.models import TipoNotificacao
    from notificacoes.services import ServicoEmail, ServicoSMS, ServicoWhatsApp
    if tipo_notificacao == TipoNotificacao.EMAIL:
        ServicoEmail.enviar(destinatario=destinatario, assunto=assunto, mensagem=mensagem)
    elif tipo_notificacao == TipoNotificacao.SMS:
        ServicoSMS.enviar(destinatario=destinatario, mensagem=mensagem)
    elif tipo_notificacao == TipoNotificacao.WHATSAPP:
        ServicoWhatsApp.enviar(destinatario=destinatario, mensagem=mensagem)


def _processar_regra(regra, result):
    """
    N-03: Executa uma RegrarNotificacao: encontra as parcelas na data-alvo e envia.
    """
    from financeiro.models import Parcela
    from notificacoes.models import TipoGatilho
    from datetime import date, timedelta

    hoje = date.today()
    PREFIXO = f'[REGRA-{regra.id}]'

    if regra.tipo_gatilho == TipoGatilho.ANTES_VENCIMENTO:
        data_alvo = hoje + timedelta(days=regra.dias_offset)
        label = f"D-{regra.dias_offset}"
        parcelas = Parcela.objects.filter(
            pago=False, tipo_parcela='NORMAL', data_vencimento=data_alvo,
        ).select_related('contrato', 'contrato__comprador', 'contrato__imobiliaria')
    else:  # APOS_VENCIMENTO
        data_alvo = hoje - timedelta(days=regra.dias_offset)
        label = f"D+{regra.dias_offset}"
        parcelas = Parcela.objects.filter(
            pago=False, tipo_parcela='NORMAL', data_vencimento=data_alvo,
        ).select_related('contrato', 'contrato__comprador', 'contrato__imobiliaria')

    result.add_message(
        f"Regra '{regra.nome}' ({label}): {parcelas.count()} parcelas em {data_alvo}"
    )

    for parcela in parcelas:
        try:
            comprador = parcela.contrato.comprador
            destinatario = _get_destinatario(comprador, regra.tipo_notificacao)
            if not destinatario:
                continue

            if _notificacao_ja_enviada_hoje(parcela, PREFIXO):
                continue

            imob_nome = getattr(parcela.contrato.imobiliaria, 'nome', 'Gestão de Contratos')
            if regra.tipo_gatilho == TipoGatilho.ANTES_VENCIMENTO:
                dias_para_vencer = regra.dias_offset
                assunto = (
                    f"{PREFIXO} Parcela {parcela.numero_parcela} vence em "
                    f"{dias_para_vencer} dia(s) — {data_alvo.strftime('%d/%m/%Y')}"
                )
                mensagem = (
                    f"Olá {comprador.nome},\n\n"
                    f"Lembramos que a parcela {parcela.numero_parcela}/{parcela.contrato.numero_parcelas} "
                    f"do contrato {parcela.contrato.numero_contrato} vence em "
                    f"{data_alvo.strftime('%d/%m/%Y')}.\n\n"
                    f"Valor: R$ {parcela.valor_atual:,.2f}\n\n"
                    f"Por favor, efetue o pagamento até a data de vencimento.\n\n"
                    f"Atenciosamente,\n{imob_nome}"
                )
            else:
                dias_atraso = regra.dias_offset
                assunto = (
                    f"{PREFIXO} Parcela {parcela.numero_parcela} em atraso há "
                    f"{dias_atraso} dia(s) — {data_alvo.strftime('%d/%m/%Y')}"
                )
                mensagem = (
                    f"Olá {comprador.nome},\n\n"
                    f"A parcela {parcela.numero_parcela}/{parcela.contrato.numero_parcelas} "
                    f"do contrato {parcela.contrato.numero_contrato} encontra-se em atraso.\n\n"
                    f"Vencimento: {data_alvo.strftime('%d/%m/%Y')} ({dias_atraso} dia(s) em atraso)\n"
                    f"Valor original: R$ {parcela.valor_atual:,.2f}\n\n"
                    f"Por favor, regularize sua situação para evitar acréscimo de juros e multa.\n\n"
                    f"Atenciosamente,\n{imob_nome}"
                )

            # Se o template customizado estiver configurado, renderizar
            if regra.template:
                ctx = {
                    'NOMECOMPRADOR': comprador.nome,
                    'NUMEROPARCELA': parcela.numero_parcela,
                    'TOTALPARCELAS': parcela.contrato.numero_parcelas,
                    'VALORPARCELA': f"R$ {parcela.valor_atual:,.2f}",
                    'DATAVENCIMENTO': data_alvo.strftime('%d/%m/%Y'),
                    'NUMEROCONTRATO': parcela.contrato.numero_contrato,
                    'NOMEIMOBILIARIA': imob_nome,
                }
                subj_r, body_r, _ = regra.template.renderizar(ctx)
                if subj_r:
                    assunto = f"{PREFIXO} {subj_r}"
                if body_r:
                    mensagem = body_r

            notif = _registrar_notificacao(
                parcela, regra.tipo_notificacao, destinatario, assunto, mensagem
            )
            try:
                _enviar_pelo_canal(regra.tipo_notificacao, destinatario, assunto, mensagem)
                notif.marcar_como_enviada()
                result.items_processed += 1
                result.add_message(
                    f"  ✓ {regra.get_tipo_notificacao_display()} → {destinatario} (parcela {parcela.id})"
                )
            except Exception as e_send:
                notif.marcar_erro(str(e_send))
                result.add_error(f"Erro ao enviar regra {regra.id} parcela {parcela.id}: {e_send}")

        except Exception as e:
            logger.exception("Erro ao processar regra %s parcela %s: %s", regra.id, parcela.id, e)
            result.add_error(f"Erro parcela {parcela.id}: {str(e)}")


def enviar_notificacoes_sync():
    """
    N-01/N-03: Envia notificações de vencimento de forma síncrona.
    Se existirem RegraNotificacao ativas do tipo ANTES, usa a régua configurável.
    Caso contrário, usa o comportamento padrão (D-5 via settings).
    """
    from financeiro.models import Parcela
    from notificacoes.models import TipoNotificacao, RegraNotificacao, TipoGatilho
    from notificacoes.services import ServicoEmail
    from datetime import date, timedelta

    result = TaskResult('enviar_notificacoes_vencimento')

    try:
        regras = list(RegraNotificacao.objects.filter(
            ativo=True, tipo_gatilho=TipoGatilho.ANTES_VENCIMENTO
        ))

        if regras:
            # N-03: régua configurável
            result.add_message(f"N-03: {len(regras)} regra(s) ANTES ativa(s)")
            for regra in regras:
                _processar_regra(regra, result)
        else:
            # Fallback N-01: exatamente D-N (data exata, como N-03 faz)
            # Usando data exata evita: (a) envio no dia do vencimento ("0 dias"),
            # (b) envio repetido todos os dias enquanto parcela estiver na janela.
            PREFIXO = '[VENCIMENTO]'
            dias_antecedencia = getattr(settings, 'NOTIFICACAO_DIAS_ANTECEDENCIA', 5)
            hoje = date.today()
            data_alvo = hoje + timedelta(days=dias_antecedencia)

            parcelas = Parcela.objects.filter(
                pago=False,
                tipo_parcela='NORMAL',
                data_vencimento=data_alvo,
            ).select_related('contrato', 'contrato__comprador', 'contrato__imobiliaria')

            result.add_message(
                f"N-01 (padrão): {parcelas.count()} parcelas vencendo em "
                f"{dias_antecedencia} dia(s) ({data_alvo.strftime('%d/%m/%Y')})"
            )

            for parcela in parcelas:
                try:
                    comprador = parcela.contrato.comprador
                    if not (getattr(comprador, 'notificar_email', True) and comprador.email):
                        continue
                    if _notificacao_ja_enviada_hoje(parcela, PREFIXO):
                        continue

                    assunto = (
                        f"{PREFIXO} Parcela {parcela.numero_parcela} vence em "
                        f"{dias_antecedencia} dia(s) — {parcela.data_vencimento.strftime('%d/%m/%Y')}"
                    )
                    imob = parcela.contrato.imobiliaria
                    imob_nome = getattr(imob, 'nome', 'Gestão de Contratos')
                    mensagem = (
                        f"Olá {comprador.nome},\n\n"
                        f"Lembramos que a parcela {parcela.numero_parcela}/{parcela.contrato.numero_parcelas} "
                        f"do contrato {parcela.contrato.numero_contrato} vence em "
                        f"{parcela.data_vencimento.strftime('%d/%m/%Y')}.\n\n"
                        f"Valor: R$ {parcela.valor_atual:,.2f}\n\n"
                        f"Por favor, efetue o pagamento até a data de vencimento.\n\n"
                        f"Atenciosamente,\n{imob_nome}"
                    )
                    html_msg = _html_email(
                        titulo='Lembrete de Vencimento',
                        cor_header='#2980b9',
                        icone='📅',
                        subtitulo=f'Olá, {comprador.nome}! Sua parcela vence em breve.',
                        linhas_info=[
                            ('Contrato', parcela.contrato.numero_contrato),
                            ('Parcela', f'{parcela.numero_parcela}/{parcela.contrato.numero_parcelas}'),
                            ('Vencimento', parcela.data_vencimento.strftime('%d/%m/%Y')),
                            ('Valor', f'R$ {parcela.valor_atual:,.2f}'),
                            ('Dias restantes', f'{dias_antecedencia} dia(s)'),
                        ],
                        rodape_nome=imob_nome,
                        rodape_tel=getattr(imob, 'telefone', ''),
                        rodape_email=getattr(imob, 'email', ''),
                        aviso='Efetue o pagamento até a data de vencimento para evitar juros e multa.',
                        cor_aviso='#2980b9',
                    )

                    notif = _registrar_notificacao(
                        parcela, TipoNotificacao.EMAIL, comprador.email, assunto, mensagem
                    )
                    try:
                        ServicoEmail.enviar(
                            destinatario=comprador.email, assunto=assunto,
                            mensagem=mensagem, html_message=html_msg,
                        )
                        notif.marcar_como_enviada()
                        result.items_processed += 1
                        result.add_message(f"Vencimento enviado → {comprador.email} (parcela {parcela.id})")
                    except Exception as e_send:
                        notif.marcar_erro(str(e_send))
                        result.add_error(f"Erro ao enviar vencimento parcela {parcela.id}: {e_send}")

                except Exception as e:
                    logger.exception("Erro ao processar parcela %s: %s", parcela.id, e)
                    result.add_error(f"Erro parcela {parcela.id}: {str(e)}")

        result.finish()

    except Exception as e:
        logger.exception("Erro geral em enviar_notificacoes_sync: %s", e)
        result.add_error(f"Erro geral: {str(e)}")
        result.finish(success=False)

    return result


def enviar_inadimplentes_sync():
    """
    N-02/N-03: Envia notificações de inadimplência de forma síncrona.
    Se existirem RegraNotificacao ativas do tipo APOS, usa a régua configurável.
    Caso contrário, usa o comportamento padrão (>= D+3 via settings).
    """
    from financeiro.models import Parcela
    from notificacoes.models import TipoNotificacao, RegraNotificacao, TipoGatilho
    from notificacoes.services import ServicoEmail
    from datetime import date, timedelta

    result = TaskResult('enviar_inadimplentes')

    try:
        regras = list(RegraNotificacao.objects.filter(
            ativo=True, tipo_gatilho=TipoGatilho.APOS_VENCIMENTO
        ))

        if regras:
            # N-03: régua configurável
            result.add_message(f"N-03: {len(regras)} regra(s) APÓS ativa(s)")
            for regra in regras:
                _processar_regra(regra, result)
        else:
            # Fallback N-02: exatamente D+N (mesma lógica de data_alvo do N-03)
            # Usa data_vencimento=data_corte para disparar UMA VEZ no dia exato,
            # evitando reenvio diário para parcelas com atraso acumulado.
            PREFIXO = '[INADIMPLENCIA]'
            dias_carencia = getattr(settings, 'NOTIFICACAO_DIAS_INADIMPLENCIA', 3)
            hoje = date.today()
            data_corte = hoje - timedelta(days=dias_carencia)

            parcelas = Parcela.objects.filter(
                pago=False,
                tipo_parcela='NORMAL',
                data_vencimento=data_corte,
            ).select_related('contrato', 'contrato__comprador', 'contrato__imobiliaria')

            result.add_message(
                f"N-02 (padrão): {parcelas.count()} parcelas em atraso (D+{dias_carencia})"
            )

            for parcela in parcelas:
                try:
                    comprador = parcela.contrato.comprador
                    if not (getattr(comprador, 'notificar_email', True) and comprador.email):
                        continue
                    # Dedup all-time: N-02 dispara UMA única vez por parcela
                    if _notificacao_ja_enviada(parcela, PREFIXO):
                        continue

                    dias_atraso = (hoje - parcela.data_vencimento).days
                    assunto = (
                        f"{PREFIXO} Parcela {parcela.numero_parcela} em atraso há {dias_atraso} dia(s) "
                        f"— {parcela.data_vencimento.strftime('%d/%m/%Y')}"
                    )
                    imob = parcela.contrato.imobiliaria
                    imob_nome = getattr(imob, 'nome', 'Gestão de Contratos')
                    mensagem = (
                        f"Olá {comprador.nome},\n\n"
                        f"Verificamos que a parcela {parcela.numero_parcela}/{parcela.contrato.numero_parcelas} "
                        f"do contrato {parcela.contrato.numero_contrato} encontra-se em atraso.\n\n"
                        f"Vencimento: {parcela.data_vencimento.strftime('%d/%m/%Y')} "
                        f"({dias_atraso} dia(s) em atraso)\n"
                        f"Valor original: R$ {parcela.valor_atual:,.2f}\n\n"
                        f"Por favor, regularize sua situação o quanto antes para evitar "
                        f"acréscimo de juros e multa.\n\n"
                        f"Em caso de dúvidas, entre em contato conosco.\n\n"
                        f"Atenciosamente,\n{imob_nome}"
                    )
                    html_msg = _html_email(
                        titulo='Aviso de Inadimplência',
                        cor_header='#c0392b',
                        icone='⚠️',
                        subtitulo=f'Olá, {comprador.nome}! Identificamos uma parcela em atraso.',
                        linhas_info=[
                            ('Contrato', parcela.contrato.numero_contrato),
                            ('Parcela', f'{parcela.numero_parcela}/{parcela.contrato.numero_parcelas}'),
                            ('Vencimento', parcela.data_vencimento.strftime('%d/%m/%Y')),
                            ('Dias em atraso', f'{dias_atraso} dia(s)'),
                            ('Valor em aberto', f'R$ {parcela.valor_atual:,.2f}'),
                        ],
                        rodape_nome=imob_nome,
                        rodape_tel=getattr(imob, 'telefone', ''),
                        rodape_email=getattr(imob, 'email', ''),
                        aviso=(
                            'Regularize o pagamento o quanto antes para evitar acréscimo de '
                            'juros e multa, bem como protesto do título.'
                        ),
                        cor_aviso='#c0392b',
                    )

                    notif = _registrar_notificacao(
                        parcela, TipoNotificacao.EMAIL, comprador.email, assunto, mensagem
                    )
                    try:
                        ServicoEmail.enviar(
                            destinatario=comprador.email, assunto=assunto,
                            mensagem=mensagem, html_message=html_msg,
                        )
                        notif.marcar_como_enviada()
                        result.items_processed += 1
                        result.add_message(
                            f"Inadimplência enviada → {comprador.email} (parcela {parcela.id}, {dias_atraso}d)"
                        )
                    except Exception as e_send:
                        notif.marcar_erro(str(e_send))
                        result.add_error(f"Erro ao enviar inadimplência parcela {parcela.id}: {e_send}")

                except Exception as e:
                    logger.exception("Erro ao processar parcela inadimplente %s: %s", parcela.id, e)
                    result.add_error(f"Erro parcela {parcela.id}: {str(e)}")

        result.finish()

    except Exception as e:
        logger.exception("Erro geral em enviar_inadimplentes_sync: %s", e)
        result.add_error(f"Erro geral: {str(e)}")
        result.finish(success=False)

    return result


def atualizar_status_parcelas_sync():
    """
    Verifica parcelas vencidas e não pagas.
    Parcela usa pago=True/False — não há campo status a actualizar.
    Esta tarefa apenas emite um relatório de contagem.
    """
    from financeiro.models import Parcela
    from datetime import date

    result = TaskResult('atualizar_status_parcelas')

    try:
        hoje = date.today()

        # Contar parcelas vencidas e não pagas
        count = Parcela.objects.filter(
            pago=False,
            data_vencimento__lt=hoje
        ).count()

        result.items_processed = count
        result.add_message(f"{count} parcelas em atraso (vencidas e não pagas)")
        result.finish()

    except Exception as e:
        logger.exception("Erro em atualizar_status_parcelas: %s", e)
        result.add_error(f"Erro: {str(e)}")
        result.finish(success=False)

    return result


def _enviar_email_da_fila(notif):
    """
    Despacha uma Notificacao do tipo EMAIL.
    Boleto (notif.parcela set) → EmailMultiAlternatives com HTML + PDF em anexo.
    Demais → ServicoEmail plain-text.
    """
    from notificacoes.services import ServicoEmail
    from django.core.mail import EmailMultiAlternatives
    from django.conf import settings as _settings

    mensagem = notif.mensagem
    is_html = mensagem.strip().startswith('<')

    if notif.parcela and is_html:
        email_obj = EmailMultiAlternatives(
            subject=notif.assunto,
            body='',
            from_email=_settings.DEFAULT_FROM_EMAIL,
            to=[notif.destinatario],
        )
        email_obj.attach_alternative(mensagem, 'text/html')

        # Tentar anexar PDF do boleto
        parcela = notif.parcela
        pdf_bytes = None
        try:
            if parcela.boleto_pdf and parcela.boleto_pdf.name:
                from django.core.files.storage import default_storage
                if default_storage.exists(parcela.boleto_pdf.name):
                    pdf_bytes = parcela.boleto_pdf.read()
        except Exception:
            pass
        if not pdf_bytes and getattr(parcela, 'boleto_pdf_db', None):
            try:
                pdf_bytes = bytes(parcela.boleto_pdf_db)
            except Exception:
                pass
        if pdf_bytes:
            contrato = parcela.contrato
            nome = f"boleto_{contrato.numero_contrato}_{parcela.numero_parcela}.pdf"
            email_obj.attach(nome, pdf_bytes, 'application/pdf')

        email_obj.send()
    else:
        ServicoEmail.enviar(
            destinatario=notif.destinatario,
            assunto=notif.assunto,
            mensagem=mensagem,
        )


def processar_fila_notificacoes():
    """
    Processa todas as Notificacao com status=PENDENTE (Option B — fila no banco).
    Retry automático: mantém PENDENTE até MAX_TENTATIVAS, depois marca ERRO.
    Deve ser chamado pelo cron (task_run_all) ou endpoint dedicado.
    """
    from notificacoes.models import Notificacao, TipoNotificacao, StatusNotificacao
    from notificacoes.services import ServicoSMS, ServicoWhatsApp

    MAX_TENTATIVAS = 3
    result = TaskResult('processar_fila_notificacoes')

    try:
        pendentes = list(
            Notificacao.objects.filter(status=StatusNotificacao.PENDENTE)
            .order_by('data_agendamento')
            .select_related('parcela', 'parcela__contrato')
        )
        result.add_message(f"{len(pendentes)} notificação(ões) PENDENTE(s) na fila")

        for notif in pendentes:
            try:
                if notif.tipo == TipoNotificacao.EMAIL:
                    _enviar_email_da_fila(notif)
                elif notif.tipo == TipoNotificacao.SMS:
                    ServicoSMS.enviar(destinatario=notif.destinatario, mensagem=notif.mensagem)
                elif notif.tipo == TipoNotificacao.WHATSAPP:
                    ServicoWhatsApp.enviar(destinatario=notif.destinatario, mensagem=notif.mensagem)
                else:
                    raise ValueError(f"Tipo de notificação desconhecido: {notif.tipo}")

                notif.marcar_como_enviada()
                result.items_processed += 1
                result.add_message(
                    f"  ✓ {notif.get_tipo_display()} → {notif.destinatario} (notif {notif.id})"
                )

            except Exception as e:
                proximas_tentativas = notif.tentativas + 1
                if proximas_tentativas >= MAX_TENTATIVAS:
                    notif.marcar_erro(str(e))
                    result.add_error(
                        f"Notif {notif.id} falhou {proximas_tentativas}x (ERRO definitivo): {e}"
                    )
                else:
                    notif.tentativas = proximas_tentativas
                    notif.save(update_fields=['tentativas'])
                    result.add_message(
                        f"  ↺ Notif {notif.id} tentativa {proximas_tentativas}/{MAX_TENTATIVAS}: {e}"
                    )

        result.finish()

    except Exception as e:
        logger.exception("Erro geral em processar_fila_notificacoes: %s", e)
        result.add_error(f"Erro geral: {str(e)}")
        result.finish(success=False)

    return result


# =============================================================================
# VIEWS PARA EXECUÇÃO DE TAREFAS VIA HTTP
# =============================================================================

@require_http_methods(["POST"])
@task_api_rate_limit
@task_auth_required
def task_processar_reajustes(request):
    """Endpoint para processar reajustes."""
    result = processar_reajustes_sync()
    status_code = 200 if result.success else 500
    return JsonResponse(result.to_dict(), status=status_code)


@require_http_methods(["POST"])
@task_api_rate_limit
@task_auth_required
def task_enviar_notificacoes(request):
    """Endpoint para enviar notificações de vencimento (N-01: D-5)."""
    result = enviar_notificacoes_sync()
    status_code = 200 if result.success else 500
    return JsonResponse(result.to_dict(), status=status_code)


@require_http_methods(["POST"])
@task_api_rate_limit
@task_auth_required
def task_enviar_inadimplentes(request):
    """Endpoint para enviar notificações de inadimplência (N-02: D+3)."""
    result = enviar_inadimplentes_sync()
    status_code = 200 if result.success else 500
    return JsonResponse(result.to_dict(), status=status_code)


@require_http_methods(["POST"])
@task_api_rate_limit
@task_auth_required
def task_atualizar_parcelas(request):
    """Endpoint para atualizar status de parcelas."""
    result = atualizar_status_parcelas_sync()
    status_code = 200 if result.success else 500
    return JsonResponse(result.to_dict(), status=status_code)


@require_http_methods(["POST"])
@task_api_rate_limit
@task_auth_required
def task_processar_fila(request):
    """Endpoint para processar fila de notificações PENDENTE (Option B)."""
    result = processar_fila_notificacoes()
    status_code = 200 if result.success else 500
    return JsonResponse(result.to_dict(), status=status_code)


@require_http_methods(["POST"])
@task_api_rate_limit
@task_auth_required
def task_run_all(request):
    """
    Executa todas as tarefas agendadas.
    Ideal para cron jobs externos.
    """
    results = []

    # 1. Atualizar status de parcelas
    results.append(atualizar_status_parcelas_sync().to_dict())

    # 2. Processar reajustes
    results.append(processar_reajustes_sync().to_dict())

    # 3. Processar fila de notificações (boletos gerados, Option B)
    results.append(processar_fila_notificacoes().to_dict())

    # 4. Enviar notificações de vencimento (N-01)
    results.append(enviar_notificacoes_sync().to_dict())

    # 5. Enviar notificações de inadimplência (N-02)
    results.append(enviar_inadimplentes_sync().to_dict())

    all_success = all(r['success'] for r in results)

    return JsonResponse({
        'status': 'success' if all_success else 'partial_failure',
        'executed_at': datetime.now().isoformat(),
        'tasks': results
    }, status=200 if all_success else 207)


@require_http_methods(["GET"])
def task_status(request):
    """
    Retorna status das tarefas (não requer autenticação).
    Útil para verificar se o sistema de tarefas está configurado.
    """
    return JsonResponse({
        'tasks_enabled': bool(get_param('TASK_TOKEN')),
        'available_tasks': [
            {
                'name': 'processar_reajustes',
                'endpoint': '/api/tasks/processar-reajustes/',
                'description': 'Processa reajustes pendentes de contratos'
            },
            {
                'name': 'enviar_notificacoes',
                'endpoint': '/api/tasks/enviar-notificacoes/',
                'description': 'Envia notificações de vencimento'
            },
            {
                'name': 'atualizar_parcelas',
                'endpoint': '/api/tasks/atualizar-parcelas/',
                'description': 'Atualiza status de parcelas vencidas'
            },
            {
                'name': 'processar_fila',
                'endpoint': '/api/tasks/processar-fila/',
                'description': 'Processa fila de notificações PENDENTE (boletos gerados, retry automático)'
            },
            {
                'name': 'run_all',
                'endpoint': '/api/tasks/run-all/',
                'description': 'Executa todas as tarefas'
            },
            {
                'name': 'relatorio_semanal',
                'endpoint': '/api/tasks/relatorio-semanal/',
                'description': 'Envia relatório semanal para cada imobiliária'
            },
            {
                'name': 'relatorio_mensal',
                'endpoint': '/api/tasks/relatorio-mensal/',
                'description': 'Envia relatório mensal consolidado para contabilidades'
            }
        ],
        'cron_setup': {
            'recommended_service': 'cron-job.org (gratuito)',
            'schedule': 'Diariamente às 08:00',
            'endpoint': '/api/tasks/run-all/',
            'method': 'POST',
            'header': 'X-Task-Token: <seu-token>'
        }
    })


# =============================================================================
# RELATÓRIOS PERIÓDICOS (P3)
# =============================================================================

def relatorio_semanal_incorporadoras_sync():
    """
    Gera e envia relatório semanal para cada imobiliária.

    Conteúdo: inadimplência, reajustes pendentes, boletos emitidos,
    recebimentos da semana. Enviado por e-mail via Django mail.
    """
    from django.core.mail import send_mail
    from django.db.models import Sum, Count
    from financeiro.models import Parcela

    result = TaskResult('relatorio_semanal_incorporadoras')

    try:
        from core.models import Imobiliaria
        from django.utils import timezone

        hoje = timezone.now().date()
        inicio_semana = hoje - timedelta(days=hoje.weekday())  # segunda-feira

        imobiliarias = Imobiliaria.objects.filter(ativo=True)
        relatorios_gerados = 0

        for imobiliaria in imobiliarias:
            parcelas_qs = Parcela.objects.filter(
                contrato__imobiliaria=imobiliaria,
                contrato__status='ATIVO',
            )

            # Recebimentos da semana
            recebimentos = parcelas_qs.filter(
                pago=True,
                data_pagamento__gte=inicio_semana,
                data_pagamento__lte=hoje,
            ).aggregate(
                quantidade=Count('id'),
                valor=Sum('valor_pago'),
            )

            # Inadimplência atual
            vencidas = parcelas_qs.filter(
                pago=False,
                data_vencimento__lt=hoje,
            ).aggregate(
                quantidade=Count('id'),
                valor=Sum('valor_atual'),
            )

            # Vencendo na próxima semana
            prox_semana = hoje + timedelta(days=7)
            a_vencer = parcelas_qs.filter(
                pago=False,
                data_vencimento__gte=hoje,
                data_vencimento__lte=prox_semana,
            ).aggregate(
                quantidade=Count('id'),
                valor=Sum('valor_atual'),
            )

            relatorio = {
                'imobiliaria': imobiliaria.nome,
                'periodo': f'{inicio_semana} a {hoje}',
                'recebimentos': {
                    'quantidade': recebimentos['quantidade'] or 0,
                    'valor': float(recebimentos['valor'] or 0),
                },
                'inadimplencia': {
                    'quantidade': vencidas['quantidade'] or 0,
                    'valor': float(vencidas['valor'] or 0),
                },
                'a_vencer_7_dias': {
                    'quantidade': a_vencer['quantidade'] or 0,
                    'valor': float(a_vencer['valor'] or 0),
                },
            }

            # Enviar por e-mail se imobiliária tiver e-mail configurado
            if imobiliaria.email:
                try:
                    corpo = (
                        f"Relatório Semanal — {imobiliaria.nome}\n"
                        f"Período: {relatorio['periodo']}\n\n"
                        f"Recebimentos: {relatorio['recebimentos']['quantidade']} "
                        f"(R$ {relatorio['recebimentos']['valor']:.2f})\n"
                        f"Inadimplência: {relatorio['inadimplencia']['quantidade']} "
                        f"(R$ {relatorio['inadimplencia']['valor']:.2f})\n"
                        f"A vencer (7d): {relatorio['a_vencer_7_dias']['quantidade']} "
                        f"(R$ {relatorio['a_vencer_7_dias']['valor']:.2f})\n"
                    )
                    send_mail(
                        subject=f'Relatório Semanal — {imobiliaria.nome}',
                        message=corpo,
                        from_email=None,  # usa DEFAULT_FROM_EMAIL
                        recipient_list=[_destinatario_email_teste(imobiliaria.email)],
                        fail_silently=True,
                    )
                except Exception as e:
                    logger.warning("Erro ao enviar e-mail para %s: %s", imobiliaria.email, e)

            relatorios_gerados += 1
            result.add_message(
                f'{imobiliaria.nome}: {relatorio["recebimentos"]["quantidade"]} recebimentos, '
                f'{relatorio["inadimplencia"]["quantidade"]} inadimplentes'
            )

        result.items_processed = relatorios_gerados
        result.finish()
        logger.info("Relatório semanal gerado para %d imobiliárias", relatorios_gerados)

    except Exception as e:
        logger.exception("Erro em relatorio_semanal_incorporadoras: %s", e)
        result.add_error(f"Erro: {str(e)}")
        result.finish(success=False)

    return result


def relatorio_mensal_consolidado_sync():
    """
    Gera relatório mensal consolidado de todas as imobiliárias
    para a contabilidade.

    Executar no 1º dia útil do mês.
    Conteúdo: totais por imobiliária, contratos ativos/encerrados,
    recebimentos, inadimplência, reajustes aplicados.
    """
    from django.core.mail import send_mail
    from django.db.models import Sum, Count
    from financeiro.models import Parcela, Reajuste
    from contratos.models import Contrato

    result = TaskResult('relatorio_mensal_consolidado')

    try:
        from core.models import Contabilidade
        from django.utils import timezone

        hoje = timezone.now().date()
        primeiro_dia_mes_atual = hoje.replace(day=1)
        ultimo_dia_mes_anterior = primeiro_dia_mes_atual - timedelta(days=1)
        primeiro_dia_mes_anterior = ultimo_dia_mes_anterior.replace(day=1)

        contabilidades = Contabilidade.objects.filter(ativo=True)
        relatorios_gerados = 0

        for contabilidade in contabilidades:
            imobiliarias = contabilidade.imobiliarias.filter(ativo=True)
            dados_contabilidade = {
                'contabilidade': contabilidade.nome,
                'mes_referencia': primeiro_dia_mes_anterior.strftime('%B/%Y'),
                'imobiliarias': [],
                'totais': {
                    'contratos_ativos': 0,
                    'recebimentos': 0,
                    'valor_recebido': 0,
                    'inadimplentes': 0,
                    'valor_inadimplente': 0,
                    'reajustes_aplicados': 0,
                },
            }

            for imobiliaria in imobiliarias:
                parcelas_qs = Parcela.objects.filter(
                    contrato__imobiliaria=imobiliaria,
                )

                contratos_ativos = Contrato.objects.filter(
                    imobiliaria=imobiliaria,
                    status='ATIVO',
                ).count()

                recebimentos = parcelas_qs.filter(
                    pago=True,
                    data_pagamento__gte=primeiro_dia_mes_anterior,
                    data_pagamento__lte=ultimo_dia_mes_anterior,
                ).aggregate(
                    quantidade=Count('id'),
                    valor=Sum('valor_pago'),
                )

                inadimplentes = parcelas_qs.filter(
                    pago=False,
                    data_vencimento__lt=hoje,
                ).aggregate(
                    quantidade=Count('id'),
                    valor=Sum('valor_atual'),
                )

                reajustes = Reajuste.objects.filter(
                    contrato__imobiliaria=imobiliaria,
                    data_reajuste__gte=primeiro_dia_mes_anterior,
                    data_reajuste__lte=ultimo_dia_mes_anterior,
                ).count()

                dados_imob = {
                    'nome': imobiliaria.nome,
                    'contratos_ativos': contratos_ativos,
                    'recebimentos': recebimentos['quantidade'] or 0,
                    'valor_recebido': float(recebimentos['valor'] or 0),
                    'inadimplentes': inadimplentes['quantidade'] or 0,
                    'valor_inadimplente': float(inadimplentes['valor'] or 0),
                    'reajustes_aplicados': reajustes,
                }

                dados_contabilidade['imobiliarias'].append(dados_imob)
                totais = dados_contabilidade['totais']
                totais['contratos_ativos'] += contratos_ativos
                totais['recebimentos'] += dados_imob['recebimentos']
                totais['valor_recebido'] += dados_imob['valor_recebido']
                totais['inadimplentes'] += dados_imob['inadimplentes']
                totais['valor_inadimplente'] += dados_imob['valor_inadimplente']
                totais['reajustes_aplicados'] += reajustes

            # Enviar e-mail para contabilidade
            if contabilidade.email:
                try:
                    totais = dados_contabilidade['totais']
                    linhas = [
                        f"Relatório Mensal Consolidado — {contabilidade.nome}",
                        f"Referência: {dados_contabilidade['mes_referencia']}",
                        "",
                        f"Contratos ativos: {totais['contratos_ativos']}",
                        f"Recebimentos: {totais['recebimentos']} (R$ {totais['valor_recebido']:.2f})",
                        f"Inadimplência: {totais['inadimplentes']} (R$ {totais['valor_inadimplente']:.2f})",
                        f"Reajustes aplicados: {totais['reajustes_aplicados']}",
                        "",
                        "Por imobiliária:",
                    ]
                    for imob in dados_contabilidade['imobiliarias']:
                        linhas.append(
                            f"  {imob['nome']}: "
                            f"{imob['contratos_ativos']} contratos, "
                            f"R$ {imob['valor_recebido']:.2f} recebido, "
                            f"{imob['inadimplentes']} inadimplentes"
                        )
                    send_mail(
                        subject=f'Relatório Mensal — {contabilidade.nome} — {dados_contabilidade["mes_referencia"]}',
                        message='\n'.join(linhas),
                        from_email=None,
                        recipient_list=[_destinatario_email_teste(contabilidade.email)],
                        fail_silently=True,
                    )
                except Exception as e:
                    logger.warning("Erro ao enviar e-mail para %s: %s", contabilidade.email, e)

            relatorios_gerados += 1
            result.add_message(
                f'{contabilidade.nome}: {dados_contabilidade["totais"]["contratos_ativos"]} '
                f'contratos, R$ {dados_contabilidade["totais"]["valor_recebido"]:.2f} recebido'
            )

        result.items_processed = relatorios_gerados
        result.finish()
        logger.info("Relatório mensal consolidado gerado para %d contabilidades", relatorios_gerados)

    except Exception as e:
        logger.exception("Erro em relatorio_mensal_consolidado: %s", e)
        result.add_error(f"Erro: {str(e)}")
        result.finish(success=False)

    return result


@require_http_methods(["POST"])
@task_api_rate_limit
@task_auth_required
def task_relatorio_semanal(request):
    """Endpoint para gerar relatório semanal de incorporadoras."""
    result = relatorio_semanal_incorporadoras_sync()
    status_code = 200 if result.success else 500
    return JsonResponse(result.to_dict(), status=status_code)


@require_http_methods(["POST"])
@task_api_rate_limit
@task_auth_required
def task_relatorio_mensal(request):
    """Endpoint para gerar relatório mensal consolidado."""
    result = relatorio_mensal_consolidado_sync()
    status_code = 200 if result.success else 500
    return JsonResponse(result.to_dict(), status=status_code)


@require_http_methods(["POST"])
@task_api_rate_limit
@task_auth_required
def task_processar_notificacoes(request):
    """
    Endpoint dedicado para processamento COMPLETO de notificações.

    Executa sequencialmente:
      1. processar_fila_notificacoes  — boletos gerados aguardando envio (PENDENTE)
      2. enviar_notificacoes_sync     — avisos de vencimento (N-01: D-5, D-3, D-1, D0)
      3. enviar_inadimplentes_sync    — avisos de inadimplência (N-02: D+3, D+7, D+15)

    Use este endpoint quando quiser acionar APENAS notificações com maior frequência
    (ex.: a cada 6 horas), sem re-executar reajustes e atualização de parcelas.
    """
    results = []
    results.append(processar_fila_notificacoes().to_dict())
    results.append(enviar_notificacoes_sync().to_dict())
    results.append(enviar_inadimplentes_sync().to_dict())

    all_success = all(r['success'] for r in results)
    return JsonResponse({
        'status': 'success' if all_success else 'partial_failure',
        'executed_at': datetime.now().isoformat(),
        'tasks': results,
    }, status=200 if all_success else 207)


def _data_inicio_incremental(tipo_indice: str, hoje) -> 'date':
    """
    Calcula data_inicio para busca incremental por tipo de índice.

    Sem dados no BD:
      - Usa a data do contrato mais antigo ativo que utiliza este índice
        (primário ou fallback), garantindo cobertura histórica completa.
      - Se nenhum contrato usa o índice, usa 13 meses atrás.

    Com dados no BD:
      - Reprocessa a partir do último registro − 1 mês (overlap para revisões).
      - Sempre garante pelo menos 3 meses de lookback.
    """
    from datetime import date as _date
    from dateutil.relativedelta import relativedelta as _rd
    from contratos.models import IndiceReajuste, Contrato as _Contrato

    ultimo = (
        IndiceReajuste.objects
        .filter(tipo_indice=tipo_indice)
        .order_by('-ano', '-mes')
        .values('ano', 'mes')
        .first()
    )

    if not ultimo:
        # Carga inicial: buscar a partir do contrato mais antigo que usa este índice
        contrato_mais_antigo = (
            _Contrato.objects
            .filter(
                status='ATIVO',
                tipo_correcao=tipo_indice,
            )
            .order_by('data_contrato')
            .values('data_contrato')
            .first()
        )
        if not contrato_mais_antigo:
            # Tenta também como fallback
            contrato_mais_antigo = (
                _Contrato.objects
                .filter(
                    status='ATIVO',
                    tipo_correcao_fallback=tipo_indice,
                )
                .order_by('data_contrato')
                .values('data_contrato')
                .first()
            )
        if contrato_mais_antigo and contrato_mais_antigo['data_contrato']:
            dc = contrato_mais_antigo['data_contrato']
            return _date(dc.year, dc.month, 1)
        return hoje - _rd(months=13)

    data_ultimo = _date(ultimo['ano'], ultimo['mes'], 1)
    # Overlap de 1 mês para capturar revisões; mínimo de 3 meses de lookback
    data_inicio = max(data_ultimo - _rd(months=1), hoje - _rd(months=3))
    return data_inicio


def atualizar_indices_sync():
    """
    Baixa e importa índices econômicos de forma incremental.

    Para cada índice consulta o último registro no BD e busca apenas o
    período em falta (+ 1–3 meses de overlap para capturar revisões).
    Carga inicial (BD vazio) busca 13 meses completos.
    """
    from financeiro.services.indices_economicos_service import IndicesEconomicosService
    from datetime import date
    from dateutil.relativedelta import relativedelta

    result = TaskResult('atualizar_indices')
    INDICES = ['IPCA', 'INPC', 'IGPM', 'INCC', 'IGPDI', 'SELIC', 'TR']

    hoje = date.today()
    data_fim = hoje

    service = IndicesEconomicosService()
    total_criados = 0
    total_atualizados = 0

    for tipo in INDICES:
        data_inicio = _data_inicio_incremental(tipo, hoje)
        try:
            resumo = service.importar_indices(tipo, data_inicio, data_fim)
            criados = resumo.get('criados', 0)
            atualizados = resumo.get('atualizados', 0)
            total_criados += criados
            total_atualizados += atualizados
            result.add_message(
                f'{tipo}: {criados} novos, {atualizados} atualizados'
                f' (período {data_inicio:%m/%Y}–{data_fim:%m/%Y})'
            )
            result.items_processed += criados + atualizados
        except Exception as e:
            result.add_error(f'{tipo}: erro — {e}')
            logger.exception('Erro ao importar índice %s: %s', tipo, e)

    if service.erros:
        for err in service.erros:
            result.add_error(err)

    result.add_message(f'Total: {total_criados} criados, {total_atualizados} atualizados')
    result.finish()
    result.success = len(result.errors) < len(INDICES)
    return result


@require_http_methods(["POST"])
@task_api_rate_limit
@task_auth_required
def task_atualizar_indices(request):
    """
    Endpoint para baixar índices econômicos das APIs públicas (IBGE + Banco Central).

    Agende semanalmente via cron-job.org (1×/semana) para manter a base de índices
    atualizada e permitir aplicação de reajustes assim que o período de referência
    estiver disponível.
    """
    result = atualizar_indices_sync()
    status_code = 200 if result.success else 500
    return JsonResponse(result.to_dict(), status=status_code)


@require_http_methods(["POST"])
@task_api_rate_limit
@task_auth_required
def task_processar_bounces(request):
    """
    Endpoint para processar bounces de e-mail via IMAP.

    Wrapper HTTP do management command `processar_bounces`: lê a caixa
    bounces@msbrasil.inf.br, detecta NDR/DSN e atualiza status_entrega='bounced'.

    Agende a cada 30 minutos no cron-job.org (J-06).
    """
    from django.core.management import call_command
    from io import StringIO

    result = TaskResult('processar_bounces')
    stdout = StringIO()
    stderr = StringIO()

    try:
        call_command('processar_bounces', stdout=stdout, stderr=stderr)
        output = stdout.getvalue().strip()
        if output:
            for line in output.split('\n'):
                result.add_message(line)
        err_output = stderr.getvalue().strip()
        if err_output:
            for line in err_output.split('\n'):
                result.add_error(line)
        result.finish()
    except Exception as e:
        result.add_error(str(e))
        result.finish(success=False)
        logger.exception('[task_processar_bounces] %s', e)

    status_code = 200 if result.success else 500
    return JsonResponse(result.to_dict(), status=status_code)


@require_http_methods(["POST"])
@task_api_rate_limit
@task_auth_required
def task_limpar_sessoes(request):
    """
    Endpoint para limpar sessões Django expiradas.

    Wrapper HTTP do management command `clearsessions` (built-in Django).
    Agende semanalmente no cron-job.org (J-07, domingo 03:00).
    """
    from django.core.management import call_command

    result = TaskResult('limpar_sessoes')

    try:
        call_command('clearsessions')
        result.add_message('Sessões expiradas removidas com sucesso.')
        result.finish()
    except Exception as e:
        result.add_error(str(e))
        result.finish(success=False)
        logger.exception('[task_limpar_sessoes] %s', e)

    status_code = 200 if result.success else 500
    return JsonResponse(result.to_dict(), status=status_code)


def testar_notificacoes_sync(email_destino=None, sms_destino=None, skip_sms=False):
    """
    Diagnóstico completo de e-mail e SMS.
    Retorna dict com resultados de cada etapa.
    """
    import traceback as tb
    from django.core.mail import send_mail

    resultado = {
        'configuracoes': {},
        'templates': {},
        'email_direto': None,
        'servico_email': None,
        'sms': None,
        'avisos': [],
    }

    # 1. Configurações
    backend = getattr(settings, 'EMAIL_BACKEND', '')
    host = getattr(settings, 'EMAIL_HOST', '')
    port = getattr(settings, 'EMAIL_PORT', '')
    use_tls = getattr(settings, 'EMAIL_USE_TLS', False)
    use_ssl = getattr(settings, 'EMAIL_USE_SSL', False)
    user = getattr(settings, 'EMAIL_HOST_USER', '')
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', '')
    test_mode = getattr(settings, 'TEST_MODE', False)
    test_email = getattr(settings, 'TEST_RECIPIENT_EMAIL', '')
    test_phone = getattr(settings, 'TEST_RECIPIENT_PHONE', '')
    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
    auth_token_twilio = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
    numero_twilio = getattr(settings, 'TWILIO_PHONE_NUMBER', '')

    resultado['configuracoes'] = {
        'EMAIL_BACKEND': backend,
        'EMAIL_HOST': host,
        'EMAIL_PORT': port,
        'EMAIL_USE_TLS': use_tls,
        'EMAIL_USE_SSL': use_ssl,
        'EMAIL_HOST_USER': user,
        'DEFAULT_FROM_EMAIL': from_email,
        'TEST_MODE': test_mode,
        'TEST_RECIPIENT_EMAIL': test_email,
        'TEST_RECIPIENT_PHONE': test_phone,
        'TWILIO_CONFIGURADO': bool(account_sid and auth_token_twilio and numero_twilio),
    }

    if 'console' in backend.lower():
        resultado['avisos'].append(
            'EMAIL_BACKEND=console — e-mails vão para o log, NÃO são entregues. '
            'Defina EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend no .env/Render.'
        )

    # 2. Templates
    try:
        from notificacoes.models import TemplateNotificacao, TipoTemplate, TipoNotificacao
        for codigo in [TipoTemplate.BOLETO_CRIADO, TipoTemplate.BOLETO_5_DIAS,
                       TipoTemplate.BOLETO_VENCE_AMANHA, TipoTemplate.BOLETO_VENCEU_ONTEM]:
            t = TemplateNotificacao.objects.filter(codigo=codigo, tipo=TipoNotificacao.EMAIL).first()
            resultado['templates'][codigo] = {
                'existe': bool(t),
                'ativo': t.ativo if t else False,
            }
            if not t:
                resultado['avisos'].append(
                    f'Template {codigo} não encontrado — notificações falharão silenciosamente.'
                )
    except Exception as e:
        resultado['templates']['erro'] = str(e)

    # 3. E-mail direto (send_mail)
    destino_email = email_destino or test_email or from_email or 'receber@msbrasil.inf.br'
    try:
        enviados = send_mail(
            subject='[TESTE] Diagnóstico de E-mail — Gestão de Contratos',
            message=(
                f'Teste de diagnóstico de e-mail.\n'
                f'TEST_MODE: {test_mode}\n'
                f'EMAIL_BACKEND: {backend}\n'
                f'EMAIL_HOST: {host}:{port}\n'
            ),
            from_email=from_email,
            recipient_list=[destino_email],
            fail_silently=False,
        )
        resultado['email_direto'] = {
            'sucesso': bool(enviados),
            'destinatario': destino_email,
            'mensagem': 'E-mail enviado com sucesso' if enviados else 'send_mail retornou 0',
        }
    except Exception as e:
        resultado['email_direto'] = {
            'sucesso': False,
            'destinatario': destino_email,
            'erro': str(e),
            'traceback': tb.format_exc(),
        }

    # 4. ServicoEmail.enviar()
    try:
        from notificacoes.services import ServicoEmail, _destinatario_email_teste
        destino_final = _destinatario_email_teste(destino_email)
        ServicoEmail.enviar(
            destinatario=destino_email,
            assunto='[TESTE] ServicoEmail — Gestão de Contratos',
            mensagem=f'Teste via ServicoEmail.enviar(). TEST_MODE: {test_mode}. Destinatário final: {destino_final}.',
        )
        resultado['servico_email'] = {
            'sucesso': True,
            'destinatario_original': destino_email,
            'destinatario_final': destino_final,
        }
    except Exception as e:
        resultado['servico_email'] = {
            'sucesso': False,
            'erro': str(e),
            'traceback': tb.format_exc(),
        }

    # 5. SMS
    if not skip_sms and all([account_sid, auth_token_twilio, numero_twilio]):
        destino_sms = sms_destino or test_phone or '+5531993257479'
        try:
            from notificacoes.services import ServicoSMS, _destinatario_telefone_teste
            destino_final_sms = _destinatario_telefone_teste(destino_sms)
            ServicoSMS.enviar(
                destinatario=destino_sms,
                mensagem='[TESTE] SMS de diagnóstico — Gestão de Contratos. Pode ignorar.',
            )
            resultado['sms'] = {
                'sucesso': True,
                'destinatario_original': destino_sms,
                'destinatario_final': destino_final_sms,
            }
        except Exception as e:
            resultado['sms'] = {
                'sucesso': False,
                'erro': str(e),
                'traceback': tb.format_exc(),
            }
    elif skip_sms:
        resultado['sms'] = {'pulado': True}
    else:
        resultado['sms'] = {'pulado': True, 'motivo': 'Credenciais Twilio não configuradas'}

    return resultado


@require_http_methods(["POST"])
@task_api_rate_limit
@task_auth_required
def task_testar_notificacoes(request):
    """
    Endpoint de diagnóstico: testa e-mail e SMS, retorna JSON detalhado.

    Parâmetros opcionais (query string ou body JSON):
        email   — e-mail destino (padrão: TEST_RECIPIENT_EMAIL)
        sms     — telefone destino (padrão: TEST_RECIPIENT_PHONE)
        skip_sms — se '1' ou 'true', pula teste de SMS
    """
    import json as json_mod
    email = request.GET.get('email')
    sms = request.GET.get('sms')
    skip_sms_param = request.GET.get('skip_sms', '').lower() in ('1', 'true', 'yes')

    if request.content_type and 'json' in request.content_type:
        try:
            body = json_mod.loads(request.body)
            email = email or body.get('email')
            sms = sms or body.get('sms')
            skip_sms_param = skip_sms_param or body.get('skip_sms', False)
        except Exception:
            pass

    resultado = testar_notificacoes_sync(
        email_destino=email,
        sms_destino=sms,
        skip_sms=skip_sms_param,
    )
    status_code = 200
    return JsonResponse(resultado, status=status_code)
