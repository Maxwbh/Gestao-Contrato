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
from django.http import JsonResponse
from django.db.models import Q
from .models import (
    Notificacao, TemplateNotificacao,
    ConfiguracaoEmail, ConfiguracaoSMS, ConfiguracaoWhatsApp
)
from .forms import ConfiguracaoEmailForm, TemplateNotificacaoForm


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

    context = {
        'notificacoes': notificacoes,
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

class ConfiguracaoEmailListView(LoginRequiredMixin, ListView):
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
        return JsonResponse({
            'status': 'error',
            'message': f'Erro na conexao: {str(e)}'
        }, status=400)


# =============================================================================
# CRUD VIEWS - TEMPLATE NOTIFICACAO (Mensagens de Email)
# =============================================================================

class TemplateNotificacaoListView(LoginRequiredMixin, ListView):
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

        tipo = self.request.GET.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo=tipo)

        codigo = self.request.GET.get('codigo')
        if codigo:
            queryset = queryset.filter(codigo=codigo)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_templates'] = TemplateNotificacao.objects.count()
        context['search'] = self.request.GET.get('search', '')
        context['tipo_selecionado'] = self.request.GET.get('tipo', '')
        context['codigo_selecionado'] = self.request.GET.get('codigo', '')

        # Para filtros
        from .models import TipoNotificacao, TipoTemplate
        context['tipos_notificacao'] = TipoNotificacao.choices
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
        tipo=template_original.tipo,
        imobiliaria=None,  # Template global por padrao
        assunto=template_original.assunto,
        corpo=template_original.corpo,
        corpo_html=template_original.corpo_html,
        ativo=False  # Inativo por padrao
    )

    messages.success(request, f'Template duplicado como "{template_novo.nome}"')
    return redirect('notificacoes:editar_template', pk=template_novo.pk)


@login_required
def preview_template(request, pk):
    """Visualiza preview do template com dados de exemplo"""
    template = get_object_or_404(TemplateNotificacao, pk=pk)

    # Dados de exemplo
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
        'DATAATUAL': '10/06/2024',
        'HORAATUAL': '14:30',
        'LINKBOLETO': 'https://sistema.com/boleto/12345',
    }

    assunto, corpo, corpo_html = template.renderizar(contexto_exemplo)

    return JsonResponse({
        'nome': template.nome,
        'tipo': template.get_tipo_display(),
        'assunto': assunto,
        'corpo': corpo,
        'corpo_html': corpo_html,
    })
