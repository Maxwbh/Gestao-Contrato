from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Gestão Principal'

    def ready(self):
        from core.parametros import aplicar_em_settings
        aplicar_em_settings()
