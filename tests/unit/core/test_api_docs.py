"""
Documentação da API (drf-spectacular): garante que o catálogo curado de
endpoints é injetado no schema (a API usa views Django puras, não DRF, então
sem o hook o schema nasceria vazio) e que o Swagger/Redoc respondem.
"""
import pytest
from django.urls import reverse

from gestao_contrato.api_docs import CURATED_PATHS


@pytest.mark.django_db
class TestSchemaCurado:
    def test_schema_expoe_endpoints_curados(self, client):
        r = client.get(reverse('schema'))
        assert r.status_code == 200
        corpo = r.content.decode()
        # Todas as rotas curadas devem aparecer no schema gerado.
        for path in CURATED_PATHS:
            assert path in corpo, f'rota ausente no schema: {path}'

    def test_schema_tem_seguranca_por_cookie(self, client):
        corpo = client.get(reverse('schema')).content.decode()
        assert 'cookieAuth' in corpo and 'sessionid' in corpo

    def test_swagger_ui_responde(self, client):
        assert client.get(reverse('swagger-ui')).status_code == 200

    def test_redoc_responde(self, client):
        assert client.get(reverse('redoc')).status_code == 200
