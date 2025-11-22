"""
Views do app Financeiro

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum, Count, Q, F
from django.views.generic import TemplateView
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from .models import Parcela, Reajuste
from core.models import Imobiliaria
from contratos.models import Contrato, StatusContrato


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

    # Filtro por Número do Contrato
    contrato_numero = request.GET.get('contrato', '').strip()
    if contrato_numero:
        parcelas = parcelas.filter(contrato__numero__icontains=contrato_numero)

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
            Q(contrato__numero__icontains=busca)
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
        'filtro_contrato': contrato_numero,
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
    parcela = get_object_or_404(Parcela, pk=pk)

    if request.method == 'POST':
        valor_pago = request.POST.get('valor_pago')
        data_pagamento = request.POST.get('data_pagamento', timezone.now().date())
        observacoes = request.POST.get('observacoes', '')

        try:
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
    }
    return render(request, 'financeiro/dashboard_imobiliaria.html', context)
