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
from .models import Contrato, StatusContrato
from .forms import ContratoForm


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

        return context


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
