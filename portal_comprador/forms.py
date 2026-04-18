"""
Formulários do Portal do Comprador

Inclui:
- Formulário de auto-cadastro por CPF/CNPJ
- Formulário de login
- Formulário de atualização de dados pessoais
- Formulário de alteração de senha
"""
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
import re

from core.models import Comprador


class AutoCadastroForm(forms.Form):
    """
    Formulário para auto-cadastro do comprador.

    O comprador informa CPF ou CNPJ e cria uma senha para acessar o portal.
    O sistema verifica se existe um comprador com esse documento.
    """
    documento = forms.CharField(
        max_length=18,
        label='CPF ou CNPJ',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Digite seu CPF ou CNPJ',
            'autocomplete': 'off'
        }),
        help_text='Digite apenas números ou com pontuação'
    )
    email = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Digite seu e-mail'
        }),
        help_text='Informe o mesmo e-mail cadastrado no contrato'
    )
    senha = forms.CharField(
        min_length=6,
        label='Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Crie uma senha'
        }),
        help_text='Mínimo de 6 caracteres'
    )
    confirmar_senha = forms.CharField(
        min_length=6,
        label='Confirmar Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Confirme sua senha'
        })
    )

    def clean_documento(self):
        """Limpa e valida o documento (CPF ou CNPJ)"""
        documento = self.cleaned_data['documento']
        # Remove caracteres não numéricos
        documento_limpo = re.sub(r'\D', '', documento)

        if len(documento_limpo) == 11:
            # CPF
            return documento_limpo
        elif len(documento_limpo) == 14:
            # CNPJ
            return documento_limpo
        else:
            raise ValidationError('CPF deve ter 11 dígitos ou CNPJ deve ter 14 dígitos')

    def clean(self):
        cleaned_data = super().clean()
        senha = cleaned_data.get('senha')
        confirmar_senha = cleaned_data.get('confirmar_senha')

        if senha and confirmar_senha and senha != confirmar_senha:
            raise ValidationError('As senhas não coincidem')

        documento = cleaned_data.get('documento')
        email = cleaned_data.get('email')

        if documento:
            # Verificar se existe um comprador com esse documento
            comprador = None
            if len(documento) == 11:
                # Buscar por CPF (com ou sem formatação)
                cpf_formatado = f'{documento[:3]}.{documento[3:6]}.{documento[6:9]}-{documento[9:]}'
                comprador = Comprador.objects.filter(
                    models.Q(cpf=documento) | models.Q(cpf=cpf_formatado)
                ).first()
            else:
                # Buscar por CNPJ (com ou sem formatação)
                cnpj_formatado = f'{documento[:2]}.{documento[2:5]}.{documento[5:8]}/{documento[8:12]}-{documento[12:]}'
                comprador = Comprador.objects.filter(
                    models.Q(cnpj=documento) | models.Q(cnpj=cnpj_formatado)
                ).first()

            if not comprador:
                raise ValidationError('Nenhum contrato encontrado para este documento')

            # Verificar se o e-mail confere
            if email and comprador.email and comprador.email.lower() != email.lower():
                raise ValidationError('E-mail não confere com o cadastro')

            # Verificar se já tem acesso
            from portal_comprador.models import AcessoComprador
            if hasattr(comprador, 'acesso_portal'):
                raise ValidationError('Já existe uma conta para este documento. Use a opção de login.')

            cleaned_data['comprador'] = comprador

        return cleaned_data


class LoginCompradorForm(forms.Form):
    """
    Formulário de login do comprador.

    O comprador pode fazer login usando CPF/CNPJ e senha.
    """
    documento = forms.CharField(
        max_length=18,
        label='CPF ou CNPJ',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Digite seu CPF ou CNPJ',
            'autocomplete': 'off'
        })
    )
    senha = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Digite sua senha'
        })
    )

    def clean_documento(self):
        """Limpa o documento (CPF ou CNPJ)"""
        documento = self.cleaned_data['documento']
        # Remove caracteres não numéricos
        return re.sub(r'\D', '', documento)


class DadosPessoaisForm(forms.ModelForm):
    """
    Formulário para atualização de dados pessoais pelo comprador.

    O comprador só pode alterar:
    - Nome
    - Endereço de correspondência (CEP, logradouro, número, complemento, bairro, cidade, estado)
    - E-mail
    - Telefone/Celular
    """
    class Meta:
        model = Comprador
        fields = [
            'nome',
            'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado',
            'email', 'telefone', 'celular',
            'notificar_email', 'notificar_sms', 'notificar_whatsapp',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly'  # Nome só pode ser visualizado
            }),
            'cep': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '00000-000',
                'data-viacep': 'true'
            }),
            'logradouro': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'complemento': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(00) 0000-0000'
            }),
            'celular': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(00) 00000-0000'
            }),
            'notificar_email': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notificar_sms': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notificar_whatsapp': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Marcar campos que o comprador NÃO pode alterar como readonly
        self.fields['nome'].widget.attrs['readonly'] = True


class AlterarSenhaCompradorForm(forms.Form):
    """
    Formulário para alteração de senha do comprador.
    """
    senha_atual = forms.CharField(
        label='Senha Atual',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite sua senha atual'
        })
    )
    nova_senha = forms.CharField(
        min_length=6,
        label='Nova Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite a nova senha'
        }),
        help_text='Mínimo de 6 caracteres'
    )
    confirmar_senha = forms.CharField(
        min_length=6,
        label='Confirmar Nova Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirme a nova senha'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        nova_senha = cleaned_data.get('nova_senha')
        confirmar_senha = cleaned_data.get('confirmar_senha')

        if nova_senha and confirmar_senha and nova_senha != confirmar_senha:
            raise ValidationError('As senhas não coincidem')

        return cleaned_data


# Import para o clean do AutoCadastroForm
from django.db import models
