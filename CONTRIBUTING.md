<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/brand/svg/ms-assinatura-horizontal-fundo-escuro.svg">
  <img src="docs/brand/svg/ms-assinatura-horizontal-fundo-claro.svg" alt="M&S do Brasil" height="44">
</picture>

# Guia de Contribuição

Projeto proprietário da **M&S do Brasil LTDA** — contribuições por colaboradores
autorizados. Este guia documenta o fluxo de trabalho do repositório.

## Fluxo de branches

```
feature/qualquer-branch ──PR──▶ hml ──PR (squash, 1 commit)──▶ master
                                │                                │
                          deploy homolog                   deploy produção
                          (versão N-hml)                  (versão oficial)
```

1. **Toda mudança** nasce em uma branch própria e abre **PR para `hml`**
   (o CI bloqueia PRs para `master` que não partam de `hml`).
2. A validação funcional acontece no ambiente de homologação (deploy da
   branch `hml`, versão exibida com sufixo `-hml`).
3. A promoção **`hml` → `master`** é feita por **squash** — a alteração chega
   à main compactada em **1 commit**.
4. **Versionamento:** `MAJOR.MINOR` vem do arquivo `VERSION`; o `PATCH` conta
   apenas commits que alteram **código-fonte**. Commit só de documentação/
   infra **não altera a versão** (lista em `core/version.py::_EXCLUIR_NAO_FONTE`).

## Setup local

Ver [README → Instalação](README.md#instalação) e
[docs/development/SETUP.md](docs/development/SETUP.md). Resumo:

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # preencha conforme docs/deployment/ENV_PARAMETROS.md
python manage.py migrate && python manage.py createsuperuser
python manage.py gerar_dados_teste --limpar   # massa de demonstração
python manage.py runserver
```

## Testes

```bash
pytest tests/unit                 # suíte principal (a mesma do CI)
pytest tests/unit/financeiro      # um módulo específico
```

- O CI roda **por módulo alterado** — mudança só em docs não executa testes.
- Toda mudança de código deve vir com teste cobrindo o comportamento novo.
- Boleto/cobrança: use os mocks e o **boleto fake**
  ([docs/analise/CENARIOS_TESTE_BOLETO_API.md](docs/analise/CENARIOS_TESTE_BOLETO_API.md)) —
  nenhum teste chama API de banco.

## Convenções

- **Commits:** `tipo(escopo): resumo` — ex.: `fix(financeiro): ...`,
  `feat(boleto-api): ...`, `docs(readme): ...`. Mensagens em português.
- **Sem segredos:** nunca versione credenciais/dados reais. O hook
  `scripts/hooks/pre-commit` e o teste `test_security.py` bloqueiam vazamentos
  (ver [SECURITY.md](SECURITY.md)).
- **Estilo:** black · isort · flake8 (config em `pyproject.toml`).
- **Templates Django:** blocos `extra_js` sempre irmãos de `content` (bloco
  aninhado renderiza duas vezes); dados para JS via `|json_script`.

## Documentação e marca

A documentação segue a identidade da **M&S do Brasil**
([guia de marca](docs/brand/README.md)):

- **Tom:** técnico, direto e verificável. Diga o que o sistema faz e mostre o
  comando ou o arquivo; sem adjetivo sobrando nem promessa vaga.
- **Títulos sem emoji.** Marcas de status em tabela (✅ / ⬜) continuam valendo.
- **Logotipo:** use os arquivos de `docs/brand/svg/` sem redesenhar, esticar,
  recolorir ou girar. `fundo-claro` em fundo claro, `fundo-escuro` em fundo
  escuro (no GitHub, o bloco `<picture>` do README troca sozinho). Altura
  mínima da assinatura horizontal: 28 px.
- **Cores:** as de `docs/brand/tokens/tokens.css`. Em badges e diagramas:
  marinho `#0D1B4B`, azul `#1D4ED8`, ciano escuro `#0891B2`, apoio `#5F6C88`.
  Vermelho só como cor funcional de erro (`#B42318`), nunca como destaque.
- **Nomes:** "M&S do Brasil" por extenso na primeira menção; produtos são
  "Gestão de Contratos", "Cobrança-API" e "PyCobrança".

## Segurança

Vulnerabilidades **não** viram issue pública — siga a
[Política de Segurança](SECURITY.md).

---

<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/brand/svg/ms-assinatura-horizontal-fundo-escuro.svg">
  <img src="docs/brand/svg/ms-assinatura-horizontal-fundo-claro.svg" alt="M&S do Brasil" height="36">
</picture>

<sub>Um projeto **M&S do Brasil** · [msbrasil.inf.br](https://msbrasil.inf.br) · contato@msbrasil.inf.br</sub>

</div>
