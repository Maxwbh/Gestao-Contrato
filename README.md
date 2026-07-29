<div align="center">

# 🏢 Gestão de Contratos

**Sistema Django para gestão de contratos de venda de imóveis** — parcelas, reajustes automáticos, cobrança bancária (CNAB + cobrança registrada), notificações multicanal, portal do comprador e relatórios/BI.

[![CI](https://github.com/Maxwbh/Gestao-Contrato/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/Maxwbh/Gestao-Contrato/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-6.0-092E20?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-4169E1?logo=postgresql&logoColor=white)
![Testes](https://img.shields.io/badge/testes-1842-2ea44f)
![Versão](https://img.shields.io/badge/vers%C3%A3o-3.2-0058be)
![Licença](https://img.shields.io/badge/licen%C3%A7a-Proprietary-lightgrey)

<img src="docs/screenshots/home.png" alt="Gestão de Contratos — plataforma de contratos, cobrança e reajustes" width="88%">

<br>

**Do contrato à baixa, num só lugar.** &nbsp;•&nbsp; Parcelas e reajustes automáticos &nbsp;•&nbsp; Cobrança registrada Pix / BoletoPix / CNAB &nbsp;•&nbsp; Portal do comprador &nbsp;•&nbsp; BI

</div>

---

## 📑 Índice

- [Sobre o Sistema](#-sobre-o-sistema)
- [Novidades da Versão 3.2](#-novidades-da-versão-32)
- [Novidades da Versão 3.1](#-novidades-da-versão-31)
- [Funcionalidades](#-funcionalidades)
- [Ciclo Mensal de Cobrança](#-ciclo-mensal-de-cobrança)
- [Tecnologias](#️-tecnologias)
- [Instalação](#-instalação)
- [Configuração (.env)](#-configuração-env)
- [Deploy no Render](#-deploy-no-render)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Testes](#-testes)
- [Docker / BRCobrança](#-docker--brcobrança)
- [Contato](#-contato)

---

## 📋 Sobre o Sistema

O **Gestão de Contratos** é uma plataforma **multi-tenant** que cobre todo o ciclo da **venda parcelada de imóveis** — do cadastro do contrato à baixa da cobrança. Foi pensado para **contabilidades** que administram múltiplos loteamentos e imobiliárias, centralizando contratos, parcelas, reajustes, emissão bancária e relacionamento com o comprador em um só lugar.

**Para quem é:** contabilidades, loteadoras e imobiliárias que vendem imóveis em parcelas e precisam controlar reajustes, cobrança registrada (Pix/Boleto/CNAB) e inadimplência com rastreabilidade.

**O que resolve:**
- 🔁 **Reajuste automático** de parcelas por índices oficiais (IPCA/IGP-M/SELIC), com histórico auditável.
- 💳 **Cobrança de ponta a ponta** — CNAB (remessa/retorno) e cobrança registrada C6/Sicoob (Pix, BoletoPix, Pix Automático), com **conciliação** automática.
- 🔔 **Comunicação com o comprador** — notificações por e-mail/SMS/WhatsApp e **portal do comprador** para 2ª via e acompanhamento.
- 📊 **Visão gerencial** — dashboards, aging de inadimplência e relatórios/BI por contabilidade.

Modelo de hierarquia (isolamento por tenant via `get_imobiliarias_usuario()` — cada usuário só enxerga as imobiliárias a que tem acesso):

| Entidade | Papel |
|----------|-------|
| **Contabilidade** | Administra múltiplas imobiliárias (topo da hierarquia) |
| **Imobiliária** | Beneficiária/cedente dos contratos e contas bancárias |
| **Imóvel** | Lote, terreno, casa, apartamento ou comercial |
| **Comprador** | Cliente (PF ou PJ) que adquire o imóvel |
| **Contrato** | Parcelas, reajustes, intermediárias, boletos e notificações |

---

## ✨ Novidades da Versão 3.2

> Cobrança registrada multi-método (épico Boleto-API completo), modernização da plataforma e do pipeline de CI:

- **💠 Cobrança registrada multi-método (BAPI-01..41)** — épico Boleto-API concluído: credenciais bancárias **cifradas** (Fernet) por provedor, onboarding stateless (`bapi_` Bearer), emissão de **Boleto, BoletoPix, Pix avulso (2ª via/quitação), Pix Automático (débito recorrente)** e **carnê registrado** via gateway; máquina de estados da cobrança, webhook HMAC idempotente, polling Sicoob, fila CIP e retentativa de PA agendados no Celery beat.
- **📊 Painel de Conciliação Boleto-API** — % conciliado, distribuição por status, recebido por origem (Webhook / Polling Sicoob / Conciliação Pix / Baixa manual) e recorrências, com escopo multi-tenant; **conciliação financeira** cruzando os recebíveis do banco (`GET /conciliacao`) com as parcelas liquidadas.
- **🔐 Fail-closed nos webhooks** — em produção, webhooks de baixa (`EVENT_WEBHOOK_SECRET`, `PIX_WEBHOOK_TOKEN`) e API de BI respondem 503 quando a chave não está configurada; chaves de IA são env-only (fora do banco).
- **⬆️ Python 3.12 + Django 6.0** — atualização do runtime (de Python 3.11 / Django 4.2 LTS, em fim de vida) e do driver de banco **psycopg 3** (de psycopg2).
- **🔒 Dependências de segurança** — gunicorn 23 (corrige request smuggling), Pillow 11, requests 2.34; celery 5.6, redis 8, django-celery-beat 2.9, crispy-forms 2.6, drf-spectacular 0.30, reportlab 5.
- **⚡ CI por módulo alterado** — o pipeline analisa o diff e roda só os testes dos módulos afetados, em runners paralelos; mudança apenas em documentação/infra não executa testes. PR típico cai de ~5 min para ~30 s–2 min.
- **🏷️ Versão automática robusta** — o número `MAJOR.MINOR.PATCH` (com commit/data) é gravado em build-time (`.build_info`), garantindo exibição correta em produção mesmo sem `git` no runtime.

---

## ✨ Novidades da Versão 3.1

> As grandes atualizações recentes, além da base já consolidada:

- **💳 Cobrança Registrada via Boleto-API** — integração com gateway **C6 Bank / Sicoob** (OAuth + mTLS) para cobrança registrada online, com **conciliação por evento push (webhook)** em vez de CNAB. Feature flag por conta (`ContaBancaria.provider`) mantém o **fluxo CNAB/BRCobrança como padrão seguro**.
- **🧭 Hub "Cobrança do Mês" (HU-25)** — assistente guiado com stepper clicável: *Gerar Boletos → Gerar Remessa → Receber Retorno*, filtros compartilhados e ação encadeada de 1 clique.
- **❤️ Conciliação & Saúde da Cobrança (HU-26)** — painel de fechamento com % conciliado (por valor), recebido por origem (CNAB/PIX/OFX/Manual), aging clicável e reinclusão de rejeitados.
- **📈 Índices econômicos aprimorados** — **número-índice** e **acumulados** visíveis, cálculo exato de variação, backfill de valores imprecisos e importação BCB resiliente a timeout.
- **🎨 Usabilidade dos fluxos de cobrança** — feedback consistente (toasts), avisos de boletos que conciliam por webhook, navegação encadeada, travas anti duplo-submit e validações client-side.

---

## 🚀 Funcionalidades

### 1. Gestão de Entidades
- Cadastro de Contabilidades, Imobiliárias/Beneficiários, Imóveis e Compradores (PF/PJ)
- Contas bancárias por imobiliária com **provedor de cobrança selecionável** (BRCobrança/CNAB, C6, Sicoob)
- CNPJ alfanumérico 2026 (IN RFB 2229/2024)
- **Usuários do sistema** (HU-28): cadastro **restrito a administradores**, com perfil (Administrador × comum), credencial por **senha inicial** (troca obrigatória no 1º acesso) ou **convite por e-mail**, e acessos multi-tenant **limitados ao escopo do cadastrador**. Comprador é separado (entra só pelo portal). Ver [Manual de Usuários](docs/manual_usuarios.md)

### 2. Contratos
- Parcelas geradas automaticamente; dia de vencimento e nº de parcelas configuráveis
- Correção monetária: **IPCA, IGP-M, INCC, IGP-DI, INPC, TR, SELIC ou Fixo**
- Amortização **PRICE ou SAC**; prestações intermediárias (balões)
- **Juros Escalantes** (HU-360): tabela por ciclo com PMT recalculado e bloqueio cascata
- **Rescisão Contratual** (G-11): fruição + multa penal/adm + mora pro rata
- **Cessão de Direitos** (G-12): taxa 3% sobre saldo devedor com novo contrato

### 3. Gestão Financeira
- Geração de parcelas, cálculo de juros/multa por atraso, saldo devedor e histórico de pagamentos
- **Boletos bancários** via BRCobrança (CNAB) **ou** cobrança registrada via **Boleto-API** (C6/Sicoob)
- **Métodos de cobrança por contrato**: Boleto, Carnê, **BoletoPix** (boleto + QR Pix), **Pix Automático** (débito recorrente com agendamento D-2 e retentativa) e **Pix avulso** (2ª via/quitação)
- **CNAB Remessa** (G-08) e **CNAB Retorno** (G-09) com rastreamento de nosso número
- **Carnê** consolidado por contrato (PDF) — via BRCobrança ou **registrado via gateway** (`POST /carne`)
- **Registro manual de pagamento** (sincroniza o status da cobrança registrada), **quitação/antecipação** com desconto e **conciliação OFX**
- **Webhook Boleto-API** (`/financeiro/webhooks/boleto-api/`) — baixa idempotente por evento, assinatura **HMAC-SHA256**, máquina de estados que rejeita eventos fora de ordem
- **Painel de Conciliação Boleto-API** (`/financeiro/cobranca/conciliacao/boleto-api/`) + **conciliação financeira** de recebíveis (HUs BAPI-01..41 em [docs/api/BOLETO_API_HUS.md](docs/api/BOLETO_API_HUS.md))

### 4. Reajuste Automático
- Integração com a **API do Banco Central** (IPCA/IGP-M/SELIC), com número-índice e acumulados
- Reajuste automático por ciclo (padrão 12 meses) ou manual; histórico completo
- Spread, piso e teto configuráveis por contrato; fallback de índice

### 5. Portal do Comprador
- Acesso individual por CPF/senha, dashboard, contratos e **2ª via de boleto**
- **Upload de comprovantes** com validação de magic bytes
- **PWA instalável** (manifest + service worker offline) e **Web Push** (VAPID)
- Isolamento estrito: cada comprador só acessa seus próprios dados

### 6. Notificações e Relatórios
- **E-mail, SMS e WhatsApp** (Twilio) com templates `%%TAG%%` e blocos condicionais
- Régua de vencimento (D-5, D-3, D-1, D0) e de inadimplência (D+3, D+7, D+15)
- Notificação **consolidada por canal** (e-mail/WhatsApp em 1 PDF; SMS um a um)
- Relatórios **Semanal** e **Mensal Consolidado**; **Dashboard Executivo**
- **API BI** (`/financeiro/api/relatorios/posicao/`) para Power BI/Looker/Metabase — Bearer token

### 7. Tarefas Agendadas (cron-job.org)
Endpoints `POST /api/tasks/...` autenticados com `X-Task-Token`: relatório semanal/mensal, notificações, inadimplentes, reajustes e boletos.

### 8. Segurança
- Comparação de tokens em tempo constante (`hmac.compare_digest`) em webhooks PIX/Boleto-API e API BI
- `select_for_update()` + `transaction.atomic()` em pagamentos e aprovações
- Deduplicação atômica de eventos; validação de magic bytes; tenant isolation; API BI *fail-closed*

### 9. Importação de Contratos via IA
Upload de PDF/imagens → extração estruturada com nível de confiança por campo → match de entidades existentes → **revisão humana** → criação atômica e idempotente.

---

## 📸 Telas

| Página de Apresentação | Painel de Conciliação Boleto-API |
|---|---|
| ![Página inicial — hero, indicadores e módulos](docs/screenshots/home.png) | ![Painel de conciliação — % conciliado, origem da baixa e Pix Automático](docs/screenshots/painel-conciliacao.png) |

| Wizard de Contrato (4 etapas) | Cadastro de Usuário do Sistema |
|---|---|
| ![Wizard de contrato — etapa 4 com projeção de parcelas](docs/screenshots/wizard-contrato.png) | ![Cadastro de usuário — perfil, credencial e acessos por escopo](docs/screenshots/cadastro-usuario.png) |

| Gestão de Usuários | |
|---|---|
| ![Lista de usuários com perfil e situação](docs/screenshots/usuarios-lista.png) | |

---

## 🔄 Ciclo Mensal de Cobrança

Três telas dedicadas, orquestradas pelo **Hub "Cobrança do Mês"** (`/financeiro/cobranca/`):

| Passo | Tela | O que faz |
|-------|------|-----------|
| **1. Gerar Boletos** (HU-24) | `/financeiro/boletos/` | Geração em massa por escopo (todos / imobiliária / contrato), quantidade por contrato, Folha/Carnê, intermediárias, com bloqueio por reajuste (HU-06) |
| **2. Gerar Remessa** (HU-23) | `/financeiro/remessa/` | Agrupa por banco/layout (1 arquivo = 1 conta), "Gerar e Baixar", ZIP em lote, marcação de envio. Contas C6/Sicoob (Boleto-API) **não entram no CNAB** — conciliam por webhook |
| **3. Receber Retorno** (HU-23) | `/financeiro/retorno/` | Upload do `.ret` que **já processa a baixa**; rejeições devolvem o boleto para "Gerado" (RN-18) |
| **Fechamento** (HU-26) | `/financeiro/cobranca/conciliacao/` | % conciliado, recebido por origem, aging clicável e reinclusão de rejeitados |
| **Conciliação Boleto-API** (BAPI-38) | `/financeiro/cobranca/conciliacao/boleto-api/` | Trilho da cobrança registrada: status normalizado, origem da baixa (webhook/polling/Pix/manual), fila CIP, recorrências e relatório de recebíveis × sistema |

> Detalhes no [Manual do Contador](docs/manual_contador.md) e nas [Histórias de Usuário](docs/analise/historias-usuario/).

---

## 🛠️ Tecnologias

**Backend:** Python 3.12 · Django 6.0 · PostgreSQL 14+ (psycopg 3) · Gunicorn · Celery + Redis (beat)
**Frontend:** Bootstrap 5 · AG Grid · Font Awesome · PWA (service worker + Web Push)
**Integrações:**
- **Banco Central** — índices econômicos (IPCA/IGP-M/SELIC)
- **BRCobrança** — boletos e arquivos CNAB (Docker self-hosted)
- **Boleto-API** — cobrança registrada C6/Sicoob (OAuth + mTLS)
- **Twilio** — SMS e WhatsApp · **SMTP** — e-mail · **cron-job.org** — agendamento HTTP

---

## 📦 Instalação

```bash
# 1. Clone
git clone https://github.com/Maxwbh/Gestao-Contrato.git
cd Gestao-Contrato

# 2. Ambiente virtual
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Dependências
pip install -r requirements.txt

# 4. Variáveis de ambiente
cp .env.example .env              # edite conforme a seção abaixo

# 5. Migrações + templates + superusuário
python manage.py migrate
python manage.py criar_templates_relatorio
python manage.py shell -c "from notificacoes.boleto_notificacao import criar_templates_padrao; criar_templates_padrao()"
python manage.py createsuperuser

# 6. Estáticos e servidor
python manage.py collectstatic --noinput
python manage.py runserver        # http://localhost:8000

# 7. (opcional) BRCobrança via Docker
docker-compose up -d brcobranca
```

> Dica: `python manage.py gerar_dados_teste --limpar` popula o banco com massa de demonstração (contabilidade, imobiliárias, contratos, boletos e índices reais).

---

## 🔧 Configuração (.env)

> Referência completa (todas as chaves, camadas e defaults): [docs/deployment/ENV_PARAMETROS.md](docs/deployment/ENV_PARAMETROS.md) · modelo pronto: [`.env.example`](.env.example)

```env
SECRET_KEY=sua-chave-secreta
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://user:password@localhost:5432/gestao_contrato

# Cifra das credenciais bancárias / token bapi_ (Fernet; em produção defina!)
CREDENTIALS_ENCRYPTION_KEY=

# Tarefas agendadas (cron-job.org)
TASK_TOKEN=seu-token-secreto

# E-mail
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=seu-email@gmail.com
EMAIL_HOST_PASSWORD=sua-senha-de-app

# Twilio (SMS/WhatsApp)
TWILIO_ACCOUNT_SID=seu-account-sid
TWILIO_AUTH_TOKEN=seu-auth-token
TWILIO_PHONE_NUMBER=+5511999999999
TWILIO_WHATSAPP_NUMBER=whatsapp:+5511999999999

# BRCobrança (boletos/CNAB)
BRCOBRANCA_URL=http://localhost:9292
BRCOBRANCA_INTER_BOLETO_DELAY_MS=100   # pacing entre boletos (anti rate-limit)
BRCOBRANCA_REMESSA_COOLDOWN_S=5        # cooldown boletos → remessa

# Boleto-API (cobrança registrada C6/Sicoob)
BOLETO_API_URL=http://localhost:8001
BOLETO_API_TIMEOUT=30
BOLETO_API_MAX_TENTATIVAS=3
# OBRIGATÓRIOS em produção (fail-closed: vazio + DEBUG=False ⇒ webhook responde 503)
EVENT_WEBHOOK_SECRET=segredo-hmac-do-webhook   # assina X-Signature (HMAC-SHA256)
PIX_WEBHOOK_TOKEN=seu-token-pix

# IA (env-only — não vão para o banco)
ANTHROPIC_API_KEY=          # chatbot, importação de PDF e workflows
GEMINI_API_KEY=             # tier 0 gratuito (opcional)

# API BI (Power BI / Looker / Metabase)
BI_API_TOKEN=seu-token-bi
RELATORIO_INADIMPLENCIA_EMAILS=financeiro@empresa.com
RELATORIO_POSICAO_EMAILS=financeiro@empresa.com

# PWA Web Push (VAPID)
# Gerar: python -c "from py_vapid import Vapid; v=Vapid(); v.generate_keys(); print(v.public_key, v.private_key)"
VAPID_PUBLIC_KEY=...
VAPID_PRIVATE_KEY=...
VAPID_CLAIMS_EMAIL=admin@empresa.com
```

---

## 🚀 Deploy no Render

> **Plano Gratuito** — sem Celery. Tarefas agendadas via **cron-job.org** (HTTP POST autenticado).
>
> ⚠️ **Cobrança registrada (Boleto-API):** os jobs de conciliação/agendamento
> (polling Sicoob, conciliação Pix, fila CIP, Pix Automático D-2 e retentativa)
> são tasks do **Celery beat** (`gestao_contrato/celery.py`) e exigem worker +
> beat rodando (plano com background worker). Sem Celery, a conciliação da
> cobrança registrada fica só por webhook.

O `build.sh` executa automaticamente: `pip install` → `migrate` → templates de relatório e boleto → `collectstatic` → criação dos superusuários.

| Job | URL | Cron |
|-----|-----|------|
| Relatório semanal | `.../api/tasks/relatorio-semanal/` | `0 9 * * 1` |
| Relatório mensal | `.../api/tasks/relatorio-mensal/` | `0 9 1 * *` |
| Notificações | `.../api/tasks/notificacoes/` | `0 8 * * *` |
| Inadimplentes | `.../api/tasks/inadimplentes/` | `0 8 * * *` |
| Reajustes | `.../api/tasks/reajustes/` | `0 1 * * *` |
| Boletos | `.../api/tasks/boletos/` | `0 7 * * *` |

Configure cada job como `POST` com header `X-Task-Token: <TASK_TOKEN>` (mesmo valor do Render). Em produção use `DEBUG=False` e `ALLOWED_HOSTS=.onrender.com`.

---

## 📖 Estrutura do Projeto

```
Gestao-Contrato/
├── gestao_contrato/          # settings, urls, wsgi
├── core/                     # Contabilidade, Imobiliária, Imóvel, Comprador, ContaBancaria (provider)
│   ├── crypto.py             # Fernet — credenciais bancárias e token bapi_ cifrados
│   └── management/commands/  # gerar_dados_teste, sync_params_from_env, setup
├── contratos/                # Contrato, TabelaJurosContrato, PrestacaoIntermediaria, IndiceReajuste
│   └── services/             # rescisao_service, cessao_service, importacao_ia
├── financeiro/               # Parcela, Reajuste, EventoPIX, EventoCobrancaApi, RecorrenciaPix
│   ├── tasks.py              # Celery: reajustes, polling Sicoob, conciliação Pix, CIP, Pix Automático
│   └── services/             # boleto_service, boleto_api_client/_onboarding/_conciliacao, boleto_fake,
│                             # cnab_service, carne_service, indices, ofx, reajuste, relatorio
├── notificacoes/             # Notificacao, TemplateNotificacao, RegraNotificacao
├── portal_comprador/         # AcessoComprador, PushSubscriptionPortal (PWA/Web Push)
├── accounts/                 # Autenticação e permissões
├── templates/                # Telas (cobrança, contratos, portal, componentes)
├── static/                   # Assets, vendors e service worker PWA
├── docs/                     # HUs, mockups, análise técnica e manuais
├── tests/                    # unit / integration / functional / fixtures
├── build.sh · render.yaml · docker-compose.yml · Dockerfile.brcobranca
```

---

## 🧪 Testes

Suíte **pytest** organizada por tipo (unit / integration / functional):

```bash
pytest                        # tudo
pytest tests/unit/            # unitários (rápido)
pytest tests/integration/     # integração
pytest --cov=. --cov-report=html   # cobertura
```

**Status:** ✅ **1842 testes** (1624 unitários no CI por módulo) · **Meta de cobertura:** > 80%

Cobertura ampla das HUs (cobrança CNAB, épico Boleto-API BAPI-01..41, portal, PWA, relatórios BI, webhooks) e serviços. Cenários de teste da cobrança registrada com **boleto fake** (sem API de banco): [docs/analise/CENARIOS_TESTE_BOLETO_API.md](docs/analise/CENARIOS_TESTE_BOLETO_API.md). Detalhes em [/tests/README.md](tests/README.md).

---

## 🐳 Docker / BRCobrança

Versões **customizadas** mantidas por Maxwell da Silva Oliveira:
- **API REST:** https://github.com/Maxwbh/boleto_cnab_api
- **Biblioteca Ruby:** https://github.com/Maxwbh/brcobranca

⚠️ Use **apenas** estes repositórios (não os forks originais).

```bash
docker-compose up -d          # PostgreSQL + BRCobrança API
python manage.py migrate
python manage.py createsuperuser
```

**Ferramentas de dev:** black · isort · flake8 · pylint · mypy · pytest · factory-boy (config em `pyproject.toml`).

---

## 🤝 Contato

**Maxwell da Silva Oliveira** — M&S do Brasil LTDA
📧 maxwbh@gmail.com · 🔗 [LinkedIn](https://www.linkedin.com/in/maxwbh/) · 🐙 [GitHub](https://github.com/Maxwbh/) · 🌐 [msbrasil.inf.br](https://msbrasil.inf.br)

**Licença:** Proprietary

---

<div align="center">

**Versão 3.2** · 1842 testes · Última atualização: 2026-07-17

Cobrança Registrada multi-método C6/Sicoob (épico Boleto-API BAPI-01..41) · Painel de Conciliação · Hub Cobrança do Mês · Índices com número-índice/acumulados

</div>
