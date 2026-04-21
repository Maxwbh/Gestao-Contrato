"""
Views do app Notificacoes

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, HttpResponseNotAllowed
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from core.mixins import PaginacaoMixin
import logging

from .models import (
    Notificacao, TemplateNotificacao,
    ConfiguracaoEmail, ConfiguracaoSMS, ConfiguracaoWhatsApp,
    RegraNotificacao, TipoGatilho, TipoNotificacao, StatusNotificacao,
)
from .forms import ConfiguracaoEmailForm, ConfiguracaoWhatsAppForm, TemplateNotificacaoForm

logger = logging.getLogger(__name__)


@login_required
def listar_notificacoes(request):
    """Lista todas as notificacoes"""
    notificacoes = Notificacao.objects.select_related('parcela').all()

    # Filtros
    status = request.GET.get('status')
    if status:
        notificacoes = notificacoes.filter(status=status)

    tipo = request.GET.get('tipo')
    if tipo:
        notificacoes = notificacoes.filter(tipo=tipo)

    notificacoes = notificacoes.order_by('-data_agendamento')

    per_page = request.GET.get('per_page', '25')
    try:
        per_page = min(int(per_page), 100)
    except (ValueError, TypeError):
        per_page = 25

    paginator = Paginator(notificacoes, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'notificacoes': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': paginator.num_pages > 1,
    }
    return render(request, 'notificacoes/listar.html', context)


@login_required
def configuracoes(request):
    """Exibe as configuracoes de notificacoes"""
    context = {
        'config_email': ConfiguracaoEmail.objects.filter(ativo=True).first(),
        'config_sms': ConfiguracaoSMS.objects.filter(ativo=True).first(),
        'config_whatsapp': ConfiguracaoWhatsApp.objects.filter(ativo=True).first(),
    }
    return render(request, 'notificacoes/configuracoes.html', context)


# =============================================================================
# CRUD VIEWS - CONFIGURACAO EMAIL
# =============================================================================

class ConfiguracaoEmailListView(LoginRequiredMixin, PaginacaoMixin, ListView):
    """Lista todas as configuracoes de email"""
    model = ConfiguracaoEmail
    template_name = 'notificacoes/config_email_list.html'
    context_object_name = 'configuracoes'
    paginate_by = 20

    def get_queryset(self):
        queryset = ConfiguracaoEmail.objects.all().order_by('-ativo', '-criado_em')

        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(nome__icontains=search) |
                Q(host__icontains=search) |
                Q(email_remetente__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_configuracoes'] = ConfiguracaoEmail.objects.count()
        context['search'] = self.request.GET.get('search', '')
        return context


class ConfiguracaoEmailCreateView(LoginRequiredMixin, CreateView):
    """Cria uma nova configuracao de email"""
    model = ConfiguracaoEmail
    form_class = ConfiguracaoEmailForm
    template_name = 'notificacoes/config_email_form.html'
    success_url = reverse_lazy('notificacoes:listar_config_email')

    def form_valid(self, form):
        messages.success(self.request, f'Configuracao "{form.instance.nome}" criada com sucesso!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao criar configuracao. Verifique os dados.')
        return super().form_invalid(form)


class ConfiguracaoEmailUpdateView(LoginRequiredMixin, UpdateView):
    """Atualiza uma configuracao de email existente"""
    model = ConfiguracaoEmail
    form_class = ConfiguracaoEmailForm
    template_name = 'notificacoes/config_email_form.html'
    success_url = reverse_lazy('notificacoes:listar_config_email')

    def form_valid(self, form):
        # Se a senha estiver vazia, manter a anterior
        if not form.cleaned_data.get('senha'):
            form.instance.senha = ConfiguracaoEmail.objects.get(pk=self.object.pk).senha
        messages.success(self.request, f'Configuracao "{form.instance.nome}" atualizada com sucesso!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao atualizar configuracao. Verifique os dados.')
        return super().form_invalid(form)


class ConfiguracaoEmailDeleteView(LoginRequiredMixin, DeleteView):
    """Exclui uma configuracao de email"""
    model = ConfiguracaoEmail
    success_url = reverse_lazy('notificacoes:listar_config_email')
    template_name = 'notificacoes/config_email_confirm_delete.html'

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        nome = self.object.nome
        self.object.delete()
        messages.success(request, f'Configuracao "{nome}" excluida com sucesso!')
        return redirect(self.success_url)


@login_required
def testar_conexao_email(request, pk):
    """Testa a conexao com o servidor de email"""
    config = get_object_or_404(ConfiguracaoEmail, pk=pk)

    try:
        import smtplib
        from email.mime.text import MIMEText

        # Conectar ao servidor
        if config.usar_ssl:
            server = smtplib.SMTP_SSL(config.host, config.porta, timeout=10)
        else:
            server = smtplib.SMTP(config.host, config.porta, timeout=10)

        if config.usar_tls:
            server.starttls()

        # Autenticar
        server.login(config.usuario, config.senha)

        # Enviar email de teste
        msg = MIMEText('Este e um email de teste do Sistema de Gestao de Contratos.')
        msg['Subject'] = 'Teste de Conexao - Sistema de Gestao de Contratos'
        msg['From'] = f'{config.nome_remetente} <{config.email_remetente}>'
        msg['To'] = config.email_remetente

        server.sendmail(config.email_remetente, [config.email_remetente], msg.as_string())
        server.quit()

        return JsonResponse({
            'status': 'success',
            'message': f'Conexao bem sucedida! Email de teste enviado para {config.email_remetente}'
        })

    except Exception as e:
        logger.exception("Erro ao testar conexao email pk=%s: %s", pk, e)
        return JsonResponse({
            'status': 'error',
            'message': f'Erro na conexao: {str(e)}'
        }, status=400)


# =============================================================================
# CRUD VIEWS - CONFIGURACAO WHATSAPP
# =============================================================================

class ConfiguracaoWhatsAppListView(LoginRequiredMixin, PaginacaoMixin, ListView):
    model = ConfiguracaoWhatsApp
    template_name = 'notificacoes/config_whatsapp_list.html'
    context_object_name = 'configuracoes'
    paginate_by = 20

    def get_queryset(self):
        queryset = ConfiguracaoWhatsApp.objects.all().order_by('-ativo', '-criado_em')
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(nome__icontains=search) |
                Q(instancia__icontains=search) |
                Q(api_url__icontains=search)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_configuracoes'] = ConfiguracaoWhatsApp.objects.count()
        context['search'] = self.request.GET.get('search', '')
        return context


class ConfiguracaoWhatsAppCreateView(LoginRequiredMixin, CreateView):
    model = ConfiguracaoWhatsApp
    form_class = ConfiguracaoWhatsAppForm
    template_name = 'notificacoes/config_whatsapp_form.html'
    success_url = reverse_lazy('notificacoes:listar_config_whatsapp')

    def form_valid(self, form):
        messages.success(self.request, f'Configuracao "{form.instance.nome}" criada com sucesso!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao criar configuracao. Verifique os dados.')
        return super().form_invalid(form)


class ConfiguracaoWhatsAppUpdateView(LoginRequiredMixin, UpdateView):
    model = ConfiguracaoWhatsApp
    form_class = ConfiguracaoWhatsAppForm
    template_name = 'notificacoes/config_whatsapp_form.html'
    success_url = reverse_lazy('notificacoes:listar_config_whatsapp')

    def form_valid(self, form):
        if not form.cleaned_data.get('auth_token'):
            form.instance.auth_token = ConfiguracaoWhatsApp.objects.get(pk=self.object.pk).auth_token
        messages.success(self.request, f'Configuracao "{form.instance.nome}" atualizada com sucesso!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao atualizar configuracao. Verifique os dados.')
        return super().form_invalid(form)


class ConfiguracaoWhatsAppDeleteView(LoginRequiredMixin, DeleteView):
    model = ConfiguracaoWhatsApp
    success_url = reverse_lazy('notificacoes:listar_config_whatsapp')
    template_name = 'notificacoes/config_whatsapp_confirm_delete.html'

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        nome = self.object.nome
        self.object.delete()
        messages.success(request, f'Configuracao "{nome}" excluida com sucesso!')
        return redirect(self.success_url)


@login_required
def testar_conexao_whatsapp(request, pk):
    """Testa a conexao com o provedor WhatsApp configurado."""
    config = get_object_or_404(ConfiguracaoWhatsApp, pk=pk)

    try:
        provedor = config.provedor

        if provedor == 'EVOLUTION':
            import urllib.request as _req
            import json as _json
            url = f"{config.api_url.rstrip('/')}/instance/connectionState/{config.instancia}"
            req = _req.Request(url, headers={'apikey': config.api_key})
            with _req.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read())
            state = data.get('instance', {}).get('state', '') or data.get('state', '')
            if state == 'open':
                return JsonResponse({'status': 'success',
                                     'message': f'Instancia "{config.instancia}" conectada (state: open)'})
            return JsonResponse({'status': 'error',
                                 'message': f'Instancia nao conectada (state: {state})'}, status=400)

        elif provedor == 'ZAPI':
            import urllib.request as _req
            import json as _json
            base = config.api_url.rstrip('/')
            url = f"{base}/instances/{config.instancia}/token/{config.api_key}/status"
            headers = {'Content-Type': 'application/json'}
            if config.client_token:
                headers['Client-Token'] = config.client_token
            req = _req.Request(url, headers=headers)
            with _req.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read())
            connected = data.get('connected', False)
            if connected:
                return JsonResponse({'status': 'success', 'message': 'Z-API conectada com sucesso'})
            return JsonResponse({'status': 'error', 'message': f'Z-API nao conectada: {data}'}, status=400)

        elif provedor == 'TWILIO':
            from twilio.rest import Client as TwilioClient
            client = TwilioClient(config.account_sid, config.auth_token)
            account = client.api.accounts(config.account_sid).fetch()
            return JsonResponse({'status': 'success', 'message': f'Twilio OK — conta: {account.friendly_name}'})

        else:
            return JsonResponse(
                {'status': 'error', 'message': f'Teste nao disponivel para provedor {provedor}'}, status=400
            )

    except Exception as e:
        logger.exception("Erro ao testar conexao whatsapp pk=%s: %s", pk, e)
        return JsonResponse({'status': 'error', 'message': f'Erro: {str(e)}'}, status=400)


@login_required
def configurar_webhook_evolution(request, pk):
    """
    Registra o webhook de delivery tracking na instância Evolution API.
    Chama POST {api_url}/webhook/set/{instancia} com a URL do sistema.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Metodo nao permitido'}, status=405)

    config = get_object_or_404(ConfiguracaoWhatsApp, pk=pk)
    if config.provedor != 'EVOLUTION':
        return JsonResponse({'status': 'error', 'message': 'Apenas Evolution API suportado'}, status=400)

    try:
        import urllib.request as _req
        import json as _json
        from django.conf import settings as _s

        site_url = getattr(_s, 'SITE_URL', request.build_absolute_uri('/').rstrip('/'))
        webhook_url = f"{site_url}/notificacoes/webhook/evolution/"

        payload = {
            'url': webhook_url,
            'enabled': True,
            'webhookByEvents': False,
            'webhookBase64': False,
            # MESSAGES_UPDATE: status delivery/read
            # MESSAGES_UPSERT: captura fromMe ao enviar (status inicial PENDING→sent)
            'events': ['MESSAGES_UPDATE', 'MESSAGES_UPSERT'],
        }
        url = f"{config.api_url.rstrip('/')}/webhook/set/{config.instancia}"
        req = _req.Request(
            url,
            data=_json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json', 'apikey': config.api_key},
            method='POST',
        )
        with _req.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read())

        logger.info('[Evolution Webhook] Configurado para instancia=%s url=%s resp=%s',
                    config.instancia, webhook_url, data)
        return JsonResponse({
            'status': 'success',
            'message': f'Webhook configurado com sucesso → {webhook_url}',
            'webhook_url': webhook_url,
        })

    except Exception as e:
        logger.exception("Erro ao configurar webhook evolution pk=%s: %s", pk, e)
        return JsonResponse({'status': 'error', 'message': f'Erro: {str(e)}'}, status=400)


# =============================================================================
# WEBHOOK EVOLUTION API — Confirmação de entrega WhatsApp
# =============================================================================

# Mapeamento de status Evolution/Baileys → StatusEntrega
_EVOLUTION_STATUS_MAP = {
    # String values (Evolution API v2)
    'PENDING': 'queued',
    'SERVER_ACK': 'sent',
    'DELIVERY_ACK': 'delivered',
    'READ': 'read',
    'PLAYED': 'read',
    # Numeric values (Baileys proto.WebMessageInfo.Status)
    0: 'queued',     # ERROR/PENDING
    1: 'queued',     # PENDING
    2: 'sent',       # SERVER_ACK
    3: 'delivered',  # DELIVERY_ACK
    4: 'read',       # READ
    5: 'read',       # PLAYED
    '0': 'queued',
    '1': 'queued',
    '2': 'sent',
    '3': 'delivered',
    '4': 'read',
    '5': 'read',
}


@csrf_exempt
def webhook_evolution(request):
    """
    Recebe callbacks de status de entrega da Evolution API (MESSAGES_UPDATE).

    Evolution posta para esta URL (configurada via /webhook/set/{instance})
    quando o status de uma mensagem muda.

    Payload esperado:
    {
      "event": "messages.update",
      "instance": "nome-instancia",
      "data": [
        {
          "key": {"id": "3EB0...", "fromMe": true, "remoteJid": "55...@s.whatsapp.net"},
          "update": {"status": "READ"}
        }
      ]
    }

    Valida apikey recebida no header ou no payload contra ConfiguracaoWhatsApp.
    Atualiza Notificacao.status_entrega e Notificacao.data_confirmacao.
    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    try:
        import json as _json
        body = _json.loads(request.body)
    except Exception:
        return HttpResponse('Bad Request', status=400)

    event = body.get('event', '')
    instance_name = body.get('instance', '')

    # Validar apikey: header ou campo no payload
    apikey_header = request.META.get('HTTP_APIKEY', '')
    apikey_payload = body.get('apikey', '')
    apikey = apikey_header or apikey_payload

    if apikey:
        config = ConfiguracaoWhatsApp.objects.filter(
            provedor='EVOLUTION', instancia=instance_name, api_key=apikey, ativo=True
        ).first()
        if not config:
            logger.warning(
                '[Webhook Evolution] apikey invalida — instance=%s ip=%s',
                instance_name, request.META.get('REMOTE_ADDR')
            )
            return HttpResponse('Forbidden', status=403)
    else:
        # Sem apikey: aceitar mas logar aviso (Evolution pode não enviar em algumas versões)
        logger.warning('[Webhook Evolution] Payload sem apikey — instance=%s', instance_name)

    is_update = event in ('messages.update', 'MESSAGES_UPDATE')
    is_upsert = event in ('messages.upsert', 'MESSAGES_UPSERT')

    if not (is_update or is_upsert):
        return HttpResponse('OK', status=200)

    data_list = body.get('data', [])
    if not isinstance(data_list, list):
        data_list = [data_list]

    updated_total = 0
    for item in data_list:
        key = item.get('key', {})
        message_id = key.get('id', '').strip()
        from_me = key.get('fromMe', False)

        if not from_me or not message_id:
            continue

        if is_update:
            # MESSAGES_UPDATE: status mudou (SERVER_ACK, DELIVERY_ACK, READ, PLAYED)
            update = item.get('update', {})
            raw_status = update.get('status', '')
            status_entrega = _EVOLUTION_STATUS_MAP.get(raw_status)
            if not status_entrega:
                continue
        else:
            # MESSAGES_UPSERT: mensagem recém-enviada — captura status inicial
            raw_status = item.get('status', item.get('messageStatus', ''))
            status_entrega = _EVOLUTION_STATUS_MAP.get(raw_status, 'queued')

        updated = Notificacao.objects.filter(external_id=message_id).update(
            status_entrega=status_entrega,
            data_confirmacao=timezone.now(),
        )
        updated_total += updated

    logger.info(
        '[Webhook Evolution] event=%s instance=%s itens=%d atualizados=%d',
        event, instance_name, len(data_list), updated_total
    )
    return HttpResponse('OK', status=200)


# =============================================================================
# CRUD VIEWS - TEMPLATE NOTIFICACAO (Mensagens de Email)
# =============================================================================

class TemplateNotificacaoListView(LoginRequiredMixin, PaginacaoMixin, ListView):
    """Lista todos os templates de notificacao"""
    model = TemplateNotificacao
    template_name = 'notificacoes/template_list.html'
    context_object_name = 'templates'
    paginate_by = 20

    def get_queryset(self):
        queryset = TemplateNotificacao.objects.select_related('imobiliaria').all().order_by('codigo', 'nome')

        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(nome__icontains=search) |
                Q(assunto__icontains=search) |
                Q(corpo__icontains=search)
            )

        codigo = self.request.GET.get('codigo')
        if codigo:
            queryset = queryset.filter(codigo=codigo)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_templates'] = TemplateNotificacao.objects.count()
        context['search'] = self.request.GET.get('search', '')
        context['codigo_selecionado'] = self.request.GET.get('codigo', '')

        # Para filtros
        from .models import TipoTemplate
        context['tipos_template'] = TipoTemplate.choices
        return context


class TemplateNotificacaoCreateView(LoginRequiredMixin, CreateView):
    """Cria um novo template de notificacao"""
    model = TemplateNotificacao
    form_class = TemplateNotificacaoForm
    template_name = 'notificacoes/template_form.html'
    success_url = reverse_lazy('notificacoes:listar_templates')

    def form_valid(self, form):
        messages.success(self.request, f'Template "{form.instance.nome}" criado com sucesso!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao criar template. Verifique os dados.')
        return super().form_invalid(form)


class TemplateNotificacaoUpdateView(LoginRequiredMixin, UpdateView):
    """Atualiza um template de notificacao existente"""
    model = TemplateNotificacao
    form_class = TemplateNotificacaoForm
    template_name = 'notificacoes/template_form.html'
    success_url = reverse_lazy('notificacoes:listar_templates')

    def form_valid(self, form):
        messages.success(self.request, f'Template "{form.instance.nome}" atualizado com sucesso!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao atualizar template. Verifique os dados.')
        return super().form_invalid(form)


class TemplateNotificacaoDeleteView(LoginRequiredMixin, DeleteView):
    """Exclui um template de notificacao"""
    model = TemplateNotificacao
    success_url = reverse_lazy('notificacoes:listar_templates')
    template_name = 'notificacoes/template_confirm_delete.html'

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        nome = self.object.nome
        self.object.delete()
        messages.success(request, f'Template "{nome}" excluido com sucesso!')
        return redirect(self.success_url)


@login_required
def duplicar_template(request, pk):
    """Duplica um template existente"""
    template_original = get_object_or_404(TemplateNotificacao, pk=pk)

    # Criar copia
    template_novo = TemplateNotificacao.objects.create(
        nome=f'{template_original.nome} (Copia)',
        codigo=template_original.codigo,
        imobiliaria=None,  # Template global por padrao
        assunto=template_original.assunto,
        corpo=template_original.corpo,
        corpo_html=template_original.corpo_html,
        corpo_whatsapp=template_original.corpo_whatsapp,
        ativo=False  # Inativo por padrao
    )

    messages.success(request, f'Template duplicado como "{template_novo.nome}"')
    return redirect('notificacoes:editar_template', pk=template_novo.pk)


@login_required
def preview_template(request, pk):
    """Visualiza preview do template com dados de exemplo"""
    template = get_object_or_404(TemplateNotificacao, pk=pk)

    from django.utils import timezone
    from notificacoes.models import TipoTemplate
    hoje_str = timezone.localdate().strftime('%d/%m/%Y')

    # Dados de exemplo — base (boleto/parcela)
    contexto_exemplo = {
        'NOMECOMPRADOR': 'Joao da Silva',
        'CPFCOMPRADOR': '123.456.789-00',
        'CNPJCOMPRADOR': '12.345.678/0001-00',
        'EMAILCOMPRADOR': 'joao@exemplo.com',
        'TELEFONECOMPRADOR': '(11) 3333-4444',
        'CELULARCOMPRADOR': '(11) 99999-8888',
        'ENDERECOCOMPRADOR': 'Rua das Flores, 123 - Centro - Sao Paulo/SP',
        'NOMEIMOBILIARIA': 'Imobiliaria Exemplo',
        'CNPJIMOBILIARIA': '98.765.432/0001-00',
        'TELEFONEIMOBILIARIA': '(11) 2222-3333',
        'EMAILIMOBILIARIA': 'contato@imobiliaria.com',
        'NUMEROCONTRATO': 'CTR-2024-0001',
        'DATACONTRATO': '01/01/2024',
        'VALORTOTAL': 'R$ 150.000,00',
        'TOTALPARCELAS': '120',
        'IMOVEL': 'Lote 15, Quadra 3',
        'LOTEAMENTO': 'Residencial Primavera',
        'ENDERECOIMOVEL': 'Rua das Acaias, Lote 15 - Zona Rural',
        'PARCELA': '5/120',
        'NUMEROPARCELA': '5',
        'VALORPARCELA': 'R$ 1.250,00',
        'DATAVENCIMENTO': '15/06/2024',
        'DIASATRASO': '10',
        'VALORJUROS': 'R$ 12,50',
        'VALORMULTA': 'R$ 25,00',
        'VALORTOTALPARCELA': 'R$ 1.287,50',
        'NOSSONUMERO': '12345678901',
        'LINHADIGITAVEL': '23793.38128 60000.000003 12345.678901 1 92350000125000',
        'CODIGOBARRAS': '23791923500001250003381286000000001234567890',
        'STATUSBOLETO': 'Registrado',
        'VALORBOLETO': 'R$ 1.287,50',
        'DATAATUAL': hoje_str,
        'HORAATUAL': '14:30',
        'LINKBOLETO': 'https://sistema.com/boleto/12345',
    }

    # Dados adicionais para relatórios
    if template.codigo == TipoTemplate.RELATORIO_SEMANAL:
        contexto_exemplo.update({
            'PERIODORELATORIO': '14/04/2025 a 20/04/2025',
            'QTDRECEBIMENTOS': '18',
            'VALORRECEBIMENTOS': 'R$ 22.500,00',
            'QTDINADIMPLENTES': '5',
            'VALORINADIMPLENTES': 'R$ 6.250,00',
            'QTDAVENCER': '12',
            'VALORAVENCER': 'R$ 15.000,00',
        })
    elif template.codigo == TipoTemplate.RELATORIO_MENSAL:
        tabela_exemplo = (
            '<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%;">'
            '<thead><tr style="background:#f0f0f0;">'
            '<th>Imobiliária</th><th>Contratos Ativos</th>'
            '<th>Recebimentos</th><th>Valor Recebido</th>'
            '<th>Inadimplentes</th><th>Valor Inadimplente</th>'
            '<th>Reajustes</th></tr></thead><tbody>'
            '<tr><td>Imobiliária Exemplo</td><td>45</td><td>32</td>'
            '<td>R$ 40.000,00</td><td>3</td><td>R$ 3.750,00</td><td>5</td></tr>'
            '</tbody></table>'
        )
        contexto_exemplo.update({
            'NOMECONTABILIDADE': 'Contabilidade Exemplo Ltda',
            'MESREFERENCIA': 'março/2025',
            'PERIODORELATORIO': '01/03/2025 a 31/03/2025',
            'QTDCONTRATOSATIVOS': '45',
            'QTDRECEBIMENTOS': '32',
            'VALORRECEBIMENTOS': 'R$ 40.000,00',
            'QTDINADIMPLENTES': '3',
            'VALORINADIMPLENTES': 'R$ 3.750,00',
            'QTDREAJUSTES': '5',
            'TABELAIMOBILIARIAS': tabela_exemplo,
        })

    assunto, corpo, corpo_html, corpo_whatsapp = template.renderizar(contexto_exemplo)

    return JsonResponse({
        'nome': template.nome,
        'tem_email': template.tem_email,
        'tem_sms': template.tem_sms,
        'tem_whatsapp': template.tem_whatsapp,
        'assunto': assunto,
        'corpo': corpo,
        'corpo_html': corpo_html,
        'corpo_whatsapp': corpo_whatsapp,
    })


# ==========================================================================
# 3.27 — Configurações de Notificação: Régua (RegraNotificacao) CRUD
# ==========================================================================

@login_required
def listar_regras_notificacao(request):
    """Lista e gerencia as regras de notificação (régua de cobrança)."""
    regras = RegraNotificacao.objects.select_related('template').order_by('tipo_gatilho', 'dias_offset')
    templates = TemplateNotificacao.objects.all().order_by('nome')

    context = {
        'regras': regras,
        'templates': templates,
        'tipos_gatilho': TipoGatilho.choices,
        'tipos_notificacao': TipoNotificacao.choices,
    }
    return render(request, 'notificacoes/regras_notificacao.html', context)


@login_required
def criar_regra_notificacao(request):
    """Cria uma nova regra de notificação."""
    if request.method != 'POST':
        return redirect('notificacoes:listar_regras')

    nome = request.POST.get('nome', '').strip()
    tipo_gatilho = request.POST.get('tipo_gatilho', '')
    dias_offset = request.POST.get('dias_offset', '0')
    tipo_notificacao = request.POST.get('tipo_notificacao', TipoNotificacao.EMAIL)
    template_id = request.POST.get('template') or None
    ativo = request.POST.get('ativo') == 'on'

    try:
        dias_offset = int(dias_offset)
    except (ValueError, TypeError):
        dias_offset = 0

    try:
        template = TemplateNotificacao.objects.get(pk=template_id) if template_id else None
        regra = RegraNotificacao.objects.create(
            nome=nome,
            tipo_gatilho=tipo_gatilho,
            dias_offset=dias_offset,
            tipo_notificacao=tipo_notificacao,
            template=template,
            ativo=ativo,
        )
        messages.success(request, f'Regra "{regra.nome}" criada com sucesso.')
    except Exception as e:
        messages.error(request, f'Erro ao criar regra: {e}')

    return redirect('notificacoes:listar_regras')


@login_required
def editar_regra_notificacao(request, pk):
    """Edita uma regra de notificação existente."""
    regra = get_object_or_404(RegraNotificacao, pk=pk)

    if request.method != 'POST':
        return redirect('notificacoes:listar_regras')

    regra.nome = request.POST.get('nome', regra.nome).strip()
    regra.tipo_gatilho = request.POST.get('tipo_gatilho', regra.tipo_gatilho)
    try:
        regra.dias_offset = int(request.POST.get('dias_offset', regra.dias_offset))
    except (ValueError, TypeError):
        pass
    regra.tipo_notificacao = request.POST.get('tipo_notificacao', regra.tipo_notificacao)
    template_id = request.POST.get('template') or None
    regra.template = TemplateNotificacao.objects.filter(pk=template_id).first() if template_id else None
    regra.ativo = request.POST.get('ativo') == 'on'

    try:
        regra.save()
        messages.success(request, f'Regra "{regra.nome}" atualizada.')
    except Exception as e:
        messages.error(request, f'Erro ao atualizar: {e}')

    return redirect('notificacoes:listar_regras')


@login_required
def excluir_regra_notificacao(request, pk):
    """Exclui uma regra de notificação."""
    regra = get_object_or_404(RegraNotificacao, pk=pk)
    if request.method == 'POST':
        nome = regra.nome
        regra.delete()
        messages.success(request, f'Regra "{nome}" excluída.')
    return redirect('notificacoes:listar_regras')


@login_required
def toggle_regra_notificacao(request, pk):
    """Ativa/desativa uma regra via AJAX (POST)."""
    regra = get_object_or_404(RegraNotificacao, pk=pk)
    if request.method == 'POST':
        regra.ativo = not regra.ativo
        regra.save(update_fields=['ativo'])
        return JsonResponse({'sucesso': True, 'ativo': regra.ativo})
    return JsonResponse({'sucesso': False}, status=405)


# =============================================================================
# PAINEL DE CONTROLE DE MENSAGENS
# =============================================================================

# Mapeamento de status de entrega Twilio → label PT-BR
_STATUS_ENTREGA_LABELS = {
    'accepted': 'Aceito',
    'queued': 'Enfileirado',
    'sending': 'Enviando',
    'sent': 'Enviado',
    'delivered': 'Entregue',
    'undelivered': 'Não entregue',
    'failed': 'Falhou',
    'read': 'Lido',
}

_STATUS_ENTREGA_CHOICES = [
    # Twilio SMS/WhatsApp
    ('accepted', 'Aceito'),
    ('queued', 'Enfileirado'),
    ('sending', 'Enviando'),
    ('sent', 'Enviado'),
    ('delivered', 'Entregue'),
    ('undelivered', 'Não entregue'),
    ('failed', 'Falhou'),
    ('read', 'Lido'),
    # E-mail — rastreamento local
    ('clicked', 'Clicado (link)'),
    ('bounced', 'Bounce (NDR)'),
    ('opened', 'Aberto (pixel)'),
]


@login_required
def painel_mensagens(request):
    """
    Painel de controle de mensagens: histórico completo com status de envio
    e confirmação de entrega (SMS/WhatsApp via Twilio webhook; e-mail via Message-ID).
    """
    qs = Notificacao.objects.select_related('parcela').all()

    # --- Filtros ---
    f_tipo = request.GET.get('tipo', '').strip()
    f_status = request.GET.get('status', '').strip()
    f_status_entrega = request.GET.get('status_entrega', '').strip()
    f_data_inicio = request.GET.get('data_inicio', '').strip()
    f_data_fim = request.GET.get('data_fim', '').strip()
    f_busca = request.GET.get('busca', '').strip()

    if f_tipo:
        qs = qs.filter(tipo=f_tipo)
    if f_status:
        qs = qs.filter(status=f_status)
    if f_status_entrega:
        qs = qs.filter(status_entrega=f_status_entrega)
    if f_data_inicio:
        try:
            qs = qs.filter(data_agendamento__date__gte=f_data_inicio)
        except Exception:
            pass
    if f_data_fim:
        try:
            qs = qs.filter(data_agendamento__date__lte=f_data_fim)
        except Exception:
            pass
    if f_busca:
        qs = qs.filter(
            Q(destinatario__icontains=f_busca) |
            Q(assunto__icontains=f_busca) |
            Q(external_id__icontains=f_busca)
        )

    qs = qs.order_by('-data_agendamento')

    # --- Agregações (sobre o queryset filtrado) ---
    stats_status = {}
    for row in qs.values('status').annotate(c=Count('id')):
        stats_status[row['status']] = row['c']

    stats_tipo = {}
    for row in qs.values('tipo').annotate(c=Count('id')):
        stats_tipo[row['tipo']] = row['c']

    stats_entrega = {}
    for row in qs.exclude(status_entrega='').values('status_entrega').annotate(c=Count('id')):
        stats_entrega[row['status_entrega']] = row['c']

    total = qs.count()
    total_entregues = stats_entrega.get('delivered', 0) + stats_entrega.get('read', 0)
    total_falhos = stats_entrega.get('failed', 0) + stats_entrega.get('undelivered', 0)
    total_sem_confirmacao = qs.filter(
        status=StatusNotificacao.ENVIADA,
        status_entrega=''
    ).count()

    # --- Paginação ---
    per_page = request.GET.get('per_page', '25')
    try:
        per_page = min(int(per_page), 100)
    except (ValueError, TypeError):
        per_page = 25

    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'notificacoes': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': paginator.num_pages > 1,
        'total': total,
        'total_entregues': total_entregues,
        'total_falhos': total_falhos,
        'total_sem_confirmacao': total_sem_confirmacao,
        'stats_status': stats_status,
        'stats_tipo': stats_tipo,
        'stats_entrega': stats_entrega,
        'status_entrega_labels': _STATUS_ENTREGA_LABELS,
        # Filtros para manter na forma
        'f_tipo': f_tipo,
        'f_status': f_status,
        'f_status_entrega': f_status_entrega,
        'f_data_inicio': f_data_inicio,
        'f_data_fim': f_data_fim,
        'f_busca': f_busca,
        'tipos_notificacao': TipoNotificacao.choices,
        'status_notificacao_choices': StatusNotificacao.choices,
        'status_entrega_choices': _STATUS_ENTREGA_CHOICES,
    }
    return render(request, 'notificacoes/painel_mensagens.html', context)


@login_required
def reenviar_notificacao_ajax(request, pk):
    """
    Recoloca a notificação como PENDENTE e enfileira reenvio via Celery (AJAX POST).
    Limpa external_id e status_entrega anteriores.
    """
    if request.method != 'POST':
        return JsonResponse({'sucesso': False, 'erro': 'Método não permitido'}, status=405)

    notificacao = get_object_or_404(Notificacao, pk=pk)

    notificacao.status = StatusNotificacao.PENDENTE
    notificacao.erro_mensagem = ''
    notificacao.external_id = ''
    notificacao.status_entrega = ''
    notificacao.data_confirmacao = None
    notificacao.save(update_fields=[
        'status', 'erro_mensagem', 'external_id', 'status_entrega', 'data_confirmacao'
    ])

    from .tasks import reenviar_notificacao as _task
    _task.delay(pk)

    logger.info("[Painel] Reenvio enfileirado para notificacao pk=%s", pk)
    return JsonResponse({'sucesso': True})


# =============================================================================
# WEBHOOK TWILIO — Confirmação de entrega SMS / WhatsApp
# =============================================================================

def _get_twilio_auth_token():
    """Retorna o Twilio auth_token do banco ou das settings."""
    config_sms = ConfiguracaoSMS.objects.filter(ativo=True, provedor='TWILIO').first()
    if config_sms and config_sms.auth_token:
        return config_sms.auth_token

    config_wa = ConfiguracaoWhatsApp.objects.filter(ativo=True, provedor='TWILIO').first()
    if config_wa and config_wa.auth_token:
        return config_wa.auth_token

    from django.conf import settings as _s
    return getattr(_s, 'TWILIO_AUTH_TOKEN', '')


def track_click(request, token):
    """
    Registra o clique no link do boleto e redireciona para o download.

    URL: /notificacoes/track/<uuid>/click/
    Sem autenticação — acessado pelo destinatário do e-mail.

    O destino é reconstruído a partir da parcela vinculada à notificação,
    eliminando qualquer risco de open-redirect por parâmetro de URL.
    """
    from django.conf import settings as _s
    from django.shortcuts import redirect as _redirect

    message_id = f"<{token}@gestao-contrato>"

    # Atualizar status da notificação
    Notificacao.objects.filter(external_id=message_id).update(
        status_entrega='clicked',
        data_confirmacao=timezone.now(),
    )
    logger.info('[ClickTracking] token=%s message_id=%s', token, message_id)

    # Destino: URL de download do boleto (reconstruído a partir da parcela)
    # Procura a notificação para obter a parcela
    notificacao = Notificacao.objects.filter(external_id=message_id).select_related('parcela').first()
    if notificacao and notificacao.parcela_id:
        site_url = getattr(_s, 'SITE_URL', '').rstrip('/')
        destino = f"{site_url}/financeiro/parcelas/{notificacao.parcela_id}/boleto/download/"
    else:
        destino = getattr(_s, 'SITE_URL', '') or '/'

    return _redirect(destino)


@csrf_exempt
def webhook_twilio(request):
    """
    Recebe callbacks de status de entrega do Twilio (SMS e WhatsApp).

    Twilio posta para esta URL (configurada em TWILIO_STATUS_CALLBACK_URL ou
    diretamente no console Twilio) quando o status de uma mensagem muda.
    Campos recebidos: MessageSid, MessageStatus, To, From, AccountSid.

    Valida a assinatura X-Twilio-Signature antes de processar.
    Atualiza Notificacao.status_entrega e Notificacao.data_confirmacao.
    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    # Validar assinatura Twilio
    auth_token = _get_twilio_auth_token()
    if auth_token:
        try:
            from twilio.request_validator import RequestValidator
            validator = RequestValidator(auth_token)
            url = request.build_absolute_uri()
            signature = request.META.get('HTTP_X_TWILIO_SIGNATURE', '')
            if not validator.validate(url, request.POST, signature):
                logger.warning(
                    '[Webhook Twilio] Assinatura inválida — ip=%s url=%s',
                    request.META.get('REMOTE_ADDR'), url
                )
                return HttpResponse('Forbidden', status=403)
        except ImportError:
            logger.warning('[Webhook Twilio] twilio.request_validator não disponível — ignorando validação')
        except Exception as exc:
            logger.warning('[Webhook Twilio] Erro na validação de assinatura: %s', exc)
            return HttpResponse('Forbidden', status=403)

    message_sid = request.POST.get('MessageSid', '').strip()
    message_status = request.POST.get('MessageStatus', '').strip()

    if not message_sid or not message_status:
        return HttpResponse('Bad Request', status=400)

    updated = Notificacao.objects.filter(external_id=message_sid).update(
        status_entrega=message_status,
        data_confirmacao=timezone.now(),
    )

    logger.info(
        '[Webhook Twilio] SID=%s status=%s registros_atualizados=%d',
        message_sid, message_status, updated
    )
    return HttpResponse('OK', status=200)
