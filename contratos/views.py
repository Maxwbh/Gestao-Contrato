"""
Views do app Contratos

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import models
from django.db.models import Q, Sum
from .models import Contrato, StatusContrato, IndiceReajuste, PrestacaoIntermediaria, TabelaJurosContrato
from .forms import ContratoForm, IndiceReajusteForm
from core.mixins import PaginacaoMixin
import requests
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
import logging
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


def _voltar_url(request, default):
    """Retorna o HTTP_REFERER se for da mesma origem, senão o default."""
    from urllib.parse import urlparse
    ref = request.META.get('HTTP_REFERER', '')
    if ref:
        p = urlparse(ref)
        if not p.netloc or p.netloc == request.get_host():
            return ref
    return default


class ContratoListView(LoginRequiredMixin, PaginacaoMixin, ListView):
    """Lista todos os contratos"""
    model = Contrato
    template_name = 'contratos/contrato_list.html'
    context_object_name = 'contratos'
    paginate_by = 20

    def get_queryset(self):
        queryset = Contrato.objects.select_related(
            'imovel', 'imovel__imobiliaria',
            'comprador',
            'imobiliaria'
        ).order_by('-data_contrato')

        # Filtro de busca
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(numero_contrato__icontains=search) |
                Q(comprador__nome__icontains=search) |
                Q(imovel__identificacao__icontains=search) |
                Q(imovel__loteamento__icontains=search)
            )

        # Filtro de status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Filtro de imobiliária
        imobiliaria = self.request.GET.get('imobiliaria')
        if imobiliaria:
            queryset = queryset.filter(imobiliaria_id=imobiliaria)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['imobiliaria_filter'] = self.request.GET.get('imobiliaria', '')
        context['status_choices'] = StatusContrato.choices
        context['total_contratos'] = Contrato.objects.count()
        context['contratos_ativos'] = Contrato.objects.filter(status=StatusContrato.ATIVO).count()
        context['contratos_quitados'] = Contrato.objects.filter(status=StatusContrato.QUITADO).count()

        # Lista de imobiliárias para filtro
        from core.models import Imobiliaria
        context['imobiliarias'] = Imobiliaria.objects.filter(ativo=True)

        # Contratos que precisam de reajuste no mês corrente
        context['contratos_reajuste'] = self._get_contratos_reajuste_pendente()

        return context

    def _get_contratos_reajuste_pendente(self):
        """
        Retorna contratos que precisam de reajuste no mês corrente.
        Um contrato precisa de reajuste quando:
        1. Está ativo
        2. Tipo de correção não é FIXO
        3. Passou o prazo de reajuste desde a última atualização
        """
        from django.utils import timezone
        from .models import TipoCorrecao
        from dateutil.relativedelta import relativedelta

        hoje = timezone.now().date()
        contratos_pendentes = []

        contratos_ativos = Contrato.objects.filter(
            status=StatusContrato.ATIVO
        ).exclude(
            tipo_correcao=TipoCorrecao.FIXO
        ).select_related('comprador', 'imovel', 'imobiliaria')

        for contrato in contratos_ativos:
            # Data base para reajuste
            data_base = contrato.data_ultimo_reajuste or contrato.data_contrato

            # Calcular próxima data de reajuste
            proxima_data_reajuste = data_base + relativedelta(months=contrato.prazo_reajuste_meses)

            # Se a próxima data de reajuste é no mês corrente ou já passou
            if (proxima_data_reajuste.year < hoje.year
                    or (proxima_data_reajuste.year == hoje.year
                        and proxima_data_reajuste.month <= hoje.month)):

                # Calcular meses em atraso
                meses_atraso = (hoje.year - proxima_data_reajuste.year) * 12 + (hoje.month - proxima_data_reajuste.month)

                contratos_pendentes.append({
                    'contrato': contrato,
                    'data_ultimo_reajuste': contrato.data_ultimo_reajuste,
                    'proxima_data_reajuste': proxima_data_reajuste,
                    'meses_atraso': meses_atraso,
                    'tipo_correcao': contrato.get_tipo_correcao_display(),
                })

        # Ordenar por meses em atraso (mais atrasados primeiro)
        contratos_pendentes.sort(key=lambda x: x['meses_atraso'], reverse=True)

        return contratos_pendentes


class ContratoCreateView(LoginRequiredMixin, CreateView):
    """Cria um novo contrato"""
    model = Contrato
    form_class = ContratoForm
    template_name = 'contratos/contrato_form.html'
    success_url = reverse_lazy('contratos:listar')

    def form_valid(self, form):
        messages.success(self.request, f'Contrato {form.instance.numero_contrato} criado com sucesso! Parcelas geradas automaticamente.')
        return super().form_valid(form)

    def form_invalid(self, form):
        # Monta mensagem de erro detalhada
        erros = []
        for campo, lista_erros in form.errors.items():
            nome_campo = form.fields[campo].label if campo in form.fields else campo
            for erro in lista_erros:
                erros.append(f'{nome_campo}: {erro}')

        if erros:
            messages.error(self.request, f'Erro ao criar contrato: {"; ".join(erros[:3])}')
        else:
            messages.error(self.request, 'Erro ao criar contrato. Verifique os dados.')
        return super().form_invalid(form)


class ContratoUpdateView(LoginRequiredMixin, UpdateView):
    """Atualiza um contrato existente"""
    model = Contrato
    form_class = ContratoForm
    template_name = 'contratos/contrato_form.html'
    success_url = reverse_lazy('contratos:listar')

    def form_valid(self, form):
        messages.success(self.request, f'Contrato {form.instance.numero_contrato} atualizado com sucesso!')
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
            messages.error(self.request, 'Erro ao atualizar contrato. Verifique os dados.')
        return super().form_invalid(form)


class ContratoDetailView(LoginRequiredMixin, DetailView):
    """Exibe detalhes de um contrato"""
    model = Contrato
    template_name = 'contratos/contrato_detail.html'
    context_object_name = 'contrato'

    def get_queryset(self):
        return Contrato.objects.select_related(
            'imovel', 'imovel__imobiliaria',
            'comprador',
            'imobiliaria'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contrato = self.object
        from django.utils import timezone

        context['progresso'] = contrato.calcular_progresso()
        context['valor_pago'] = contrato.calcular_valor_pago()
        context['saldo_devedor'] = contrato.calcular_saldo_devedor()

        # Parcelas
        context['parcelas'] = contrato.parcelas.all().order_by('numero_parcela')
        context['parcelas_pagas'] = contrato.parcelas.filter(pago=True).count()
        context['parcelas_pendentes'] = contrato.parcelas.filter(pago=False).count()

        # Próxima parcela a vencer
        context['proxima_parcela'] = contrato.parcelas.filter(
            pago=False,
            data_vencimento__gte=timezone.now().date()
        ).order_by('data_vencimento').first()

        # Parcelas em atraso
        context['parcelas_atrasadas'] = contrato.parcelas.filter(
            pago=False,
            data_vencimento__lt=timezone.now().date()
        ).count()

        # Reajustes do contrato
        context['reajustes'] = contrato.reajustes.all().order_by('-data_reajuste')

        # Índices disponíveis para reajuste manual
        context['indices_reajuste'] = IndiceReajuste.objects.filter(
            ano=timezone.now().year
        ).order_by('-mes').values('tipo_indice').distinct()

        # Tipos de índice únicos para o dropdown
        context['tipos_indice'] = [
            ('IPCA', 'IPCA - IBGE'),
            ('IGPM', 'IGP-M - FGV'),
            ('INCC', 'INCC - FGV'),
            ('INPC', 'INPC - IBGE'),
            ('SELIC', 'SELIC'),
            ('MANUAL', 'Percentual Manual'),
        ]

        # Conta bancária da imobiliária (usa a do contrato ou a principal da imobiliária)
        conta_bancaria = None
        if hasattr(contrato, 'get_conta_bancaria'):
            conta_bancaria = contrato.get_conta_bancaria()
        if not conta_bancaria:
            conta_bancaria = contrato.imobiliaria.contas_bancarias.filter(
                principal=True, ativo=True
            ).first()
        if not conta_bancaria:
            conta_bancaria = contrato.imobiliaria.contas_bancarias.filter(
                ativo=True
            ).first()
        context['conta_bancaria'] = conta_bancaria

        # =====================================================================
        # PRESTAÇÕES INTERMEDIÁRIAS
        # =====================================================================
        if hasattr(contrato, 'intermediarias'):
            from django.utils import timezone as tz
            from dateutil.relativedelta import relativedelta
            todas = contrato.intermediarias.all().order_by('numero_sequencial')
            context['intermediarias'] = todas
            context['total_intermediarias'] = todas.count()
            context['intermediarias_pagas'] = todas.filter(paga=True).count()
            context['intermediarias_pendentes'] = todas.filter(paga=False).count()
            # Intermediárias vencidas sem boleto gerado
            hoje = tz.now().date()
            vencidas_sem_boleto = [
                inter for inter in todas.filter(paga=False, parcela_vinculada__isnull=True)
                if (contrato.data_primeiro_vencimento + relativedelta(months=inter.mes_vencimento - 1)).replace(
                    day=min(contrato.dia_vencimento, 28)
                ) <= hoje
            ]
            context['intermediarias_vencidas_sem_boleto'] = vencidas_sem_boleto
        else:
            context['intermediarias'] = []
            context['total_intermediarias'] = 0
            context['intermediarias_pagas'] = 0
            context['intermediarias_pendentes'] = 0
            context['intermediarias_vencidas_sem_boleto'] = []

        # =====================================================================
        # CONTROLE DE BLOQUEIO DE BOLETO POR REAJUSTE
        # =====================================================================
        # verificar_bloqueio_reajuste() retorna bool (True = bloqueado)
        _bloqueado = (
            contrato.verificar_bloqueio_reajuste()
            if hasattr(contrato, 'verificar_bloqueio_reajuste')
            else False
        )
        context['bloqueio_reajuste'] = {
            'bloqueado': bool(_bloqueado),
            'motivo': '',
            'ciclo_atual': 1,
            'ciclo_pendente': None,
        }

        # Verificar status de cada parcela para geração de boleto
        # Batch: prefetch applied reajuste cycles once to avoid N+1 queries
        parcelas_status_boleto = []
        if hasattr(contrato, 'pode_gerar_boleto'):
            from financeiro.models import Reajuste as ReajusteModel
            from django.utils import timezone as _tz
            from dateutil.relativedelta import relativedelta as _rdelta
            from contratos.models import TipoCorrecao as _TC

            _hoje = _tz.now().date()
            _prazo = contrato.prazo_reajuste_meses or 12
            _fixo = contrato.tipo_correcao == _TC.FIXO

            # Single query: all applied cycles for this contract
            _applied_cycles = set(
                ReajusteModel.objects.filter(contrato=contrato, aplicado=True)
                .values_list('ciclo', flat=True)
            )

            # Find first blocked cycle (done once, not per parcela)
            _blocked_cycle = None
            _blocked_msg = ''
            if not _fixo:
                for _c in range(2, 9999):
                    _data = contrato.data_contrato + _rdelta(months=(_c - 1) * _prazo)
                    if _hoje < _data:
                        break  # future cycle — stop
                    if _c not in _applied_cycles:
                        _blocked_cycle = _c
                        _blocked_msg = (
                            f"Reajuste do ciclo {_c} pendente desde "
                            f"{_data.strftime('%d/%m/%Y')}. "
                            f"Execute o reajuste antes de gerar boletos."
                        )
                        break

            for parcela in context['parcelas']:
                if _fixo:
                    pode_gerar, motivo = True, "Índice FIXO — sem necessidade de reajuste."
                else:
                    _ciclo_parcela = (parcela.numero_parcela - 1) // _prazo + 1
                    if _ciclo_parcela <= 1:
                        pode_gerar, motivo = True, "Primeiro ciclo — liberado."
                    elif _blocked_cycle is not None and _blocked_cycle <= _ciclo_parcela:
                        pode_gerar, motivo = False, _blocked_msg
                    else:
                        pode_gerar = True
                        motivo = f"Reajuste do ciclo {_ciclo_parcela} aplicado."
                parcelas_status_boleto.append({
                    'parcela': parcela,
                    'pode_gerar_boleto': pode_gerar,
                    'motivo_bloqueio': motivo if not pode_gerar else '',
                })
        else:
            for parcela in context['parcelas']:
                parcelas_status_boleto.append({
                    'parcela': parcela,
                    'pode_gerar_boleto': True,
                    'motivo_bloqueio': '',
                })
        context['parcelas_status_boleto'] = parcelas_status_boleto

        # =====================================================================
        # RESUMO FINANCEIRO DO CONTRATO
        # =====================================================================
        if hasattr(contrato, 'get_resumo_financeiro'):
            context['resumo_financeiro'] = contrato.get_resumo_financeiro()
        else:
            context['resumo_financeiro'] = {}

        # =====================================================================
        # INFORMAÇÕES DE CICLO DE REAJUSTE
        # =====================================================================
        context['ciclo_atual'] = getattr(contrato, 'ciclo_reajuste_atual', 1)
        context['prazo_reajuste'] = getattr(contrato, 'prazo_reajuste_meses', 12)
        context['ultimo_mes_boleto'] = getattr(contrato, 'ultimo_mes_boleto_gerado', 0)

        # =====================================================================
        # Q-04: TABELA DE JUROS ESCALANTES
        # =====================================================================
        context['tabela_juros'] = contrato.tabela_juros.all().order_by('ciclo_inicio')

        # =====================================================================
        # HISTÓRICO DE PAGAMENTOS (3.19)
        # =====================================================================
        from financeiro.models import HistoricoPagamento
        context['historico_pagamentos'] = (
            HistoricoPagamento.objects
            .filter(parcela__contrato=contrato)
            .select_related('parcela')
            .order_by('-data_pagamento')
        )

        # Botão Voltar dinâmico
        from django.urls import reverse
        context['voltar_url'] = _voltar_url(
            self.request, reverse('contratos:listar')
        )

        return context


class ContratoDeleteView(LoginRequiredMixin, DeleteView):
    """Cancela um contrato (soft delete via status)"""
    model = Contrato
    success_url = reverse_lazy('contratos:listar')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Verifica se tem parcelas pagas
        parcelas_pagas = self.object.parcelas.filter(pago=True).count()
        if parcelas_pagas > 0:
            messages.error(request, f'Não é possível cancelar o contrato. Existem {parcelas_pagas} parcela(s) já paga(s).')
            return redirect('contratos:detalhe', pk=self.object.pk)

        # Soft delete - apenas muda o status para CANCELADO
        self.object.status = StatusContrato.CANCELADO
        self.object.save()

        # Liberar o imóvel
        if self.object.imovel:
            self.object.imovel.disponivel = True
            self.object.imovel.save()

        messages.success(request, f'Contrato {self.object.numero_contrato} cancelado com sucesso!')
        return redirect(self.success_url)


# Views antigas mantidas para compatibilidade
@login_required
def listar_contratos(request):
    """Lista todos os contratos (view antiga)"""
    return ContratoListView.as_view()(request)


@login_required
def detalhe_contrato(request, pk):
    """Exibe detalhes de um contrato (view antiga)"""
    return ContratoDetailView.as_view()(request, pk=pk)


@login_required
def parcelas_contrato(request, pk):
    """Lista todas as parcelas de um contrato"""
    contrato = get_object_or_404(Contrato, pk=pk)
    parcelas = contrato.parcelas.all().order_by('numero_parcela')

    context = {
        'contrato': contrato,
        'parcelas': parcelas,
    }
    return render(request, 'contratos/parcelas.html', context)


@login_required
@require_http_methods(["POST"])
def api_completar_parcelas(request, pk):
    """
    Cria as parcelas faltantes de um contrato sem recriar as existentes.
    Útil após gerar_dados_teste (que cria só até o mês atual).
    """
    contrato = get_object_or_404(Contrato, pk=pk)

    existentes = contrato.parcelas.count()
    if existentes >= contrato.numero_parcelas:
        return JsonResponse({
            'status': 'ok',
            'message': 'Nenhuma parcela faltando.',
            'criadas': 0,
        })

    try:
        criados = contrato.completar_parcelas_faltantes()
        messages.success(
            request,
            f'{len(criados)} parcela(s) criada(s) para {contrato.numero_contrato}.'
        )
        return JsonResponse({
            'status': 'ok',
            'message': f'{len(criados)} parcela(s) criada(s).',
            'criadas': len(criados),
            'numeros': criados,
        })
    except Exception as e:
        logger.exception("Erro ao completar parcelas do contrato %s: %s", pk, e)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ==============================================================
# CRUD de Índices de Reajuste
# ==============================================================

class IndiceReajusteListView(LoginRequiredMixin, PaginacaoMixin, ListView):
    """Lista todos os índices de reajuste"""
    model = IndiceReajuste
    template_name = 'contratos/indice_list.html'
    context_object_name = 'indices'
    paginate_by = 50

    def get_queryset(self):
        queryset = IndiceReajuste.objects.all().order_by('-ano', '-mes', 'tipo_indice')

        # Filtro por tipo
        tipo = self.request.GET.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo_indice=tipo)

        # Filtro por ano
        ano = self.request.GET.get('ano')
        if ano:
            queryset = queryset.filter(ano=ano)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tipo_filter'] = self.request.GET.get('tipo', '')
        context['ano_filter'] = self.request.GET.get('ano', '')

        # Anos disponíveis para filtro
        context['anos_disponiveis'] = IndiceReajuste.objects.values_list(
            'ano', flat=True
        ).distinct().order_by('-ano')

        # Tipos de índice
        context['tipos_indice'] = [
            ('IPCA', 'IPCA'),
            ('IGPM', 'IGP-M'),
            ('INCC', 'INCC'),
            ('IGPDI', 'IGP-DI'),
            ('INPC', 'INPC'),
            ('TR', 'TR'),
            ('SELIC', 'SELIC'),
        ]

        # Total de índices
        context['total_indices'] = IndiceReajuste.objects.count()

        # Estatísticas por tipo
        tipos = ['IPCA', 'IGPM', 'INCC', 'IGPDI', 'INPC', 'TR', 'SELIC']
        context['estatisticas_indices'] = []
        for tipo in tipos:
            total = IndiceReajuste.objects.filter(tipo_indice=tipo).count()
            if total > 0:  # Só mostrar tipos que têm registros
                ultimo = IndiceReajuste.objects.filter(tipo_indice=tipo).order_by('-ano', '-mes').first()
                context['estatisticas_indices'].append({
                    'tipo': tipo,
                    'total': total,
                    'ultimo': ultimo,
                })

        # Data do contrato mais antigo (para limite de importação)
        contrato_mais_antigo = Contrato.objects.order_by('data_contrato').first()
        if contrato_mais_antigo:
            context['data_contrato_mais_antigo'] = contrato_mais_antigo.data_contrato
        else:
            context['data_contrato_mais_antigo'] = None

        return context


class IndiceReajusteCreateView(LoginRequiredMixin, CreateView):
    """Cria um novo índice de reajuste"""
    model = IndiceReajuste
    form_class = IndiceReajusteForm
    template_name = 'contratos/indice_form.html'
    success_url = reverse_lazy('contratos:indices_listar')

    def form_valid(self, form):
        messages.success(self.request, f'Índice {form.instance} cadastrado com sucesso!')
        return super().form_valid(form)


class IndiceReajusteUpdateView(LoginRequiredMixin, UpdateView):
    """Atualiza um índice de reajuste"""
    model = IndiceReajuste
    form_class = IndiceReajusteForm
    template_name = 'contratos/indice_form.html'
    success_url = reverse_lazy('contratos:indices_listar')

    def form_valid(self, form):
        messages.success(self.request, f'Índice {form.instance} atualizado com sucesso!')
        return super().form_valid(form)


class IndiceReajusteDeleteView(LoginRequiredMixin, DeleteView):
    """Exclui um índice de reajuste"""
    model = IndiceReajuste
    success_url = reverse_lazy('contratos:indices_listar')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        messages.success(request, f'Índice {self.object} excluído com sucesso!')
        return super().delete(request, *args, **kwargs)


# ==============================================================
# APIs para buscar índices do IBGE/BCB
# ==============================================================

@login_required
@require_http_methods(["POST"])
def importar_indices_ibge(request):
    """
    Importa índices do IBGE (IPCA) e BCB (IGP-M, SELIC)
    API IBGE (SIDRA): https://servicodados.ibge.gov.br/api/docs/agregados
    API BCB: https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados
    """
    try:
        data = json.loads(request.body)
        tipo_indice = data.get('tipo_indice', 'IPCA')
        ano_inicio = data.get('ano_inicio')
        mes_inicio = data.get('mes_inicio', 1)

        # Determinar data de início
        if not ano_inicio:
            # Buscar último índice cadastrado ou data do contrato mais antigo
            ultimo_indice = IndiceReajuste.objects.filter(
                tipo_indice=tipo_indice
            ).order_by('-ano', '-mes').first()

            if ultimo_indice:
                # Começar do mês seguinte ao último cadastrado
                ano_inicio = ultimo_indice.ano
                mes_inicio = ultimo_indice.mes + 1
                if mes_inicio > 12:
                    mes_inicio = 1
                    ano_inicio += 1
            else:
                # Buscar contrato mais antigo
                contrato_mais_antigo = Contrato.objects.order_by('data_contrato').first()
                if contrato_mais_antigo:
                    ano_inicio = contrato_mais_antigo.data_contrato.year
                    mes_inicio = contrato_mais_antigo.data_contrato.month
                else:
                    ano_inicio = datetime.now().year - 1
                    mes_inicio = 1

        # Buscar dados da API
        if tipo_indice == 'IPCA':
            indices = _buscar_ipca_ibge(ano_inicio, mes_inicio)
        elif tipo_indice == 'IGPM':
            indices = _buscar_igpm_bcb(ano_inicio, mes_inicio)
        elif tipo_indice == 'INCC':
            indices = _buscar_incc_bcb(ano_inicio, mes_inicio)
        elif tipo_indice == 'IGPDI':
            indices = _buscar_igpdi_bcb(ano_inicio, mes_inicio)
        elif tipo_indice == 'INPC':
            indices = _buscar_inpc_ibge(ano_inicio, mes_inicio)
        elif tipo_indice == 'TR':
            indices = _buscar_tr_bcb(ano_inicio, mes_inicio)
        elif tipo_indice == 'SELIC':
            indices = _buscar_selic_bcb(ano_inicio, mes_inicio)
        else:
            return JsonResponse({'success': False, 'error': 'Tipo de índice inválido'}, status=400)

        # Salvar índices no banco usando bulk operations para melhor performance
        count_created = 0
        count_updated = 0

        # Buscar índices existentes para este tipo
        existing_indices = {
            (idx.ano, idx.mes): idx
            for idx in IndiceReajuste.objects.filter(tipo_indice=tipo_indice)
        }

        to_create = []
        to_update = []
        now = datetime.now()

        for indice_data in indices:
            key = (indice_data['ano'], indice_data['mes'])

            if key in existing_indices:
                # Atualizar existente
                obj = existing_indices[key]
                obj.valor = indice_data['valor']
                obj.valor_acumulado_ano = indice_data.get('acumulado_ano')
                obj.valor_acumulado_12m = indice_data.get('acumulado_12m')
                obj.fonte = indice_data.get('fonte', 'API')
                obj.data_importacao = now
                to_update.append(obj)
                count_updated += 1
            else:
                # Criar novo
                to_create.append(IndiceReajuste(
                    tipo_indice=tipo_indice,
                    ano=indice_data['ano'],
                    mes=indice_data['mes'],
                    valor=indice_data['valor'],
                    valor_acumulado_ano=indice_data.get('acumulado_ano'),
                    valor_acumulado_12m=indice_data.get('acumulado_12m'),
                    fonte=indice_data.get('fonte', 'API'),
                    data_importacao=now,
                ))
                count_created += 1

        # Bulk create novos registros
        if to_create:
            IndiceReajuste.objects.bulk_create(to_create, batch_size=100)

        # Bulk update registros existentes
        if to_update:
            IndiceReajuste.objects.bulk_update(
                to_update,
                ['valor', 'valor_acumulado_ano', 'valor_acumulado_12m', 'fonte', 'data_importacao'],
                batch_size=100
            )

        return JsonResponse({
            'success': True,
            'message': f'Importação concluída! {count_created} novos, {count_updated} atualizados.',
            'created': count_created,
            'updated': count_updated,
            'total': len(indices)
        })

    except Exception as e:
        logger.exception("Erro ao importar indices: %s", e)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def _buscar_ipca_ibge(ano_inicio, mes_inicio):
    """
    Busca IPCA da API SIDRA do IBGE
    Tabela 1737 - IPCA - Variação mensal, acumulada no ano e acumulada em 12 meses
    """
    indices = []

    try:
        # API SIDRA - Tabela 1737 (IPCA)
        # Código da variável: 63 (variação mensal)
        url = "https://servicodados.ibge.gov.br/api/v3/agregados/1737/periodos/all/variaveis/63|69|2265?localidades=N1[all]"

        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        if not data or len(data) == 0:
            return indices

        # Processar dados
        # Estrutura: data[0] = var mensal, data[1] = acum ano, data[2] = acum 12m
        var_mensal = data[0]['resultados'][0]['series'][0]['serie'] if len(data) > 0 else {}
        var_acum_ano = data[1]['resultados'][0]['series'][0]['serie'] if len(data) > 1 else {}
        var_acum_12m = data[2]['resultados'][0]['series'][0]['serie'] if len(data) > 2 else {}

        for periodo, valor in var_mensal.items():
            if valor == '-' or valor == '...' or valor is None:
                continue

            # Período formato: 202401 (AAAAMM)
            ano = int(periodo[:4])
            mes = int(periodo[4:6])

            # Filtrar por data de início
            if ano < ano_inicio or (ano == ano_inicio and mes < mes_inicio):
                continue

            indices.append({
                'ano': ano,
                'mes': mes,
                'valor': float(valor.replace(',', '.')),
                'acumulado_ano': float(var_acum_ano.get(periodo, '0').replace(',', '.')) if var_acum_ano.get(periodo) not in ['-', '...', None] else None,
                'acumulado_12m': float(var_acum_12m.get(periodo, '0').replace(',', '.')) if var_acum_12m.get(periodo) not in ['-', '...', None] else None,
                'fonte': 'IBGE/SIDRA'
            })

    except Exception as e:
        logger.exception("Erro ao buscar IPCA: %s", e)

    return indices


def _buscar_igpm_bcb(ano_inicio, mes_inicio):
    """
    Busca IGP-M da API do Banco Central
    Série 189 - IGP-M - Variação mensal
    """
    indices = []

    try:
        # Formatar data de início
        data_inicio = f"01/{mes_inicio:02d}/{ano_inicio}"

        # API BCB - Série 189 (IGP-M mensal)
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.189/dados?formato=json&dataInicial={data_inicio}"

        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        for item in data:
            # Data formato: dd/mm/yyyy
            partes = item['data'].split('/')
            _, mes, ano = int(partes[0]), int(partes[1]), int(partes[2])

            indices.append({
                'ano': ano,
                'mes': mes,
                'valor': float(item['valor']),
                'acumulado_ano': None,
                'acumulado_12m': None,
                'fonte': 'BCB'
            })

    except Exception as e:
        logger.exception("Erro ao buscar IGP-M: %s", e)

    return indices


def _buscar_selic_bcb(ano_inicio, mes_inicio):
    """
    Busca SELIC da API do Banco Central
    Série 4390 - Taxa Selic acumulada no mês
    """
    indices = []

    try:
        # Formatar data de início
        data_inicio = f"01/{mes_inicio:02d}/{ano_inicio}"

        # API BCB - Série 4390 (SELIC mensal)
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.4390/dados?formato=json&dataInicial={data_inicio}"

        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        for item in data:
            # Data formato: dd/mm/yyyy
            partes = item['data'].split('/')
            _, mes, ano = int(partes[0]), int(partes[1]), int(partes[2])

            indices.append({
                'ano': ano,
                'mes': mes,
                'valor': float(item['valor']),
                'acumulado_ano': None,
                'acumulado_12m': None,
                'fonte': 'BCB'
            })

    except Exception as e:
        logger.exception("Erro ao buscar SELIC: %s", e)

    return indices


def _buscar_incc_bcb(ano_inicio, mes_inicio):
    """
    Busca INCC da API do Banco Central
    Série 192 - INCC-DI - Variação mensal
    """
    indices = []

    try:
        data_inicio = f"01/{mes_inicio:02d}/{ano_inicio}"
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.192/dados?formato=json&dataInicial={data_inicio}"

        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        for item in data:
            partes = item['data'].split('/')
            mes = int(partes[1])
            ano = int(partes[2])

            indices.append({
                'ano': ano,
                'mes': mes,
                'valor': float(item['valor']),
                'acumulado_ano': None,
                'acumulado_12m': None,
                'fonte': 'BCB/FGV'
            })

    except Exception as e:
        logger.exception("Erro ao buscar INCC: %s", e)

    return indices


def _buscar_igpdi_bcb(ano_inicio, mes_inicio):
    """
    Busca IGP-DI da API do Banco Central
    Série 190 - IGP-DI - Variação mensal
    """
    indices = []

    try:
        data_inicio = f"01/{mes_inicio:02d}/{ano_inicio}"
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.190/dados?formato=json&dataInicial={data_inicio}"

        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        for item in data:
            partes = item['data'].split('/')
            mes = int(partes[1])
            ano = int(partes[2])

            indices.append({
                'ano': ano,
                'mes': mes,
                'valor': float(item['valor']),
                'acumulado_ano': None,
                'acumulado_12m': None,
                'fonte': 'BCB/FGV'
            })

    except Exception as e:
        logger.exception("Erro ao buscar IGP-DI: %s", e)

    return indices


def _buscar_inpc_ibge(ano_inicio, mes_inicio):
    """
    Busca INPC da API SIDRA do IBGE
    Tabela 1100 - INPC - Variação mensal
    """
    indices = []

    try:
        # API SIDRA - Tabela 1100 (INPC)
        url = "https://servicodados.ibge.gov.br/api/v3/agregados/1100/periodos/all/variaveis/44?localidades=N1[all]"

        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        if not data or len(data) == 0:
            return indices

        var_mensal = data[0]['resultados'][0]['series'][0]['serie'] if len(data) > 0 else {}

        for periodo, valor in var_mensal.items():
            if valor == '-' or valor == '...' or valor is None:
                continue

            ano = int(periodo[:4])
            mes = int(periodo[4:6])

            if ano < ano_inicio or (ano == ano_inicio and mes < mes_inicio):
                continue

            indices.append({
                'ano': ano,
                'mes': mes,
                'valor': float(valor.replace(',', '.')),
                'acumulado_ano': None,
                'acumulado_12m': None,
                'fonte': 'IBGE/SIDRA'
            })

    except Exception as e:
        logger.exception("Erro ao buscar INPC: %s", e)

    return indices


def _buscar_tr_bcb(ano_inicio, mes_inicio):
    """
    Busca TR (Taxa Referencial) da API do Banco Central
    Série 226 - Taxa referencial - acumulada no mês
    """
    indices = []

    try:
        data_inicio = f"01/{mes_inicio:02d}/{ano_inicio}"
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.226/dados?formato=json&dataInicial={data_inicio}"

        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        for item in data:
            partes = item['data'].split('/')
            mes = int(partes[1])
            ano = int(partes[2])

            indices.append({
                'ano': ano,
                'mes': mes,
                'valor': float(item['valor']),
                'acumulado_ano': None,
                'acumulado_12m': None,
                'fonte': 'BCB'
            })

    except Exception as e:
        logger.exception("Erro ao buscar TR: %s", e)

    return indices


# ==============================================================
# CRUD de Prestações Intermediárias
# ==============================================================


class IntermediariasListView(LoginRequiredMixin, PaginacaoMixin, ListView):
    """Lista todas as prestações intermediárias de um contrato"""
    model = PrestacaoIntermediaria
    template_name = 'contratos/intermediaria_list.html'
    context_object_name = 'intermediarias'
    paginate_by = 20

    def get_queryset(self):
        self.contrato = get_object_or_404(Contrato, pk=self.kwargs['contrato_id'])
        return PrestacaoIntermediaria.objects.filter(
            contrato=self.contrato
        ).select_related('contrato', 'parcela_vinculada').order_by('numero_sequencial')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contrato'] = self.contrato

        # Estatísticas
        intermediarias = self.get_queryset()
        context['total_intermediarias'] = intermediarias.count()
        context['intermediarias_pagas'] = intermediarias.filter(paga=True).count()
        context['intermediarias_pendentes'] = intermediarias.filter(paga=False).count()

        from django.db.models import Sum
        context['valor_total'] = intermediarias.aggregate(
            total=Sum('valor')
        )['total'] or Decimal('0.00')
        context['valor_pago'] = intermediarias.filter(paga=True).aggregate(
            total=Sum('valor_pago')
        )['total'] or Decimal('0.00')
        context['valor_pendente'] = intermediarias.filter(paga=False).aggregate(
            total=Sum('valor')
        )['total'] or Decimal('0.00')

        return context


class IntermediariasDetailView(LoginRequiredMixin, DetailView):
    """Exibe detalhes de uma prestação intermediária"""
    model = PrestacaoIntermediaria
    template_name = 'contratos/intermediaria_detail.html'
    context_object_name = 'intermediaria'

    def get_queryset(self):
        return PrestacaoIntermediaria.objects.select_related(
            'contrato', 'contrato__comprador', 'contrato__imovel',
            'parcela_vinculada'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contrato'] = self.object.contrato

        # Verificar se pode gerar boleto
        if hasattr(self.object.contrato, 'pode_gerar_boleto'):
            pode_gerar, motivo = self.object.contrato.pode_gerar_boleto(
                self.object.mes_vencimento
            )
            context['pode_gerar_boleto'] = pode_gerar
            context['motivo_bloqueio'] = motivo if not pode_gerar else ''
        else:
            context['pode_gerar_boleto'] = True
            context['motivo_bloqueio'] = ''

        return context


def _recalcular_se_necessario(contrato):
    """
    Recalcula amortização das parcelas NORMAL quando intermediarias_reduzem_pmt=True.

    Replica a lógica do wizard: base_pv = valor_financiado − Σ(valor de todas as
    intermediárias, pagas ou não), garantindo que mudanças posteriores nas
    intermediárias se reflitam nas parcelas mensais.
    """
    if not contrato.intermediarias_reduzem_pmt:
        return
    soma = contrato.intermediarias.aggregate(
        total=Sum('valor')
    )['total'] or Decimal('0')
    base_pv = max(contrato.valor_financiado - soma, Decimal('0.01'))
    contrato.recalcular_amortizacao(base_pv=base_pv)


@login_required
@require_http_methods(["POST"])
def criar_intermediaria(request, contrato_id):
    """Cria uma nova prestação intermediária para um contrato"""
    contrato = get_object_or_404(Contrato, pk=contrato_id)

    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST

        # Validar quantidade máxima de intermediárias
        qtd_atual = contrato.intermediarias.count() if hasattr(contrato, 'intermediarias') else 0
        if qtd_atual >= 30:  # Limite absoluto
            return JsonResponse({
                'sucesso': False,
                'erro': 'Limite máximo de 30 prestações intermediárias atingido'
            }, status=400)

        # Determinar próximo número sequencial
        ultimo_numero = contrato.intermediarias.aggregate(
            max_seq=models.Max('numero_sequencial')
        )['max_seq'] or 0
        proximo_numero = ultimo_numero + 1

        # Criar a intermediária
        intermediaria = PrestacaoIntermediaria.objects.create(
            contrato=contrato,
            numero_sequencial=proximo_numero,
            mes_vencimento=int(data.get('mes_vencimento', 12)),
            valor=Decimal(str(data.get('valor', 0))),
            observacoes=data.get('observacoes', '')
        )

        # Recalcular PMT das parcelas se a flag intermediarias_reduzem_pmt estiver ativa
        _recalcular_se_necessario(contrato)

        return JsonResponse({
            'sucesso': True,
            'mensagem': f'Prestação intermediária #{proximo_numero} criada com sucesso',
            'intermediaria_id': intermediaria.id,
            'numero_sequencial': intermediaria.numero_sequencial
        })

    except ValueError as e:
        return JsonResponse({
            'sucesso': False,
            'erro': f'Valor inválido: {str(e)}'
        }, status=400)
    except Exception as e:
        logger.exception("Erro ao criar intermediaria: %s", e)
        return JsonResponse({
            'sucesso': False,
            'erro': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def atualizar_intermediaria(request, pk):
    """Atualiza uma prestação intermediária"""
    intermediaria = get_object_or_404(PrestacaoIntermediaria, pk=pk)

    if intermediaria.paga:
        return JsonResponse({
            'sucesso': False,
            'erro': 'Não é possível alterar uma prestação já paga'
        }, status=400)

    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST

        if 'mes_vencimento' in data:
            intermediaria.mes_vencimento = int(data['mes_vencimento'])
        valor_alterado = False
        if 'valor' in data:
            novo_valor = Decimal(str(data['valor']))
            if novo_valor != intermediaria.valor:
                intermediaria.valor = novo_valor
                valor_alterado = True
        if 'observacoes' in data:
            intermediaria.observacoes = data['observacoes']

        intermediaria.save()

        # Sincronizar parcela vinculada se o valor foi alterado e existe parcela
        if valor_alterado and intermediaria.parcela_vinculada:
            intermediaria.parcela_vinculada.valor_atual = intermediaria.valor_atual
            intermediaria.parcela_vinculada.save(update_fields=['valor_atual'])

        # Recalcular PMT das parcelas se a flag intermediarias_reduzem_pmt estiver ativa
        _recalcular_se_necessario(intermediaria.contrato)

        return JsonResponse({
            'sucesso': True,
            'mensagem': 'Prestação intermediária atualizada com sucesso'
        })

    except Exception as e:
        logger.exception("Erro ao atualizar intermediaria pk=%s: %s", pk, e)
        return JsonResponse({
            'sucesso': False,
            'erro': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def excluir_intermediaria(request, pk):
    """Exclui uma prestação intermediária"""
    intermediaria = get_object_or_404(PrestacaoIntermediaria, pk=pk)

    if intermediaria.paga:
        return JsonResponse({
            'sucesso': False,
            'erro': 'Não é possível excluir uma prestação já paga'
        }, status=400)

    if intermediaria.parcela_vinculada:
        return JsonResponse({
            'sucesso': False,
            'erro': 'Não é possível excluir uma prestação com parcela vinculada. Cancele o boleto primeiro.'
        }, status=400)

    try:
        contrato = intermediaria.contrato
        numero = intermediaria.numero_sequencial
        intermediaria.delete()

        # Recalcular PMT das parcelas se a flag intermediarias_reduzem_pmt estiver ativa
        _recalcular_se_necessario(contrato)

        return JsonResponse({
            'sucesso': True,
            'mensagem': f'Prestação intermediária #{numero} excluída com sucesso',
            'redirect': f'/contratos/{contrato.pk}/intermediarias/'
        })

    except Exception as e:
        logger.exception("Erro ao excluir intermediaria pk=%s: %s", pk, e)
        return JsonResponse({
            'sucesso': False,
            'erro': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def pagar_intermediaria(request, pk):
    """Registra o pagamento de uma prestação intermediária"""
    intermediaria = get_object_or_404(PrestacaoIntermediaria, pk=pk)

    if intermediaria.paga:
        return JsonResponse({
            'sucesso': False,
            'erro': 'Esta prestação já está paga'
        }, status=400)

    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST

        valor_pago = Decimal(str(data.get('valor_pago', intermediaria.valor)))
        data_pagamento_str = data.get('data_pagamento', '')

        if data_pagamento_str:
            data_pagamento = datetime.strptime(data_pagamento_str, '%Y-%m-%d').date()
        else:
            from django.utils import timezone
            data_pagamento = timezone.now().date()

        intermediaria.paga = True
        intermediaria.valor_pago = valor_pago
        intermediaria.data_pagamento = data_pagamento

        if 'observacoes' in data:
            intermediaria.observacoes = data['observacoes']

        intermediaria.save()

        # Sincronizar parcela vinculada (se existir) como paga
        if intermediaria.parcela_vinculada:
            parcela_vinc = intermediaria.parcela_vinculada
            parcela_vinc.pago = True
            parcela_vinc.valor_pago = valor_pago
            parcela_vinc.data_pagamento = data_pagamento
            parcela_vinc.save(update_fields=['pago', 'valor_pago', 'data_pagamento'])

        return JsonResponse({
            'sucesso': True,
            'mensagem': f'Pagamento de R$ {valor_pago:,.2f} registrado com sucesso',
            'intermediaria_id': intermediaria.id
        })

    except Exception as e:
        logger.exception("Erro ao processar intermediaria pk=%s: %s", pk, e)
        return JsonResponse({
            'sucesso': False,
            'erro': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def gerar_boleto_intermediaria(request, pk):
    """Gera boleto para uma prestação intermediária"""
    from financeiro.models import Parcela, TipoParcela
    from core.models import ContaBancaria

    intermediaria = get_object_or_404(
        PrestacaoIntermediaria.objects.select_related('contrato'),
        pk=pk
    )

    if intermediaria.paga:
        return JsonResponse({
            'sucesso': False,
            'erro': 'Prestação já está paga'
        }, status=400)

    if intermediaria.parcela_vinculada:
        return JsonResponse({
            'sucesso': False,
            'erro': 'Esta prestação já possui um boleto vinculado'
        }, status=400)

    contrato = intermediaria.contrato

    # Verificar bloqueio por reajuste (apenas quando intermediárias são reajustadas)
    force = request.POST.get('force', 'false').lower() == 'true'
    if not force and contrato.intermediarias_reajustadas and hasattr(contrato, 'pode_gerar_boleto'):
        pode_gerar, motivo = contrato.pode_gerar_boleto(intermediaria.mes_vencimento)
        if not pode_gerar:
            return JsonResponse({
                'sucesso': False,
                'erro': f'Boleto bloqueado: {motivo}',
                'bloqueado_reajuste': True
            }, status=400)

    try:
        # Calcular data de vencimento baseada no mês da intermediária
        from dateutil.relativedelta import relativedelta
        data_base = contrato.data_primeiro_vencimento
        data_vencimento = data_base + relativedelta(months=intermediaria.mes_vencimento - 1)

        # Ajustar dia de vencimento
        dia_vencimento = contrato.dia_vencimento
        try:
            data_vencimento = data_vencimento.replace(day=dia_vencimento)
        except ValueError:
            # Dia não existe no mês (ex: 31 em fevereiro)
            import calendar
            ultimo_dia = calendar.monthrange(data_vencimento.year, data_vencimento.month)[1]
            data_vencimento = data_vencimento.replace(day=min(dia_vencimento, ultimo_dia))

        # Criar parcela vinculada.
        # numero_parcela usa offset além das NORMAL para não conflitar com
        # unique_together = [['contrato', 'numero_parcela']] na model Parcela.
        numero_inter = contrato.numero_parcelas + intermediaria.numero_sequencial
        parcela = Parcela.objects.create(
            contrato=contrato,
            numero_parcela=numero_inter,
            data_vencimento=data_vencimento,
            valor_original=intermediaria.valor,
            valor_atual=intermediaria.valor_reajustado or intermediaria.valor,
            tipo_parcela=TipoParcela.INTERMEDIARIA if hasattr(Parcela, 'tipo_parcela') else 'INTERMEDIARIA',
            ciclo_reajuste=contrato.calcular_ciclo_parcela(intermediaria.mes_vencimento) if hasattr(contrato, 'calcular_ciclo_parcela') else 1,
        )

        # Vincular parcela à intermediária
        intermediaria.parcela_vinculada = parcela
        intermediaria.save()

        # Gerar boleto
        conta_id = request.POST.get('conta_bancaria_id')
        if conta_id:
            conta_bancaria = get_object_or_404(ContaBancaria, pk=conta_id, ativo=True)
        else:
            conta_bancaria = contrato.imobiliaria.contas_bancarias.filter(
                principal=True, ativo=True
            ).first()

        if conta_bancaria:
            resultado = parcela.gerar_boleto(conta_bancaria)
            if resultado and resultado.get('sucesso'):
                return JsonResponse({
                    'sucesso': True,
                    'mensagem': 'Boleto gerado com sucesso',
                    'parcela_id': parcela.id,
                    'nosso_numero': resultado.get('nosso_numero', '')
                })
            else:
                return JsonResponse({
                    'sucesso': False,
                    'erro': resultado.get('erro') if resultado else 'Erro ao gerar boleto'
                }, status=400)
        else:
            return JsonResponse({
                'sucesso': True,
                'mensagem': 'Parcela criada. Configure uma conta bancária para gerar o boleto.',
                'parcela_id': parcela.id
            })

    except Exception as e:
        logger.exception("Erro ao gerar boleto intermediaria pk=%s: %s", pk, e)
        return JsonResponse({
            'sucesso': False,
            'erro': str(e)
        }, status=500)


@login_required
def api_intermediarias_contrato(request, contrato_id):
    """API para retornar lista de intermediárias de um contrato em JSON"""
    contrato = get_object_or_404(Contrato, pk=contrato_id)

    intermediarias = PrestacaoIntermediaria.objects.filter(
        contrato=contrato
    ).select_related('parcela_vinculada').order_by('numero_sequencial')

    data = []
    for inter in intermediarias:
        # Verificar bloqueio por reajuste
        if hasattr(contrato, 'pode_gerar_boleto'):
            pode_gerar, motivo = contrato.pode_gerar_boleto(inter.mes_vencimento)
        else:
            pode_gerar, motivo = True, ""

        data.append({
            'id': inter.id,
            'numero_sequencial': inter.numero_sequencial,
            'mes_vencimento': inter.mes_vencimento,
            'valor': float(inter.valor),
            'valor_reajustado': float(inter.valor_reajustado) if inter.valor_reajustado else None,
            'paga': inter.paga,
            'data_pagamento': inter.data_pagamento.isoformat() if inter.data_pagamento else None,
            'valor_pago': float(inter.valor_pago) if inter.valor_pago else None,
            'tem_boleto': inter.parcela_vinculada is not None,
            'parcela_id': inter.parcela_vinculada_id,
            'pode_gerar_boleto': pode_gerar,
            'motivo_bloqueio': motivo if not pode_gerar else '',
            'observacoes': inter.observacoes,
        })

    return JsonResponse({
        'sucesso': True,
        'total': len(data),
        'intermediarias': data
    })


# =============================================================================
# Wizard — API: imóveis disponíveis por imobiliária
# =============================================================================

@login_required
def api_wizard_imoveis(request):
    """Retorna imóveis disponíveis pertencentes à imobiliária informada."""
    from core.models import Imovel as _Imovel
    imobiliaria_id = request.GET.get('imobiliaria_id')
    if not imobiliaria_id:
        return JsonResponse({'imoveis': []})
    qs = _Imovel.objects.filter(
        imobiliaria_id=imobiliaria_id,
        disponivel=True,
        ativo=True,
    ).values('id', 'identificacao', 'loteamento')
    imoveis = [
        {
            'id': i['id'],
            'texto': f"{i['identificacao']}{' — ' + i['loteamento'] if i['loteamento'] else ''}",
        }
        for i in qs
    ]
    return JsonResponse({'imoveis': imoveis})


# =============================================================================
# HU-08 — API Preview de Parcelas (projeção sem salvar)
# =============================================================================

@login_required
def api_preview_parcelas(request):
    """
    GET/POST: recebe dados do wizard (step1 + step2) e retorna projeção
    das primeiras N parcelas com marcação dos ciclos de reajuste.
    """
    from decimal import Decimal as D
    from dateutil.relativedelta import relativedelta
    import json

    try:
        if request.method == 'POST':
            payload = json.loads(request.body)
        else:
            payload = request.GET

        valor_total = D(str(payload.get('valor_total', 0)))
        valor_entrada = D(str(payload.get('valor_entrada', 0)))
        numero_parcelas = int(payload.get('numero_parcelas', 1))
        prazo_reajuste = int(payload.get('prazo_reajuste_meses', 12))
        reduzem_pmt = str(payload.get('intermediarias_reduzem_pmt', 'false')).lower() in ('true', '1')
        soma_inter = D(str(payload.get('soma_intermediarias', 0)))

        data_primeiro_vencimento = payload.get('data_primeiro_vencimento', '')
        dia_vencimento = int(payload.get('dia_vencimento', 1))

        from datetime import date
        try:
            from datetime import datetime
            data_base = datetime.strptime(data_primeiro_vencimento, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            data_base = date.today()

        tipo_amortizacao = str(payload.get('tipo_amortizacao', 'PRICE')).upper()

        valor_financiado = valor_total - valor_entrada
        if reduzem_pmt:
            base_pmt = max(valor_financiado - soma_inter, D('0.01'))
        else:
            base_pmt = valor_financiado

        # Juros por ciclo
        juros_rows = payload.get('juros', [])
        if isinstance(juros_rows, str):
            juros_rows = json.loads(juros_rows)

        def get_juros_ciclo(ciclo):
            for row in juros_rows:
                ci = int(row.get('ciclo_inicio', 1))
                cf = row.get('ciclo_fim')
                if cf:
                    if ci <= ciclo <= int(cf):
                        return D(str(row['juros_mensal']))
                else:
                    if ciclo >= ci:
                        return D(str(row['juros_mensal']))
            return D('0')

        # Intermediárias por mês
        inter_list = payload.get('intermediarias_lista', [])
        if isinstance(inter_list, str):
            inter_list = json.loads(inter_list)
        inter_mes = {int(r['mes_vencimento']): D(str(r['valor'])) for r in inter_list}

        # Gerar tabela de amortização para primeiros 24 períodos
        from financeiro.models import Reajuste as _P
        juros_ciclo1 = get_juros_ciclo(1)
        preview_count = min(numero_parcelas, 24)

        if tipo_amortizacao == 'SAC':
            # Pré-calcular tabela SAC completa para os primeiros 24
            tabela_full = _P._calcular_sac_tabela(base_pmt, juros_ciclo1, numero_parcelas)
            tabela_preview = tabela_full[:preview_count]
            pmt_ref = tabela_full[0][0] if tabela_full else D('0')
        else:
            # Price: PMT constante para ciclo 1
            pmt_ref = _P._calcular_pmt(base_pmt, juros_ciclo1, numero_parcelas)
            tabela_preview = None  # calculado inline

        parcelas = []
        for i in range(1, preview_count + 1):
            ciclo = (i - 1) // prazo_reajuste + 1
            juros_ciclo = get_juros_ciclo(ciclo)
            venc = data_base + relativedelta(months=i - 1)
            try:
                venc = venc.replace(day=dia_vencimento)
            except ValueError:
                import calendar
                ultimo = calendar.monthrange(venc.year, venc.month)[1]
                venc = venc.replace(day=min(dia_vencimento, ultimo))

            if tipo_amortizacao == 'SAC':
                pmt_k, amort_k, juros_k = tabela_preview[i - 1]
            else:
                # Para Price: recalcula PMT se ciclo mudar (projeção aproximada)
                pmt_k = _P._calcular_pmt(base_pmt, juros_ciclo, numero_parcelas - (i - 1))
                amort_k = None
                juros_k = None

            parcelas.append({
                'numero': i,
                'ciclo': ciclo,
                'vencimento': venc.strftime('%d/%m/%Y'),
                'valor': float(pmt_k),
                'juros_mensal': float(juros_ciclo),
                'inicio_ciclo': (i - 1) % prazo_reajuste == 0 and i > 1,
                'intermediaria': float(inter_mes[i]) if i in inter_mes else None,
                'amortizacao': float(amort_k) if amort_k is not None else None,
                'juros_embutido': float(juros_k) if juros_k is not None else None,
            })

        return JsonResponse({
            'sucesso': True,
            'tipo_amortizacao': tipo_amortizacao,
            'pmt': float(pmt_ref),
            'valor_financiado': float(valor_financiado),
            'base_pmt': float(base_pmt),
            'total_parcelas': numero_parcelas,
            'preview_count': preview_count,
            'parcelas': parcelas,
        })

    except Exception as e:
        logger.exception("Erro ao calcular preview de parcelas: %s", e)
        return JsonResponse({'sucesso': False, 'erro': str(e)}, status=500)


# =============================================================================
# WIZARD — Contrato com Tabela Price + Intermediárias
# =============================================================================

def _gerar_numero_contrato():
    """Gera o próximo número de contrato no formato CTR-AAAA-NNNN."""
    from django.utils import timezone
    from contratos.models import Contrato
    ano = timezone.now().year
    prefix = f'CTR-{ano}-'
    ultimos = Contrato.objects.filter(
        numero_contrato__startswith=prefix
    ).values_list('numero_contrato', flat=True)
    seq = 1
    for n in ultimos:
        try:
            num = int(n[len(prefix):])
            if num >= seq:
                seq = num + 1
        except (ValueError, IndexError):
            pass
    return f'{prefix}{seq:04d}'


class ContratoWizardView(LoginRequiredMixin, View):
    """
    Wizard de 4 etapas para criar contratos com TabelaJuros escalante
    e intermediárias parametrizadas.

    Etapas:
      1. basico        — dados do contrato
      2. juros         — faixas de TabelaJurosContrato
      3. intermediarias — padrão (intervalo) ou manual
      4. preview       — confirmação + salvar
    """
    STEPS = ['basico', 'juros', 'intermediarias', 'preview']
    SESSION_KEY = 'wizard_contrato'

    def _session(self, request):
        return request.session.setdefault(self.SESSION_KEY, {})

    def _clear(self, request):
        request.session.pop(self.SESSION_KEY, None)
        request.session.modified = True

    def get(self, request, step='basico'):
        from .forms import (
            ContratoWizardBasicoForm,
            IntermediariaPadraoForm,
        )
        sess = self._session(request)

        if step == 'basico':
            initial = sess.get('basico', {})
            if not initial.get('numero_contrato'):
                initial = dict(initial)
                initial['numero_contrato'] = _gerar_numero_contrato()
            form = ContratoWizardBasicoForm(initial=initial)
            return render(request, 'contratos/wizard/step1_basico.html', {
                'form': form, 'step': step, 'step_num': 1,
            })

        elif step == 'juros':
            if 'basico' not in sess:
                return redirect('contratos:wizard', step='basico')
            juros_data = sess.get('juros', [{'ciclo_inicio': 1, 'ciclo_fim': 1, 'juros_mensal': '0.0000', 'observacoes': 'Ciclo 1 — isenção'}])
            prazo = sess['basico'].get('prazo_reajuste_meses', 12)
            return render(request, 'contratos/wizard/step2_juros.html', {
                'juros_rows': juros_data, 'step': step, 'step_num': 2,
                'basico': sess['basico'],
                'prazo_reajuste_meses': prazo,
            })

        elif step == 'intermediarias':
            if 'basico' not in sess:
                return redirect('contratos:wizard', step='basico')
            padrao_form = IntermediariaPadraoForm(initial=sess.get('intermediarias_padrao_initial', {'intervalo_meses': 6, 'mes_inicio': 6}))
            manual_rows = sess.get('intermediarias_manual', [])
            modo = sess.get('intermediarias_modo', 'padrao')
            return render(request, 'contratos/wizard/step3_intermediarias.html', {
                'padrao_form': padrao_form,
                'manual_rows': manual_rows,
                'modo': modo,
                'step': step, 'step_num': 3,
                'basico': sess['basico'],
            })

        elif step == 'preview':
            if 'basico' not in sess:
                return redirect('contratos:wizard', step='basico')
            resumo = self._calcular_resumo(sess)
            return render(request, 'contratos/wizard/step4_preview.html', {
                'resumo': resumo, 'step': step, 'step_num': 4,
                'sess': sess,
            })

        return redirect('contratos:wizard', step='basico')

    def post(self, request, step='basico'):
        from .forms import (
            ContratoWizardBasicoForm, TabelaJurosForm,
            IntermediariaPadraoForm, IntermediariaManualForm,
        )
        from django.db import transaction
        sess = self._session(request)

        if step == 'basico':
            form = ContratoWizardBasicoForm(request.POST)
            if form.is_valid():
                sess['basico'] = form.cleaned_data_serializable()
                request.session.modified = True
                return redirect('contratos:wizard', step='juros')
            return render(request, 'contratos/wizard/step1_basico.html', {
                'form': form, 'step': step, 'step_num': 1,
            })

        elif step == 'juros':
            # Parse juros rows from POST
            juros_rows = []
            errors = []
            try:
                count = max(0, int(request.POST.get('juros_count', 0)))
            except (ValueError, TypeError):
                count = 0
            for i in range(count):
                f = TabelaJurosForm({
                    'ciclo_inicio': request.POST.get(f'juros_{i}_ciclo_inicio'),
                    'ciclo_fim': request.POST.get(f'juros_{i}_ciclo_fim'),
                    'juros_mensal': request.POST.get(f'juros_{i}_juros_mensal'),
                    'observacoes': request.POST.get(f'juros_{i}_observacoes', ''),
                })
                if f.is_valid():
                    juros_rows.append({
                        'ciclo_inicio': f.cleaned_data['ciclo_inicio'],
                        'ciclo_fim': f.cleaned_data['ciclo_fim'],
                        'juros_mensal': str(f.cleaned_data['juros_mensal']),
                        'observacoes': f.cleaned_data['observacoes'],
                    })
                else:
                    errors.extend(f.errors.as_text().splitlines())

            if errors:
                messages.error(request, f'Erros nas faixas de juros: {"; ".join(errors[:3])}')
                return redirect('contratos:wizard', step='juros')

            sess['juros'] = juros_rows
            request.session.modified = True
            return redirect('contratos:wizard', step='intermediarias')

        elif step == 'intermediarias':
            modo = request.POST.get('modo', 'padrao')
            sess['intermediarias_modo'] = modo

            # Salva configuração de intermediárias na seção basico da sessão
            if 'basico' in sess:
                sess['basico']['intermediarias_reduzem_pmt'] = request.POST.get('intermediarias_reduzem_pmt') == 'on'
                sess['basico']['intermediarias_reajustadas'] = request.POST.get('intermediarias_reajustadas') == 'on'

            if modo == 'padrao':
                form = IntermediariaPadraoForm(request.POST)
                if form.is_valid():
                    sess['intermediarias_padrao_initial'] = {
                        'valor': str(form.cleaned_data['valor']),
                        'intervalo_meses': form.cleaned_data['intervalo_meses'],
                        'numero_ocorrencias': form.cleaned_data['numero_ocorrencias'],
                        'mes_inicio': form.cleaned_data['mes_inicio'],
                    }
                    sess['intermediarias_lista'] = form.gerar_intermediarias_serializable()
                    request.session.modified = True
                    return redirect('contratos:wizard', step='preview')
                padrao_form = form
                return render(request, 'contratos/wizard/step3_intermediarias.html', {
                    'padrao_form': padrao_form, 'manual_rows': [],
                    'modo': modo, 'step': step, 'step_num': 3, 'basico': sess.get('basico', {}),
                })

            elif modo == 'manual':
                try:
                    count = max(0, int(request.POST.get('inter_count', 0)))
                except (ValueError, TypeError):
                    count = 0
                lista = []
                errors = []
                for i in range(count):
                    f = IntermediariaManualForm({
                        'numero_sequencial': request.POST.get(f'inter_{i}_seq'),
                        'mes_vencimento': request.POST.get(f'inter_{i}_mes'),
                        'valor': request.POST.get(f'inter_{i}_valor'),
                    })
                    if f.is_valid():
                        lista.append({
                            'numero_sequencial': f.cleaned_data['numero_sequencial'],
                            'mes_vencimento': f.cleaned_data['mes_vencimento'],
                            'valor': str(f.cleaned_data['valor']),
                        })
                    else:
                        errors.extend(f.errors.as_text().splitlines())

                if errors:
                    messages.error(request, f'Erros nas intermediárias: {"; ".join(errors[:3])}')
                    return redirect('contratos:wizard', step='intermediarias')

                sess['intermediarias_lista'] = lista
                request.session.modified = True
                return redirect('contratos:wizard', step='preview')

            elif modo == 'nenhuma':
                sess['intermediarias_lista'] = []
                request.session.modified = True
                return redirect('contratos:wizard', step='preview')

        elif step == 'salvar':
            if 'basico' not in sess:
                return redirect('contratos:wizard', step='basico')

            try:
                with transaction.atomic():
                    contrato = self._salvar_contrato(request, sess)
                self._clear(request)
                messages.success(
                    request,
                    f'Contrato {contrato.numero_contrato} criado com sucesso! '
                    f'{contrato.parcelas.count()} parcelas geradas.'
                )
                return redirect('contratos:detalhe', pk=contrato.pk)
            except Exception as e:
                logger.exception('Erro ao salvar wizard: %s', e)
                messages.error(request, f'Erro ao criar contrato: {e}')
                return redirect('contratos:wizard', step='preview')

        return redirect('contratos:wizard', step='basico')

    def _calcular_resumo(self, sess):
        """Calcula o resumo financeiro do wizard para o step de preview"""
        from decimal import Decimal as D
        import json as _json

        def to_dec(val, default=0):
            if val is None:
                return D(str(default))
            try:
                return D(str(val))
            except Exception:
                return D(str(default))

        basico = sess.get('basico', {})
        juros_rows = sess.get('juros', [])
        intermediarias = sess.get('intermediarias_lista', [])

        valor_total = to_dec(basico.get('valor_total'), 0)
        valor_entrada = to_dec(basico.get('valor_entrada'), 0)
        numero_parcelas = int(basico.get('numero_parcelas') or 1)
        valor_financiado = valor_total - valor_entrada

        soma_intermediarias = sum(D(str(r['valor'])) for r in intermediarias)
        reduzem_pmt = basico.get('intermediarias_reduzem_pmt', False)
        tipo_amortizacao = basico.get('tipo_amortizacao', 'PRICE')

        if reduzem_pmt:
            base_pmt = max(valor_financiado - soma_intermediarias, D('0.01'))
        else:
            base_pmt = valor_financiado

        # Usar taxa do ciclo 1 se definida
        taxa_ciclo1 = D('0')
        for row in juros_rows:
            if int(row.get('ciclo_inicio') or 999) == 1:
                taxa_ciclo1 = to_dec(row.get('juros_mensal'), 0)
                break

        if numero_parcelas > 0:
            from financeiro.models import Reajuste as _P
            if tipo_amortizacao == 'SAC':
                # PMT do primeiro período SAC (o maior)
                tabela = _P._calcular_sac_tabela(base_pmt, taxa_ciclo1, numero_parcelas)
                pmt_ciclo1 = tabela[0][0] if tabela else D('0')
                pmt_ultimo = tabela[-1][0] if tabela else D('0')
            else:
                pmt_ciclo1 = _P._calcular_pmt(base_pmt, taxa_ciclo1, numero_parcelas)
                pmt_ultimo = pmt_ciclo1  # Price: PMT constante por ciclo
        else:
            pmt_ciclo1 = pmt_ultimo = D('0')

        intermediarias_preview = intermediarias[:12]
        return {
            'valor_total': valor_total,
            'valor_entrada': valor_entrada,
            'valor_financiado': valor_financiado,
            'numero_parcelas': numero_parcelas,
            'pmt_ciclo1': pmt_ciclo1,
            'pmt_ultimo': pmt_ultimo,
            'taxa_ciclo1': taxa_ciclo1,
            'tipo_amortizacao': tipo_amortizacao,
            'soma_intermediarias': soma_intermediarias,
            'n_intermediarias': len(intermediarias),
            'juros_rows': juros_rows,
            'juros_json': _json.dumps(juros_rows),
            'intermediarias': intermediarias_preview,
            'intermediarias_json': _json.dumps(intermediarias_preview),
            'intermediarias_total': len(intermediarias),
            'basico': basico,
            'reduzem_pmt': reduzem_pmt,
            'reajustadas': basico.get('intermediarias_reajustadas', True),
        }

    def _salvar_contrato(self, request, sess):
        """Cria o contrato com TabelaJuros e intermediárias em uma única transação"""
        from decimal import Decimal as D
        from contratos.models import TabelaJurosContrato, PrestacaoIntermediaria

        basico = sess['basico']
        # Reconstruct form from session data
        contrato = self._criar_contrato_from_session(basico)

        # TabelaJuros rows
        for row in sess.get('juros', []):
            TabelaJurosContrato.objects.create(
                contrato=contrato,
                ciclo_inicio=row['ciclo_inicio'],
                ciclo_fim=row.get('ciclo_fim'),
                juros_mensal=D(str(row['juros_mensal'])),
                observacoes=row.get('observacoes', ''),
            )

        # Intermediárias
        for row in sess.get('intermediarias_lista', []):
            PrestacaoIntermediaria.objects.create(
                contrato=contrato,
                numero_sequencial=row['numero_sequencial'],
                mes_vencimento=row['mes_vencimento'],
                valor=D(str(row['valor'])),
            )

        # Recalcula amortização (Price ou SAC) com base na TabelaJuros recém-criada.
        # Também trata intermediarias_reduzem_pmt.
        from django.db.models import Sum
        base_pv = contrato.valor_financiado
        if contrato.intermediarias_reduzem_pmt:
            soma = contrato.intermediarias.aggregate(total=Sum('valor'))['total'] or D('0')
            base_pv = max(base_pv - soma, D('0.01'))

        contrato.recalcular_amortizacao(base_pv=base_pv)

        return contrato

    def _criar_contrato_from_session(self, basico):
        """Creates a Contrato object from session data dict"""
        from contratos.models import Contrato
        from decimal import Decimal as D
        from datetime import date

        def to_date(v):
            if isinstance(v, date):
                return v
            if isinstance(v, str):
                from datetime import datetime
                for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
                    try:
                        return datetime.strptime(v, fmt).date()
                    except ValueError:
                        pass
            return v

        def to_dec(v):
            return D(str(v)) if v not in (None, '', 'None') else None

        contrato = Contrato.objects.create(
            imobiliaria_id=basico['imobiliaria'],
            imovel_id=basico['imovel'],
            comprador_id=basico['comprador'],
            numero_contrato=basico['numero_contrato'],
            data_contrato=to_date(basico['data_contrato']),
            data_primeiro_vencimento=to_date(basico['data_primeiro_vencimento']),
            valor_total=to_dec(basico['valor_total']),
            valor_entrada=to_dec(basico['valor_entrada']) or D('0'),
            numero_parcelas=int(basico['numero_parcelas']),
            dia_vencimento=int(basico['dia_vencimento']),
            percentual_juros_mora=to_dec(basico.get('percentual_juros_mora', '1.00')),
            percentual_multa=to_dec(basico.get('percentual_multa', '2.00')),
            tipo_correcao=basico.get('tipo_correcao', 'IPCA'),
            prazo_reajuste_meses=int(basico.get('prazo_reajuste_meses', 12)),
            tipo_correcao_fallback=basico.get('tipo_correcao_fallback', ''),
            spread_reajuste=to_dec(basico.get('spread_reajuste')),
            reajuste_piso=to_dec(basico.get('reajuste_piso')),
            reajuste_teto=to_dec(basico.get('reajuste_teto')),
            tipo_amortizacao=basico.get('tipo_amortizacao', 'PRICE'),
            intermediarias_reduzem_pmt=bool(basico.get('intermediarias_reduzem_pmt', False)),
            intermediarias_reajustadas=bool(basico.get('intermediarias_reajustadas', True)),
            percentual_fruicao=to_dec(basico.get('percentual_fruicao', '0.5000')),
            percentual_multa_rescisao_penal=to_dec(basico.get('percentual_multa_rescisao_penal', '10.0000')),
            percentual_multa_rescisao_adm=to_dec(basico.get('percentual_multa_rescisao_adm', '12.0000')),
            percentual_cessao=to_dec(basico.get('percentual_cessao', '3.0000')),
            status=basico.get('status', 'ATIVO'),
            observacoes=basico.get('observacoes', ''),
        )
        return contrato


# =============================================================================
# G-11: Cálculo de Rescisão
# =============================================================================

@login_required
def calcular_rescisao_view(request, pk):
    """
    Calcula o valor de devolução em caso de rescisão pelo comprador.
    GET: exibe formulário com data de rescisão.
    POST: processa cálculo e exibe resultado.
    """
    contrato = get_object_or_404(Contrato, pk=pk)

    from datetime import date as date_type
    resultado = None
    data_rescisao = None

    if request.method == 'POST':
        data_str = request.POST.get('data_rescisao', '')
        try:
            data_rescisao = date_type.fromisoformat(data_str) if data_str else date_type.today()
        except ValueError:
            data_rescisao = date_type.today()
        resultado = contrato.calcular_rescisao(data_rescisao)

    return render(request, 'contratos/calcular_rescisao.html', {
        'contrato': contrato,
        'resultado': resultado,
        'data_rescisao': data_rescisao,
    })


# =============================================================================
# G-12: Cálculo de Cessão de Direitos
# =============================================================================

@login_required
def calcular_cessao_view(request, pk):
    """
    Calcula a taxa de cessão de direitos.
    GET: exibe formulário com data de cessão.
    POST: processa cálculo e exibe resultado.
    """
    contrato = get_object_or_404(Contrato, pk=pk)

    from datetime import date as date_type
    resultado = None
    data_cessao = None

    if request.method == 'POST':
        data_str = request.POST.get('data_cessao', '')
        try:
            data_cessao = date_type.fromisoformat(data_str) if data_str else date_type.today()
        except ValueError:
            data_cessao = date_type.today()
        resultado = contrato.calcular_cessao(data_cessao)

    return render(request, 'contratos/calcular_cessao.html', {
        'contrato': contrato,
        'resultado': resultado,
        'data_cessao': data_cessao,
    })


# =============================================================================
# TabelaJurosContrato — CRUD inline (Q-04 / HU-360)
# Permite gerenciar juros escalantes diretamente na tela do contrato.
# =============================================================================


@login_required
@require_http_methods(["GET", "POST"])
def api_tabela_juros_contrato(request, pk):
    """
    GET  → retorna lista JSON das faixas de juros do contrato.
    POST → cria uma nova faixa (ciclo_inicio, ciclo_fim opcional, juros_mensal, observacoes).
    """
    contrato = get_object_or_404(Contrato, pk=pk)

    if request.method == 'GET':
        rows = list(
            contrato.tabela_juros.order_by('ciclo_inicio').values(
                'id', 'ciclo_inicio', 'ciclo_fim', 'juros_mensal', 'observacoes'
            )
        )
        for r in rows:
            r['juros_mensal'] = str(r['juros_mensal'])
        return JsonResponse({'sucesso': True, 'tabela': rows})

    # POST
    import json
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    try:
        ciclo_inicio = int(data.get('ciclo_inicio', 0))
        ciclo_fim_raw = data.get('ciclo_fim') or None
        ciclo_fim = int(ciclo_fim_raw) if ciclo_fim_raw else None
        from decimal import Decimal as D
        juros_mensal = D(str(data.get('juros_mensal', '0')))
        observacoes = str(data.get('observacoes', ''))[:200]
    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)}, status=400)

    if ciclo_inicio < 1:
        return JsonResponse({'sucesso': False, 'erro': 'ciclo_inicio deve ser >= 1'}, status=400)
    if ciclo_fim and ciclo_fim < ciclo_inicio:
        return JsonResponse({'sucesso': False, 'erro': 'ciclo_fim deve ser >= ciclo_inicio'}, status=400)

    entry = TabelaJurosContrato.objects.create(
        contrato=contrato,
        ciclo_inicio=ciclo_inicio,
        ciclo_fim=ciclo_fim,
        juros_mensal=juros_mensal,
        observacoes=observacoes,
    )
    return JsonResponse({
        'sucesso': True,
        'entry': {
            'id': entry.pk,
            'ciclo_inicio': entry.ciclo_inicio,
            'ciclo_fim': entry.ciclo_fim,
            'juros_mensal': str(entry.juros_mensal),
            'observacoes': entry.observacoes,
        }
    }, status=201)


@login_required
@require_http_methods(["DELETE"])
def api_tabela_juros_delete(request, pk):
    """DELETE → remove uma faixa de juros pelo ID.

    Recalcula amortização das parcelas após a remoção para manter
    consistência entre TabelaJurosContrato e valores das parcelas.
    Bloqueia se o contrato já possui reajustes aplicados (parcelas
    reajustadas não devem ser recalculadas retroativamente).
    """
    from financeiro.models import Reajuste
    entry = get_object_or_404(TabelaJurosContrato, pk=pk)
    contrato = entry.contrato

    # Guard: impede exclusão se reajuste já foi aplicado no contrato.
    # Recalcular amortização após reajustes aplicados corromperia os valores.
    if Reajuste.objects.filter(contrato=contrato, aplicado=True).exists():
        return JsonResponse({
            'sucesso': False,
            'erro': (
                'Não é possível excluir faixas de juros após reajustes terem sido aplicados. '
                'Os valores das parcelas já foram corrigidos e não podem ser recalculados retroativamente.'
            )
        }, status=400)

    entry.delete()

    # Recalcula amortização: se ainda há faixas, aplica PMT pela nova tabela;
    # se removeu todas as faixas, `get_juros_para_ciclo` retorna None e
    # recalcular_amortizacao() usa taxa=0 (amortização linear).
    if contrato.parcelas.exists():
        base_pv = contrato.valor_financiado
        if contrato.intermediarias_reduzem_pmt:
            soma = contrato.intermediarias.aggregate(
                total=Sum('valor')
            )['total'] or Decimal('0')
            base_pv = max(base_pv - soma, Decimal('0.01'))
        contrato.recalcular_amortizacao(base_pv=base_pv)

    return JsonResponse({'sucesso': True})
