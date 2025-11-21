"""
Views do app Core

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
from django.db import connection
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Q
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from datetime import datetime, timedelta
from .models import (
    Contabilidade, Imobiliaria, Imovel, Comprador, TipoImovel,
    ContaBancaria, BancoBrasil, LayoutCNAB, AcessoUsuario,
    get_contabilidades_usuario, get_imobiliarias_usuario,
    usuario_tem_acesso_imobiliaria, usuario_tem_acesso_contabilidade
)
from .forms import ContabilidadeForm, CompradorForm, ImovelForm, ImobiliariaForm, ContaBancariaForm, AcessoUsuarioForm
import io
import json


# =============================================================================
# CONTROLE DE ACESSO - MIXIN
# =============================================================================

class AcessoMixin:
    """
    Mixin para controle de acesso baseado nos registros de AcessoUsuario.

    Cada usuário pode ter múltiplos acessos:
    - Usuário A → Contabilidade A → Imobiliária A
    - Usuário A → Contabilidade A → Imobiliária B
    - Usuário A → Contabilidade B → Imobiliária E
    """

    def get_contabilidades_permitidas(self):
        """Retorna as contabilidades que o usuário pode acessar"""
        return get_contabilidades_usuario(self.request.user)

    def get_imobiliarias_permitidas(self, contabilidade=None):
        """Retorna as imobiliárias que o usuário pode acessar"""
        return get_imobiliarias_usuario(self.request.user, contabilidade)

    def pode_acessar_contabilidade(self, contabilidade):
        """Verifica se o usuário pode acessar uma contabilidade específica"""
        return usuario_tem_acesso_contabilidade(self.request.user, contabilidade)

    def pode_acessar_imobiliaria(self, imobiliaria):
        """Verifica se o usuário pode acessar uma imobiliária específica"""
        return usuario_tem_acesso_imobiliaria(self.request.user, imobiliaria)


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


# =============================================================================
# CRUD VIEWS - CONTABILIDADE
# =============================================================================

class ContabilidadeListView(LoginRequiredMixin, ListView):
    """Lista todas as contabilidades ativas"""
    model = Contabilidade
    template_name = 'core/contabilidade_list.html'
    context_object_name = 'contabilidades'
    paginate_by = 20

    def get_queryset(self):
        queryset = Contabilidade.objects.filter(ativo=True).order_by('nome')

        # Filtro de busca
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(nome__icontains=search) |
                Q(cnpj__icontains=search) |
                Q(responsavel__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_contabilidades'] = Contabilidade.objects.filter(ativo=True).count()
        context['search'] = self.request.GET.get('search', '')
        return context


class ContabilidadeCreateView(LoginRequiredMixin, CreateView):
    """Cria uma nova contabilidade"""
    model = Contabilidade
    form_class = ContabilidadeForm
    template_name = 'core/contabilidade_form.html'
    success_url = reverse_lazy('core:listar_contabilidades')

    def form_valid(self, form):
        messages.success(self.request, f'Contabilidade {form.instance.nome} cadastrada com sucesso!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao cadastrar contabilidade. Verifique os dados.')
        return super().form_invalid(form)


class ContabilidadeUpdateView(LoginRequiredMixin, UpdateView):
    """Atualiza uma contabilidade existente"""
    model = Contabilidade
    form_class = ContabilidadeForm
    template_name = 'core/contabilidade_form.html'
    success_url = reverse_lazy('core:listar_contabilidades')

    def get_queryset(self):
        return Contabilidade.objects.filter(ativo=True)

    def form_valid(self, form):
        messages.success(self.request, f'Contabilidade {form.instance.nome} atualizada com sucesso!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao atualizar contabilidade. Verifique os dados.')
        return super().form_invalid(form)


class ContabilidadeDeleteView(LoginRequiredMixin, DeleteView):
    """Desativa uma contabilidade (soft delete)"""
    model = Contabilidade
    success_url = reverse_lazy('core:listar_contabilidades')

    def get_queryset(self):
        return Contabilidade.objects.filter(ativo=True)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.ativo = False
        self.object.save()
        messages.success(request, f'Contabilidade {self.object.nome} removida com sucesso!')
        return redirect(self.success_url)


# =============================================================================
# CRUD VIEWS - COMPRADOR
# =============================================================================

class CompradorListView(LoginRequiredMixin, ListView):
    """Lista todos os compradores ativos"""
    model = Comprador
    template_name = 'core/comprador_list.html'
    context_object_name = 'compradores'
    paginate_by = 20

    def get_queryset(self):
        queryset = Comprador.objects.filter(ativo=True).order_by('-criado_em')

        # Filtro de busca
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(nome__icontains=search) |
                Q(cpf__icontains=search) |
                Q(email__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_compradores'] = Comprador.objects.filter(ativo=True).count()
        context['search'] = self.request.GET.get('search', '')
        return context


class CompradorCreateView(LoginRequiredMixin, CreateView):
    """Cria um novo comprador"""
    model = Comprador
    form_class = CompradorForm
    template_name = 'core/comprador_form.html'
    success_url = reverse_lazy('core:listar_compradores')

    def form_valid(self, form):
        messages.success(self.request, f'Comprador {form.instance.nome} cadastrado com sucesso!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao cadastrar comprador. Verifique os dados.')
        return super().form_invalid(form)


class CompradorUpdateView(LoginRequiredMixin, UpdateView):
    """Atualiza um comprador existente"""
    model = Comprador
    form_class = CompradorForm
    template_name = 'core/comprador_form.html'
    success_url = reverse_lazy('core:listar_compradores')

    def get_queryset(self):
        return Comprador.objects.filter(ativo=True)

    def form_valid(self, form):
        messages.success(self.request, f'Comprador {form.instance.nome} atualizado com sucesso!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao atualizar comprador. Verifique os dados.')
        return super().form_invalid(form)


class CompradorDeleteView(LoginRequiredMixin, DeleteView):
    """Desativa um comprador (soft delete)"""
    model = Comprador
    success_url = reverse_lazy('core:listar_compradores')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.ativo = False
        self.object.save()
        messages.success(request, f'Comprador {self.object.nome} removido com sucesso!')
        return redirect(self.success_url)


# =============================================================================
# CRUD VIEWS - IMOVEL
# =============================================================================

class ImovelListView(LoginRequiredMixin, ListView):
    """Lista todos os imóveis ativos"""
    model = Imovel
    template_name = 'core/imovel_list.html'
    context_object_name = 'imoveis'
    paginate_by = 20

    def get_queryset(self):
        queryset = Imovel.objects.filter(ativo=True).select_related('imobiliaria', 'tipo').order_by('-criado_em')

        # Filtros
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(identificacao__icontains=search) |
                Q(loteamento__icontains=search) |
                Q(endereco__icontains=search)
            )

        disponivel = self.request.GET.get('disponivel')
        if disponivel:
            queryset = queryset.filter(disponivel=(disponivel == 'true'))

        imobiliaria = self.request.GET.get('imobiliaria')
        if imobiliaria:
            queryset = queryset.filter(imobiliaria_id=imobiliaria)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_imoveis'] = Imovel.objects.filter(ativo=True).count()
        context['imoveis_disponiveis'] = Imovel.objects.filter(ativo=True, disponivel=True).count()
        context['imobiliarias'] = Imobiliaria.objects.filter(ativo=True)
        context['search'] = self.request.GET.get('search', '')
        return context


class ImovelCreateView(LoginRequiredMixin, CreateView):
    """Cria um novo imóvel"""
    model = Imovel
    form_class = ImovelForm
    template_name = 'core/imovel_form.html'
    success_url = reverse_lazy('core:listar_imoveis')

    def form_valid(self, form):
        messages.success(self.request, f'Imóvel {form.instance.identificacao} cadastrado com sucesso!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao cadastrar imóvel. Verifique os dados.')
        return super().form_invalid(form)


class ImovelUpdateView(LoginRequiredMixin, UpdateView):
    """Atualiza um imóvel existente"""
    model = Imovel
    form_class = ImovelForm
    template_name = 'core/imovel_form.html'
    success_url = reverse_lazy('core:listar_imoveis')

    def get_queryset(self):
        return Imovel.objects.filter(ativo=True)

    def form_valid(self, form):
        messages.success(self.request, f'Imóvel {form.instance.identificacao} atualizado com sucesso!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao atualizar imóvel. Verifique os dados.')
        return super().form_invalid(form)


class ImovelDeleteView(LoginRequiredMixin, DeleteView):
    """Desativa um imóvel (soft delete)"""
    model = Imovel
    success_url = reverse_lazy('core:listar_imoveis')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.ativo = False
        self.object.save()
        messages.success(request, f'Imóvel {self.object.identificacao} removido com sucesso!')
        return redirect(self.success_url)


# =============================================================================
# CRUD VIEWS - IMOBILIARIA
# =============================================================================

class ImobiliariaListView(LoginRequiredMixin, ListView):
    """Lista todas as imobiliárias ativas"""
    model = Imobiliaria
    template_name = 'core/imobiliaria_list.html'
    context_object_name = 'imobiliarias'
    paginate_by = 20

    def get_queryset(self):
        queryset = Imobiliaria.objects.filter(ativo=True).select_related('contabilidade').order_by('-criado_em')

        # Filtro de busca
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(nome__icontains=search) |
                Q(razao_social__icontains=search) |
                Q(cnpj__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_imobiliarias'] = Imobiliaria.objects.filter(ativo=True).count()
        context['search'] = self.request.GET.get('search', '')
        return context


class ImobiliariaCreateView(LoginRequiredMixin, CreateView):
    """Cria uma nova imobiliária"""
    model = Imobiliaria
    form_class = ImobiliariaForm
    template_name = 'core/imobiliaria_form.html'
    success_url = reverse_lazy('core:listar_imobiliarias')

    def form_valid(self, form):
        messages.success(self.request, f'Imobiliária {form.instance.nome} cadastrada com sucesso!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao cadastrar imobiliária. Verifique os dados.')
        return super().form_invalid(form)


class ImobiliariaUpdateView(LoginRequiredMixin, UpdateView):
    """Atualiza uma imobiliária existente"""
    model = Imobiliaria
    form_class = ImobiliariaForm
    template_name = 'core/imobiliaria_form.html'
    success_url = reverse_lazy('core:listar_imobiliarias')

    def get_queryset(self):
        return Imobiliaria.objects.filter(ativo=True)

    def form_valid(self, form):
        messages.success(self.request, f'Imobiliária {form.instance.nome} atualizada com sucesso!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao atualizar imobiliária. Verifique os dados.')
        return super().form_invalid(form)


class ImobiliariaDeleteView(LoginRequiredMixin, DeleteView):
    """Desativa uma imobiliária (soft delete)"""
    model = Imobiliaria
    success_url = reverse_lazy('core:listar_imobiliarias')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.ativo = False
        self.object.save()
        messages.success(request, f'Imobiliária {self.object.nome} removida com sucesso!')
        return redirect(self.success_url)


# =============================================================================
# API VIEWS - CONTA BANCÁRIA (para AJAX)
# =============================================================================

@login_required
@require_http_methods(["GET"])
def api_listar_contas_bancarias(request, imobiliaria_id):
    """Lista todas as contas bancárias de uma imobiliária"""
    try:
        imobiliaria = get_object_or_404(Imobiliaria, pk=imobiliaria_id, ativo=True)
        contas = imobiliaria.contas_bancarias.filter(ativo=True).order_by('-principal', 'banco')

        data = []
        for conta in contas:
            data.append({
                'id': conta.id,
                'banco': conta.banco,
                'banco_nome': conta.get_banco_display(),
                'descricao': conta.descricao,
                'agencia': conta.agencia,
                'conta': conta.conta,
                'convenio': conta.convenio,
                'carteira': conta.carteira,
                'tipo_pix': conta.tipo_pix,
                'chave_pix': conta.chave_pix,
                'principal': conta.principal,
                'cobranca_registrada': conta.cobranca_registrada,
            })

        return JsonResponse({'status': 'success', 'contas': data})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_obter_conta_bancaria(request, conta_id):
    """Obtém os dados de uma conta bancária específica"""
    try:
        conta = get_object_or_404(ContaBancaria, pk=conta_id, ativo=True)

        data = {
            'id': conta.id,
            'imobiliaria_id': conta.imobiliaria_id,
            'banco': conta.banco,
            'banco_nome': conta.get_banco_display(),
            'descricao': conta.descricao,
            'agencia': conta.agencia,
            'conta': conta.conta,
            'convenio': conta.convenio,
            'carteira': conta.carteira,
            'nosso_numero_atual': conta.nosso_numero_atual,
            'modalidade': conta.modalidade,
            'tipo_pix': conta.tipo_pix,
            'chave_pix': conta.chave_pix,
            'principal': conta.principal,
            'cobranca_registrada': conta.cobranca_registrada,
            'prazo_baixa': conta.prazo_baixa,
            'prazo_protesto': conta.prazo_protesto,
            'layout_cnab': conta.layout_cnab,
            'numero_remessa_cnab_atual': conta.numero_remessa_cnab_atual,
        }

        return JsonResponse({'status': 'success', 'conta': data})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_criar_conta_bancaria(request):
    """Cria uma nova conta bancária"""
    try:
        data = json.loads(request.body)

        imobiliaria = get_object_or_404(Imobiliaria, pk=data.get('imobiliaria_id'), ativo=True)

        conta = ContaBancaria.objects.create(
            imobiliaria=imobiliaria,
            banco=data.get('banco', ''),
            descricao=data.get('descricao', ''),
            agencia=data.get('agencia', ''),
            conta=data.get('conta', ''),
            convenio=data.get('convenio', ''),
            carteira=data.get('carteira', ''),
            nosso_numero_atual=data.get('nosso_numero_atual', 0),
            modalidade=data.get('modalidade', ''),
            tipo_pix=data.get('tipo_pix', ''),
            chave_pix=data.get('chave_pix', ''),
            principal=data.get('principal', False),
            cobranca_registrada=data.get('cobranca_registrada', True),
            prazo_baixa=data.get('prazo_baixa', 0),
            prazo_protesto=data.get('prazo_protesto', 0),
            layout_cnab=data.get('layout_cnab', 'CNAB_240'),
            numero_remessa_cnab_atual=data.get('numero_remessa_cnab_atual', 0),
        )

        return JsonResponse({
            'status': 'success',
            'message': 'Conta bancária criada com sucesso!',
            'conta_id': conta.id
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["PUT", "POST"])
def api_atualizar_conta_bancaria(request, conta_id):
    """Atualiza uma conta bancária existente"""
    try:
        conta = get_object_or_404(ContaBancaria, pk=conta_id, ativo=True)
        data = json.loads(request.body)

        conta.banco = data.get('banco', conta.banco)
        conta.descricao = data.get('descricao', conta.descricao)
        conta.agencia = data.get('agencia', conta.agencia)
        conta.conta = data.get('conta', conta.conta)
        conta.convenio = data.get('convenio', conta.convenio)
        conta.carteira = data.get('carteira', conta.carteira)
        conta.nosso_numero_atual = data.get('nosso_numero_atual', conta.nosso_numero_atual)
        conta.modalidade = data.get('modalidade', conta.modalidade)
        conta.tipo_pix = data.get('tipo_pix', conta.tipo_pix)
        conta.chave_pix = data.get('chave_pix', conta.chave_pix)
        conta.principal = data.get('principal', conta.principal)
        conta.cobranca_registrada = data.get('cobranca_registrada', conta.cobranca_registrada)
        conta.prazo_baixa = data.get('prazo_baixa', conta.prazo_baixa)
        conta.prazo_protesto = data.get('prazo_protesto', conta.prazo_protesto)
        conta.layout_cnab = data.get('layout_cnab', conta.layout_cnab)
        conta.numero_remessa_cnab_atual = data.get('numero_remessa_cnab_atual', conta.numero_remessa_cnab_atual)
        conta.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Conta bancária atualizada com sucesso!'
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["DELETE", "POST"])
def api_excluir_conta_bancaria(request, conta_id):
    """Exclui (soft delete) uma conta bancária"""
    try:
        conta = get_object_or_404(ContaBancaria, pk=conta_id, ativo=True)
        conta.ativo = False
        conta.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Conta bancária removida com sucesso!'
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_listar_bancos(request):
    """Lista todos os bancos disponíveis e layouts CNAB"""
    bancos = [{'codigo': choice[0], 'nome': choice[1]} for choice in BancoBrasil.choices]
    layouts = [{'codigo': choice[0], 'nome': choice[1]} for choice in LayoutCNAB.choices]
    return JsonResponse({
        'status': 'success',
        'bancos': bancos,
        'layouts_cnab': layouts
    })


# =============================================================================
# CRUD VIEWS - ACESSO USUÁRIO
# =============================================================================

class AcessoUsuarioListView(LoginRequiredMixin, ListView):
    """Lista todos os acessos de usuários"""
    model = AcessoUsuario
    template_name = 'core/acesso_list.html'
    context_object_name = 'acessos'
    paginate_by = 20

    def get_queryset(self):
        queryset = AcessoUsuario.objects.filter(ativo=True).select_related(
            'usuario', 'contabilidade', 'imobiliaria'
        ).order_by('usuario__username', 'contabilidade__nome', 'imobiliaria__nome')

        # Filtros
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(usuario__username__icontains=search) |
                Q(usuario__first_name__icontains=search) |
                Q(contabilidade__nome__icontains=search) |
                Q(imobiliaria__nome__icontains=search)
            )

        usuario_id = self.request.GET.get('usuario')
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)

        contabilidade_id = self.request.GET.get('contabilidade')
        if contabilidade_id:
            queryset = queryset.filter(contabilidade_id=contabilidade_id)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_acessos'] = AcessoUsuario.objects.filter(ativo=True).count()
        context['search'] = self.request.GET.get('search', '')
        context['usuarios'] = get_user_model().objects.filter(is_active=True).order_by('username')
        context['contabilidades'] = Contabilidade.objects.filter(ativo=True).order_by('nome')
        return context


class AcessoUsuarioCreateView(LoginRequiredMixin, CreateView):
    """Cria um novo acesso de usuário"""
    model = AcessoUsuario
    form_class = AcessoUsuarioForm
    template_name = 'core/acesso_form.html'
    success_url = reverse_lazy('core:listar_acessos')

    def form_valid(self, form):
        messages.success(
            self.request,
            f'Acesso de {form.instance.usuario.username} a {form.instance.imobiliaria.nome} criado com sucesso!'
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao criar acesso. Verifique os dados.')
        return super().form_invalid(form)


class AcessoUsuarioUpdateView(LoginRequiredMixin, UpdateView):
    """Atualiza um acesso de usuário existente"""
    model = AcessoUsuario
    form_class = AcessoUsuarioForm
    template_name = 'core/acesso_form.html'
    success_url = reverse_lazy('core:listar_acessos')

    def get_queryset(self):
        return AcessoUsuario.objects.filter(ativo=True)

    def form_valid(self, form):
        messages.success(self.request, 'Acesso atualizado com sucesso!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao atualizar acesso. Verifique os dados.')
        return super().form_invalid(form)


class AcessoUsuarioDeleteView(LoginRequiredMixin, DeleteView):
    """Desativa um acesso de usuário (soft delete)"""
    model = AcessoUsuario
    success_url = reverse_lazy('core:listar_acessos')

    def get_queryset(self):
        return AcessoUsuario.objects.filter(ativo=True)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.ativo = False
        self.object.save()
        messages.success(
            request,
            f'Acesso de {self.object.usuario.username} a {self.object.imobiliaria.nome} removido!'
        )
        return redirect(self.success_url)


# =============================================================================
# API VIEWS - ACESSO USUÁRIO (para AJAX)
# =============================================================================

@login_required
@require_http_methods(["GET"])
def api_listar_imobiliarias_por_contabilidade(request, contabilidade_id):
    """Lista imobiliárias de uma contabilidade específica (para dropdown dinâmico)"""
    try:
        contabilidade = get_object_or_404(Contabilidade, pk=contabilidade_id, ativo=True)
        imobiliarias = contabilidade.imobiliarias.filter(ativo=True).order_by('nome')

        data = [{'id': i.id, 'nome': i.nome} for i in imobiliarias]

        return JsonResponse({'status': 'success', 'imobiliarias': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_listar_acessos_usuario(request, usuario_id):
    """Lista todos os acessos de um usuário específico"""
    try:
        User = get_user_model()
        usuario = get_object_or_404(User, pk=usuario_id)
        acessos = AcessoUsuario.objects.filter(
            usuario=usuario, ativo=True
        ).select_related('contabilidade', 'imobiliaria')

        data = []
        for acesso in acessos:
            data.append({
                'id': acesso.id,
                'contabilidade': {
                    'id': acesso.contabilidade.id,
                    'nome': acesso.contabilidade.nome
                },
                'imobiliaria': {
                    'id': acesso.imobiliaria.id,
                    'nome': acesso.imobiliaria.nome
                },
                'pode_editar': acesso.pode_editar,
                'pode_excluir': acesso.pode_excluir
            })

        return JsonResponse({'status': 'success', 'acessos': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
