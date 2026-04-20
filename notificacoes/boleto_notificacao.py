"""
Serviço de Notificações para Boletos

Processa templates de email e envia notificações de boletos
usando TAGs como %%NOMECOMPRADOR%%, %%DATAVENCIMENTO%%, etc.

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
import logging
from datetime import date, timedelta
from uuid import uuid4
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from .models import (
    TemplateNotificacao, TipoTemplate, TipoNotificacao,
    Notificacao, StatusNotificacao
)
from .services import ServicoSMS, _destinatario_email_teste, _destinatario_telefone_teste

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
            )

            if not template:
                logger.warning(f"Template {tipo_template} não encontrado")
                return {
                    'sucesso': False,
                    'erro': f'Template {tipo_template} não configurado'
                }

            # Montar contexto
            contexto = self.montar_contexto(parcela)

            # Gerar UUID de rastreamento ANTES de renderizar o template,
            # para que %%LINKBOLETO%% já contenha a URL de click-tracking.
            tracking_uuid = uuid4()
            message_id = f"<{tracking_uuid}@gestao-contrato>"

            link_boleto_original = contexto.get('LINKBOLETO', '')
            if link_boleto_original and self.base_url:
                # Substituir o link pelo URL de click-tracking (sem query string
                # exposta — o destino é reconstruído pelo servidor a partir da parcela)
                contexto['LINKBOLETO'] = (
                    f"{self.base_url}/notificacoes/track/{tracking_uuid}/click/"
                )

            assunto, corpo_texto, corpo_html, _ = template.renderizar(contexto)

            # Aplicar safeguard TEST_MODE (só afeta o envio, não o registro)
            destinatario_final = _destinatario_email_teste(comprador.email)

            # Criar registro de notificação com o destinatário real
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
                # Cabeçalhos: Message-ID (rastreamento) + Return-Path (bounces)
                headers = {'Message-ID': message_id}
                bounce_addr = getattr(settings, 'BOUNCE_EMAIL_ADDRESS', '')
                if bounce_addr:
                    headers['Return-Path'] = bounce_addr
                    headers['Errors-To'] = bounce_addr

                email = EmailMultiAlternatives(
                    subject=assunto,
                    body=corpo_texto,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[destinatario_final],
                    headers=headers,
                )

                # Adicionar versão HTML se disponível
                if corpo_html:
                    email.attach_alternative(corpo_html, "text/html")

                # Anexar PDF do boleto se disponível e solicitado
                # Tenta disco primeiro, depois boleto_pdf_db (banco de dados)
                if anexar_pdf:
                    pdf_bytes = None
                    try:
                        if parcela.boleto_pdf and parcela.boleto_pdf.name:
                            from django.core.files.storage import default_storage
                            if default_storage.exists(parcela.boleto_pdf.name):
                                pdf_bytes = parcela.boleto_pdf.read()
                    except Exception as e:
                        logger.warning(f"Não foi possível ler PDF do disco: {e}")

                    if not pdf_bytes and getattr(parcela, 'boleto_pdf_db', None):
                        try:
                            pdf_bytes = bytes(parcela.boleto_pdf_db)
                        except Exception as e:
                            logger.warning(f"Não foi possível ler PDF do banco: {e}")

                    if pdf_bytes:
                        nome_arquivo = f"boleto_{contrato.numero_contrato}_{parcela.numero_parcela}.pdf"
                        email.attach(nome_arquivo, pdf_bytes, 'application/pdf')
                    else:
                        logger.warning(f"PDF do boleto não disponível para parcela {parcela.pk}")

                email.send()
                notificacao.marcar_como_enviada(external_id=message_id)

                logger.info("Email de boleto enviado para %s - Parcela %s (id=%s)",
                            destinatario_final, parcela.pk, message_id)
                return {
                    'sucesso': True,
                    'notificacao_id': notificacao.pk,
                    'destinatario': destinatario_final
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

    def enviar_sms_boleto(self, parcela, tipo_template):
        """
        Envia SMS de notificação de boleto.

        Args:
            parcela: Instância de Parcela
            tipo_template: TipoTemplate (ex: TipoTemplate.BOLETO_CRIADO)

        Returns:
            dict: Resultado do envio
        """
        try:
            contrato = parcela.contrato
            comprador = contrato.comprador
            imobiliaria = contrato.imovel.imobiliaria

            # Verificar preferência de SMS
            if not comprador.notificar_sms:
                return {'sucesso': False, 'erro': 'Comprador optou por não receber SMS'}

            # Número de celular — preferência: celular, fallback: telefone
            numero_raw = (comprador.celular or comprador.telefone or '').strip()
            if not numero_raw:
                return {'sucesso': False, 'erro': 'Comprador não possui celular/telefone cadastrado'}

            # Normalizar para E.164 (+55DDNNNNNNNNN) exigido pelo Twilio
            import re as _re
            numero = _re.sub(r'\D', '', numero_raw)  # só dígitos
            if len(numero) == 11:          # 31999999999 → +5531999999999
                numero = '+55' + numero
            elif len(numero) == 10:        # 3199999999 → +55319999999 (fixo)
                numero = '+55' + numero
            elif len(numero) == 13 and numero.startswith('55'):
                numero = '+' + numero      # 5531999999999 → +5531999999999
            elif not numero.startswith('+'):
                numero = '+' + numero      # mantém se já tiver código país
            if len(numero) < 12:           # inválido após normalização
                return {'sucesso': False, 'erro': f'Número de telefone inválido: {numero_raw}'}

            # Tentar template SMS no banco de dados
            template = TemplateNotificacao.get_template(
                codigo=tipo_template,
                imobiliaria=imobiliaria,
            )

            if template and template.tem_sms:
                contexto = self.montar_contexto(parcela)
                _, mensagem, _, _ = template.renderizar(contexto)
            else:
                # Mensagem padrão quando não há template SMS configurado
                mensagem = (
                    f"Ola {comprador.nome.split()[0]}, "
                    f"seu boleto parcela {parcela.numero_parcela} "
                    f"valor {self._formatar_valor(parcela.valor_atual)} "
                    f"vence {self._formatar_data(parcela.data_vencimento)}. "
                    f"{imobiliaria.nome}"
                )

            # Safeguard TEST_MODE (só afeta o envio, não o registro)
            numero_final = _destinatario_telefone_teste(numero)

            # Criar registro de notificação com o número real
            notificacao = Notificacao.objects.create(
                parcela=parcela,
                tipo=TipoNotificacao.SMS,
                destinatario=numero,
                assunto=f'SMS Boleto Parcela {parcela.numero_parcela}',
                mensagem=mensagem,
                status=StatusNotificacao.PENDENTE
            )

            try:
                _, sid = ServicoSMS.enviar(destinatario=numero, mensagem=mensagem)
                notificacao.marcar_como_enviada(external_id=sid)
                logger.info("SMS de boleto enviado para %s - Parcela %s (sid=%s)",
                            numero_final, parcela.pk, sid)
                return {
                    'sucesso': True,
                    'notificacao_id': notificacao.pk,
                    'destinatario': numero_final,
                }
            except Exception as e:
                notificacao.marcar_erro(str(e))
                raise

        except Exception as e:
            logger.exception(f"Erro ao enviar SMS de boleto: {e}")
            return {'sucesso': False, 'erro': str(e)}

    def agendar_notificacao_boleto_criado(self, parcela):
        """
        Agenda notificação de boleto criado na fila do banco de dados (sem envio imediato).
        O processamento é feito pelo task `processar_fila_notificacoes` (cron).

        Cria registros Notificacao(status=PENDENTE) para cada canal habilitado
        pelo comprador, mas NÃO tenta enviar. Falhas de template são capturadas
        e logadas sem propagar exceção — a chamada sempre retorna.

        Returns:
            dict: {'agendadas': [<pk>, ...]}
        """
        contrato = parcela.contrato
        comprador = contrato.comprador
        imobiliaria = contrato.imovel.imobiliaria
        agendadas = []

        # --- EMAIL ---
        if comprador.email and getattr(comprador, 'notificar_email', True):
            try:
                template = TemplateNotificacao.get_template(
                    codigo=TipoTemplate.BOLETO_CRIADO,
                    imobiliaria=imobiliaria,
                )
                if template:
                    contexto = self.montar_contexto(parcela)
                    assunto, corpo_sms, corpo_html, _ = template.renderizar(contexto)
                else:
                    assunto = f"Boleto Gerado - Parcela {parcela.numero_parcela}"
                    corpo_sms = f"Boleto da parcela {parcela.numero_parcela} gerado."
                    corpo_html = ''

                notif = Notificacao.objects.create(
                    parcela=parcela,
                    tipo=TipoNotificacao.EMAIL,
                    destinatario=comprador.email,
                    assunto=assunto,
                    mensagem=corpo_html or corpo_sms,
                    status=StatusNotificacao.PENDENTE,
                )
                agendadas.append(notif.pk)
            except Exception as exc:
                logger.exception(
                    "Erro ao agendar email boleto para parcela %s: %s", parcela.pk, exc
                )

        # --- SMS ---
        if getattr(comprador, 'notificar_sms', False):
            try:
                import re as _re
                numero_raw = (getattr(comprador, 'celular', '') or getattr(comprador, 'telefone', '') or '').strip()
                if numero_raw:
                    numero = _re.sub(r'\D', '', numero_raw)
                    if len(numero) == 11:
                        numero = '+55' + numero
                    elif len(numero) == 10:
                        numero = '+55' + numero
                    elif len(numero) == 13 and numero.startswith('55'):
                        numero = '+' + numero
                    elif not numero.startswith('+'):
                        numero = '+' + numero

                    if len(numero) >= 12:
                        template = TemplateNotificacao.get_template(
                            codigo=TipoTemplate.BOLETO_CRIADO,
                            imobiliaria=imobiliaria,
                        )
                        if template and template.tem_sms:
                            contexto = self.montar_contexto(parcela)
                            _, mensagem_sms, _, _ = template.renderizar(contexto)
                        else:
                            mensagem_sms = (
                                f"Ola {comprador.nome.split()[0]}, "
                                f"seu boleto parcela {parcela.numero_parcela} "
                                f"valor {self._formatar_valor(parcela.valor_atual)} "
                                f"vence {self._formatar_data(parcela.data_vencimento)}. "
                                f"{imobiliaria.nome}"
                            )

                        notif = Notificacao.objects.create(
                            parcela=parcela,
                            tipo=TipoNotificacao.SMS,
                            destinatario=numero,
                            assunto=f'SMS Boleto Parcela {parcela.numero_parcela}',
                            mensagem=mensagem_sms,
                            status=StatusNotificacao.PENDENTE,
                        )
                        agendadas.append(notif.pk)
            except Exception as exc:
                logger.exception(
                    "Erro ao agendar SMS boleto para parcela %s: %s", parcela.pk, exc
                )

        # --- WHATSAPP ---
        if getattr(comprador, 'notificar_whatsapp', False):
            try:
                import re as _re
                numero_raw = (getattr(comprador, 'celular', '') or getattr(comprador, 'telefone', '') or '').strip()
                if numero_raw:
                    numero = _re.sub(r'\D', '', numero_raw)
                    if len(numero) == 11:
                        numero = '+55' + numero
                    elif len(numero) == 10:
                        numero = '+55' + numero
                    elif len(numero) == 13 and numero.startswith('55'):
                        numero = '+' + numero
                    elif not numero.startswith('+'):
                        numero = '+' + numero

                    if len(numero) >= 12:
                        template = TemplateNotificacao.get_template(
                            codigo=TipoTemplate.BOLETO_CRIADO,
                            imobiliaria=imobiliaria,
                        )
                        if template and template.tem_whatsapp:
                            contexto = self.montar_contexto(parcela)
                            _, _, _, mensagem_wa = template.renderizar(contexto)
                        else:
                            mensagem_wa = (
                                f"Ola {comprador.nome.split()[0]}, "
                                f"boleto parcela {parcela.numero_parcela} "
                                f"valor {self._formatar_valor(parcela.valor_atual)} "
                                f"vence {self._formatar_data(parcela.data_vencimento)}. "
                                f"{imobiliaria.nome}"
                            )

                        notif = Notificacao.objects.create(
                            parcela=parcela,
                            tipo=TipoNotificacao.WHATSAPP,
                            destinatario=numero,
                            assunto=f'WhatsApp Boleto Parcela {parcela.numero_parcela}',
                            mensagem=mensagem_wa,
                            status=StatusNotificacao.PENDENTE,
                        )
                        agendadas.append(notif.pk)
            except Exception as exc:
                logger.exception(
                    "Erro ao agendar WhatsApp boleto para parcela %s: %s", parcela.pk, exc
                )

        logger.info("Notificações agendadas para parcela %s: pks=%s", parcela.pk, agendadas)
        return {'agendadas': agendadas}

    def notificar_boleto_criado(self, parcela, anexar_pdf=True):
        """Envia notificações de boleto criado (email + SMS conforme preferências do comprador)"""
        return self._notificar(parcela, TipoTemplate.BOLETO_CRIADO, anexar_pdf=anexar_pdf)

    def _notificar(self, parcela, tipo_template, anexar_pdf=True):
        """Helper interno: envia email + SMS (se comprador optar) para um tipo de template."""
        resultado = self.enviar_email_boleto(parcela, tipo_template, anexar_pdf=anexar_pdf)
        comprador = parcela.contrato.comprador
        if comprador.notificar_sms:
            res_sms = self.enviar_sms_boleto(parcela, tipo_template)
            if not res_sms.get('sucesso'):
                logger.warning("SMS não enviado parcela %s: %s", parcela.pk, res_sms.get('erro'))
            resultado['sms'] = res_sms
        return resultado

    def notificar_boleto_5_dias(self, parcela):
        """Envia notificação de boleto com 5 dias para vencer"""
        return self._notificar(parcela, TipoTemplate.BOLETO_5_DIAS, anexar_pdf=True)

    def notificar_boleto_vence_amanha(self, parcela):
        """Envia notificação de boleto que vence amanhã"""
        return self._notificar(parcela, TipoTemplate.BOLETO_VENCE_AMANHA, anexar_pdf=True)

    def notificar_boleto_venceu_ontem(self, parcela):
        """Envia notificação de boleto que venceu ontem"""
        return self._notificar(parcela, TipoTemplate.BOLETO_VENCEU_ONTEM, anexar_pdf=False)

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
    Cria os templates padrão de notificação de boletos (modelo unificado por canal).
    Cada registro contém conteúdo para Email (corpo_html), SMS (corpo) e WhatsApp (corpo_whatsapp).
    """

    templates = [
        {
            'codigo': TipoTemplate.BOLETO_CRIADO,
            'nome': 'Boleto Gerado',
            'assunto': 'Boleto Gerado - Parcela %%PARCELA%% - %%NOMEIMOBILIARIA%%',
            'corpo': (
                '%%NOMEIMOBILIARIA%%: Ola %%NOMECOMPRADOR%%, '
                'boleto parcela %%PARCELA%% '
                'R$%%VALORBOLETO%% vence %%DATAVENCIMENTO%%.'
            ),
            'corpo_html': """<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f8;padding:30px 0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0"
           style="max-width:600px;width:100%;background:#fff;border-radius:8px;
                  overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
      <tr>
        <td style="background:#27ae60;padding:28px 32px;text-align:center;">
          <div style="font-size:32px;margin-bottom:8px;">🏦</div>
          <h1 style="margin:0;color:#fff;font-size:22px;">Boleto Gerado</h1>
          <p style="margin:6px 0 0;color:rgba(255,255,255,.85);font-size:14px;">
            Olá, %%NOMECOMPRADOR%%! Seu boleto está disponível para pagamento.
          </p>
        </td>
      </tr>
      <tr>
        <td style="padding:28px 32px;">
          <table width="100%" cellpadding="0" cellspacing="0"
                 style="border:1px solid #e8eaed;border-radius:6px;overflow:hidden;">
            <tr><td style="background:#f8f9fa;padding:12px 16px;" colspan="2">
              <span style="font-size:12px;font-weight:700;color:#888;text-transform:uppercase;">Detalhes do Boleto</span>
            </td></tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Contrato:</strong></td>
              <td style="padding:8px 16px;color:#222;font-size:14px;border-bottom:1px solid #f0f0f0;text-align:right;">%%NUMEROCONTRATO%%</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Imóvel:</strong></td>
              <td style="padding:8px 16px;color:#222;font-size:14px;border-bottom:1px solid #f0f0f0;text-align:right;">%%IMOVEL%% — %%LOTEAMENTO%%</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Parcela:</strong></td>
              <td style="padding:8px 16px;color:#222;font-size:14px;border-bottom:1px solid #f0f0f0;text-align:right;">%%PARCELA%%</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Vencimento:</strong></td>
              <td style="padding:8px 16px;color:#222;font-size:14px;border-bottom:1px solid #f0f0f0;text-align:right;">%%DATAVENCIMENTO%%</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;"><strong>Valor:</strong></td>
              <td style="padding:8px 16px;font-size:18px;color:#27ae60;font-weight:700;text-align:right;">%%VALORBOLETO%%</td>
            </tr>
          </table>
          <div style="background:#f8f9fa;padding:12px 16px;border-radius:6px;margin:20px 0;">
            <p style="margin:0 0 6px;font-size:12px;font-weight:700;color:#888;text-transform:uppercase;">Linha Digitável</p>
            <code style="font-size:13px;word-break:break-all;color:#333;">%%LINHADIGITAVEL%%</code>
          </div>
          <p style="color:#666;font-size:13px;">O boleto segue em anexo para sua comodidade.</p>
        </td>
      </tr>
      <tr>
        <td style="background:#f8f9fa;padding:16px 32px;text-align:center;border-top:1px solid #e8eaed;">
          <p style="margin:0;font-size:13px;font-weight:700;color:#444;">%%NOMEIMOBILIARIA%%</p>
          <p style="margin:4px 0 0;font-size:12px;color:#888;">%%TELEFONEIMOBILIARIA%% &nbsp;|&nbsp; %%EMAILIMOBILIARIA%%</p>
          <p style="margin:8px 0 0;font-size:11px;color:#bbb;">Você recebe este e-mail por ter uma parcela em aberto.</p>
        </td>
      </tr>
    </table>
  </td></tr>
</table>
</body>
</html>""",
            'corpo_whatsapp': (
                '*%%NOMEIMOBILIARIA%%* — Boleto gerado!\n\n'
                'Olá %%NOMECOMPRADOR%%,\n'
                'Parcela: %%PARCELA%%\n'
                'Valor: %%VALORBOLETO%%\n'
                'Vencimento: %%DATAVENCIMENTO%%\n\n'
                'Linha digitável:\n%%LINHADIGITAVEL%%\n\n'
                'Download: %%LINKBOLETO%%'
            ),
        },
        {
            'codigo': TipoTemplate.BOLETO_5_DIAS,
            'nome': 'Lembrete - 5 dias para vencimento',
            'assunto': 'Lembrete: Seu boleto vence em 5 dias - Parcela %%PARCELA%%',
            'corpo': (
                '%%NOMEIMOBILIARIA%%: Lembrete %%NOMECOMPRADOR%%, '
                'boleto parcela %%PARCELA%% vence em 5 dias '
                'valor %%VALORBOLETO%% data %%DATAVENCIMENTO%%.'
            ),
            'corpo_html': """<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f8;padding:30px 0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0"
           style="max-width:600px;width:100%;background:#fff;border-radius:8px;
                  overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
      <tr>
        <td style="background:#2980b9;padding:28px 32px;text-align:center;">
          <div style="font-size:32px;margin-bottom:8px;">📅</div>
          <h1 style="margin:0;color:#fff;font-size:22px;">Lembrete de Vencimento</h1>
          <p style="margin:6px 0 0;color:rgba(255,255,255,.85);font-size:14px;">
            Olá, %%NOMECOMPRADOR%%! Seu boleto vence em 5 dias.
          </p>
        </td>
      </tr>
      <tr>
        <td style="padding:28px 32px;">
          <table width="100%" cellpadding="0" cellspacing="0"
                 style="border:1px solid #e8eaed;border-radius:6px;overflow:hidden;">
            <tr><td style="background:#f8f9fa;padding:12px 16px;" colspan="2">
              <span style="font-size:12px;font-weight:700;color:#888;text-transform:uppercase;">Detalhes do Boleto</span>
            </td></tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Contrato:</strong></td>
              <td style="padding:8px 16px;color:#222;font-size:14px;border-bottom:1px solid #f0f0f0;text-align:right;">%%NUMEROCONTRATO%%</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Parcela:</strong></td>
              <td style="padding:8px 16px;color:#222;font-size:14px;border-bottom:1px solid #f0f0f0;text-align:right;">%%PARCELA%%</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Vencimento:</strong></td>
              <td style="padding:8px 16px;color:#222;font-size:14px;border-bottom:1px solid #f0f0f0;text-align:right;">%%DATAVENCIMENTO%%</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;"><strong>Valor:</strong></td>
              <td style="padding:8px 16px;font-size:18px;color:#27ae60;font-weight:700;text-align:right;">%%VALORBOLETO%%</td>
            </tr>
          </table>
          <div style="background:#2980b9;color:#fff;padding:12px 16px;border-radius:6px;margin:20px 0;font-size:13px;">
            Efetue o pagamento até %%DATAVENCIMENTO%% para evitar juros e multa.
          </div>
          <div style="background:#f8f9fa;padding:12px 16px;border-radius:6px;margin:16px 0;">
            <p style="margin:0 0 6px;font-size:12px;font-weight:700;color:#888;text-transform:uppercase;">Linha Digitável</p>
            <code style="font-size:13px;word-break:break-all;color:#333;">%%LINHADIGITAVEL%%</code>
          </div>
          <p style="color:#666;font-size:13px;">O boleto segue em anexo para sua comodidade.</p>
        </td>
      </tr>
      <tr>
        <td style="background:#f8f9fa;padding:16px 32px;text-align:center;border-top:1px solid #e8eaed;">
          <p style="margin:0;font-size:13px;font-weight:700;color:#444;">%%NOMEIMOBILIARIA%%</p>
          <p style="margin:4px 0 0;font-size:12px;color:#888;">%%TELEFONEIMOBILIARIA%% &nbsp;|&nbsp; %%EMAILIMOBILIARIA%%</p>
          <p style="margin:8px 0 0;font-size:11px;color:#bbb;">Você recebe este e-mail por ter uma parcela em aberto.</p>
        </td>
      </tr>
    </table>
  </td></tr>
</table>
</body>
</html>""",
            'corpo_whatsapp': (
                '*%%NOMEIMOBILIARIA%%* — Lembrete de vencimento\n\n'
                'Olá %%NOMECOMPRADOR%%,\n'
                'Seu boleto vence em *5 dias*!\n\n'
                'Parcela: %%PARCELA%%\n'
                'Valor: %%VALORBOLETO%%\n'
                'Vencimento: %%DATAVENCIMENTO%%\n\n'
                'Evite multas pagando até a data de vencimento.\n'
                'Download: %%LINKBOLETO%%'
            ),
        },
        {
            'codigo': TipoTemplate.BOLETO_VENCE_AMANHA,
            'nome': 'Urgente - Boleto vence amanhã',
            'assunto': 'URGENTE: Seu boleto vence AMANHÃ - Parcela %%PARCELA%%',
            'corpo': (
                '%%NOMEIMOBILIARIA%%: ATENCAO %%NOMECOMPRADOR%%, '
                'boleto parcela %%PARCELA%% vence AMANHA '
                'valor %%VALORBOLETO%%.'
            ),
            'corpo_html': """<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f8;padding:30px 0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0"
           style="max-width:600px;width:100%;background:#fff;border-radius:8px;
                  overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
      <tr>
        <td style="background:#e67e22;padding:28px 32px;text-align:center;">
          <div style="font-size:32px;margin-bottom:8px;">⏰</div>
          <h1 style="margin:0;color:#fff;font-size:22px;">Boleto Vence AMANHÃ!</h1>
          <p style="margin:6px 0 0;color:rgba(255,255,255,.85);font-size:14px;">
            Olá, %%NOMECOMPRADOR%%! Atenção: seu boleto vence amanhã.
          </p>
        </td>
      </tr>
      <tr>
        <td style="padding:28px 32px;">
          <table width="100%" cellpadding="0" cellspacing="0"
                 style="border:1px solid #e8eaed;border-radius:6px;overflow:hidden;">
            <tr><td style="background:#f8f9fa;padding:12px 16px;" colspan="2">
              <span style="font-size:12px;font-weight:700;color:#888;text-transform:uppercase;">Detalhes do Boleto</span>
            </td></tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Contrato:</strong></td>
              <td style="padding:8px 16px;color:#222;font-size:14px;border-bottom:1px solid #f0f0f0;text-align:right;">%%NUMEROCONTRATO%%</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Parcela:</strong></td>
              <td style="padding:8px 16px;color:#222;font-size:14px;border-bottom:1px solid #f0f0f0;text-align:right;">%%PARCELA%%</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Vencimento:</strong></td>
              <td style="padding:8px 16px;color:#e67e22;font-size:14px;font-weight:700;border-bottom:1px solid #f0f0f0;text-align:right;">%%DATAVENCIMENTO%% (AMANHÃ)</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;"><strong>Valor:</strong></td>
              <td style="padding:8px 16px;font-size:18px;color:#27ae60;font-weight:700;text-align:right;">%%VALORBOLETO%%</td>
            </tr>
          </table>
          <div style="background:#e67e22;color:#fff;padding:12px 16px;border-radius:6px;margin:20px 0;font-size:13px;">
            Pague hoje para evitar multas e juros a partir de amanhã!
          </div>
          <div style="background:#f8f9fa;padding:12px 16px;border-radius:6px;margin:16px 0;">
            <p style="margin:0 0 6px;font-size:12px;font-weight:700;color:#888;text-transform:uppercase;">Linha Digitável</p>
            <code style="font-size:13px;word-break:break-all;color:#333;">%%LINHADIGITAVEL%%</code>
          </div>
          <p style="color:#666;font-size:13px;">O boleto segue em anexo para sua comodidade.</p>
        </td>
      </tr>
      <tr>
        <td style="background:#f8f9fa;padding:16px 32px;text-align:center;border-top:1px solid #e8eaed;">
          <p style="margin:0;font-size:13px;font-weight:700;color:#444;">%%NOMEIMOBILIARIA%%</p>
          <p style="margin:4px 0 0;font-size:12px;color:#888;">%%TELEFONEIMOBILIARIA%% &nbsp;|&nbsp; %%EMAILIMOBILIARIA%%</p>
          <p style="margin:8px 0 0;font-size:11px;color:#bbb;">Você recebe este e-mail por ter uma parcela em aberto.</p>
        </td>
      </tr>
    </table>
  </td></tr>
</table>
</body>
</html>""",
            'corpo_whatsapp': (
                '*%%NOMEIMOBILIARIA%%* — ATENÇÃO!\n\n'
                'Olá %%NOMECOMPRADOR%%,\n'
                'Seu boleto vence *AMANHÃ*!\n\n'
                'Parcela: %%PARCELA%%\n'
                'Valor: %%VALORBOLETO%%\n'
                'Vencimento: %%DATAVENCIMENTO%%\n\n'
                'Pague hoje para evitar multas e juros!\n'
                'Download: %%LINKBOLETO%%'
            ),
        },
        {
            'codigo': TipoTemplate.BOLETO_VENCEU_ONTEM,
            'nome': 'Aviso - Boleto vencido',
            'assunto': 'AVISO: Boleto vencido - Parcela %%PARCELA%%',
            'corpo': (
                '%%NOMEIMOBILIARIA%%: Ola %%NOMECOMPRADOR%%, '
                'boleto parcela %%PARCELA%% venceu em %%DATAVENCIMENTO%%. '
                'Contato: %%TELEFONEIMOBILIARIA%%'
            ),
            'corpo_html': """<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f8;padding:30px 0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0"
           style="max-width:600px;width:100%;background:#fff;border-radius:8px;
                  overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
      <tr>
        <td style="background:#c0392b;padding:28px 32px;text-align:center;">
          <div style="font-size:32px;margin-bottom:8px;">⚠️</div>
          <h1 style="margin:0;color:#fff;font-size:22px;">Boleto Vencido</h1>
          <p style="margin:6px 0 0;color:rgba(255,255,255,.85);font-size:14px;">
            Olá, %%NOMECOMPRADOR%%! Identificamos um boleto em atraso.
          </p>
        </td>
      </tr>
      <tr>
        <td style="padding:28px 32px;">
          <table width="100%" cellpadding="0" cellspacing="0"
                 style="border:1px solid #e8eaed;border-radius:6px;overflow:hidden;">
            <tr><td style="background:#f8f9fa;padding:12px 16px;" colspan="2">
              <span style="font-size:12px;font-weight:700;color:#888;text-transform:uppercase;">Detalhes do Boleto</span>
            </td></tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Contrato:</strong></td>
              <td style="padding:8px 16px;color:#222;font-size:14px;border-bottom:1px solid #f0f0f0;text-align:right;">%%NUMEROCONTRATO%%</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Parcela:</strong></td>
              <td style="padding:8px 16px;color:#222;font-size:14px;border-bottom:1px solid #f0f0f0;text-align:right;">%%PARCELA%%</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Venceu em:</strong></td>
              <td style="padding:8px 16px;color:#c0392b;font-size:14px;font-weight:700;border-bottom:1px solid #f0f0f0;text-align:right;">%%DATAVENCIMENTO%%</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;"><strong>Valor:</strong></td>
              <td style="padding:8px 16px;font-size:18px;color:#c0392b;font-weight:700;text-align:right;">%%VALORBOLETO%%</td>
            </tr>
          </table>
          <div style="background:#c0392b;color:#fff;padding:12px 16px;border-radius:6px;margin:20px 0;font-size:13px;">
            Regularize o pagamento para evitar acréscimo de juros, multa e protesto do título.
          </div>
          <p style="color:#666;font-size:13px;">
            Entre em contato conosco: <strong>%%TELEFONEIMOBILIARIA%%</strong> | %%EMAILIMOBILIARIA%%
          </p>
        </td>
      </tr>
      <tr>
        <td style="background:#f8f9fa;padding:16px 32px;text-align:center;border-top:1px solid #e8eaed;">
          <p style="margin:0;font-size:13px;font-weight:700;color:#444;">%%NOMEIMOBILIARIA%%</p>
          <p style="margin:4px 0 0;font-size:12px;color:#888;">%%TELEFONEIMOBILIARIA%% &nbsp;|&nbsp; %%EMAILIMOBILIARIA%%</p>
          <p style="margin:8px 0 0;font-size:11px;color:#bbb;">Você recebe este e-mail por ter uma parcela em aberto.</p>
        </td>
      </tr>
    </table>
  </td></tr>
</table>
</body>
</html>""",
            'corpo_whatsapp': (
                '*%%NOMEIMOBILIARIA%%* — Boleto vencido\n\n'
                'Olá %%NOMECOMPRADOR%%,\n'
                'O boleto da parcela %%PARCELA%% venceu em %%DATAVENCIMENTO%%.\n\n'
                'Poderão incidir multa e juros conforme contrato.\n'
                'Entre em contato para regularização:\n'
                '%%TELEFONEIMOBILIARIA%% | %%EMAILIMOBILIARIA%%'
            ),
        },
    ]

    created = 0
    for data in templates:
        template, criado = TemplateNotificacao.objects.get_or_create(
            codigo=data['codigo'],
            imobiliaria=None,
            defaults={
                'nome': data['nome'],
                'assunto': data['assunto'],
                'corpo': data['corpo'],
                'corpo_html': data.get('corpo_html', ''),
                'corpo_whatsapp': data.get('corpo_whatsapp', ''),
                'ativo': True,
            }
        )
        if criado:
            created += 1
            logger.info(f"Template criado: {data['nome']}")

    return created
