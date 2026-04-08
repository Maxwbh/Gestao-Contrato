# Estrutura de Testes

Sistema de testes organizados por tipo e aplicação.

**Desenvolvedor:** Maxwell da Silva Oliveira (maxwbh@gmail.com)

## 📁 Estrutura de Diretórios

```
tests/
├── README.md                    # Este arquivo
├── conftest.py                  # Configuração global do pytest
├── pytest.ini                   # Configuração do pytest
├── requirements-test.txt        # Dependências de teste
│
├── unit/                        # Testes unitários (rápidos, isolados)
│   ├── __init__.py
│   ├── core/                    # Testes do app core
│   │   ├── __init__.py
│   │   ├── test_models.py
│   │   ├── test_forms.py
│   │   └── test_validators.py
│   ├── contratos/               # Testes do app contratos
│   │   ├── __init__.py
│   │   ├── test_models.py
│   │   ├── test_forms.py
│   │   └── test_business_logic.py
│   ├── financeiro/              # Testes do app financeiro
│   │   ├── __init__.py
│   │   ├── test_models.py
│   │   ├── test_services.py
│   │   └── test_boleto_service.py
│   ├── accounts/                # Testes de autenticação
│   │   ├── __init__.py
│   │   └── test_permissions.py
│   └── notificacoes/            # Testes de notificações
│       ├── __init__.py
│       └── test_tasks.py
│
├── integration/                 # Testes de integração (APIs externas, DB)
│   ├── __init__.py
│   ├── test_brcobranca_api.py
│   ├── test_banco_central_api.py
│   ├── test_viacep_api.py
│   └── test_database_queries.py
│
├── functional/                  # Testes funcionais (end-to-end)
│   ├── __init__.py
│   ├── test_contrato_workflow.py
│   ├── test_boleto_generation.py
│   ├── test_reajuste_workflow.py
│   └── test_user_journey.py
│
└── fixtures/                    # Fixtures e dados de teste
    ├── __init__.py
    ├── factories.py             # Factory Boy factories
    ├── mock_data.py             # Dados mockados
    └── sample_files/            # Arquivos de exemplo
        ├── boletos/
        └── cnab/
```

## 🧪 Tipos de Testes

### 1. Testes Unitários (`unit/`)
- Testam componentes individuais isolados
- Rápidos (< 1s por teste)
- Não acessam banco de dados real (usam mocks/fixtures)
- Não fazem requisições HTTP reais

**Exemplo:**
```python
# tests/unit/core/test_validators.py
import pytest
from core.validators import validar_cnpj

def test_cnpj_valido():
    assert validar_cnpj('23.456.781/0001-11') == True

def test_cnpj_invalido():
    assert validar_cnpj('00.000.000/0000-00') == False
```

### 2. Testes de Integração (`integration/`)
- Testam integração entre componentes
- Acessam banco de dados real (test database)
- Podem fazer requisições HTTP mockadas
- Médios (~1-5s por teste)

**Exemplo:**
```python
# tests/integration/test_brcobranca_api.py
import pytest
from unittest.mock import patch
from financeiro.services.boleto_service import BoletoService

@pytest.mark.django_db
def test_gerar_boleto_banco_brasil(parcela_factory, conta_bancaria_factory):
    """Testa geração de boleto do Banco do Brasil"""
    parcela = parcela_factory()
    conta = conta_bancaria_factory(banco='001')

    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b'PDF_CONTENT'

        service = BoletoService()
        result = service.gerar_boleto(parcela, conta)

        assert result['sucesso'] is True
        assert result['pdf_content'] is not None
```

### 3. Testes Funcionais (`functional/`)
- Testam fluxos completos end-to-end
- Simulam comportamento real do usuário
- Lentos (~5-30s por teste)
- Usam Django TestCase ou Selenium

**Exemplo:**
```python
# tests/functional/test_contrato_workflow.py
import pytest
from django.test import Client

@pytest.mark.django_db
def test_criar_contrato_completo(user_factory, imobiliaria_factory):
    """Testa criação completa de um contrato"""
    client = Client()
    user = user_factory()
    client.force_login(user)

    # 1. Criar imobiliária
    response = client.post('/imobiliarias/criar/', {...})
    assert response.status_code == 302

    # 2. Criar comprador
    response = client.post('/compradores/criar/', {...})
    assert response.status_code == 302

    # 3. Criar contrato
    response = client.post('/contratos/criar/', {...})
    assert response.status_code == 302

    # 4. Verificar parcelas geradas
    contrato = Contrato.objects.last()
    assert contrato.parcelas.count() == 12
```

## 🏭 Fixtures e Factories

### Factory Boy

Usamos Factory Boy para criar objetos de teste:

```python
# tests/fixtures/factories.py
import factory
from core.models import Imobiliaria, ContaBancaria
from contratos.models import Contrato, Parcela

class ImobiliariaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Imobiliaria

    nome = factory.Sequence(lambda n: f'Imobiliária {n}')
    razao_social = factory.Sequence(lambda n: f'Imobiliária LTDA {n}')
    cnpj = factory.Sequence(lambda n: f'23456781{n:06d}11')
    email = factory.LazyAttribute(lambda obj: f'{obj.nome.lower().replace(" ", "")}@example.com')

class ContaBancariaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ContaBancaria

    imobiliaria = factory.SubFactory(ImobiliariaFactory)
    banco = '001'
    agencia = '1234'
    conta = '567890'
    convenio = '0123456'
    carteira = '18'
    principal = True

class ContratoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Contrato

    numero_contrato = factory.Sequence(lambda n: f'CTR-2023-{n:04d}')
    valor_total = 100000.00
    numero_parcelas = 12
    # ... outros campos
```

## 🚀 Executando os Testes

### Todos os testes
```bash
pytest
```

### Apenas testes unitários (rápido)
```bash
pytest tests/unit/
```

### Apenas testes de integração
```bash
pytest tests/integration/
```

### Apenas testes funcionais
```bash
pytest tests/functional/
```

### Teste específico
```bash
pytest tests/unit/core/test_validators.py::test_cnpj_valido
```

### Com coverage
```bash
pytest --cov=. --cov-report=html
```

### Verbose (detalhado)
```bash
pytest -v
```

### Parar no primeiro erro
```bash
pytest -x
```

## ⚙️ Configuração

### pytest.ini
```ini
[pytest]
DJANGO_SETTINGS_MODULE = gestao_contrato.settings
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --reuse-db
    --nomigrations
    --strict-markers
    -ra
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    functional: marks tests as functional tests
    unit: marks tests as unit tests
```

### conftest.py
```python
# tests/conftest.py
import pytest
from pytest_factoryboy import register
from tests.fixtures.factories import (
    ImobiliariaFactory,
    ContaBancariaFactory,
    ContratoFactory,
    ParcelaFactory,
)

# Registrar factories
register(ImobiliariaFactory)
register(ContaBancariaFactory)
register(ContratoFactory)
register(ParcelaFactory)

@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()

@pytest.fixture
def authenticated_client(user_factory):
    from django.test import Client
    client = Client()
    user = user_factory()
    client.force_login(user)
    return client
```

## 📊 Cobertura de Testes

Meta: **> 80% de cobertura**

```bash
# Gerar relatório de cobertura
pytest --cov=. --cov-report=html --cov-report=term

# Abrir relatório HTML
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

## 🔍 Melhores Práticas

### ✅ DO
- Use factories para criar objetos de teste
- Isole testes unitários (sem DB, sem HTTP)
- Teste casos de sucesso E falha
- Use nomes descritivos para testes
- Mantenha testes simples e focados
- Use fixtures para setup compartilhado

### ❌ DON'T
- Não faça testes dependerem de ordem de execução
- Não use dados hard-coded (use factories)
- Não teste código de terceiros (Django, libs)
- Não crie testes muito lentos sem necessidade
- Não use sleeps (use mocks)

## 🔧 Dependências de Teste

```bash
# tests/requirements-test.txt
pytest==7.4.3
pytest-django==4.7.0
pytest-cov==4.1.0
pytest-mock==3.12.0
pytest-factoryboy==2.6.0
factory-boy==3.3.0
faker==20.1.0
freezegun==1.4.0
responses==0.24.1
```

## 📚 Recursos

- **pytest:** https://docs.pytest.org/
- **pytest-django:** https://pytest-django.readthedocs.io/
- **Factory Boy:** https://factoryboy.readthedocs.io/
- **Django Testing:** https://docs.djangoproject.com/en/stable/topics/testing/

---

**Desenvolvido por:** Maxwell da Silva Oliveira (maxwbh@gmail.com)
**Empresa:** M&S do Brasil LTDA
