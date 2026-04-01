"""
Formulários do app Contratos

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django import forms
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Row, Column, HTML, Div
from decimal import Decimal
from .models import Contrato, TipoCorrecao, StatusContrato, IndiceReajuste
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

        # Se for edicao, desabilitar campos que nao devem ser alterados
        if self.instance and self.instance.pk:
            self.fields['numero_parcelas'].disabled = True
            self.fields['numero_parcelas'].help_text = 'Nao e possivel alterar apos criacao'
            self.fields['valor_total'].disabled = True
            self.fields['valor_total'].help_text = 'Nao e possivel alterar apos criacao'
            self.fields['valor_entrada'].disabled = True
            self.fields['valor_entrada'].help_text = 'Nao e possivel alterar apos criacao'

        # Layout crispy forms
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            # Legenda
            HTML('''
                <div class="legenda-campos">
                    <i class="fas fa-info-circle me-1"></i>
                    <span class="obrigatorio">* Campos obrigatorios</span>
                    <span class="ms-3 opcional">Demais campos sao opcionais</span>
                </div>
            '''),

            # Card: Partes do Contrato (Obrigatorio)
            HTML('''
                <div class="card mb-3 card-obrigatorio">
                    <div class="card-header py-2">
                        <i class="fas fa-users me-2"></i><strong>Partes do Contrato</strong>
                    </div>
                    <div class="card-body py-3">
            '''),
            Row(
                Column(Field('imobiliaria', wrapper_class='mb-2 campo-obrigatorio'), css_class='col-md-4'),
                Column(Field('comprador', wrapper_class='mb-2 campo-obrigatorio'), css_class='col-md-4'),
                Column(Field('imovel', wrapper_class='mb-2 campo-obrigatorio'), css_class='col-md-4'),
            ),
            HTML('</div></div>'),

            # Card: Dados do Contrato (Obrigatorio)
            HTML('''
                <div class="card mb-3 card-obrigatorio">
                    <div class="card-header py-2">
                        <i class="fas fa-file-alt me-2"></i><strong>Dados do Contrato</strong>
                    </div>
                    <div class="card-body py-3">
            '''),
            Row(
                Column(Field('numero_contrato', wrapper_class='mb-2 campo-obrigatorio'), css_class='col-md-4'),
                Column(Field('data_contrato', wrapper_class='mb-2 campo-obrigatorio'), css_class='col-md-4'),
                Column(Field('status', wrapper_class='mb-2'), css_class='col-md-4'),
            ),
            HTML('</div></div>'),

            # Card: Valores (Obrigatorio)
            HTML('''
                <div class="card mb-3 card-obrigatorio">
                    <div class="card-header py-2">
                        <i class="fas fa-dollar-sign me-2"></i><strong>Valores</strong>
                    </div>
                    <div class="card-body py-3">
            '''),
            Row(
                Column(Field('valor_total', wrapper_class='mb-2 campo-obrigatorio'), css_class='col-md-6'),
                Column(Field('valor_entrada', wrapper_class='mb-2'), css_class='col-md-6'),
            ),
            HTML('</div></div>'),

            # Card: Parcelas (Obrigatorio)
            HTML('''
                <div class="card mb-3 card-obrigatorio">
                    <div class="card-header py-2">
                        <i class="fas fa-calendar-alt me-2"></i><strong>Configuracao de Parcelas</strong>
                    </div>
                    <div class="card-body py-3">
            '''),
            Row(
                Column(Field('numero_parcelas', wrapper_class='mb-2 campo-obrigatorio'), css_class='col-md-3'),
                Column(Field('dia_vencimento', wrapper_class='mb-2 campo-obrigatorio'), css_class='col-md-3'),
                Column(Field('data_primeiro_vencimento', wrapper_class='mb-2 campo-obrigatorio'), css_class='col-md-6'),
            ),
            HTML('</div></div>'),

            # Card: Juros e Multa (Opcional)
            HTML('''
                <div class="card mb-3 card-opcional">
                    <div class="card-header py-2">
                        <i class="fas fa-percentage me-2"></i><strong>Juros e Multa por Atraso</strong>
                    </div>
                    <div class="card-body py-3">
            '''),
            Row(
                Column(Field('percentual_juros_mora', wrapper_class='mb-2'), css_class='col-md-6'),
                Column(Field('percentual_multa', wrapper_class='mb-2'), css_class='col-md-6'),
            ),
            HTML('</div></div>'),

            # Card: Correcao Monetaria (Opcional)
            HTML('''
                <div class="card mb-3 card-opcional">
                    <div class="card-header py-2">
                        <i class="fas fa-chart-line me-2"></i><strong>Correcao Monetaria</strong>
                    </div>
                    <div class="card-body py-3">
            '''),
            Row(
                Column(Field('tipo_correcao', wrapper_class='mb-2'), css_class='col-md-6'),
                Column(Field('prazo_reajuste_meses', wrapper_class='mb-2'), css_class='col-md-6'),
            ),
            HTML('</div></div>'),

            # Card: Observacoes (Opcional)
            HTML('''
                <div class="card mb-3 card-opcional">
                    <div class="card-header py-2">
                        <i class="fas fa-sticky-note me-2"></i><strong>Observacoes</strong>
                    </div>
                    <div class="card-body py-3">
            '''),
            Field('observacoes', wrapper_class='mb-0'),
            HTML('</div></div>'),

            # Botoes
            HTML('''
                <div class="d-flex justify-content-between align-items-center mt-4 pt-3 border-top">
                    <a href="{% url 'contratos:listar' %}" class="btn btn-outline-secondary">
                        <i class="fas fa-arrow-left me-2"></i>Voltar
                    </a>
                    <button type="submit" class="btn btn-primary btn-lg px-5">
                        <i class="fas fa-save me-2"></i>Salvar Contrato
                    </button>
                </div>
            ''')
        )

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


class IndiceReajusteForm(forms.ModelForm):
    """Formulário para cadastro de Índice de Reajuste"""

    class Meta:
        model = IndiceReajuste
        fields = ['tipo_indice', 'ano', 'mes', 'valor', 'valor_acumulado_ano',
                  'valor_acumulado_12m', 'fonte']
        widgets = {
            'ano': forms.NumberInput(attrs={
                'min': '1990',
                'max': '2100',
                'placeholder': 'Ex: 2024'
            }),
            'tipo_indice': forms.Select(choices=[
                ('IPCA', 'IPCA - Índice de Preços ao Consumidor Amplo'),
                ('IGPM', 'IGP-M - Índice Geral de Preços do Mercado'),
                ('INCC', 'INCC - Índice Nacional de Custo da Construção'),
                ('IGPDI', 'IGP-DI - Índice Geral de Preços - Disponibilidade Interna'),
                ('INPC', 'INPC - Índice Nacional de Preços ao Consumidor'),
                ('TR', 'TR - Taxa Referencial'),
                ('SELIC', 'SELIC - Taxa Básica de Juros'),
            ]),
            'mes': forms.Select(choices=[
                (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'),
                (4, 'Abril'), (5, 'Maio'), (6, 'Junho'),
                (7, 'Julho'), (8, 'Agosto'), (9, 'Setembro'),
                (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro'),
            ]),
            'valor': forms.NumberInput(attrs={
                'step': '0.0001',
                'placeholder': 'Ex: 0.5200'
            }),
            'valor_acumulado_ano': forms.NumberInput(attrs={
                'step': '0.0001',
                'placeholder': 'Ex: 3.2100'
            }),
            'valor_acumulado_12m': forms.NumberInput(attrs={
                'step': '0.0001',
                'placeholder': 'Ex: 4.6200'
            }),
            'fonte': forms.TextInput(attrs={
                'placeholder': 'Ex: IBGE, BCB, FGV'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Adicionar classes Bootstrap
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                if isinstance(field.widget, forms.Select):
                    field.widget.attrs['class'] = 'form-select'
                else:
                    field.widget.attrs['class'] = 'form-control'

        # Layout crispy forms
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            # Card: Dados do Índice (Obrigatório)
            HTML('''
                <div class="card mb-3 card-obrigatorio">
                    <div class="card-header py-2">
                        <i class="fas fa-chart-line me-2"></i><strong>Dados do Indice</strong>
                    </div>
                    <div class="card-body py-3">
            '''),
            Row(
                Column(Field('tipo_indice', wrapper_class='mb-2 campo-obrigatorio'), css_class='col-md-4'),
                Column(Field('ano', wrapper_class='mb-2 campo-obrigatorio'), css_class='col-md-4'),
                Column(Field('mes', wrapper_class='mb-2 campo-obrigatorio'), css_class='col-md-4'),
            ),
            Row(
                Column(Field('valor', wrapper_class='mb-2 campo-obrigatorio'), css_class='col-md-4'),
                Column(Field('valor_acumulado_ano', wrapper_class='mb-2'), css_class='col-md-4'),
                Column(Field('valor_acumulado_12m', wrapper_class='mb-2'), css_class='col-md-4'),
            ),
            HTML('</div></div>'),

            # Card: Fonte (Opcional)
            HTML('''
                <div class="card mb-3 card-opcional">
                    <div class="card-header py-2">
                        <i class="fas fa-info-circle me-2"></i><strong>Informacoes Adicionais</strong>
                    </div>
                    <div class="card-body py-3">
            '''),
            Field('fonte', wrapper_class='mb-0'),
            HTML('</div></div>'),

            # Botoes
            HTML('''
                <div class="d-flex justify-content-between align-items-center mt-4 pt-3 border-top">
                    <a href="{% url 'contratos:indices_listar' %}" class="btn btn-outline-secondary">
                        <i class="fas fa-arrow-left me-2"></i>Voltar
                    </a>
                    <button type="submit" class="btn btn-primary btn-lg px-5">
                        <i class="fas fa-save me-2"></i>Salvar Indice
                    </button>
                </div>
            ''')
        )

    def clean(self):
        cleaned_data = super().clean()
        tipo_indice = cleaned_data.get('tipo_indice')
        ano = cleaned_data.get('ano')
        mes = cleaned_data.get('mes')

        # Verificar duplicidade (exceto na edição)
        if tipo_indice and ano and mes:
            qs = IndiceReajuste.objects.filter(
                tipo_indice=tipo_indice,
                ano=ano,
                mes=mes
            )
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError(
                    f'Já existe um índice {tipo_indice} cadastrado para {mes:02d}/{ano}.'
                )

        return cleaned_data


# =============================================================================
# WIZARD — Contrato com Tabela Price + Intermediárias
# =============================================================================

class ContratoWizardBasicoForm(forms.ModelForm):
    """Wizard Step 1: Dados básicos do contrato"""

    class Meta:
        model = Contrato
        fields = [
            'imobiliaria', 'imovel', 'comprador',
            'numero_contrato', 'data_contrato', 'data_primeiro_vencimento',
            'valor_total', 'valor_entrada',
            'numero_parcelas', 'dia_vencimento',
            'percentual_juros_mora', 'percentual_multa',
            'tipo_correcao', 'prazo_reajuste_meses', 'tipo_correcao_fallback',
            'spread_reajuste', 'reajuste_piso', 'reajuste_teto',
            'intermediarias_reduzem_pmt', 'intermediarias_reajustadas',
            'percentual_fruicao', 'percentual_multa_rescisao_penal',
            'percentual_multa_rescisao_adm', 'percentual_cessao',
            'observacoes',
        ]
        widgets = {
            'data_contrato': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'data_primeiro_vencimento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'valor_total': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'placeholder': '350000,00'}),
            'valor_entrada': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': '100000,00'}),
            'numero_parcelas': forms.NumberInput(attrs={'min': '1', 'max': '600', 'placeholder': '360'}),
            'dia_vencimento': forms.NumberInput(attrs={'min': '1', 'max': '28', 'placeholder': '10'}),
            'percentual_juros_mora': forms.NumberInput(attrs={'step': '0.01', 'placeholder': '1,00'}),
            'percentual_multa': forms.NumberInput(attrs={'step': '0.01', 'placeholder': '2,00'}),
            'prazo_reajuste_meses': forms.NumberInput(attrs={'min': '1', 'max': '120', 'placeholder': '12'}),
            'spread_reajuste': forms.NumberInput(attrs={'step': '0.0001', 'placeholder': '0,0000'}),
            'reajuste_piso': forms.NumberInput(attrs={'step': '0.0001', 'placeholder': 'Ex: 0,0000'}),
            'reajuste_teto': forms.NumberInput(attrs={'step': '0.0001', 'placeholder': 'Ex: 15,0000'}),
            'percentual_fruicao': forms.NumberInput(attrs={'step': '0.0001', 'placeholder': '0,5000'}),
            'percentual_multa_rescisao_penal': forms.NumberInput(attrs={'step': '0.0001', 'placeholder': '10,0000'}),
            'percentual_multa_rescisao_adm': forms.NumberInput(attrs={'step': '0.0001', 'placeholder': '12,0000'}),
            'percentual_cessao': forms.NumberInput(attrs={'step': '0.0001', 'placeholder': '3,0000'}),
            'observacoes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                if isinstance(field.widget, forms.Select):
                    field.widget.attrs['class'] = 'form-select'
                elif isinstance(field.widget, forms.CheckboxInput):
                    field.widget.attrs['class'] = 'form-check-input'
                else:
                    field.widget.attrs['class'] = 'form-control'
        self.fields['imovel'].queryset = Imovel.objects.filter(disponivel=True, ativo=True)
        self.fields['comprador'].queryset = Comprador.objects.filter(ativo=True)
        self.fields['imobiliaria'].queryset = Imobiliaria.objects.filter(ativo=True)

    def clean(self):
        cleaned_data = super().clean()
        valor_total = cleaned_data.get('valor_total')
        valor_entrada = cleaned_data.get('valor_entrada')
        if valor_total and valor_entrada and valor_entrada >= valor_total:
            raise forms.ValidationError({'valor_entrada': 'O valor de entrada deve ser menor que o valor total.'})
        return cleaned_data

    def cleaned_data_serializable(self):
        """Returns cleaned_data with all values serialized for JSON session storage"""
        from datetime import date
        data = {}
        for k, v in self.cleaned_data.items():
            if isinstance(v, Decimal):
                data[k] = str(v)
            elif isinstance(v, date):
                data[k] = v.isoformat()
            elif hasattr(v, 'pk'):  # FK / model instance
                data[k] = v.pk
            elif v is None:
                data[k] = None
            else:
                data[k] = v
        return data


class TabelaJurosForm(forms.Form):
    """Linha de TabelaJurosContrato no wizard step 2"""
    ciclo_inicio = forms.IntegerField(
        min_value=1, max_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '1'}),
        label='Ciclo Início'
    )
    ciclo_fim = forms.IntegerField(
        min_value=1, max_value=100, required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '1', 'placeholder': '(em aberto)'}),
        label='Ciclo Fim'
    )
    juros_mensal = forms.DecimalField(
        max_digits=8, decimal_places=4,
        min_value=0, max_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.0001', 'placeholder': '0,6000'}),
        label='Taxa Mensal (%)'
    )
    observacoes = forms.CharField(
        required=False, max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Opcional'}),
        label='Observações'
    )

    def clean(self):
        cleaned_data = super().clean()
        inicio = cleaned_data.get('ciclo_inicio')
        fim = cleaned_data.get('ciclo_fim')
        if inicio and fim and fim < inicio:
            raise forms.ValidationError('Ciclo Fim deve ser maior ou igual ao Ciclo Início.')
        return cleaned_data


class IntermediariaPadraoForm(forms.Form):
    """Criação de intermediárias por padrão (valor + intervalo + count)"""
    valor = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '5000,00'}),
        label='Valor (R$)'
    )
    intervalo_meses = forms.IntegerField(
        min_value=1, max_value=360,
        initial=6,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': '6'}),
        label='Intervalo (meses)'
    )
    numero_ocorrencias = forms.IntegerField(
        min_value=1, max_value=60,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': '60'}),
        label='Número de Ocorrências'
    )
    mes_inicio = forms.IntegerField(
        min_value=1, max_value=360,
        initial=6,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': '6'}),
        label='Mês do Primeiro Vencimento'
    )

    def gerar_intermediarias(self):
        """Retorna lista de dicts {numero_sequencial, mes_vencimento, valor}"""
        valor = self.cleaned_data['valor']
        intervalo = self.cleaned_data['intervalo_meses']
        count = self.cleaned_data['numero_ocorrencias']
        mes_inicio = self.cleaned_data['mes_inicio']
        resultado = []
        for i in range(count):
            mes = mes_inicio + i * intervalo
            resultado.append({
                'numero_sequencial': i + 1,
                'mes_vencimento': mes,
                'valor': valor,
            })
        return resultado

    def gerar_intermediarias_serializable(self):
        """Same as gerar_intermediarias but values are JSON-serializable"""
        rows = self.gerar_intermediarias()
        return [
            {'numero_sequencial': r['numero_sequencial'],
             'mes_vencimento': r['mes_vencimento'],
             'valor': str(r['valor'])}
            for r in rows
        ]


class IntermediariaManualForm(forms.Form):
    """Linha individual de intermediária (modo manual)"""
    numero_sequencial = forms.IntegerField(
        min_value=1, max_value=60,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '1'}),
        label='Seq.'
    )
    mes_vencimento = forms.IntegerField(
        min_value=1, max_value=360,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '1'}),
        label='Mês'
    )
    valor = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01'}),
        label='Valor (R$)'
    )
