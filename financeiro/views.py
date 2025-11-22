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


# =============================================================================
# VIEWS DE BOLETO BANCÁRIO
# =============================================================================

@login_required
@require_POST
def gerar_boleto_parcela(request, pk):
    """
    Gera boleto para uma parcela específica.
    """
    parcela = get_object_or_404(Parcela, pk=pk)

    if parcela.pago:
        return JsonResponse({
            'sucesso': False,
            'erro': 'Parcela já está paga'
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
        force = request.POST.get('force', 'false').lower() == 'true'
        resultado = parcela.gerar_boleto(conta_bancaria, force=force)

        if resultado and resultado.get('sucesso'):
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
    """
    contrato = get_object_or_404(Contrato, pk=contrato_id)

    # Obter conta bancária
    conta_id = request.POST.get('conta_bancaria_id')
    conta_bancaria = None

    if conta_id:
        conta_bancaria = get_object_or_404(ContaBancaria, pk=conta_id, ativo=True)

    try:
        resultados = contrato.gerar_boletos_parcelas(conta_bancaria=conta_bancaria)

        if isinstance(resultados, dict) and resultados.get('erro'):
            return JsonResponse({
                'sucesso': False,
                'erro': resultados['erro']
            }, status=400)

        total = len(resultados)
        sucesso = sum(1 for r in resultados if r.get('sucesso'))
        falhas = total - sucesso

        return JsonResponse({
            'sucesso': True,
            'total': total,
            'gerados': sucesso,
            'falhas': falhas,
            'resultados': resultados,
            'mensagem': f'{sucesso} de {total} boletos gerados com sucesso'
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
def visualizar_boleto(request, pk):
    """
    Visualiza dados do boleto de uma parcela.
    """
    parcela = get_object_or_404(
        Parcela.objects.select_related(
            'contrato',
            'contrato__comprador',
            'contrato__imovel',
            'contrato__imovel__imobiliaria',
            'conta_bancaria'
        ),
        pk=pk
    )

    if not parcela.tem_boleto:
        messages.warning(request, 'Boleto ainda não foi gerado para esta parcela.')
        return redirect('financeiro:detalhe_parcela', pk=pk)

    context = {
        'parcela': parcela,
        'contrato': parcela.contrato,
        'comprador': parcela.contrato.comprador,
        'imobiliaria': parcela.contrato.imovel.imobiliaria,
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
