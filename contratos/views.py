"""
Views do app Contratos

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Contrato


@login_required
def listar_contratos(request):
    """Lista todos os contratos"""
    contratos = Contrato.objects.select_related(
        'imovel',
        'comprador',
        'imobiliaria'
    ).all()

    context = {
        'contratos': contratos,
    }
    return render(request, 'contratos/listar.html', context)


@login_required
def detalhe_contrato(request, pk):
    """Exibe detalhes de um contrato específico"""
    contrato = get_object_or_404(
        Contrato.objects.select_related(
            'imovel',
            'comprador',
            'imobiliaria'
        ),
        pk=pk
    )

    context = {
        'contrato': contrato,
        'progresso': contrato.calcular_progresso(),
        'valor_pago': contrato.calcular_valor_pago(),
        'saldo_devedor': contrato.calcular_saldo_devedor(),
    }
    return render(request, 'contratos/detalhe.html', context)


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
