"""
Models do app accounts

Este app utiliza o modelo User padrão do Django (django.contrib.auth.models.User).
Não possui modelos próprios, mas este arquivo existe para manter a estrutura
padrão de um app Django e permitir futuras extensões se necessário.

Desenvolvedor: Maxwell da Silva Oliveira
"""

# O app accounts usa django.contrib.auth.models.User
# Nenhum modelo customizado é necessário no momento.

# Se no futuro for necessário um modelo de perfil estendido:
# from django.db import models
# from django.contrib.auth.models import User
#
# class PerfilUsuario(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
#     # campos adicionais aqui
