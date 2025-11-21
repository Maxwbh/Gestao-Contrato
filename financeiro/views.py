"""
Views do app Financeiro

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Parcela, Reajuste


@login_required
def listar_parcelas(request):
    """Lista todas as parcelas"""
    parcelas = Parcela.objects.select_related(
        'contrato',
        'contrato__comprador',
        'contrato__imovel'
    ).all()

    # Filtros
    status = request.GET.get('status')
    if status == 'pagas':
        parcelas = parcelas.filter(pago=True)
    elif status == 'pendentes':
        parcelas = parcelas.filter(pago=False)
    elif status == 'vencidas':
        parcelas = parcelas.filter(pago=False, data_vencimento__lt=timezone.now().date())

    context = {
        'parcelas': parcelas,
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
