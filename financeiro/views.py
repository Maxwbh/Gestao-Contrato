"""
Views do app Financeiro

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse
from django.utils import timezone
from django.db.models import Sum, Count, Q, F
from django.views.generic import TemplateView
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.clickjacking import xframe_options_sameorigin
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import logging

from .models import Parcela, Reajuste, StatusBoleto
from core.models import Imobiliaria, ContaBancaria
from contratos.models import Contrato, StatusContrato

logger = logging.getLogger(__name__)


class DashboardFinanceiroView(LoginRequiredMixin, TemplateView):
    """Dashboard Financeiro por Imobiliária"""
    template_name = 'financeiro/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoje = timezone.now().date()

        # Filtro por imobiliária
        imobiliaria_id = self.request.GET.get('imobiliaria')
        imobiliarias = Imobiliaria.objects.filter(ativo=True)
        imobiliaria_selecionada = None

        if imobiliaria_id:
            try:
                imobiliaria_selecionada = Imobiliaria.objects.get(pk=imobiliaria_id, ativo=True)
            except Imobiliaria.DoesNotExist:
                pass

        # Base queryset de contratos
        contratos_qs = Contrato.objects.all()
        if imobiliaria_selecionada:
            contratos_qs = contratos_qs.filter(imobiliaria=imobiliaria_selecionada)

        # Base queryset de parcelas
        parcelas_qs = Parcela.objects.all()
        if imobiliaria_selecionada:
            parcelas_qs = parcelas_qs.filter(contrato__imobiliaria=imobiliaria_selecionada)

        # Estatísticas de Contratos
        context['total_contratos'] = contratos_qs.count()
        context['contratos_ativos'] = contratos_qs.filter(status=StatusContrato.ATIVO).count()
        context['contratos_quitados'] = contratos_qs.filter(status=StatusContrato.QUITADO).count()
        context['contratos_cancelados'] = contratos_qs.filter(status=StatusContrato.CANCELADO).count()

        # Valor total dos contratos
        context['valor_total_contratos'] = contratos_qs.aggregate(
            total=Sum('valor_total')
        )['total'] or Decimal('0.00')

        # Estatísticas de Parcelas
        context['total_parcelas'] = parcelas_qs.count()
        context['parcelas_pagas'] = parcelas_qs.filter(pago=True).count()
        context['parcelas_pendentes'] = parcelas_qs.filter(pago=False).count()
        context['parcelas_vencidas'] = parcelas_qs.filter(
            pago=False, data_vencimento__lt=hoje
        ).count()

        # Valores
        context['valor_recebido'] = parcelas_qs.filter(pago=True).aggregate(
            total=Sum('valor_pago')
        )['total'] or Decimal('0.00')

        context['valor_a_receber'] = parcelas_qs.filter(pago=False).aggregate(
            total=Sum('valor_atual')
        )['total'] or Decimal('0.00')

        context['valor_em_atraso'] = parcelas_qs.filter(
            pago=False, data_vencimento__lt=hoje
        ).aggregate(total=Sum('valor_atual'))['total'] or Decimal('0.00')

        # Períodos para filtros
        primeiro_dia_mes = hoje.replace(day=1)
        ultimo_dia_mes_passado = primeiro_dia_mes - timedelta(days=1)
        primeiro_dia_mes_passado = ultimo_dia_mes_passado.replace(day=1)
        seis_meses_atras = hoje - relativedelta(months=6)
        primeiro_dia_ano = hoje.replace(month=1, day=1)

        # Parcelas do mês atual
        context['parcelas_mes_atual'] = self._get_estatisticas_periodo(
            parcelas_qs, primeiro_dia_mes, hoje
        )

        # Parcelas do mês passado
        context['parcelas_mes_passado'] = self._get_estatisticas_periodo(
            parcelas_qs, primeiro_dia_mes_passado, ultimo_dia_mes_passado
        )

        # Parcelas últimos 6 meses
        context['parcelas_6_meses'] = self._get_estatisticas_periodo(
            parcelas_qs, seis_meses_atras, hoje
        )

        # Parcelas do ano
        context['parcelas_ano'] = self._get_estatisticas_periodo(
            parcelas_qs, primeiro_dia_ano, hoje
        )

        # Top 10 contratos com mais atraso
        context['contratos_mais_atraso'] = self._get_contratos_mais_atraso(
            contratos_qs, limite=10
        )

        # Imobiliárias e selecionada
        context['imobiliarias'] = imobiliarias
        context['imobiliaria_selecionada'] = imobiliaria_selecionada

        return context

    def _get_estatisticas_periodo(self, parcelas_qs, data_inicio, data_fim):
        """Retorna estatísticas de parcelas em um período"""
        parcelas_periodo = parcelas_qs.filter(
            data_vencimento__gte=data_inicio,
            data_vencimento__lte=data_fim
        )

        return {
            'total': parcelas_periodo.count(),
            'pagas': parcelas_periodo.filter(pago=True).count(),
            'pendentes': parcelas_periodo.filter(pago=False).count(),
            'vencidas': parcelas_periodo.filter(
                pago=False, data_vencimento__lt=timezone.now().date()
            ).count(),
            'valor_esperado': parcelas_periodo.aggregate(
                total=Sum('valor_atual')
            )['total'] or Decimal('0.00'),
            'valor_recebido': parcelas_periodo.filter(pago=True).aggregate(
                total=Sum('valor_pago')
            )['total'] or Decimal('0.00'),
        }

    def _get_contratos_mais_atraso(self, contratos_qs, limite=10):
        """Retorna contratos com mais parcelas em atraso"""
        hoje = timezone.now().date()
        contratos_atraso = []

        for contrato in contratos_qs.filter(status=StatusContrato.ATIVO):
            parcelas_atraso = contrato.parcelas.filter(
                pago=False, data_vencimento__lt=hoje
            )
            if parcelas_atraso.exists():
                total_atraso = parcelas_atraso.aggregate(
                    total=Sum('valor_atual')
                )['total'] or Decimal('0.00')
                dias_atraso = (hoje - parcelas_atraso.order_by('data_vencimento').first().data_vencimento).days
                contratos_atraso.append({
                    'contrato': contrato,
                    'parcelas_atraso': parcelas_atraso.count(),
                    'valor_atraso': total_atraso,
                    'dias_atraso': dias_atraso,
                })

        # Ordenar por valor em atraso (decrescente)
        contratos_atraso.sort(key=lambda x: x['valor_atraso'], reverse=True)
        return contratos_atraso[:limite]


@login_required
def api_dashboard_dados(request):
    """API para retornar dados do dashboard em JSON (para gráficos)"""
    hoje = timezone.now().date()

    # Filtro por imobiliária
    imobiliaria_id = request.GET.get('imobiliaria')
    parcelas_qs = Parcela.objects.all()
    contratos_qs = Contrato.objects.all()

    if imobiliaria_id:
        parcelas_qs = parcelas_qs.filter(contrato__imobiliaria_id=imobiliaria_id)
        contratos_qs = contratos_qs.filter(imobiliaria_id=imobiliaria_id)

    # Dados para gráfico de pizza - Status das parcelas
    status_parcelas = {
        'labels': ['Pagas', 'Pendentes', 'Vencidas'],
        'data': [
            parcelas_qs.filter(pago=True).count(),
            parcelas_qs.filter(pago=False, data_vencimento__gte=hoje).count(),
            parcelas_qs.filter(pago=False, data_vencimento__lt=hoje).count(),
        ],
        'colors': ['#28a745', '#ffc107', '#dc3545']
    }

    # Dados para gráfico de pizza - Status dos contratos
    status_contratos = {
        'labels': ['Ativos', 'Quitados', 'Cancelados', 'Suspensos'],
        'data': [
            contratos_qs.filter(status=StatusContrato.ATIVO).count(),
            contratos_qs.filter(status=StatusContrato.QUITADO).count(),
            contratos_qs.filter(status=StatusContrato.CANCELADO).count(),
            contratos_qs.filter(status=StatusContrato.SUSPENSO).count(),
        ],
        'colors': ['#007bff', '#28a745', '#dc3545', '#6c757d']
    }

    # Dados para gráfico de barras - Recebimentos por mês (últimos 12 meses)
    recebimentos_mensais = {'labels': [], 'recebido': [], 'esperado': []}
    meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

    for i in range(11, -1, -1):
        data = hoje - relativedelta(months=i)
        primeiro_dia = data.replace(day=1)
        ultimo_dia = (primeiro_dia + relativedelta(months=1)) - timedelta(days=1)

        parcelas_mes = parcelas_qs.filter(
            data_vencimento__gte=primeiro_dia,
            data_vencimento__lte=ultimo_dia
        )

        recebido = parcelas_mes.filter(pago=True).aggregate(
            total=Sum('valor_pago')
        )['total'] or 0
        esperado = parcelas_mes.aggregate(
            total=Sum('valor_atual')
        )['total'] or 0

        recebimentos_mensais['labels'].append(f"{meses[data.month-1]}/{data.year % 100}")
        recebimentos_mensais['recebido'].append(float(recebido))
        recebimentos_mensais['esperado'].append(float(esperado))

    # Dados para gráfico de linha - Inadimplência por mês
    inadimplencia_mensal = {'labels': [], 'valores': [], 'quantidades': []}

    for i in range(11, -1, -1):
        data = hoje - relativedelta(months=i)
        primeiro_dia = data.replace(day=1)
        ultimo_dia = (primeiro_dia + relativedelta(months=1)) - timedelta(days=1)

        parcelas_vencidas = parcelas_qs.filter(
            pago=False,
            data_vencimento__gte=primeiro_dia,
            data_vencimento__lte=ultimo_dia,
            data_vencimento__lt=hoje
        )

        valor_inadimplente = parcelas_vencidas.aggregate(
            total=Sum('valor_atual')
        )['total'] or 0

        inadimplencia_mensal['labels'].append(f"{meses[data.month-1]}/{data.year % 100}")
        inadimplencia_mensal['valores'].append(float(valor_inadimplente))
        inadimplencia_mensal['quantidades'].append(parcelas_vencidas.count())

    return JsonResponse({
        'status_parcelas': status_parcelas,
        'status_contratos': status_contratos,
        'recebimentos_mensais': recebimentos_mensais,
        'inadimplencia_mensal': inadimplencia_mensal,
    })


@login_required
def listar_parcelas(request):
    """
    Lista todas as parcelas com filtros avançados.

    Filtros disponíveis:
    - status: pagas, pendentes, vencidas, a_vencer
    - imobiliaria: ID da imobiliária
    - comprador: ID do comprador
    - contrato: número do contrato
    - data_inicio: data de vencimento inicial
    - data_fim: data de vencimento final
    - q: busca textual
    """
    from core.models import Comprador

    parcelas = Parcela.objects.select_related(
        'contrato',
        'contrato__comprador',
        'contrato__imovel',
        'contrato__imovel__imobiliaria'
    ).order_by('-data_vencimento')

    # Dados para os filtros
    imobiliarias = Imobiliaria.objects.filter(ativo=True).order_by('nome')
    compradores = Comprador.objects.filter(ativo=True).order_by('nome')

    # Filtro por Status
    status = request.GET.get('status', '')
    if status == 'pagas':
        parcelas = parcelas.filter(pago=True)
    elif status == 'pendentes':
        parcelas = parcelas.filter(pago=False)
    elif status == 'vencidas':
        parcelas = parcelas.filter(pago=False, data_vencimento__lt=timezone.now().date())
    elif status == 'a_vencer':
        parcelas = parcelas.filter(pago=False, data_vencimento__gte=timezone.now().date())

    # Filtro por Imobiliária
    imobiliaria_id = request.GET.get('imobiliaria', '')
    if imobiliaria_id:
        parcelas = parcelas.filter(contrato__imovel__imobiliaria_id=imobiliaria_id)

    # Filtro por Comprador
    comprador_id = request.GET.get('comprador', '')
    if comprador_id:
        parcelas = parcelas.filter(contrato__comprador_id=comprador_id)

    # Filtro por Número do Contrato ou ID
    contrato_param = request.GET.get('contrato', '').strip()
    if contrato_param:
        # Se for número, filtra por ID do contrato
        if contrato_param.isdigit():
            parcelas = parcelas.filter(contrato_id=contrato_param)
        else:
            # Senão, filtra por número do contrato
            parcelas = parcelas.filter(contrato__numero_contrato__icontains=contrato_param)

    # Filtro por Período de Vencimento
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    if data_inicio:
        parcelas = parcelas.filter(data_vencimento__gte=data_inicio)
    if data_fim:
        parcelas = parcelas.filter(data_vencimento__lte=data_fim)

    # Busca textual (nome do comprador ou identificação do imóvel)
    busca = request.GET.get('q', '').strip()
    if busca:
        parcelas = parcelas.filter(
            Q(contrato__comprador__nome__icontains=busca) |
            Q(contrato__imovel__identificacao__icontains=busca) |
            Q(contrato__numero_contrato__icontains=busca)
        )

    # Estatísticas
    hoje = timezone.now().date()
    total_parcelas = parcelas.count()
    valor_total = parcelas.aggregate(total=Sum('valor_atual'))['total'] or Decimal('0.00')
    parcelas_vencidas_count = parcelas.filter(pago=False, data_vencimento__lt=hoje).count()

    context = {
        'parcelas': parcelas[:500],  # Limitar para performance
        'imobiliarias': imobiliarias,
        'compradores': compradores,
        # Valores atuais dos filtros
        'filtro_status': status,
        'filtro_imobiliaria': imobiliaria_id,
        'filtro_comprador': comprador_id,
        'filtro_contrato': contrato_param,
        'filtro_data_inicio': data_inicio,
        'filtro_data_fim': data_fim,
        'filtro_busca': busca,
        # Estatísticas
        'total_parcelas': total_parcelas,
        'valor_total': valor_total,
        'parcelas_vencidas_count': parcelas_vencidas_count,
    }
    return render(request, 'financeiro/listar_parcelas.html', context)


@login_required
def detalhe_parcela(request, pk):
    """Exibe detalhes de uma parcela específica"""
    parcela = get_object_or_404(
        Parcela.objects.select_related(
            'contrato',
            'contrato__comprador',
            'contrato__imovel'
        ),
        pk=pk
    )

    # Atualizar juros e multa se estiver vencida
    if parcela.esta_vencida and not parcela.pago:
        parcela.atualizar_juros_multa()

    context = {
        'parcela': parcela,
    }
    return render(request, 'financeiro/detalhe_parcela.html', context)


@login_required
def registrar_pagamento(request, pk):
    """Registra o pagamento de uma parcela"""
    from datetime import datetime

    parcela = get_object_or_404(Parcela, pk=pk)

    if request.method == 'POST':
        valor_pago_str = request.POST.get('valor_pago', '0')
        data_pagamento_str = request.POST.get('data_pagamento', '')
        observacoes = request.POST.get('observacoes', '')

        try:
            # Converter valor para Decimal
            valor_pago = Decimal(valor_pago_str.replace(',', '.'))

            # Converter data
            if data_pagamento_str:
                data_pagamento = datetime.strptime(data_pagamento_str, '%Y-%m-%d').date()
            else:
                data_pagamento = timezone.now().date()

            parcela.registrar_pagamento(
                valor_pago=valor_pago,
                data_pagamento=data_pagamento,
                observacoes=observacoes
            )
            messages.success(request, 'Pagamento registrado com sucesso!')
            return redirect('financeiro:detalhe_parcela', pk=pk)
        except Exception as e:
            messages.error(request, f'Erro ao registrar pagamento: {str(e)}')

    context = {
        'parcela': parcela,
    }
    return render(request, 'financeiro/registrar_pagamento.html', context)


@login_required
def listar_reajustes(request):
    """Lista todos os reajustes"""
    reajustes = Reajuste.objects.select_related('contrato').all()

    context = {
        'reajustes': reajustes,
    }
    return render(request, 'financeiro/listar_reajustes.html', context)


# =============================================================================
# GESTÃO DE PARCELAS POR IMOBILIÁRIA
# =============================================================================

@login_required
def parcelas_mes_atual(request):
    """
    Lista parcelas que vencem no mês atual, agrupadas por imobiliária.
    """
    hoje = timezone.now().date()
    primeiro_dia_mes = hoje.replace(day=1)

    # Último dia do mês
    if hoje.month == 12:
        ultimo_dia_mes = hoje.replace(day=31)
    else:
        ultimo_dia_mes = hoje.replace(month=hoje.month + 1, day=1) - timedelta(days=1)

    # Filtro por imobiliária
    imobiliaria_id = request.GET.get('imobiliaria', '')
    imobiliarias = Imobiliaria.objects.filter(ativo=True).order_by('nome')

    # Base queryset
    parcelas = Parcela.objects.select_related(
        'contrato',
        'contrato__comprador',
        'contrato__imovel',
        'contrato__imovel__imobiliaria'
    ).filter(
        data_vencimento__gte=primeiro_dia_mes,
        data_vencimento__lte=ultimo_dia_mes
    ).order_by('data_vencimento', 'contrato__imovel__imobiliaria__nome')

    if imobiliaria_id:
        parcelas = parcelas.filter(contrato__imovel__imobiliaria_id=imobiliaria_id)

    # Filtro por status
    status = request.GET.get('status', '')
    if status == 'pagas':
        parcelas = parcelas.filter(pago=True)
    elif status == 'pendentes':
        parcelas = parcelas.filter(pago=False)
    elif status == 'vencidas':
        parcelas = parcelas.filter(pago=False, data_vencimento__lt=hoje)

    # Estatísticas do mês
    stats = parcelas.aggregate(
        total=Count('id'),
        valor_total=Sum('valor_atual'),
        pagas=Count('id', filter=Q(pago=True)),
        valor_pago=Sum('valor_pago', filter=Q(pago=True)),
        pendentes=Count('id', filter=Q(pago=False)),
        valor_pendente=Sum('valor_atual', filter=Q(pago=False)),
        vencidas=Count('id', filter=Q(pago=False, data_vencimento__lt=hoje)),
        valor_vencido=Sum('valor_atual', filter=Q(pago=False, data_vencimento__lt=hoje)),
    )

    # Agrupar por imobiliária para resumo
    parcelas_por_imobiliaria = {}
    for parcela in parcelas:
        imob_nome = parcela.contrato.imovel.imobiliaria.nome if parcela.contrato.imovel.imobiliaria else 'Sem Imobiliária'
        if imob_nome not in parcelas_por_imobiliaria:
            parcelas_por_imobiliaria[imob_nome] = {
                'total': 0,
                'pagas': 0,
                'pendentes': 0,
                'valor_total': Decimal('0.00'),
                'valor_pago': Decimal('0.00'),
                'valor_pendente': Decimal('0.00'),
            }
        parcelas_por_imobiliaria[imob_nome]['total'] += 1
        parcelas_por_imobiliaria[imob_nome]['valor_total'] += parcela.valor_atual
        if parcela.pago:
            parcelas_por_imobiliaria[imob_nome]['pagas'] += 1
            parcelas_por_imobiliaria[imob_nome]['valor_pago'] += parcela.valor_pago or Decimal('0.00')
        else:
            parcelas_por_imobiliaria[imob_nome]['pendentes'] += 1
            parcelas_por_imobiliaria[imob_nome]['valor_pendente'] += parcela.valor_atual

    context = {
        'parcelas': parcelas,
        'imobiliarias': imobiliarias,
        'filtro_imobiliaria': imobiliaria_id,
        'filtro_status': status,
        'mes_atual': hoje.strftime('%B/%Y'),
        'primeiro_dia': primeiro_dia_mes,
        'ultimo_dia': ultimo_dia_mes,
        'stats': stats,
        'parcelas_por_imobiliaria': parcelas_por_imobiliaria,
    }
    return render(request, 'financeiro/parcelas_mes.html', context)


@login_required
def dashboard_imobiliaria(request, imobiliaria_id):
    """
    Dashboard financeiro detalhado para uma imobiliária específica.

    Inclui:
    - Estatísticas gerais de parcelas e contratos
    - Contratos com reajuste pendente
    - Parcelas bloqueadas por reajuste
    - Prestações intermediárias
    - Top 10 compradores com mais atraso
    """
    imobiliaria = get_object_or_404(Imobiliaria, pk=imobiliaria_id, ativo=True)
    hoje = timezone.now().date()

    # Período do mês atual
    primeiro_dia_mes = hoje.replace(day=1)
    if hoje.month == 12:
        ultimo_dia_mes = hoje.replace(day=31)
    else:
        ultimo_dia_mes = hoje.replace(month=hoje.month + 1, day=1) - timedelta(days=1)

    # Todas as parcelas da imobiliária
    parcelas_imob = Parcela.objects.select_related(
        'contrato',
        'contrato__comprador',
        'contrato__imovel'
    ).filter(
        contrato__imovel__imobiliaria=imobiliaria
    )

    # Estatísticas gerais
    stats_geral = parcelas_imob.aggregate(
        total=Count('id'),
        pagas=Count('id', filter=Q(pago=True)),
        pendentes=Count('id', filter=Q(pago=False)),
        vencidas=Count('id', filter=Q(pago=False, data_vencimento__lt=hoje)),
        valor_total=Sum('valor_atual'),
        valor_recebido=Sum('valor_pago', filter=Q(pago=True)),
        valor_pendente=Sum('valor_atual', filter=Q(pago=False)),
        valor_vencido=Sum('valor_atual', filter=Q(pago=False, data_vencimento__lt=hoje)),
    )

    # Parcelas do mês atual
    parcelas_mes = parcelas_imob.filter(
        data_vencimento__gte=primeiro_dia_mes,
        data_vencimento__lte=ultimo_dia_mes
    )

    stats_mes = parcelas_mes.aggregate(
        total=Count('id'),
        pagas=Count('id', filter=Q(pago=True)),
        pendentes=Count('id', filter=Q(pago=False)),
        vencidas=Count('id', filter=Q(pago=False, data_vencimento__lt=hoje)),
        valor_total=Sum('valor_atual'),
        valor_recebido=Sum('valor_pago', filter=Q(pago=True)),
        valor_pendente=Sum('valor_atual', filter=Q(pago=False)),
    )

    # Parcelas vencidas (não pagas e data < hoje)
    parcelas_vencidas = parcelas_imob.filter(
        pago=False,
        data_vencimento__lt=hoje
    ).order_by('data_vencimento')[:20]

    # Próximas parcelas a vencer (próximos 30 dias)
    proximas_parcelas = parcelas_imob.filter(
        pago=False,
        data_vencimento__gte=hoje,
        data_vencimento__lte=hoje + timedelta(days=30)
    ).order_by('data_vencimento')[:20]

    # Contratos da imobiliária
    contratos = Contrato.objects.filter(
        imovel__imobiliaria=imobiliaria
    ).select_related('comprador', 'imovel')

    stats_contratos = contratos.aggregate(
        total=Count('id'),
        ativos=Count('id', filter=Q(status=StatusContrato.ATIVO)),
        quitados=Count('id', filter=Q(status=StatusContrato.QUITADO)),
        valor_total=Sum('valor_total'),
    )

    # =========================================================================
    # CONTRATOS COM REAJUSTE PENDENTE
    # =========================================================================
    contratos_reajuste_pendente = []
    contratos_com_boleto_bloqueado = []

    for contrato in contratos.filter(status=StatusContrato.ATIVO):
        # Verificar se tem bloqueio de reajuste
        if hasattr(contrato, 'verificar_bloqueio_reajuste'):
            bloqueio_info = contrato.verificar_bloqueio_reajuste()
            if bloqueio_info.get('bloqueado'):
                contratos_com_boleto_bloqueado.append({
                    'contrato': contrato,
                    'ciclo_atual': bloqueio_info.get('ciclo_atual', 1),
                    'ciclo_pendente': bloqueio_info.get('ciclo_pendente'),
                    'motivo': bloqueio_info.get('motivo', ''),
                })

        # Verificar reajuste pendente
        if hasattr(contrato, 'data_ultimo_reajuste') and hasattr(contrato, 'prazo_reajuste_meses'):
            data_base = contrato.data_ultimo_reajuste or contrato.data_contrato
            proxima_data_reajuste = data_base + relativedelta(months=contrato.prazo_reajuste_meses)

            if proxima_data_reajuste <= hoje:
                meses_atraso = (hoje.year - proxima_data_reajuste.year) * 12 + (hoje.month - proxima_data_reajuste.month)
                contratos_reajuste_pendente.append({
                    'contrato': contrato,
                    'data_ultimo_reajuste': contrato.data_ultimo_reajuste,
                    'proxima_data_reajuste': proxima_data_reajuste,
                    'meses_atraso': meses_atraso,
                    'tipo_correcao': contrato.get_tipo_correcao_display() if hasattr(contrato, 'get_tipo_correcao_display') else 'N/A',
                })

    # Ordenar por meses em atraso
    contratos_reajuste_pendente.sort(key=lambda x: x['meses_atraso'], reverse=True)

    # =========================================================================
    # PRESTAÇÕES INTERMEDIÁRIAS
    # =========================================================================
    from contratos.models import PrestacaoIntermediaria

    intermediarias_pendentes = PrestacaoIntermediaria.objects.filter(
        contrato__imovel__imobiliaria=imobiliaria,
        paga=False
    ).select_related('contrato', 'contrato__comprador').order_by('mes_vencimento')[:10]

    stats_intermediarias = PrestacaoIntermediaria.objects.filter(
        contrato__imovel__imobiliaria=imobiliaria
    ).aggregate(
        total=Count('id'),
        pagas=Count('id', filter=Q(paga=True)),
        pendentes=Count('id', filter=Q(paga=False)),
        valor_total=Sum('valor'),
        valor_pago=Sum('valor_pago', filter=Q(paga=True)),
        valor_pendente=Sum('valor', filter=Q(paga=False)),
    )

    # Top 10 compradores com mais atraso
    compradores_atraso = []
    for contrato in contratos.filter(status=StatusContrato.ATIVO):
        parcelas_atraso = contrato.parcelas.filter(pago=False, data_vencimento__lt=hoje)
        if parcelas_atraso.exists():
            valor_atraso = parcelas_atraso.aggregate(total=Sum('valor_atual'))['total'] or Decimal('0.00')
            compradores_atraso.append({
                'comprador': contrato.comprador,
                'contrato': contrato,
                'qtd_parcelas': parcelas_atraso.count(),
                'valor_atraso': valor_atraso,
                'dias_atraso': (hoje - parcelas_atraso.first().data_vencimento).days,
            })
    compradores_atraso.sort(key=lambda x: x['valor_atraso'], reverse=True)

    context = {
        'imobiliaria': imobiliaria,
        'stats_geral': stats_geral,
        'stats_mes': stats_mes,
        'stats_contratos': stats_contratos,
        'parcelas_vencidas': parcelas_vencidas,
        'proximas_parcelas': proximas_parcelas,
        'compradores_atraso': compradores_atraso[:10],
        'mes_atual': hoje.strftime('%B/%Y'),
        # Novos campos
        'contratos_reajuste_pendente': contratos_reajuste_pendente[:10],
        'contratos_com_boleto_bloqueado': contratos_com_boleto_bloqueado[:10],
        'total_contratos_bloqueados': len(contratos_com_boleto_bloqueado),
        'total_contratos_reajuste_pendente': len(contratos_reajuste_pendente),
        'intermediarias_pendentes': intermediarias_pendentes,
        'stats_intermediarias': stats_intermediarias,
    }
    return render(request, 'financeiro/dashboard_imobiliaria.html', context)


# =============================================================================
# VIEWS DE BOLETO BANCÁRIO
# =============================================================================

@login_required
@require_POST
def gerar_boleto_parcela(request, pk):
    """
    Gera boleto para uma parcela específica.

    IMPORTANTE: Verifica se a parcela pode ter boleto gerado considerando
    o ciclo de reajuste. Boletos após o 12º mês só podem ser gerados
    após aplicação do reajuste correspondente.
    """
    parcela = get_object_or_404(Parcela, pk=pk)

    if parcela.pago:
        return JsonResponse({
            'sucesso': False,
            'erro': 'Parcela já está paga'
        }, status=400)

    # =========================================================================
    # VERIFICAÇÃO DE BLOQUEIO POR REAJUSTE
    # =========================================================================
    contrato = parcela.contrato
    force = request.POST.get('force', 'false').lower() == 'true'

    # Só verifica bloqueio se não for forçado (force=true ignora o bloqueio)
    if not force and hasattr(contrato, 'pode_gerar_boleto'):
        pode_gerar, motivo = contrato.pode_gerar_boleto(parcela.numero_parcela)
        if not pode_gerar:
            return JsonResponse({
                'sucesso': False,
                'erro': f'Boleto bloqueado: {motivo}',
                'bloqueado_reajuste': True,
                'ciclo_atual': getattr(contrato, 'ciclo_reajuste_atual', 1),
                'numero_parcela': parcela.numero_parcela
            }, status=400)

    # Obter conta bancária (pode vir do request ou usar a padrão)
    conta_id = request.POST.get('conta_bancaria_id')
    conta_bancaria = None

    if conta_id:
        conta_bancaria = get_object_or_404(ContaBancaria, pk=conta_id, ativo=True)
    else:
        # Usar conta principal da imobiliária
        imobiliaria = parcela.contrato.imovel.imobiliaria
        conta_bancaria = imobiliaria.contas_bancarias.filter(
            principal=True, ativo=True
        ).first()

    if not conta_bancaria:
        return JsonResponse({
            'sucesso': False,
            'erro': 'Nenhuma conta bancária configurada'
        }, status=400)

    try:
        resultado = parcela.gerar_boleto(conta_bancaria, force=force)

        if resultado and resultado.get('sucesso'):
            # Atualizar último mês com boleto gerado no contrato
            if hasattr(contrato, 'ultimo_mes_boleto_gerado'):
                if parcela.numero_parcela > contrato.ultimo_mes_boleto_gerado:
                    contrato.ultimo_mes_boleto_gerado = parcela.numero_parcela
                    contrato.save(update_fields=['ultimo_mes_boleto_gerado'])

            return JsonResponse({
                'sucesso': True,
                'parcela_id': parcela.id,
                'nosso_numero': resultado.get('nosso_numero', ''),
                'linha_digitavel': resultado.get('linha_digitavel', ''),
                'codigo_barras': resultado.get('codigo_barras', ''),
                'tem_pdf': parcela.boleto_pdf.name if parcela.boleto_pdf else False,
                'mensagem': 'Boleto gerado com sucesso'
            })
        else:
            return JsonResponse({
                'sucesso': False,
                'erro': resultado.get('erro', 'Erro ao gerar boleto') if resultado else 'Erro desconhecido'
            }, status=500)

    except Exception as e:
        logger.exception(f"Erro ao gerar boleto: {e}")
        return JsonResponse({
            'sucesso': False,
            'erro': str(e)
        }, status=500)


@login_required
@require_POST
def gerar_boletos_contrato(request, contrato_id):
    """
    Gera boletos para todas as parcelas pendentes de um contrato.

    IMPORTANTE: Verifica o bloqueio por reajuste antes de gerar cada boleto.
    Parcelas de ciclos não reajustados serão marcadas como bloqueadas.
    """
    contrato = get_object_or_404(Contrato, pk=contrato_id)

    # Obter conta bancária
    conta_id = request.POST.get('conta_bancaria_id')
    conta_bancaria = None
    force = request.POST.get('force', 'false').lower() == 'true'

    if conta_id:
        conta_bancaria = get_object_or_404(ContaBancaria, pk=conta_id, ativo=True)

    try:
        # =====================================================================
        # VERIFICAÇÃO DE BLOQUEIO POR REAJUSTE
        # =====================================================================
        parcelas_pendentes = contrato.parcelas.filter(pago=False).order_by('numero_parcela')

        if not parcelas_pendentes.exists():
            return JsonResponse({
                'sucesso': False,
                'erro': 'Não há parcelas pendentes para gerar boletos'
            }, status=400)

        resultados = []
        gerados = 0
        bloqueados = 0
        erros = 0

        for parcela in parcelas_pendentes:
            # Verificar bloqueio por reajuste
            if not force and hasattr(contrato, 'pode_gerar_boleto'):
                pode_gerar, motivo = contrato.pode_gerar_boleto(parcela.numero_parcela)
                if not pode_gerar:
                    resultados.append({
                        'parcela_id': parcela.id,
                        'numero_parcela': parcela.numero_parcela,
                        'sucesso': False,
                        'bloqueado_reajuste': True,
                        'erro': motivo
                    })
                    bloqueados += 1
                    continue

            # Verificar se já tem boleto
            if parcela.tem_boleto and not force:
                resultados.append({
                    'parcela_id': parcela.id,
                    'numero_parcela': parcela.numero_parcela,
                    'sucesso': True,
                    'mensagem': 'Boleto já existente'
                })
                continue

            # Gerar boleto
            try:
                resultado = parcela.gerar_boleto(conta_bancaria, force=force)
                if resultado and resultado.get('sucesso'):
                    gerados += 1
                    resultados.append({
                        'parcela_id': parcela.id,
                        'numero_parcela': parcela.numero_parcela,
                        'sucesso': True,
                        'nosso_numero': resultado.get('nosso_numero')
                    })

                    # Atualizar último mês com boleto gerado
                    if hasattr(contrato, 'ultimo_mes_boleto_gerado'):
                        if parcela.numero_parcela > contrato.ultimo_mes_boleto_gerado:
                            contrato.ultimo_mes_boleto_gerado = parcela.numero_parcela
                else:
                    erros += 1
                    resultados.append({
                        'parcela_id': parcela.id,
                        'numero_parcela': parcela.numero_parcela,
                        'sucesso': False,
                        'erro': resultado.get('erro') if resultado else 'Erro desconhecido'
                    })
            except Exception as e:
                erros += 1
                resultados.append({
                    'parcela_id': parcela.id,
                    'numero_parcela': parcela.numero_parcela,
                    'sucesso': False,
                    'erro': str(e)
                })

        # Salvar atualização do último mês com boleto gerado
        if hasattr(contrato, 'ultimo_mes_boleto_gerado'):
            contrato.save(update_fields=['ultimo_mes_boleto_gerado'])

        total = len(resultados)

        return JsonResponse({
            'sucesso': True,
            'total': total,
            'gerados': gerados,
            'bloqueados': bloqueados,
            'erros': erros,
            'resultados': resultados,
            'mensagem': f'{gerados} boletos gerados, {bloqueados} bloqueados por reajuste, {erros} erros'
        })

    except Exception as e:
        logger.exception(f"Erro ao gerar boletos do contrato: {e}")
        return JsonResponse({
            'sucesso': False,
            'erro': str(e)
        }, status=500)


@login_required
@require_GET
def download_boleto(request, pk):
    """
    Download do PDF do boleto.
    """
    parcela = get_object_or_404(Parcela, pk=pk)

    if not parcela.boleto_pdf:
        messages.error(request, 'Boleto não disponível para download.')
        return redirect('financeiro:detalhe_parcela', pk=pk)

    try:
        response = FileResponse(
            parcela.boleto_pdf.open('rb'),
            as_attachment=True,
            filename=f'boleto_{parcela.contrato.numero_contrato}_{parcela.numero_parcela}.pdf'
        )
        response['Content-Type'] = 'application/pdf'
        return response
    except Exception as e:
        logger.exception(f"Erro ao fazer download do boleto: {e}")
        messages.error(request, 'Erro ao baixar o boleto.')
        return redirect('financeiro:detalhe_parcela', pk=pk)


@login_required
@require_GET
@xframe_options_sameorigin
def visualizar_boleto(request, pk):
    """
    Exibe página com dados do boleto de uma parcela.
    Permite carregamento em iframe do mesmo domínio.
    """
    parcela = get_object_or_404(Parcela, pk=pk)

    if not parcela.tem_boleto:
        messages.warning(request, 'Boleto ainda não foi gerado para esta parcela.')
        return redirect('financeiro:detalhe_parcela', pk=pk)

    contrato = parcela.contrato
    comprador = contrato.comprador
    imobiliaria = contrato.imobiliaria

    # Calcular valores para hoje
    valores_hoje = parcela.calcular_valores_hoje()

    # Verificar se e popup (sem navbar) - verificando se tem parametro popup ou se nao tem referer
    popup = request.GET.get('popup', 'false').lower() == 'true' or not request.META.get('HTTP_REFERER')

    context = {
        'parcela': parcela,
        'contrato': contrato,
        'comprador': comprador,
        'imobiliaria': imobiliaria,
        'valores_hoje': valores_hoje,
        'popup': popup,
    }

    return render(request, 'financeiro/visualizar_boleto.html', context)


@login_required
@require_POST
def cancelar_boleto(request, pk):
    """
    Cancela um boleto.
    """
    parcela = get_object_or_404(Parcela, pk=pk)

    if parcela.status_boleto in [StatusBoleto.NAO_GERADO, StatusBoleto.CANCELADO]:
        return JsonResponse({
            'sucesso': False,
            'erro': 'Boleto não pode ser cancelado'
        }, status=400)

    if parcela.pago:
        return JsonResponse({
            'sucesso': False,
            'erro': 'Não é possível cancelar boleto de parcela paga'
        }, status=400)

    motivo = request.POST.get('motivo', '')

    try:
        parcela.cancelar_boleto(motivo)
        return JsonResponse({
            'sucesso': True,
            'mensagem': 'Boleto cancelado com sucesso'
        })
    except Exception as e:
        logger.exception(f"Erro ao cancelar boleto: {e}")
        return JsonResponse({
            'sucesso': False,
            'erro': str(e)
        }, status=500)


@login_required
def api_status_boleto(request, pk):
    """
    Retorna o status do boleto de uma parcela (para atualização via AJAX).
    """
    parcela = get_object_or_404(Parcela, pk=pk)

    return JsonResponse({
        'parcela_id': parcela.id,
        'status': parcela.status_boleto,
        'status_display': parcela.get_status_boleto_display(),
        'tem_boleto': parcela.tem_boleto,
        'nosso_numero': parcela.nosso_numero,
        'linha_digitavel': parcela.linha_digitavel,
        'tem_pdf': bool(parcela.boleto_pdf),
        'data_geracao': parcela.data_geracao_boleto.isoformat() if parcela.data_geracao_boleto else None,
    })


# =============================================================================
# VIEWS CNAB - ARQUIVOS DE REMESSA E RETORNO
# =============================================================================

@login_required
def listar_arquivos_remessa(request):
    """Lista todos os arquivos de remessa"""
    from .models import ArquivoRemessa

    arquivos = ArquivoRemessa.objects.select_related(
        'conta_bancaria', 'conta_bancaria__imobiliaria'
    ).order_by('-data_geracao')

    # Filtros
    conta_id = request.GET.get('conta')
    status = request.GET.get('status')

    if conta_id:
        arquivos = arquivos.filter(conta_bancaria_id=conta_id)
    if status:
        arquivos = arquivos.filter(status=status)

    contas = ContaBancaria.objects.filter(ativo=True).select_related('imobiliaria')

    context = {
        'arquivos': arquivos[:100],
        'contas_bancarias': contas,
        'filtro_conta': conta_id,
        'filtro_status': status,
    }
    return render(request, 'financeiro/cnab/listar_remessas.html', context)


@login_required
def detalhe_arquivo_remessa(request, pk):
    """Exibe detalhes de um arquivo de remessa"""
    from .models import ArquivoRemessa

    arquivo = get_object_or_404(
        ArquivoRemessa.objects.select_related(
            'conta_bancaria', 'conta_bancaria__imobiliaria'
        ).prefetch_related(
            'itens', 'itens__parcela', 'itens__parcela__contrato',
            'itens__parcela__contrato__comprador'
        ),
        pk=pk
    )

    context = {
        'arquivo': arquivo,
        'itens': arquivo.itens.all(),
    }
    return render(request, 'financeiro/cnab/detalhe_remessa.html', context)


@login_required
def gerar_arquivo_remessa(request):
    """
    View para gerar novo arquivo de remessa.
    GET: Exibe formulario com boletos disponiveis
    POST: Gera o arquivo com os boletos selecionados
    """
    from .models import ArquivoRemessa, Parcela, StatusBoleto
    from .services.cnab_service import CNABService

    contas = ContaBancaria.objects.filter(ativo=True).select_related('imobiliaria')

    if request.method == 'POST':
        conta_id = request.POST.get('conta_bancaria')
        layout = request.POST.get('layout', 'CNAB_240')
        parcela_ids = request.POST.getlist('parcelas')

        if not conta_id:
            messages.error(request, 'Selecione uma conta bancaria.')
            return redirect('financeiro:gerar_remessa')

        if not parcela_ids:
            messages.error(request, 'Selecione pelo menos uma parcela.')
            return redirect('financeiro:gerar_remessa')

        conta = get_object_or_404(ContaBancaria, pk=conta_id, ativo=True)
        parcelas = Parcela.objects.filter(
            pk__in=parcela_ids,
            status_boleto=StatusBoleto.GERADO,
            pago=False
        )

        if not parcelas.exists():
            messages.error(request, 'Nenhuma parcela valida selecionada.')
            return redirect('financeiro:gerar_remessa')

        try:
            service = CNABService()
            resultado = service.gerar_remessa(list(parcelas), conta, layout)

            if resultado.get('sucesso'):
                arquivo = resultado.get('arquivo_remessa')
                messages.success(
                    request,
                    f"Remessa {arquivo.numero_remessa} gerada com sucesso! "
                    f"{resultado.get('quantidade_boletos')} boletos, "
                    f"R$ {resultado.get('valor_total'):,.2f}"
                )
                return redirect('financeiro:detalhe_remessa', pk=arquivo.pk)
            else:
                messages.error(request, f"Erro ao gerar remessa: {resultado.get('erro')}")

        except Exception as e:
            logger.exception(f"Erro ao gerar remessa: {e}")
            messages.error(request, f"Erro ao gerar remessa: {str(e)}")

        return redirect('financeiro:gerar_remessa')

    # GET - Exibir boletos disponiveis
    conta_id = request.GET.get('conta')
    boletos_disponiveis = []

    if conta_id:
        conta = get_object_or_404(ContaBancaria, pk=conta_id, ativo=True)
        service = CNABService()
        boletos_disponiveis = service.obter_boletos_sem_remessa(conta)

    context = {
        'contas_bancarias': contas,
        'filtro_conta': conta_id,
        'boletos_disponiveis': boletos_disponiveis,
    }
    return render(request, 'financeiro/cnab/gerar_remessa.html', context)


@login_required
@require_POST
def regenerar_arquivo_remessa(request, pk):
    """Regenera um arquivo de remessa existente"""
    from .models import ArquivoRemessa
    from .services.cnab_service import CNABService

    arquivo = get_object_or_404(ArquivoRemessa, pk=pk)

    if not arquivo.pode_reenviar:
        return JsonResponse({
            'sucesso': False,
            'erro': 'Este arquivo nao pode ser regenerado'
        }, status=400)

    try:
        service = CNABService()
        resultado = service.regenerar_remessa(arquivo)

        if resultado.get('sucesso'):
            return JsonResponse({
                'sucesso': True,
                'mensagem': 'Remessa regenerada com sucesso',
                'redirect': f"/financeiro/cnab/remessa/{resultado.get('arquivo_remessa').pk}/"
            })
        else:
            return JsonResponse({
                'sucesso': False,
                'erro': resultado.get('erro')
            }, status=500)

    except Exception as e:
        logger.exception(f"Erro ao regenerar remessa: {e}")
        return JsonResponse({
            'sucesso': False,
            'erro': str(e)
        }, status=500)


@login_required
@require_POST
def marcar_remessa_enviada(request, pk):
    """Marca um arquivo de remessa como enviado ao banco"""
    from .models import ArquivoRemessa

    arquivo = get_object_or_404(ArquivoRemessa, pk=pk)

    if arquivo.status != 'GERADO':
        return JsonResponse({
            'sucesso': False,
            'erro': 'Apenas arquivos com status GERADO podem ser marcados como enviados'
        }, status=400)

    arquivo.marcar_enviado()
    return JsonResponse({
        'sucesso': True,
        'mensagem': 'Remessa marcada como enviada'
    })


@login_required
def download_arquivo_remessa(request, pk):
    """Download do arquivo de remessa"""
    from .models import ArquivoRemessa

    arquivo = get_object_or_404(ArquivoRemessa, pk=pk)

    if not arquivo.arquivo:
        messages.error(request, 'Arquivo nao disponivel para download.')
        return redirect('financeiro:detalhe_remessa', pk=pk)

    try:
        response = FileResponse(
            arquivo.arquivo.open('rb'),
            as_attachment=True,
            filename=arquivo.nome_arquivo
        )
        response['Content-Type'] = 'text/plain'
        return response
    except Exception as e:
        logger.exception(f"Erro ao fazer download da remessa: {e}")
        messages.error(request, 'Erro ao baixar o arquivo.')
        return redirect('financeiro:detalhe_remessa', pk=pk)


# =============================================================================
# VIEWS DE ARQUIVO DE RETORNO
# =============================================================================

@login_required
def listar_arquivos_retorno(request):
    """Lista todos os arquivos de retorno"""
    from .models import ArquivoRetorno

    arquivos = ArquivoRetorno.objects.select_related(
        'conta_bancaria', 'conta_bancaria__imobiliaria', 'processado_por'
    ).order_by('-data_upload')

    # Filtros
    conta_id = request.GET.get('conta')
    status = request.GET.get('status')

    if conta_id:
        arquivos = arquivos.filter(conta_bancaria_id=conta_id)
    if status:
        arquivos = arquivos.filter(status=status)

    contas = ContaBancaria.objects.filter(ativo=True).select_related('imobiliaria')

    context = {
        'arquivos': arquivos[:100],
        'contas_bancarias': contas,
        'filtro_conta': conta_id,
        'filtro_status': status,
    }
    return render(request, 'financeiro/cnab/listar_retornos.html', context)


@login_required
def detalhe_arquivo_retorno(request, pk):
    """Exibe detalhes de um arquivo de retorno"""
    from .models import ArquivoRetorno

    arquivo = get_object_or_404(
        ArquivoRetorno.objects.select_related(
            'conta_bancaria', 'conta_bancaria__imobiliaria', 'processado_por'
        ).prefetch_related(
            'itens', 'itens__parcela', 'itens__parcela__contrato',
            'itens__parcela__contrato__comprador'
        ),
        pk=pk
    )

    # Agrupar itens por tipo de ocorrencia
    itens_por_tipo = {}
    for item in arquivo.itens.all():
        tipo = item.tipo_ocorrencia
        if tipo not in itens_por_tipo:
            itens_por_tipo[tipo] = []
        itens_por_tipo[tipo].append(item)

    context = {
        'arquivo': arquivo,
        'itens': arquivo.itens.all(),
        'itens_por_tipo': itens_por_tipo,
    }
    return render(request, 'financeiro/cnab/detalhe_retorno.html', context)


@login_required
def upload_arquivo_retorno(request):
    """Upload de arquivo de retorno para processamento"""
    from .models import ArquivoRetorno

    contas = ContaBancaria.objects.filter(ativo=True).select_related('imobiliaria')

    if request.method == 'POST':
        conta_id = request.POST.get('conta_bancaria')
        arquivo_upload = request.FILES.get('arquivo')

        if not conta_id:
            messages.error(request, 'Selecione uma conta bancaria.')
            return redirect('financeiro:upload_retorno')

        if not arquivo_upload:
            messages.error(request, 'Selecione um arquivo para upload.')
            return redirect('financeiro:upload_retorno')

        conta = get_object_or_404(ContaBancaria, pk=conta_id, ativo=True)

        try:
            arquivo_retorno = ArquivoRetorno.objects.create(
                conta_bancaria=conta,
                nome_arquivo=arquivo_upload.name,
            )
            arquivo_retorno.arquivo.save(arquivo_upload.name, arquivo_upload)

            messages.success(
                request,
                f"Arquivo '{arquivo_upload.name}' carregado com sucesso! "
                f"Clique em 'Processar' para realizar a baixa dos boletos."
            )
            return redirect('financeiro:detalhe_retorno', pk=arquivo_retorno.pk)

        except Exception as e:
            logger.exception(f"Erro ao fazer upload do retorno: {e}")
            messages.error(request, f"Erro ao fazer upload: {str(e)}")

        return redirect('financeiro:upload_retorno')

    context = {
        'contas_bancarias': contas,
    }
    return render(request, 'financeiro/cnab/upload_retorno.html', context)


@login_required
@require_POST
def processar_arquivo_retorno(request, pk):
    """Processa um arquivo de retorno (realiza as baixas)"""
    from .models import ArquivoRetorno
    from .services.cnab_service import CNABService

    arquivo = get_object_or_404(ArquivoRetorno, pk=pk)

    if not arquivo.pode_reprocessar:
        return JsonResponse({
            'sucesso': False,
            'erro': 'Este arquivo ja foi processado e nao pode ser reprocessado'
        }, status=400)

    try:
        service = CNABService()
        resultado = service.processar_retorno(arquivo, request.user)

        if resultado.get('sucesso'):
            return JsonResponse({
                'sucesso': True,
                'mensagem': 'Arquivo processado com sucesso',
                'total_registros': resultado.get('total_registros'),
                'registros_processados': resultado.get('registros_processados'),
                'registros_erro': resultado.get('registros_erro'),
                'valor_total_pago': str(resultado.get('valor_total_pago')),
            })
        else:
            return JsonResponse({
                'sucesso': False,
                'erro': resultado.get('erro')
            }, status=500)

    except Exception as e:
        logger.exception(f"Erro ao processar retorno: {e}")
        return JsonResponse({
            'sucesso': False,
            'erro': str(e)
        }, status=500)


@login_required
def download_arquivo_retorno(request, pk):
    """Download do arquivo de retorno"""
    from .models import ArquivoRetorno

    arquivo = get_object_or_404(ArquivoRetorno, pk=pk)

    if not arquivo.arquivo:
        messages.error(request, 'Arquivo nao disponivel para download.')
        return redirect('financeiro:detalhe_retorno', pk=pk)

    try:
        response = FileResponse(
            arquivo.arquivo.open('rb'),
            as_attachment=True,
            filename=arquivo.nome_arquivo
        )
        response['Content-Type'] = 'text/plain'
        return response
    except Exception as e:
        logger.exception(f"Erro ao fazer download do retorno: {e}")
        messages.error(request, 'Erro ao baixar o arquivo.')
        return redirect('financeiro:detalhe_retorno', pk=pk)


# =============================================================================
# VIEWS DE PAGAMENTO E CARNE
# =============================================================================

@login_required
@require_POST
def pagar_parcela_ajax(request, pk):
    """
    Registra o pagamento de uma parcela via AJAX.
    Permite editar juros, multa e desconto manualmente.
    """
    from .models import HistoricoPagamento

    parcela = get_object_or_404(Parcela, pk=pk)

    if parcela.pago:
        return JsonResponse({
            'sucesso': False,
            'erro': 'Esta parcela ja esta paga'
        }, status=400)

    try:
        data_pagamento = request.POST.get('data_pagamento')
        valor_pago = Decimal(request.POST.get('valor_pago', 0))
        valor_juros = Decimal(request.POST.get('valor_juros', 0))
        valor_multa = Decimal(request.POST.get('valor_multa', 0))
        valor_desconto = Decimal(request.POST.get('valor_desconto', 0))
        observacoes = request.POST.get('observacoes', '')

        if not data_pagamento:
            data_pagamento = timezone.now().date()

        # Atualizar parcela
        parcela.valor_juros = valor_juros
        parcela.valor_multa = valor_multa
        parcela.valor_desconto = valor_desconto
        parcela.pago = True
        parcela.data_pagamento = data_pagamento
        parcela.valor_pago = valor_pago

        if observacoes:
            parcela.observacoes = observacoes

        # Atualizar status do boleto se houver
        if parcela.tem_boleto:
            parcela.status_boleto = StatusBoleto.PAGO
            parcela.data_pagamento_boleto = timezone.now()
            parcela.valor_pago_boleto = valor_pago

        parcela.save()

        # Registrar historico
        HistoricoPagamento.objects.create(
            parcela=parcela,
            data_pagamento=data_pagamento,
            valor_pago=valor_pago,
            valor_parcela=parcela.valor_atual,
            valor_juros=valor_juros,
            valor_multa=valor_multa,
            valor_desconto=valor_desconto,
            forma_pagamento='DINHEIRO',
            observacoes=observacoes
        )

        return JsonResponse({
            'sucesso': True,
            'mensagem': 'Pagamento registrado com sucesso',
            'parcela_id': parcela.id
        })

    except Exception as e:
        logger.exception(f"Erro ao registrar pagamento: {e}")
        return JsonResponse({
            'sucesso': False,
            'erro': str(e)
        }, status=500)


@login_required
@require_POST
def gerar_carne(request, contrato_id):
    """
    Gera boletos para multiplas parcelas de um contrato (carne).

    IMPORTANTE: Utiliza o método pode_gerar_boleto() do contrato para
    verificar bloqueio por reajuste. Boletos de parcelas de ciclos
    sem reajuste aplicado serão bloqueados.
    """
    import json

    contrato = get_object_or_404(Contrato, pk=contrato_id)

    try:
        data = json.loads(request.body)
        parcela_ids = data.get('parcelas', [])
        force = data.get('force', False)

        if not parcela_ids:
            return JsonResponse({
                'sucesso': False,
                'erro': 'Nenhuma parcela selecionada'
            }, status=400)

        # Buscar parcelas
        parcelas = Parcela.objects.filter(
            pk__in=parcela_ids,
            contrato=contrato,
            pago=False
        ).order_by('numero_parcela')

        if not parcelas.exists():
            return JsonResponse({
                'sucesso': False,
                'erro': 'Nenhuma parcela valida encontrada'
            }, status=400)

        resultados = []
        gerados = 0
        bloqueados = 0
        erros = 0

        for parcela in parcelas:
            # =====================================================================
            # VERIFICAÇÃO DE BLOQUEIO POR REAJUSTE (usando pode_gerar_boleto)
            # =====================================================================
            if not force and hasattr(contrato, 'pode_gerar_boleto'):
                pode_gerar, motivo = contrato.pode_gerar_boleto(parcela.numero_parcela)
                if not pode_gerar:
                    resultados.append({
                        'parcela_id': parcela.id,
                        'numero_parcela': parcela.numero_parcela,
                        'sucesso': False,
                        'bloqueado_reajuste': True,
                        'erro': motivo
                    })
                    bloqueados += 1
                    continue

            # Verificar se ja tem boleto
            if parcela.tem_boleto and not force:
                resultados.append({
                    'parcela_id': parcela.id,
                    'numero_parcela': parcela.numero_parcela,
                    'sucesso': True,
                    'mensagem': 'Boleto ja existente'
                })
                continue

            # Gerar boleto
            try:
                resultado = parcela.gerar_boleto(enviar_email=False)
                if resultado and resultado.get('sucesso'):
                    gerados += 1
                    resultados.append({
                        'parcela_id': parcela.id,
                        'numero_parcela': parcela.numero_parcela,
                        'sucesso': True,
                        'nosso_numero': resultado.get('nosso_numero')
                    })

                    # Atualizar último mês com boleto gerado
                    if hasattr(contrato, 'ultimo_mes_boleto_gerado'):
                        if parcela.numero_parcela > contrato.ultimo_mes_boleto_gerado:
                            contrato.ultimo_mes_boleto_gerado = parcela.numero_parcela
                else:
                    erros += 1
                    resultados.append({
                        'parcela_id': parcela.id,
                        'numero_parcela': parcela.numero_parcela,
                        'sucesso': False,
                        'erro': resultado.get('erro') if resultado else 'Erro desconhecido'
                    })
            except Exception as e:
                erros += 1
                resultados.append({
                    'parcela_id': parcela.id,
                    'numero_parcela': parcela.numero_parcela,
                    'sucesso': False,
                    'erro': str(e)
                })

        # Salvar atualização do último mês com boleto gerado
        if hasattr(contrato, 'ultimo_mes_boleto_gerado'):
            contrato.save(update_fields=['ultimo_mes_boleto_gerado'])

        return JsonResponse({
            'sucesso': True,
            'gerados': gerados,
            'bloqueados': bloqueados,
            'erros': erros,
            'total': len(parcela_ids),
            'resultados': resultados,
            'mensagem': f'{gerados} boletos gerados, {bloqueados} bloqueados por reajuste'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'sucesso': False,
            'erro': 'Dados invalidos'
        }, status=400)
    except Exception as e:
        logger.exception(f"Erro ao gerar carne: {e}")
        return JsonResponse({
            'sucesso': False,
            'erro': str(e)
        }, status=500)


@login_required
@require_GET
def api_parcelas_elegibilidade(request, contrato_id):
    """
    Retorna informacoes sobre elegibilidade de geracao de boletos para parcelas.

    Regras de elegibilidade por ciclo de reajuste:
    - Ciclo 1 (parcelas 1-12 para prazo_reajuste_meses=12): Sempre liberado
    - Ciclo 2+ (parcelas 13+): Requer reajuste aplicado para o ciclo
    - tipo_correcao='FIXO': Todas as parcelas liberadas (sem reajuste necessario)

    Retorna lista de parcelas com status de elegibilidade e informacoes do ciclo.
    """
    contrato = get_object_or_404(Contrato, pk=contrato_id)

    # Obter todas as parcelas nao pagas
    parcelas = contrato.parcelas.filter(pago=False).order_by('numero_parcela')

    # Verificar se o tipo de correcao e FIXO (sem reajuste necessario)
    tipo_correcao_fixo = contrato.tipo_correcao == 'FIXO'

    # Informacoes do ciclo atual
    prazo_reajuste = contrato.prazo_reajuste_meses or 12
    ciclo_atual = contrato.ciclo_reajuste_atual or 1

    # Reajustes aplicados
    from financeiro.models import Reajuste
    reajustes_aplicados = set(
        Reajuste.objects.filter(contrato=contrato, aplicado=True)
        .values_list('ciclo', flat=True)
    )

    # Calcular maximo de parcelas disponiveis para geracao
    parcelas_disponiveis = []
    primeiro_ciclo_bloqueado = None
    total_disponiveis = 0
    total_bloqueadas = 0

    for parcela in parcelas:
        ciclo_parcela = contrato.calcular_ciclo_parcela(parcela.numero_parcela)

        # Determinar elegibilidade
        if tipo_correcao_fixo:
            # FIXO: todas liberadas
            pode_gerar = True
            motivo = "Indice FIXO - sem reajuste necessario"
        elif ciclo_parcela == 1:
            # Primeiro ciclo: sempre liberado
            pode_gerar = True
            motivo = "Primeiro ciclo - liberado"
        elif ciclo_parcela in reajustes_aplicados:
            # Reajuste ja aplicado para este ciclo
            pode_gerar = True
            motivo = f"Reajuste do ciclo {ciclo_parcela} aplicado"
        else:
            # Reajuste pendente
            pode_gerar = False
            motivo = f"Aguardando reajuste do ciclo {ciclo_parcela}"
            if primeiro_ciclo_bloqueado is None:
                primeiro_ciclo_bloqueado = ciclo_parcela

        if pode_gerar:
            total_disponiveis += 1
        else:
            total_bloqueadas += 1

        parcelas_disponiveis.append({
            'id': parcela.id,
            'numero_parcela': parcela.numero_parcela,
            'data_vencimento': parcela.data_vencimento.strftime('%d/%m/%Y'),
            'valor_atual': float(parcela.valor_atual),
            'ciclo': ciclo_parcela,
            'pode_gerar': pode_gerar,
            'tem_boleto': parcela.tem_boleto,
            'motivo': motivo
        })

    # Calcular informacoes do proximo ciclo de reajuste
    proximo_ciclo_reajuste = None
    if primeiro_ciclo_bloqueado:
        parcela_inicio_ciclo = ((primeiro_ciclo_bloqueado - 1) * prazo_reajuste) + 1
        parcela_fim_ciclo = primeiro_ciclo_bloqueado * prazo_reajuste
        proximo_ciclo_reajuste = {
            'ciclo': primeiro_ciclo_bloqueado,
            'parcela_inicial': parcela_inicio_ciclo,
            'parcela_final': min(parcela_fim_ciclo, contrato.numero_parcelas),
            'mensagem': f"Aplique o reajuste para liberar as parcelas {parcela_inicio_ciclo} a {min(parcela_fim_ciclo, contrato.numero_parcelas)}"
        }

    return JsonResponse({
        'sucesso': True,
        'contrato_id': contrato.id,
        'tipo_correcao': contrato.tipo_correcao,
        'tipo_correcao_fixo': tipo_correcao_fixo,
        'prazo_reajuste_meses': prazo_reajuste,
        'ciclo_atual': ciclo_atual,
        'reajustes_aplicados': list(reajustes_aplicados),
        'total_parcelas_pendentes': parcelas.count(),
        'total_disponiveis': total_disponiveis,
        'total_bloqueadas': total_bloqueadas,
        'proximo_ciclo_reajuste': proximo_ciclo_reajuste,
        'parcelas': parcelas_disponiveis
    })


@login_required
@require_POST
def api_gerar_boletos_lote(request):
    """
    Gera boletos em lote para multiplos contratos.

    Recebe:
    - contratos: lista de IDs de contratos
    - quantidade: quantidade de boletos por contrato (opcional, padrao=1)
    - force: ignorar bloqueio de reajuste (opcional, padrao=False)

    Respeita a logica de reajuste:
    - Gera apenas parcelas cujo ciclo ja teve reajuste aplicado
    - tipo_correcao='FIXO' permite gerar todas as parcelas
    """
    import json

    try:
        data = json.loads(request.body)
        contrato_ids = data.get('contratos', [])
        quantidade = int(data.get('quantidade', 1))
        force = data.get('force', False)

        if not contrato_ids:
            return JsonResponse({
                'sucesso': False,
                'erro': 'Nenhum contrato selecionado'
            }, status=400)

        if quantidade < 1:
            quantidade = 1

        resultados = []
        total_gerados = 0
        total_bloqueados = 0
        total_erros = 0

        for contrato_id in contrato_ids:
            try:
                contrato = Contrato.objects.get(pk=contrato_id, status='ATIVO')
            except Contrato.DoesNotExist:
                resultados.append({
                    'contrato_id': contrato_id,
                    'sucesso': False,
                    'erro': 'Contrato nao encontrado ou inativo'
                })
                total_erros += 1
                continue

            # Obter parcelas elegiveis (nao pagas, sem boleto, elegíveis por reajuste)
            parcelas = contrato.parcelas.filter(
                pago=False,
                status_boleto='NAO_GERADO'
            ).order_by('numero_parcela')

            gerados_contrato = 0
            bloqueados_contrato = 0
            parcelas_resultado = []

            for parcela in parcelas[:quantidade + 10]:  # Pegar algumas extras caso algumas sejam bloqueadas
                if gerados_contrato >= quantidade:
                    break

                # Verificar elegibilidade por reajuste
                if not force:
                    pode_gerar, motivo = contrato.pode_gerar_boleto(parcela.numero_parcela)
                    if not pode_gerar:
                        bloqueados_contrato += 1
                        parcelas_resultado.append({
                            'parcela_id': parcela.id,
                            'numero_parcela': parcela.numero_parcela,
                            'sucesso': False,
                            'bloqueado': True,
                            'motivo': motivo
                        })
                        continue

                # Gerar boleto
                try:
                    resultado = parcela.gerar_boleto(enviar_email=False)
                    if resultado and resultado.get('sucesso'):
                        gerados_contrato += 1
                        total_gerados += 1

                        # Atualizar ultimo mes com boleto gerado
                        if parcela.numero_parcela > contrato.ultimo_mes_boleto_gerado:
                            contrato.ultimo_mes_boleto_gerado = parcela.numero_parcela

                        parcelas_resultado.append({
                            'parcela_id': parcela.id,
                            'numero_parcela': parcela.numero_parcela,
                            'sucesso': True,
                            'nosso_numero': resultado.get('nosso_numero')
                        })
                    else:
                        total_erros += 1
                        parcelas_resultado.append({
                            'parcela_id': parcela.id,
                            'numero_parcela': parcela.numero_parcela,
                            'sucesso': False,
                            'erro': resultado.get('erro') if resultado else 'Erro desconhecido'
                        })
                except Exception as e:
                    total_erros += 1
                    parcelas_resultado.append({
                        'parcela_id': parcela.id,
                        'numero_parcela': parcela.numero_parcela,
                        'sucesso': False,
                        'erro': str(e)
                    })

            # Salvar atualizacao do contrato
            if gerados_contrato > 0:
                contrato.save(update_fields=['ultimo_mes_boleto_gerado'])

            total_bloqueados += bloqueados_contrato

            resultados.append({
                'contrato_id': contrato_id,
                'numero_contrato': contrato.numero_contrato,
                'sucesso': gerados_contrato > 0,
                'gerados': gerados_contrato,
                'bloqueados': bloqueados_contrato,
                'parcelas': parcelas_resultado
            })

        return JsonResponse({
            'sucesso': True,
            'total_contratos': len(contrato_ids),
            'total_gerados': total_gerados,
            'total_bloqueados': total_bloqueados,
            'total_erros': total_erros,
            'resultados': resultados,
            'mensagem': f'{total_gerados} boletos gerados em {len(contrato_ids)} contrato(s)'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'sucesso': False,
            'erro': 'Dados invalidos'
        }, status=400)
    except Exception as e:
        logger.exception(f"Erro ao gerar boletos em lote: {e}")
        return JsonResponse({
            'sucesso': False,
            'erro': str(e)
        }, status=500)


# =============================================================================
# REAJUSTES DE CONTRATO
# =============================================================================

@login_required
@require_POST
def aplicar_reajuste_contrato(request, contrato_id):
    """
    Aplica um reajuste manual nas parcelas de um contrato.
    Recebe: indice_tipo, percentual, parcela_inicial, parcela_final, observacoes
    """
    contrato = get_object_or_404(Contrato, pk=contrato_id)

    try:
        import json
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST

        indice_tipo = data.get('indice_tipo', 'MANUAL')
        percentual = Decimal(str(data.get('percentual', 0)))
        parcela_inicial = int(data.get('parcela_inicial', 1))
        parcela_final = int(data.get('parcela_final', contrato.numero_parcelas))
        observacoes = data.get('observacoes', '')

        if percentual == 0:
            return JsonResponse({
                'sucesso': False,
                'erro': 'O percentual de reajuste nao pode ser zero'
            }, status=400)

        # Validar parcelas
        if parcela_inicial < 1 or parcela_final > contrato.numero_parcelas:
            return JsonResponse({
                'sucesso': False,
                'erro': 'Numeros de parcela invalidos'
            }, status=400)

        if parcela_inicial > parcela_final:
            return JsonResponse({
                'sucesso': False,
                'erro': 'Parcela inicial deve ser menor ou igual a parcela final'
            }, status=400)

        # Verificar se há parcelas não pagas no intervalo
        parcelas_pendentes = contrato.parcelas.filter(
            numero_parcela__gte=parcela_inicial,
            numero_parcela__lte=parcela_final,
            pago=False
        )

        if not parcelas_pendentes.exists():
            return JsonResponse({
                'sucesso': False,
                'erro': 'Nenhuma parcela pendente no intervalo selecionado'
            }, status=400)

        # Criar o registro de reajuste
        reajuste = Reajuste.objects.create(
            contrato=contrato,
            data_reajuste=timezone.now().date(),
            indice_tipo=indice_tipo,
            percentual=percentual,
            parcela_inicial=parcela_inicial,
            parcela_final=parcela_final,
            aplicado_manual=True,
            observacoes=observacoes
        )

        # Aplicar o reajuste nas parcelas
        reajuste.aplicar_reajuste()

        # Contar parcelas afetadas
        parcelas_afetadas = parcelas_pendentes.count()

        return JsonResponse({
            'sucesso': True,
            'mensagem': f'Reajuste de {percentual}% aplicado com sucesso em {parcelas_afetadas} parcela(s)',
            'reajuste_id': reajuste.id,
            'parcelas_afetadas': parcelas_afetadas
        })

    except ValueError as e:
        return JsonResponse({
            'sucesso': False,
            'erro': f'Valor invalido: {str(e)}'
        }, status=400)
    except Exception as e:
        logger.exception(f"Erro ao aplicar reajuste: {e}")
        return JsonResponse({
            'sucesso': False,
            'erro': str(e)
        }, status=500)


@login_required
@require_POST
def excluir_reajuste(request, pk):
    """
    Exclui um reajuste e reverte os valores das parcelas.
    Apenas reajustes manuais podem ser excluidos.
    """
    reajuste = get_object_or_404(Reajuste, pk=pk)

    if not reajuste.aplicado_manual:
        return JsonResponse({
            'sucesso': False,
            'erro': 'Apenas reajustes manuais podem ser excluidos'
        }, status=400)

    try:
        contrato = reajuste.contrato

        # Reverter o reajuste nas parcelas
        fator_reajuste = 1 + (reajuste.percentual / 100)

        parcelas = contrato.parcelas.filter(
            numero_parcela__gte=reajuste.parcela_inicial,
            numero_parcela__lte=reajuste.parcela_final,
            pago=False
        )

        for parcela in parcelas:
            # Reverter o valor (dividir pelo fator aplicado)
            parcela.valor_atual = parcela.valor_atual / fator_reajuste
            parcela.save()

        # Excluir o registro de reajuste
        reajuste.delete()

        return JsonResponse({
            'sucesso': True,
            'mensagem': 'Reajuste excluido e valores revertidos com sucesso'
        })

    except Exception as e:
        logger.exception(f"Erro ao excluir reajuste: {e}")
        return JsonResponse({
            'sucesso': False,
            'erro': str(e)
        }, status=500)


@login_required
def obter_indice_reajuste(request):
    """
    Retorna o percentual do indice de reajuste para um tipo e periodo.
    Parametros GET: tipo_indice, ano, mes
    """
    from contratos.models import IndiceReajuste

    tipo_indice = request.GET.get('tipo_indice', '')
    ano = request.GET.get('ano', timezone.now().year)
    mes = request.GET.get('mes', timezone.now().month)

    try:
        ano = int(ano)
        mes = int(mes)

        indice = IndiceReajuste.objects.filter(
            tipo_indice=tipo_indice,
            ano=ano,
            mes=mes
        ).first()

        if indice:
            return JsonResponse({
                'sucesso': True,
                'percentual': float(indice.valor),  # Campo correto e 'valor', nao 'percentual'
                'valor': float(indice.valor),
                'tipo_indice': indice.tipo_indice,
                'ano': indice.ano,
                'mes': indice.mes,
                'valor_acumulado_12m': float(indice.valor_acumulado_12m) if indice.valor_acumulado_12m else None,
                'valor_acumulado_ano': float(indice.valor_acumulado_ano) if indice.valor_acumulado_ano else None,
            })
        else:
            return JsonResponse({
                'sucesso': False,
                'erro': f'Indice {tipo_indice} nao encontrado para {mes}/{ano}'
            })

    except Exception as e:
        return JsonResponse({
            'sucesso': False,
            'erro': str(e)
        }, status=500)


@login_required
def calcular_reajuste_proporcional(request, contrato_id):
    """
    Calcula o percentual de reajuste acumulado proporcional para um contrato.

    O calculo considera:
    - Primeiro mes: proporcional aos dias restantes do mes
    - Meses intermediarios: indice completo
    - Ultimo mes: proporcional aos dias do mes ate a data final

    Parametros GET: tipo_indice (opcional, usa o indice do contrato se nao informado)
    """
    from contratos.models import IndiceReajuste
    from calendar import monthrange
    from datetime import date

    contrato = get_object_or_404(Contrato, pk=contrato_id)

    try:
        tipo_indice = request.GET.get('tipo_indice', contrato.get_tipo_correcao_display())

        # Determinar periodo do reajuste
        if contrato.data_ultimo_reajuste:
            data_inicio = contrato.data_ultimo_reajuste
        else:
            data_inicio = contrato.data_contrato

        data_fim = timezone.now().date()

        # Se nao passou prazo minimo, retornar 0
        meses_desde = (data_fim.year - data_inicio.year) * 12 + (data_fim.month - data_inicio.month)
        if meses_desde < contrato.prazo_reajuste_meses:
            return JsonResponse({
                'sucesso': False,
                'erro': f'Reajuste ainda nao e necessario. Proximo reajuste em {contrato.prazo_reajuste_meses - meses_desde} mese(s).'
            })

        # Calcular reajuste proporcional
        fator_acumulado = Decimal('1.0')
        detalhes_meses = []

        # Iterar pelos meses do periodo
        mes_atual = data_inicio.month
        ano_atual = data_inicio.year

        while (ano_atual < data_fim.year) or (ano_atual == data_fim.year and mes_atual <= data_fim.month):
            # Buscar indice do mes
            indice = IndiceReajuste.objects.filter(
                tipo_indice=tipo_indice,
                ano=ano_atual,
                mes=mes_atual
            ).first()

            if indice:
                percentual_mes = indice.valor  # Campo correto e 'valor', nao 'percentual'
            else:
                percentual_mes = Decimal('0')

            # Calcular dias do mes
            dias_no_mes = monthrange(ano_atual, mes_atual)[1]

            # Primeiro mes - proporcional
            if ano_atual == data_inicio.year and mes_atual == data_inicio.month:
                dias_considerados = dias_no_mes - data_inicio.day + 1
                proporcao = Decimal(dias_considerados) / Decimal(dias_no_mes)
            # Ultimo mes - proporcional
            elif ano_atual == data_fim.year and mes_atual == data_fim.month:
                dias_considerados = data_fim.day
                proporcao = Decimal(dias_considerados) / Decimal(dias_no_mes)
            # Meses intermediarios - completo
            else:
                dias_considerados = dias_no_mes
                proporcao = Decimal('1.0')

            # Aplicar proporcao ao indice
            percentual_proporcional = percentual_mes * proporcao
            fator_mes = 1 + (percentual_proporcional / 100)
            fator_acumulado *= fator_mes

            detalhes_meses.append({
                'mes': mes_atual,
                'ano': ano_atual,
                'indice_original': float(percentual_mes),
                'dias_considerados': dias_considerados,
                'dias_mes': dias_no_mes,
                'proporcao': float(proporcao),
                'indice_proporcional': float(percentual_proporcional)
            })

            # Avancar para proximo mes
            mes_atual += 1
            if mes_atual > 12:
                mes_atual = 1
                ano_atual += 1

        # Calcular percentual total
        percentual_total = (fator_acumulado - 1) * 100

        return JsonResponse({
            'sucesso': True,
            'percentual_acumulado': float(percentual_total),
            'fator_acumulado': float(fator_acumulado),
            'data_inicio': data_inicio.strftime('%d/%m/%Y'),
            'data_fim': data_fim.strftime('%d/%m/%Y'),
            'tipo_indice': tipo_indice,
            'meses_detalhes': detalhes_meses,
            'total_meses': len(detalhes_meses)
        })

    except Exception as e:
        logger.exception(f"Erro ao calcular reajuste proporcional: {e}")
        return JsonResponse({
            'sucesso': False,
            'erro': str(e)
        }, status=500)


@login_required
def api_calcular_indice_acumulado(request):
    """
    API para calcular o índice acumulado com detalhes completos.

    Metodologia Cálculo Exato (calculoexato.com.br):
    - Fator = produto de (1 + índice_mensal/100) para cada mês
    - Percentual acumulado = (Fator - 1) * 100
    - Valor atualizado = Valor original * Fator

    Parâmetros GET:
        tipo_indice: Tipo do índice (IPCA, IGPM, etc.)
        ano_inicio: Ano inicial
        mes_inicio: Mês inicial
        ano_fim: Ano final
        mes_fim: Mês final
        proporcional: Se 'true', calcula pro-rata para primeiro/último mês
        valor_original: Valor para simular atualização (opcional)

    Retorno:
        JSON com detalhes completos do cálculo incluindo:
        - fator_acumulado: Fator multiplicador
        - percentual_acumulado: Percentual de correção
        - meses: Lista com detalhes de cada mês
        - calculo_detalhado: Fórmula textual do cálculo
        - valor_atualizado: Se valor_original informado
    """
    from financeiro.services.reajuste_service import ReajusteService
    from datetime import date

    try:
        tipo_indice = request.GET.get('tipo_indice', 'IPCA')
        ano_inicio = int(request.GET.get('ano_inicio', timezone.now().year - 1))
        mes_inicio = int(request.GET.get('mes_inicio', 1))
        ano_fim = int(request.GET.get('ano_fim', timezone.now().year))
        mes_fim = int(request.GET.get('mes_fim', timezone.now().month))
        proporcional = request.GET.get('proporcional', 'false').lower() == 'true'
        valor_original_str = request.GET.get('valor_original', '')

        # Criar datas
        data_inicio = date(ano_inicio, mes_inicio, 1)
        data_fim = date(ano_fim, mes_fim, 1)

        # Validar datas
        if data_inicio > data_fim:
            return JsonResponse({
                'sucesso': False,
                'erro': 'Data inicial deve ser anterior ou igual à data final'
            }, status=400)

        # Calcular usando o serviço
        service = ReajusteService()
        resultado = service.calcular_indice_acumulado_detalhado(
            tipo_indice=tipo_indice,
            data_inicio=data_inicio,
            data_fim=data_fim,
            proporcional=proporcional
        )

        # Se valor original informado, calcular valor atualizado
        if valor_original_str:
            try:
                valor_original = Decimal(valor_original_str.replace(',', '.'))
                fator = Decimal(str(resultado['fator_acumulado']))
                valor_atualizado = valor_original * fator
                resultado['valor_original'] = float(valor_original)
                resultado['valor_atualizado'] = float(valor_atualizado)
                resultado['diferenca'] = float(valor_atualizado - valor_original)
            except (ValueError, TypeError):
                pass

        return JsonResponse(resultado)

    except ValueError as e:
        return JsonResponse({
            'sucesso': False,
            'erro': f'Valor inválido: {str(e)}'
        }, status=400)
    except Exception as e:
        logger.exception(f"Erro ao calcular índice acumulado: {e}")
        return JsonResponse({
            'sucesso': False,
            'erro': str(e)
        }, status=500)


# =============================================================================
# DASHBOARD CONSOLIDADO DA CONTABILIDADE
# =============================================================================

class DashboardContabilidadeView(LoginRequiredMixin, TemplateView):
    """
    Dashboard consolidado para a Contabilidade.

    Apresenta visão geral de todas as imobiliárias sob gestão,
    com estatísticas consolidadas e alertas importantes.
    """
    template_name = 'financeiro/dashboard_contabilidade.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from core.models import Contabilidade
        from contratos.models import PrestacaoIntermediaria

        hoje = timezone.now().date()

        # Filtro por contabilidade (se usuário tiver acesso restrito)
        contabilidade_id = self.request.GET.get('contabilidade')
        contabilidade_selecionada = None

        if contabilidade_id:
            try:
                contabilidade_selecionada = Contabilidade.objects.get(pk=contabilidade_id)
            except Contabilidade.DoesNotExist:
                pass

        # Lista de contabilidades
        contabilidades = Contabilidade.objects.filter(ativo=True)
        context['contabilidades'] = contabilidades
        context['contabilidade_selecionada'] = contabilidade_selecionada

        # Base querysets
        if contabilidade_selecionada:
            imobiliarias = Imobiliaria.objects.filter(
                contabilidade=contabilidade_selecionada, ativo=True
            )
        else:
            imobiliarias = Imobiliaria.objects.filter(ativo=True)

        imobiliaria_ids = imobiliarias.values_list('id', flat=True)

        contratos_qs = Contrato.objects.filter(imobiliaria__in=imobiliaria_ids)
        parcelas_qs = Parcela.objects.filter(contrato__imobiliaria__in=imobiliaria_ids)

        # =========================================================================
        # ESTATÍSTICAS GERAIS
        # =========================================================================
        context['total_imobiliarias'] = imobiliarias.count()

        # Estatísticas de contratos
        stats_contratos = contratos_qs.aggregate(
            total=Count('id'),
            ativos=Count('id', filter=Q(status=StatusContrato.ATIVO)),
            quitados=Count('id', filter=Q(status=StatusContrato.QUITADO)),
            cancelados=Count('id', filter=Q(status=StatusContrato.CANCELADO)),
            valor_total=Sum('valor_total'),
        )
        context['stats_contratos'] = stats_contratos

        # Estatísticas de parcelas
        stats_parcelas = parcelas_qs.aggregate(
            total=Count('id'),
            pagas=Count('id', filter=Q(pago=True)),
            pendentes=Count('id', filter=Q(pago=False)),
            vencidas=Count('id', filter=Q(pago=False, data_vencimento__lt=hoje)),
            valor_total=Sum('valor_atual'),
            valor_recebido=Sum('valor_pago', filter=Q(pago=True)),
            valor_pendente=Sum('valor_atual', filter=Q(pago=False)),
            valor_vencido=Sum('valor_atual', filter=Q(pago=False, data_vencimento__lt=hoje)),
        )
        context['stats_parcelas'] = stats_parcelas

        # =========================================================================
        # ESTATÍSTICAS POR IMOBILIÁRIA
        # =========================================================================
        stats_por_imobiliaria = []
        for imob in imobiliarias:
            parcelas_imob = parcelas_qs.filter(contrato__imobiliaria=imob)
            contratos_imob = contratos_qs.filter(imobiliaria=imob)

            # Contar contratos com bloqueio por reajuste
            contratos_bloqueados = 0
            for contrato in contratos_imob.filter(status=StatusContrato.ATIVO):
                if hasattr(contrato, 'verificar_bloqueio_reajuste'):
                    bloqueio_info = contrato.verificar_bloqueio_reajuste()
                    if bloqueio_info.get('bloqueado'):
                        contratos_bloqueados += 1

            stats = {
                'imobiliaria': imob,
                'total_contratos': contratos_imob.count(),
                'contratos_ativos': contratos_imob.filter(status=StatusContrato.ATIVO).count(),
                'contratos_bloqueados': contratos_bloqueados,
                'parcelas_pendentes': parcelas_imob.filter(pago=False).count(),
                'parcelas_vencidas': parcelas_imob.filter(pago=False, data_vencimento__lt=hoje).count(),
                'valor_pendente': parcelas_imob.filter(pago=False).aggregate(
                    total=Sum('valor_atual')
                )['total'] or Decimal('0.00'),
                'valor_vencido': parcelas_imob.filter(pago=False, data_vencimento__lt=hoje).aggregate(
                    total=Sum('valor_atual')
                )['total'] or Decimal('0.00'),
            }
            stats_por_imobiliaria.append(stats)

        # Ordenar por valor vencido (mais críticos primeiro)
        stats_por_imobiliaria.sort(key=lambda x: x['valor_vencido'], reverse=True)
        context['stats_por_imobiliaria'] = stats_por_imobiliaria

        # =========================================================================
        # CONTRATOS COM REAJUSTE PENDENTE (TODAS IMOBILIÁRIAS)
        # =========================================================================
        contratos_reajuste_pendente = []
        for contrato in contratos_qs.filter(status=StatusContrato.ATIVO):
            if hasattr(contrato, 'data_ultimo_reajuste') and hasattr(contrato, 'prazo_reajuste_meses'):
                data_base = contrato.data_ultimo_reajuste or contrato.data_contrato
                proxima_data_reajuste = data_base + relativedelta(months=contrato.prazo_reajuste_meses)

                if proxima_data_reajuste <= hoje:
                    meses_atraso = (hoje.year - proxima_data_reajuste.year) * 12 + (hoje.month - proxima_data_reajuste.month)
                    contratos_reajuste_pendente.append({
                        'contrato': contrato,
                        'imobiliaria': contrato.imobiliaria,
                        'data_ultimo_reajuste': contrato.data_ultimo_reajuste,
                        'proxima_data_reajuste': proxima_data_reajuste,
                        'meses_atraso': meses_atraso,
                        'tipo_correcao': contrato.get_tipo_correcao_display() if hasattr(contrato, 'get_tipo_correcao_display') else 'N/A',
                    })

        contratos_reajuste_pendente.sort(key=lambda x: x['meses_atraso'], reverse=True)
        context['contratos_reajuste_pendente'] = contratos_reajuste_pendente[:20]
        context['total_reajustes_pendentes'] = len(contratos_reajuste_pendente)

        # =========================================================================
        # ALERTAS E INDICADORES
        # =========================================================================
        # Inadimplência (parcelas vencidas há mais de 30 dias)
        parcelas_inadimplentes = parcelas_qs.filter(
            pago=False,
            data_vencimento__lt=hoje - timedelta(days=30)
        ).count()
        context['parcelas_inadimplentes'] = parcelas_inadimplentes

        # Taxa de inadimplência
        total_parcelas = stats_parcelas['total'] or 1
        taxa_inadimplencia = (parcelas_inadimplentes / total_parcelas) * 100
        context['taxa_inadimplencia'] = round(taxa_inadimplencia, 2)

        # Receita prevista para os próximos 30 dias
        receita_prevista = parcelas_qs.filter(
            pago=False,
            data_vencimento__gte=hoje,
            data_vencimento__lte=hoje + timedelta(days=30)
        ).aggregate(total=Sum('valor_atual'))['total'] or Decimal('0.00')
        context['receita_prevista_30d'] = receita_prevista

        # =========================================================================
        # PRESTAÇÕES INTERMEDIÁRIAS
        # =========================================================================
        intermediarias_qs = PrestacaoIntermediaria.objects.filter(
            contrato__imobiliaria__in=imobiliaria_ids
        )
        stats_intermediarias = intermediarias_qs.aggregate(
            total=Count('id'),
            pagas=Count('id', filter=Q(paga=True)),
            pendentes=Count('id', filter=Q(paga=False)),
            valor_total=Sum('valor'),
            valor_pago=Sum('valor_pago', filter=Q(paga=True)),
            valor_pendente=Sum('valor', filter=Q(paga=False)),
        )
        context['stats_intermediarias'] = stats_intermediarias

        # =========================================================================
        # PERÍODO DO MÊS ATUAL
        # =========================================================================
        primeiro_dia_mes = hoje.replace(day=1)
        if hoje.month == 12:
            ultimo_dia_mes = hoje.replace(day=31)
        else:
            ultimo_dia_mes = hoje.replace(month=hoje.month + 1, day=1) - timedelta(days=1)

        parcelas_mes = parcelas_qs.filter(
            data_vencimento__gte=primeiro_dia_mes,
            data_vencimento__lte=ultimo_dia_mes
        )
        stats_mes = parcelas_mes.aggregate(
            total=Count('id'),
            pagas=Count('id', filter=Q(pago=True)),
            pendentes=Count('id', filter=Q(pago=False)),
            valor_total=Sum('valor_atual'),
            valor_recebido=Sum('valor_pago', filter=Q(pago=True)),
            valor_pendente=Sum('valor_atual', filter=Q(pago=False)),
        )
        context['stats_mes'] = stats_mes
        context['mes_atual'] = hoje.strftime('%B/%Y')

        return context


@login_required
def api_dashboard_contabilidade(request):
    """
    API para retornar dados do dashboard de contabilidade em JSON.
    Usado para gráficos e atualizações via AJAX.
    """
    from core.models import Contabilidade
    from contratos.models import PrestacaoIntermediaria

    hoje = timezone.now().date()

    # Filtro por contabilidade
    contabilidade_id = request.GET.get('contabilidade')
    if contabilidade_id:
        imobiliarias = Imobiliaria.objects.filter(
            contabilidade_id=contabilidade_id, ativo=True
        )
    else:
        imobiliarias = Imobiliaria.objects.filter(ativo=True)

    imobiliaria_ids = imobiliarias.values_list('id', flat=True)
    parcelas_qs = Parcela.objects.filter(contrato__imobiliaria__in=imobiliaria_ids)
    contratos_qs = Contrato.objects.filter(imobiliaria__in=imobiliaria_ids)

    # Dados para gráficos
    meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

    # Recebimentos por mês (últimos 12 meses)
    recebimentos_mensais = {'labels': [], 'recebido': [], 'esperado': []}
    for i in range(11, -1, -1):
        data = hoje - relativedelta(months=i)
        primeiro_dia = data.replace(day=1)
        ultimo_dia = (primeiro_dia + relativedelta(months=1)) - timedelta(days=1)

        parcelas_mes = parcelas_qs.filter(
            data_vencimento__gte=primeiro_dia,
            data_vencimento__lte=ultimo_dia
        )

        recebido = parcelas_mes.filter(pago=True).aggregate(
            total=Sum('valor_pago')
        )['total'] or 0
        esperado = parcelas_mes.aggregate(
            total=Sum('valor_atual')
        )['total'] or 0

        recebimentos_mensais['labels'].append(f"{meses[data.month-1]}/{data.year % 100}")
        recebimentos_mensais['recebido'].append(float(recebido))
        recebimentos_mensais['esperado'].append(float(esperado))

    # Distribuição por imobiliária
    distribuicao_imobiliarias = {'labels': [], 'valores': [], 'cores': []}
    cores = ['#007bff', '#28a745', '#dc3545', '#ffc107', '#17a2b8', '#6c757d', '#fd7e14', '#6610f2']

    for i, imob in enumerate(imobiliarias[:8]):  # Máximo 8 imobiliárias
        valor = parcelas_qs.filter(
            contrato__imobiliaria=imob, pago=False
        ).aggregate(total=Sum('valor_atual'))['total'] or 0

        distribuicao_imobiliarias['labels'].append(imob.nome_fantasia or imob.razao_social[:20])
        distribuicao_imobiliarias['valores'].append(float(valor))
        distribuicao_imobiliarias['cores'].append(cores[i % len(cores)])

    # Status dos contratos
    status_contratos = {
        'labels': ['Ativos', 'Quitados', 'Cancelados', 'Suspensos'],
        'data': [
            contratos_qs.filter(status=StatusContrato.ATIVO).count(),
            contratos_qs.filter(status=StatusContrato.QUITADO).count(),
            contratos_qs.filter(status=StatusContrato.CANCELADO).count(),
            contratos_qs.filter(status=StatusContrato.SUSPENSO).count(),
        ],
        'cores': ['#28a745', '#007bff', '#dc3545', '#6c757d']
    }

    return JsonResponse({
        'recebimentos_mensais': recebimentos_mensais,
        'distribuicao_imobiliarias': distribuicao_imobiliarias,
        'status_contratos': status_contratos,
    })


# =============================================================================
# VIEWS DE RELATÓRIOS AVANÇADOS
# =============================================================================

class RelatorioPrestacoesAPagarView(LoginRequiredMixin, TemplateView):
    """
    Relatório de prestações a pagar.
    Permite filtrar por contrato, período, imobiliária e status.
    """
    template_name = 'financeiro/relatorios/prestacoes_a_pagar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .services import RelatorioService, FiltroRelatorio

        # Obter parâmetros de filtro
        contrato_id = self.request.GET.get('contrato')
        imobiliaria_id = self.request.GET.get('imobiliaria')
        data_inicio = self.request.GET.get('data_inicio')
        data_fim = self.request.GET.get('data_fim')
        apenas_vencidas = self.request.GET.get('apenas_vencidas') == 'true'

        # Criar filtro
        filtro = FiltroRelatorio()
        if contrato_id:
            filtro.contrato_id = int(contrato_id)
        if imobiliaria_id:
            filtro.imobiliaria_id = int(imobiliaria_id)
        if data_inicio:
            from datetime import datetime
            filtro.data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        if data_fim:
            from datetime import datetime
            filtro.data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()

        # Gerar relatório
        service = RelatorioService()
        relatorio = service.gerar_relatorio_prestacoes_a_pagar(filtro)

        context['relatorio'] = relatorio
        context['filtros'] = {
            'contrato_id': contrato_id,
            'imobiliaria_id': imobiliaria_id,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'apenas_vencidas': apenas_vencidas,
        }

        # Listas para os filtros
        context['imobiliarias'] = Imobiliaria.objects.filter(ativo=True)
        context['contratos'] = Contrato.objects.filter(status=StatusContrato.ATIVO)

        return context


class RelatorioPrestacoesPageasView(LoginRequiredMixin, TemplateView):
    """
    Relatório de prestações pagas.
    Permite filtrar por período de pagamento, contrato e imobiliária.
    """
    template_name = 'financeiro/relatorios/prestacoes_pagas.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .services import RelatorioService, FiltroRelatorio

        # Obter parâmetros de filtro
        contrato_id = self.request.GET.get('contrato')
        imobiliaria_id = self.request.GET.get('imobiliaria')
        data_inicio = self.request.GET.get('data_inicio')
        data_fim = self.request.GET.get('data_fim')

        # Criar filtro
        filtro = FiltroRelatorio()
        if contrato_id:
            filtro.contrato_id = int(contrato_id)
        if imobiliaria_id:
            filtro.imobiliaria_id = int(imobiliaria_id)
        if data_inicio:
            from datetime import datetime
            filtro.data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        if data_fim:
            from datetime import datetime
            filtro.data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()

        # Gerar relatório
        service = RelatorioService()
        relatorio = service.gerar_relatorio_prestacoes_pagas(filtro)

        context['relatorio'] = relatorio
        context['filtros'] = {
            'contrato_id': contrato_id,
            'imobiliaria_id': imobiliaria_id,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
        }

        # Listas para os filtros
        context['imobiliarias'] = Imobiliaria.objects.filter(ativo=True)
        context['contratos'] = Contrato.objects.all()

        return context


class RelatorioPosicaoContratosView(LoginRequiredMixin, TemplateView):
    """
    Relatório de posição de contratos.
    Mostra resumo de cada contrato com saldo devedor, progresso, etc.
    """
    template_name = 'financeiro/relatorios/posicao_contratos.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .services import RelatorioService, FiltroRelatorio

        # Obter parâmetros de filtro
        imobiliaria_id = self.request.GET.get('imobiliaria')
        status = self.request.GET.get('status')

        # Criar filtro
        filtro = FiltroRelatorio()
        if imobiliaria_id:
            filtro.imobiliaria_id = int(imobiliaria_id)

        # Gerar relatório
        service = RelatorioService()
        relatorio = service.gerar_relatorio_posicao_contratos(filtro)

        # Filtrar por status se necessário
        if status:
            relatorio['itens'] = [
                item for item in relatorio['itens']
                if item.get('status') == status
            ]

        context['relatorio'] = relatorio
        context['filtros'] = {
            'imobiliaria_id': imobiliaria_id,
            'status': status,
        }

        # Listas para os filtros
        context['imobiliarias'] = Imobiliaria.objects.filter(ativo=True)
        context['status_choices'] = StatusContrato.choices

        return context


class RelatorioPrevisaoReajustesView(LoginRequiredMixin, TemplateView):
    """
    Relatório de previsão de reajustes.
    Mostra contratos que precisarão de reajuste nos próximos dias.
    """
    template_name = 'financeiro/relatorios/previsao_reajustes.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .services import RelatorioService

        # Obter parâmetros
        dias_antecedencia = int(self.request.GET.get('dias', 60))
        imobiliaria_id = self.request.GET.get('imobiliaria')

        # Gerar relatório
        service = RelatorioService()
        relatorio = service.gerar_relatorio_previsao_reajustes(dias_antecedencia)

        # Filtrar por imobiliária se necessário
        if imobiliaria_id:
            relatorio['itens'] = [
                item for item in relatorio['itens']
                if str(item.get('imobiliaria_id')) == imobiliaria_id
            ]

        context['relatorio'] = relatorio
        context['filtros'] = {
            'dias': dias_antecedencia,
            'imobiliaria_id': imobiliaria_id,
        }

        # Listas para os filtros
        context['imobiliarias'] = Imobiliaria.objects.filter(ativo=True)

        return context


@login_required
def exportar_relatorio(request, tipo):
    """
    Exporta um relatório para CSV ou JSON.

    Tipos disponíveis:
    - prestacoes_a_pagar
    - prestacoes_pagas
    - posicao_contratos
    - previsao_reajustes

    Formatos: csv, json
    """
    from .services import RelatorioService, FiltroRelatorio

    formato = request.GET.get('formato', 'csv')

    # Criar filtro com base nos parâmetros
    filtro = FiltroRelatorio()
    contrato_id = request.GET.get('contrato')
    imobiliaria_id = request.GET.get('imobiliaria')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    if contrato_id:
        filtro.contrato_id = int(contrato_id)
    if imobiliaria_id:
        filtro.imobiliaria_id = int(imobiliaria_id)
    if data_inicio:
        from datetime import datetime
        filtro.data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
    if data_fim:
        from datetime import datetime
        filtro.data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()

    # Gerar relatório
    service = RelatorioService()

    if tipo == 'prestacoes_a_pagar':
        relatorio = service.gerar_relatorio_prestacoes_a_pagar(filtro)
    elif tipo == 'prestacoes_pagas':
        relatorio = service.gerar_relatorio_prestacoes_pagas(filtro)
    elif tipo == 'posicao_contratos':
        relatorio = service.gerar_relatorio_posicao_contratos(filtro)
    elif tipo == 'previsao_reajustes':
        dias = int(request.GET.get('dias', 60))
        relatorio = service.gerar_relatorio_previsao_reajustes(dias)
    else:
        return HttpResponse('Tipo de relatório inválido', status=400)

    # Exportar
    from django.utils import timezone
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')

    if formato == 'json':
        conteudo = service.exportar_para_json(relatorio)
        content_type = 'application/json'
        extensao = 'json'
    elif formato == 'excel' or formato == 'xlsx':
        try:
            conteudo = service.exportar_para_excel(relatorio)
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            extensao = 'xlsx'
        except ImportError as e:
            return HttpResponse(str(e), status=500)
    elif formato == 'pdf':
        try:
            conteudo = service.exportar_para_pdf(relatorio)
            content_type = 'application/pdf'
            extensao = 'pdf'
        except ImportError as e:
            return HttpResponse(str(e), status=500)
    else:
        conteudo = service.exportar_para_csv(relatorio)
        content_type = 'text/csv'
        extensao = 'csv'

    # Criar response
    filename = f'relatorio_{tipo}_{timestamp}.{extensao}'

    response = HttpResponse(conteudo, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response


@login_required
def api_relatorio_resumo(request):
    """
    API para retornar resumo de relatórios em JSON.
    Útil para widgets e dashboards.
    """
    from .services import RelatorioService, FiltroRelatorio

    hoje = timezone.now().date()

    # Filtro por imobiliária
    imobiliaria_id = request.GET.get('imobiliaria')
    filtro = FiltroRelatorio()
    if imobiliaria_id:
        filtro.imobiliaria_id = int(imobiliaria_id)

    service = RelatorioService()

    # Prestações a pagar (próximos 30 dias)
    filtro.data_inicio = hoje
    filtro.data_fim = hoje + timedelta(days=30)
    relatorio_a_pagar = service.gerar_relatorio_prestacoes_a_pagar(filtro)

    # Prestações pagas (últimos 30 dias)
    filtro.data_inicio = hoje - timedelta(days=30)
    filtro.data_fim = hoje
    relatorio_pagas = service.gerar_relatorio_prestacoes_pagas(filtro)

    # Previsão de reajustes
    relatorio_reajustes = service.gerar_relatorio_previsao_reajustes(60)

    return JsonResponse({
        'a_pagar': {
            'total_parcelas': relatorio_a_pagar['totalizador'].total_parcelas if hasattr(relatorio_a_pagar['totalizador'], 'total_parcelas') else 0,
            'valor_total': float(relatorio_a_pagar['totalizador'].valor_total) if hasattr(relatorio_a_pagar['totalizador'], 'valor_total') else 0,
        },
        'pagas': {
            'total_parcelas': relatorio_pagas['totalizador'].total_parcelas if hasattr(relatorio_pagas['totalizador'], 'total_parcelas') else 0,
            'valor_total': float(relatorio_pagas['totalizador'].valor_total) if hasattr(relatorio_pagas['totalizador'], 'valor_total') else 0,
        },
        'reajustes_pendentes': len(relatorio_reajustes.get('itens', [])),
    })


# =============================================================================
# APIs REST - IMOBILIÁRIAS
# =============================================================================

@login_required
@require_GET
def api_imobiliarias_lista(request):
    """
    API para listar imobiliárias da contabilidade.

    GET /api/contabilidade/imobiliarias/

    Parâmetros:
        - contabilidade: ID da contabilidade (opcional)
        - ativo: true/false (opcional)
    """
    from core.models import Contabilidade

    contabilidade_id = request.GET.get('contabilidade')
    ativo = request.GET.get('ativo', 'true').lower() == 'true'

    queryset = Imobiliaria.objects.all()

    if contabilidade_id:
        queryset = queryset.filter(contabilidade_id=contabilidade_id)

    if ativo is not None:
        queryset = queryset.filter(ativo=ativo)

    imobiliarias = []
    for imob in queryset.select_related('contabilidade'):
        # Estatísticas básicas
        contratos_ativos = Contrato.objects.filter(
            imobiliaria=imob, status=StatusContrato.ATIVO
        ).count()
        valor_a_receber = Parcela.objects.filter(
            contrato__imobiliaria=imob, pago=False
        ).aggregate(total=Sum('valor_atual'))['total'] or Decimal('0.00')

        imobiliarias.append({
            'id': imob.id,
            'razao_social': imob.razao_social,
            'nome_fantasia': imob.nome_fantasia,
            'cnpj': imob.cnpj,
            'email': imob.email,
            'telefone': imob.telefone,
            'ativo': imob.ativo,
            'contabilidade': {
                'id': imob.contabilidade.id,
                'nome': imob.contabilidade.razao_social,
            } if imob.contabilidade else None,
            'contratos_ativos': contratos_ativos,
            'valor_a_receber': float(valor_a_receber),
        })

    return JsonResponse({
        'sucesso': True,
        'imobiliarias': imobiliarias,
        'total': len(imobiliarias),
    })


@login_required
@require_GET
def api_imobiliaria_dashboard(request, imobiliaria_id):
    """
    API para dados do dashboard de uma imobiliária específica.

    GET /api/imobiliaria/{id}/dashboard/
    """
    imobiliaria = get_object_or_404(Imobiliaria, pk=imobiliaria_id)
    hoje = timezone.now().date()

    # Contratos
    contratos_qs = Contrato.objects.filter(imobiliaria=imobiliaria)
    parcelas_qs = Parcela.objects.filter(contrato__imobiliaria=imobiliaria)

    stats_contratos = contratos_qs.aggregate(
        total=Count('id'),
        ativos=Count('id', filter=Q(status=StatusContrato.ATIVO)),
        quitados=Count('id', filter=Q(status=StatusContrato.QUITADO)),
        cancelados=Count('id', filter=Q(status=StatusContrato.CANCELADO)),
        valor_total=Sum('valor_total'),
    )

    stats_parcelas = parcelas_qs.aggregate(
        total=Count('id'),
        pagas=Count('id', filter=Q(pago=True)),
        pendentes=Count('id', filter=Q(pago=False)),
        vencidas=Count('id', filter=Q(pago=False, data_vencimento__lt=hoje)),
        valor_recebido=Sum('valor_pago', filter=Q(pago=True)),
        valor_pendente=Sum('valor_atual', filter=Q(pago=False)),
        valor_vencido=Sum('valor_atual', filter=Q(pago=False, data_vencimento__lt=hoje)),
    )

    # Próximas parcelas a vencer
    proximas_parcelas = parcelas_qs.filter(
        pago=False,
        data_vencimento__gte=hoje
    ).order_by('data_vencimento')[:10]

    proximas = [{
        'id': p.id,
        'contrato': p.contrato.numero_contrato,
        'comprador': p.contrato.comprador.nome,
        'numero_parcela': p.numero_parcela,
        'data_vencimento': p.data_vencimento.strftime('%Y-%m-%d'),
        'valor': float(p.valor_atual),
        'status_boleto': p.status_boleto,
    } for p in proximas_parcelas]

    # Parcelas vencidas
    parcelas_vencidas = parcelas_qs.filter(
        pago=False,
        data_vencimento__lt=hoje
    ).order_by('-data_vencimento')[:10]

    vencidas = [{
        'id': p.id,
        'contrato': p.contrato.numero_contrato,
        'comprador': p.contrato.comprador.nome,
        'numero_parcela': p.numero_parcela,
        'data_vencimento': p.data_vencimento.strftime('%Y-%m-%d'),
        'dias_atraso': (hoje - p.data_vencimento).days,
        'valor': float(p.valor_atual),
    } for p in parcelas_vencidas]

    # Contratos com reajuste pendente
    contratos_reajuste = []
    for contrato in contratos_qs.filter(status=StatusContrato.ATIVO):
        if hasattr(contrato, 'verificar_reajuste_necessario'):
            if contrato.verificar_reajuste_necessario():
                contratos_reajuste.append({
                    'id': contrato.id,
                    'numero': contrato.numero_contrato,
                    'comprador': contrato.comprador.nome,
                    'tipo_correcao': contrato.tipo_correcao,
                    'data_proximo_reajuste': contrato.data_proximo_reajuste.strftime('%Y-%m-%d') if contrato.data_proximo_reajuste else None,
                })

    return JsonResponse({
        'sucesso': True,
        'imobiliaria': {
            'id': imobiliaria.id,
            'nome': imobiliaria.nome_fantasia or imobiliaria.razao_social,
        },
        'contratos': stats_contratos,
        'parcelas': stats_parcelas,
        'proximas_parcelas': proximas,
        'parcelas_vencidas': vencidas,
        'reajustes_pendentes': contratos_reajuste,
    })


# =============================================================================
# APIs REST - CONTRATOS
# =============================================================================

@login_required
@require_GET
def api_contratos_lista(request):
    """
    API para listar contratos com filtros.

    GET /api/contratos/

    Parâmetros:
        - imobiliaria: ID da imobiliária (opcional)
        - status: Status do contrato (opcional)
        - comprador: ID do comprador (opcional)
        - page: Página (default 1)
        - per_page: Itens por página (default 20)
    """
    imobiliaria_id = request.GET.get('imobiliaria')
    status = request.GET.get('status')
    comprador_id = request.GET.get('comprador')
    page = int(request.GET.get('page', 1))
    per_page = min(int(request.GET.get('per_page', 20)), 100)

    queryset = Contrato.objects.all().select_related(
        'imobiliaria', 'comprador', 'imovel'
    )

    if imobiliaria_id:
        queryset = queryset.filter(imobiliaria_id=imobiliaria_id)
    if status:
        queryset = queryset.filter(status=status)
    if comprador_id:
        queryset = queryset.filter(comprador_id=comprador_id)

    total = queryset.count()
    offset = (page - 1) * per_page
    contratos_page = queryset.order_by('-data_contrato')[offset:offset + per_page]

    contratos = []
    for c in contratos_page:
        saldo_devedor = c.calcular_saldo_devedor()
        progresso = c.calcular_progresso()

        contratos.append({
            'id': c.id,
            'numero_contrato': c.numero_contrato,
            'data_contrato': c.data_contrato.strftime('%Y-%m-%d'),
            'status': c.status,
            'imobiliaria': {
                'id': c.imobiliaria.id,
                'nome': c.imobiliaria.nome_fantasia or c.imobiliaria.razao_social,
            },
            'comprador': {
                'id': c.comprador.id,
                'nome': c.comprador.nome,
                'documento': c.comprador.cpf or c.comprador.cnpj,
            },
            'imovel': {
                'id': c.imovel.id,
                'identificacao': c.imovel.identificacao,
            },
            'valor_total': float(c.valor_total),
            'valor_entrada': float(c.valor_entrada),
            'numero_parcelas': c.numero_parcelas,
            'saldo_devedor': float(saldo_devedor),
            'progresso': round(progresso, 2),
            'tipo_correcao': c.tipo_correcao,
        })

    return JsonResponse({
        'sucesso': True,
        'contratos': contratos,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page,
    })


@login_required
@require_GET
def api_contrato_detalhe(request, contrato_id):
    """
    API para detalhes de um contrato específico.

    GET /api/contratos/{id}/
    """
    contrato = get_object_or_404(
        Contrato.objects.select_related('imobiliaria', 'comprador', 'imovel'),
        pk=contrato_id
    )

    resumo = contrato.get_resumo_financeiro()

    return JsonResponse({
        'sucesso': True,
        'contrato': {
            'id': contrato.id,
            'numero_contrato': contrato.numero_contrato,
            'data_contrato': contrato.data_contrato.strftime('%Y-%m-%d'),
            'data_primeiro_vencimento': contrato.data_primeiro_vencimento.strftime('%Y-%m-%d'),
            'status': contrato.status,
            'imobiliaria': {
                'id': contrato.imobiliaria.id,
                'nome': contrato.imobiliaria.nome_fantasia or contrato.imobiliaria.razao_social,
                'cnpj': contrato.imobiliaria.cnpj,
            },
            'comprador': {
                'id': contrato.comprador.id,
                'nome': contrato.comprador.nome,
                'documento': contrato.comprador.cpf or contrato.comprador.cnpj,
                'email': contrato.comprador.email,
                'telefone': contrato.comprador.telefone,
            },
            'imovel': {
                'id': contrato.imovel.id,
                'identificacao': contrato.imovel.identificacao,
                'endereco': contrato.imovel.endereco,
            },
            'valores': {
                'total': float(contrato.valor_total),
                'entrada': float(contrato.valor_entrada),
                'financiado': float(contrato.valor_financiado),
                'parcela_original': float(contrato.valor_parcela_original),
            },
            'parcelas': {
                'numero_total': contrato.numero_parcelas,
                'dia_vencimento': contrato.dia_vencimento,
            },
            'reajuste': {
                'tipo_correcao': contrato.tipo_correcao,
                'prazo_meses': contrato.prazo_reajuste_meses,
                'data_ultimo': contrato.data_ultimo_reajuste.strftime('%Y-%m-%d') if contrato.data_ultimo_reajuste else None,
                'data_proximo': contrato.data_proximo_reajuste.strftime('%Y-%m-%d') if contrato.data_proximo_reajuste else None,
                'ciclo_atual': contrato.ciclo_reajuste_atual,
                'bloqueio_ativo': contrato.bloqueio_boleto_reajuste,
            },
            'encargos': {
                'juros_mora': float(contrato.percentual_juros_mora),
                'multa': float(contrato.percentual_multa),
            },
            'resumo_financeiro': {
                'valor_pago': float(resumo.get('total_pago', 0)),
                'valor_a_pagar': float(resumo.get('total_a_pagar', 0)),
                'valor_vencido': float(resumo.get('total_vencido', 0)),
                'parcelas_pagas': resumo.get('parcelas_pagas', 0),
                'parcelas_a_pagar': resumo.get('parcelas_a_pagar', 0),
                'parcelas_vencidas': resumo.get('parcelas_vencidas', 0),
                'saldo_devedor': float(resumo.get('saldo_devedor', 0)),
                'progresso': round(resumo.get('progresso_percentual', 0), 2),
            },
        },
    })


@login_required
@require_GET
def api_contrato_parcelas(request, contrato_id):
    """
    API para listar parcelas de um contrato.

    GET /api/contratos/{id}/parcelas/

    Parâmetros:
        - status: pago, pendente, vencido (opcional)
        - page: Página (default 1)
        - per_page: Itens por página (default 50)
    """
    contrato = get_object_or_404(Contrato, pk=contrato_id)

    status_filter = request.GET.get('status')
    page = int(request.GET.get('page', 1))
    per_page = min(int(request.GET.get('per_page', 50)), 100)
    hoje = timezone.now().date()

    queryset = contrato.parcelas.all()

    if status_filter == 'pago':
        queryset = queryset.filter(pago=True)
    elif status_filter == 'pendente':
        queryset = queryset.filter(pago=False, data_vencimento__gte=hoje)
    elif status_filter == 'vencido':
        queryset = queryset.filter(pago=False, data_vencimento__lt=hoje)

    total = queryset.count()
    offset = (page - 1) * per_page
    parcelas_page = queryset.order_by('numero_parcela')[offset:offset + per_page]

    parcelas = []
    for p in parcelas_page:
        parcelas.append({
            'id': p.id,
            'numero_parcela': p.numero_parcela,
            'tipo': p.tipo_parcela,
            'ciclo_reajuste': p.ciclo_reajuste,
            'data_vencimento': p.data_vencimento.strftime('%Y-%m-%d'),
            'valor_original': float(p.valor_original),
            'valor_atual': float(p.valor_atual),
            'valor_juros': float(p.valor_juros),
            'valor_multa': float(p.valor_multa),
            'valor_desconto': float(p.valor_desconto),
            'valor_total': float(p.valor_total),
            'pago': p.pago,
            'data_pagamento': p.data_pagamento.strftime('%Y-%m-%d') if p.data_pagamento else None,
            'valor_pago': float(p.valor_pago) if p.valor_pago else None,
            'dias_atraso': p.dias_atraso,
            'vencida': p.esta_vencida,
            'boleto': {
                'status': p.status_boleto,
                'nosso_numero': p.nosso_numero,
                'tem_boleto': p.tem_boleto,
            },
        })

    return JsonResponse({
        'sucesso': True,
        'contrato_id': contrato.id,
        'parcelas': parcelas,
        'total': total,
        'page': page,
        'per_page': per_page,
    })


@login_required
@require_GET
def api_contrato_reajustes(request, contrato_id):
    """
    API para listar histórico de reajustes de um contrato.

    GET /api/contratos/{id}/reajustes/
    """
    contrato = get_object_or_404(Contrato, pk=contrato_id)

    reajustes = Reajuste.objects.filter(contrato=contrato).order_by('-data_reajuste')

    lista_reajustes = [{
        'id': r.id,
        'data_reajuste': r.data_reajuste.strftime('%Y-%m-%d'),
        'indice_tipo': r.indice_tipo,
        'percentual': float(r.percentual),
        'ciclo': r.ciclo,
        'parcela_inicial': r.parcela_inicial,
        'parcela_final': r.parcela_final,
        'aplicado': r.aplicado,
        'data_aplicacao': r.data_aplicacao.strftime('%Y-%m-%d %H:%M') if r.data_aplicacao else None,
        'aplicado_manual': r.aplicado_manual,
        'observacoes': r.observacoes,
    } for r in reajustes]

    # Informações de reajuste pendente
    reajuste_pendente = None
    if contrato.verificar_reajuste_necessario():
        reajuste_pendente = {
            'tipo_correcao': contrato.tipo_correcao,
            'ciclo_atual': contrato.ciclo_reajuste_atual,
            'data_proximo': contrato.data_proximo_reajuste.strftime('%Y-%m-%d') if contrato.data_proximo_reajuste else None,
            'bloqueio_ativo': contrato.bloqueio_boleto_reajuste,
        }

    return JsonResponse({
        'sucesso': True,
        'contrato_id': contrato.id,
        'reajustes': lista_reajustes,
        'total': len(lista_reajustes),
        'reajuste_pendente': reajuste_pendente,
    })


# =============================================================================
# APIs REST - PARCELAS
# =============================================================================

@login_required
@require_GET
def api_parcelas_lista(request):
    """
    API para listar parcelas com filtros avançados.

    GET /api/parcelas/

    Parâmetros:
        - imobiliaria: ID da imobiliária (opcional)
        - contrato: ID do contrato (opcional)
        - status: pago, pendente, vencido (opcional)
        - data_inicio: Data inicial de vencimento (YYYY-MM-DD)
        - data_fim: Data final de vencimento (YYYY-MM-DD)
        - page: Página (default 1)
        - per_page: Itens por página (default 50)
    """
    imobiliaria_id = request.GET.get('imobiliaria')
    contrato_id = request.GET.get('contrato')
    status_filter = request.GET.get('status')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    page = int(request.GET.get('page', 1))
    per_page = min(int(request.GET.get('per_page', 50)), 100)

    hoje = timezone.now().date()
    queryset = Parcela.objects.all().select_related(
        'contrato', 'contrato__comprador', 'contrato__imobiliaria'
    )

    if imobiliaria_id:
        queryset = queryset.filter(contrato__imobiliaria_id=imobiliaria_id)
    if contrato_id:
        queryset = queryset.filter(contrato_id=contrato_id)

    if status_filter == 'pago':
        queryset = queryset.filter(pago=True)
    elif status_filter == 'pendente':
        queryset = queryset.filter(pago=False, data_vencimento__gte=hoje)
    elif status_filter == 'vencido':
        queryset = queryset.filter(pago=False, data_vencimento__lt=hoje)

    if data_inicio:
        from datetime import datetime
        queryset = queryset.filter(
            data_vencimento__gte=datetime.strptime(data_inicio, '%Y-%m-%d').date()
        )
    if data_fim:
        from datetime import datetime
        queryset = queryset.filter(
            data_vencimento__lte=datetime.strptime(data_fim, '%Y-%m-%d').date()
        )

    total = queryset.count()
    offset = (page - 1) * per_page
    parcelas_page = queryset.order_by('data_vencimento')[offset:offset + per_page]

    # Totalizadores
    totais = queryset.aggregate(
        valor_total=Sum('valor_atual'),
        valor_pago=Sum('valor_pago', filter=Q(pago=True)),
    )

    parcelas = [{
        'id': p.id,
        'contrato': {
            'id': p.contrato.id,
            'numero': p.contrato.numero_contrato,
        },
        'comprador': p.contrato.comprador.nome,
        'imobiliaria': p.contrato.imobiliaria.nome_fantasia or p.contrato.imobiliaria.razao_social,
        'numero_parcela': p.numero_parcela,
        'data_vencimento': p.data_vencimento.strftime('%Y-%m-%d'),
        'valor_atual': float(p.valor_atual),
        'valor_total': float(p.valor_total),
        'pago': p.pago,
        'data_pagamento': p.data_pagamento.strftime('%Y-%m-%d') if p.data_pagamento else None,
        'dias_atraso': p.dias_atraso,
        'status_boleto': p.status_boleto,
    } for p in parcelas_page]

    return JsonResponse({
        'sucesso': True,
        'parcelas': parcelas,
        'total': total,
        'page': page,
        'per_page': per_page,
        'totais': {
            'valor_total': float(totais['valor_total'] or 0),
            'valor_pago': float(totais['valor_pago'] or 0),
        },
    })


@login_required
@require_POST
def api_parcela_registrar_pagamento(request, parcela_id):
    """
    API para registrar pagamento de uma parcela.

    POST /api/parcelas/{id}/pagamento/

    Body JSON:
        - valor_pago: Valor pago (obrigatório)
        - data_pagamento: Data do pagamento (opcional, default hoje)
        - forma_pagamento: Forma de pagamento (opcional)
        - observacoes: Observações (opcional)
    """
    import json
    parcela = get_object_or_404(Parcela, pk=parcela_id)

    if parcela.pago:
        return JsonResponse({
            'sucesso': False,
            'erro': 'Esta parcela já está paga.'
        }, status=400)

    try:
        data = json.loads(request.body)

        valor_pago = Decimal(str(data.get('valor_pago', 0)))
        if valor_pago <= 0:
            return JsonResponse({
                'sucesso': False,
                'erro': 'Informe um valor pago válido.'
            }, status=400)

        data_pagamento = data.get('data_pagamento')
        if data_pagamento:
            from datetime import datetime
            data_pagamento = datetime.strptime(data_pagamento, '%Y-%m-%d').date()
        else:
            data_pagamento = timezone.now().date()

        observacoes = data.get('observacoes', '')
        forma_pagamento = data.get('forma_pagamento', 'DINHEIRO')

        # Registrar pagamento
        parcela.registrar_pagamento(
            valor_pago=valor_pago,
            data_pagamento=data_pagamento,
            observacoes=observacoes
        )

        # Criar histórico
        from financeiro.models import HistoricoPagamento
        HistoricoPagamento.objects.create(
            parcela=parcela,
            data_pagamento=data_pagamento,
            valor_pago=valor_pago,
            valor_parcela=parcela.valor_atual,
            valor_juros=parcela.valor_juros,
            valor_multa=parcela.valor_multa,
            valor_desconto=parcela.valor_desconto,
            forma_pagamento=forma_pagamento,
            observacoes=observacoes
        )

        return JsonResponse({
            'sucesso': True,
            'mensagem': f'Pagamento de R$ {valor_pago} registrado com sucesso.',
            'parcela': {
                'id': parcela.id,
                'numero_parcela': parcela.numero_parcela,
                'pago': parcela.pago,
                'data_pagamento': parcela.data_pagamento.strftime('%Y-%m-%d'),
                'valor_pago': float(parcela.valor_pago),
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'sucesso': False,
            'erro': 'Dados inválidos.'
        }, status=400)
    except Exception as e:
        logger.exception(f"Erro ao registrar pagamento: {e}")
        return JsonResponse({
            'sucesso': False,
            'erro': str(e)
        }, status=500)


# =============================================================================
# APIs REST - BOLETO E CNAB
# =============================================================================

@login_required
def api_boleto_gerar(request, parcela_id):
    """
    API para gerar boleto de uma parcela.

    POST /api/boletos/{parcela_id}/gerar/

    Body JSON (opcional):
        - conta_bancaria_id: ID da conta bancária (usa padrão se não informado)
        - force: Força regeneração mesmo se já existe (default: false)
        - enviar_email: Envia email ao comprador (default: true)

    Returns:
        - sucesso: boolean
        - boleto: dados do boleto gerado
        - erro: mensagem de erro (se houver)
    """
    import json

    parcela = get_object_or_404(Parcela, pk=parcela_id)

    if request.method != 'POST':
        return JsonResponse({
            'sucesso': False,
            'erro': 'Método não permitido. Use POST.'
        }, status=405)

    try:
        data = json.loads(request.body) if request.body else {}

        conta_bancaria_id = data.get('conta_bancaria_id')
        force = data.get('force', False)
        enviar_email = data.get('enviar_email', True)

        if parcela.pago:
            return JsonResponse({
                'sucesso': False,
                'erro': 'Parcela já está paga.'
            }, status=400)

        pode_gerar, motivo = parcela.pode_gerar_boleto()
        if not pode_gerar and not force:
            return JsonResponse({
                'sucesso': False,
                'erro': motivo,
                'bloqueado_reajuste': True
            }, status=400)

        if parcela.tem_boleto and not force:
            return JsonResponse({
                'sucesso': True,
                'mensagem': 'Boleto já existe.',
                'boleto': {
                    'parcela_id': parcela.id,
                    'nosso_numero': parcela.nosso_numero,
                    'linha_digitavel': parcela.linha_digitavel,
                    'codigo_barras': parcela.codigo_barras,
                    'valor': float(parcela.valor_boleto or parcela.valor_atual),
                    'data_vencimento': parcela.data_vencimento.strftime('%Y-%m-%d'),
                    'status': parcela.status_boleto,
                    'tem_pdf': bool(parcela.boleto_pdf),
                }
            })

        conta_bancaria = None
        if conta_bancaria_id:
            conta_bancaria = get_object_or_404(ContaBancaria, pk=conta_bancaria_id, ativo=True)

        resultado = parcela.gerar_boleto(
            conta_bancaria=conta_bancaria,
            force=force,
            enviar_email=enviar_email
        )

        if resultado and resultado.get('sucesso'):
            parcela.refresh_from_db()
            return JsonResponse({
                'sucesso': True,
                'mensagem': 'Boleto gerado com sucesso.',
                'boleto': {
                    'parcela_id': parcela.id,
                    'nosso_numero': parcela.nosso_numero,
                    'linha_digitavel': parcela.linha_digitavel,
                    'codigo_barras': parcela.codigo_barras,
                    'valor': float(parcela.valor_boleto or parcela.valor_atual),
                    'data_vencimento': parcela.data_vencimento.strftime('%Y-%m-%d'),
                    'status': parcela.status_boleto,
                    'tem_pdf': bool(parcela.boleto_pdf),
                    'pix_copia_cola': parcela.pix_copia_cola or None,
                }
            })
        else:
            return JsonResponse({
                'sucesso': False,
                'erro': resultado.get('erro') if resultado else 'Erro ao gerar boleto.'
            }, status=500)

    except json.JSONDecodeError:
        return JsonResponse({'sucesso': False, 'erro': 'JSON inválido.'}, status=400)
    except Exception as e:
        logger.exception(f"Erro ao gerar boleto via API: {e}")
        return JsonResponse({'sucesso': False, 'erro': str(e)}, status=500)


@login_required
def api_boleto_detalhe(request, parcela_id):
    """
    API para obter detalhes do boleto de uma parcela.
    GET /api/boletos/{parcela_id}/
    """
    parcela = get_object_or_404(Parcela, pk=parcela_id)

    if not parcela.tem_boleto:
        return JsonResponse({
            'sucesso': False,
            'erro': 'Esta parcela não possui boleto gerado.'
        }, status=404)

    return JsonResponse({
        'sucesso': True,
        'boleto': {
            'parcela_id': parcela.id,
            'contrato_id': parcela.contrato_id,
            'numero_parcela': parcela.numero_parcela,
            'nosso_numero': parcela.nosso_numero,
            'numero_documento': parcela.numero_documento,
            'linha_digitavel': parcela.linha_digitavel,
            'codigo_barras': parcela.codigo_barras,
            'valor': float(parcela.valor_boleto or parcela.valor_atual),
            'valor_original': float(parcela.valor_original),
            'data_vencimento': parcela.data_vencimento.strftime('%Y-%m-%d'),
            'status': parcela.status_boleto,
            'status_display': parcela.get_status_boleto_display(),
            'pago': parcela.pago,
            'data_pagamento': parcela.data_pagamento.strftime('%Y-%m-%d') if parcela.data_pagamento else None,
            'valor_pago': float(parcela.valor_pago) if parcela.valor_pago else None,
            'data_geracao': parcela.data_geracao_boleto.isoformat() if parcela.data_geracao_boleto else None,
            'tem_pdf': bool(parcela.boleto_pdf),
            'boleto_url': parcela.boleto_url or None,
            'pix_copia_cola': parcela.pix_copia_cola or None,
            'comprador': {
                'nome': parcela.contrato.comprador.nome,
                'documento': parcela.contrato.comprador.cpf or parcela.contrato.comprador.cnpj,
            }
        }
    })


@login_required
@require_POST
def api_boleto_cancelar(request, parcela_id):
    """
    API para cancelar boleto de uma parcela.
    POST /api/boletos/{parcela_id}/cancelar/
    Body: {"motivo": "texto"}
    """
    import json
    parcela = get_object_or_404(Parcela, pk=parcela_id)

    if not parcela.tem_boleto:
        return JsonResponse({'sucesso': False, 'erro': 'Sem boleto para cancelar.'}, status=400)
    if parcela.pago:
        return JsonResponse({'sucesso': False, 'erro': 'Parcela já paga.'}, status=400)

    try:
        data = json.loads(request.body) if request.body else {}
        motivo = data.get('motivo', '')
        if not motivo:
            return JsonResponse({'sucesso': False, 'erro': 'Informe o motivo.'}, status=400)

        parcela.cancelar_boleto(motivo=motivo)
        return JsonResponse({'sucesso': True, 'mensagem': 'Boleto cancelado.'})

    except json.JSONDecodeError:
        return JsonResponse({'sucesso': False, 'erro': 'JSON inválido.'}, status=400)
    except Exception as e:
        logger.exception(f"Erro ao cancelar boleto: {e}")
        return JsonResponse({'sucesso': False, 'erro': str(e)}, status=500)


@login_required
def api_boletos_lote(request):
    """
    API para gerar boletos em lote.
    POST /api/boletos/lote/
    Body: {"parcela_ids": [1,2,3], "conta_bancaria_id": 1, "force": false}
    """
    import json

    if request.method != 'POST':
        return JsonResponse({'sucesso': False, 'erro': 'Use POST.'}, status=405)

    try:
        data = json.loads(request.body)
        parcela_ids = data.get('parcela_ids', [])
        conta_bancaria_id = data.get('conta_bancaria_id')
        force = data.get('force', False)
        enviar_email = data.get('enviar_email', False)

        if not parcela_ids:
            return JsonResponse({'sucesso': False, 'erro': 'Informe parcelas.'}, status=400)

        parcelas = Parcela.objects.filter(pk__in=parcela_ids, pago=False)
        if not parcelas.exists():
            return JsonResponse({'sucesso': False, 'erro': 'Nenhuma parcela válida.'}, status=400)

        conta_bancaria = None
        if conta_bancaria_id:
            conta_bancaria = get_object_or_404(ContaBancaria, pk=conta_bancaria_id, ativo=True)

        resultados = []
        gerados = erros = bloqueados = 0

        for parcela in parcelas:
            pode, motivo = parcela.pode_gerar_boleto()
            if not pode and not force:
                resultados.append({'parcela_id': parcela.id, 'sucesso': False, 'bloqueado': True, 'erro': motivo})
                bloqueados += 1
                continue

            if parcela.tem_boleto and not force:
                resultados.append({'parcela_id': parcela.id, 'sucesso': True, 'ja_existe': True})
                continue

            try:
                res = parcela.gerar_boleto(conta_bancaria=conta_bancaria, force=force, enviar_email=enviar_email)
                if res and res.get('sucesso'):
                    gerados += 1
                    resultados.append({'parcela_id': parcela.id, 'sucesso': True, 'nosso_numero': res.get('nosso_numero')})
                else:
                    erros += 1
                    resultados.append({'parcela_id': parcela.id, 'sucesso': False, 'erro': res.get('erro') if res else 'Erro'})
            except Exception as e:
                erros += 1
                resultados.append({'parcela_id': parcela.id, 'sucesso': False, 'erro': str(e)})

        return JsonResponse({'sucesso': True, 'gerados': gerados, 'erros': erros, 'bloqueados': bloqueados, 'resultados': resultados})

    except json.JSONDecodeError:
        return JsonResponse({'sucesso': False, 'erro': 'JSON inválido.'}, status=400)
    except Exception as e:
        logger.exception(f"Erro em lote: {e}")
        return JsonResponse({'sucesso': False, 'erro': str(e)}, status=500)


# =============================================================================
# APIs REST - CNAB REMESSA
# =============================================================================

@login_required
def api_cnab_remessa_listar(request):
    """API para listar remessas CNAB. GET /api/cnab/remessas/"""
    from .models import ArquivoRemessa

    qs = ArquivoRemessa.objects.select_related('conta_bancaria', 'conta_bancaria__imobiliaria').order_by('-data_geracao')

    if request.GET.get('conta_bancaria_id'):
        qs = qs.filter(conta_bancaria_id=request.GET['conta_bancaria_id'])
    if request.GET.get('status'):
        qs = qs.filter(status=request.GET['status'])

    page = int(request.GET.get('page', 1))
    per_page = min(int(request.GET.get('per_page', 20)), 100)
    total = qs.count()
    arquivos = qs[(page-1)*per_page:page*per_page]

    remessas = [{
        'id': a.id, 'numero_remessa': a.numero_remessa, 'layout': a.layout,
        'nome_arquivo': a.nome_arquivo, 'status': a.status,
        'data_geracao': a.data_geracao.isoformat() if a.data_geracao else None,
        'quantidade_boletos': a.quantidade_boletos, 'valor_total': float(a.valor_total),
        'conta_bancaria': {'id': a.conta_bancaria.id, 'banco': a.conta_bancaria.banco},
    } for a in arquivos]

    return JsonResponse({'sucesso': True, 'remessas': remessas, 'total': total, 'page': page})


@login_required
def api_cnab_remessa_detalhe(request, remessa_id):
    """API para detalhes de remessa. GET /api/cnab/remessas/{id}/"""
    from .models import ArquivoRemessa

    arq = get_object_or_404(ArquivoRemessa.objects.select_related('conta_bancaria').prefetch_related('itens', 'itens__parcela'), pk=remessa_id)

    itens = [{'id': i.id, 'parcela_id': i.parcela_id, 'nosso_numero': i.nosso_numero,
              'valor': float(i.valor), 'data_vencimento': i.data_vencimento.strftime('%Y-%m-%d')} for i in arq.itens.all()]

    return JsonResponse({
        'sucesso': True,
        'remessa': {
            'id': arq.id, 'numero_remessa': arq.numero_remessa, 'layout': arq.layout,
            'nome_arquivo': arq.nome_arquivo, 'status': arq.status,
            'quantidade_boletos': arq.quantidade_boletos, 'valor_total': float(arq.valor_total),
            'pode_reenviar': arq.pode_reenviar,
        },
        'itens': itens
    })


@login_required
@require_POST
def api_cnab_remessa_gerar(request):
    """
    API para gerar remessa CNAB.
    POST /api/cnab/remessas/gerar/
    Body: {"conta_bancaria_id": 1, "parcela_ids": [1,2,3], "layout": "CNAB_240"}
    """
    import json
    from .models import StatusBoleto
    from .services.cnab_service import CNABService

    try:
        data = json.loads(request.body)
        conta_id = data.get('conta_bancaria_id')
        parcela_ids = data.get('parcela_ids', [])
        layout = data.get('layout', 'CNAB_240')

        if not conta_id:
            return JsonResponse({'sucesso': False, 'erro': 'Informe conta bancária.'}, status=400)
        if not parcela_ids:
            return JsonResponse({'sucesso': False, 'erro': 'Informe parcelas.'}, status=400)

        conta = get_object_or_404(ContaBancaria, pk=conta_id, ativo=True)
        parcelas = Parcela.objects.filter(pk__in=parcela_ids, status_boleto=StatusBoleto.GERADO, pago=False)

        if not parcelas.exists():
            return JsonResponse({'sucesso': False, 'erro': 'Nenhuma parcela válida.'}, status=400)

        service = CNABService()
        resultado = service.gerar_remessa(list(parcelas), conta, layout)

        if resultado.get('sucesso'):
            arq = resultado['arquivo_remessa']
            return JsonResponse({
                'sucesso': True,
                'remessa': {'id': arq.id, 'numero_remessa': arq.numero_remessa, 'nome_arquivo': arq.nome_arquivo,
                           'quantidade_boletos': resultado.get('quantidade_boletos'), 'valor_total': float(resultado.get('valor_total', 0))}
            })
        return JsonResponse({'sucesso': False, 'erro': resultado.get('erro')}, status=500)

    except json.JSONDecodeError:
        return JsonResponse({'sucesso': False, 'erro': 'JSON inválido.'}, status=400)
    except Exception as e:
        logger.exception(f"Erro ao gerar remessa: {e}")
        return JsonResponse({'sucesso': False, 'erro': str(e)}, status=500)


@login_required
def api_cnab_boletos_disponiveis(request):
    """API para listar boletos disponíveis para remessa. GET /api/cnab/boletos-disponiveis/?conta_bancaria_id=1"""
    from .services.cnab_service import CNABService

    conta_id = request.GET.get('conta_bancaria_id')
    if not conta_id:
        return JsonResponse({'sucesso': False, 'erro': 'Informe conta bancária.'}, status=400)

    conta = get_object_or_404(ContaBancaria, pk=conta_id, ativo=True)
    service = CNABService()
    boletos = service.obter_boletos_sem_remessa(conta)

    data = [{'parcela_id': p.id, 'numero_contrato': p.contrato.numero_contrato, 'numero_parcela': p.numero_parcela,
             'nosso_numero': p.nosso_numero, 'valor': float(p.valor_boleto or p.valor_atual),
             'data_vencimento': p.data_vencimento.strftime('%Y-%m-%d'), 'comprador': p.contrato.comprador.nome} for p in boletos]

    return JsonResponse({'sucesso': True, 'boletos': data, 'total': len(data)})


# =============================================================================
# APIs REST - CNAB RETORNO
# =============================================================================

@login_required
def api_cnab_retorno_listar(request):
    """API para listar retornos CNAB. GET /api/cnab/retornos/"""
    from .models import ArquivoRetorno

    qs = ArquivoRetorno.objects.select_related('conta_bancaria').order_by('-data_upload')

    if request.GET.get('conta_bancaria_id'):
        qs = qs.filter(conta_bancaria_id=request.GET['conta_bancaria_id'])
    if request.GET.get('status'):
        qs = qs.filter(status=request.GET['status'])

    page = int(request.GET.get('page', 1))
    per_page = min(int(request.GET.get('per_page', 20)), 100)
    total = qs.count()
    arquivos = qs[(page-1)*per_page:page*per_page]

    retornos = [{
        'id': a.id, 'nome_arquivo': a.nome_arquivo, 'layout': a.layout, 'status': a.status,
        'data_upload': a.data_upload.isoformat() if a.data_upload else None,
        'total_registros': a.total_registros, 'registros_processados': a.registros_processados,
        'valor_total_pago': float(a.valor_total_pago),
    } for a in arquivos]

    return JsonResponse({'sucesso': True, 'retornos': retornos, 'total': total, 'page': page})


@login_required
def api_cnab_retorno_detalhe(request, retorno_id):
    """API para detalhes de retorno. GET /api/cnab/retornos/{id}/"""
    from .models import ArquivoRetorno

    arq = get_object_or_404(ArquivoRetorno.objects.select_related('conta_bancaria').prefetch_related('itens'), pk=retorno_id)

    itens = [{'id': i.id, 'nosso_numero': i.nosso_numero, 'codigo_ocorrencia': i.codigo_ocorrencia,
              'tipo_ocorrencia': i.tipo_ocorrencia, 'valor_pago': float(i.valor_pago) if i.valor_pago else None,
              'data_credito': i.data_credito.strftime('%Y-%m-%d') if i.data_credito else None, 'processado': i.processado} for i in arq.itens.all()]

    return JsonResponse({
        'sucesso': True,
        'retorno': {
            'id': arq.id, 'nome_arquivo': arq.nome_arquivo, 'layout': arq.layout, 'status': arq.status,
            'total_registros': arq.total_registros, 'registros_processados': arq.registros_processados,
            'registros_erro': arq.registros_erro, 'valor_total_pago': float(arq.valor_total_pago),
        },
        'itens': itens
    })


@login_required
@require_POST
def api_cnab_retorno_processar(request, retorno_id):
    """API para processar retorno CNAB. POST /api/cnab/retornos/{id}/processar/"""
    from .models import ArquivoRetorno, StatusArquivoRetorno
    from .services.cnab_service import CNABService

    arquivo = get_object_or_404(ArquivoRetorno, pk=retorno_id)

    if arquivo.status == StatusArquivoRetorno.PROCESSADO:
        return JsonResponse({'sucesso': False, 'erro': 'Já processado.'}, status=400)

    try:
        service = CNABService()
        resultado = service.processar_retorno(arquivo)

        if resultado.get('sucesso'):
            return JsonResponse({
                'sucesso': True, 'total_registros': resultado.get('total_registros', 0),
                'processados': resultado.get('processados', 0), 'liquidacoes': resultado.get('liquidacoes', 0),
            })
        return JsonResponse({'sucesso': False, 'erro': resultado.get('erro')}, status=500)

    except Exception as e:
        logger.exception(f"Erro ao processar retorno: {e}")
        return JsonResponse({'sucesso': False, 'erro': str(e)}, status=500)


@login_required
def api_contas_bancarias(request):
    """API para listar contas bancárias. GET /api/contas-bancarias/"""
    qs = ContaBancaria.objects.filter(ativo=True).select_related('imobiliaria')

    if request.GET.get('imobiliaria_id'):
        qs = qs.filter(imobiliaria_id=request.GET['imobiliaria_id'])

    contas = [{
        'id': c.id, 'banco': c.banco, 'descricao': c.descricao, 'agencia': c.agencia, 'conta': c.conta,
        'convenio': c.convenio, 'carteira': c.carteira, 'layout_cnab': c.layout_cnab, 'principal': c.principal,
        'imobiliaria': {'id': c.imobiliaria.id, 'nome': c.imobiliaria.nome}
    } for c in qs]

    return JsonResponse({'sucesso': True, 'contas': contas})
