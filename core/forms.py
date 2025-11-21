"""
Formulários do app Core

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django import forms
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div, HTML, Field
from crispy_forms.bootstrap import PrependedText, AppendedText
from .models import (
    Contabilidade, Imobiliaria, Imovel, Comprador, TipoImovel,
    ContaBancaria, BancoBrasil, TipoValor, TipoTitulo, LayoutCNAB,
    AcessoUsuario
)
from django.contrib.auth import get_user_model
import re


class ContabilidadeForm(forms.ModelForm):
    """Formulário para cadastro de Contabilidade"""

    class Meta:
        model = Contabilidade
        fields = [
            'nome', 'razao_social', 'cnpj',
            'endereco', 'telefone', 'email', 'responsavel'
        ]
        widgets = {
            'cnpj': forms.TextInput(attrs={'placeholder': '00.000.000/0000-00', 'maxlength': '20'}),
            'endereco': forms.Textarea(attrs={'rows': 2}),
            'telefone': forms.TextInput(attrs={'placeholder': '(00) 0000-0000'}),
            'email': forms.EmailInput(attrs={'placeholder': 'contato@contabilidade.com'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                if isinstance(field.widget, forms.Select):
                    field.widget.attrs['class'] = 'form-select'
                else:
                    field.widget.attrs['class'] = 'form-control'

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            # Card: Informações da Contabilidade
            HTML('''
                <div class="card mb-3">
                    <div class="card-header py-2">
                        <i class="fas fa-calculator me-2"></i><strong>Informações da Contabilidade</strong>
                    </div>
                    <div class="card-body py-3">
            '''),
            Row(
                Column(Field('nome', wrapper_class='mb-2'), css_class='col-md-6'),
                Column(Field('cnpj', wrapper_class='mb-2'), css_class='col-md-6'),
            ),
            Field('razao_social', wrapper_class='mb-2'),
            HTML('</div></div>'),

            # Card: Contato
            HTML('''
                <div class="card mb-3">
                    <div class="card-header py-2">
                        <i class="fas fa-phone me-2"></i><strong>Contato</strong>
                    </div>
                    <div class="card-body py-3">
            '''),
            Field('endereco', wrapper_class='mb-2'),
            Row(
                Column(Field('telefone', wrapper_class='mb-2'), css_class='col-md-4'),
                Column(Field('email', wrapper_class='mb-2'), css_class='col-md-4'),
                Column(Field('responsavel', wrapper_class='mb-2'), css_class='col-md-4'),
            ),
            HTML('</div></div>'),

            # Botões
            HTML('''
                <div class="d-flex justify-content-between align-items-center mt-4 pt-3 border-top">
                    <a href="{% url 'core:listar_contabilidades' %}" class="btn btn-outline-secondary">
                        <i class="fas fa-arrow-left me-2"></i>Voltar
                    </a>
                    <button type="submit" class="btn btn-primary btn-lg px-5">
                        <i class="fas fa-save me-2"></i>Salvar Contabilidade
                    </button>
                </div>
            ''')
        )


class CompradorForm(forms.ModelForm):
    """Formulário para cadastro de Comprador (PF ou PJ)"""

    class Meta:
        model = Comprador
        fields = [
            'tipo_pessoa',
            # Campo compartilhado (Nome/Razão Social)
            'nome',
            # Campos PF
            'cpf', 'rg', 'data_nascimento', 'estado_civil', 'profissao',
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
            'tipo_pessoa': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'data_nascimento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'cep': forms.TextInput(attrs={
                'placeholder': '00000-000',
                'data-viacep': 'true',
                'class': 'form-control cep-input',
                'maxlength': '9'
            }),
            'cpf': forms.TextInput(attrs={'placeholder': '000.000.000-00', 'maxlength': '14'}),
            'cnpj': forms.TextInput(attrs={'placeholder': '00.000.000/0000-00', 'maxlength': '20'}),
            'responsavel_cpf': forms.TextInput(attrs={'placeholder': '000.000.000-00', 'maxlength': '14'}),
            'conjuge_cpf': forms.TextInput(attrs={'placeholder': '000.000.000-00', 'maxlength': '14'}),
            'telefone': forms.TextInput(attrs={'placeholder': '(00) 0000-0000'}),
            'celular': forms.TextInput(attrs={'placeholder': '(00) 00000-0000'}),
            'email': forms.EmailInput(attrs={'placeholder': 'email@exemplo.com'}),
            'numero': forms.TextInput(attrs={'placeholder': 'Nº'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'estado_civil': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'tipo_pessoa': 'Tipo de Pessoa',
            'nome': 'Nome Completo / Razão Social',
            'notificar_email': 'Email',
            'notificar_sms': 'SMS',
            'notificar_whatsapp': 'WhatsApp',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Adicionar classes e placeholders
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                if isinstance(field.widget, forms.Select):
                    field.widget.attrs['class'] = 'form-select'
                elif isinstance(field.widget, forms.CheckboxInput):
                    field.widget.attrs['class'] = 'form-check-input'
                elif isinstance(field.widget, forms.RadioSelect):
                    pass  # RadioSelect handled differently
                else:
                    field.widget.attrs['class'] = 'form-control'

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'comprador-form'
        self.helper.layout = Layout(
            # Card: Tipo de Pessoa
            HTML('''
                <div class="card mb-3 border-primary">
                    <div class="card-header bg-primary text-white py-2">
                        <i class="fas fa-user-tag me-2"></i><strong>Tipo de Cadastro</strong>
                    </div>
                    <div class="card-body py-3">
                        <div class="d-flex justify-content-center gap-4">
            '''),
            Field('tipo_pessoa', template='core/widgets/radio_inline.html'),
            HTML('''
                        </div>
                    </div>
                </div>
            '''),

            # Card: Identificação (campos dinâmicos PF/PJ)
            HTML('''
                <div class="card mb-3">
                    <div class="card-header py-2">
                        <i class="fas fa-id-card me-2"></i><strong id="titulo-identificacao">Identificação</strong>
                    </div>
                    <div class="card-body py-3">
            '''),

            # Nome/Razão Social (sempre visível, label muda)
            Row(
                Column(Field('nome', wrapper_class='mb-2'), css_class='col-12'),
            ),

            # Campos específicos PF
            Div(
                Row(
                    Column(Field('cpf', wrapper_class='mb-2'), css_class='col-md-4'),
                    Column(Field('rg', wrapper_class='mb-2'), css_class='col-md-4'),
                    Column(Field('data_nascimento', wrapper_class='mb-2'), css_class='col-md-4'),
                ),
                Row(
                    Column(Field('estado_civil', wrapper_class='mb-2'), css_class='col-md-6'),
                    Column(Field('profissao', wrapper_class='mb-2'), css_class='col-md-6'),
                ),
                css_id='campos-pf'
            ),

            # Campos específicos PJ
            Div(
                Row(
                    Column(Field('cnpj', wrapper_class='mb-2'), css_class='col-md-6'),
                    Column(Field('nome_fantasia', wrapper_class='mb-2'), css_class='col-md-6'),
                ),
                Row(
                    Column(Field('inscricao_estadual', wrapper_class='mb-2'), css_class='col-md-6'),
                    Column(Field('inscricao_municipal', wrapper_class='mb-2'), css_class='col-md-6'),
                ),
                HTML('<hr class="my-2"><small class="text-muted mb-2 d-block"><i class="fas fa-user-tie me-1"></i>Responsável Legal</small>'),
                Row(
                    Column(Field('responsavel_legal', wrapper_class='mb-2'), css_class='col-md-8'),
                    Column(Field('responsavel_cpf', wrapper_class='mb-2'), css_class='col-md-4'),
                ),
                css_id='campos-pj',
                style='display:none;'
            ),

            HTML('</div></div>'),

            # Card: Endereço
            HTML('''
                <div class="card mb-3">
                    <div class="card-header py-2">
                        <i class="fas fa-map-marker-alt me-2"></i><strong>Endereço</strong>
                        <small class="text-muted ms-2">(CEP preenche automaticamente)</small>
                    </div>
                    <div class="card-body py-3">
            '''),
            Row(
                Column(Field('cep', wrapper_class='mb-2'), css_class='col-md-2'),
                Column(Field('logradouro', wrapper_class='mb-2'), css_class='col-md-6'),
                Column(Field('numero', wrapper_class='mb-2'), css_class='col-md-2'),
                Column(Field('complemento', wrapper_class='mb-2'), css_class='col-md-2'),
            ),
            Row(
                Column(Field('bairro', wrapper_class='mb-2'), css_class='col-md-4'),
                Column(Field('cidade', wrapper_class='mb-2'), css_class='col-md-5'),
                Column(Field('estado', wrapper_class='mb-2'), css_class='col-md-3'),
            ),
            HTML('</div></div>'),

            # Card: Contato + Notificações (lado a lado)
            HTML('<div class="row">'),

            # Contato
            HTML('''
                <div class="col-md-7">
                    <div class="card mb-3 h-100">
                        <div class="card-header py-2">
                            <i class="fas fa-phone me-2"></i><strong>Contato</strong>
                        </div>
                        <div class="card-body py-3">
            '''),
            Row(
                Column(Field('telefone', wrapper_class='mb-2'), css_class='col-md-6'),
                Column(Field('celular', wrapper_class='mb-2'), css_class='col-md-6'),
            ),
            Field('email', wrapper_class='mb-2'),
            HTML('</div></div></div>'),

            # Notificações
            HTML('''
                <div class="col-md-5">
                    <div class="card mb-3 h-100">
                        <div class="card-header py-2">
                            <i class="fas fa-bell me-2"></i><strong>Notificações</strong>
                        </div>
                        <div class="card-body py-3 d-flex flex-column justify-content-center">
                            <div class="d-flex justify-content-around">
            '''),
            Div(
                Field('notificar_email'),
                css_class='form-check'
            ),
            Div(
                Field('notificar_sms'),
                css_class='form-check'
            ),
            Div(
                Field('notificar_whatsapp'),
                css_class='form-check'
            ),
            HTML('</div></div></div></div>'),

            HTML('</div>'),  # Fecha row

            # Card: Cônjuge (apenas PF)
            Div(
                HTML('''
                    <div class="card mb-3">
                        <div class="card-header py-2 bg-light">
                            <i class="fas fa-ring me-2"></i><strong>Cônjuge</strong>
                            <small class="text-muted ms-2">(se casado)</small>
                        </div>
                        <div class="card-body py-3">
                '''),
                Row(
                    Column(Field('conjuge_nome', wrapper_class='mb-2'), css_class='col-md-6'),
                    Column(Field('conjuge_cpf', wrapper_class='mb-2'), css_class='col-md-3'),
                    Column(Field('conjuge_rg', wrapper_class='mb-2'), css_class='col-md-3'),
                ),
                HTML('</div></div>'),
                css_id='card-conjuge'
            ),

            # Card: Observações
            HTML('''
                <div class="card mb-3">
                    <div class="card-header py-2 bg-light">
                        <i class="fas fa-sticky-note me-2"></i><strong>Observações</strong>
                    </div>
                    <div class="card-body py-2">
            '''),
            Field('observacoes', wrapper_class='mb-0'),
            HTML('</div></div>'),

            # Botões
            HTML('''
                <div class="d-flex justify-content-between align-items-center mt-4 pt-3 border-top">
                    <a href="{% url 'core:listar_compradores' %}" class="btn btn-outline-secondary">
                        <i class="fas fa-arrow-left me-2"></i>Voltar
                    </a>
                    <button type="submit" class="btn btn-primary btn-lg px-5">
                        <i class="fas fa-save me-2"></i>Salvar Comprador
                    </button>
                </div>
            ''')
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
    """Formulário para cadastro de Imóvel com georreferenciamento"""

    class Meta:
        model = Imovel
        fields = [
            'imobiliaria', 'tipo', 'identificacao', 'loteamento',
            # Endereço estruturado
            'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado',
            # Georreferenciamento
            'latitude', 'longitude',
            # Dados do imóvel
            'area', 'valor',
            # Documentação
            'matricula', 'inscricao_municipal',
            # Outros
            'observacoes', 'disponivel'
        ]
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 2}),
            'cep': forms.TextInput(attrs={
                'placeholder': '00000-000',
                'data-viacep': 'true',
                'class': 'form-control cep-input',
                'maxlength': '9'
            }),
            'latitude': forms.NumberInput(attrs={
                'step': '0.0000001',
                'placeholder': '-23.5505199',
                'id': 'id_latitude'
            }),
            'longitude': forms.NumberInput(attrs={
                'step': '0.0000001',
                'placeholder': '-46.6333094',
                'id': 'id_longitude'
            }),
            'valor': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
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

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_id = 'imovel-form'
        self.helper.layout = Layout(
            # Card: Informações Básicas
            HTML('''
                <div class="card mb-3">
                    <div class="card-header py-2">
                        <i class="fas fa-home me-2"></i><strong>Informações Básicas</strong>
                    </div>
                    <div class="card-body py-3">
            '''),
            Row(
                Column(Field('imobiliaria', wrapper_class='mb-2'), css_class='col-md-6'),
                Column(Field('tipo', wrapper_class='mb-2'), css_class='col-md-6'),
            ),
            Row(
                Column(Field('identificacao', wrapper_class='mb-2'), css_class='col-md-6'),
                Column(Field('loteamento', wrapper_class='mb-2'), css_class='col-md-6'),
            ),
            HTML('</div></div>'),

            # Card: Endereço
            HTML('''
                <div class="card mb-3">
                    <div class="card-header py-2">
                        <i class="fas fa-map-marker-alt me-2"></i><strong>Endereço</strong>
                        <small class="text-muted ms-2">(CEP preenche automaticamente)</small>
                    </div>
                    <div class="card-body py-3">
            '''),
            Row(
                Column(Field('cep', wrapper_class='mb-2'), css_class='col-md-2'),
                Column(Field('logradouro', wrapper_class='mb-2'), css_class='col-md-6'),
                Column(Field('numero', wrapper_class='mb-2'), css_class='col-md-2'),
                Column(Field('complemento', wrapper_class='mb-2'), css_class='col-md-2'),
            ),
            Row(
                Column(Field('bairro', wrapper_class='mb-2'), css_class='col-md-4'),
                Column(Field('cidade', wrapper_class='mb-2'), css_class='col-md-5'),
                Column(Field('estado', wrapper_class='mb-2'), css_class='col-md-3'),
            ),
            HTML('</div></div>'),

            # Card: Geolocalização (Mapa)
            HTML('''
                <div class="card mb-3 border-success">
                    <div class="card-header py-2 bg-success text-white">
                        <i class="fas fa-map-marked-alt me-2"></i><strong>Geolocalização</strong>
                        <small class="ms-2">(Clique no mapa ou busque o endereço)</small>
                    </div>
                    <div class="card-body py-3">
                        <div class="row mb-3">
                            <div class="col-12">
                                <div class="input-group">
                                    <input type="text" id="busca-endereco" class="form-control" placeholder="Buscar endereço no mapa...">
                                    <button type="button" id="btn-buscar-endereco" class="btn btn-outline-success">
                                        <i class="fas fa-search"></i> Buscar
                                    </button>
                                    <button type="button" id="btn-usar-endereco" class="btn btn-outline-primary">
                                        <i class="fas fa-map-pin"></i> Usar Endereço do Formulário
                                    </button>
                                </div>
                            </div>
                        </div>
                        <div id="map" style="height: 400px; border-radius: 8px; border: 1px solid #ddd;"></div>
                        <div class="row mt-3">
            '''),
            Row(
                Column(Field('latitude', wrapper_class='mb-2'), css_class='col-md-6'),
                Column(Field('longitude', wrapper_class='mb-2'), css_class='col-md-6'),
            ),
            HTML('</div></div></div>'),

            # Card: Dados do Imóvel
            HTML('''
                <div class="card mb-3">
                    <div class="card-header py-2">
                        <i class="fas fa-ruler-combined me-2"></i><strong>Dados do Imóvel</strong>
                    </div>
                    <div class="card-body py-3">
            '''),
            Row(
                Column(AppendedText('area', 'm²', wrapper_class='mb-2'), css_class='col-md-4'),
                Column(PrependedText('valor', 'R$', wrapper_class='mb-2'), css_class='col-md-4'),
                Column(
                    Div(Field('disponivel'), css_class='form-check mt-4'),
                    css_class='col-md-4'
                ),
            ),
            HTML('</div></div>'),

            # Card: Documentação
            HTML('''
                <div class="card mb-3">
                    <div class="card-header py-2">
                        <i class="fas fa-file-alt me-2"></i><strong>Documentação</strong>
                    </div>
                    <div class="card-body py-3">
            '''),
            Row(
                Column(Field('matricula', wrapper_class='mb-2'), css_class='col-md-6'),
                Column(Field('inscricao_municipal', wrapper_class='mb-2'), css_class='col-md-6'),
            ),
            HTML('</div></div>'),

            # Card: Observações
            HTML('''
                <div class="card mb-3">
                    <div class="card-header py-2 bg-light">
                        <i class="fas fa-sticky-note me-2"></i><strong>Observações</strong>
                    </div>
                    <div class="card-body py-2">
            '''),
            Field('observacoes', wrapper_class='mb-0'),
            HTML('</div></div>'),

            # Botões
            HTML('''
                <div class="d-flex justify-content-between align-items-center mt-4 pt-3 border-top">
                    <a href="{% url 'core:listar_imoveis' %}" class="btn btn-outline-secondary">
                        <i class="fas fa-arrow-left me-2"></i>Voltar
                    </a>
                    <button type="submit" class="btn btn-primary btn-lg px-5">
                        <i class="fas fa-save me-2"></i>Salvar Imóvel
                    </button>
                </div>
            ''')
        )


class ImobiliariaForm(forms.ModelForm):
    """Formulário para cadastro de Imobiliária"""

    class Meta:
        model = Imobiliaria
        fields = [
            'contabilidade', 'nome', 'razao_social', 'cnpj',
            'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado',
            'telefone', 'email', 'responsavel_financeiro',
            'banco', 'agencia', 'conta', 'pix',
            # Configurações de Boleto
            'tipo_valor_multa', 'percentual_multa_padrao',
            'tipo_valor_juros', 'percentual_juros_padrao',
            'dias_para_encargos_padrao',
            'boleto_sem_valor', 'parcela_no_documento', 'campo_desconto_abatimento_pdf',
            'tipo_valor_desconto', 'percentual_desconto_padrao', 'dias_para_desconto_padrao',
            'tipo_valor_desconto2', 'desconto2_padrao', 'dias_para_desconto2_padrao',
            'tipo_valor_desconto3', 'desconto3_padrao', 'dias_para_desconto3_padrao',
            'instrucao_padrao', 'tipo_titulo', 'aceite'
        ]
        widgets = {
            'cep': forms.TextInput(attrs={
                'placeholder': '00000-000',
                'data-viacep': 'true',
                'class': 'form-control cep-input',
                'maxlength': '9'
            }),
            'cnpj': forms.TextInput(attrs={'placeholder': '00.000.000/0000-00', 'maxlength': '20'}),
            'percentual_multa_padrao': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'percentual_juros_padrao': forms.NumberInput(attrs={'step': '0.0001', 'min': '0'}),
            'percentual_desconto_padrao': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'desconto2_padrao': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'desconto3_padrao': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'instrucao_padrao': forms.TextInput(attrs={'placeholder': 'Uma linha no espaço instrução ao caixa'}),
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

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            # Card: Informações da Empresa
            HTML('''
                <div class="card mb-3">
                    <div class="card-header py-2">
                        <i class="fas fa-building me-2"></i><strong>Informações da Empresa</strong>
                    </div>
                    <div class="card-body py-3">
            '''),
            Field('contabilidade', wrapper_class='mb-2'),
            Row(
                Column(Field('nome', wrapper_class='mb-2'), css_class='col-md-6'),
                Column(Field('cnpj', wrapper_class='mb-2'), css_class='col-md-6'),
            ),
            Field('razao_social', wrapper_class='mb-2'),
            HTML('</div></div>'),

            # Card: Endereço
            HTML('''
                <div class="card mb-3">
                    <div class="card-header py-2">
                        <i class="fas fa-map-marker-alt me-2"></i><strong>Endereço</strong>
                        <small class="text-muted ms-2">(CEP preenche automaticamente)</small>
                    </div>
                    <div class="card-body py-3">
            '''),
            Row(
                Column(Field('cep', wrapper_class='mb-2'), css_class='col-md-2'),
                Column(Field('logradouro', wrapper_class='mb-2'), css_class='col-md-6'),
                Column(Field('numero', wrapper_class='mb-2'), css_class='col-md-2'),
                Column(Field('complemento', wrapper_class='mb-2'), css_class='col-md-2'),
            ),
            Row(
                Column(Field('bairro', wrapper_class='mb-2'), css_class='col-md-4'),
                Column(Field('cidade', wrapper_class='mb-2'), css_class='col-md-5'),
                Column(Field('estado', wrapper_class='mb-2'), css_class='col-md-3'),
            ),
            HTML('</div></div>'),

            # Card: Contato
            HTML('''
                <div class="card mb-3">
                    <div class="card-header py-2">
                        <i class="fas fa-phone me-2"></i><strong>Contato</strong>
                    </div>
                    <div class="card-body py-3">
            '''),
            Row(
                Column(Field('telefone', wrapper_class='mb-2'), css_class='col-md-4'),
                Column(Field('email', wrapper_class='mb-2'), css_class='col-md-4'),
                Column(Field('responsavel_financeiro', wrapper_class='mb-2'), css_class='col-md-4'),
            ),
            HTML('</div></div>'),

            # Card: Dados Bancários (Legacy - para referência)
            HTML('''
                <div class="card mb-3">
                    <div class="card-header py-2">
                        <i class="fas fa-university me-2"></i><strong>Dados Bancários (Referência)</strong>
                        <small class="text-muted ms-2">(Use "Contas Bancárias" abaixo para gerenciar)</small>
                    </div>
                    <div class="card-body py-3">
            '''),
            Row(
                Column(Field('banco', wrapper_class='mb-2'), css_class='col-md-4'),
                Column(Field('agencia', wrapper_class='mb-2'), css_class='col-md-2'),
                Column(Field('conta', wrapper_class='mb-2'), css_class='col-md-3'),
                Column(Field('pix', wrapper_class='mb-2'), css_class='col-md-3'),
            ),
            HTML('</div></div>'),

            # Card: Configurações Padrão de Boleto
            HTML('''
                <div class="card mb-3 border-info">
                    <div class="card-header py-2 bg-info text-white">
                        <i class="fas fa-barcode me-2"></i><strong>Configurações Padrão de Boleto</strong>
                    </div>
                    <div class="card-body py-3">
                        <h6 class="text-muted mb-3"><i class="fas fa-exclamation-circle me-1"></i>Multa</h6>
            '''),
            Row(
                Column(Field('tipo_valor_multa', wrapper_class='mb-2'), css_class='col-md-3'),
                Column(Field('percentual_multa_padrao', wrapper_class='mb-2'), css_class='col-md-9'),
            ),
            HTML('<hr><h6 class="text-muted mb-3"><i class="fas fa-percentage me-1"></i>Juros</h6>'),
            Row(
                Column(Field('tipo_valor_juros', wrapper_class='mb-2'), css_class='col-md-3'),
                Column(Field('percentual_juros_padrao', wrapper_class='mb-2'), css_class='col-md-6'),
                Column(Field('dias_para_encargos_padrao', wrapper_class='mb-2'), css_class='col-md-3'),
            ),
            HTML('<hr><h6 class="text-muted mb-3"><i class="fas fa-tags me-1"></i>Desconto 1</h6>'),
            Row(
                Column(Field('tipo_valor_desconto', wrapper_class='mb-2'), css_class='col-md-3'),
                Column(Field('percentual_desconto_padrao', wrapper_class='mb-2'), css_class='col-md-6'),
                Column(Field('dias_para_desconto_padrao', wrapper_class='mb-2'), css_class='col-md-3'),
            ),
            HTML('<h6 class="text-muted mb-3 mt-2"><i class="fas fa-tags me-1"></i>Desconto 2</h6>'),
            Row(
                Column(Field('tipo_valor_desconto2', wrapper_class='mb-2'), css_class='col-md-3'),
                Column(Field('desconto2_padrao', wrapper_class='mb-2'), css_class='col-md-6'),
                Column(Field('dias_para_desconto2_padrao', wrapper_class='mb-2'), css_class='col-md-3'),
            ),
            HTML('<h6 class="text-muted mb-3 mt-2"><i class="fas fa-tags me-1"></i>Desconto 3</h6>'),
            Row(
                Column(Field('tipo_valor_desconto3', wrapper_class='mb-2'), css_class='col-md-3'),
                Column(Field('desconto3_padrao', wrapper_class='mb-2'), css_class='col-md-6'),
                Column(Field('dias_para_desconto3_padrao', wrapper_class='mb-2'), css_class='col-md-3'),
            ),
            HTML('<hr><h6 class="text-muted mb-3"><i class="fas fa-file-invoice me-1"></i>Título e Instrução</h6>'),
            Row(
                Column(Field('tipo_titulo', wrapper_class='mb-2'), css_class='col-md-4'),
                Column(Field('instrucao_padrao', wrapper_class='mb-2'), css_class='col-md-8'),
            ),
            HTML('<hr><h6 class="text-muted mb-3"><i class="fas fa-cog me-1"></i>Opções do Boleto</h6>'),
            Row(
                Column(
                    Div(Field('boleto_sem_valor'), css_class='form-check'),
                    css_class='col-md-4'
                ),
                Column(
                    Div(Field('parcela_no_documento'), css_class='form-check'),
                    css_class='col-md-4'
                ),
                Column(
                    Div(Field('campo_desconto_abatimento_pdf'), css_class='form-check'),
                    css_class='col-md-4'
                ),
            ),
            Row(
                Column(
                    Div(Field('aceite'), css_class='form-check'),
                    css_class='col-md-4'
                ),
            ),
            HTML('</div></div>'),

            # Botões
            HTML('''
                <div class="d-flex justify-content-between align-items-center mt-4 pt-3 border-top">
                    <a href="{% url 'core:listar_imobiliarias' %}" class="btn btn-outline-secondary">
                        <i class="fas fa-arrow-left me-2"></i>Voltar
                    </a>
                    <button type="submit" class="btn btn-primary btn-lg px-5">
                        <i class="fas fa-save me-2"></i>Salvar Imobiliária
                    </button>
                </div>
            ''')
        )


class ContaBancariaForm(forms.ModelForm):
    """Formulário para cadastro de Conta Bancária"""

    class Meta:
        model = ContaBancaria
        fields = [
            'banco', 'descricao', 'principal',
            'agencia', 'conta',
            'convenio', 'carteira', 'nosso_numero_atual', 'modalidade',
            'tipo_pix', 'chave_pix',
            'cobranca_registrada', 'prazo_baixa', 'prazo_protesto',
            'layout_cnab', 'numero_remessa_cnab_atual'
        ]
        widgets = {
            'banco': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.TextInput(attrs={'placeholder': 'Ex: Conta Principal'}),
            'tipo_pix': forms.Select(attrs={'class': 'form-select'}),
            'layout_cnab': forms.Select(attrs={'class': 'form-select'}),
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


class AcessoUsuarioForm(forms.ModelForm):
    """Formulário para gerenciar Acessos de Usuários"""

    class Meta:
        model = AcessoUsuario
        fields = ['usuario', 'contabilidade', 'imobiliaria', 'pode_editar', 'pode_excluir']
        widgets = {
            'usuario': forms.Select(attrs={'class': 'form-select'}),
            'contabilidade': forms.Select(attrs={'class': 'form-select'}),
            'imobiliaria': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        User = get_user_model()
        self.fields['usuario'].queryset = User.objects.filter(is_active=True).order_by('username')
        self.fields['contabilidade'].queryset = Contabilidade.objects.filter(ativo=True).order_by('nome')
        self.fields['imobiliaria'].queryset = Imobiliaria.objects.filter(ativo=True).order_by('nome')

        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                if isinstance(field.widget, forms.Select):
                    field.widget.attrs['class'] = 'form-select'
                elif isinstance(field.widget, forms.CheckboxInput):
                    field.widget.attrs['class'] = 'form-check-input'
                else:
                    field.widget.attrs['class'] = 'form-control'

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            # Card: Acesso
            HTML('''
                <div class="card mb-3">
                    <div class="card-header py-2">
                        <i class="fas fa-key me-2"></i><strong>Configurar Acesso</strong>
                    </div>
                    <div class="card-body py-3">
            '''),
            Field('usuario', wrapper_class='mb-3'),
            Row(
                Column(Field('contabilidade', wrapper_class='mb-2'), css_class='col-md-6'),
                Column(Field('imobiliaria', wrapper_class='mb-2'), css_class='col-md-6'),
            ),
            HTML('<hr><h6 class="text-muted mb-3"><i class="fas fa-shield-alt me-1"></i>Permissões</h6>'),
            Row(
                Column(
                    Div(Field('pode_editar'), css_class='form-check'),
                    css_class='col-md-6'
                ),
                Column(
                    Div(Field('pode_excluir'), css_class='form-check'),
                    css_class='col-md-6'
                ),
            ),
            HTML('</div></div>'),

            # Botões
            HTML('''
                <div class="d-flex justify-content-between align-items-center mt-4 pt-3 border-top">
                    <a href="{% url 'core:listar_acessos' %}" class="btn btn-outline-secondary">
                        <i class="fas fa-arrow-left me-2"></i>Voltar
                    </a>
                    <button type="submit" class="btn btn-primary btn-lg px-5">
                        <i class="fas fa-save me-2"></i>Salvar Acesso
                    </button>
                </div>
            ''')
        )
