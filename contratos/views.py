"""
Views do app Contratos

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import models
from django.db.models import Q, Sum, Count
from .models import Contrato, StatusContrato, IndiceReajuste
from .forms import ContratoForm, IndiceReajusteForm
import requests
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
from datetime import datetime
from decimal import Decimal


class ContratoListView(LoginRequiredMixin, ListView):
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
            if (proxima_data_reajuste.year < hoje.year or
                (proxima_data_reajuste.year == hoje.year and proxima_data_reajuste.month <= hoje.month)):

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
        from financeiro.models import Reajuste
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
            context['intermediarias'] = contrato.intermediarias.all().order_by('numero_sequencial')
            context['total_intermediarias'] = contrato.intermediarias.count()
            context['intermediarias_pagas'] = contrato.intermediarias.filter(paga=True).count()
            context['intermediarias_pendentes'] = contrato.intermediarias.filter(paga=False).count()
        else:
            context['intermediarias'] = []
            context['total_intermediarias'] = 0
            context['intermediarias_pagas'] = 0
            context['intermediarias_pendentes'] = 0

        # =====================================================================
        # CONTROLE DE BLOQUEIO DE BOLETO POR REAJUSTE
        # =====================================================================
        if hasattr(contrato, 'verificar_bloqueio_reajuste'):
            bloqueio_info = contrato.verificar_bloqueio_reajuste()
            context['bloqueio_reajuste'] = bloqueio_info
        else:
            context['bloqueio_reajuste'] = {
                'bloqueado': False,
                'motivo': '',
                'ciclo_atual': 1,
                'ciclo_pendente': None,
            }

        # Verificar status de cada parcela para geração de boleto
        parcelas_status_boleto = []
        for parcela in context['parcelas']:
            if hasattr(contrato, 'pode_gerar_boleto'):
                pode_gerar, motivo = contrato.pode_gerar_boleto(parcela.numero_parcela)
            else:
                pode_gerar, motivo = True, "Liberado"
            parcelas_status_boleto.append({
                'parcela': parcela,
                'pode_gerar_boleto': pode_gerar,
                'motivo_bloqueio': motivo if not pode_gerar else '',
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


# ==============================================================
# CRUD de Índices de Reajuste
# ==============================================================

class IndiceReajusteListView(LoginRequiredMixin, ListView):
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
            return JsonResponse({'success': False, 'error': 'Tipo de índice inválido'})

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
        return JsonResponse({'success': False, 'error': str(e)})


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
        print(f"Erro ao buscar IPCA: {e}")

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
            dia = int(partes[0])
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
        print(f"Erro ao buscar IGP-M: {e}")

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
            dia = int(partes[0])
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
        print(f"Erro ao buscar SELIC: {e}")

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
        print(f"Erro ao buscar INCC: {e}")

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
        print(f"Erro ao buscar IGP-DI: {e}")

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
        print(f"Erro ao buscar INPC: {e}")

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
        print(f"Erro ao buscar TR: {e}")

    return indices


# ==============================================================
# CRUD de Prestações Intermediárias
# ==============================================================

from .models import PrestacaoIntermediaria
from django.http import HttpResponseRedirect


class IntermediariasListView(LoginRequiredMixin, ListView):
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


@login_required
@require_http_methods(["POST"])
def criar_intermediaria(request, contrato_id):
    """Cria uma nova prestação intermediária para um contrato"""
    contrato = get_object_or_404(Contrato, pk=contrato_id)

    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST

        # Validar quantidade máxima de intermediárias
        qtd_atual = contrato.intermediarias.count() if hasattr(contrato, 'intermediarias') else 0
        max_intermediarias = getattr(contrato, 'quantidade_intermediarias', 30)

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
        if 'valor' in data:
            intermediaria.valor = Decimal(str(data['valor']))
        if 'observacoes' in data:
            intermediaria.observacoes = data['observacoes']

        intermediaria.save()

        return JsonResponse({
            'sucesso': True,
            'mensagem': 'Prestação intermediária atualizada com sucesso'
        })

    except Exception as e:
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
        contrato_id = intermediaria.contrato_id
        numero = intermediaria.numero_sequencial
        intermediaria.delete()

        return JsonResponse({
            'sucesso': True,
            'mensagem': f'Prestação intermediária #{numero} excluída com sucesso',
            'redirect': f'/contratos/{contrato_id}/intermediarias/'
        })

    except Exception as e:
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

        return JsonResponse({
            'sucesso': True,
            'mensagem': f'Pagamento de R$ {valor_pago:,.2f} registrado com sucesso',
            'intermediaria_id': intermediaria.id
        })

    except Exception as e:
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

    # Verificar bloqueio por reajuste
    force = request.POST.get('force', 'false').lower() == 'true'
    if not force and hasattr(contrato, 'pode_gerar_boleto'):
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

        # Criar parcela vinculada
        parcela = Parcela.objects.create(
            contrato=contrato,
            numero_parcela=intermediaria.mes_vencimento,
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
                }, status=500)
        else:
            return JsonResponse({
                'sucesso': True,
                'mensagem': 'Parcela criada. Configure uma conta bancária para gerar o boleto.',
                'parcela_id': parcela.id
            })

    except Exception as e:
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
