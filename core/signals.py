"""
Signals do app core.

HU-28: garante que todo usuário tenha um PerfilUsuario (papel/troca de senha).
"""
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def criar_perfil_usuario(sender, instance, created, **kwargs):
    """Cria o PerfilUsuario (papel COMUM) na criação de um usuário.

    Compradores do portal também recebem perfil, mas nunca ganham papel ADMIN
    nem AcessoUsuario — a distinção é feita pela presença de AcessoComprador.
    """
    if not created:
        return
    from core.models import PerfilUsuario
    PerfilUsuario.objects.get_or_create(usuario=instance)
