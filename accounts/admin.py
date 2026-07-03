"""
Admin do app accounts

Este app utiliza o modelo User padrão do Django que já está registrado
no admin por django.contrib.auth.admin.UserAdmin.

Desenvolvedor: Maxwell da Silva Oliveira
"""

# O User padrão do Django já está registrado no admin.
# Nenhuma configuração adicional necessária.

# Se no futuro houver um modelo de perfil estendido:
# from django.contrib import admin
# from .models import PerfilUsuario
#
# @admin.register(PerfilUsuario)
# class PerfilUsuarioAdmin(admin.ModelAdmin):
#     list_display = ['user', ...]
