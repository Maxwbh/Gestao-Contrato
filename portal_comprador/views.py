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
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from django.core.paginator import Paginator
from django.core.cache import cache
from django.core.mail import send_mail
from django.core import signing
from django.conf import settings
from django.urls import reverse
from django.db.models import Sum, Count, Q
from decimal import Decimal
from datetime import timedelta
import time
import logging

from contratos.models import Contrato, StatusContrato
from core.permissions import portal_rate_limit
from financeiro.models import Parcela, StatusBoleto

from .models import AcessoComprador, LogAcessoComprador
from .forms import (
    AutoCadastroForm, LoginCompradorForm,
    DadosPessoaisForm, AlterarSenhaCompradorForm
)

logger = logging.getLogger(__name__)


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
        acesso = request.user.acesso_comprador
        if not acesso.ativo:
            return None
        return acesso.comprador
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

            verificacao_habilitada = getattr(settings, 'PORTAL_EMAIL_VERIFICACAO', False)

            # Criar acesso do comprador
            acesso = AcessoComprador.objects.create(
                comprador=comprador,
                usuario=user,
                # email_verificado=True quando feature desabilitada — sem pendência
                email_verificado=not verificacao_habilitada,
            )

            # Enviar e-mail de verificação apenas quando feature habilitada
            if verificacao_habilitada and comprador.email:
                token = signing.dumps(acesso.pk, salt='portal-email-verify')
                link = request.build_absolute_uri(
                    reverse('portal_comprador:verificar_email', kwargs={'token': token})
                )
                send_mail(
                    subject='Confirme seu e-mail — Portal do Comprador',
                    message=(
                        f'Bem-vindo ao Portal do Comprador, {comprador.nome}!\n\n'
                        f'Clique no link abaixo para verificar seu e-mail (válido por 24 horas):\n\n'
                        f'{link}'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[comprador.email],
                    fail_silently=True,
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
        # Rate limit: 5 tentativas por minuto por IP
        ip = get_client_ip(request)
        rl_key = f'portal_login:{ip}:{int(time.time() // 60)}'
        attempts = cache.get(rl_key, 0)
        if attempts >= 5:
            messages.error(request, 'Muitas tentativas de login. Aguarde 1 minuto e tente novamente.')
            return render(request, 'portal_comprador/login.html', {'form': LoginCompradorForm()})

        form = LoginCompradorForm(request.POST)
        if form.is_valid():
            documento = form.cleaned_data['documento']
            senha = form.cleaned_data['senha']

            username = f'comprador_{documento}'
            user = authenticate(request, username=username, password=senha)

            if user is not None:
                if hasattr(user, 'acesso_comprador') and not user.acesso_comprador.ativo:
                    messages.error(request, 'Acesso ao portal foi desativado. Entre em contato com o suporte.')
                else:
                    login(request, user)
                    if hasattr(user, 'acesso_comprador'):
                        acesso = user.acesso_comprador
                        acesso.registrar_acesso()
                        registrar_log_acesso(request, acesso, 'login')
                    messages.success(request, 'Bem-vindo de volta!')
                    return redirect('portal_comprador:dashboard')
            else:
                # Incrementa contador apenas em falha
                cache.set(rl_key, attempts + 1, timeout=90)
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
        status=StatusContrato.ATIVO
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
    ).select_related('imovel', 'imobiliaria').annotate(
        total_parcelas=Count('parcelas'),
        parcelas_pagas=Count('parcelas', filter=Q(parcelas__pago=True)),
    ).order_by('-data_contrato')

    context = {
        'comprador': comprador,
        'contratos': contratos,
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
        'hoje': hoje,
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

    # Estatísticas — single aggregate instead of 4 separate count() queries
    _stats_qs = Parcela.objects.filter(contrato__comprador=comprador).aggregate(
        total=Count('id'),
        a_pagar=Count('id', filter=Q(pago=False, data_vencimento__gte=hoje)),
        vencidos=Count('id', filter=Q(pago=False, data_vencimento__lt=hoje)),
        pagos=Count('id', filter=Q(pago=True)),
    )
    stats = {
        'total':  _stats_qs['total'] or 0,
        'a_pagar': _stats_qs['a_pagar'] or 0,
        'vencidos': _stats_qs['vencidos'] or 0,
        'pagos':  _stats_qs['pagos'] or 0,
    }

    paginator = Paginator(parcelas, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'comprador': comprador,
        'parcelas': page_obj,
        'page_obj': page_obj,
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
    try:
        response = FileResponse(
            parcela.boleto_pdf.open('rb'),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="boleto_{parcela.contrato.numero_contrato}_{parcela.numero_parcela}.pdf"'
        return response
    except Exception as e:
        logger.exception("Erro ao abrir PDF do boleto parcela pk=%s: %s", parcela_id, e)
        messages.error(request, 'Erro ao acessar o arquivo do boleto.')
        return redirect('portal_comprador:meus_boletos')


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

    try:
        response = FileResponse(
            parcela.boleto_pdf.open('rb'),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = 'inline'
        return response
    except Exception as e:
        logger.exception("Erro ao abrir PDF do boleto para visualização parcela pk=%s: %s", parcela_id, e)
        return HttpResponse('Erro ao acessar o arquivo do boleto.', status=500)


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
# RECUPERAÇÃO DE SENHA
# =============================================================================

def esqueci_senha(request):
    """
    Solicita redefinição de senha por CPF/CNPJ.
    Envia e-mail com link assinado (válido por 1 hora).
    """
    if request.user.is_authenticated and hasattr(request.user, 'acesso_comprador'):
        return redirect('portal_comprador:dashboard')

    from .forms import EsqueciSenhaForm
    if request.method == 'POST':
        form = EsqueciSenhaForm(request.POST)
        if form.is_valid():
            acesso = form.cleaned_data['acesso']
            # Token inclui hash da senha atual → invalida automaticamente após uso
            token = signing.dumps(
                f'{acesso.pk}:{acesso.usuario.password}',
                salt='portal-reset-senha',
            )
            link = request.build_absolute_uri(
                reverse('portal_comprador:redefinir_senha', kwargs={'token': token})
            )
            send_mail(
                subject='Redefinição de senha — Portal do Comprador',
                message=(
                    f'Olá, {acesso.comprador.nome}!\n\n'
                    f'Clique no link abaixo para redefinir sua senha (válido por 1 hora):\n\n'
                    f'{link}\n\n'
                    f'Se não solicitou, ignore este e-mail.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[acesso.comprador.email],
                fail_silently=True,
            )
            messages.success(request, 'Instruções enviadas para o e-mail cadastrado.')
            return redirect('portal_comprador:login')
    else:
        form = EsqueciSenhaForm()

    return render(request, 'portal_comprador/esqueci_senha.html', {'form': form})


def redefinir_senha(request, token):
    """
    Define nova senha usando o link enviado por e-mail.
    Token expira em 1 hora e é invalidado ao trocar a senha.
    """
    from .forms import RedefinirSenhaForm
    try:
        payload = signing.loads(token, salt='portal-reset-senha', max_age=3600)
        pk, senha_hash = payload.split(':', 1)
        acesso = AcessoComprador.objects.select_related('usuario', 'comprador').get(pk=pk)
        # Verifica que a senha não foi alterada desde que o token foi emitido
        if acesso.usuario.password != senha_hash:
            raise signing.BadSignature()
    except (signing.BadSignature, signing.SignatureExpired,
            AcessoComprador.DoesNotExist, ValueError):
        messages.error(request, 'Link inválido ou expirado. Solicite um novo link.')
        return redirect('portal_comprador:esqueci_senha')

    if request.method == 'POST':
        form = RedefinirSenhaForm(request.POST)
        if form.is_valid():
            acesso.usuario.set_password(form.cleaned_data['nova_senha'])
            acesso.usuario.save()
            messages.success(request, 'Senha redefinida com sucesso! Faça login com a nova senha.')
            return redirect('portal_comprador:login')
    else:
        form = RedefinirSenhaForm()

    return render(request, 'portal_comprador/redefinir_senha.html', {
        'form': form,
        'token': token,
    })


# =============================================================================
# VERIFICAÇÃO DE E-MAIL
# =============================================================================

def verificar_email(request, token):
    """
    Confirma o e-mail do comprador a partir do link enviado no cadastro.
    Token expira em 24 horas.
    """
    try:
        pk = signing.loads(token, salt='portal-email-verify', max_age=86400)
        acesso = AcessoComprador.objects.get(pk=pk)
    except (signing.BadSignature, signing.SignatureExpired, AcessoComprador.DoesNotExist):
        messages.error(request, 'Link inválido ou expirado. Solicite um novo e-mail de verificação.')
        return redirect('portal_comprador:login')

    if not acesso.email_verificado:
        acesso.email_verificado = True
        acesso.save(update_fields=['email_verificado'])
        messages.success(request, 'E-mail verificado com sucesso!')
    else:
        messages.info(request, 'Seu e-mail já estava verificado.')

    if request.user.is_authenticated:
        return redirect('portal_comprador:dashboard')
    return redirect('portal_comprador:login')


@login_required(login_url='portal_comprador:login')
def reenviar_verificacao(request):
    """Reenvia o e-mail de verificação para o comprador autenticado."""
    if not getattr(settings, 'PORTAL_EMAIL_VERIFICACAO', False):
        messages.info(request, 'Verificação de e-mail não está habilitada.')
        return redirect('portal_comprador:dashboard')

    comprador = get_comprador_from_request(request)
    if not comprador:
        return redirect('portal_comprador:login')

    acesso = request.user.acesso_comprador
    if acesso.email_verificado:
        messages.info(request, 'Seu e-mail já está verificado.')
        return redirect('portal_comprador:dashboard')

    if not comprador.email:
        messages.error(request, 'Nenhum e-mail cadastrado. Atualize seus dados primeiro.')
        return redirect('portal_comprador:meus_dados')

    token = signing.dumps(acesso.pk, salt='portal-email-verify')
    link = request.build_absolute_uri(
        reverse('portal_comprador:verificar_email', kwargs={'token': token})
    )
    send_mail(
        subject='Confirme seu e-mail — Portal do Comprador',
        message=(
            f'Olá, {comprador.nome}!\n\n'
            f'Clique no link abaixo para verificar seu e-mail (válido por 24 horas):\n\n'
            f'{link}'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[comprador.email],
        fail_silently=True,
    )
    messages.success(request, 'E-mail de verificação enviado!')
    return redirect('portal_comprador:dashboard')


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
            'tem_boleto': parcela.tem_boleto,
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


# =============================================================================
# FASE 9 — APIs P2 do Portal do Comprador
# =============================================================================

@login_required(login_url='portal_comprador:login')
def api_portal_vencimentos(request):
    """
    Lista vencimentos (parcelas pendentes/vencidas) do comprador logado.

    GET /portal/api/vencimentos/

    Filtros: status (pendente/vencido/a_vencer), data_inicio, data_fim,
             contrato (id), page, per_page
    """
    comprador = get_comprador_from_request(request)
    if not comprador:
        return JsonResponse({'erro': 'Acesso não autorizado'}, status=403)

    hoje = timezone.now().date()
    qs = Parcela.objects.select_related(
        'contrato', 'contrato__comprador', 'contrato__imovel'
    ).filter(contrato__comprador=comprador)

    # Filtro por status
    status = request.GET.get('status', '')
    if status == 'pendente':
        qs = qs.filter(pago=False)
    elif status == 'vencido':
        qs = qs.filter(pago=False, data_vencimento__lt=hoje)
    elif status == 'a_vencer':
        qs = qs.filter(pago=False, data_vencimento__gte=hoje)
    elif status == 'pago':
        qs = qs.filter(pago=True)
    else:
        # Default: apenas pendentes (não pagas)
        qs = qs.filter(pago=False)

    # Filtros de período
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    if data_inicio:
        from datetime import datetime as dt
        qs = qs.filter(data_vencimento__gte=dt.strptime(data_inicio, '%Y-%m-%d').date())
    if data_fim:
        from datetime import datetime as dt
        qs = qs.filter(data_vencimento__lte=dt.strptime(data_fim, '%Y-%m-%d').date())

    contrato_id = request.GET.get('contrato')
    if contrato_id:
        qs = qs.filter(contrato_id=contrato_id)

    qs = qs.order_by('data_vencimento', 'numero_parcela')

    # Paginação
    try:
        page = max(1, int(request.GET.get('page', 1)))
        per_page = min(max(1, int(request.GET.get('per_page', 50))), 100)
    except (ValueError, TypeError):
        page, per_page = 1, 50
    total = qs.count()
    offset = (page - 1) * per_page
    parcelas_page = qs[offset:offset + per_page]

    parcelas_data = []
    for p in parcelas_page:
        dias_atraso = max(0, (hoje - p.data_vencimento).days) if not p.pago and p.data_vencimento < hoje else 0
        parcelas_data.append({
            'id': p.id,
            'contrato': {
                'id': p.contrato.id,
                'numero': p.contrato.numero_contrato,
                'imovel': p.contrato.imovel.identificacao if p.contrato.imovel else '',
            },
            'numero_parcela': p.numero_parcela,
            'total_parcelas': p.contrato.numero_parcelas,
            'data_vencimento': p.data_vencimento.strftime('%Y-%m-%d'),
            'valor_atual': float(p.valor_atual),
            'pago': p.pago,
            'data_pagamento': p.data_pagamento.strftime('%Y-%m-%d') if p.data_pagamento else None,
            'dias_atraso': dias_atraso,
            'tem_boleto': p.tem_boleto,
            'status_boleto': p.status_boleto,
            'linha_digitavel': p.linha_digitavel or '',
        })

    totais = qs.aggregate(
        valor_total=Sum('valor_atual'),
        vencidas=Count('id', filter=Q(pago=False, data_vencimento__lt=hoje)),
    )

    return JsonResponse({
        'sucesso': True,
        'parcelas': parcelas_data,
        'total': total,
        'page': page,
        'per_page': per_page,
        'totais': {
            'valor_total': float(totais['valor_total'] or 0),
            'quantidade_vencidas': totais['vencidas'] or 0,
        },
    })


@login_required(login_url='portal_comprador:login')
def api_portal_boletos(request):
    """
    Lista boletos do comprador logado.

    GET /portal/api/boletos/

    Filtros: status_boleto (GERADO/REGISTRADO/PAGO/VENCIDO/CANCELADO),
             contrato (id), page, per_page
    """
    comprador = get_comprador_from_request(request)
    if not comprador:
        return JsonResponse({'erro': 'Acesso não autorizado'}, status=403)

    qs = Parcela.objects.select_related(
        'contrato', 'contrato__imovel'
    ).filter(
        contrato__comprador=comprador
    ).exclude(status_boleto=StatusBoleto.NAO_GERADO)

    # Filtros
    status_boleto = request.GET.get('status_boleto', '')
    if status_boleto:
        qs = qs.filter(status_boleto=status_boleto.upper())

    contrato_id = request.GET.get('contrato')
    if contrato_id:
        qs = qs.filter(contrato_id=contrato_id)

    qs = qs.order_by('-data_vencimento', 'numero_parcela')

    # Paginação
    try:
        page = max(1, int(request.GET.get('page', 1)))
        per_page = min(max(1, int(request.GET.get('per_page', 50))), 100)
    except (ValueError, TypeError):
        page, per_page = 1, 50
    total = qs.count()
    offset = (page - 1) * per_page
    boletos_page = qs[offset:offset + per_page]

    boletos_data = []
    for p in boletos_page:
        boletos_data.append({
            'id': p.id,
            'contrato': {
                'id': p.contrato.id,
                'numero': p.contrato.numero_contrato,
                'imovel': p.contrato.imovel.identificacao if p.contrato.imovel else '',
            },
            'numero_parcela': p.numero_parcela,
            'data_vencimento': p.data_vencimento.strftime('%Y-%m-%d'),
            'valor_atual': float(p.valor_atual),
            'pago': p.pago,
            'status_boleto': p.status_boleto,
            'nosso_numero': p.nosso_numero or '',
            'linha_digitavel': p.linha_digitavel or '',
            'url_visualizar': f'/portal/boletos/{p.id}/visualizar/',
            'url_download': f'/portal/boletos/{p.id}/download/',
        })

    return JsonResponse({
        'sucesso': True,
        'boletos': boletos_data,
        'total': total,
        'page': page,
        'per_page': per_page,
    })


# =============================================================================
# 4-P3-4 : POST /portal/api/boletos/segunda-via/
# =============================================================================

@login_required
@portal_rate_limit
@require_POST
def api_portal_segunda_via(request, parcela_id):
    """
    Gera segunda via do boleto para o comprador autenticado.
    Recalcula juros/multa do dia antes de enviar para BRCobrança.

    POST /portal/api/boletos/<parcela_id>/segunda-via/
    """
    comprador = get_comprador_from_request(request)
    if not comprador:
        return JsonResponse(
            {'sucesso': False, 'erro': 'Acesso não autorizado'},
            status=403
        )

    from financeiro.models import Parcela
    try:
        parcela = Parcela.objects.select_related(
            'contrato', 'contrato__comprador'
        ).get(pk=parcela_id, contrato__comprador=comprador)
    except Parcela.DoesNotExist:
        return JsonResponse({'sucesso': False, 'erro': 'Boleto não encontrado'}, status=404)

    if parcela.pago:
        return JsonResponse({'sucesso': False, 'erro': 'Parcela já paga'}, status=400)

    if not parcela.nosso_numero:
        return JsonResponse(
            {'sucesso': False, 'erro': 'Boleto não foi gerado ainda'},
            status=400
        )

    try:
        from financeiro.services.boleto_service import BoletoService
        service = BoletoService()
        resultado = service.gerar_segunda_via(parcela)

        if resultado.get('sucesso'):
            return JsonResponse({
                'sucesso': True,
                'nosso_numero': parcela.nosso_numero,
                'linha_digitavel': resultado.get('linha_digitavel', parcela.linha_digitavel or ''),
                'valor': float(resultado.get('valor', parcela.valor_atual)),
                'vencimento': resultado.get('vencimento', parcela.data_vencimento.isoformat()),
                'url_pdf': resultado.get('url_pdf', ''),
            })
        else:
            return JsonResponse(
                {'sucesso': False, 'erro': resultado.get('erro', 'Erro ao gerar segunda via')},
                status=400
            )
    except Exception as e:
        import logging
        logging.getLogger('portal_comprador').exception("Erro segunda via parcela %s: %s", parcela_id, e)
        return JsonResponse({'sucesso': False, 'erro': str(e)}, status=500)


# =============================================================================
# 4-P3-5 : GET /portal/api/boletos/<id>/linha-digitavel/
# =============================================================================

@login_required
@require_GET
def api_portal_linha_digitavel(request, parcela_id):
    """
    Retorna a linha digitável do boleto para o comprador autenticado.

    GET /portal/api/boletos/<parcela_id>/linha-digitavel/
    """
    comprador = get_comprador_from_request(request)
    if not comprador:
        return JsonResponse(
            {'sucesso': False, 'erro': 'Acesso não autorizado'},
            status=403
        )

    from financeiro.models import Parcela
    try:
        parcela = Parcela.objects.select_related('contrato').get(
            pk=parcela_id, contrato__comprador=comprador
        )
    except Parcela.DoesNotExist:
        return JsonResponse({'sucesso': False, 'erro': 'Boleto não encontrado'}, status=404)

    if not parcela.nosso_numero:
        return JsonResponse(
            {'sucesso': False, 'erro': 'Boleto não gerado'},
            status=404
        )

    return JsonResponse({
        'sucesso': True,
        'parcela_id': parcela.pk,
        'numero_parcela': parcela.numero_parcela,
        'nosso_numero': parcela.nosso_numero,
        'linha_digitavel': parcela.linha_digitavel or '',
        'codigo_barras': parcela.codigo_barras or '',
        'valor': float(parcela.valor_atual),
        'data_vencimento': parcela.data_vencimento.isoformat(),
        'pago': parcela.pago,
    })
