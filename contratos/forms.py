"""
Formulários do app Contratos

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django import forms
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Row, Column, HTML, Div
from .models import Contrato, TipoCorrecao, StatusContrato
from core.models import Imovel, Comprador, Imobiliaria


class ContratoForm(forms.ModelForm):
    """Formulário para cadastro de Contrato"""

    class Meta:
        model = Contrato
        fields = [
            'imobiliaria', 'imovel', 'comprador',
            'numero_contrato', 'data_contrato', 'data_primeiro_vencimento',
            'valor_total', 'valor_entrada',
            'numero_parcelas', 'dia_vencimento',
            'percentual_juros_mora', 'percentual_multa',
            'tipo_correcao', 'prazo_reajuste_meses',
            'status', 'observacoes'
        ]
        widgets = {
            'data_contrato': forms.DateInput(
                attrs={'type': 'date'},
                format='%Y-%m-%d'
            ),
            'data_primeiro_vencimento': forms.DateInput(
                attrs={'type': 'date'},
                format='%Y-%m-%d'
            ),
            'valor_total': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0,00'
            }),
            'valor_entrada': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0',
                'placeholder': '0,00'
            }),
            'numero_parcelas': forms.NumberInput(attrs={
                'min': '1',
                'max': '600',
                'placeholder': 'Ex: 120'
            }),
            'dia_vencimento': forms.NumberInput(attrs={
                'min': '1',
                'max': '31',
                'placeholder': 'Ex: 10'
            }),
            'percentual_juros_mora': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0',
                'max': '100',
                'placeholder': '1,00'
            }),
            'percentual_multa': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0',
                'max': '100',
                'placeholder': '2,00'
            }),
            'prazo_reajuste_meses': forms.NumberInput(attrs={
                'min': '1',
                'max': '120',
                'placeholder': '12'
            }),
            'observacoes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Observações adicionais sobre o contrato...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Adicionar classes Bootstrap
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                if isinstance(field.widget, forms.Select):
                    field.widget.attrs['class'] = 'form-select'
                elif isinstance(field.widget, forms.CheckboxInput):
                    field.widget.attrs['class'] = 'form-check-input'
                else:
                    field.widget.attrs['class'] = 'form-control'

        # Filtrar apenas imóveis disponíveis (ou o imóvel atual se editando)
        if self.instance and self.instance.pk:
            self.fields['imovel'].queryset = Imovel.objects.filter(
                Q(disponivel=True, ativo=True) |
                Q(pk=self.instance.imovel_id)
            )
        else:
            self.fields['imovel'].queryset = Imovel.objects.filter(
                disponivel=True, ativo=True
            )

        # Filtrar apenas compradores e imobiliárias ativos
        self.fields['comprador'].queryset = Comprador.objects.filter(ativo=True)
        self.fields['imobiliaria'].queryset = Imobiliaria.objects.filter(ativo=True)

        # Se for edição, desabilitar campos que não devem ser alterados
        if self.instance and self.instance.pk:
            self.fields['numero_parcelas'].disabled = True
            self.fields['numero_parcelas'].help_text = 'Não é possível alterar após criação'
            self.fields['valor_total'].disabled = True
            self.fields['valor_total'].help_text = 'Não é possível alterar após criação'
            self.fields['valor_entrada'].disabled = True
            self.fields['valor_entrada'].help_text = 'Não é possível alterar após criação'

    def clean(self):
        cleaned_data = super().clean()
        valor_total = cleaned_data.get('valor_total')
        valor_entrada = cleaned_data.get('valor_entrada')

        if valor_total and valor_entrada:
            if valor_entrada >= valor_total:
                raise forms.ValidationError({
                    'valor_entrada': 'O valor de entrada deve ser menor que o valor total.'
                })

        return cleaned_data
