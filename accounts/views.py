"""
Views de autenticação e registro de usuários

Desenvolvedor: Maxwell da Silva Oliveira
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import LoginForm, RegistroUsuarioForm, AlterarSenhaForm, PerfilUsuarioForm


def login_view(request):
    """View de login"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Bem-vindo, {user.first_name or user.username}!')

            # Redirecionar para next se existir
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('core:dashboard')
        else:
            messages.error(request, 'Usuário ou senha inválidos.')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """View de logout"""
    logout(request)
    messages.info(request, 'Você saiu do sistema.')
    return redirect('accounts:login')


def registro_view(request):
    """View de registro de novo usuário"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Conta criada com sucesso! Bem-vindo, {user.first_name}!')
            return redirect('core:dashboard')
        else:
            messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = RegistroUsuarioForm()

    return render(request, 'accounts/registro.html', {'form': form})


@login_required
def perfil_view(request):
    """View para ver e editar perfil"""
    if request.method == 'POST':
        form = PerfilUsuarioForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil atualizado com sucesso!')
            return redirect('accounts:perfil')
    else:
        form = PerfilUsuarioForm(instance=request.user)

    return render(request, 'accounts/perfil.html', {'form': form})


@login_required
def alterar_senha_view(request):
    """View para alterar senha"""
    if request.method == 'POST':
        form = AlterarSenhaForm(request.POST)
        if form.is_valid():
            user = request.user
            if user.check_password(form.cleaned_data['senha_atual']):
                user.set_password(form.cleaned_data['nova_senha'])
                user.save()
                update_session_auth_hash(request, user)  # Mantém logado
                messages.success(request, 'Senha alterada com sucesso!')
                return redirect('accounts:perfil')
            else:
                messages.error(request, 'Senha atual incorreta.')
    else:
        form = AlterarSenhaForm()

    return render(request, 'accounts/alterar_senha.html', {'form': form})
