"""
Modelos do Portal do Comprador

Vincula compradores a usuários do sistema para acesso ao portal.
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class AcessoComprador(models.Model):
    """
    Vincula um Comprador a um usuário do sistema.

    Permite que o comprador faça login usando CPF/CNPJ e
    acesse seus contratos, boletos e dados pessoais.
    """
    comprador = models.OneToOneField(
        'core.Comprador',
        on_delete=models.CASCADE,
        related_name='acesso_portal',
        verbose_name='Comprador'
    )
    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='acesso_comprador',
        verbose_name='Usuário'
    )
    data_criacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Criação'
    )
    ultimo_acesso = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Último Acesso'
    )
    email_verificado = models.BooleanField(
        default=False,
        verbose_name='E-mail Verificado'
    )
    token_verificacao = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Token de Verificação'
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name='Ativo'
    )

    class Meta:
        verbose_name = 'Acesso do Comprador'
        verbose_name_plural = 'Acessos dos Compradores'

    def __str__(self):
        return f'{self.comprador.nome} ({self.usuario.username})'

    def registrar_acesso(self):
        """Registra o último acesso do comprador"""
        self.ultimo_acesso = timezone.now()
        self.save(update_fields=['ultimo_acesso'])


class LogAcessoComprador(models.Model):
    """
    Registra acessos do comprador ao portal.
    """
    acesso_comprador = models.ForeignKey(
        AcessoComprador,
        on_delete=models.CASCADE,
        related_name='logs_acesso',
        verbose_name='Acesso do Comprador'
    )
    data_acesso = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Acesso'
    )
    ip_acesso = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name='IP de Acesso'
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name='User Agent'
    )
    pagina_acessada = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Página Acessada'
    )

    class Meta:
        verbose_name = 'Log de Acesso'
        verbose_name_plural = 'Logs de Acesso'
        ordering = ['-data_acesso']

    def __str__(self):
        return f'{self.acesso_comprador.comprador.nome} - {self.data_acesso}'
