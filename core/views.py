"""
Views do app Core

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.management import call_command
from django.db.models import Count, Sum, Q
from datetime import datetime, timedelta
from .models import Contabilidade, Imobiliaria, Imovel, Comprador
import io


def index(request):
    """Página inicial do sistema"""
    try:
        context = {
            'total_contabilidades': Contabilidade.objects.filter(ativo=True).count(),
            'total_imobiliarias': Imobiliaria.objects.filter(ativo=True).count(),
            'total_imoveis': Imovel.objects.filter(ativo=True).count(),
            'total_compradores': Comprador.objects.filter(ativo=True).count(),
        }
    except Exception as e:
        # Se banco não está configurado, mostrar mensagem amigável
        context = {
            'erro': 'Banco de dados não configurado. Execute as migrations primeiro.',
            'total_contabilidades': 0,
            'total_imobiliarias': 0,
            'total_imoveis': 0,
            'total_compradores': 0,
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


@require_http_methods(["GET", "POST"])
def gerar_dados_teste(request):
    """
    Endpoint para gerar dados de teste

    GET: Retorna status do sistema
    POST: Gera dados de teste

    Parâmetros POST:
        limpar (bool): Se deve limpar dados antes (default: False)
    """
    if request.method == 'GET':
        # Retornar estatísticas atuais
        try:
            return JsonResponse({
                'status': 'ok',
                'dados_existentes': {
                    'contabilidades': Contabilidade.objects.count(),
                    'imobiliarias': Imobiliaria.objects.count(),
                    'imoveis': Imovel.objects.count(),
                    'compradores': Comprador.objects.count(),
                }
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': 'Banco de dados não configurado. Execute migrations primeiro.',
                'error': str(e)
            }, status=500)

    # POST - Gerar dados
    try:
        limpar = request.POST.get('limpar', 'false').lower() == 'true'

        # Capturar output do comando
        out = io.StringIO()

        # Executar comando
        call_command('gerar_dados_teste', limpar=limpar, stdout=out)

        output = out.getvalue()

        # Retornar sucesso
        return JsonResponse({
            'status': 'success',
            'message': 'Dados gerados com sucesso!',
            'output': output,
            'dados_gerados': {
                'contabilidades': Contabilidade.objects.count(),
                'imobiliarias': Imobiliaria.objects.count(),
                'imoveis': Imovel.objects.count(),
                'compradores': Comprador.objects.count(),
            }
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': 'Erro ao gerar dados',
            'error': str(e)
        }, status=500)
