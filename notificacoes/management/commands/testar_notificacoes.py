"""
Comando de diagnóstico para testar o envio de e-mail e SMS.

Uso:
    python manage.py testar_notificacoes
    python manage.py testar_notificacoes --email destino@exemplo.com
    python manage.py testar_notificacoes --sms +5531999999999
    python manage.py testar_notificacoes --skip-sms
"""
import traceback
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import send_mail, get_connection


class Command(BaseCommand):
    help = 'Diagnóstico completo de e-mail e SMS — testa configurações e envia mensagem real'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            default=None,
            help='Endereço de e-mail para teste (padrão: TEST_RECIPIENT_EMAIL ou DEFAULT_FROM_EMAIL)',
        )
        parser.add_argument(
            '--sms',
            type=str,
            default=None,
            help='Número de telefone para teste de SMS (padrão: TEST_RECIPIENT_PHONE)',
        )
        parser.add_argument(
            '--skip-sms',
            action='store_true',
            help='Pula o teste de SMS',
        )
        parser.add_argument(
            '--skip-email',
            action='store_true',
            help='Pula o teste de e-mail',
        )

    def _mask(self, value, show=4):
        """Mascara string sensível, mostrando apenas os últimos `show` caracteres."""
        if not value:
            return '(não configurado)'
        s = str(value)
        if len(s) <= show:
            return '*' * len(s)
        return '*' * (len(s) - show) + s[-show:]

    def _secao(self, titulo):
        self.stdout.write('\n' + self.style.HTTP_INFO('=' * 60))
        self.stdout.write(self.style.HTTP_INFO(f'  {titulo}'))
        self.stdout.write(self.style.HTTP_INFO('=' * 60))

    def _ok(self, msg):
        self.stdout.write(self.style.SUCCESS(f'  ✓ {msg}'))

    def _err(self, msg):
        self.stdout.write(self.style.ERROR(f'  ✗ {msg}'))

    def _info(self, label, value):
        self.stdout.write(f'  {label:<30} {value}')

    def handle(self, *args, **options):
        results = {}

        # ------------------------------------------------------------------ #
        # 1. CONFIGURAÇÕES DJANGO
        # ------------------------------------------------------------------ #
        self._secao('1. Configurações Django (settings.py)')
        backend = getattr(settings, 'EMAIL_BACKEND', '(não definido)')
        host = getattr(settings, 'EMAIL_HOST', '(não definido)')
        port = getattr(settings, 'EMAIL_PORT', '(não definido)')
        use_tls = getattr(settings, 'EMAIL_USE_TLS', False)
        use_ssl = getattr(settings, 'EMAIL_USE_SSL', False)
        user = getattr(settings, 'EMAIL_HOST_USER', '')
        password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', '')
        test_mode = getattr(settings, 'TEST_MODE', False)
        test_email = getattr(settings, 'TEST_RECIPIENT_EMAIL', '')
        test_phone = getattr(settings, 'TEST_RECIPIENT_PHONE', '')

        self._info('EMAIL_BACKEND', backend)
        self._info('EMAIL_HOST', host)
        self._info('EMAIL_PORT', str(port))
        self._info('EMAIL_USE_TLS', str(use_tls))
        self._info('EMAIL_USE_SSL', str(use_ssl))
        self._info('EMAIL_HOST_USER', user or '(não configurado)')
        self._info('EMAIL_HOST_PASSWORD', self._mask(password))
        self._info('DEFAULT_FROM_EMAIL', from_email)
        self._info('TEST_MODE', str(test_mode))
        self._info('TEST_RECIPIENT_EMAIL', test_email or '(não configurado)')
        self._info('TEST_RECIPIENT_PHONE', test_phone or '(não configurado)')

        if 'console' in backend.lower():
            self._err(
                'EMAIL_BACKEND está usando ConsoleEmailBackend — '
                'e-mails vão para o log, NÃO são enviados de verdade!\n'
                '  → Defina EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend no .env'
            )
        else:
            self._ok('EMAIL_BACKEND configurado para SMTP')

        # ------------------------------------------------------------------ #
        # 2. ConfiguracaoEmail no banco de dados
        # ------------------------------------------------------------------ #
        self._secao('2. ConfiguracaoEmail (banco de dados)')
        try:
            from notificacoes.models import ConfiguracaoEmail
            configs = ConfiguracaoEmail.objects.all()
            if not configs.exists():
                self._info('Registros', 'Nenhuma configuração cadastrada')
            for cfg in configs:
                status = 'ATIVA' if cfg.ativo else 'inativa'
                self._info(f'  [{status}] {cfg.nome_remetente}', f'{cfg.email_remetente} → {cfg.host}:{cfg.porta}')
            config_ativa = configs.filter(ativo=True).first()
            if config_ativa:
                self._ok(f'Configuração ativa encontrada: {config_ativa.nome_remetente}')
            else:
                self._info('Configuração ativa', 'Nenhuma — será usado settings.py')
        except Exception as e:
            self._err(f'Erro ao consultar ConfiguracaoEmail: {e}')

        # ------------------------------------------------------------------ #
        # 3. TemplateNotificacao — BOLETO_CRIADO
        # ------------------------------------------------------------------ #
        self._secao('3. Templates de Notificação')
        try:
            from notificacoes.models import TemplateNotificacao, TipoTemplate, TipoNotificacao
            codigos_email = [
                TipoTemplate.BOLETO_CRIADO,
                TipoTemplate.BOLETO_5_DIAS,
                TipoTemplate.BOLETO_VENCE_AMANHA,
                TipoTemplate.BOLETO_VENCEU_ONTEM,
            ]
            codigos_sms = [
                TipoTemplate.BOLETO_CRIADO,
                TipoTemplate.BOLETO_5_DIAS,
                TipoTemplate.BOLETO_VENCE_AMANHA,
                TipoTemplate.BOLETO_VENCEU_ONTEM,
            ]
            self._info('E-mail', '')
            for codigo in codigos_email:
                t = TemplateNotificacao.objects.filter(
                    codigo=codigo, tipo=TipoNotificacao.EMAIL
                ).first()
                if t:
                    self._ok(f'[EMAIL] {codigo} ({("ATIVO" if t.ativo else "inativo")})')
                else:
                    self._err(
                        f'[EMAIL] {codigo} NÃO encontrado — notificações falharão silenciosamente!\n'
                        '  → python manage.py shell -c "from notificacoes.boleto_notificacao import criar_templates_padrao; criar_templates_padrao()"'
                    )
            self._info('SMS', '')
            for codigo in codigos_sms:
                t = TemplateNotificacao.objects.filter(
                    codigo=codigo, tipo=TipoNotificacao.SMS
                ).first()
                if t:
                    self._ok(f'[SMS]   {codigo} ({("ATIVO" if t.ativo else "inativo")})')
                else:
                    self._info(f'  [SMS]   {codigo}', 'não configurado (usará mensagem padrão)')
        except Exception as e:
            self._err(f'Erro ao verificar templates: {e}')

        # ------------------------------------------------------------------ #
        # 4. Teste de envio de e-mail direto (send_mail)
        # ------------------------------------------------------------------ #
        if not options['skip_email']:
            self._secao('4. Teste de Envio de E-mail (send_mail direto)')
            destino_email = (
                options['email']
                or test_email
                or from_email
                or 'receber@msbrasil.inf.br'
            )
            self._info('Destinatário', destino_email)
            try:
                enviados = send_mail(
                    subject='[TESTE] Diagnóstico de E-mail — Gestão de Contratos',
                    message=(
                        'Este é um e-mail de teste enviado pelo comando de diagnóstico.\n\n'
                        f'TEST_MODE: {test_mode}\n'
                        f'EMAIL_BACKEND: {backend}\n'
                        f'EMAIL_HOST: {host}:{port}\n'
                        f'DEFAULT_FROM_EMAIL: {from_email}\n'
                    ),
                    from_email=from_email,
                    recipient_list=[destino_email],
                    fail_silently=False,
                )
                if enviados:
                    self._ok(f'E-mail enviado com sucesso para {destino_email}')
                    results['email_direto'] = 'OK'
                else:
                    self._err('send_mail retornou 0 — backend não enviou')
                    results['email_direto'] = 'FALHOU (0 enviados)'
            except Exception as e:
                self._err(f'Falha no envio: {e}')
                self.stdout.write(traceback.format_exc())
                results['email_direto'] = f'ERRO: {e}'

        # ------------------------------------------------------------------ #
        # 5. Teste ServicoEmail.enviar()
        # ------------------------------------------------------------------ #
        if not options['skip_email']:
            self._secao('5. Teste ServicoEmail.enviar() (com TEST_MODE safeguard)')
            destino_email = (
                options['email']
                or test_email
                or from_email
                or 'receber@msbrasil.inf.br'
            )
            self._info('Destinatário (antes safeguard)', destino_email)
            try:
                from notificacoes.services import ServicoEmail, _destinatario_email_teste
                destino_final = _destinatario_email_teste(destino_email)
                self._info('Destinatário (após safeguard)', destino_final)
                ServicoEmail.enviar(
                    destinatario=destino_email,
                    assunto='[TESTE] ServicoEmail — Gestão de Contratos',
                    mensagem=(
                        'Teste via ServicoEmail.enviar().\n\n'
                        f'TEST_MODE: {test_mode}\n'
                        f'Destinatário original: {destino_email}\n'
                        f'Destinatário final: {destino_final}\n'
                    ),
                )
                self._ok(f'ServicoEmail.enviar() executado com sucesso → {destino_final}')
                results['servico_email'] = 'OK'
            except Exception as e:
                self._err(f'Falha: {e}')
                self.stdout.write(traceback.format_exc())
                results['servico_email'] = f'ERRO: {e}'

        # ------------------------------------------------------------------ #
        # 6. Teste de SMS (Twilio)
        # ------------------------------------------------------------------ #
        if not options['skip_sms']:
            self._secao('6. Teste de SMS (Twilio)')
            account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
            auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
            numero_from = getattr(settings, 'TWILIO_PHONE_NUMBER', '')

            self._info('TWILIO_ACCOUNT_SID', self._mask(account_sid, 6))
            self._info('TWILIO_AUTH_TOKEN', self._mask(auth_token))
            self._info('TWILIO_PHONE_NUMBER', numero_from or '(não configurado)')

            if not all([account_sid, auth_token, numero_from]):
                self._err('Credenciais Twilio incompletas — pulando teste de SMS')
                results['sms'] = 'PULADO (credenciais ausentes)'
            else:
                destino_sms = (
                    options['sms']
                    or test_phone
                    or '+5531993257479'
                )
                self._info('Destinatário SMS', destino_sms)
                try:
                    from notificacoes.services import ServicoSMS, _destinatario_telefone_teste
                    destino_final = _destinatario_telefone_teste(destino_sms)
                    self._info('Destinatário (após safeguard)', destino_final)
                    ServicoSMS.enviar(
                        destinatario=destino_sms,
                        mensagem='[TESTE] SMS de diagnóstico — Gestão de Contratos. Pode ignorar.',
                    )
                    self._ok(f'SMS enviado com sucesso → {destino_final}')
                    results['sms'] = 'OK'
                except Exception as e:
                    self._err(f'Falha no envio de SMS: {e}')
                    self.stdout.write(traceback.format_exc())
                    results['sms'] = f'ERRO: {e}'

        # ------------------------------------------------------------------ #
        # 7. Resumo
        # ------------------------------------------------------------------ #
        self._secao('7. Resumo')
        for chave, valor in results.items():
            if valor == 'OK':
                self._ok(f'{chave}: {valor}')
            elif valor.startswith('PULADO'):
                self._info(f'  ⚠ {chave}', valor)
            else:
                self._err(f'{chave}: {valor}')

        if 'console' in backend.lower():
            self.stdout.write(self.style.WARNING(
                '\n  AVISO IMPORTANTE: EMAIL_BACKEND=console — '
                'os e-mails aparecem no log do servidor mas NÃO são entregues.\n'
                '  Adicione ao .env (ou variáveis de ambiente no Render):\n'
                '    EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend\n'
            ))
        self.stdout.write('')
