"""
Views do app Core

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
from django.db import connection
from django.contrib.auth import get_user_model
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
        # Se banco não está configurado, redirecionar para setup
        return redirect('core:setup')
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


@csrf_exempt
def setup(request):
    """
    Página de setup inicial do sistema
    Executa migrations, cria superuser e opcionalmente gera dados de teste

    Acessível via: /setup/
    """
    if request.method == 'GET':
        # Verificar status do banco
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            db_ok = True

            # Verificar se tem tabelas
            tables = connection.introspection.table_names()
            has_tables = len(tables) > 0

            # Verificar se tem dados
            if has_tables:
                try:
                    total_contabilidades = Contabilidade.objects.count()
                    total_users = get_user_model().objects.count()
                except:
                    total_contabilidades = 0
                    total_users = 0
            else:
                total_contabilidades = 0
                total_users = 0

        except Exception as e:
            db_ok = False
            has_tables = False
            total_contabilidades = 0
            total_users = 0

        context = {
            'db_ok': db_ok,
            'has_tables': has_tables,
            'total_contabilidades': total_contabilidades,
            'total_users': total_users,
        }
        return render(request, 'core/setup.html', context)

    # POST - Executar setup
    try:
        action = request.POST.get('action', 'setup')
        out = io.StringIO()
        messages = []

        if action == 'migrations':
            # Executar migrations
            messages.append('Executando makemigrations...')
            call_command('makemigrations', stdout=out)
            messages.append('Executando migrate...')
            call_command('migrate', stdout=out)
            messages.append('✅ Migrations executadas com sucesso!')

        elif action == 'superuser':
            # Criar superuser
            User = get_user_model()
            if not User.objects.filter(username='admin').exists():
                User.objects.create_superuser('admin', 'admin@gestaocontrato.com', 'admin123')
                messages.append('✅ Superuser criado: admin / admin123')
            else:
                messages.append('⚠️ Superuser já existe')

        elif action == 'dados':
            # Gerar dados de teste
            limpar = request.POST.get('limpar') == 'true'
            messages.append('Gerando dados de teste...')
            call_command('gerar_dados_teste', limpar=limpar, stdout=out)
            messages.append('✅ Dados gerados com sucesso!')

        elif action == 'setup_completo':
            # Setup completo
            messages.append('🚀 Iniciando setup completo...')

            # 1. Migrations
            messages.append('📊 Executando migrations...')
            call_command('makemigrations', stdout=out)
            call_command('migrate', stdout=out)
            messages.append('✅ Migrations OK')

            # 2. Superuser
            User = get_user_model()
            if not User.objects.filter(username='admin').exists():
                User.objects.create_superuser('admin', 'admin@gestaocontrato.com', 'admin123')
                messages.append('✅ Superuser criado: admin / admin123')
            else:
                messages.append('✅ Superuser já existe')

            # 3. Dados de teste (opcional)
            gerar_dados = request.POST.get('gerar_dados') == 'true'
            if gerar_dados:
                messages.append('📋 Gerando dados de teste...')
                call_command('gerar_dados_teste', stdout=out)
                messages.append('✅ Dados de teste gerados!')

            messages.append('🎉 Setup completo finalizado!')

        output = out.getvalue()

        return JsonResponse({
            'status': 'success',
            'messages': messages,
            'output': output
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Erro no setup: {str(e)}'
        }, status=500)


@csrf_exempt
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
                'message': 'Banco de dados não configurado. Acesse /setup/ primeiro.',
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
