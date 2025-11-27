# Guia de Contribuição

Obrigado por considerar contribuir para o Sistema de Gestão de Contratos! Este documento fornece diretrizes para contribuir com o projeto.

**Desenvolvedor:** Maxwell da Silva Oliveira (maxwbh@gmail.com)

## 📋 Índice

- [Código de Conduta](#código-de-conduta)
- [Como Contribuir](#como-contribuir)
- [Processo de Desenvolvimento](#processo-de-desenvolvimento)
- [Padrões de Código](#padrões-de-código)
- [Commits e Versionamento](#commits-e-versionamento)
- [Testes](#testes)
- [Documentação](#documentação)

---

## 🤝 Código de Conduta

Este projeto adere a um Código de Conduta. Ao participar, espera-se que você o respeite. Leia o [Código de Conduta](../CODE_OF_CONDUCT.md) completo.

---

## 💡 Como Contribuir

### Reportar Bugs

Ao reportar bugs, inclua:

- **Descrição clara** do problema
- **Passos para reproduzir** o erro
- **Comportamento esperado** vs **comportamento atual**
- **Ambiente:** SO, versão do Python, versão do Django
- **Screenshots** se aplicável
- **Logs de erro** completos

**Template:**
```markdown
**Descrição**
Descrição clara e concisa do bug.

**Para Reproduzir**
Passos para reproduzir o comportamento:
1. Ir para '...'
2. Clicar em '...'
3. Ver erro

**Comportamento Esperado**
O que você esperava que acontecesse.

**Screenshots**
Se aplicável, adicione screenshots.

**Ambiente:**
- OS: [ex: Ubuntu 22.04]
- Python: [ex: 3.11.5]
- Django: [ex: 4.2.7]

**Contexto Adicional**
Qualquer outra informação sobre o problema.
```

### Sugerir Melhorias

Para sugerir melhorias:

- Use as **Issues** do GitHub
- Descreva o benefício da melhoria
- Forneça exemplos de uso
- Considere o impacto em código existente

### Pull Requests

1. **Fork** o repositório
2. Crie uma **branch** para sua feature (`git checkout -b feature/AmazingFeature`)
3. **Commit** suas mudanças (veja [Commits](#commits-e-versionamento))
4. **Push** para a branch (`git push origin feature/AmazingFeature`)
5. Abra um **Pull Request**

**Checklist do PR:**
- [ ] Código segue os padrões do projeto
- [ ] Testes foram adicionados/atualizados
- [ ] Testes passam (`pytest`)
- [ ] Documentação foi atualizada
- [ ] Commit messages seguem o padrão
- [ ] Versão foi incrementada (se aplicável)

---

## 🔄 Processo de Desenvolvimento

### 1. Configurar Ambiente

```bash
# Clone o repositório
git clone https://github.com/Maxwbh/Gestao-Contrato.git
cd Gestao-Contrato

# Crie ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instale dependências de desenvolvimento
pip install -e ".[dev]"

# Configure pre-commit hooks (recomendado)
pip install pre-commit
pre-commit install
```

### 2. Criar Branch

Use prefixos semânticos:

```bash
git checkout -b feature/nome-da-feature    # Nova funcionalidade
git checkout -b fix/corrigir-bug           # Correção de bug
git checkout -b docs/atualizar-readme      # Documentação
git checkout -b refactor/melhorar-codigo   # Refatoração
git checkout -b test/adicionar-testes      # Testes
```

### 3. Desenvolver

- Escreva código limpo e legível
- Siga os padrões de código
- Adicione/atualize testes
- Atualize documentação

### 4. Testar

```bash
# Executar todos os testes
pytest

# Testes com cobertura
pytest --cov=. --cov-report=html

# Linting
black .
isort .
flake8 .
```

### 5. Commit

```bash
# Incrementar versão (se mudança significativa)
python bump_version.py patch  # 1.0.0 -> 1.0.1

# Commit com mensagem descritiva
git add .
git commit -m "feat: adiciona nova funcionalidade X

Descrição detalhada da mudança.

Desenvolvedor: Maxwell da Silva Oliveira <maxwbh@gmail.com>"
```

### 6. Push e PR

```bash
git push origin feature/nome-da-feature
```

Abra Pull Request no GitHub com:
- Título claro
- Descrição detalhada
- Referência a issues relacionadas

---

## 📐 Padrões de Código

### Python

- **PEP 8** com adaptações
- **Line length:** 100 caracteres
- **Formatador:** Black
- **Import sorting:** isort
- **Linting:** flake8, pylint
- **Type hints:** Recomendado mas não obrigatório

**Exemplo:**
```python
from typing import Optional, Dict, Any

def calcular_parcela(
    valor_total: float,
    numero_parcelas: int,
    taxa_juros: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calcula o valor da parcela.

    Args:
        valor_total: Valor total do contrato
        numero_parcelas: Número de parcelas
        taxa_juros: Taxa de juros (opcional)

    Returns:
        Dicionário com valor da parcela e informações
    """
    valor_parcela = valor_total / numero_parcelas

    if taxa_juros:
        valor_parcela *= (1 + taxa_juros / 100)

    return {
        'valor_parcela': round(valor_parcela, 2),
        'numero_parcelas': numero_parcelas,
        'valor_total': valor_total
    }
```

### Django

- **Models:** Sempre adicione `verbose_name` e `help_text`
- **Views:** Prefira Class-Based Views
- **Forms:** Use Crispy Forms quando possível
- **Templates:** Use template inheritance
- **URLs:** Use `name` em todas as URLs

### JavaScript

- **ES6+** quando possível
- **Indentação:** 2 espaços
- **Evite global scope**
- **Use `const`/`let`, não `var`**

---

## 💬 Commits e Versionamento

### Mensagens de Commit

Siga o formato **Conventional Commits**:

```
<tipo>: <descrição curta>

<corpo opcional>

<footer opcional>
```

**Tipos:**
- `feat`: Nova funcionalidade
- `fix`: Correção de bug
- `docs`: Apenas documentação
- `style`: Formatação, ponto e vírgula, etc
- `refactor`: Refatoração de código
- `test`: Adicionar/corrigir testes
- `chore`: Manutenção, configuração

**Exemplos:**
```bash
feat: adiciona geração de boletos Sicoob

Implementa integração com API BRCobranca para gerar
boletos do banco Sicoob.

Desenvolvedor: Maxwell da Silva Oliveira <maxwbh@gmail.com>
```

```bash
fix: corrige erro 500 na geração de boletos

Remove campo numero_documento não suportado pelo BRCobranca.

Closes #123
```

### Versionamento Semântico

O projeto usa [Semantic Versioning](https://semver.org/):

**MAJOR.MINOR.PATCH** (ex: 1.2.3)

- **MAJOR:** Mudanças incompatíveis na API
- **MINOR:** Nova funcionalidade compatível
- **PATCH:** Correções de bugs compatíveis

**Incrementar versão:**
```bash
python bump_version.py patch  # 1.0.0 -> 1.0.1
python bump_version.py minor  # 1.0.0 -> 1.1.0
python bump_version.py major  # 1.0.0 -> 2.0.0
```

---

## 🧪 Testes

### Estrutura

```
tests/
├── unit/           # Testes unitários (rápidos, isolados)
├── integration/    # Testes de integração
├── functional/     # Testes end-to-end
└── fixtures/       # Factories e dados de teste
```

### Escrever Testes

```python
import pytest
from decimal import Decimal

def test_calcular_juros(parcela_factory):
    """Deve calcular juros corretamente"""
    # Arrange
    parcela = parcela_factory(
        valor_original=Decimal('1000.00'),
        dias_atraso=30
    )

    # Act
    juros = parcela.calcular_juros()

    # Assert
    assert juros == Decimal('10.00')  # 1% ao mês
```

### Cobertura

- **Meta:** > 80% de cobertura
- Execute: `pytest --cov=. --cov-report=html`
- Veja: `open htmlcov/index.html`

---

## 📚 Documentação

### Docstrings

Use formato **Google Style**:

```python
def gerar_boleto(parcela, conta_bancaria):
    """
    Gera boleto para a parcela.

    Args:
        parcela (Parcela): Parcela a gerar boleto
        conta_bancaria (ContaBancaria): Conta para emissão

    Returns:
        dict: Resultado com PDF e dados do boleto

    Raises:
        ValueError: Se dados inválidos
        APIError: Se erro na API

    Example:
        >>> resultado = gerar_boleto(parcela, conta)
        >>> print(resultado['sucesso'])
        True
    """
    pass
```

### README e Docs

- Mantenha README atualizado
- Adicione exemplos práticos
- Documente mudanças breaking
- Atualize docs/ quando adicionar features

---

## ❓ Dúvidas?

- **Email:** maxwbh@gmail.com
- **Issues:** https://github.com/Maxwbh/Gestao-Contrato/issues

---

## 🎉 Agradecimentos

Obrigado por contribuir! Suas contribuições tornam este projeto melhor. 🚀

---

**Desenvolvido por:** Maxwell da Silva Oliveira (maxwbh@gmail.com)
**Empresa:** M&S do Brasil LTDA
