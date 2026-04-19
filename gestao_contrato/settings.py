"""
Django settings for gestao_contrato project.
Sistema de Gestão de Contratos de Venda de Imóveis

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
LinkedIn: https://www.linkedin.com/in/maxwbh/
GitHub: https://github.com/Maxwbh/
"""

import os
from pathlib import Path
import dj_database_url
from decouple import config, Csv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

# ALLOWED_HOSTS configuration
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=Csv())

# Se ALLOWED_HOSTS estiver vazio, adicionar padrões
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.onrender.com']
else:
    # Sempre incluir .onrender.com para funcionamento no Render
    if '.onrender.com' not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append('.onrender.com')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party apps
    'crispy_forms',
    'crispy_bootstrap5',
    'django_celery_beat',
    'rest_framework',
    'drf_spectacular',

    # Local apps
    'accounts',
    'core',
    'contratos',
    'financeiro',
    'notificacoes',
    'portal_comprador',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'gestao_contrato.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'gestao_contrato.wsgi.application'

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

if config('DATABASE_URL', default=None):
    DATABASES = {
        'default': dj_database_url.config(
            default=config('DATABASE_URL'),
            # pgBouncer transaction mode: manter conn_max_age=0 para que Django
            # nao tente reutilizar conexoes entre requests (cada transacao pode
            # ir para um backend diferente no pool).
            conn_max_age=0,
            conn_health_checks=False,
        )
    }
    import sys as _sys
    _is_testing = 'pytest' in _sys.modules or (
        len(_sys.argv) > 1 and _sys.argv[1] == 'test'
    )

    if not _is_testing:
        # Usar schema separado para esta aplicacao (compartilhamento de banco)
        # IMPORTANTE: Usar APENAS gestao_contrato (sem public) para evitar
        # conflito com django_migrations da outra aplicacao
        DATABASES['default']['OPTIONS'] = {
            'options': '-c search_path=gestao_contrato'
        }
    else:
        # Testes: usar schema public (sem multi-tenant; evita erros de schema ausente)
        DATABASES['default']['OPTIONS'] = {}

    # Banco de teste: nome fixo, schema public
    DATABASES['default']['TEST'] = {
        'NAME': 'test_gestao_contrato',
    }

    # pgBouncer transaction mode: desabilitar cursores nomeados server-side.
    # Django usa cursores nomeados para iterar querysets grandes (fetchmany),
    # mas pgBouncer pode rotear fetchmany() para um backend diferente do cursor,
    # causando "cursor X does not exist". DISABLE_SERVER_SIDE_CURSORS=True faz
    # Django buscar todas as linhas de uma vez (sem cursor nomeado).
    DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS'] = True

    # Signal para garantir search_path em cada conexao (desabilitado em testes)
    if not _is_testing:
        from django.db.backends.signals import connection_created

        def set_search_path(sender, connection, **kwargs):
            if connection.vendor == 'postgresql':
                cursor = connection.cursor()
                cursor.execute("SET search_path TO gestao_contrato")
        connection_created.connect(set_search_path)
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Login/Logout URLs
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'core:dashboard'
LOGOUT_REDIRECT_URL = 'accounts:login'

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Adicionar STATICFILES_DIRS apenas se o diretório existir
STATICFILES_DIRS = []
static_dir = BASE_DIR / 'static'
if static_dir.exists():
    STATICFILES_DIRS = [static_dir]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Celery Configuration
CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# =============================================================================
# Parâmetros operacionais — valores padrão (bootstrap)
# Estes valores são usados apenas na primeira inicialização ou em testes.
# Em produção, CoreConfig.ready() sobrescreve estas configurações com os
# valores armazenados em ParametroSistema (banco de dados).
# Para alterar em produção: Admin → Gestão Principal → Parâmetros do Sistema.
# =============================================================================

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = 'localhost'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
DEFAULT_FROM_EMAIL = 'noreply@gestaocontrato.com.br'
EMAIL_TIMEOUT = 10

# Twilio Configuration (SMS e WhatsApp)
TWILIO_ACCOUNT_SID = ''
TWILIO_AUTH_TOKEN = ''
TWILIO_PHONE_NUMBER = ''
TWILIO_WHATSAPP_NUMBER = ''
TWILIO_STATUS_CALLBACK_URL = ''

# Bounce Monitoring (IMAP)
BOUNCE_EMAIL_ADDRESS = ''
BOUNCE_IMAP_HOST = 'imap.zoho.com'
BOUNCE_IMAP_PORT = 993
BOUNCE_IMAP_USER = ''
BOUNCE_IMAP_PASSWORD = ''
BOUNCE_IMAP_FOLDER = 'INBOX'

# Supabase (acesso direto via cliente Python, se necessário)
SUPABASE_URL = config('SUPABASE_URL', default='')
SUPABASE_KEY = config('SUPABASE_KEY', default='')

# Modo de Teste
TEST_MODE = False
TEST_RECIPIENT_EMAIL = 'receber@msbrasil.inf.br'
TEST_RECIPIENT_PHONE = '+5531993257479'

# =============================================================================
# REST FRAMEWORK (DRF) + drf-spectacular (Swagger/OpenAPI)
# =============================================================================

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Gestão de Contratos API',
    'DESCRIPTION': (
        'API REST para o sistema de Gestão de Contratos Imobiliários.\n\n'
        '## Autenticação\n'
        'Todas as rotas requerem autenticação via sessão Django (`/accounts/login/`).\n\n'
        '## Módulos\n'
        '- **Financeiro**: parcelas, boletos, CNAB, reajustes, dashboards\n'
        '- **Core**: contabilidades, imobiliárias, compradores, CEP/CNPJ\n'
        '- **Portal Comprador**: contratos, boletos e segunda via\n'
        '- **Tasks**: cron jobs para reajustes, notificações e relatórios\n'
    ),
    'VERSION': '3.1.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'CONTACT': {
        'name': 'Maxwell da Silva Oliveira',
        'email': 'maxwbh@gmail.com',
    },
    'LICENSE': {'name': 'Proprietário — M&S do Brasil LTDA'},
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': False,
    },
    'COMPONENT_SPLIT_REQUEST': True,
    'SORT_OPERATIONS': False,
}

# Notificações
NOTIFICACAO_DIAS_ANTECEDENCIA = 5
NOTIFICACAO_DIAS_INADIMPLENCIA = 3

# Tarefas Agendadas
TASK_TOKEN = None

# BRCobrança
BRCOBRANCA_URL = 'http://localhost:9292'
BRCOBRANCA_TIMEOUT = 30
BRCOBRANCA_MAX_TENTATIVAS = 3
BRCOBRANCA_DELAY_INICIAL = 2

# Portal do Comprador
PORTAL_EMAIL_VERIFICACAO = False

# Aplicação
SITE_URL = 'http://localhost:8000'

# APIs BCB — Índices Econômicos
BCBAPI_URL = 'https://api.bcb.gov.br/dados/serie/bcdata.sgs.{}/dados'
IPCA_SERIE_ID = '433'
IGPM_SERIE_ID = '189'
SELIC_SERIE_ID = '432'

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'console_simple': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'filters': ['require_debug_true'],
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        # App-level loggers
        'financeiro': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'contratos': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'core': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'notificacoes': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Sentry Configuration (opcional)
if config('SENTRY_DSN', default=None):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=config('SENTRY_DSN'),
        integrations=[DjangoIntegration()],
        traces_sample_rate=1.0,
        send_default_pii=True
    )

# Security Settings for Production
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'SAMEORIGIN'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # CSRF Trusted Origins - Required for Django 4.x+ behind HTTPS proxy
    CSRF_TRUSTED_ORIGINS = config(
        'CSRF_TRUSTED_ORIGINS',
        default='https://*.onrender.com',
        cast=Csv()
    )
