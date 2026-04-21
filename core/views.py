"""
Views do app Core

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
# csrf_exempt removido por questões de segurança - endpoints agora verificam permissões
from django.core.management import call_command
from django.db import connection
from django.contrib.auth import get_user_model
from django.db.models import Sum, Q
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from datetime import datetime, timedelta
from django.utils import timezone
from .mixins import PaginacaoMixin
from .models import (
    Contabilidade, Imobiliaria, Imovel, Comprador,
    ContaBancaria, BancoBrasil, LayoutCNAB, AcessoUsuario, VerticePoligono,
    get_contabilidades_usuario, get_imobiliarias_usuario,
    usuario_tem_acesso_imobiliaria, usuario_tem_acesso_contabilidade,
    usuario_tem_permissao_total
)
from .forms import ContabilidadeForm, CompradorForm, ImovelForm, ImobiliariaForm, AcessoUsuarioForm
from django.core.cache import cache
import io
import json
import logging

logger = logging.getLogger(__name__)


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


# =============================================================================
# HEALTH CHECK - MONITORAMENTO
# =============================================================================

def health_check(request):
    """
    Endpoint para verificação de saúde da aplicação.

    Retorna JSON com status dos serviços:
    - database: Conexão com o banco de dados
    - cache: Conexão com Redis (se configurado)

    Códigos HTTP:
    - 200: Sistema saudável
    - 503: Sistema com problemas
    """
    import time
    start_time = time.time()

    status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'checks': {
            'database': {'status': 'unknown', 'latency_ms': None},
            'cache': {'status': 'unknown', 'latency_ms': None},
        }
    }

    # Verificar banco de dados
    try:
        db_start = time.time()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        db_latency = (time.time() - db_start) * 1000
        status['checks']['database'] = {
            'status': 'healthy',
            'latency_ms': round(db_latency, 2)
        }
    except Exception as e:
        logger.exception("Health check: falha no banco de dados: %s", e)
        status['status'] = 'unhealthy'
        status['checks']['database'] = {
            'status': 'unhealthy',
            'error': str(e)
        }

    # Verificar cache/Redis
    try:
        from django.core.cache import cache
        cache_start = time.time()
        cache.set('health_check_test', 'ok', 10)
        result = cache.get('health_check_test')
        cache_latency = (time.time() - cache_start) * 1000

        if result == 'ok':
            status['checks']['cache'] = {
                'status': 'healthy',
                'latency_ms': round(cache_latency, 2)
            }
        else:
            status['checks']['cache'] = {
                'status': 'degraded',
                'message': 'Cache read/write mismatch'
            }
    except Exception as e:
        # Cache não é crítico, então não marca como unhealthy
        status['checks']['cache'] = {
            'status': 'unavailable',
            'message': str(e)
        }

    # Tempo total de verificação
    status['total_latency_ms'] = round((time.time() - start_time) * 1000, 2)

    http_status = 200 if status['status'] == 'healthy' else 503
    return JsonResponse(status, status=http_status)


def index(request):
    """Página inicial do sistema"""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    # Redirecionar para setup SOMENTE se não houver nenhum superusuário cadastrado
    try:
        has_superuser = User.objects.filter(is_superuser=True).exists()
    except Exception:
        has_superuser = False

    if not has_superuser:
        return redirect('core:setup')

    try:
        context = {
            'total_contabilidades': Contabilidade.objects.filter(ativo=True).count(),
            'total_imobiliarias': Imobiliaria.objects.filter(ativo=True).count(),
            'total_imoveis': Imovel.objects.filter(ativo=True).count(),
            'total_compradores': Comprador.objects.filter(ativo=True).count(),
        }
    except Exception:
        context = {
            'total_contabilidades': 0,
            'total_imobiliarias': 0,
            'total_imoveis': 0,
            'total_compradores': 0,
        }
    return render(request, 'core/index.html', context)


@login_required
def dashboard(request):
    """Dashboard principal com estatísticas"""
    from contratos.models import Contrato, StatusContrato
    from financeiro.models import Parcela

    hoje = timezone.now().date()
    inicio_mes = hoje.replace(day=1)
    fim_mes = (inicio_mes + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    # -------------------------------------------------------------------------
    # Agregados com cache de 5 minutos (contagens e somas que não mudam por segundo)
    # -------------------------------------------------------------------------
    cache_key = f'dashboard:stats:{hoje.isoformat()}'
    stats = cache.get(cache_key)

    if stats is None:
        total_contabilidades = Contabilidade.objects.filter(ativo=True).count()
        total_imobiliarias = Imobiliaria.objects.filter(ativo=True).count()
        total_imoveis = Imovel.objects.filter(ativo=True).count()
        imoveis_disponiveis = Imovel.objects.filter(ativo=True, disponivel=True).count()
        total_compradores = Comprador.objects.filter(ativo=True).count()
        total_contratos = Contrato.objects.filter(status=StatusContrato.ATIVO).count()

        parcelas_vencidas = Parcela.objects.filter(
            pago=False, data_vencimento__lt=hoje
        ).count()

        parcelas_mes = Parcela.objects.filter(
            pago=False,
            data_vencimento__gte=inicio_mes,
            data_vencimento__lte=fim_mes,
        ).count()

        valor_recebido = Parcela.objects.filter(
            pago=True,
            data_pagamento__gte=inicio_mes,
            data_pagamento__lte=fim_mes,
        ).aggregate(total=Sum('valor_pago'))['total'] or 0

        boletos_pendentes = Parcela.objects.filter(
            pago=False, status_boleto='NAO_GERADO'
        ).count()
        boletos_gerados = Parcela.objects.filter(
            pago=False, status_boleto__in=['GERADO', 'REGISTRADO']
        ).count()
        boletos_vencidos = Parcela.objects.filter(
            pago=False,
            status_boleto__in=['GERADO', 'REGISTRADO', 'VENCIDO'],
            data_vencimento__lt=hoje,
        ).count()

        valor_recebido_formatado = (
            f"{valor_recebido:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        )

        stats = {
            'total_contabilidades': total_contabilidades,
            'total_imobiliarias': total_imobiliarias,
            'total_imoveis': total_imoveis,
            'imoveis_disponiveis': imoveis_disponiveis,
            'total_compradores': total_compradores,
            'total_contratos': total_contratos,
            'parcelas_vencidas': parcelas_vencidas,
            'parcelas_mes': parcelas_mes,
            'valor_recebido_mes': valor_recebido_formatado,
            'boletos_pendentes': boletos_pendentes,
            'boletos_gerados': boletos_gerados,
            'boletos_vencidos': boletos_vencidos,
        }
        cache.set(cache_key, stats, timeout=300)  # 5 minutos

    # -------------------------------------------------------------------------
    # Listas detalhadas — consultadas a cada request (pequenas, com .select_related)
    # -------------------------------------------------------------------------
    parcelas_vencidas_lista = list(
        Parcela.objects.filter(pago=False, data_vencimento__lt=hoje)
        .select_related('contrato', 'contrato__comprador')
        .order_by('-data_vencimento')[:10]
    )

    proximas_parcelas = list(
        Parcela.objects.filter(
            pago=False,
            data_vencimento__gte=hoje,
            data_vencimento__lte=hoje + timedelta(days=15),
        )
        .select_related('contrato', 'contrato__comprador')
        .order_by('data_vencimento')[:10]
    )
    for parcela in proximas_parcelas:
        parcela.dias_para_vencer = (parcela.data_vencimento - hoje).days

    context = {
        **stats,
        'parcelas_vencidas_lista': parcelas_vencidas_lista,
        'proximas_parcelas': proximas_parcelas,
    }
    return render(request, 'core/dashboard.html', context)


def _build_setup_context():
    """
    Monta o contexto exibido pela tela de setup/geração de dados.
    Compartilhado por `setup` (/setup/) e `pagina_dados_teste` (/dados-teste/)
    para manter uma única tela unificada com o passo-a-passo.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_ok = True
        tables = connection.introspection.table_names()
        has_tables = len(tables) > 0
    except Exception:
        db_ok = False
        has_tables = False

    total_contabilidades = 0
    total_users = 0
    has_superuser = False
    total_contas_bancarias = 0
    total_imobiliarias = 0

    if has_tables:
        try:
            total_contabilidades = Contabilidade.objects.count()
            total_users = get_user_model().objects.count()
            has_superuser = get_user_model().objects.filter(is_superuser=True).exists()
            total_contas_bancarias = ContaBancaria.objects.count()
            total_imobiliarias = Imobiliaria.objects.count()
        except Exception:
            pass

    return {
        'db_ok': db_ok,
        'has_tables': has_tables,
        'total_contabilidades': total_contabilidades,
        'total_users': total_users,
        'has_superuser': has_superuser,
        'total_contas_bancarias': total_contas_bancarias,
        'total_imobiliarias': total_imobiliarias,
    }


def setup(request):
    """
    Página de setup inicial do sistema
    Executa migrations, cria superuser e opcionalmente gera dados de teste

    Acessível via: /setup/
    NOTA: Endpoint protegido - requer superusuário para ações POST
    """
    if request.method == 'GET':
        return render(request, 'core/setup.html', _build_setup_context())

    # POST - Executar setup (requer autenticação para ações sensíveis)
    # Verificar se é primeira configuração (sem usuários) ou se usuário é superuser
    User = get_user_model()
    try:
        is_first_setup = User.objects.count() == 0
    except Exception:
        # Tabelas ainda não existem (migrations não foram executadas) — permitir acesso livre
        is_first_setup = True

    if not is_first_setup:
        if not request.user.is_authenticated:
            return JsonResponse({
                'status': 'error',
                'message': 'Autenticação necessária. Faça login como admin.'
            }, status=401)
        if not request.user.is_superuser:
            return JsonResponse({
                'status': 'error',
                'message': 'Acesso negado. Apenas superusuários podem executar o setup.'
            }, status=403)

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
                call_command('gerar_dados_teste', limpar=True, stdout=out)
                messages.append('✅ Dados de teste gerados!')

            messages.append('🎉 Setup completo finalizado!')

        output = out.getvalue()

        return JsonResponse({
            'status': 'success',
            'messages': messages,
            'output': output
        })

    except Exception as e:
        logger.exception("Setup: erro na execução: %s", e)
        return JsonResponse({
            'status': 'error',
            'message': f'Erro no setup: {str(e)}'
        }, status=500)


@require_http_methods(["GET", "POST"])
def gerar_dados_teste(request):
    """
    Endpoint para gerar dados de teste (ACESSÍVEL SEM LOGIN para ambiente de teste)

    GET: Retorna status do sistema
    POST: Gera dados de teste

    Parâmetros POST (form-data ou JSON):
        limpar (bool): Se deve limpar dados antes (default: False)

    Exemplo de uso:
        curl -X POST http://localhost:8000/api/gerar-dados-teste/ -d "limpar=true"
        curl -X POST http://localhost:8000/api/gerar-dados-teste/ -H "Content-Type: application/json" -d '{"limpar": true}'
    """
    # NOTA: Endpoint liberado para facilitar setup em ambiente Render Free
    # Em produção real, adicionar verificação de token ou IP
    # Importar modelos adicionais
    from contratos.models import Contrato, IndiceReajuste
    from financeiro.models import Parcela

    if request.method == 'GET':
        # Retornar estatísticas atuais
        try:
            return JsonResponse({
                'status': 'ok',
                'endpoint': '/api/gerar-dados-teste/',
                'metodos': ['GET', 'POST'],
                'parametros': {
                    'limpar': 'bool - Se true, limpa todos os dados antes de gerar novos'
                },
                'dados_existentes': {
                    'contabilidades': Contabilidade.objects.count(),
                    'imobiliarias': Imobiliaria.objects.count(),
                    'contas_bancarias': ContaBancaria.objects.count(),
                    'imoveis': Imovel.objects.count(),
                    'compradores': Comprador.objects.count(),
                    'contratos': Contrato.objects.count(),
                    'parcelas': Parcela.objects.count(),
                    'indices_reajuste': IndiceReajuste.objects.count(),
                }
            })
        except Exception as e:
            logger.exception("Erro ao verificar status do banco: %s", e)
            return JsonResponse({
                'status': 'error',
                'message': 'Banco de dados não configurado. Acesse /setup/ primeiro.',
                'error': str(e)
            }, status=500)

    # POST - Gerar dados
    try:
        # Aceitar tanto form-data quanto JSON
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                limpar = data.get('limpar', False)
            except Exception:
                limpar = False
        else:
            limpar = request.POST.get('limpar', 'false').lower() == 'true'

        # Capturar output do comando
        out = io.StringIO()

        # Executar comando
        call_command('gerar_dados_teste', limpar=limpar, stdout=out)

        output = out.getvalue()

        from contratos.models import TabelaJurosContrato
        # Retornar sucesso
        return JsonResponse({
            'status': 'success',
            'message': 'Dados gerados com sucesso!',
            'output': output,
            'dados_gerados': {
                'contabilidades': Contabilidade.objects.count(),
                'imobiliarias': Imobiliaria.objects.count(),
                'contas_bancarias': ContaBancaria.objects.count(),
                'imoveis': Imovel.objects.count(),
                'compradores': Comprador.objects.count(),
                'contratos': Contrato.objects.count(),
                'parcelas': Parcela.objects.count(),
                'indices_reajuste': IndiceReajuste.objects.count(),
                'tabela_juros': TabelaJurosContrato.objects.count(),
            }
        })

    except Exception as e:
        logger.exception("Erro ao gerar dados de teste: %s", e)
        import traceback
        return JsonResponse({
            'status': 'error',
            'message': 'Erro ao gerar dados',
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


@require_http_methods(["GET", "POST", "DELETE"])
def limpar_dados_teste(request):
    """
    Endpoint para limpar dados de teste (APENAS ADMIN/SUPERUSUÁRIO)

    GET: Retorna estatísticas dos dados que serão excluídos
    POST/DELETE: Exclui todos os dados de teste

    Parâmetros POST (form-data ou JSON):
        confirmar (bool): Confirmação de exclusão (default: False)

    Exemplo de uso:
        curl -X DELETE http://localhost:8000/api/limpar-dados-teste/ -H "Content-Type: application/json" -d '{"confirmar": true}'
    """
    # Verificar se usuário é admin/superusuário para operações de exclusão
    if request.method in ['POST', 'DELETE']:
        if not request.user.is_authenticated:
            return JsonResponse({
                'status': 'error',
                'message': 'Autenticação necessária. Faça login como admin.',
            }, status=401)

        if not (request.user.is_superuser or request.user.is_staff):
            return JsonResponse({
                'status': 'error',
                'message': 'Acesso negado. Apenas administradores podem excluir dados.',
            }, status=403)

    # Importar modelos adicionais
    from contratos.models import Contrato, IndiceReajuste
    from financeiro.models import Parcela

    if request.method == 'GET':
        # Retornar estatísticas dos dados que serão excluídos
        try:
            return JsonResponse({
                'status': 'ok',
                'endpoint': '/api/limpar-dados-teste/',
                'metodos': ['GET', 'POST', 'DELETE'],
                'aviso': 'Esta ação irá EXCLUIR PERMANENTEMENTE todos os dados!',
                'parametros': {
                    'confirmar': 'bool - Deve ser true para confirmar a exclusão'
                },
                'dados_a_excluir': {
                    'parcelas': Parcela.objects.count(),
                    'contratos': Contrato.objects.count(),
                    'indices_reajuste': IndiceReajuste.objects.count(),
                    'imoveis': Imovel.objects.count(),
                    'compradores': Comprador.objects.count(),
                    'imobiliarias': Imobiliaria.objects.count(),
                    'contabilidades': Contabilidade.objects.count(),
                }
            })
        except Exception as e:
            logger.exception("Erro ao verificar status do banco: %s", e)
            return JsonResponse({
                'status': 'error',
                'message': 'Banco de dados não configurado.',
                'error': str(e)
            }, status=500)

    # POST/DELETE - Limpar dados
    try:
        # Aceitar tanto form-data quanto JSON
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                confirmar = data.get('confirmar', False)
            except Exception:
                confirmar = False
        else:
            confirmar = request.POST.get('confirmar', 'false').lower() == 'true'

        if not confirmar:
            return JsonResponse({
                'status': 'error',
                'message': 'Confirmação necessária. Envie {"confirmar": true} para excluir os dados.',
            }, status=400)

        # Contar dados antes de excluir
        dados_excluidos = {
            'parcelas': Parcela.objects.count(),
            'contratos': Contrato.objects.count(),
            'indices_reajuste': IndiceReajuste.objects.count(),
            'imoveis': Imovel.objects.count(),
            'compradores': Comprador.objects.count(),
            'imobiliarias': Imobiliaria.objects.count(),
            'contabilidades': Contabilidade.objects.count(),
        }

        # Excluir na ordem correta (respeitar FKs)
        Parcela.objects.all().delete()
        Contrato.objects.all().delete()
        IndiceReajuste.objects.all().delete()
        Imovel.objects.all().delete()
        Comprador.objects.all().delete()
        Imobiliaria.objects.all().delete()
        Contabilidade.objects.all().delete()

        return JsonResponse({
            'status': 'success',
            'message': 'Dados excluídos com sucesso!',
            'dados_excluidos': dados_excluidos,
            'dados_restantes': {
                'parcelas': Parcela.objects.count(),
                'contratos': Contrato.objects.count(),
                'indices_reajuste': IndiceReajuste.objects.count(),
                'imoveis': Imovel.objects.count(),
                'compradores': Comprador.objects.count(),
                'imobiliarias': Imobiliaria.objects.count(),
                'contabilidades': Contabilidade.objects.count(),
            }
        })

    except Exception as e:
        import traceback
        logger.exception("Erro ao limpar dados: %s", e)
        return JsonResponse({
            'status': 'error',
            'message': 'Erro ao limpar dados',
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


# =============================================================================
# CRUD VIEWS - CONTABILIDADE
# =============================================================================

class ContabilidadeListView(LoginRequiredMixin, PaginacaoMixin, ListView):
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
        # Monta mensagem de erro detalhada
        erros = []
        for campo, lista_erros in form.errors.items():
            nome_campo = form.fields[campo].label if campo in form.fields else campo
            for erro in lista_erros:
                erros.append(f'{nome_campo}: {erro}')

        if erros:
            messages.error(self.request, f'Erro ao cadastrar: {"; ".join(erros[:3])}')
        else:
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
        # Monta mensagem de erro detalhada
        erros = []
        for campo, lista_erros in form.errors.items():
            nome_campo = form.fields[campo].label if campo in form.fields else campo
            for erro in lista_erros:
                erros.append(f'{nome_campo}: {erro}')

        if erros:
            messages.error(self.request, f'Erro ao atualizar: {"; ".join(erros[:3])}')
        else:
            messages.error(self.request, 'Erro ao atualizar contabilidade. Verifique os dados.')
        return super().form_invalid(form)


class ContabilidadeDeleteView(LoginRequiredMixin, DeleteView):
    """Desativa uma contabilidade (soft delete)"""
    model = Contabilidade
    success_url = reverse_lazy('core:listar_contabilidades')

    def get_queryset(self):
        return Contabilidade.objects.filter(ativo=True)

    def form_valid(self, form):
        self.object = self.get_object()
        self.object.ativo = False
        self.object.save()
        messages.success(self.request, f'Contabilidade {self.object.nome} removida com sucesso!')
        return redirect(self.success_url)


# =============================================================================
# 3.20 — CONFIGURAÇÕES DA CONTABILIDADE
# =============================================================================

@login_required
def contabilidade_configuracoes(request, pk):
    """
    3.20 — Página de configurações da Contabilidade.

    Consolida em uma única view:
    - Dados cadastrais (editar inline)
    - Imobiliárias vinculadas
    - Usuários com acesso (via AcessoUsuario)
    """
    from .models import AcessoUsuario

    contabilidade = get_object_or_404(Contabilidade, pk=pk, ativo=True)

    if request.method == 'POST':
        form = ContabilidadeForm(request.POST, instance=contabilidade)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configurações da contabilidade atualizadas com sucesso!')
            return redirect('core:contabilidade_configuracoes', pk=pk)
        else:
            messages.error(request, 'Erro ao salvar. Verifique os campos.')
    else:
        form = ContabilidadeForm(instance=contabilidade)

    imobiliarias = contabilidade.imobiliarias.filter(ativo=True).order_by('nome')
    acessos = AcessoUsuario.objects.filter(
        contabilidade=contabilidade
    ).select_related('usuario', 'imobiliaria').order_by('usuario__username')

    # Estatísticas rápidas
    from contratos.models import Contrato
    total_contratos = Contrato.objects.filter(
        imobiliaria__in=imobiliarias
    ).count()
    total_ativos = Contrato.objects.filter(
        imobiliaria__in=imobiliarias, status='ATIVO'
    ).count()

    context = {
        'contabilidade': contabilidade,
        'form': form,
        'imobiliarias': imobiliarias,
        'acessos': acessos,
        'total_imobiliarias': imobiliarias.count(),
        'total_contratos': total_contratos,
        'total_contratos_ativos': total_ativos,
    }
    return render(request, 'core/contabilidade_configuracoes.html', context)


# =============================================================================
# CRUD VIEWS - COMPRADOR
# =============================================================================

class CompradorListView(LoginRequiredMixin, PaginacaoMixin, ListView):
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

    def form_valid(self, form):
        self.object = self.get_object()
        self.object.ativo = False
        self.object.save()
        messages.success(self.request, f'Comprador {self.object.nome} removido com sucesso!')
        return redirect(self.success_url)


# =============================================================================
# CRUD VIEWS - IMOVEL
# =============================================================================

class ImovelListView(LoginRequiredMixin, PaginacaoMixin, ListView):
    """Lista todos os imóveis ativos"""
    model = Imovel
    template_name = 'core/imovel_list.html'
    context_object_name = 'imoveis'
    paginate_by = 20

    def get_queryset(self):
        queryset = Imovel.objects.filter(ativo=True).select_related('imobiliaria').prefetch_related('contratos').order_by('-criado_em')

        # Filtros
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(identificacao__icontains=search) |
                Q(loteamento__icontains=search) |
                Q(cidade__icontains=search) |
                Q(bairro__icontains=search)
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
        ativos = Imovel.objects.filter(ativo=True)
        context['total_imoveis'] = ativos.count()
        context['imoveis_disponiveis'] = ativos.filter(disponivel=True).count()

        # Todos os imóveis com coordenadas — passados ao mapa (não paginado)
        todos_mapa = ativos.filter(
            latitude__isnull=False,
            longitude__isnull=False
        ).select_related('imobiliaria').prefetch_related('vertices').order_by('loteamento', 'identificacao')
        context['todos_imoveis_mapa'] = todos_mapa
        context['imoveis_com_coordenadas'] = todos_mapa.count()

        # M-13: dados de polígonos serializados para o mapa
        poligonos = {}
        for im in todos_mapa:
            verts = [
                {'lat': float(v.latitude), 'lng': float(v.longitude)}
                for v in im.vertices.all()
            ]
            if verts:
                poligonos[im.pk] = verts
        import json as _json
        context['poligonos_json'] = _json.dumps(poligonos)

        # Lista de loteamentos distintos para o filtro do mapa
        context['loteamentos'] = (
            ativos.exclude(loteamento='').exclude(loteamento__isnull=True)
            .values_list('loteamento', flat=True)
            .distinct().order_by('loteamento')
        )
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

    def form_valid(self, form):
        self.object = self.get_object()
        self.object.ativo = False
        self.object.save()
        messages.success(self.request, f'Imóvel {self.object.identificacao} removido com sucesso!')
        return redirect(self.success_url)


# =============================================================================
# LOTEAMENTO DEDICATED PAGE — M-11 / M-12
# =============================================================================

@login_required
def loteamento_detalhe(request, nome):
    """
    Página dedicada de um loteamento/empreendimento.
    M-11: mapa e lista de lotes.
    M-12: estatísticas (total, disponíveis %, valor médio).
    """
    from django.db.models import Avg, Min, Max
    import urllib.parse

    # Resolve nome (URL pode ter + ou %20 para espaços)
    nome = urllib.parse.unquote(nome)

    imoveis = (
        Imovel.objects.filter(ativo=True, loteamento__iexact=nome)
        .select_related('imobiliaria')
        .prefetch_related('contratos')
        .order_by('identificacao')
    )

    if not imoveis.exists():
        messages.error(request, f'Loteamento "{nome}" não encontrado.')
        return redirect('core:listar_imoveis')

    total = imoveis.count()
    disponiveis = imoveis.filter(disponivel=True).count()
    vendidos = total - disponiveis
    pct_disponivel = round(disponiveis / total * 100) if total else 0
    pct_vendido = 100 - pct_disponivel

    stats_valor = imoveis.filter(valor__isnull=False).aggregate(
        media=Avg('valor'),
        minimo=Min('valor'),
        maximo=Max('valor'),
    )

    imoveis_mapa = imoveis.filter(
        latitude__isnull=False,
        longitude__isnull=False,
    )

    # Filtro de disponibilidade
    filtro_disp = request.GET.get('disponivel', '')
    lista_imoveis = imoveis
    if filtro_disp == 'true':
        lista_imoveis = imoveis.filter(disponivel=True)
    elif filtro_disp == 'false':
        lista_imoveis = imoveis.filter(disponivel=False)

    context = {
        'nome_loteamento': nome,
        'imoveis': lista_imoveis,
        'imoveis_mapa': imoveis_mapa,
        'total': total,
        'disponiveis': disponiveis,
        'vendidos': vendidos,
        'pct_disponivel': pct_disponivel,
        'pct_vendido': pct_vendido,
        'valor_medio': stats_valor['media'],
        'valor_minimo': stats_valor['minimo'],
        'valor_maximo': stats_valor['maximo'],
        'filtro_disp': filtro_disp,
    }
    return render(request, 'core/loteamento_detalhe.html', context)


# =============================================================================
# CRUD VIEWS - IMOBILIARIA
# =============================================================================

class ImobiliariaListView(LoginRequiredMixin, PaginacaoMixin, ListView):
    """Lista todas as imobiliárias ativas"""
    model = Imobiliaria
    template_name = 'core/imobiliaria_list.html'
    context_object_name = 'imobiliarias'
    paginate_by = 20

    def get_queryset(self):
        queryset = Imobiliaria.objects.filter(ativo=True).select_related('contabilidade').prefetch_related('contas_bancarias').order_by('-criado_em')

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

        # Adicionar conta principal para cada imobiliária
        imobiliarias = context.get('imobiliarias', [])
        for imobiliaria in imobiliarias:
            imobiliaria.conta_principal = imobiliaria.contas_bancarias.filter(principal=True, ativo=True).first()

        return context


class ImobiliariaCreateView(LoginRequiredMixin, CreateView):
    """Cria uma nova imobiliária"""
    model = Imobiliaria
    form_class = ImobiliariaForm
    template_name = 'core/imobiliaria_form.html'
    success_url = reverse_lazy('core:listar_imobiliarias')

    def form_valid(self, form):
        super().form_valid(form)

        # Criar acesso automático para o usuário que criou (se não for admin/superuser)
        user = self.request.user
        if not usuario_tem_permissao_total(user):
            AcessoUsuario.objects.get_or_create(
                usuario=user,
                contabilidade=self.object.contabilidade,
                imobiliaria=self.object,
                defaults={
                    'pode_editar': True,
                    'pode_excluir': False
                }
            )

        messages.success(self.request, f'Imobiliária {form.instance.nome} cadastrada com sucesso!')

        # Processar contas bancárias do JSON (se houver)
        contas_json = self.request.POST.get('contas_bancarias_json', '')
        if contas_json:
            import json
            try:
                contas = json.loads(contas_json)
                for conta_data in contas:
                    # Mesclar agencia_dv com agencia se fornecido
                    agencia = conta_data.get('agencia', '')
                    agencia_dv = conta_data.get('agencia_dv', '')
                    if agencia and agencia_dv:
                        agencia_completa = f"{agencia}-{agencia_dv}"
                    else:
                        agencia_completa = agencia

                    # Mesclar conta_dv com conta se fornecido
                    conta = conta_data.get('conta', '')
                    conta_dv = conta_data.get('conta_dv', '')
                    if conta and conta_dv:
                        conta_completa = f"{conta}-{conta_dv}"
                    else:
                        conta_completa = conta

                    ContaBancaria.objects.create(
                        imobiliaria=self.object,
                        banco=conta_data.get('banco', ''),
                        descricao=conta_data.get('descricao', ''),
                        agencia=agencia_completa,
                        conta=conta_completa,
                        convenio=conta_data.get('convenio', ''),
                        carteira=conta_data.get('carteira', ''),
                        principal=conta_data.get('principal', False),
                    )
            except (json.JSONDecodeError, Exception) as e:
                logger.exception("Erro ao salvar contas bancárias na criação da imobiliária: %s", e)
                messages.warning(self.request, f'Imobiliária criada, mas houve erro ao salvar contas bancárias: {e}')

        return redirect(self.success_url)

    def form_invalid(self, form):
        # Monta mensagem de erro detalhada
        erros = []
        for campo, lista_erros in form.errors.items():
            nome_campo = form.fields[campo].label if campo in form.fields else campo
            for erro in lista_erros:
                erros.append(f'{nome_campo}: {erro}')

        if erros:
            messages.error(self.request, f'Erro ao cadastrar: {"; ".join(erros[:3])}')
        else:
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
        # Monta mensagem de erro detalhada
        erros = []
        for campo, lista_erros in form.errors.items():
            nome_campo = form.fields[campo].label if campo in form.fields else campo
            for erro in lista_erros:
                erros.append(f'{nome_campo}: {erro}')

        if erros:
            messages.error(self.request, f'Erro ao atualizar: {"; ".join(erros[:3])}')
        else:
            messages.error(self.request, 'Erro ao atualizar imobiliária. Verifique os dados.')
        return super().form_invalid(form)


class ImobiliariaDeleteView(LoginRequiredMixin, DeleteView):
    """Desativa uma imobiliária (soft delete)"""
    model = Imobiliaria
    success_url = reverse_lazy('core:listar_imobiliarias')

    def form_valid(self, form):
        self.object = self.get_object()
        self.object.ativo = False
        self.object.save()
        messages.success(self.request, f'Imobiliária {self.object.nome} removida com sucesso!')
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
        logger.exception("Erro ao listar contas bancarias imobiliaria_id=%s: %s", imobiliaria_id, e)
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
            'posto': conta.posto,
            'byte_idt': conta.byte_idt,
            'emissao': conta.emissao,
            'codigo_beneficiario': conta.codigo_beneficiario,
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
        logger.exception("Erro ao obter conta bancaria conta_id=%s: %s", conta_id, e)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
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
            posto=data.get('posto', ''),
            byte_idt=data.get('byte_idt', ''),
            emissao=data.get('emissao', ''),
            codigo_beneficiario=data.get('codigo_beneficiario', ''),
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
        logger.exception("Erro ao criar conta bancaria: %s", e)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
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
        conta.posto = data.get('posto', conta.posto)
        conta.byte_idt = data.get('byte_idt', conta.byte_idt)
        conta.emissao = data.get('emissao', conta.emissao)
        conta.codigo_beneficiario = data.get('codigo_beneficiario', conta.codigo_beneficiario)
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
        logger.exception("Erro ao atualizar conta bancaria conta_id=%s: %s", conta_id, e)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
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
        logger.exception("Erro ao excluir conta bancaria conta_id=%s: %s", conta_id, e)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_listar_bancos(request):
    """
    Lista bancos e layouts CNAB suportados.

    Consulta a API BRCobrança (boleto_cnab_api) via probe dinâmico para
    detectar quais bancos e formatos de remessa estão disponíveis.
    Se o serviço estiver indisponível usa a tabela estática como fallback.
    Resultado é cacheado por 60 min para evitar probes a cada requisição.
    """
    from django.conf import settings as _s
    from financeiro.services.bancos import descobrir_bancos_fallback
    brcobranca_url = getattr(_s, 'BRCOBRANCA_URL', 'http://localhost:9292')
    bancos = descobrir_bancos_fallback(brcobranca_url)
    layouts = [{'codigo': choice[0], 'nome': choice[1]} for choice in LayoutCNAB.choices]
    return JsonResponse({
        'status': 'success',
        'bancos': bancos,
        'layouts_cnab': layouts,
    })


# =============================================================================
# CRUD VIEWS - ACESSO USUÁRIO
# =============================================================================

class AcessoUsuarioListView(LoginRequiredMixin, PaginacaoMixin, ListView):
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

    def form_valid(self, form):
        self.object = self.get_object()
        self.object.ativo = False
        self.object.save()
        messages.success(
            self.request,
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
        logger.exception("Erro ao listar imobiliarias contabilidade_id=%s: %s", contabilidade_id, e)
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
        logger.exception("Erro ao listar acessos usuario_id=%s: %s", usuario_id, e)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# =============================================================================
# PÁGINA DE DADOS DE TESTE (Admin Only)
# =============================================================================

@login_required
def pagina_dados_teste(request):
    """
    Página HTML para gerar/limpar dados de teste.
    Apenas administradores (is_staff ou is_superuser) podem acessar.

    Renderiza a mesma tela de `/setup/` (passo-a-passo) para manter
    uma única UI para as duas rotas.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Acesso negado. Apenas administradores podem acessar esta página.')
        return redirect('core:dashboard')

    return render(request, 'core/setup.html', _build_setup_context())


# =============================================================================
# U-06: BUSCA GLOBAL (Ctrl+K)
# =============================================================================

@login_required
def api_busca_global(request):
    """
    Busca rápida global — retorna resultados agrupados por tipo.
    GET ?q=<query>  (mín. 2 chars)
    """
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': [], 'q': q})

    from django.db.models import Q as _Q
    from contratos.models import Contrato as _Contrato
    from core.models import Comprador as _Comprador, Imovel as _Imovel

    resultados = []

    # Contratos
    contratos = _Contrato.objects.filter(
        _Q(numero_contrato__icontains=q) |
        _Q(comprador__nome__icontains=q) |
        _Q(imovel__identificacao__icontains=q) |
        _Q(imovel__loteamento__icontains=q)
    ).select_related('comprador', 'imovel', 'imobiliaria').order_by('-data_contrato')[:8]

    for c in contratos:
        imovel_label = ''
        if c.imovel:
            imovel_label = c.imovel.identificacao or c.imovel.loteamento or ''
        resultados.append({
            'tipo': 'contrato',
            'icon': 'description',
            'titulo': c.numero_contrato,
            'subtitulo': f"{c.comprador.nome if c.comprador else '—'} · {imovel_label}",
            'status': c.get_status_display(),
            'url': f'/contratos/{c.pk}/',
        })

    # Compradores
    compradores = _Comprador.objects.filter(
        _Q(nome__icontains=q) |
        _Q(cpf__icontains=q) |
        _Q(cnpj__icontains=q) |
        _Q(email__icontains=q)
    ).order_by('nome')[:6]

    for cp in compradores:
        doc = cp.cpf or cp.cnpj or ''
        resultados.append({
            'tipo': 'comprador',
            'icon': 'person',
            'titulo': cp.nome,
            'subtitulo': doc,
            'status': cp.get_tipo_pessoa_display() if hasattr(cp, 'get_tipo_pessoa_display') else '',
            'url': f'/compradores/{cp.pk}/editar/',
        })

    # Imóveis
    imoveis = _Imovel.objects.filter(
        _Q(identificacao__icontains=q) |
        _Q(loteamento__icontains=q) |
        _Q(cidade__icontains=q)
    ).order_by('identificacao')[:6]

    for im in imoveis:
        resultados.append({
            'tipo': 'imovel',
            'icon': 'home',
            'titulo': im.identificacao or im.loteamento or f'Imóvel #{im.pk}',
            'subtitulo': f"{im.cidade or ''}{'/' + im.estado if im.estado else ''}" if (im.cidade or im.estado) else '',
            'status': 'Disponível' if im.disponivel else 'Vendido',
            'url': f'/imoveis/{im.pk}/editar/',
        })

    return JsonResponse({'results': resultados, 'q': q, 'total': len(resultados)})


# =============================================================================
# API - BRASILAPI (CEP e CNPJ)
# =============================================================================

@login_required
def api_buscar_cep(request, cep):
    """
    Busca endereco pelo CEP usando BrasilAPI.

    URL: /api/cep/<cep>/
    Metodo: GET

    Retorna:
    {
        "sucesso": true,
        "cep": "01310-100",
        "logradouro": "Avenida Paulista",
        "complemento": "",
        "bairro": "Bela Vista",
        "cidade": "Sao Paulo",
        "estado": "SP",
        "fonte": "BrasilAPI"
    }
    """
    from .services.brasilapi_service import buscar_cep

    resultado = buscar_cep(cep)

    if resultado and resultado.get('sucesso'):
        return JsonResponse(resultado)
    else:
        return JsonResponse(
            resultado or {'sucesso': False, 'erro': 'Erro ao buscar CEP'},
            status=404 if resultado and 'nao encontrado' in resultado.get('erro', '') else 500
        )


@login_required
def api_buscar_cnpj(request, cnpj):
    """
    Busca dados da empresa pelo CNPJ usando BrasilAPI.

    URL: /api/cnpj/<cnpj>/
    Metodo: GET

    Retorna:
    {
        "sucesso": true,
        "cnpj": "00.000.000/0001-91",
        "razao_social": "EMPRESA LTDA",
        "nome_fantasia": "EMPRESA",
        "situacao_cadastral": "ATIVA",
        "email": "contato@empresa.com",
        "telefone": "1199999999",
        "cep": "01310-100",
        "logradouro": "Avenida Paulista",
        "numero": "1000",
        "complemento": "Sala 100",
        "bairro": "Bela Vista",
        "cidade": "Sao Paulo",
        "estado": "SP",
        "fonte": "BrasilAPI"
    }
    """
    from .services.brasilapi_service import buscar_cnpj

    resultado = buscar_cnpj(cnpj)

    if resultado and resultado.get('sucesso'):
        return JsonResponse(resultado)
    else:
        erro = resultado.get('erro', '') if resultado else ''
        if 'nao encontrado' in erro.lower():
            status_code = 404
        elif 'invalido' in erro.lower():
            status_code = 400
        else:
            status_code = 500

        return JsonResponse(
            resultado or {'sucesso': False, 'erro': 'Erro ao buscar CNPJ'},
            status=status_code
        )


# ==============================================================================
# M-13: API de Polígonos de Lote
# ==============================================================================

@login_required
@require_http_methods(['GET', 'POST'])
def api_poligono_imovel(request, pk):
    """
    GET  → retorna lista de vértices [{ordem, lat, lng}]
    POST → salva/substitui todos os vértices (JSON body: {vertices: [{lat, lng}, ...]})
    """
    imovel = get_object_or_404(Imovel, pk=pk)

    if request.method == 'GET':
        vertices = imovel.vertices.values('ordem', 'latitude', 'longitude')
        data = [
            {'ordem': v['ordem'], 'lat': float(v['latitude']), 'lng': float(v['longitude'])}
            for v in vertices
        ]
        return JsonResponse({'imovel_id': pk, 'vertices': data})

    # POST — substitui vértices
    if not request.user.is_staff and not request.user.is_superuser:
        return JsonResponse({'erro': 'Sem permissão para editar polígonos.'}, status=403)

    try:
        body = json.loads(request.body)
        vertices = body.get('vertices', [])
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'erro': 'JSON inválido.'}, status=400)

    if not isinstance(vertices, list):
        return JsonResponse({'erro': 'Campo "vertices" deve ser uma lista.'}, status=400)

    # Valida e salva
    VerticePoligono.objects.filter(imovel=imovel).delete()
    novos = []
    for i, v in enumerate(vertices):
        try:
            lat = float(v['lat'])
            lng = float(v['lng'])
        except (KeyError, TypeError, ValueError):
            return JsonResponse({'erro': f'Vértice {i} inválido — precisa de lat e lng numéricos.'}, status=400)
        novos.append(VerticePoligono(imovel=imovel, ordem=i, latitude=lat, longitude=lng))

    VerticePoligono.objects.bulk_create(novos)
    return JsonResponse({'ok': True, 'salvos': len(novos)})
