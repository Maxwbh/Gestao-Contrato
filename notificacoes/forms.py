"""
Formularios do app Notificacoes

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
"""
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field, HTML, Div
from .models import ConfiguracaoEmail, TemplateNotificacao
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
    """Formulario para templates de notificacao unificados (Email + SMS + WhatsApp)."""

    class Meta:
        model = TemplateNotificacao
        fields = [
            'nome', 'codigo', 'imobiliaria',
            'assunto', 'corpo_html', 'corpo', 'corpo_whatsapp', 'ativo'
        ]
        widgets = {
            'nome': forms.TextInput(attrs={
                'placeholder': 'Ex: Lembrete de Vencimento',
                'class': 'form-control',
            }),
            'assunto': forms.TextInput(attrs={
                'placeholder': 'Assunto do e-mail (suporta TAGs %%TAG%%)',
                'class': 'form-control',
            }),
            'corpo_html': forms.Textarea(attrs={
                'rows': 12,
                'class': 'form-control',
                'id': 'id_corpo_html',
            }),
            'corpo': forms.Textarea(attrs={
                'rows': 4,
                'maxlength': '255',
                'placeholder': 'Texto SMS (máx. 255 caracteres). Use TAGs como %%NOMECOMPRADOR%%.',
                'class': 'form-control',
                'id': 'id_corpo',
            }),
            'corpo_whatsapp': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Mensagem WhatsApp. Use TAGs como %%NOMECOMPRADOR%%, %%LINKBOLETO%%.',
                'class': 'form-control',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['imobiliaria'].queryset = Imobiliaria.objects.filter(ativo=True).order_by('nome')
        self.fields['imobiliaria'].required = False
        self.fields['imobiliaria'].widget.attrs['class'] = 'form-select'
        self.fields['codigo'].widget.attrs['class'] = 'form-select'
        self.fields['ativo'].widget.attrs['class'] = 'form-check-input'

    def clean_corpo(self):
        """SMS: máximo 255 caracteres."""
        corpo = self.cleaned_data.get('corpo', '')
        if corpo and len(corpo) > 255:
            raise forms.ValidationError(
                f'O corpo SMS deve ter no máximo 255 caracteres (atual: {len(corpo)}).'
            )
        return corpo

    def clean(self):
        cleaned = super().clean()
        # Pelo menos um canal deve ter conteúdo
        corpo_html = cleaned.get('corpo_html', '').strip()
        corpo = cleaned.get('corpo', '').strip()
        corpo_whatsapp = cleaned.get('corpo_whatsapp', '').strip()
        assunto = cleaned.get('assunto', '').strip()
        if not any([corpo_html, assunto, corpo, corpo_whatsapp]):
            raise forms.ValidationError(
                'Preencha pelo menos um campo de conteúdo (Email, SMS ou WhatsApp).'
            )
        return cleaned
