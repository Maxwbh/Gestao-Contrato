"""
Modelos do Portal do Comprador

Vincula compradores a usuários do sistema para acesso ao portal.
"""
from django.db import models, transaction
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


class ComprovantePagamentoUpload(models.Model):
    """
    Roadmap 34.4: Upload de comprovante de pagamento pelo comprador via portal.
    Após upload, fica pendente até validação pelo administrador.
    """
    STATUS_PENDENTE = 'PENDENTE'
    STATUS_APROVADO = 'APROVADO'
    STATUS_REJEITADO = 'REJEITADO'
    STATUS_CHOICES = [
        (STATUS_PENDENTE, 'Aguardando Validação'),
        (STATUS_APROVADO, 'Aprovado'),
        (STATUS_REJEITADO, 'Rejeitado'),
    ]

    FORMA_CHOICES = [
        ('PIX', 'PIX'),
        ('TED', 'Transferência (TED/DOC)'),
        ('DINHEIRO', 'Dinheiro'),
        ('BOLETO', 'Boleto Bancário'),
        ('OUTRO', 'Outro'),
    ]

    parcela = models.ForeignKey(
        'financeiro.Parcela',
        on_delete=models.CASCADE,
        related_name='comprovantes_upload',
        verbose_name='Parcela'
    )
    acesso_comprador = models.ForeignKey(
        AcessoComprador,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Enviado por (Acesso)'
    )
    comprovante = models.FileField(
        upload_to='comprovantes_portal/%Y/%m/',
        verbose_name='Arquivo do Comprovante'
    )
    valor_informado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Valor Pago Informado'
    )
    data_pagamento_informada = models.DateField(verbose_name='Data do Pagamento')
    forma_pagamento = models.CharField(
        max_length=15,
        choices=FORMA_CHOICES,
        default='PIX',
        verbose_name='Forma de Pagamento'
    )
    observacoes_comprador = models.TextField(blank=True, verbose_name='Observações do Comprador')
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default=STATUS_PENDENTE,
        verbose_name='Status'
    )
    motivo_rejeicao = models.TextField(blank=True, verbose_name='Motivo da Rejeição')
    validado_em = models.DateTimeField(null=True, blank=True, verbose_name='Validado em')
    validado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comprovantes_validados',
        verbose_name='Validado por'
    )
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Enviado em')
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Comprovante de Pagamento (Portal)'
        verbose_name_plural = 'Comprovantes de Pagamento (Portal)'
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['status', '-criado_em']),
            models.Index(fields=['parcela', 'status']),
        ]

    def __str__(self):
        return f'Comprovante {self.parcela} — {self.get_status_display()}'

    def aprovar(self, usuario):
        """Aprova o comprovante e registra o pagamento na parcela vinculada."""
        from financeiro.models import HistoricoPagamento
        if self.status != self.STATUS_PENDENTE:
            return False
        if self.parcela.pago:
            self.status = self.STATUS_REJEITADO
            self.motivo_rejeicao = 'Parcela já está paga (validação automática)'
            self.validado_em = timezone.now()
            self.validado_por = usuario
            self.save()
            return False
        with transaction.atomic():
            valor_parcela = self.parcela.valor_atual
            self.parcela.registrar_pagamento(
                valor_pago=self.valor_informado,
                data_pagamento=self.data_pagamento_informada,
                observacoes=f'Comprovante validado via portal (upload #{self.pk})',
                validar_minimo=False,
            )
            HistoricoPagamento.objects.create(
                parcela=self.parcela,
                data_pagamento=self.data_pagamento_informada,
                valor_pago=self.valor_informado,
                valor_parcela=valor_parcela,
                forma_pagamento=self.forma_pagamento,
                observacoes=(self.observacoes_comprador or '')
                            + f'\n[Validado a partir do comprovante #{self.pk}]',
                origem_pagamento='PORTAL_UPLOAD',
                comprovante=self.comprovante,
            )
            self.status = self.STATUS_APROVADO
            self.validado_em = timezone.now()
            self.validado_por = usuario
            self.save(update_fields=['status', 'validado_em', 'validado_por'])
        return True

    def rejeitar(self, usuario, motivo):
        """Rejeita o comprovante, registrando o motivo."""
        if self.status != self.STATUS_PENDENTE:
            return False
        self.status = self.STATUS_REJEITADO
        self.motivo_rejeicao = motivo or 'Rejeitado sem motivo informado'
        self.validado_em = timezone.now()
        self.validado_por = usuario
        self.save(update_fields=['status', 'motivo_rejeicao', 'validado_em', 'validado_por'])
        return True


# =============================================================================
# 34.6 P3 — PWA: Web Push Subscriptions
# =============================================================================

class PushSubscriptionPortal(models.Model):
    """
    Armazena as assinaturas Web Push dos compradores para envio de notificações push.

    O endpoint, p256dh e auth são fornecidos pelo browser ao chamar
    PushManager.subscribe() no service worker.
    """
    acesso_comprador = models.ForeignKey(
        AcessoComprador,
        on_delete=models.CASCADE,
        related_name='push_subscriptions',
        verbose_name='Acesso do comprador',
    )
    endpoint = models.TextField(verbose_name='Endpoint Push')
    p256dh = models.TextField(verbose_name='Chave p256dh')
    auth = models.TextField(verbose_name='Auth secret')
    user_agent = models.CharField(max_length=200, blank=True, verbose_name='User-Agent')
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Assinatura Push'
        verbose_name_plural = 'Assinaturas Push'
        unique_together = [('acesso_comprador', 'endpoint')]

    def __str__(self):
        return f'Push #{self.pk} — {self.acesso_comprador.comprador.nome}'
