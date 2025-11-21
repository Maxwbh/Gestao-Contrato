"""
Views do app Core

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q
from datetime import datetime, timedelta
from .models import Contabilidade, Imobiliaria, Imovel, Comprador


def index(request):
    """Página inicial do sistema"""
    context = {
        'total_contabilidades': Contabilidade.objects.filter(ativo=True).count(),
        'total_imobiliarias': Imobiliaria.objects.filter(ativo=True).count(),
        'total_imoveis': Imovel.objects.filter(ativo=True).count(),
        'total_compradores': Comprador.objects.filter(ativo=True).count(),
    }
    return render(request, 'core/index.html', context)


@login_required
def dashboard(request):
    """Dashboard principal com estatísticas"""
    context = {
        'total_contabilidades': Contabilidade.objects.filter(ativo=True).count(),
        'total_imobiliarias': Imobiliaria.objects.filter(ativo=True).count(),
        'total_imoveis': Imovel.objects.filter(ativo=True).count(),
        'imoveis_disponiveis': Imovel.objects.filter(ativo=True, disponivel=True).count(),
        'total_compradores': Comprador.objects.filter(ativo=True).count(),
    }
    return render(request, 'core/dashboard.html', context)
