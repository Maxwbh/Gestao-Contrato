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
from django.db.models import Count, Sum, Q
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from datetime import datetime, timedelta
from django.utils import timezone
from .mixins import PaginacaoMixin
from .models import (
    Contabilidade, Imobiliaria, Imovel, Comprador,
    ContaBancaria, BancoBrasil, LayoutCNAB, AcessoUsuario, VerticePoligono, LoteamentoOverlay,
    get_contabilidades_usuario, get_imobiliarias_usuario,
    usuario_tem_acesso_imobiliaria, usuario_tem_acesso_contabilidade,
    usuario_tem_permissao_total, registrar_auditoria, LogAuditoria,
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
    from financeiro.models import Parcela, StatusBoleto

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
        total_compradores = Comprador.objects.filter(ativo=True).count()
        total_contratos = Contrato.objects.filter(status=StatusContrato.ATIVO).count()

        imovel_agg = Imovel.objects.filter(ativo=True).aggregate(
            total=Count('id'),
            disponiveis=Count('id', filter=Q(disponivel=True)),
        )
        total_imoveis = imovel_agg['total']
        imoveis_disponiveis = imovel_agg['disponiveis']

        parcela_agg = Parcela.objects.aggregate(
            vencidas=Count('id', filter=Q(pago=False, data_vencimento__lt=hoje)),
            mes=Count('id', filter=Q(pago=False, data_vencimento__gte=inicio_mes, data_vencimento__lte=fim_mes)),
            valor_recebido=Sum('valor_pago', filter=Q(pago=True, data_pagamento__gte=inicio_mes, data_pagamento__lte=fim_mes)),
            boletos_pend=Count('id', filter=Q(pago=False, status_boleto=StatusBoleto.NAO_GERADO)),
            boletos_ger=Count('id', filter=Q(pago=False, status_boleto__in=[StatusBoleto.GERADO, StatusBoleto.REGISTRADO])),
            boletos_venc=Count('id', filter=Q(pago=False, data_vencimento__lt=hoje, status_boleto__in=[StatusBoleto.GERADO, StatusBoleto.REGISTRADO, StatusBoleto.VENCIDO])),
        )
        parcelas_vencidas = parcela_agg['vencidas']
        parcelas_mes = parcela_agg['mes']
        valor_recebido = parcela_agg['valor_recebido'] or 0
        boletos_pendentes = parcela_agg['boletos_pend']
        boletos_gerados = parcela_agg['boletos_ger']
        boletos_vencidos = parcela_agg['boletos_venc']

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
    total_contratos = 0
    parcelas_nao_geradas = 0
    total_remessas = 0
    total_retornos = 0
    imobiliarias_com_logo = 0

    if has_tables:
        try:
            total_contabilidades = Contabilidade.objects.count()
            total_users = get_user_model().objects.count()
            has_superuser = get_user_model().objects.filter(is_superuser=True).exists()
            total_contas_bancarias = ContaBancaria.objects.count()
            total_imobiliarias = Imobiliaria.objects.count()
            imobiliarias_com_logo = Imobiliaria.objects.exclude(logo='').exclude(logo=None).count()
        except Exception:
            pass
        try:
            from contratos.models import Contrato as _Contrato
            from financeiro.models import Parcela as _Parcela, StatusBoleto as _StatusBoleto
            from financeiro.models import ArquivoRemessa as _AR, ArquivoRetorno as _ARet
            total_contratos = _Contrato.objects.count()
            parcelas_nao_geradas = _Parcela.objects.filter(
                pago=False, status_boleto=_StatusBoleto.NAO_GERADO
            ).count()
            total_remessas = _AR.objects.count()
            total_retornos = _ARet.objects.count()
        except Exception:
            pass

    tem_dados_passo3 = total_contratos > 0

    return {
        'db_ok': db_ok,
        'has_tables': has_tables,
        'total_contabilidades': total_contabilidades,
        'total_users': total_users,
        'has_superuser': has_superuser,
        'total_contas_bancarias': total_contas_bancarias,
        'total_imobiliarias': total_imobiliarias,
        'total_contratos': total_contratos,
        'parcelas_nao_geradas': parcelas_nao_geradas,
        'tem_dados_para_boletos': total_contratos > 0,
        'total_remessas': total_remessas,
        'total_retornos': total_retornos,
        'imobiliarias_com_logo': imobiliarias_com_logo,
        'tem_dados_passo3': tem_dados_passo3,
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
        is_first_setup = not User.objects.exists()
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
                    'limpar': 'bool - Se true, limpa todos os dados antes de gerar novos',
                    'banco': 'str - Concentra 100% dos boletos no banco (001=BB, 756=Sicoob, 237=Bradesco, 336=C6)',
                },
                'geracao': _job_dados_teste_get(),
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

    # POST - Gerar dados (assíncrono: Render mata requests longos em ~100s;
    # a geração leva vários minutos → roda em thread e o cliente faz polling)
    try:
        # Aceitar tanto form-data quanto JSON
        banco = None
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                limpar = data.get('limpar', False)
                banco = data.get('banco') or None
            except Exception:
                limpar = False
        else:
            limpar = request.POST.get('limpar', 'false').lower() == 'true'
            banco = request.POST.get('banco') or None

        if banco and banco not in ('001', '756', '237', '336'):
            return JsonResponse({
                'status': 'error',
                'message': f'Banco inválido: {banco}. Use 001, 756, 237 ou 336.',
            }, status=400)

        estado = _job_dados_teste_get()
        if estado.get('status') == 'running':
            return JsonResponse({
                'status': 'running',
                'message': 'Geração já em andamento. Acompanhe pelo status.',
                'geracao': estado,
            }, status=409)

        inicio_iso = timezone.now().isoformat()

        _job_dados_teste_set({
            'status': 'running',
            'iniciado': inicio_iso,
            'limpar': limpar,
            'banco': banco,
        })

        import threading

        class _SaidaComProgresso(io.StringIO):
            """Atualiza a etapa no estado do job a cada linha de progresso —
            heartbeat para o polling do front e para a detecção de job órfão.
            Também encaminha cada linha ao logger para visibilidade no Render."""
            def write(self, s):
                r = super().write(s)
                linha = s.strip()
                if linha:
                    logger.info('[SETUP P1] %s', linha)
                    if not linha.startswith(('→', '•', '✓', '⚠', '[')):
                        try:
                            _job_dados_teste_set({
                                'status': 'running',
                                'iniciado': inicio_iso,
                                'etapa': linha[:140],
                            })
                        except Exception:
                            pass
                return r

        def _executar():
            from django.db import connection
            out = _SaidaComProgresso()
            logger.info('[SETUP P1] Iniciando geração de dados — limpar=%s banco=%s', limpar, banco)
            try:
                call_command('gerar_dados_teste', limpar=limpar, banco=banco, sem_boletos=True, stdout=out)
                from contratos.models import Contrato as _Contrato
                dados = {
                    'contabilidades': Contabilidade.objects.count(),
                    'imobiliarias': Imobiliaria.objects.count(),
                    'contas_bancarias': ContaBancaria.objects.count(),
                    'imoveis': Imovel.objects.count(),
                    'compradores': Comprador.objects.count(),
                    'contratos': _Contrato.objects.count(),
                    'parcelas': Parcela.objects.count(),
                    'indices_reajuste': IndiceReajuste.objects.count(),
                }
                logger.info('[SETUP P1] Concluído com sucesso: %s', dados)
                _job_dados_teste_set({
                    'status': 'done',
                    'iniciado': inicio_iso,
                    'finalizado': timezone.now().isoformat(),
                    'output': out.getvalue()[-8000:],
                    'dados_gerados': dados,
                })
            except Exception as exc:
                logger.exception('[SETUP P1] Erro na geração de dados: %s', exc)
                _job_dados_teste_set({
                    'status': 'error',
                    'finalizado': timezone.now().isoformat(),
                    'erro': str(exc),
                    'output': out.getvalue()[-8000:],
                })
            finally:
                connection.close()

        threading.Thread(target=_executar, daemon=True).start()

        return JsonResponse({
            'status': 'started',
            'message': 'Geração iniciada em segundo plano. Faça GET neste endpoint para acompanhar.',
        }, status=202)

    except Exception as e:
        logger.exception("Erro ao gerar dados de teste: %s", e)
        import traceback
        return JsonResponse({
            'status': 'error',
            'message': 'Erro ao gerar dados',
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


_JOB_DADOS_TESTE_CHAVE = '_job_gerar_dados_teste'
# Sem heartbeat (etapa gravada a cada passo) por este tempo → job considerado
# morto. Folga para passos legitimamente longos (cold start do brcobranca-api
# + geração de PDFs reais por lote pode levar 1-3 min entre heartbeats)
_JOB_DADOS_TESTE_STALE_MIN = 12


def _job_dados_teste_get():
    """Lê o estado da geração de dados (persistido no banco — visível entre workers)."""
    from core.models import ParametroSistema
    from datetime import timedelta
    try:
        p = ParametroSistema.objects.filter(chave=_JOB_DADOS_TESTE_CHAVE).first()
        if not p or not p.valor:
            return {}
        estado = json.loads(p.valor)
        # Worker pode ter sido reciclado no meio da geração: o job grava
        # heartbeat (etapa) a cada passo — 'running' sem atualização recente
        # é tratado como falha para liberar nova execução
        if estado.get('status') == 'running' and p.atualizado_em:
            if timezone.now() - p.atualizado_em > timedelta(minutes=_JOB_DADOS_TESTE_STALE_MIN):
                estado = {
                    'status': 'error',
                    'erro': f'Geração sem progresso há {_JOB_DADOS_TESTE_STALE_MIN} min '
                            '(o worker pode ter sido reiniciado durante um deploy). '
                            'Tente novamente.',
                }
                _job_dados_teste_set(estado)
        return estado
    except Exception:
        return {}


def _job_dados_teste_set(estado):
    from core.models import ParametroSistema
    ParametroSistema.objects.update_or_create(
        chave=_JOB_DADOS_TESTE_CHAVE,
        defaults={
            'valor': json.dumps(estado, ensure_ascii=False),
            'grupo': ParametroSistema.GRUPO_TESTE,
            'tipo': ParametroSistema.TIPO_STR,
            'descricao': 'Estado interno da geração assíncrona de dados de teste',
        },
    )


_JOB_BOLETOS_CHAVE = '_job_gerar_boletos_teste'
_JOB_BOLETOS_STALE_MIN = 20


def _job_boletos_get():
    from core.models import ParametroSistema
    from datetime import timedelta
    try:
        p = ParametroSistema.objects.filter(chave=_JOB_BOLETOS_CHAVE).first()
        if not p or not p.valor:
            return {}
        estado = json.loads(p.valor)
        if estado.get('status') == 'running' and p.atualizado_em:
            if timezone.now() - p.atualizado_em > timedelta(minutes=_JOB_BOLETOS_STALE_MIN):
                estado = {
                    'status': 'error',
                    'erro': f'Geração de boletos sem progresso há {_JOB_BOLETOS_STALE_MIN} min '
                            '(worker pode ter sido reiniciado). Tente novamente.',
                }
                _job_boletos_set(estado)
        return estado
    except Exception:
        return {}


def _job_boletos_set(estado):
    from core.models import ParametroSistema
    ParametroSistema.objects.update_or_create(
        chave=_JOB_BOLETOS_CHAVE,
        defaults={
            'valor': json.dumps(estado, ensure_ascii=False),
            'grupo': ParametroSistema.GRUPO_TESTE,
            'tipo': ParametroSistema.TIPO_STR,
            'descricao': 'Estado interno da geração assíncrona de boletos de teste',
        },
    )


@require_http_methods(["GET", "POST"])
def gerar_boletos_teste(request):
    """
    Endpoint para geração de boletos (Passo 2 do setup).

    GET: Retorna status do job de boletos.
    POST: Inicia geração assíncrona de boletos para dados existentes.

    Parâmetros POST (JSON):
        banco (str): Banco para os boletos (001, 756, 237, 336 ou null para round-robin).
    """
    if request.method == 'GET':
        return JsonResponse({'status': 'ok', 'geracao': _job_boletos_get()})

    try:
        banco = None
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                banco = data.get('banco') or None
            except Exception:
                pass
        else:
            banco = request.POST.get('banco') or None

        if banco and banco not in ('001', '756', '237', '336'):
            return JsonResponse({
                'status': 'error',
                'message': f'Banco inválido: {banco}. Use 001, 756, 237 ou 336.',
            }, status=400)

        estado = _job_boletos_get()
        if estado.get('status') == 'running':
            return JsonResponse({
                'status': 'running',
                'message': 'Geração de boletos já em andamento.',
                'geracao': estado,
            }, status=409)

        inicio_iso = timezone.now().isoformat()
        _job_boletos_set({'status': 'running', 'iniciado': inicio_iso, 'banco': banco})

        import threading

        class _SaidaBoletos(io.StringIO):
            """Encaminha cada linha ao logger (visibilidade no Render) e ao job state."""
            def write(self, s):
                r = super().write(s)
                linha = s.strip()
                if linha:
                    logger.info('[SETUP P2] %s', linha)
                    if not linha.startswith(('→', '•', '✓', '⚠', '[')):
                        try:
                            _job_boletos_set({
                                'status': 'running',
                                'iniciado': inicio_iso,
                                'etapa': linha[:140],
                            })
                        except Exception:
                            pass
                return r

        def _executar():
            from django.db import connection as _conn
            out = _SaidaBoletos()
            logger.info('[SETUP P2] Iniciando geração de boletos — banco=%s', banco)
            try:
                call_command('gerar_dados_teste', so_boletos=True, banco=banco, stdout=out)
                from financeiro.models import Parcela as _P, StatusBoleto as _SB
                qtd = _P.objects.filter(status_boleto=_SB.GERADO, pago=False).count()
                logger.info('[SETUP P2] Concluído: %d boleto(s) gerado(s)', qtd)
                _job_boletos_set({
                    'status': 'done',
                    'iniciado': inicio_iso,
                    'finalizado': timezone.now().isoformat(),
                    'boletos_gerados': qtd,
                    'output': out.getvalue()[-4000:],
                })
            except Exception as exc:
                logger.exception('[SETUP P2] Erro na geração de boletos: %s', exc)
                _job_boletos_set({
                    'status': 'error',
                    'finalizado': timezone.now().isoformat(),
                    'erro': str(exc),
                    'output': out.getvalue()[-4000:],
                })
            finally:
                _conn.close()

        threading.Thread(target=_executar, daemon=True).start()

        return JsonResponse({
            'status': 'started',
            'message': 'Geração de boletos iniciada. Acompanhe pelo GET.',
        }, status=202)

    except Exception as e:
        logger.exception("Erro ao iniciar geração de boletos: %s", e)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


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
    from contratos.models import Contrato, StatusContrato
    total_contratos = Contrato.objects.filter(
        imobiliaria__in=imobiliarias
    ).count()
    total_ativos = Contrato.objects.filter(
        imobiliaria__in=imobiliarias, status=StatusContrato.ATIVO
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
        from core.breadcrumbs import bc, bc_dashboard
        context = super().get_context_data(**kwargs)
        context['total_compradores'] = Comprador.objects.filter(ativo=True).count()
        context['search'] = self.request.GET.get('search', '')
        context['breadcrumb'] = [
            bc_dashboard(),
            bc('Cadastros'),
            bc('Compradores'),
        ]
        return context


class CompradorCreateView(LoginRequiredMixin, CreateView):
    """Cria um novo comprador"""
    model = Comprador
    form_class = CompradorForm
    template_name = 'core/comprador_form.html'
    success_url = reverse_lazy('core:listar_compradores')

    def get_context_data(self, **kwargs):
        from core.breadcrumbs import bc, bc_dashboard
        context = super().get_context_data(**kwargs)
        context['breadcrumb'] = [
            bc_dashboard(),
            bc('Compradores', 'core:listar_compradores'),
            bc('Novo'),
        ]
        return context

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

    def get_context_data(self, **kwargs):
        from core.breadcrumbs import bc, bc_dashboard
        from notificacoes.models import Notificacao
        context = super().get_context_data(**kwargs)
        context['breadcrumb'] = [
            bc_dashboard(),
            bc('Compradores', 'core:listar_compradores'),
            bc(self.object.nome),
        ]
        context['notificacoes_recentes'] = (
            Notificacao.objects
            .filter(parcela__contrato__comprador=self.object)
            .select_related('parcela')
            .order_by('-data_agendamento')[:10]
        )
        return context

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
        _agg = ativos.aggregate(
            total=Count('id'),
            disponiveis=Count('id', filter=Q(disponivel=True)),
        )
        context['total_imoveis'] = _agg['total']
        context['imoveis_disponiveis'] = _agg['disponiveis']

        # Todos os imóveis com coordenadas — passados ao mapa (não paginado)
        todos_mapa = list(
            ativos.filter(
                latitude__isnull=False,
                longitude__isnull=False
            ).select_related('imobiliaria').prefetch_related('vertices').order_by('loteamento', 'identificacao')
        )
        context['todos_imoveis_mapa'] = todos_mapa
        context['imoveis_com_coordenadas'] = len(todos_mapa)

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
        loteamentos = list(
            ativos.exclude(loteamento='').exclude(loteamento__isnull=True)
            .values_list('loteamento', flat=True)
            .distinct().order_by('loteamento')
        )
        context['loteamentos'] = loteamentos

        # M-14: overlays de planta baixa por loteamento
        overlays = {}
        for ov in LoteamentoOverlay.objects.filter(ativo=True, nome_loteamento__in=loteamentos):
            overlays[ov.nome_loteamento] = {
                'url': request.build_absolute_uri(ov.imagem.url),
                'bounds': ov.bounds(),
                'opacidade': ov.opacidade,
            }
        context['overlays_json'] = json.dumps(overlays)
        context['imobiliarias'] = Imobiliaria.objects.filter(ativo=True)
        context['search'] = self.request.GET.get('search', '')

        from core.breadcrumbs import bc, bc_dashboard
        context['breadcrumb'] = [
            bc_dashboard(),
            bc('Cadastros'),
            bc('Imóveis'),
        ]
        return context


class ImovelCreateView(LoginRequiredMixin, CreateView):
    """Cria um novo imóvel"""
    model = Imovel
    form_class = ImovelForm
    template_name = 'core/imovel_form.html'
    success_url = reverse_lazy('core:listar_imoveis')

    def get_context_data(self, **kwargs):
        from core.breadcrumbs import bc, bc_dashboard
        context = super().get_context_data(**kwargs)
        context['breadcrumb'] = [
            bc_dashboard(),
            bc('Imóveis', 'core:listar_imoveis'),
            bc('Novo'),
        ]
        return context

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

    def get_context_data(self, **kwargs):
        from core.breadcrumbs import bc, bc_dashboard
        context = super().get_context_data(**kwargs)
        context['breadcrumb'] = [
            bc_dashboard(),
            bc('Imóveis', 'core:listar_imoveis'),
            bc(self.object.identificacao or f'#{self.object.pk}'),
        ]
        return context

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

    import json as _json
    overlay_obj = LoteamentoOverlay.objects.filter(nome_loteamento__iexact=nome, ativo=True).first()
    overlay_data = None
    if overlay_obj:
        overlay_data = _json.dumps({
            'url': request.build_absolute_uri(overlay_obj.imagem.url),
            'bounds': overlay_obj.bounds(),
            'opacidade': overlay_obj.opacidade,
        })

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
        'overlay_json': overlay_data,
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

        # Adicionar conta principal — usa o cache do prefetch_related (sem N+1)
        imobiliarias = context.get('imobiliarias', [])
        for imobiliaria in imobiliarias:
            imobiliaria.conta_principal = next(
                (c for c in imobiliaria.contas_bancarias.all() if c.principal and c.ativo),
                None
            )

        from core.breadcrumbs import bc, bc_dashboard
        context['breadcrumb'] = [
            bc_dashboard(),
            bc('Cadastros'),
            bc('Imobiliárias'),
        ]
        return context


class ImobiliariaCreateView(LoginRequiredMixin, CreateView):
    """Cria uma nova imobiliária"""
    model = Imobiliaria
    form_class = ImobiliariaForm
    template_name = 'core/imobiliaria_form.html'
    success_url = reverse_lazy('core:listar_imobiliarias')

    def get_context_data(self, **kwargs):
        from core.breadcrumbs import bc, bc_dashboard
        context = super().get_context_data(**kwargs)
        context['breadcrumb'] = [
            bc_dashboard(),
            bc('Imobiliárias', 'core:listar_imobiliarias'),
            bc('Nova'),
        ]
        return context

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
                novas_contas = []
                for conta_data in contas:
                    agencia = conta_data.get('agencia', '')
                    agencia_dv = conta_data.get('agencia_dv', '')
                    agencia_completa = f"{agencia}-{agencia_dv}" if agencia and agencia_dv else agencia

                    conta = conta_data.get('conta', '')
                    conta_dv = conta_data.get('conta_dv', '')
                    conta_completa = f"{conta}-{conta_dv}" if conta and conta_dv else conta

                    novas_contas.append(ContaBancaria(
                        imobiliaria=self.object,
                        banco=conta_data.get('banco', ''),
                        descricao=conta_data.get('descricao', ''),
                        agencia=agencia_completa,
                        conta=conta_completa,
                        convenio=conta_data.get('convenio', ''),
                        carteira=conta_data.get('carteira', ''),
                        principal=conta_data.get('principal', False),
                    ))
                if novas_contas:
                    ContaBancaria.objects.bulk_create(novas_contas)
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

    def get_context_data(self, **kwargs):
        from core.breadcrumbs import bc, bc_dashboard
        context = super().get_context_data(**kwargs)
        context['breadcrumb'] = [
            bc_dashboard(),
            bc('Imobiliárias', 'core:listar_imobiliarias'),
            bc(self.object.nome),
        ]
        return context

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


@login_required
def api_overlay_loteamento(request, nome):
    """
    GET  → JSON com dados do overlay ativo para o loteamento.
    POST → cria/atualiza overlay (staff/superuser; multipart com campos + arquivo).
    M-14: Planta baixa como overlay no mapa.
    """
    import urllib.parse
    nome = urllib.parse.unquote(nome)

    if request.method == 'GET':
        overlay = LoteamentoOverlay.objects.filter(
            nome_loteamento__iexact=nome, ativo=True
        ).first()
        if not overlay:
            return JsonResponse({'overlay': None})
        return JsonResponse({
            'overlay': {
                'url': request.build_absolute_uri(overlay.imagem.url),
                'bounds': overlay.bounds(),
                'opacidade': overlay.opacidade,
            }
        })

    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'erro': 'Sem permissão.'}, status=403)

    if request.method == 'POST':
        try:
            lat_sw = float(request.POST.get('lat_sw', ''))
            lng_sw = float(request.POST.get('lng_sw', ''))
            lat_ne = float(request.POST.get('lat_ne', ''))
            lng_ne = float(request.POST.get('lng_ne', ''))
            opacidade = float(request.POST.get('opacidade', '0.7'))
        except (TypeError, ValueError):
            return JsonResponse({'erro': 'Parâmetros inválidos.'}, status=400)

        imagem = request.FILES.get('imagem')
        overlay, created = LoteamentoOverlay.objects.get_or_create(
            nome_loteamento=nome,
            defaults={'lat_sw': lat_sw, 'lng_sw': lng_sw, 'lat_ne': lat_ne, 'lng_ne': lng_ne,
                      'opacidade': opacidade, 'ativo': True},
        )
        overlay.lat_sw = lat_sw
        overlay.lng_sw = lng_sw
        overlay.lat_ne = lat_ne
        overlay.lng_ne = lng_ne
        overlay.opacidade = opacidade
        overlay.ativo = True
        if imagem:
            overlay.imagem = imagem
        overlay.save()
        return JsonResponse({'ok': True, 'created': created, 'id': overlay.pk})

    return JsonResponse({'erro': 'Método não suportado.'}, status=405)


# =============================================================================
# CONFIGURAÇÕES DO SISTEMA — HUB CENTRALIZADO
# =============================================================================

@login_required
def configuracoes_sistema(request):
    """Hub centralizado de configurações globais da plataforma. Restrito a staff."""
    if not (request.user.is_staff or request.user.is_superuser):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    from django.conf import settings as django_settings
    from .models import ParametroSistema
    from notificacoes.models import (
        ConfiguracaoEmail, ConfiguracaoSMS, ConfiguracaoWhatsApp, RegraNotificacao
    )
    from collections import defaultdict

    def _params_por_prefixo(prefixo):
        """Retorna dict {chave: valor} para params cujas chaves começam com prefixo."""
        return {
            p.chave: p.valor
            for p in ParametroSistema.objects.filter(chave__startswith=prefixo)
        }

    params_twilio = _params_por_prefixo('TWILIO_')
    params_brcobranca = _params_por_prefixo('BRCOBRANCA_')
    params_portal = _params_por_prefixo('PORTAL_')
    params_notif = _params_por_prefixo('NOTIFICACAO_')

    brcobranca_url = (
        params_brcobranca.get('BRCOBRANCA_URL')
        or getattr(django_settings, 'BRCOBRANCA_URL', 'http://localhost:9292')
    )

    todos = ParametroSistema.objects.all().order_by('grupo', 'chave')
    grupo_display = dict(ParametroSistema.GRUPO_CHOICES)
    parametros_por_grupo = defaultdict(list)
    for p in todos:
        parametros_por_grupo[grupo_display.get(p.grupo, p.grupo)].append(p)

    context = {
        'configs_email': ConfiguracaoEmail.objects.all().order_by('-ativo', 'nome'),
        'configs_whatsapp': ConfiguracaoWhatsApp.objects.all().order_by('-ativo', 'nome'),
        'config_email': ConfiguracaoEmail.objects.filter(ativo=True).first(),
        'config_whatsapp': ConfiguracaoWhatsApp.objects.filter(ativo=True).first(),
        'config_sms': ConfiguracaoSMS.objects.filter(ativo=True).first(),
        'status_brcobranca': bool(params_brcobranca.get('BRCOBRANCA_URL')),
        'params_twilio': params_twilio,
        'params_brcobranca': params_brcobranca,
        'params_portal': params_portal,
        'params_notif': params_notif,
        'parametros_por_grupo': dict(parametros_por_grupo),
        'regras_notificacao': RegraNotificacao.objects.filter(ativo=True).order_by('nome')[:10],
        'brcobranca_url': brcobranca_url,
        'brcobranca_ok': False,
    }
    return render(request, 'core/configuracoes_sistema.html', context)


@login_required
@require_http_methods(['POST'])
def api_parametros_salvar_grupo(request):
    """POST /core/api/parametros/ — salva múltiplos ParametroSistema de um grupo."""
    from .models import ParametroSistema
    try:
        data = json.loads(request.body)
        grupo = data.get('grupo', '')
        parametros = data.get('parametros', {})
        if not isinstance(parametros, dict):
            return JsonResponse({'sucesso': False, 'erro': 'Formato inválido.'}, status=400)
        chaves = list(parametros.keys())
        existentes = {p.chave: p for p in ParametroSistema.objects.filter(chave__in=chaves)}
        to_create = []
        to_update = []
        for chave, valor in parametros.items():
            valor_str = str(valor)
            if chave in existentes:
                obj = existentes[chave]
                obj.valor = valor_str
                obj.modificado_manualmente = True
                if grupo and obj.grupo != grupo:
                    obj.grupo = grupo
                to_update.append(obj)
            else:
                to_create.append(ParametroSistema(
                    chave=chave,
                    valor=valor_str,
                    grupo=grupo,
                    modificado_manualmente=True,
                ))
        if to_update:
            ParametroSistema.objects.bulk_update(to_update, ['valor', 'modificado_manualmente', 'grupo'])
        if to_create:
            ParametroSistema.objects.bulk_create(to_create, ignore_conflicts=True)
        salvos = len(to_update) + len(to_create)
        return JsonResponse({'sucesso': True, 'mensagem': f'{salvos} parâmetro(s) salvos.'})
    except Exception as e:
        logger.exception('Erro ao salvar parâmetros: %s', e)
        return JsonResponse({'sucesso': False, 'erro': str(e)}, status=500)


@login_required
@require_http_methods(['PATCH'])
def api_parametro_atualizar(request, parametro_id):
    """PATCH /core/api/parametros/<id>/ — atualiza valor de um ParametroSistema."""
    from .models import ParametroSistema
    from django.http import Http404
    param = get_object_or_404(ParametroSistema, pk=parametro_id)
    try:
        data = json.loads(request.body)
        param.valor = str(data.get('valor', ''))
        param.modificado_manualmente = True
        param.save()
        return JsonResponse({'sucesso': True, 'mensagem': f'"{param.chave}" atualizado.'})
    except Http404:
        raise
    except Exception as e:
        logger.exception('Erro ao atualizar parâmetro %s: %s', parametro_id, e)
        return JsonResponse({'sucesso': False, 'erro': str(e)}, status=500)


@login_required
@require_http_methods(['GET'])
def api_parametros_exportar(request):
    """GET /core/api/parametros/exportar/ — exporta todos os ParametroSistema como JSON."""
    from .models import ParametroSistema
    from django.http import HttpResponse
    import datetime
    params = list(
        ParametroSistema.objects.values('chave', 'valor', 'tipo', 'grupo', 'descricao', 'modificado_manualmente')
    )
    payload = {
        'exportado_em': datetime.datetime.utcnow().isoformat() + 'Z',
        'total': len(params),
        'parametros': params,
    }
    response = HttpResponse(
        json.dumps(payload, indent=2, ensure_ascii=False),
        content_type='application/json',
    )
    response['Content-Disposition'] = 'attachment; filename="config_sistema.json"'
    return response


# ─── Painel de Custos de IA ────────────────────────────────────────────────

@login_required
def ia_custos(request):
    """Painel de controle de uso e custo das APIs de IA."""
    from .models import RegistroUsoIA
    from django.db.models import Sum, Count
    from django.db.models.functions import TruncDate
    from datetime import date, timedelta
    from decimal import Decimal

    periodo = int(request.GET.get('periodo', 30))
    data_inicio = date.today() - timedelta(days=periodo - 1)
    qs = RegistroUsoIA.objects.filter(criado_em__date__gte=data_inicio)

    # Cards de resumo
    totais = qs.aggregate(
        total_custo=Sum('custo_usd'),
        total_chamadas=Count('id'),
        total_tokens_input=Sum('tokens_input'),
        total_tokens_output=Sum('tokens_output'),
    )
    total_custo = totais['total_custo'] or Decimal('0')
    total_chamadas = totais['total_chamadas'] or 0
    total_tokens = (totais['total_tokens_input'] or 0) + (totais['total_tokens_output'] or 0)

    # Distribuição por modelo
    por_modelo = list(
        qs.values('modelo')
        .annotate(custo=Sum('custo_usd'), chamadas=Count('id'))
        .order_by('-custo')
    )

    # Distribuição por operação
    por_operacao = list(
        qs.values('operacao')
        .annotate(custo=Sum('custo_usd'), chamadas=Count('id'))
        .order_by('-custo')
    )

    # Tendência diária
    tendencia = list(
        qs.annotate(dia=TruncDate('criado_em'))
        .values('dia')
        .annotate(custo=Sum('custo_usd'), chamadas=Count('id'))
        .order_by('dia')
    )

    # Últimas 20 operações
    recentes = qs.select_related('usuario').order_by('-criado_em')[:20]

    context = {
        'periodo': periodo,
        'data_inicio': data_inicio,
        'total_custo': total_custo,
        'total_chamadas': total_chamadas,
        'total_tokens': total_tokens,
        'por_modelo': por_modelo,
        'por_operacao': por_operacao,
        'tendencia': tendencia,
        'recentes': recentes,
    }
    return render(request, 'core/ia_custos.html', context)


@login_required
@require_http_methods(['GET'])
def api_ia_custos_dados(request):
    """GET /core/ia/custos/dados/ — JSON para os gráficos do painel IA."""
    from .models import RegistroUsoIA
    from django.db.models import Sum, Count
    from django.db.models.functions import TruncDate
    from datetime import date, timedelta

    periodo = int(request.GET.get('periodo', 30))
    data_inicio = date.today() - timedelta(days=periodo - 1)
    qs = RegistroUsoIA.objects.filter(criado_em__date__gte=data_inicio)

    por_modelo = list(
        qs.values('modelo')
        .annotate(custo=Sum('custo_usd'), chamadas=Count('id'))
        .order_by('-custo')
    )
    por_operacao = list(
        qs.values('operacao')
        .annotate(custo=Sum('custo_usd'), chamadas=Count('id'))
        .order_by('-custo')
    )
    tendencia = list(
        qs.annotate(dia=TruncDate('criado_em'))
        .values('dia')
        .annotate(custo=Sum('custo_usd'), chamadas=Count('id'))
        .order_by('dia')
    )

    payload = {
        'por_modelo': [
            {'modelo': r['modelo'], 'custo': float(r['custo'] or 0), 'chamadas': r['chamadas']}
            for r in por_modelo
        ],
        'por_operacao': [
            {'operacao': r['operacao'], 'custo': float(r['custo'] or 0), 'chamadas': r['chamadas']}
            for r in por_operacao
        ],
        'tendencia': [
            {'dia': r['dia'].isoformat(), 'custo': float(r['custo'] or 0), 'chamadas': r['chamadas']}
            for r in tendencia
        ],
    }
    return JsonResponse(payload)


# ─── Configuração Gráfica de Tokens ────────────────────────────────────────

@login_required
def ia_tokens_config(request):
    """Tela gráfica de configuração de cotas de tokens por modelo."""
    from .models import LimiteUsoIA, RegistroUsoIA
    from core.services.ia_monitor import consumo_periodo, get_cotacao_usd_brl
    from django.db.models import Sum
    from datetime import date

    try:
        cotacao = get_cotacao_usd_brl()
    except Exception:
        cotacao = 5.80

    # Tabela de preços: (input USD/MTok, output USD/MTok)
    precos_map = {
        'gemini-2.0-flash':          (0.0,    0.0),
        'claude-haiku-4-5-20251001': (1.00,   5.00),
        'claude-sonnet-4-6':         (3.00,  15.00),
        'claude-opus-4-8':           (5.00,  25.00),
    }

    inicio = date.today().replace(day=1)
    modelos_data = []
    for modelo in _MODELOS_IA:
        preco_in, preco_out = precos_map.get(modelo, (0.0, 0.0))
        consumo_tokens = consumo_periodo('MENSAL', modelo=modelo, tipo_limite='TOKENS')

        # Custo real do mês para este modelo
        agg = RegistroUsoIA.objects.filter(
            criado_em__date__gte=inicio, modelo=modelo,
        ).aggregate(custo=Sum('custo_usd'))
        custo_usd = float(agg['custo'] or 0)

        # Limites configurados (mensal tokens e mensal R$)
        lim_token = LimiteUsoIA.objects.filter(
            tipo_escopo='MODELO', escopo_valor=modelo,
            tipo_limite='TOKENS', periodo='MENSAL', ativo=True,
        ).first()
        lim_reais = LimiteUsoIA.objects.filter(
            tipo_escopo='MODELO', escopo_valor=modelo,
            tipo_limite='REAIS', periodo='MENSAL', ativo=True,
        ).first()

        limite_tokens = float(lim_token.valor_limite) if lim_token else None
        limite_reais_val = float(lim_reais.valor_limite) if lim_reais else None
        pct_tokens = min(100, int(consumo_tokens / limite_tokens * 100)) if limite_tokens else 0

        modelos_data.append({
            'modelo': modelo,
            'preco_in': preco_in,
            'preco_out': preco_out,
            'preco_in_brl': round(preco_in * cotacao, 4),
            'preco_out_brl': round(preco_out * cotacao, 4),
            'gratuito': preco_in == 0 and preco_out == 0,
            'consumo_tokens': int(consumo_tokens),
            'custo_usd': round(custo_usd, 4),
            'custo_brl': round(custo_usd * cotacao, 2),
            'limite_tokens': limite_tokens,
            'limite_reais': limite_reais_val,
            'pct_tokens': pct_tokens,
            'lim_token_pk': lim_token.pk if lim_token else '',
            'lim_reais_pk': lim_reais.pk if lim_reais else '',
        })

    return render(request, 'core/ia_tokens_config.html', {
        'modelos_data': modelos_data,
        'cotacao_usd_brl': cotacao,
        'periodo_choices': LimiteUsoIA.PERIODO_CHOICES,
    })


# ─── Configuração de Limites de Uso de IA ──────────────────────────────────

_MODELOS_IA = [
    'claude-haiku-4-5-20251001',
    'claude-sonnet-4-6',
    'claude-opus-4-8',
    'gemini-2.0-flash',
]
_OPERACOES_IA = ['IMPORTACAO_PDF', 'CHATBOT_INTENT', 'CHATBOT_HUMANIZE']

# Preços de referência USD/MTok para exibição na tela — (input, output)
_PRECOS_REFERENCIA = [
    {'modelo': 'gemini-2.0-flash',          'input': 0.00,  'output': 0.00,  'obs': 'Gratuito (cota diária)'},
    {'modelo': 'claude-haiku-4-5-20251001', 'input': 1.00,  'output': 5.00,  'obs': ''},
    {'modelo': 'claude-sonnet-4-6',         'input': 3.00,  'output': 15.00, 'obs': ''},
    {'modelo': 'claude-opus-4-8',           'input': 5.00,  'output': 25.00, 'obs': 'Máximo custo'},
]


@login_required
def ia_limites(request):
    """Tela de configuração de limites de uso de IA com período configurável."""
    from .models import LimiteUsoIA
    from core.services.ia_monitor import consumo_periodo, get_cotacao_usd_brl

    try:
        cotacao = get_cotacao_usd_brl()
    except Exception:
        cotacao = 5.80

    limites_raw = LimiteUsoIA.objects.all()
    limites_com_consumo = []
    for lim in limites_raw:
        if lim.tipo_escopo == LimiteUsoIA.ESCOPO_MODELO:
            atual = consumo_periodo(lim.periodo, modelo=lim.escopo_valor, tipo_limite=lim.tipo_limite)
        else:
            atual = consumo_periodo(lim.periodo, operacao=lim.escopo_valor, tipo_limite=lim.tipo_limite)
        pct = min(100, int(atual / float(lim.valor_limite) * 100)) if lim.valor_limite else 0
        limites_com_consumo.append({
            'limite': lim,
            'consumido': atual,
            'percentual': pct,
        })

    # Enriquecer preços de referência com valor em R$
    precos_ref = []
    for p in _PRECOS_REFERENCIA:
        precos_ref.append({
            **p,
            'input_brl':  round(p['input']  * cotacao, 4),
            'output_brl': round(p['output'] * cotacao, 4),
        })

    return render(request, 'core/ia_limites.html', {
        'limites_com_consumo': limites_com_consumo,
        'modelos': _MODELOS_IA,
        'operacoes': _OPERACOES_IA,
        'periodo_choices': LimiteUsoIA.PERIODO_CHOICES,
        'cotacao_usd_brl': cotacao,
        'precos_ref': precos_ref,
    })


@login_required
@require_http_methods(['POST'])
def ia_limite_salvar(request):
    """Cria ou atualiza um LimiteUsoIA."""
    from .models import LimiteUsoIA
    from decimal import Decimal as _Decimal, InvalidOperation

    pk = request.POST.get('pk', '').strip()
    tipo_escopo = request.POST.get('tipo_escopo', '').strip()
    escopo_valor = request.POST.get('escopo_valor', '').strip()
    tipo_limite = request.POST.get('tipo_limite', '').strip()
    periodo = request.POST.get('periodo', LimiteUsoIA.PERIODO_MENSAL).strip()
    valor_str = request.POST.get('valor_limite', '').replace(',', '.').strip()
    ativo = request.POST.get('ativo', 'true') != 'false'

    if not all([tipo_escopo, escopo_valor, tipo_limite, periodo, valor_str]):
        messages.error(request, 'Preencha todos os campos.')
        return redirect('core:ia_limites')

    try:
        valor = _Decimal(valor_str)
        if valor <= 0:
            raise ValueError('Valor deve ser positivo.')
    except (InvalidOperation, ValueError) as exc:
        messages.error(request, f'Valor inválido: {exc}')
        return redirect('core:ia_limites')

    try:
        if pk:
            updated = LimiteUsoIA.objects.filter(pk=pk).update(
                tipo_escopo=tipo_escopo, escopo_valor=escopo_valor,
                tipo_limite=tipo_limite, periodo=periodo,
                valor_limite=valor, ativo=ativo,
            )
            if updated:
                messages.success(request, 'Limite atualizado com sucesso.')
            else:
                messages.warning(request, 'Limite não encontrado.')
        else:
            _, created = LimiteUsoIA.objects.update_or_create(
                tipo_escopo=tipo_escopo,
                escopo_valor=escopo_valor,
                tipo_limite=tipo_limite,
                periodo=periodo,
                defaults={'valor_limite': valor, 'ativo': ativo},
            )
            messages.success(request, 'Limite criado.' if created else 'Limite atualizado.')
    except Exception as exc:
        messages.error(request, f'Erro ao salvar limite: {exc}')

    return redirect('core:ia_limites')


@login_required
@require_http_methods(['POST'])
def ia_limite_excluir(request, pk):
    """Remove um LimiteUsoIA."""
    from .models import LimiteUsoIA
    LimiteUsoIA.objects.filter(pk=pk).delete()
    messages.success(request, 'Limite removido.')
    return redirect('core:ia_limites')


@login_required
@require_http_methods(['POST'])
def ia_limite_toggle(request, pk):
    """Ativa/desativa um LimiteUsoIA sem excluir."""
    from .models import LimiteUsoIA
    lim = LimiteUsoIA.objects.filter(pk=pk).first()
    if lim:
        lim.ativo = not lim.ativo
        lim.save(update_fields=['ativo'])
        estado = 'ativado' if lim.ativo else 'desativado'
        messages.success(request, f'Limite {estado}.')
    return redirect('core:ia_limites')


@login_required
def auditoria_log(request):
    """GET /auditoria/ — lista os últimos 200 eventos de auditoria."""
    if not (request.user.is_staff or request.user.is_superuser):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    acao_filter = request.GET.get('acao', '')
    logs = LogAuditoria.objects.select_related('usuario').order_by('-timestamp')
    if acao_filter:
        logs = logs.filter(acao=acao_filter)
    logs = logs[:200]

    return render(request, 'core/auditoria_log.html', {
        'logs': logs,
        'acao_filter': acao_filter,
        'acoes': LogAuditoria.ACOES,
    })


@login_required
def api_cotacao_usd_brl(request):
    """GET /core/ia/cotacao/ — retorna cotação USD→BRL atual."""
    from core.services.ia_monitor import get_cotacao_usd_brl
    try:
        cotacao = get_cotacao_usd_brl()
        return JsonResponse({'cotacao': cotacao, 'status': 'ok'})
    except Exception as exc:
        return JsonResponse({'cotacao': 5.80, 'status': 'fallback', 'erro': str(exc)})


# =============================================================================
# 35.2 — Desbloqueio Manual de Crédito
# =============================================================================

@login_required
def comprador_desbloquear(request, pk):
    """Desbloqueio manual de crédito (somente superuser)."""
    from django.core.exceptions import PermissionDenied
    from core.models import registrar_auditoria
    if not request.user.is_superuser:
        raise PermissionDenied
    comprador = get_object_or_404(Comprador, pk=pk)
    comprador.bloqueio_credito = False
    comprador.bloqueio_credito_motivo = ''
    comprador.bloqueio_credito_em = None
    comprador.save(update_fields=['bloqueio_credito', 'bloqueio_credito_motivo', 'bloqueio_credito_em'])
    registrar_auditoria(
        request, 'DESBLOQUEIO_CREDITO', 'Comprador', pk,
        f'Desbloqueio manual de {comprador.nome}'
    )
    messages.success(request, f'{comprador.nome} desbloqueado com sucesso.')
    return redirect('core:editar_comprador', pk=pk)


@login_required
def api_comprador_status(request, pk):
    """GET /core/api/compradores/<pk>/status/ — retorna bloqueio_credito para o wizard."""
    comprador = get_object_or_404(Comprador, pk=pk)
    return JsonResponse({
        'bloqueio_credito': comprador.bloqueio_credito,
        'motivo': comprador.bloqueio_credito_motivo or '',
        'bloqueio_em': comprador.bloqueio_credito_em.strftime('%d/%m/%Y') if comprador.bloqueio_credito_em else '',
        'nome': comprador.nome,
    })


# =============================================================================
# 35.6 — Widget de IA no Dashboard
# =============================================================================

@login_required
def api_ia_status_widget(request):
    """GET /core/ia/status-widget/ — custo mês atual, limites, alertas ≥ 80%."""
    from datetime import date
    from .models import RegistroUsoIA, LimiteUsoIA
    from django.db.models import Sum as DbSum

    hoje = date.today()
    inicio_mes = hoje.replace(day=1)

    custo_mes = RegistroUsoIA.objects.filter(
        criado_em__date__gte=inicio_mes
    ).aggregate(total=DbSum('custo_usd'))['total'] or 0

    alertas = []
    for lim in LimiteUsoIA.objects.filter(ativo=True):
        try:
            from datetime import timedelta
            if lim.periodo == 'MENSAL':
                data_inicio = inicio_mes
            elif lim.periodo == 'SEMANAL':
                data_inicio = hoje - timedelta(days=hoje.weekday())
            else:
                data_inicio = hoje

            qs = RegistroUsoIA.objects.filter(criado_em__date__gte=data_inicio)
            if lim.tipo_escopo == 'MODELO' and lim.escopo_valor:
                qs = qs.filter(modelo=lim.escopo_valor)
            elif lim.tipo_escopo == 'OPERACAO' and lim.escopo_valor:
                qs = qs.filter(operacao=lim.escopo_valor)

            if lim.tipo_limite == 'TOKENS':
                agg = qs.aggregate(ti=DbSum('tokens_input'), to=DbSum('tokens_output'))
                consumo = (agg['ti'] or 0) + (agg['to'] or 0)
            else:
                consumo = float(qs.aggregate(t=DbSum('custo_usd'))['t'] or 0)

            limite_val = float(lim.valor_limite)
            pct = round(consumo / limite_val * 100, 1) if limite_val > 0 else 0
            if pct >= 80:
                alertas.append({'descricao': str(lim), 'pct': pct})
        except Exception:
            pass

    return JsonResponse({
        'custo_mes_usd': round(float(custo_mes), 4),
        'alertas_ativos': alertas,
        'alertas_count': len(alertas),
    })


# =============================================================================
# WORKFLOW DE IA (CASCADE DE MODELOS CONFIGURÁVEL)
# =============================================================================

_DEFAULT_WORKFLOW_TIERS = [
    ('claude-haiku-4-5-20251001', 1),
    ('claude-sonnet-4-6',         2),
    ('claude-opus-4-8',           3),
]

_MODELOS_WORKFLOW = [
    ('claude-haiku-4-5-20251001', 'Claude Haiku 4.5',   1.00,  5.00),
    ('claude-sonnet-4-6',         'Claude Sonnet 4.6',  3.00, 15.00),
    ('claude-opus-4-8',           'Claude Opus 4.8',    5.00, 25.00),
]


@login_required
def ia_workflow_list(request):
    from .models import WorkflowIA
    workflows = WorkflowIA.objects.prefetch_related('tiers').order_by('-ativo', 'nome')
    return render(request, 'core/ia_workflow_list.html', {'workflows': workflows})


@login_required
@require_http_methods(['GET', 'POST'])
def ia_workflow_novo(request):
    from .models import WorkflowIA, WorkflowIATier
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip() or 'Novo Workflow'
        wf = WorkflowIA.objects.create(nome=nome, descricao='')
        for modelo, ordem in _DEFAULT_WORKFLOW_TIERS:
            WorkflowIATier.objects.create(workflow=wf, modelo=modelo, ordem=ordem)
        messages.success(request, f'Workflow "{wf.nome}" criado.')
        return redirect('core:ia_workflow_editar', pk=wf.pk)
    return render(request, 'core/ia_workflow_list.html', {
        'workflows': WorkflowIA.objects.prefetch_related('tiers').order_by('-ativo', 'nome'),
        'show_novo_form': True,
    })


@login_required
def ia_workflow_editar(request, pk):
    from .models import WorkflowIA
    wf = get_object_or_404(WorkflowIA, pk=pk)
    if request.method == 'POST':
        wf.nome = request.POST.get('nome', wf.nome).strip() or wf.nome
        wf.descricao = request.POST.get('descricao', wf.descricao).strip()
        wf.save(update_fields=['nome', 'descricao'])
        messages.success(request, 'Workflow atualizado.')
        return redirect('core:ia_workflow_editar', pk=wf.pk)
    tiers = list(wf.tiers.order_by('ordem'))
    return render(request, 'core/ia_workflow_editar.html', {
        'wf': wf,
        'tiers': tiers,
        'modelos_workflow': _MODELOS_WORKFLOW,
    })


@login_required
@require_http_methods(['POST'])
def ia_workflow_ativar(request, pk):
    from .models import WorkflowIA
    wf = get_object_or_404(WorkflowIA, pk=pk)
    wf.ativar()
    return JsonResponse({'status': 'ok', 'nome': wf.nome})


@login_required
@require_http_methods(['POST'])
def ia_workflow_excluir(request, pk):
    from .models import WorkflowIA
    wf = get_object_or_404(WorkflowIA, pk=pk)
    if wf.ativo:
        return JsonResponse(
            {'status': 'erro', 'msg': 'Desative o workflow antes de excluí-lo.'}, status=400
        )
    wf.delete()
    return JsonResponse({'status': 'ok'})


@login_required
@require_http_methods(['POST'])
def ia_workflow_desativar(request, pk):
    from .models import WorkflowIA
    wf = get_object_or_404(WorkflowIA, pk=pk)
    wf.desativar()
    return JsonResponse({'status': 'ok'})


@login_required
@require_http_methods(['POST'])
def ia_workflow_tiers_salvar(request, pk):
    import json as _json
    from django.db import transaction
    from .models import WorkflowIA, WorkflowIATier
    wf = get_object_or_404(WorkflowIA, pk=pk)
    try:
        payload = _json.loads(request.body)
        tiers_data = payload.get('tiers', [])
    except (ValueError, AttributeError):
        return JsonResponse({'status': 'erro', 'msg': 'Payload inválido.'}, status=400)
    valid_models = {m[0] for m in WorkflowIATier.MODELO_CHOICES}
    with transaction.atomic():
        wf.tiers.all().delete()
        for idx, t in enumerate(tiers_data, start=1):
            modelo = str(t.get('modelo', '')).strip()
            if modelo and modelo in valid_models:
                WorkflowIATier.objects.create(
                    workflow=wf,
                    modelo=modelo,
                    ordem=idx,
                    habilitado=bool(t.get('habilitado', True)),
                )
    return JsonResponse({'status': 'ok', 'count': wf.tiers.count()})


@login_required
@require_http_methods(['POST'])
def ia_workflow_tiers_reordenar(request, pk):
    import json as _json
    from django.db import transaction
    from .models import WorkflowIA, WorkflowIATier
    wf = get_object_or_404(WorkflowIA, pk=pk)
    try:
        ids = _json.loads(request.body).get('ids', [])
        ids = [int(i) for i in ids]
    except (ValueError, AttributeError, TypeError):
        return JsonResponse({'status': 'erro', 'msg': 'IDs inválidos.'}, status=400)
    with transaction.atomic():
        # Offset temporário para evitar violação unique_together ao reordenar
        offset = 10000
        from django.db.models import F
        for tier_id in ids:
            WorkflowIATier.objects.filter(pk=tier_id, workflow=wf).update(ordem=F('ordem') + offset)
        for idx, tier_id in enumerate(ids, start=1):
            WorkflowIATier.objects.filter(pk=tier_id, workflow=wf).update(ordem=idx)
    return JsonResponse({'status': 'ok'})


# =============================================================================
# API — Comprador (CRUD)
# =============================================================================

def _serializar_comprador(c):
    return {
        'id': c.id,
        'tipo_pessoa': c.tipo_pessoa,
        'nome': c.nome,
        # PF
        'cpf': c.cpf or '',
        'rg': c.rg,
        'data_nascimento': c.data_nascimento.isoformat() if c.data_nascimento else None,
        'estado_civil': c.estado_civil,
        'profissao': c.profissao,
        # PJ
        'cnpj': c.cnpj or '',
        'nome_fantasia': c.nome_fantasia,
        'inscricao_estadual': c.inscricao_estadual,
        'inscricao_municipal': c.inscricao_municipal,
        'responsavel_legal': c.responsavel_legal,
        'responsavel_cpf': c.responsavel_cpf,
        # Endereço
        'cep': c.cep,
        'logradouro': c.logradouro,
        'numero': c.numero,
        'complemento': c.complemento,
        'bairro': c.bairro,
        'cidade': c.cidade,
        'estado': c.estado,
        # Contato
        'telefone': c.telefone,
        'celular': c.celular,
        'email': c.email,
        'notificar_email': c.notificar_email,
        'notificar_sms': c.notificar_sms,
        'notificar_whatsapp': c.notificar_whatsapp,
        # Cônjuge
        'conjuge_nome': c.conjuge_nome,
        'conjuge_cpf': c.conjuge_cpf,
        'conjuge_rg': c.conjuge_rg,
        # Outros
        'observacoes': c.observacoes,
        'bloqueio_credito': c.bloqueio_credito,
        'ativo': c.ativo,
        'criado_em': c.criado_em.isoformat() if c.criado_em else None,
        'atualizado_em': c.atualizado_em.isoformat() if c.atualizado_em else None,
    }


@login_required
@require_http_methods(['GET', 'POST'])
def api_compradores(request):
    """Lista ou cria compradores. GET aceita ?q= para busca por nome/CPF/CNPJ/email."""
    if request.method == 'GET':
        try:
            qs = Comprador.objects.filter(ativo=True).order_by('nome')
            q = request.GET.get('q', '').strip()
            if q:
                from django.db.models import Q as _Q
                qs = qs.filter(
                    _Q(nome__icontains=q) |
                    _Q(cpf__icontains=q) |
                    _Q(cnpj__icontains=q) |
                    _Q(email__icontains=q) |
                    _Q(celular__icontains=q)
                )
            total = qs.count()
            page = max(1, int(request.GET.get('page', 1)))
            page_size = min(100, max(1, int(request.GET.get('page_size', 25))))
            start = (page - 1) * page_size
            compradores = [_serializar_comprador(c) for c in qs[start:start + page_size]]
            return JsonResponse({
                'status': 'success',
                'total': total,
                'page': page,
                'page_size': page_size,
                'compradores': compradores,
            })
        except Exception as e:
            logger.exception('api_compradores GET: %s', e)
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # POST — criar
    try:
        data = json.loads(request.body)
        comprador = Comprador.objects.create(
            tipo_pessoa=data.get('tipo_pessoa', 'PF'),
            nome=data.get('nome', ''),
            cpf=data.get('cpf') or None,
            rg=data.get('rg', ''),
            data_nascimento=data.get('data_nascimento') or None,
            estado_civil=data.get('estado_civil', ''),
            profissao=data.get('profissao', ''),
            cnpj=data.get('cnpj') or None,
            nome_fantasia=data.get('nome_fantasia', ''),
            inscricao_estadual=data.get('inscricao_estadual', ''),
            inscricao_municipal=data.get('inscricao_municipal', ''),
            responsavel_legal=data.get('responsavel_legal', ''),
            responsavel_cpf=data.get('responsavel_cpf', ''),
            cep=data.get('cep', ''),
            logradouro=data.get('logradouro', ''),
            numero=data.get('numero', ''),
            complemento=data.get('complemento', ''),
            bairro=data.get('bairro', ''),
            cidade=data.get('cidade', ''),
            estado=data.get('estado', ''),
            telefone=data.get('telefone', ''),
            celular=data.get('celular', ''),
            email=data.get('email', ''),
            notificar_email=data.get('notificar_email', True),
            notificar_sms=data.get('notificar_sms', False),
            notificar_whatsapp=data.get('notificar_whatsapp', False),
            conjuge_nome=data.get('conjuge_nome', ''),
            conjuge_cpf=data.get('conjuge_cpf', ''),
            conjuge_rg=data.get('conjuge_rg', ''),
            observacoes=data.get('observacoes', ''),
        )
        return JsonResponse({'status': 'success', 'comprador': _serializar_comprador(comprador)}, status=201)
    except Exception as e:
        logger.exception('api_compradores POST: %s', e)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
@require_http_methods(['GET'])
def api_comprador_detalhe(request, pk):
    """Retorna os dados completos de um comprador."""
    try:
        comprador = get_object_or_404(Comprador, pk=pk)
        return JsonResponse({'status': 'success', 'comprador': _serializar_comprador(comprador)})
    except Exception as e:
        logger.exception('api_comprador_detalhe pk=%s: %s', pk, e)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_http_methods(['PUT', 'PATCH'])
def api_comprador_atualizar(request, pk):
    """Atualiza os dados de um comprador (PUT ou PATCH)."""
    try:
        comprador = get_object_or_404(Comprador, pk=pk)
        data = json.loads(request.body)
        campos = [
            'tipo_pessoa', 'nome', 'rg', 'data_nascimento', 'estado_civil', 'profissao',
            'nome_fantasia', 'inscricao_estadual', 'inscricao_municipal',
            'responsavel_legal', 'responsavel_cpf',
            'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado',
            'telefone', 'celular', 'email',
            'notificar_email', 'notificar_sms', 'notificar_whatsapp',
            'conjuge_nome', 'conjuge_cpf', 'conjuge_rg',
            'observacoes', 'ativo',
        ]
        for campo in campos:
            if campo in data:
                setattr(comprador, campo, data[campo])
        # Nullable fields
        if 'cpf' in data:
            comprador.cpf = data['cpf'] or None
        if 'cnpj' in data:
            comprador.cnpj = data['cnpj'] or None
        comprador.save()
        return JsonResponse({'status': 'success', 'comprador': _serializar_comprador(comprador)})
    except Exception as e:
        logger.exception('api_comprador_atualizar pk=%s: %s', pk, e)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
@require_http_methods(['DELETE'])
def api_comprador_excluir(request, pk):
    """Desativa (soft delete) um comprador."""
    try:
        comprador = get_object_or_404(Comprador, pk=pk)
        comprador.ativo = False
        comprador.save(update_fields=['ativo'])
        return JsonResponse({'status': 'success', 'message': 'Comprador desativado.'})
    except Exception as e:
        logger.exception('api_comprador_excluir pk=%s: %s', pk, e)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# =============================================================================
# API — Imobiliária (CRUD)
# =============================================================================

def _serializar_imobiliaria(imob, request=None):
    logo_url = ''
    if imob.logo:
        try:
            logo_url = request.build_absolute_uri(imob.logo.url) if request else imob.logo.url
        except Exception:
            pass
    return {
        'id': imob.id,
        'tipo_pessoa': imob.tipo_pessoa,
        'nome': imob.nome,
        'razao_social': imob.razao_social,
        'cnpj': imob.cnpj or '',
        'cpf': imob.cpf or '',
        'documento': imob.documento or '',
        # Endereço
        'cep': imob.cep,
        'logradouro': imob.logradouro,
        'numero': imob.numero,
        'complemento': imob.complemento,
        'bairro': imob.bairro,
        'cidade': imob.cidade,
        'estado': imob.estado,
        # Contato
        'telefone': imob.telefone,
        'email': imob.email,
        'responsavel_financeiro': imob.responsavel_financeiro,
        # Identidade visual
        'logo_url': logo_url,
        'cor_marca': imob.cor_marca,
        'rodape_contato': imob.rodape_contato,
        'marca_dagua': imob.marca_dagua,
        'ativo': imob.ativo,
        'criado_em': imob.criado_em.isoformat() if imob.criado_em else None,
        'atualizado_em': imob.atualizado_em.isoformat() if imob.atualizado_em else None,
    }


@login_required
@require_http_methods(['GET', 'POST'])
def api_imobiliarias(request):
    """Lista ou cria imobiliárias. GET aceita ?q= para busca por nome/CNPJ."""
    if request.method == 'GET':
        try:
            qs = Imobiliaria.objects.all().order_by('nome')
            q = request.GET.get('q', '').strip()
            if q:
                from django.db.models import Q as _Q
                qs = qs.filter(
                    _Q(nome__icontains=q) |
                    _Q(razao_social__icontains=q) |
                    _Q(cnpj__icontains=q) |
                    _Q(email__icontains=q)
                )
            ativo = request.GET.get('ativo')
            if ativo is not None:
                qs = qs.filter(ativo=(ativo.lower() in ('1', 'true', 'sim')))
            total = qs.count()
            page = max(1, int(request.GET.get('page', 1)))
            page_size = min(100, max(1, int(request.GET.get('page_size', 25))))
            start = (page - 1) * page_size
            imobiliarias = [_serializar_imobiliaria(i, request) for i in qs[start:start + page_size]]
            return JsonResponse({
                'status': 'success',
                'total': total,
                'page': page,
                'page_size': page_size,
                'imobiliarias': imobiliarias,
            })
        except Exception as e:
            logger.exception('api_imobiliarias GET: %s', e)
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # POST — criar
    try:
        data = json.loads(request.body)
        contabilidade_id = data.get('contabilidade_id')
        if not contabilidade_id:
            return JsonResponse({'status': 'error', 'message': 'contabilidade_id é obrigatório.'}, status=400)
        contabilidade = get_object_or_404(Contabilidade, pk=contabilidade_id)
        imob = Imobiliaria.objects.create(
            contabilidade=contabilidade,
            tipo_pessoa=data.get('tipo_pessoa', 'PJ'),
            nome=data.get('nome', ''),
            razao_social=data.get('razao_social', ''),
            cnpj=data.get('cnpj') or None,
            cpf=data.get('cpf') or None,
            cep=data.get('cep', ''),
            logradouro=data.get('logradouro', ''),
            numero=data.get('numero', ''),
            complemento=data.get('complemento', ''),
            bairro=data.get('bairro', ''),
            cidade=data.get('cidade', ''),
            estado=data.get('estado', ''),
            telefone=data.get('telefone', ''),
            email=data.get('email', ''),
            responsavel_financeiro=data.get('responsavel_financeiro', ''),
            cor_marca=data.get('cor_marca', ''),
            rodape_contato=data.get('rodape_contato', ''),
            marca_dagua=data.get('marca_dagua', ''),
        )
        return JsonResponse({'status': 'success', 'imobiliaria': _serializar_imobiliaria(imob, request)}, status=201)
    except Exception as e:
        logger.exception('api_imobiliarias POST: %s', e)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
@require_http_methods(['GET'])
def api_imobiliaria_detalhe(request, pk):
    """Retorna os dados completos de uma imobiliária."""
    try:
        imob = get_object_or_404(Imobiliaria, pk=pk)
        return JsonResponse({'status': 'success', 'imobiliaria': _serializar_imobiliaria(imob, request)})
    except Exception as e:
        logger.exception('api_imobiliaria_detalhe pk=%s: %s', pk, e)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_http_methods(['PUT', 'PATCH'])
def api_imobiliaria_atualizar(request, pk):
    """Atualiza os dados de uma imobiliária (PUT ou PATCH)."""
    try:
        imob = get_object_or_404(Imobiliaria, pk=pk)
        data = json.loads(request.body)
        campos = [
            'tipo_pessoa', 'nome', 'razao_social',
            'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado',
            'telefone', 'email', 'responsavel_financeiro',
            'cor_marca', 'rodape_contato', 'marca_dagua',
            'ativo',
        ]
        for campo in campos:
            if campo in data:
                setattr(imob, campo, data[campo])
        if 'cnpj' in data:
            imob.cnpj = data['cnpj'] or None
        if 'cpf' in data:
            imob.cpf = data['cpf'] or None
        imob.save()
        return JsonResponse({'status': 'success', 'imobiliaria': _serializar_imobiliaria(imob, request)})
    except Exception as e:
        logger.exception('api_imobiliaria_atualizar pk=%s: %s', pk, e)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
@require_http_methods(['DELETE'])
def api_imobiliaria_excluir(request, pk):
    """Desativa (soft delete) uma imobiliária."""
    try:
        imob = get_object_or_404(Imobiliaria, pk=pk)
        imob.ativo = False
        imob.save(update_fields=['ativo'])
        return JsonResponse({'status': 'success', 'message': 'Imobiliária desativada.'})
    except Exception as e:
        logger.exception('api_imobiliaria_excluir pk=%s: %s', pk, e)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ---------------------------------------------------------------------------
# Passo 3 — Setup: remessa CNAB, retorno e logos para imobiliárias
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(['POST'])
def api_simular_remessa_teste(request):
    """Gera arquivos de remessa CNAB simulados para todas as imobiliárias/meses."""
    try:
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command('gerar_dados_teste', so_remessa=True, stdout=out)
        saida = out.getvalue()
        from financeiro.models import ArquivoRemessa
        total = ArquivoRemessa.objects.count()
        return JsonResponse({'status': 'success', 'output': saida, 'total_remessas': total})
    except Exception as e:
        logger.exception('api_simular_remessa_teste: %s', e)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_http_methods(['POST'])
def api_simular_retorno_teste(request):
    """Gera arquivos de retorno CNAB simulados (70% pago)."""
    try:
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command('gerar_dados_teste', so_retorno=True, stdout=out)
        saida = out.getvalue()
        from financeiro.models import ArquivoRetorno
        total = ArquivoRetorno.objects.count()
        return JsonResponse({'status': 'success', 'output': saida, 'total_retornos': total})
    except Exception as e:
        logger.exception('api_simular_retorno_teste: %s', e)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_http_methods(['POST'])
def api_gerar_logos_teste(request):
    """Gera logotipos PNG para as imobiliárias de teste usando Pillow."""
    try:
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command('gerar_dados_teste', so_logos=True, stdout=out)
        saida = out.getvalue()
        com_logo = Imobiliaria.objects.exclude(logo='').exclude(logo=None).count()
        return JsonResponse({'status': 'success', 'output': saida, 'imobiliarias_com_logo': com_logo})
    except Exception as e:
        logger.exception('api_gerar_logos_teste: %s', e)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
