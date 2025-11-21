"""
Formulários do app Core

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django import forms
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div, HTML
from crispy_forms.bootstrap import PrependedText, AppendedText
from .models import Contabilidade, Imobiliaria, Imovel, Comprador, TipoImovel
import re


class CompradorForm(forms.ModelForm):
    """Formulário para cadastro de Comprador"""

    class Meta:
        model = Comprador
        fields = [
            'tipo_pessoa',
            # Campos PF
            'nome', 'cpf', 'rg', 'data_nascimento', 'estado_civil', 'profissao',
            # Campos PJ
            'cnpj', 'nome_fantasia', 'inscricao_estadual', 'inscricao_municipal',
            'responsavel_legal', 'responsavel_cpf',
            # Endereço (ambos)
            'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado',
            # Contato (ambos)
            'telefone', 'celular', 'email',
            'notificar_email', 'notificar_sms', 'notificar_whatsapp',
            # Cônjuge (apenas PF)
            'conjuge_nome', 'conjuge_cpf', 'conjuge_rg',
            # Observações
            'observacoes'
        ]
        widgets = {
            'data_nascimento': forms.DateInput(attrs={'type': 'date'}),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
            'cep': forms.TextInput(attrs={
                'placeholder': '99999-999',
                'data-viacep': 'true',
                'class': 'cep-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            HTML('<h4 class="mb-3"><i class="fas fa-id-card"></i> Tipo de Cadastro</h4>'),
            HTML('<p class="alert alert-info"><i class="fas fa-info-circle"></i> Selecione se o comprador é Pessoa Física ou Pessoa Jurídica</p>'),
            'tipo_pessoa',

            # Seção Pessoa Física
            HTML('''
                <div id="secao-pf" class="secao-tipo-pessoa">
                    <h4 class="mt-4 mb-3"><i class="fas fa-user"></i> Dados Pessoais (Pessoa Física)</h4>
                </div>
            '''),
            Div(
                Row(
                    Column('nome', css_class='form-group col-md-8'),
                    Column('cpf', css_class='form-group col-md-4'),
                ),
                Row(
                    Column('rg', css_class='form-group col-md-4'),
                    Column('data_nascimento', css_class='form-group col-md-4'),
                    Column('estado_civil', css_class='form-group col-md-4'),
                ),
                'profissao',
                css_class='campos-pf'
            ),

            # Seção Pessoa Jurídica
            HTML('''
                <div id="secao-pj" class="secao-tipo-pessoa" style="display:none;">
                    <h4 class="mt-4 mb-3"><i class="fas fa-building"></i> Dados da Empresa (Pessoa Jurídica)</h4>
                </div>
            '''),
            Div(
                Row(
                    Column('nome', css_class='form-group col-md-8 label-razao-social'),
                    Column('cnpj', css_class='form-group col-md-4'),
                ),
                Row(
                    Column('nome_fantasia', css_class='form-group col-md-6'),
                    Column('inscricao_estadual', css_class='form-group col-md-3'),
                    Column('inscricao_municipal', css_class='form-group col-md-3'),
                ),
                Row(
                    Column('responsavel_legal', css_class='form-group col-md-8'),
                    Column('responsavel_cpf', css_class='form-group col-md-4'),
                ),
                css_class='campos-pj',
                style='display:none;'
            ),

            HTML('<h4 class="mt-4 mb-3"><i class="fas fa-map-marker-alt"></i> Endereço</h4>'),
            HTML('<p class="text-muted"><i class="fas fa-info-circle"></i> Digite o CEP e o endereço será preenchido automaticamente via ViaCEP</p>'),
            Row(
                Column('cep', css_class='form-group col-md-3'),
                Column('logradouro', css_class='form-group col-md-7'),
                Column('numero', css_class='form-group col-md-2'),
            ),
            Row(
                Column('complemento', css_class='form-group col-md-4'),
                Column('bairro', css_class='form-group col-md-4'),
                Column('cidade', css_class='form-group col-md-3'),
                Column('estado', css_class='form-group col-md-1'),
            ),

            HTML('<h4 class="mt-4 mb-3"><i class="fas fa-phone"></i> Contato</h4>'),
            Row(
                Column('telefone', css_class='form-group col-md-4'),
                Column('celular', css_class='form-group col-md-4'),
                Column('email', css_class='form-group col-md-4'),
            ),

            HTML('<h4 class="mt-4 mb-3"><i class="fas fa-bell"></i> Preferências de Notificação</h4>'),
            Row(
                Column('notificar_email', css_class='form-group col-md-4'),
                Column('notificar_sms', css_class='form-group col-md-4'),
                Column('notificar_whatsapp', css_class='form-group col-md-4'),
            ),

            # Seção Cônjuge (apenas PF)
            HTML('''
                <div id="secao-conjuge" class="secao-tipo-pessoa">
                    <h4 class="mt-4 mb-3"><i class="fas fa-ring"></i> Dados do Cônjuge (se casado)</h4>
                </div>
            '''),
            Div(
                Row(
                    Column('conjuge_nome', css_class='form-group col-md-6'),
                    Column('conjuge_cpf', css_class='form-group col-md-3'),
                    Column('conjuge_rg', css_class='form-group col-md-3'),
                ),
                css_class='campos-conjuge'
            ),

            HTML('<h4 class="mt-4 mb-3"><i class="fas fa-sticky-note"></i> Observações</h4>'),
            'observacoes',

            Div(
                Submit('submit', 'Salvar Comprador', css_class='btn btn-primary btn-lg'),
                HTML('<a href="{% url \'core:listar_compradores\' %}" class="btn btn-secondary btn-lg ms-2">Cancelar</a>'),
                css_class='text-center mt-4'
            )
        )

    def clean(self):
        cleaned_data = super().clean()
        tipo_pessoa = cleaned_data.get('tipo_pessoa')
        cpf = cleaned_data.get('cpf')
        cnpj = cleaned_data.get('cnpj')

        if tipo_pessoa == 'PF':
            if not cpf:
                raise ValidationError({'cpf': 'CPF é obrigatório para Pessoa Física'})
        elif tipo_pessoa == 'PJ':
            if not cnpj:
                raise ValidationError({'cnpj': 'CNPJ é obrigatório para Pessoa Jurídica'})

        return cleaned_data


class ImovelForm(forms.ModelForm):
    """Formulário para cadastro de Imóvel"""

    class Meta:
        model = Imovel
        fields = [
            'imobiliaria', 'tipo', 'identificacao', 'loteamento',
            'endereco', 'area', 'matricula', 'inscricao_municipal',
            'observacoes', 'disponivel'
        ]
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 3}),
            'endereco': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            HTML('<h4 class="mb-3"><i class="fas fa-home"></i> Informações Básicas</h4>'),
            Row(
                Column('imobiliaria', css_class='form-group col-md-6'),
                Column('tipo', css_class='form-group col-md-6'),
            ),
            Row(
                Column('identificacao', css_class='form-group col-md-6'),
                Column('loteamento', css_class='form-group col-md-6'),
            ),

            HTML('<h4 class="mt-4 mb-3"><i class="fas fa-map-marked-alt"></i> Localização</h4>'),
            'endereco',
            AppendedText('area', 'm²'),

            HTML('<h4 class="mt-4 mb-3"><i class="fas fa-file-alt"></i> Documentação</h4>'),
            Row(
                Column('matricula', css_class='form-group col-md-6'),
                Column('inscricao_municipal', css_class='form-group col-md-6'),
            ),

            HTML('<h4 class="mt-4 mb-3"><i class="fas fa-sticky-note"></i> Observações</h4>'),
            'observacoes',

            HTML('<h4 class="mt-4 mb-3"><i class="fas fa-check-circle"></i> Status</h4>'),
            'disponivel',

            Div(
                Submit('submit', 'Salvar Imóvel', css_class='btn btn-primary btn-lg'),
                HTML('<a href="{% url \'core:listar_imoveis\' %}" class="btn btn-secondary btn-lg ms-2">Cancelar</a>'),
                css_class='text-center mt-4'
            )
        )


class ImobiliariaForm(forms.ModelForm):
    """Formulário para cadastro de Imobiliária"""

    class Meta:
        model = Imobiliaria
        fields = [
            'contabilidade', 'nome', 'razao_social', 'cnpj',
            'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado',
            'telefone', 'email', 'responsavel_financeiro',
            'banco', 'agencia', 'conta', 'pix'
        ]
        widgets = {
            'cep': forms.TextInput(attrs={
                'placeholder': '99999-999',
                'data-viacep': 'true',
                'class': 'cep-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            HTML('<h4 class="mb-3"><i class="fas fa-building"></i> Informações da Empresa</h4>'),
            'contabilidade',
            Row(
                Column('nome', css_class='form-group col-md-8'),
                Column('cnpj', css_class='form-group col-md-4'),
            ),
            'razao_social',

            HTML('<h4 class="mt-4 mb-3"><i class="fas fa-map-marker-alt"></i> Endereço</h4>'),
            HTML('<p class="text-muted"><i class="fas fa-info-circle"></i> Digite o CEP e o endereço será preenchido automaticamente via ViaCEP</p>'),
            Row(
                Column('cep', css_class='form-group col-md-3'),
                Column('logradouro', css_class='form-group col-md-7'),
                Column('numero', css_class='form-group col-md-2'),
            ),
            Row(
                Column('complemento', css_class='form-group col-md-4'),
                Column('bairro', css_class='form-group col-md-4'),
                Column('cidade', css_class='form-group col-md-3'),
                Column('estado', css_class='form-group col-md-1'),
            ),

            HTML('<h4 class="mt-4 mb-3"><i class="fas fa-phone"></i> Contato</h4>'),
            Row(
                Column('telefone', css_class='form-group col-md-6'),
                Column('email', css_class='form-group col-md-6'),
            ),
            'responsavel_financeiro',

            HTML('<h4 class="mt-4 mb-3"><i class="fas fa-university"></i> Dados Bancários</h4>'),
            Row(
                Column('banco', css_class='form-group col-md-6'),
                Column('agencia', css_class='form-group col-md-3'),
                Column('conta', css_class='form-group col-md-3'),
            ),
            'pix',

            Div(
                Submit('submit', 'Salvar Imobiliária', css_class='btn btn-primary btn-lg'),
                HTML('<a href="{% url \'core:listar_imobiliarias\' %}" class="btn btn-secondary btn-lg ms-2">Cancelar</a>'),
                css_class='text-center mt-4'
            )
        )
