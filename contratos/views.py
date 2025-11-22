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
from django.db.models import Q, Sum, Count
from .models import Contrato, StatusContrato, IndiceReajuste
from .forms import ContratoForm, IndiceReajusteForm
import requests
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
from datetime import datetime


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

        context['progresso'] = contrato.calcular_progresso()
        context['valor_pago'] = contrato.calcular_valor_pago()
        context['saldo_devedor'] = contrato.calcular_saldo_devedor()

        # Parcelas
        context['parcelas'] = contrato.parcelas.all().order_by('numero_parcela')
        context['parcelas_pagas'] = contrato.parcelas.filter(pago=True).count()
        context['parcelas_pendentes'] = contrato.parcelas.filter(pago=False).count()

        # Próxima parcela a vencer
        from django.utils import timezone
        context['proxima_parcela'] = contrato.parcelas.filter(
            pago=False,
            data_vencimento__gte=timezone.now().date()
        ).order_by('data_vencimento').first()

        # Parcelas em atraso
        context['parcelas_atrasadas'] = contrato.parcelas.filter(
            pago=False,
            data_vencimento__lt=timezone.now().date()
        ).count()

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

        # Estatísticas por tipo
        tipos = ['IPCA', 'IGPM', 'INCC', 'IGPDI', 'INPC', 'TR', 'SELIC']
        context['estatisticas_indices'] = []
        for tipo in tipos:
            total = IndiceReajuste.objects.filter(tipo_indice=tipo).count()
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

        # Salvar índices no banco
        count_created = 0
        count_updated = 0
        for indice_data in indices:
            obj, created = IndiceReajuste.objects.update_or_create(
                tipo_indice=tipo_indice,
                ano=indice_data['ano'],
                mes=indice_data['mes'],
                defaults={
                    'valor': indice_data['valor'],
                    'valor_acumulado_ano': indice_data.get('acumulado_ano'),
                    'valor_acumulado_12m': indice_data.get('acumulado_12m'),
                    'fonte': indice_data.get('fonte', 'API'),
                    'data_importacao': datetime.now(),
                }
            )
            if created:
                count_created += 1
            else:
                count_updated += 1

        return JsonResponse({
            'success': True,
            'message': f'Importação concluída! {count_created} novos, {count_updated} atualizados.',
            'created': count_created,
            'updated': count_updated
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
