# Avaliação e Propostas de Melhorias - Gestão de Contratos

**Data:** 2025-11-22
**Projeto:** Sistema de Gestão de Contratos de Venda de Imóveis
**Versão Atual:** Django 4.2.7

---

## Sumário Executivo

O projeto apresenta uma arquitetura sólida e bem estruturada, seguindo boas práticas do Django. No entanto, foram identificadas oportunidades de melhoria em **segurança**, **performance**, **testes** e **manutenibilidade**.

### Pontos Fortes
- Arquitetura multi-tenant bem implementada
- Separação clara de responsabilidades (4 apps)
- Sistema de controle de acesso robusto (AcessoMixin)
- Integração com APIs externas (BCB, Twilio)
- Configurações de segurança em produção
- Uso de Celery para tarefas assíncronas

### Áreas de Melhoria
- Ausência de testes automatizados
- Vulnerabilidades de segurança em endpoints
- Otimizações de queries N+1
- Documentação de API

---

## 1. SEGURANÇA (Prioridade: ALTA)

### 1.1 Remover `@csrf_exempt` da view setup

**Arquivo:** `core/views.py:92`

**Problema:** A view `setup` usa `@csrf_exempt`, o que a torna vulnerável a ataques CSRF.

**Risco:** Um atacante pode executar operações de setup maliciosas forçando um admin a visitar uma página maliciosa.

**Solução:**
```python
# Antes (INSEGURO)
@csrf_exempt
def setup(request):
    ...

# Depois (SEGURO)
@login_required
@require_http_methods(["GET", "POST"])
def setup(request):
    # CSRF token será verificado automaticamente para POST
    ...
```

### 1.2 Validar permissões em endpoints de API

**Arquivo:** `core/views.py`

**Problema:** Alguns endpoints JSON não verificam permissões adequadamente.

**Solução:** Adicionar decorador `@login_required` e verificação de permissões.

```python
@login_required
@require_http_methods(["POST"])
def api_gerar_dados_teste(request):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permissão negada'}, status=403)
    ...
```

### 1.3 Rate Limiting

**Problema:** Não há limitação de taxa nas APIs, permitindo ataques de força bruta.

**Solução:** Implementar `django-ratelimit`:

```python
# requirements.txt
django-ratelimit==4.1.0

# views.py
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='10/m', method='POST')
def api_endpoint(request):
    ...
```

### 1.4 Validação de CPF/CNPJ

**Problema:** Validação atual é apenas formato, não verifica dígitos verificadores.

**Solução:** Usar biblioteca `validate-docbr`:

```python
# requirements.txt
validate-docbr==1.10.0

# validators.py
from validate_docbr import CPF, CNPJ

def validar_cpf(value):
    cpf = CPF()
    if not cpf.validate(value):
        raise ValidationError('CPF inválido')

def validar_cnpj(value):
    cnpj = CNPJ()
    if not cnpj.validate(value):
        raise ValidationError('CNPJ inválido')
```

---

## 2. PERFORMANCE (Prioridade: ALTA)

### 2.1 Otimização de Queries N+1

**Arquivo:** `core/views.py`, `contratos/views.py`

**Problema:** Views listam objetos sem usar `select_related` ou `prefetch_related`.

**Exemplos de correção:**

```python
# Antes
class ContratoListView(LoginRequiredMixin, AcessoMixin, ListView):
    model = Contrato

# Depois
class ContratoListView(LoginRequiredMixin, AcessoMixin, ListView):
    model = Contrato

    def get_queryset(self):
        return super().get_queryset().select_related(
            'imovel',
            'imovel__imobiliaria',
            'comprador'
        ).prefetch_related(
            'parcelas'
        )
```

### 2.2 Cache para Índices Econômicos

**Problema:** Cada requisição consulta o banco para índices que raramente mudam.

**Solução:**

```python
from django.core.cache import cache

def get_indice_atual(tipo):
    cache_key = f'indice_{tipo}'
    indice = cache.get(cache_key)

    if indice is None:
        indice = IndiceReajuste.objects.filter(
            tipo=tipo
        ).order_by('-data_referencia').first()
        cache.set(cache_key, indice, 3600)  # 1 hora

    return indice
```

### 2.3 Paginação Otimizada

**Problema:** Listagens grandes podem causar lentidão.

**Solução:** Usar `paginate_by` em todas as ListViews:

```python
class CompradorListView(LoginRequiredMixin, ListView):
    model = Comprador
    paginate_by = 25
    ordering = ['-criado_em']
```

### 2.4 Índices de Banco de Dados

**Adicionar índices para queries frequentes:**

```python
class Parcela(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['data_vencimento', 'status']),
            models.Index(fields=['contrato', 'status']),
        ]
```

---

## 3. TESTES (Prioridade: ALTA)

### 3.1 Configuração do pytest

**Criar:** `pytest.ini`
```ini
[pytest]
DJANGO_SETTINGS_MODULE = gestao_contrato.settings
python_files = tests.py test_*.py *_tests.py
addopts = -v --tb=short
```

**Adicionar ao requirements.txt:**
```
pytest==7.4.3
pytest-django==4.7.0
pytest-cov==4.1.0
factory-boy==3.3.0
```

### 3.2 Estrutura de Testes Sugerida

```
tests/
├── conftest.py          # Fixtures compartilhadas
├── factories.py         # Factories com factory_boy
├── test_models.py       # Testes de modelos
├── test_views.py        # Testes de views
├── test_forms.py        # Testes de formulários
├── test_services.py     # Testes de serviços
└── test_tasks.py        # Testes de tasks Celery
```

### 3.3 Exemplo de Factory

```python
# tests/factories.py
import factory
from core.models import Contabilidade, Comprador

class ContabilidadeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Contabilidade

    nome = factory.Faker('company', locale='pt_BR')
    cnpj = factory.LazyFunction(lambda: gerar_cnpj_valido())
    email = factory.Faker('company_email')

class CompradorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Comprador

    nome = factory.Faker('name', locale='pt_BR')
    cpf_cnpj = factory.LazyFunction(lambda: gerar_cpf_valido())
    tipo = 'PF'
```

### 3.4 Exemplo de Teste

```python
# tests/test_models.py
import pytest
from decimal import Decimal
from .factories import ContratoFactory, ParcelaFactory

@pytest.mark.django_db
class TestParcela:
    def test_calculo_juros_atraso(self):
        parcela = ParcelaFactory(
            valor_original=Decimal('1000.00'),
            taxa_juros_mensal=Decimal('1.00')
        )
        parcela.calcular_juros(dias_atraso=30)
        assert parcela.valor_juros == Decimal('10.00')

    def test_valor_total_com_multa(self):
        parcela = ParcelaFactory(
            valor_original=Decimal('1000.00'),
            multa_percentual=Decimal('2.00')
        )
        parcela.aplicar_multa()
        assert parcela.valor_total == Decimal('1020.00')
```

---

## 4. QUALIDADE DE CÓDIGO (Prioridade: MÉDIA)

### 4.1 Type Hints

**Adicionar tipagem para melhor documentação e IDE support:**

```python
from typing import Optional, List
from decimal import Decimal

def calcular_reajuste(
    valor_base: Decimal,
    percentual: Decimal,
    tipo: str = 'IPCA'
) -> Decimal:
    """
    Calcula o valor reajustado com base no índice.

    Args:
        valor_base: Valor original a ser reajustado
        percentual: Percentual de reajuste
        tipo: Tipo do índice (IPCA, IGPM, SELIC)

    Returns:
        Valor reajustado
    """
    return valor_base * (1 + percentual / 100)
```

### 4.2 Constantes Centralizadas

**Criar:** `core/constants.py`

```python
from django.db import models

class TipoComprador(models.TextChoices):
    PESSOA_FISICA = 'PF', 'Pessoa Física'
    PESSOA_JURIDICA = 'PJ', 'Pessoa Jurídica'

class StatusParcela(models.TextChoices):
    PENDENTE = 'PENDENTE', 'Pendente'
    PAGA = 'PAGA', 'Paga'
    ATRASADA = 'ATRASADA', 'Atrasada'
    CANCELADA = 'CANCELADA', 'Cancelada'

class TipoIndice(models.TextChoices):
    IPCA = 'IPCA', 'IPCA'
    IGPM = 'IGP-M', 'IGP-M'
    SELIC = 'SELIC', 'SELIC'
    FIXO = 'FIXO', 'Taxa Fixa'
```

### 4.3 Tratamento de Exceções Específicas

```python
# Antes (muito genérico)
try:
    resultado = processar_pagamento(parcela)
except Exception as e:
    logger.error(f"Erro: {e}")

# Depois (específico)
from core.exceptions import PagamentoError, ParcelaJaPagaError

try:
    resultado = processar_pagamento(parcela)
except ParcelaJaPagaError:
    messages.warning(request, 'Esta parcela já foi paga.')
except PagamentoError as e:
    messages.error(request, f'Erro no pagamento: {e}')
    logger.error(f"PagamentoError: {e}", exc_info=True)
```

---

## 5. ARQUITETURA (Prioridade: MÉDIA)

### 5.1 Service Layer

**Criar camada de serviço para isolar lógica de negócio:**

```python
# core/services/contrato_service.py
from typing import List
from decimal import Decimal
from django.db import transaction
from core.models import Contrato, Parcela

class ContratoService:
    @staticmethod
    @transaction.atomic
    def criar_contrato_com_parcelas(
        dados_contrato: dict,
        num_parcelas: int,
        valor_entrada: Decimal = Decimal('0')
    ) -> Contrato:
        """Cria contrato e gera parcelas automaticamente."""
        contrato = Contrato.objects.create(**dados_contrato)

        valor_parcela = (contrato.valor_total - valor_entrada) / num_parcelas

        for i in range(num_parcelas):
            Parcela.objects.create(
                contrato=contrato,
                numero=i + 1,
                valor_original=valor_parcela,
                data_vencimento=calcular_vencimento(contrato.data_inicio, i)
            )

        return contrato

    @staticmethod
    def calcular_saldo_devedor(contrato: Contrato) -> Decimal:
        """Calcula o saldo devedor atual do contrato."""
        return contrato.parcelas.filter(
            status__in=['PENDENTE', 'ATRASADA']
        ).aggregate(
            total=Sum('valor_atual')
        )['total'] or Decimal('0')
```

### 5.2 API REST com Django REST Framework

**Para futuras integrações, considerar adicionar DRF:**

```python
# requirements.txt
djangorestframework==3.14.0
drf-spectacular==0.26.5  # OpenAPI/Swagger

# api/serializers.py
from rest_framework import serializers
from core.models import Contrato, Parcela

class ParcelaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parcela
        fields = ['id', 'numero', 'valor_original', 'valor_atual',
                  'data_vencimento', 'status']

class ContratoSerializer(serializers.ModelSerializer):
    parcelas = ParcelaSerializer(many=True, read_only=True)

    class Meta:
        model = Contrato
        fields = ['id', 'numero', 'valor_total', 'comprador',
                  'imovel', 'parcelas']

# api/views.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

class ContratoViewSet(viewsets.ModelViewSet):
    queryset = Contrato.objects.all()
    serializer_class = ContratoSerializer
    permission_classes = [IsAuthenticated]
```

---

## 6. DEVOPS E MONITORAMENTO (Prioridade: MÉDIA)

### 6.1 Health Check Endpoint

```python
# core/views.py
from django.http import JsonResponse
from django.db import connection

def health_check(request):
    """Endpoint para verificação de saúde da aplicação."""
    status = {
        'status': 'healthy',
        'database': False,
        'redis': False,
    }

    # Verificar banco
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        status['database'] = True
    except Exception:
        status['status'] = 'unhealthy'

    # Verificar Redis
    try:
        from django.core.cache import cache
        cache.set('health_check', '1', 1)
        status['redis'] = cache.get('health_check') == '1'
    except Exception:
        pass

    http_status = 200 if status['status'] == 'healthy' else 503
    return JsonResponse(status, status=http_status)
```

### 6.2 Métricas com Prometheus

```python
# requirements.txt
django-prometheus==2.3.1

# settings.py
INSTALLED_APPS += ['django_prometheus']

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    # ... outros middlewares ...
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]
```

### 6.3 GitHub Actions CI/CD

**Criar:** `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-django pytest-cov

      - name: Run tests
        env:
          DATABASE_URL: postgres://postgres:postgres@localhost:5432/test
          SECRET_KEY: test-secret-key
        run: |
          pytest --cov=. --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## 7. DOCUMENTAÇÃO (Prioridade: BAIXA)

### 7.1 Docstrings Padronizadas

Adotar formato Google style para docstrings:

```python
def processar_reajuste(contrato: Contrato, indice: str) -> Decimal:
    """
    Processa o reajuste de um contrato com base no índice econômico.

    Args:
        contrato: Instância do contrato a ser reajustado.
        indice: Tipo do índice (IPCA, IGPM, SELIC).

    Returns:
        Valor do reajuste aplicado.

    Raises:
        IndiceNaoEncontradoError: Se o índice não estiver disponível.
        ContratoJaReajustadoError: Se o contrato já foi reajustado no período.

    Example:
        >>> contrato = Contrato.objects.get(pk=1)
        >>> valor = processar_reajuste(contrato, 'IPCA')
        >>> print(f"Reajuste: R$ {valor}")
    """
```

### 7.2 API Documentation

Usando `drf-spectacular` para gerar documentação OpenAPI automaticamente.

---

## 8. ROADMAP DE IMPLEMENTAÇÃO

### Fase 1 - Segurança (1-2 semanas)
- [ ] Remover `@csrf_exempt`
- [ ] Adicionar rate limiting
- [ ] Validar CPF/CNPJ com dígitos verificadores
- [ ] Revisar permissões em todos endpoints

### Fase 2 - Performance (1 semana)
- [ ] Implementar `select_related`/`prefetch_related`
- [ ] Adicionar cache para índices econômicos
- [ ] Otimizar paginação
- [ ] Adicionar índices de banco de dados

### Fase 3 - Testes (2-3 semanas)
- [ ] Configurar pytest
- [ ] Criar factories
- [ ] Testes de models (80% coverage)
- [ ] Testes de views críticas
- [ ] Testes de serviços de notificação

### Fase 4 - Qualidade (1-2 semanas)
- [ ] Adicionar type hints
- [ ] Criar camada de serviço
- [ ] Padronizar exceções
- [ ] Refatorar constantes

### Fase 5 - DevOps (1 semana)
- [ ] Implementar health check
- [ ] Configurar CI/CD
- [ ] Adicionar métricas

---

## Conclusão

O projeto está bem estruturado e funcional. As melhorias propostas visam:

1. **Aumentar a segurança** - Correção de vulnerabilidades críticas
2. **Melhorar performance** - Otimizações de banco de dados
3. **Garantir qualidade** - Cobertura de testes automatizados
4. **Facilitar manutenção** - Código mais limpo e documentado

Recomenda-se priorizar as melhorias de **segurança** e **testes** antes de adicionar novas funcionalidades.
