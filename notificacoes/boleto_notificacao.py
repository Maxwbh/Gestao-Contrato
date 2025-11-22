"""
Serviço de Notificações para Boletos

Processa templates de email e envia notificações de boletos
usando TAGs como %%NOMECOMPRADOR%%, %%DATAVENCIMENTO%%, etc.

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
import logging
from decimal import Decimal
from datetime import date, timedelta
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from .models import (
    TemplateNotificacao, TipoTemplate, TipoNotificacao,
    Notificacao, StatusNotificacao
)
from .services import ServicoEmail

logger = logging.getLogger(__name__)


class BoletoNotificacaoService:
    """Serviço para envio de notificações relacionadas a boletos"""

    def __init__(self):
        self.base_url = getattr(settings, 'SITE_URL', '')

    def _formatar_valor(self, valor):
        """Formata valor monetário para exibição"""
        if valor is None:
            return 'R$ 0,00'
        return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    def _formatar_data(self, data):
        """Formata data para exibição"""
        if data is None:
            return ''
        if hasattr(data, 'strftime'):
            return data.strftime('%d/%m/%Y')
        return str(data)

    def montar_contexto(self, parcela):
        """
        Monta o contexto completo com todas as TAGs disponíveis.

        Args:
            parcela: Instância de Parcela

        Returns:
            dict: Contexto com todas as TAGs preenchidas
        """
        contrato = parcela.contrato
        comprador = contrato.comprador
        imobiliaria = contrato.imovel.imobiliaria
        imovel = contrato.imovel
        hoje = timezone.now()

        # Calcular dias de atraso
        dias_atraso = 0
        if parcela.data_vencimento < hoje.date() and not parcela.pago:
            dias_atraso = (hoje.date() - parcela.data_vencimento).days

        # Montar endereço do comprador
        endereco_comprador = ''
        if comprador.logradouro:
            partes = [comprador.logradouro]
            if comprador.numero:
                partes.append(comprador.numero)
            if comprador.complemento:
                partes.append(f"- {comprador.complemento}")
            if comprador.bairro:
                partes.append(f", {comprador.bairro}")
            if comprador.cidade:
                partes.append(f", {comprador.cidade}")
            if comprador.estado:
                partes.append(f"/{comprador.estado}")
            if comprador.cep:
                partes.append(f" - CEP: {comprador.cep}")
            endereco_comprador = ' '.join(partes)

        # Link para download do boleto
        link_boleto = ''
        if self.base_url and parcela.tem_boleto:
            link_boleto = f"{self.base_url}/financeiro/parcelas/{parcela.pk}/boleto/download/"

        contexto = {
            # Dados do Comprador
            'NOMECOMPRADOR': comprador.nome,
            'CPFCOMPRADOR': comprador.cpf or '',
            'CNPJCOMPRADOR': comprador.cnpj or '',
            'EMAILCOMPRADOR': comprador.email or '',
            'TELEFONECOMPRADOR': comprador.telefone or '',
            'CELULARCOMPRADOR': comprador.celular or '',
            'ENDERECOCOMPRADOR': endereco_comprador,

            # Dados da Imobiliária
            'NOMEIMOBILIARIA': imobiliaria.nome,
            'CNPJIMOBILIARIA': imobiliaria.cnpj or '',
            'TELEFONEIMOBILIARIA': imobiliaria.telefone or '',
            'EMAILIMOBILIARIA': imobiliaria.email or '',

            # Dados do Contrato
            'NUMEROCONTRATO': contrato.numero_contrato,
            'DATACONTRATO': self._formatar_data(contrato.data_contrato),
            'VALORTOTAL': self._formatar_valor(contrato.valor_total),
            'TOTALPARCELAS': str(contrato.numero_parcelas),

            # Dados do Imóvel
            'IMOVEL': imovel.identificacao,
            'LOTEAMENTO': imovel.loteamento or '',
            'ENDERECOIMOVEL': imovel.endereco_formatado if hasattr(imovel, 'endereco_formatado') else '',

            # Dados da Parcela
            'PARCELA': f"{parcela.numero_parcela}/{contrato.numero_parcelas}",
            'NUMEROPARCELA': str(parcela.numero_parcela),
            'VALORPARCELA': self._formatar_valor(parcela.valor_atual),
            'DATAVENCIMENTO': self._formatar_data(parcela.data_vencimento),
            'DIASATRASO': str(dias_atraso),
            'VALORJUROS': self._formatar_valor(parcela.valor_juros),
            'VALORMULTA': self._formatar_valor(parcela.valor_multa),
            'VALORTOTALPARCELA': self._formatar_valor(parcela.valor_total),

            # Dados do Boleto
            'NOSSONUMERO': parcela.nosso_numero or '',
            'LINHADIGITAVEL': parcela.linha_digitavel or '',
            'CODIGOBARRAS': parcela.codigo_barras or '',
            'STATUSBOLETO': parcela.get_status_boleto_display() if hasattr(parcela, 'get_status_boleto_display') else '',
            'VALORBOLETO': self._formatar_valor(parcela.valor_boleto or parcela.valor_atual),

            # Dados do Sistema
            'DATAATUAL': self._formatar_data(hoje.date()),
            'HORAATUAL': hoje.strftime('%H:%M'),
            'LINKBOLETO': link_boleto,
        }

        return contexto

    def enviar_email_boleto(self, parcela, tipo_template, anexar_pdf=True):
        """
        Envia email de notificação de boleto.

        Args:
            parcela: Instância de Parcela
            tipo_template: TipoTemplate (ex: TipoTemplate.BOLETO_CRIADO)
            anexar_pdf: Se True, anexa o PDF do boleto ao email

        Returns:
            dict: Resultado do envio
        """
        try:
            contrato = parcela.contrato
            comprador = contrato.comprador
            imobiliaria = contrato.imovel.imobiliaria

            # Verificar se comprador tem email
            if not comprador.email:
                return {
                    'sucesso': False,
                    'erro': 'Comprador não possui e-mail cadastrado'
                }

            # Verificar preferência de notificação
            if not comprador.notificar_email:
                return {
                    'sucesso': False,
                    'erro': 'Comprador optou por não receber e-mails'
                }

            # Buscar template
            template = TemplateNotificacao.get_template(
                codigo=tipo_template,
                imobiliaria=imobiliaria,
                tipo=TipoNotificacao.EMAIL
            )

            if not template:
                logger.warning(f"Template {tipo_template} não encontrado")
                return {
                    'sucesso': False,
                    'erro': f'Template {tipo_template} não configurado'
                }

            # Montar contexto e renderizar
            contexto = self.montar_contexto(parcela)
            assunto, corpo_texto, corpo_html = template.renderizar(contexto)

            # Criar registro de notificação
            notificacao = Notificacao.objects.create(
                parcela=parcela,
                tipo=TipoNotificacao.EMAIL,
                destinatario=comprador.email,
                assunto=assunto,
                mensagem=corpo_texto,
                status=StatusNotificacao.PENDENTE
            )

            # Enviar email
            try:
                email = EmailMultiAlternatives(
                    subject=assunto,
                    body=corpo_texto,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[comprador.email]
                )

                # Adicionar versão HTML se disponível
                if corpo_html:
                    email.attach_alternative(corpo_html, "text/html")

                # Anexar PDF do boleto se disponível e solicitado
                if anexar_pdf and parcela.boleto_pdf:
                    try:
                        nome_arquivo = f"boleto_{contrato.numero_contrato}_{parcela.numero_parcela}.pdf"
                        email.attach(nome_arquivo, parcela.boleto_pdf.read(), 'application/pdf')
                    except Exception as e:
                        logger.warning(f"Não foi possível anexar PDF: {e}")

                email.send()
                notificacao.marcar_como_enviada()

                logger.info(f"Email de boleto enviado para {comprador.email} - Parcela {parcela.pk}")
                return {
                    'sucesso': True,
                    'notificacao_id': notificacao.pk,
                    'destinatario': comprador.email
                }

            except Exception as e:
                notificacao.marcar_erro(str(e))
                raise

        except Exception as e:
            logger.exception(f"Erro ao enviar email de boleto: {e}")
            return {
                'sucesso': False,
                'erro': str(e)
            }

    def notificar_boleto_criado(self, parcela, anexar_pdf=True):
        """Envia notificação de boleto criado"""
        return self.enviar_email_boleto(
            parcela,
            TipoTemplate.BOLETO_CRIADO,
            anexar_pdf=anexar_pdf
        )

    def notificar_boleto_5_dias(self, parcela):
        """Envia notificação de boleto com 5 dias para vencer"""
        return self.enviar_email_boleto(
            parcela,
            TipoTemplate.BOLETO_5_DIAS,
            anexar_pdf=True
        )

    def notificar_boleto_vence_amanha(self, parcela):
        """Envia notificação de boleto que vence amanhã"""
        return self.enviar_email_boleto(
            parcela,
            TipoTemplate.BOLETO_VENCE_AMANHA,
            anexar_pdf=True
        )

    def notificar_boleto_venceu_ontem(self, parcela):
        """Envia notificação de boleto que venceu ontem"""
        return self.enviar_email_boleto(
            parcela,
            TipoTemplate.BOLETO_VENCEU_ONTEM,
            anexar_pdf=False
        )

    def processar_notificacoes_automaticas(self):
        """
        Processa notificações automáticas de boletos baseado na data de vencimento.
        Deve ser chamado diariamente por um cron job.

        Returns:
            dict: Estatísticas de processamento
        """
        from financeiro.models import Parcela, StatusBoleto

        hoje = date.today()
        amanha = hoje + timedelta(days=1)
        em_5_dias = hoje + timedelta(days=5)
        ontem = hoje - timedelta(days=1)

        stats = {
            '5_dias': {'enviados': 0, 'erros': 0},
            'amanha': {'enviados': 0, 'erros': 0},
            'ontem': {'enviados': 0, 'erros': 0},
        }

        # Parcelas que vencem em 5 dias
        parcelas_5_dias = Parcela.objects.filter(
            data_vencimento=em_5_dias,
            pago=False,
            status_boleto__in=[StatusBoleto.GERADO, StatusBoleto.REGISTRADO]
        ).select_related('contrato', 'contrato__comprador')

        for parcela in parcelas_5_dias:
            # Verificar se já enviou notificação hoje
            ja_enviou = Notificacao.objects.filter(
                parcela=parcela,
                status=StatusNotificacao.ENVIADA,
                assunto__icontains='5 dias'
            ).exists()

            if not ja_enviou:
                resultado = self.notificar_boleto_5_dias(parcela)
                if resultado.get('sucesso'):
                    stats['5_dias']['enviados'] += 1
                else:
                    stats['5_dias']['erros'] += 1

        # Parcelas que vencem amanhã
        parcelas_amanha = Parcela.objects.filter(
            data_vencimento=amanha,
            pago=False,
            status_boleto__in=[StatusBoleto.GERADO, StatusBoleto.REGISTRADO]
        ).select_related('contrato', 'contrato__comprador')

        for parcela in parcelas_amanha:
            ja_enviou = Notificacao.objects.filter(
                parcela=parcela,
                status=StatusNotificacao.ENVIADA,
                assunto__icontains='amanhã'
            ).exists()

            if not ja_enviou:
                resultado = self.notificar_boleto_vence_amanha(parcela)
                if resultado.get('sucesso'):
                    stats['amanha']['enviados'] += 1
                else:
                    stats['amanha']['erros'] += 1

        # Parcelas que venceram ontem
        parcelas_ontem = Parcela.objects.filter(
            data_vencimento=ontem,
            pago=False,
            status_boleto__in=[StatusBoleto.GERADO, StatusBoleto.REGISTRADO, StatusBoleto.VENCIDO]
        ).select_related('contrato', 'contrato__comprador')

        for parcela in parcelas_ontem:
            ja_enviou = Notificacao.objects.filter(
                parcela=parcela,
                status=StatusNotificacao.ENVIADA,
                assunto__icontains='venceu'
            ).exists()

            if not ja_enviou:
                resultado = self.notificar_boleto_venceu_ontem(parcela)
                if resultado.get('sucesso'):
                    stats['ontem']['enviados'] += 1
                else:
                    stats['ontem']['erros'] += 1

        logger.info(f"Notificações automáticas processadas: {stats}")
        return stats


def criar_templates_padrao():
    """
    Cria os templates padrão de notificação de boletos.
    Deve ser executado uma vez na configuração inicial.
    """

    templates = [
        {
            'codigo': TipoTemplate.BOLETO_CRIADO,
            'nome': 'Boleto Gerado',
            'tipo': TipoNotificacao.EMAIL,
            'assunto': 'Boleto Gerado - Parcela %%PARCELA%% - %%NOMEIMOBILIARIA%%',
            'corpo': """Prezado(a) %%NOMECOMPRADOR%%,

Informamos que o boleto referente à parcela %%PARCELA%% do seu contrato foi gerado.

DADOS DO BOLETO:
- Contrato: %%NUMEROCONTRATO%%
- Imóvel: %%IMOVEL%% - %%LOTEAMENTO%%
- Parcela: %%PARCELA%%
- Valor: %%VALORBOLETO%%
- Vencimento: %%DATAVENCIMENTO%%

LINHA DIGITÁVEL:
%%LINHADIGITAVEL%%

O boleto segue em anexo para sua comodidade.

Atenciosamente,
%%NOMEIMOBILIARIA%%
%%TELEFONEIMOBILIARIA%%
%%EMAILIMOBILIARIA%%
""",
            'corpo_html': """
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background-color: #2c3e50; color: white; padding: 20px; text-align: center;">
        <h1 style="margin: 0;">Boleto Gerado</h1>
    </div>

    <div style="padding: 20px;">
        <p>Prezado(a) <strong>%%NOMECOMPRADOR%%</strong>,</p>

        <p>Informamos que o boleto referente à parcela <strong>%%PARCELA%%</strong> do seu contrato foi gerado.</p>

        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #2c3e50;">Dados do Boleto</h3>
            <table style="width: 100%;">
                <tr><td><strong>Contrato:</strong></td><td>%%NUMEROCONTRATO%%</td></tr>
                <tr><td><strong>Imóvel:</strong></td><td>%%IMOVEL%% - %%LOTEAMENTO%%</td></tr>
                <tr><td><strong>Parcela:</strong></td><td>%%PARCELA%%</td></tr>
                <tr><td><strong>Valor:</strong></td><td style="font-size: 18px; color: #27ae60;"><strong>%%VALORBOLETO%%</strong></td></tr>
                <tr><td><strong>Vencimento:</strong></td><td>%%DATAVENCIMENTO%%</td></tr>
            </table>
        </div>

        <div style="background-color: #e8f4f8; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h4 style="margin-top: 0;">Linha Digitável:</h4>
            <code style="font-size: 14px; word-break: break-all;">%%LINHADIGITAVEL%%</code>
        </div>

        <p style="color: #666;">O boleto segue em anexo para sua comodidade.</p>
    </div>

    <div style="background-color: #f1f1f1; padding: 15px; text-align: center; font-size: 12px; color: #666;">
        <p style="margin: 0;"><strong>%%NOMEIMOBILIARIA%%</strong></p>
        <p style="margin: 5px 0;">%%TELEFONEIMOBILIARIA%% | %%EMAILIMOBILIARIA%%</p>
    </div>
</body>
</html>
"""
        },
        {
            'codigo': TipoTemplate.BOLETO_5_DIAS,
            'nome': 'Lembrete - 5 dias para vencimento',
            'tipo': TipoNotificacao.EMAIL,
            'assunto': 'Lembrete: Seu boleto vence em 5 dias - Parcela %%PARCELA%%',
            'corpo': """Prezado(a) %%NOMECOMPRADOR%%,

Este é um lembrete amigável: seu boleto vence em 5 dias!

DADOS DO BOLETO:
- Contrato: %%NUMEROCONTRATO%%
- Parcela: %%PARCELA%%
- Valor: %%VALORBOLETO%%
- Vencimento: %%DATAVENCIMENTO%%

LINHA DIGITÁVEL:
%%LINHADIGITAVEL%%

Evite multas e juros pagando até a data de vencimento.

O boleto segue em anexo.

Atenciosamente,
%%NOMEIMOBILIARIA%%
%%TELEFONEIMOBILIARIA%%
""",
            'corpo_html': ''
        },
        {
            'codigo': TipoTemplate.BOLETO_VENCE_AMANHA,
            'nome': 'Urgente - Boleto vence amanhã',
            'tipo': TipoNotificacao.EMAIL,
            'assunto': 'URGENTE: Seu boleto vence AMANHÃ - Parcela %%PARCELA%%',
            'corpo': """Prezado(a) %%NOMECOMPRADOR%%,

ATENÇÃO: Seu boleto vence AMANHÃ!

DADOS DO BOLETO:
- Contrato: %%NUMEROCONTRATO%%
- Parcela: %%PARCELA%%
- Valor: %%VALORBOLETO%%
- Vencimento: %%DATAVENCIMENTO%%

LINHA DIGITÁVEL:
%%LINHADIGITAVEL%%

Pague hoje para evitar multas e juros!

O boleto segue em anexo.

Atenciosamente,
%%NOMEIMOBILIARIA%%
%%TELEFONEIMOBILIARIA%%
""",
            'corpo_html': ''
        },
        {
            'codigo': TipoTemplate.BOLETO_VENCEU_ONTEM,
            'nome': 'Aviso - Boleto vencido',
            'tipo': TipoNotificacao.EMAIL,
            'assunto': 'AVISO: Boleto vencido - Parcela %%PARCELA%%',
            'corpo': """Prezado(a) %%NOMECOMPRADOR%%,

Identificamos que o boleto da parcela %%PARCELA%% venceu ontem.

DADOS DO BOLETO:
- Contrato: %%NUMEROCONTRATO%%
- Parcela: %%PARCELA%%
- Valor original: %%VALORBOLETO%%
- Vencimento: %%DATAVENCIMENTO%%

A partir de hoje, poderão incidir multa e juros conforme contrato.

Entre em contato conosco para regularização ou emissão de nova via.

Atenciosamente,
%%NOMEIMOBILIARIA%%
%%TELEFONEIMOBILIARIA%%
%%EMAILIMOBILIARIA%%
""",
            'corpo_html': ''
        },
    ]

    created = 0
    for data in templates:
        template, criado = TemplateNotificacao.objects.get_or_create(
            codigo=data['codigo'],
            imobiliaria=None,
            tipo=data['tipo'],
            defaults={
                'nome': data['nome'],
                'assunto': data['assunto'],
                'corpo': data['corpo'],
                'corpo_html': data.get('corpo_html', ''),
                'ativo': True
            }
        )
        if criado:
            created += 1
            logger.info(f"Template criado: {data['nome']}")

    return created
