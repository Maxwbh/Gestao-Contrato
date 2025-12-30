"""
Views do Portal do Comprador

Funcionalidades:
- Auto-cadastro por CPF/CNPJ
- Login/Logout
- Dashboard com contratos
- Visualização de boletos (pagos e a pagar)
- Atualização de dados pessoais
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.db.models import Sum, Count, Q
from decimal import Decimal
from datetime import timedelta
import re

from core.models import Comprador
from contratos.models import Contrato
from financeiro.models import Parcela

from .models import AcessoComprador, LogAcessoComprador
from .forms import (
    AutoCadastroForm, LoginCompradorForm,
    DadosPessoaisForm, AlterarSenhaCompradorForm
)


def get_client_ip(request):
    """Obtém o IP do cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def registrar_log_acesso(request, acesso_comprador, pagina=''):
    """Registra um log de acesso"""
    LogAcessoComprador.objects.create(
        acesso_comprador=acesso_comprador,
        ip_acesso=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        pagina_acessada=pagina
    )


def get_comprador_from_request(request):
    """Obtém o comprador do usuário logado"""
    if not request.user.is_authenticated:
        return None
    try:
        return request.user.acesso_comprador.comprador
    except (AttributeError, AcessoComprador.DoesNotExist):
        return None


# =============================================================================
# AUTENTICAÇÃO
# =============================================================================

def auto_cadastro(request):
    """
    View para auto-cadastro do comprador.

    O comprador informa CPF/CNPJ e e-mail para criar uma conta.
    """
    if request.user.is_authenticated:
        if hasattr(request.user, 'acesso_comprador'):
            return redirect('portal_comprador:dashboard')
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = AutoCadastroForm(request.POST)
        if form.is_valid():
            comprador = form.cleaned_data['comprador']
            documento = form.cleaned_data['documento']
            senha = form.cleaned_data['senha']

            # Criar usuário
            username = f'comprador_{documento}'
            user = User.objects.create_user(
                username=username,
                email=comprador.email,
                password=senha,
                first_name=comprador.nome.split()[0] if comprador.nome else '',
                last_name=' '.join(comprador.nome.split()[1:]) if comprador.nome else ''
            )

            # Criar acesso do comprador
            acesso = AcessoComprador.objects.create(
                comprador=comprador,
                usuario=user
            )

            # Fazer login
            login(request, user)

            # Registrar log de acesso
            registrar_log_acesso(request, acesso, 'auto_cadastro')

            messages.success(request, f'Bem-vindo ao Portal do Comprador, {comprador.nome}!')
            return redirect('portal_comprador:dashboard')
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = AutoCadastroForm()

    return render(request, 'portal_comprador/auto_cadastro.html', {'form': form})


def login_comprador(request):
    """
    View de login do comprador.
    """
    if request.user.is_authenticated:
        if hasattr(request.user, 'acesso_comprador'):
            return redirect('portal_comprador:dashboard')
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = LoginCompradorForm(request.POST)
        if form.is_valid():
            documento = form.cleaned_data['documento']
            senha = form.cleaned_data['senha']

            # Buscar usuário pelo documento
            username = f'comprador_{documento}'
            user = authenticate(request, username=username, password=senha)

            if user is not None:
                login(request, user)

                # Registrar acesso
                if hasattr(user, 'acesso_comprador'):
                    acesso = user.acesso_comprador
                    acesso.registrar_acesso()
                    registrar_log_acesso(request, acesso, 'login')

                messages.success(request, f'Bem-vindo de volta!')
                return redirect('portal_comprador:dashboard')
            else:
                messages.error(request, 'CPF/CNPJ ou senha inválidos.')
    else:
        form = LoginCompradorForm()

    return render(request, 'portal_comprador/login.html', {'form': form})


def logout_comprador(request):
    """View de logout do comprador"""
    logout(request)
    messages.info(request, 'Você saiu do portal.')
    return redirect('portal_comprador:login')


# =============================================================================
# DASHBOARD
# =============================================================================

@login_required(login_url='portal_comprador:login')
def dashboard(request):
    """
    Dashboard do comprador.

    Mostra:
    - Resumo dos contratos
    - Próximas parcelas a vencer
    - Parcelas em atraso
    - Dados do comprador
    """
    comprador = get_comprador_from_request(request)
    if not comprador:
        messages.error(request, 'Acesso não autorizado.')
        return redirect('portal_comprador:login')

    hoje = timezone.now().date()

    # Contratos do comprador
    contratos = Contrato.objects.filter(
        comprador=comprador,
        status='ATIVO'
    ).select_related('imovel', 'imobiliaria')

    # Estatísticas gerais
    stats_contratos = contratos.aggregate(
        total=Count('id'),
        valor_total=Sum('valor_total'),
    )

    # Todas as parcelas do comprador
    parcelas = Parcela.objects.filter(
        contrato__comprador=comprador
    ).select_related('contrato', 'contrato__imovel')

    stats_parcelas = parcelas.aggregate(
        total=Count('id'),
        pagas=Count('id', filter=Q(pago=True)),
        pendentes=Count('id', filter=Q(pago=False)),
        vencidas=Count('id', filter=Q(pago=False, data_vencimento__lt=hoje)),
        valor_total=Sum('valor_atual'),
        valor_pago=Sum('valor_pago', filter=Q(pago=True)),
        valor_pendente=Sum('valor_atual', filter=Q(pago=False)),
        valor_vencido=Sum('valor_atual', filter=Q(pago=False, data_vencimento__lt=hoje)),
    )

    # Próximas parcelas a vencer (próximos 30 dias)
    proximas_parcelas = parcelas.filter(
        pago=False,
        data_vencimento__gte=hoje,
        data_vencimento__lte=hoje + timedelta(days=30)
    ).order_by('data_vencimento')[:5]

    # Parcelas em atraso
    parcelas_atrasadas = parcelas.filter(
        pago=False,
        data_vencimento__lt=hoje
    ).order_by('data_vencimento')[:10]

    # Últimos pagamentos
    ultimos_pagamentos = parcelas.filter(
        pago=True
    ).order_by('-data_pagamento')[:5]

    # Registrar acesso
    if hasattr(request.user, 'acesso_comprador'):
        registrar_log_acesso(request, request.user.acesso_comprador, 'dashboard')

    context = {
        'comprador': comprador,
        'contratos': contratos,
        'stats_contratos': stats_contratos,
        'stats_parcelas': stats_parcelas,
        'proximas_parcelas': proximas_parcelas,
        'parcelas_atrasadas': parcelas_atrasadas,
        'ultimos_pagamentos': ultimos_pagamentos,
        'hoje': hoje,
    }
    return render(request, 'portal_comprador/dashboard.html', context)


# =============================================================================
# CONTRATOS
# =============================================================================

@login_required(login_url='portal_comprador:login')
def meus_contratos(request):
    """Lista todos os contratos do comprador"""
    comprador = get_comprador_from_request(request)
    if not comprador:
        messages.error(request, 'Acesso não autorizado.')
        return redirect('portal_comprador:login')

    contratos = Contrato.objects.filter(
        comprador=comprador
    ).select_related('imovel', 'imobiliaria').order_by('-data_contrato')

    # Adicionar resumo a cada contrato
    contratos_lista = []
    for contrato in contratos:
        parcelas = contrato.parcelas.all()
        resumo = {
            'contrato': contrato,
            'total_parcelas': parcelas.count(),
            'parcelas_pagas': parcelas.filter(pago=True).count(),
            'parcelas_pendentes': parcelas.filter(pago=False).count(),
            'progresso': contrato.calcular_progresso() if hasattr(contrato, 'calcular_progresso') else 0,
            'saldo_devedor': contrato.calcular_saldo_devedor() if hasattr(contrato, 'calcular_saldo_devedor') else 0,
        }
        contratos_lista.append(resumo)

    context = {
        'comprador': comprador,
        'contratos': contratos_lista,
    }
    return render(request, 'portal_comprador/meus_contratos.html', context)


@login_required(login_url='portal_comprador:login')
def detalhe_contrato(request, contrato_id):
    """Exibe detalhes de um contrato do comprador"""
    comprador = get_comprador_from_request(request)
    if not comprador:
        messages.error(request, 'Acesso não autorizado.')
        return redirect('portal_comprador:login')

    contrato = get_object_or_404(
        Contrato.objects.select_related('imovel', 'imobiliaria'),
        pk=contrato_id,
        comprador=comprador
    )

    hoje = timezone.now().date()

    # Parcelas do contrato
    parcelas = contrato.parcelas.all().order_by('numero_parcela')

    stats_parcelas = parcelas.aggregate(
        total=Count('id'),
        pagas=Count('id', filter=Q(pago=True)),
        pendentes=Count('id', filter=Q(pago=False)),
        vencidas=Count('id', filter=Q(pago=False, data_vencimento__lt=hoje)),
        valor_pago=Sum('valor_pago', filter=Q(pago=True)),
        valor_pendente=Sum('valor_atual', filter=Q(pago=False)),
    )

    # Intermediárias (se existirem)
    intermediarias = []
    if hasattr(contrato, 'intermediarias'):
        intermediarias = contrato.intermediarias.all().order_by('numero_sequencial')

    # Resumo financeiro
    resumo_financeiro = {}
    if hasattr(contrato, 'get_resumo_financeiro'):
        resumo_financeiro = contrato.get_resumo_financeiro()

    context = {
        'comprador': comprador,
        'contrato': contrato,
        'parcelas': parcelas,
        'stats_parcelas': stats_parcelas,
        'intermediarias': intermediarias,
        'resumo_financeiro': resumo_financeiro,
        'progresso': contrato.calcular_progresso() if hasattr(contrato, 'calcular_progresso') else 0,
    }
    return render(request, 'portal_comprador/detalhe_contrato.html', context)


# =============================================================================
# BOLETOS
# =============================================================================

@login_required(login_url='portal_comprador:login')
def meus_boletos(request):
    """
    Lista todos os boletos do comprador.

    Permite filtrar por:
    - Status (a pagar, pagos, vencidos)
    - Contrato
    """
    comprador = get_comprador_from_request(request)
    if not comprador:
        messages.error(request, 'Acesso não autorizado.')
        return redirect('portal_comprador:login')

    hoje = timezone.now().date()

    # Filtros
    status_filtro = request.GET.get('status', 'todos')
    contrato_id = request.GET.get('contrato')

    # Base queryset
    parcelas = Parcela.objects.filter(
        contrato__comprador=comprador
    ).select_related('contrato', 'contrato__imovel').order_by('-data_vencimento')

    # Aplicar filtro de contrato
    if contrato_id:
        parcelas = parcelas.filter(contrato_id=contrato_id)

    # Aplicar filtro de status
    if status_filtro == 'a_pagar':
        parcelas = parcelas.filter(pago=False, data_vencimento__gte=hoje)
    elif status_filtro == 'vencidos':
        parcelas = parcelas.filter(pago=False, data_vencimento__lt=hoje)
    elif status_filtro == 'pagos':
        parcelas = parcelas.filter(pago=True)

    # Lista de contratos para o filtro
    contratos = Contrato.objects.filter(comprador=comprador)

    # Estatísticas
    stats = {
        'total': Parcela.objects.filter(contrato__comprador=comprador).count(),
        'a_pagar': Parcela.objects.filter(
            contrato__comprador=comprador, pago=False, data_vencimento__gte=hoje
        ).count(),
        'vencidos': Parcela.objects.filter(
            contrato__comprador=comprador, pago=False, data_vencimento__lt=hoje
        ).count(),
        'pagos': Parcela.objects.filter(
            contrato__comprador=comprador, pago=True
        ).count(),
    }

    context = {
        'comprador': comprador,
        'parcelas': parcelas[:50],  # Limitar a 50 por página
        'contratos': contratos,
        'status_filtro': status_filtro,
        'contrato_id': contrato_id,
        'stats': stats,
        'hoje': hoje,
    }
    return render(request, 'portal_comprador/meus_boletos.html', context)


@login_required(login_url='portal_comprador:login')
def download_boleto(request, parcela_id):
    """Download do PDF do boleto"""
    comprador = get_comprador_from_request(request)
    if not comprador:
        return JsonResponse({'erro': 'Acesso não autorizado'}, status=403)

    parcela = get_object_or_404(
        Parcela,
        pk=parcela_id,
        contrato__comprador=comprador
    )

    if not parcela.boleto_pdf:
        messages.error(request, 'Boleto não disponível para download.')
        return redirect('portal_comprador:meus_boletos')

    # Registrar log de acesso
    if hasattr(request.user, 'acesso_comprador'):
        registrar_log_acesso(request, request.user.acesso_comprador, f'download_boleto_{parcela_id}')

    # Retornar arquivo
    response = FileResponse(
        parcela.boleto_pdf.open('rb'),
        content_type='application/pdf'
    )
    response['Content-Disposition'] = f'attachment; filename="boleto_{parcela.contrato.numero_contrato}_{parcela.numero_parcela}.pdf"'
    return response


@login_required(login_url='portal_comprador:login')
def visualizar_boleto(request, parcela_id):
    """Visualização inline do boleto"""
    comprador = get_comprador_from_request(request)
    if not comprador:
        return JsonResponse({'erro': 'Acesso não autorizado'}, status=403)

    parcela = get_object_or_404(
        Parcela,
        pk=parcela_id,
        contrato__comprador=comprador
    )

    if not parcela.boleto_pdf:
        return HttpResponse('Boleto não disponível', status=404)

    # Registrar log de acesso
    if hasattr(request.user, 'acesso_comprador'):
        registrar_log_acesso(request, request.user.acesso_comprador, f'visualizar_boleto_{parcela_id}')

    response = FileResponse(
        parcela.boleto_pdf.open('rb'),
        content_type='application/pdf'
    )
    response['Content-Disposition'] = 'inline'
    return response


# =============================================================================
# DADOS PESSOAIS
# =============================================================================

@login_required(login_url='portal_comprador:login')
def meus_dados(request):
    """
    View para visualização e atualização de dados pessoais.

    O comprador pode atualizar apenas:
    - Endereço de correspondência
    - E-mail
    - Telefone/Celular
    """
    comprador = get_comprador_from_request(request)
    if not comprador:
        messages.error(request, 'Acesso não autorizado.')
        return redirect('portal_comprador:login')

    if request.method == 'POST':
        form = DadosPessoaisForm(request.POST, instance=comprador)
        if form.is_valid():
            # Impedir alteração do nome (segurança extra)
            form.instance.nome = comprador.nome
            form.save()
            messages.success(request, 'Dados atualizados com sucesso!')
            return redirect('portal_comprador:meus_dados')
        else:
            messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = DadosPessoaisForm(instance=comprador)

    context = {
        'comprador': comprador,
        'form': form,
    }
    return render(request, 'portal_comprador/meus_dados.html', context)


@login_required(login_url='portal_comprador:login')
def alterar_senha(request):
    """View para alteração de senha"""
    comprador = get_comprador_from_request(request)
    if not comprador:
        messages.error(request, 'Acesso não autorizado.')
        return redirect('portal_comprador:login')

    if request.method == 'POST':
        form = AlterarSenhaCompradorForm(request.POST)
        if form.is_valid():
            user = request.user
            if user.check_password(form.cleaned_data['senha_atual']):
                user.set_password(form.cleaned_data['nova_senha'])
                user.save()
                update_session_auth_hash(request, user)  # Mantém logado
                messages.success(request, 'Senha alterada com sucesso!')
                return redirect('portal_comprador:meus_dados')
            else:
                messages.error(request, 'Senha atual incorreta.')
    else:
        form = AlterarSenhaCompradorForm()

    context = {
        'comprador': comprador,
        'form': form,
    }
    return render(request, 'portal_comprador/alterar_senha.html', context)


# =============================================================================
# API
# =============================================================================

@login_required(login_url='portal_comprador:login')
def api_parcelas_contrato(request, contrato_id):
    """API para retornar parcelas de um contrato em JSON"""
    comprador = get_comprador_from_request(request)
    if not comprador:
        return JsonResponse({'erro': 'Acesso não autorizado'}, status=403)

    contrato = get_object_or_404(
        Contrato,
        pk=contrato_id,
        comprador=comprador
    )

    hoje = timezone.now().date()
    parcelas = contrato.parcelas.all().order_by('numero_parcela')

    data = []
    for parcela in parcelas:
        dias_atraso = 0
        if not parcela.pago and parcela.data_vencimento < hoje:
            dias_atraso = (hoje - parcela.data_vencimento).days

        data.append({
            'id': parcela.id,
            'numero_parcela': parcela.numero_parcela,
            'data_vencimento': parcela.data_vencimento.isoformat(),
            'valor': float(parcela.valor_atual),
            'pago': parcela.pago,
            'data_pagamento': parcela.data_pagamento.isoformat() if parcela.data_pagamento else None,
            'valor_pago': float(parcela.valor_pago) if parcela.valor_pago else None,
            'dias_atraso': dias_atraso,
            'tem_boleto': bool(parcela.boleto_pdf),
        })

    return JsonResponse({
        'sucesso': True,
        'parcelas': data,
        'total': len(data)
    })


@login_required(login_url='portal_comprador:login')
def api_resumo_financeiro(request):
    """API para retornar resumo financeiro do comprador"""
    comprador = get_comprador_from_request(request)
    if not comprador:
        return JsonResponse({'erro': 'Acesso não autorizado'}, status=403)

    hoje = timezone.now().date()

    parcelas = Parcela.objects.filter(contrato__comprador=comprador)

    stats = parcelas.aggregate(
        total=Count('id'),
        pagas=Count('id', filter=Q(pago=True)),
        pendentes=Count('id', filter=Q(pago=False)),
        vencidas=Count('id', filter=Q(pago=False, data_vencimento__lt=hoje)),
        valor_total=Sum('valor_atual'),
        valor_pago=Sum('valor_pago', filter=Q(pago=True)),
        valor_pendente=Sum('valor_atual', filter=Q(pago=False)),
        valor_vencido=Sum('valor_atual', filter=Q(pago=False, data_vencimento__lt=hoje)),
    )

    # Converter Decimal para float
    for key, value in stats.items():
        if isinstance(value, Decimal):
            stats[key] = float(value) if value else 0

    return JsonResponse({
        'sucesso': True,
        'resumo': stats
    })
