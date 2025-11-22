"""
Views do app Notificações

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import (
    Notificacao, TemplateNotificacao,
    ConfiguracaoEmail, ConfiguracaoSMS, ConfiguracaoWhatsApp
)


@login_required
def listar_notificacoes(request):
    """Lista todas as notificações"""
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
    """Exibe as configurações de notificações"""
    context = {
        'config_email': ConfiguracaoEmail.objects.filter(ativo=True).first(),
        'config_sms': ConfiguracaoSMS.objects.filter(ativo=True).first(),
        'config_whatsapp': ConfiguracaoWhatsApp.objects.filter(ativo=True).first(),
    }
    return render(request, 'notificacoes/configuracoes.html', context)


@login_required
def listar_templates(request):
    """Lista todos os templates de notificação"""
    templates = TemplateNotificacao.objects.all()

    context = {
        'templates': templates,
    }
    return render(request, 'notificacoes/templates.html', context)
