"""
Formularios do app Notificacoes

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field, HTML, Div
from .models import ConfiguracaoEmail, TemplateNotificacao, TipoNotificacao, TipoTemplate
from core.models import Imobiliaria


class ConfiguracaoEmailForm(forms.ModelForm):
    """Formulario para configuracao de servidor de e-mail"""

    class Meta:
        model = ConfiguracaoEmail
        fields = [
            'nome', 'host', 'porta', 'usuario', 'senha',
            'usar_tls', 'usar_ssl', 'email_remetente', 'nome_remetente', 'ativo'
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'Ex: Servidor Principal'}),
            'host': forms.TextInput(attrs={'placeholder': 'smtp.gmail.com'}),
            'porta': forms.NumberInput(attrs={'placeholder': '587'}),
            'usuario': forms.TextInput(attrs={'placeholder': 'usuario@gmail.com'}),
            'senha': forms.PasswordInput(attrs={'placeholder': '********', 'autocomplete': 'new-password'}),
            'email_remetente': forms.EmailInput(attrs={'placeholder': 'noreply@empresa.com'}),
            'nome_remetente': forms.TextInput(attrs={'placeholder': 'Sistema de Gestao de Contratos'}),
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

        # Se estiver editando, mostrar placeholder na senha
        if self.instance and self.instance.pk:
            self.fields['senha'].widget.attrs['placeholder'] = 'Deixe em branco para manter a senha atual'
            self.fields['senha'].required = False

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            # Card: Identificacao
            HTML('''
                <div class="card mb-3">
                    <div class="card-header py-2 bg-primary text-white">
                        <i class="fas fa-envelope me-2"></i><strong>Identificacao</strong>
                    </div>
                    <div class="card-body py-3">
            '''),
            Row(
                Column(Field('nome', wrapper_class='mb-2'), css_class='col-md-8'),
                Column(
                    Div(Field('ativo'), css_class='form-check mt-4'),
                    css_class='col-md-4'
                ),
            ),
            HTML('</div></div>'),

            # Card: Servidor SMTP
            HTML('''
                <div class="card mb-3">
                    <div class="card-header py-2">
                        <i class="fas fa-server me-2"></i><strong>Servidor SMTP</strong>
                    </div>
                    <div class="card-body py-3">
            '''),
            Row(
                Column(Field('host', wrapper_class='mb-2'), css_class='col-md-8'),
                Column(Field('porta', wrapper_class='mb-2'), css_class='col-md-4'),
            ),
            Row(
                Column(Field('usuario', wrapper_class='mb-2'), css_class='col-md-6'),
                Column(Field('senha', wrapper_class='mb-2'), css_class='col-md-6'),
            ),
            Row(
                Column(
                    Div(Field('usar_tls'), css_class='form-check'),
                    css_class='col-md-6'
                ),
                Column(
                    Div(Field('usar_ssl'), css_class='form-check'),
                    css_class='col-md-6'
                ),
            ),
            HTML('''
                        <small class="text-muted">
                            <i class="fas fa-info-circle me-1"></i>
                            TLS (porta 587) ou SSL (porta 465). Nao ative ambos ao mesmo tempo.
                        </small>
                    </div>
                </div>
            '''),

            # Card: Remetente
            HTML('''
                <div class="card mb-3">
                    <div class="card-header py-2">
                        <i class="fas fa-user me-2"></i><strong>Remetente</strong>
                    </div>
                    <div class="card-body py-3">
            '''),
            Row(
                Column(Field('email_remetente', wrapper_class='mb-2'), css_class='col-md-6'),
                Column(Field('nome_remetente', wrapper_class='mb-2'), css_class='col-md-6'),
            ),
            HTML('</div></div>'),

            # Botoes
            HTML('''
                <div class="d-flex justify-content-between align-items-center mt-4 pt-3 border-top">
                    <a href="{% url 'notificacoes:listar_config_email' %}" class="btn btn-outline-secondary">
                        <i class="fas fa-arrow-left me-2"></i>Voltar
                    </a>
                    <div>
                        <button type="button" class="btn btn-outline-info me-2" id="btn-testar-conexao">
                            <i class="fas fa-vial me-1"></i>Testar Conexao
                        </button>
                        <button type="submit" class="btn btn-primary btn-lg px-5">
                            <i class="fas fa-save me-2"></i>Salvar
                        </button>
                    </div>
                </div>
            ''')
        )

    def clean(self):
        cleaned_data = super().clean()
        usar_tls = cleaned_data.get('usar_tls')
        usar_ssl = cleaned_data.get('usar_ssl')

        if usar_tls and usar_ssl:
            raise forms.ValidationError('Nao e possivel usar TLS e SSL ao mesmo tempo.')

        return cleaned_data


class TemplateNotificacaoForm(forms.ModelForm):
    """Formulario para templates de notificacao/mensagens de email"""

    class Meta:
        model = TemplateNotificacao
        fields = [
            'nome', 'codigo', 'tipo', 'imobiliaria',
            'assunto', 'corpo', 'corpo_html', 'ativo'
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'Ex: Lembrete de Vencimento'}),
            'assunto': forms.TextInput(attrs={'placeholder': 'Assunto do e-mail (suporta TAGs)'}),
            'corpo': forms.Textarea(attrs={'rows': 8, 'placeholder': 'Corpo da mensagem (use TAGs como %%NOMECOMPRADOR%%)'}),
            'corpo_html': forms.Textarea(attrs={'rows': 10, 'placeholder': 'Versao HTML do e-mail (opcional)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['imobiliaria'].queryset = Imobiliaria.objects.filter(ativo=True).order_by('nome')
        self.fields['imobiliaria'].required = False

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
            # Card: Identificacao
            HTML('''
                <div class="card mb-3">
                    <div class="card-header py-2 bg-success text-white">
                        <i class="fas fa-file-alt me-2"></i><strong>Identificacao do Template</strong>
                    </div>
                    <div class="card-body py-3">
            '''),
            Row(
                Column(Field('nome', wrapper_class='mb-2'), css_class='col-md-6'),
                Column(Field('codigo', wrapper_class='mb-2'), css_class='col-md-6'),
            ),
            Row(
                Column(Field('tipo', wrapper_class='mb-2'), css_class='col-md-4'),
                Column(Field('imobiliaria', wrapper_class='mb-2'), css_class='col-md-6'),
                Column(
                    Div(Field('ativo'), css_class='form-check mt-4'),
                    css_class='col-md-2'
                ),
            ),
            HTML('''
                        <small class="text-muted">
                            <i class="fas fa-info-circle me-1"></i>
                            Deixe "Imobiliaria" vazio para criar um template global (usado por todas).
                        </small>
                    </div>
                </div>
            '''),

            # Card: Conteudo
            HTML('''
                <div class="card mb-3">
                    <div class="card-header py-2">
                        <i class="fas fa-edit me-2"></i><strong>Conteudo da Mensagem</strong>
                    </div>
                    <div class="card-body py-3">
            '''),
            Field('assunto', wrapper_class='mb-3'),
            Field('corpo', wrapper_class='mb-3'),
            HTML('''
                        <div class="accordion mb-3" id="accordionHtml">
                            <div class="accordion-item">
                                <h2 class="accordion-header">
                                    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseHtml">
                                        <i class="fas fa-code me-2"></i>Versao HTML (Avancado)
                                    </button>
                                </h2>
                                <div id="collapseHtml" class="accordion-collapse collapse" data-bs-parent="#accordionHtml">
                                    <div class="accordion-body p-2">
            '''),
            Field('corpo_html', wrapper_class='mb-0'),
            HTML('''
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            '''),

            # Card: TAGs Disponiveis
            HTML('''
                <div class="card mb-3 border-info">
                    <div class="card-header py-2 bg-info text-white">
                        <i class="fas fa-tags me-2"></i><strong>TAGs Disponiveis</strong>
                        <button type="button" class="btn btn-sm btn-light float-end" data-bs-toggle="collapse" data-bs-target="#collapseTags">
                            <i class="fas fa-chevron-down"></i>
                        </button>
                    </div>
                    <div id="collapseTags" class="collapse">
                        <div class="card-body py-3">
                            <div class="row">
                                <div class="col-md-4">
                                    <h6 class="text-primary"><i class="fas fa-user me-1"></i>Comprador</h6>
                                    <ul class="list-unstyled small">
                                        <li><code>%%NOMECOMPRADOR%%</code> - Nome completo</li>
                                        <li><code>%%CPFCOMPRADOR%%</code> - CPF</li>
                                        <li><code>%%EMAILCOMPRADOR%%</code> - E-mail</li>
                                        <li><code>%%TELEFONECOMPRADOR%%</code> - Telefone</li>
                                        <li><code>%%CELULARCOMPRADOR%%</code> - Celular</li>
                                    </ul>
                                </div>
                                <div class="col-md-4">
                                    <h6 class="text-primary"><i class="fas fa-file-contract me-1"></i>Contrato/Parcela</h6>
                                    <ul class="list-unstyled small">
                                        <li><code>%%NUMEROCONTRATO%%</code> - Numero do contrato</li>
                                        <li><code>%%PARCELA%%</code> - Parcela (ex: 5/24)</li>
                                        <li><code>%%VALORPARCELA%%</code> - Valor da parcela</li>
                                        <li><code>%%DATAVENCIMENTO%%</code> - Data vencimento</li>
                                        <li><code>%%DIASATRASO%%</code> - Dias de atraso</li>
                                    </ul>
                                </div>
                                <div class="col-md-4">
                                    <h6 class="text-primary"><i class="fas fa-barcode me-1"></i>Boleto</h6>
                                    <ul class="list-unstyled small">
                                        <li><code>%%NOSSONUMERO%%</code> - Nosso numero</li>
                                        <li><code>%%LINHADIGITAVEL%%</code> - Linha digitavel</li>
                                        <li><code>%%CODIGOBARRAS%%</code> - Codigo de barras</li>
                                        <li><code>%%VALORBOLETO%%</code> - Valor do boleto</li>
                                        <li><code>%%LINKBOLETO%%</code> - Link para download</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            '''),

            # Botoes
            HTML('''
                <div class="d-flex justify-content-between align-items-center mt-4 pt-3 border-top">
                    <a href="{% url 'notificacoes:listar_templates' %}" class="btn btn-outline-secondary">
                        <i class="fas fa-arrow-left me-2"></i>Voltar
                    </a>
                    <button type="submit" class="btn btn-success btn-lg px-5">
                        <i class="fas fa-save me-2"></i>Salvar Template
                    </button>
                </div>
            ''')
        )
