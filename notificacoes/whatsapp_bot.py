"""
WhatsApp Chatbot — 2ª via, boletos em atraso, comprovante, resumo financeiro.

Fluxos:
  A — Identificação por telefone ou CPF
  B — Menu principal
  C — 2ª via de boleto
  D — Boletos em atraso (com encargos)
  E — Recebimento de comprovante de pagamento
  F — Resumo financeiro

Estados de sessão (SessaoConversaWhatsApp):
  INICIO              → tenta identificar por telefone, senão pede CPF
  AGUARDA_CPF         → aguarda CPF do cliente
  MENU                → exibe e processa o menu principal
  AGUARDA_SELECAO_BOLETO → aguarda escolha de parcela (modo 2via|atraso|comprovante)
  AGUARDA_COMPROVANTE → aguarda envio da mídia (imagem/PDF)
"""
import base64
import datetime
import json
import logging
import re
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

_TIMEOUT_SESSAO_MINUTOS = 20


def _somente_digitos(texto):
    return re.sub(r'\D', '', texto or '')


def _fmt_brl(valor):
    try:
        v = float(valor or 0)
    except (TypeError, ValueError):
        return 'R$ 0,00'
    return f"R$ {v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def _hoje():
    from django.utils import timezone
    return timezone.localdate()


_SAUDACOES = {'oi', 'olá', 'ola', 'bom dia', 'boa tarde', 'boa noite', 'menu', 'início', 'inicio', 'ajuda', 'help'}


class WhatsAppBotService:
    """Dispatcher de estados para o chatbot WhatsApp (Evolution API)."""

    # -------------------------------------------------------------------------
    # Entry point
    # -------------------------------------------------------------------------

    def processar(self, telefone, mensagem, tipo_msg, config_wa):
        """
        Ponto de entrada chamado pelo webhook para cada mensagem recebida.

        Args:
            telefone:   E.164 sem '+', ex: '5531999998888'
            mensagem:   texto recebido (vazio quando tipo_msg='media')
            tipo_msg:   'text' | 'media'
            config_wa:  ConfiguracaoWhatsApp ativo
        """
        from notificacoes.models import SessaoConversaWhatsApp

        from django.utils import timezone

        sessao, criada = SessaoConversaWhatsApp.objects.get_or_create(
            numero_whatsapp=telefone,
            ativo=True,
            defaults={'instancia': config_wa.instancia if config_wa else ''},
        )

        # C-14: timeout de sessão — aviso após 20 min de inatividade
        _estados_sem_timeout = (
            SessaoConversaWhatsApp.INICIO,
            SessaoConversaWhatsApp.AGUARDA_CPF,
        )
        if not criada and sessao.estado not in _estados_sem_timeout:
            delta = timezone.now() - sessao.atualizado_em
            if delta > datetime.timedelta(minutes=_TIMEOUT_SESSAO_MINUTOS):
                self._responder(
                    telefone,
                    '⏱ Sua sessão expirou por inatividade.\nDigite *olá* para começar novamente.',
                    config_wa,
                )
                sessao.estado = SessaoConversaWhatsApp.INICIO
                sessao.dados = {}
                sessao.save(update_fields=['estado', 'dados'])
                return

        try:
            txt = (mensagem or '').strip().lower()

            # Palavra-chave global: reinicia no menu (exceto estados de identificação)
            if txt in _SAUDACOES and sessao.estado not in (
                SessaoConversaWhatsApp.INICIO,
                SessaoConversaWhatsApp.AGUARDA_CPF,
            ):
                sessao.estado = SessaoConversaWhatsApp.MENU
                sessao.dados = {}
                sessao.save(update_fields=['estado', 'dados'])
                self._menu_principal(sessao, config_wa)
                return

            dispatch = {
                SessaoConversaWhatsApp.INICIO: self._fluxo_identificacao,
                SessaoConversaWhatsApp.AGUARDA_CPF: self._fluxo_aguarda_cpf,
                SessaoConversaWhatsApp.MENU: lambda s, t, m, c: self._despachar_menu(s, t, m, c),
                SessaoConversaWhatsApp.AGUARDA_SELECAO_BOLETO: lambda s, t, m, c: self._fluxo_selecao_boleto(s, t, c),
                SessaoConversaWhatsApp.AGUARDA_COMPROVANTE: lambda s, t, m, c: self._fluxo_aguarda_comprovante(s, m, c),
            }
            handler = dispatch.get(sessao.estado)
            if handler:
                handler(sessao, txt, tipo_msg, config_wa)

        except Exception:
            logger.exception('[ChatbotWA] erro ao processar mensagem de %s', telefone)
            self._responder(
                telefone,
                'Ops! Ocorreu um erro. Tente novamente ou responda *0* para falar com um atendente.',
                config_wa,
            )

    # -------------------------------------------------------------------------
    # Fluxo A — Identificação
    # -------------------------------------------------------------------------

    def _fluxo_identificacao(self, sessao, txt, tipo_msg, config_wa):
        comprador = self._identificar_por_telefone(sessao.numero_whatsapp)
        if comprador:
            sessao.comprador = comprador
            sessao.estado = sessao.MENU
            sessao.save(update_fields=['comprador', 'estado'])
            self._menu_principal(sessao, config_wa)
        else:
            sessao.estado = sessao.AGUARDA_CPF
            sessao.dados = {'tentativas': 0}
            sessao.save(update_fields=['estado', 'dados'])
            self._responder(
                sessao.numero_whatsapp,
                'Olá! 👋 Para acessar seus boletos, informe seu *CPF* (somente números):',
                config_wa,
            )

    def _fluxo_aguarda_cpf(self, sessao, txt, tipo_msg, config_wa):
        cpf_digits = _somente_digitos(txt)
        comprador = self._identificar_por_cpf(cpf_digits) if len(cpf_digits) == 11 else None

        if comprador:
            sessao.comprador = comprador
            sessao.estado = sessao.MENU
            sessao.dados = {}
            sessao.save(update_fields=['comprador', 'estado', 'dados'])
            self._menu_principal(sessao, config_wa)
        else:
            tentativas = sessao.dados.get('tentativas', 0) + 1
            if tentativas >= 3:
                sessao.encerrar()
                self._responder(
                    sessao.numero_whatsapp,
                    'CPF não encontrado. Entre em contato com a imobiliária para suporte.',
                    config_wa,
                )
            else:
                sessao.dados = {'tentativas': tentativas}
                sessao.save(update_fields=['dados'])
                self._responder(
                    sessao.numero_whatsapp,
                    f'CPF não encontrado ({tentativas}/3). Informe apenas os 11 dígitos do CPF:',
                    config_wa,
                )

    # -------------------------------------------------------------------------
    # Fluxo B — Menu principal
    # -------------------------------------------------------------------------

    def _menu_principal(self, sessao, config_wa):
        nome = sessao.comprador.nome.split()[0] if sessao.comprador_id else 'Cliente'
        self._responder(
            sessao.numero_whatsapp,
            f'🏠 *Gestão de Contratos*\n'
            f'Olá, {nome}! Como posso ajudar?\n\n'
            '1️⃣  2ª via de boleto\n'
            '2️⃣  Boletos em atraso\n'
            '3️⃣  Enviar comprovante de pagamento\n'
            '4️⃣  Meu resumo financeiro\n'
            '0️⃣  Falar com atendente\n\n'
            'Responda com o *número* da opção.',
            config_wa,
        )

    def _despachar_menu(self, sessao, txt, tipo_msg, config_wa):
        # Comprovante pode chegar como mídia diretamente (sem selecionar opção)
        if tipo_msg == 'media':
            self._iniciar_comprovante(sessao, config_wa)
            return

        opcoes = {
            '1': self._iniciar_2a_via,
            '2': self._iniciar_atraso,
            '3': self._iniciar_comprovante,
            '4': self._fluxo_resumo,
            '0': self._chamar_atendente,
        }
        aliases = {
            '2a via': '1', '2ª via': '1', 'segunda via': '1', 'boleto': '1', '2via': '1',
            'atraso': '2', 'vencido': '2', 'atrasado': '2', 'dívida': '2', 'divida': '2',
            'comprovante': '3', 'paguei': '3', 'pago': '3',
            'resumo': '4', 'situação': '4', 'situacao': '4', 'saldo': '4', 'financeiro': '4',
            'atendente': '0', 'humano': '0', 'pessoa': '0',
        }
        chave = aliases.get(txt, txt)
        handler = opcoes.get(chave)
        if handler:
            handler(sessao, config_wa)
        else:
            self._responder(
                sessao.numero_whatsapp,
                'Opção inválida. Responda com *1*, *2*, *3*, *4* ou *0*.',
                config_wa,
            )

    # -------------------------------------------------------------------------
    # Fluxo C — 2ª via de boleto
    # -------------------------------------------------------------------------

    def _iniciar_2a_via(self, sessao, config_wa):
        parcelas = self._parcelas_abertas(sessao.comprador)
        if not parcelas:
            self._responder(
                sessao.numero_whatsapp,
                '✅ Você não possui boletos abertos no momento.',
                config_wa,
            )
            return

        linhas = ['📋 *Boletos disponíveis para 2ª via:*\n']
        ids = []
        hoje = _hoje()
        for i, p in enumerate(parcelas, 1):
            venc = p.data_vencimento.strftime('%d/%m/%Y')
            icone = '⚠️' if p.data_vencimento < hoje else '📅'
            linhas.append(f'{i}. {icone} Parcela {p.numero_parcela} — Venc. {venc} — {_fmt_brl(p.valor_atual)}')
            ids.append(p.pk)

        linhas.append('\nQual parcela deseja? Responda com o *número*. (*0* para voltar)')
        self._set_estado(sessao, sessao.AGUARDA_SELECAO_BOLETO, {'parcelas_ids': ids, 'modo': '2via'})
        self._responder(sessao.numero_whatsapp, '\n'.join(linhas), config_wa)

    def _iniciar_atraso(self, sessao, config_wa):
        parcelas = self._parcelas_abertas(sessao.comprador, vencidas_only=True)
        if not parcelas:
            self._responder(
                sessao.numero_whatsapp,
                '✅ Você não possui boletos em atraso. Parabéns por estar em dia!',
                config_wa,
            )
            return

        linhas = ['⚠️ *Boletos em Atraso:*\n']
        ids = []
        hoje = _hoje()
        for i, p in enumerate(parcelas, 1):
            juros, multa = p.calcular_juros_multa(hoje)
            total = p.valor_atual + juros + multa
            venc = p.data_vencimento.strftime('%d/%m/%Y')
            linhas.append(
                f'{i}. Parcela {p.numero_parcela} — Venc. {venc}\n'
                f'   Principal: {_fmt_brl(p.valor_atual)}\n'
                f'   Juros + Multa: {_fmt_brl(juros + multa)}\n'
                f'   *Total hoje: {_fmt_brl(total)}*\n'
            )
            ids.append(p.pk)

        linhas.append('Deseja a 2ª via de alguma parcela? Responda com o *número* ou *0* para voltar.')
        self._set_estado(sessao, sessao.AGUARDA_SELECAO_BOLETO, {'parcelas_ids': ids, 'modo': 'atraso'})
        self._responder(sessao.numero_whatsapp, '\n'.join(linhas), config_wa)

    def _fluxo_selecao_boleto(self, sessao, txt, config_wa):
        if txt == '0':
            self._set_estado(sessao, sessao.MENU, {})
            self._menu_principal(sessao, config_wa)
            return

        parcelas_ids = sessao.dados.get('parcelas_ids', [])
        modo = sessao.dados.get('modo', '2via')

        try:
            idx = int(txt) - 1
            if idx < 0 or idx >= len(parcelas_ids):
                raise ValueError
            parcela_id = parcelas_ids[idx]
        except (ValueError, TypeError):
            self._responder(
                sessao.numero_whatsapp,
                f'Opção inválida. Escolha de *1* a *{len(parcelas_ids)}* ou *0* para voltar.',
                config_wa,
            )
            return

        if modo == 'comprovante':
            self._set_estado(sessao, sessao.AGUARDA_COMPROVANTE, {'parcela_selecionada': parcela_id})
            self._responder(
                sessao.numero_whatsapp,
                'Agora envie a *imagem* ou *PDF* do comprovante de pagamento:',
                config_wa,
            )
        else:
            self._enviar_2a_via_parcela(sessao, parcela_id, config_wa)
            self._set_estado(sessao, sessao.MENU, {})

    def _enviar_2a_via_parcela(self, sessao, parcela_id, config_wa):
        from financeiro.models import Parcela
        from financeiro.services.boleto_service import BoletoService

        try:
            parcela = Parcela.objects.select_related('contrato__imobiliaria').get(pk=parcela_id)
        except Parcela.DoesNotExist:
            self._responder(sessao.numero_whatsapp, 'Parcela não encontrada.', config_wa)
            return

        conta = parcela.contrato.get_conta_bancaria()
        if not conta:
            self._responder(
                sessao.numero_whatsapp,
                '⚠️ Conta bancária não configurada. Contate a imobiliária.',
                config_wa,
            )
            return

        resultado = BoletoService().gerar_segunda_via(parcela, conta)
        if not resultado.get('sucesso'):
            self._responder(
                sessao.numero_whatsapp,
                f'⚠️ Não foi possível gerar a 2ª via: {resultado.get("erro", "erro desconhecido")}',
                config_wa,
            )
            return

        hoje = _hoje()
        juros, multa = parcela.calcular_juros_multa(hoje)
        total = resultado.get('valor_total') or (parcela.valor_atual + juros + multa)
        linha = parcela.linha_digitavel or '(não disponível)'
        venc = parcela.data_vencimento.strftime('%d/%m/%Y')

        self._responder(
            sessao.numero_whatsapp,
            f'✅ *2ª Via — Parcela {parcela.numero_parcela}*\n'
            f'📋 Linha digitável:\n`{linha}`\n'
            f'📅 Vencimento: {venc}\n'
            f'💰 Valor: {_fmt_brl(total)}',
            config_wa,
        )

        pdf = resultado.get('pdf_content')
        if pdf:
            self._enviar_pdf(
                sessao.numero_whatsapp,
                pdf,
                f'boleto_parcela_{parcela.numero_parcela}.pdf',
                config_wa,
            )

    # -------------------------------------------------------------------------
    # Fluxo E — Comprovante de pagamento
    # -------------------------------------------------------------------------

    def _iniciar_comprovante(self, sessao, config_wa):
        parcelas = self._parcelas_abertas(sessao.comprador)
        if not parcelas:
            self._responder(
                sessao.numero_whatsapp,
                '✅ Você não possui parcelas abertas.',
                config_wa,
            )
            return

        linhas = ['📎 *Comprovante de Pagamento*\nA qual parcela este comprovante se refere?\n']
        ids = []
        for i, p in enumerate(parcelas, 1):
            venc = p.data_vencimento.strftime('%d/%m/%Y')
            linhas.append(f'{i}. Parcela {p.numero_parcela} — Venc. {venc} — {_fmt_brl(p.valor_atual)}')
            ids.append(p.pk)

        linhas.append('\nResponda com o *número* da parcela.')
        self._set_estado(sessao, sessao.AGUARDA_SELECAO_BOLETO, {'parcelas_ids': ids, 'modo': 'comprovante'})
        self._responder(sessao.numero_whatsapp, '\n'.join(linhas), config_wa)

    def _fluxo_aguarda_comprovante(self, sessao, tipo_msg, config_wa):
        if tipo_msg != 'media':
            self._responder(
                sessao.numero_whatsapp,
                'Por favor, envie a *imagem* ou *PDF* do comprovante.',
                config_wa,
            )
            return

        parcela_id = sessao.dados.get('parcela_selecionada')
        if not parcela_id:
            self._set_estado(sessao, sessao.MENU, {})
            self._responder(
                sessao.numero_whatsapp,
                '⚠️ Sessão expirada. Responda *3* para tentar novamente.',
                config_wa,
            )
            return

        self._registrar_comprovante(sessao, parcela_id, config_wa)

    def _registrar_comprovante(self, sessao, parcela_id, config_wa):
        from django.core.mail import send_mail
        from financeiro.models import Parcela
        from notificacoes.models import Notificacao, TipoNotificacao, StatusNotificacao

        try:
            parcela = Parcela.objects.select_related('contrato__imobiliaria').get(pk=parcela_id)
        except Parcela.DoesNotExist:
            self._responder(sessao.numero_whatsapp, 'Parcela não encontrada.', config_wa)
            return

        Notificacao.objects.create(
            parcela=parcela,
            tipo=TipoNotificacao.WHATSAPP,
            destinatario=sessao.numero_whatsapp,
            assunto=f'Comprovante recebido — Parcela {parcela.numero_parcela}',
            mensagem=(
                f'Comprador {sessao.comprador.nome if sessao.comprador else sessao.numero_whatsapp} '
                f'enviou comprovante via WhatsApp para parcela {parcela.numero_parcela} '
                f'(contrato {parcela.contrato_id}). Confirme o pagamento no admin.'
            ),
            status=StatusNotificacao.PENDENTE,
        )

        self._responder(
            sessao.numero_whatsapp,
            '✅ Comprovante recebido! Nossa equipe confirmará em até *1 dia útil*.',
            config_wa,
        )

        try:
            imob = parcela.contrato.imobiliaria
            if imob and imob.email:
                send_mail(
                    subject=f'[Comprovante WA] {sessao.comprador.nome if sessao.comprador else sessao.numero_whatsapp} — Parcela {parcela.numero_parcela}',
                    message=(
                        f'Comprador: {sessao.comprador.nome if sessao.comprador else "—"}\n'
                        f'WhatsApp: {sessao.numero_whatsapp}\n'
                        f'Parcela: {parcela.numero_parcela}\n'
                        f'Valor: {_fmt_brl(parcela.valor_atual)}\n\n'
                        'Confirme o pagamento no painel administrativo.'
                    ),
                    from_email=None,
                    recipient_list=[imob.email],
                    fail_silently=True,
                )
        except Exception:
            logger.exception('[ChatbotWA] falha ao notificar admin por e-mail')

        self._set_estado(sessao, sessao.MENU, {})

    # -------------------------------------------------------------------------
    # Fluxo F — Resumo financeiro
    # -------------------------------------------------------------------------

    def _fluxo_resumo(self, sessao, config_wa):
        from contratos.models import Contrato

        contratos = list(Contrato.objects.filter(
            comprador=sessao.comprador, ativo=True
        ).order_by('id')[:3])

        if not contratos:
            self._responder(
                sessao.numero_whatsapp,
                '📊 Você não possui contratos ativos.',
                config_wa,
            )
            return

        linhas = []
        for contrato in contratos:
            r = contrato.get_resumo_financeiro()
            prox = contrato.parcelas.filter(pago=False).order_by('data_vencimento').first()
            prox_txt = (
                f"📅 Próx. venc.: {prox.data_vencimento.strftime('%d/%m/%Y')} — {_fmt_brl(prox.valor_atual)}"
                if prox else '✅ Sem parcelas abertas'
            )
            linhas.append(
                f'📊 *Contrato #{contrato.pk}*\n'
                f'✅ Pagas: {r["parcelas_pagas"]} de {r["total_parcelas"]}\n'
                f'💰 Total pago: {_fmt_brl(r["total_pago"])}\n'
                f'{prox_txt}\n'
                f'⚠️ Em atraso: {r["parcelas_vencidas"]} parcela(s)\n'
                f'📈 Progresso: {r.get("progresso_percentual", 0):.0f}%'
            )

        self._responder(sessao.numero_whatsapp, '\n\n'.join(linhas), config_wa)

    # -------------------------------------------------------------------------
    # Opção 0 — Atendente
    # -------------------------------------------------------------------------

    def _chamar_atendente(self, sessao, config_wa):
        from django.core.mail import send_mail
        from contratos.models import Contrato

        self._responder(
            sessao.numero_whatsapp,
            '👤 Solicitação enviada! Um atendente entrará em contato em breve.',
            config_wa,
        )

        try:
            contrato = Contrato.objects.filter(
                comprador=sessao.comprador, ativo=True
            ).first()
            imob = contrato.imobiliaria if contrato else None
            if imob and imob.email:
                nome = sessao.comprador.nome if sessao.comprador_id else sessao.numero_whatsapp
                send_mail(
                    subject=f'[Atendimento WA] {nome}',
                    message=(
                        f'Cliente solicitou atendimento via WhatsApp.\n'
                        f'Número: {sessao.numero_whatsapp}\n'
                        f'Comprador: {nome}'
                    ),
                    from_email=None,
                    recipient_list=[imob.email],
                    fail_silently=True,
                )
        except Exception:
            logger.exception('[ChatbotWA] falha ao notificar atendente')

    # -------------------------------------------------------------------------
    # Comunicação — Evolution API
    # -------------------------------------------------------------------------

    def _responder(self, telefone, texto, config_wa):
        from notificacoes.services import ServicoWhatsApp
        try:
            if config_wa and config_wa.provedor == 'EVOLUTION':
                ServicoWhatsApp._enviar_evolution(telefone, texto, config_wa)
            else:
                logger.warning(
                    '[ChatbotWA] resposta ignorada — provedor %s não suportado',
                    config_wa.provedor if config_wa else 'None',
                )
        except Exception:
            logger.exception('[ChatbotWA] falha ao responder para %s', telefone)

    def _enviar_pdf(self, telefone, pdf_bytes, filename, config_wa):
        """Envia PDF via Evolution API /message/sendMedia/{instancia}."""
        if not config_wa or config_wa.provedor != 'EVOLUTION':
            return
        if not all([config_wa.api_url, config_wa.api_key, config_wa.instancia]):
            return
        try:
            pdf_b64 = base64.b64encode(pdf_bytes).decode()
            url = f"{config_wa.api_url.rstrip('/')}/message/sendMedia/{config_wa.instancia}"
            payload = {
                'number': telefone,
                'mediatype': 'document',
                'mimetype': 'application/pdf',
                'media': pdf_b64,
                'fileName': filename,
                'caption': '📄 Boleto — 2ª via',
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers={'Content-Type': 'application/json', 'apikey': config_wa.api_key},
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                resp.read()
            logger.info('[ChatbotWA] PDF enviado para %s (%s)', telefone, filename)
        except Exception:
            logger.exception('[ChatbotWA] falha ao enviar PDF para %s', telefone)

    # -------------------------------------------------------------------------
    # Identificação de compradores
    # -------------------------------------------------------------------------

    def _identificar_por_telefone(self, telefone):
        from core.models import Comprador
        digitos = _somente_digitos(telefone)
        # Tenta sufixos de 11 dígitos (celular) e 10 dígitos (fixo)
        sufixos = {digitos[-11:], digitos[-10:]} if len(digitos) >= 11 else {digitos}
        for campo in ('celular', 'telefone'):
            for sfx in sufixos:
                comp = Comprador.objects.filter(**{f'{campo}__endswith': sfx}).first()
                if comp:
                    return comp
        return None

    def _identificar_por_cpf(self, cpf_digits):
        """Busca Comprador pelo CPF (11 dígitos sem formatação).

        Tenta lookup exato (sem formatação), depois com formatação
        padrão XXX.XXX.XXX-XX (forma como costuma ser armazenado).
        """
        from core.models import Comprador
        try:
            cpf_formatado = (
                f'{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}'
                if len(cpf_digits) == 11 else cpf_digits
            )
            return (
                Comprador.objects.filter(cpf=cpf_digits).first()
                or Comprador.objects.filter(cpf=cpf_formatado).first()
            )
        except Exception:
            return None

    def _parcelas_abertas(self, comprador, vencidas_only=False):
        from financeiro.models import Parcela
        qs = Parcela.objects.filter(
            contrato__comprador=comprador,
            pago=False,
        ).select_related('contrato').order_by('data_vencimento')
        if vencidas_only:
            qs = qs.filter(data_vencimento__lt=_hoje())
        return list(qs[:5])

    # -------------------------------------------------------------------------
    # Helper de estado
    # -------------------------------------------------------------------------

    def _set_estado(self, sessao, estado, dados):
        sessao.estado = estado
        sessao.dados = dados
        sessao.save(update_fields=['estado', 'dados'])
