<div align="center">

# 🏢 Gestão de Contratos

**Sistema Django para gestão de contratos de venda de imóveis** — parcelas, reajustes automáticos, cobrança bancária (CNAB + cobrança registrada), notificações multicanal, portal do comprador e relatórios/BI.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-4.2-092E20?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-12+-4169E1?logo=postgresql&logoColor=white)
![Testes](https://img.shields.io/badge/testes-1683%20passando-2ea44f)
![Versão](https://img.shields.io/badge/vers%C3%A3o-3.1-0058be)
![Licença](https://img.shields.io/badge/licen%C3%A7a-Proprietary-lightgrey)

</div>

---

## 📑 Índice

- [Sobre o Sistema](#-sobre-o-sistema)
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

Plataforma multi-tenant para **contabilidades** que administram múltiplos loteamentos e imobiliárias, com controle completo do ciclo de venda parcelada:

| Entidade | Papel |
|----------|-------|
| **Contabilidade** | Administra múltiplas imobiliárias (topo da hierarquia) |
| **Imobiliária** | Beneficiária/cedente dos contratos e contas bancárias |
| **Imóvel** | Lote, terreno, casa, apartamento ou comercial |
| **Comprador** | Cliente (PF ou PJ) que adquire o imóvel |
| **Contrato** | Parcelas, reajustes, intermediárias, boletos e notificações |

O isolamento por tenant (`get_imobiliarias_usuario()`) garante que cada usuário só enxergue os dados das imobiliárias a que tem acesso.

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
- **CNAB Remessa** (G-08) e **CNAB Retorno** (G-09) com rastreamento de nosso número
- **Carnê** consolidado por contrato (PDF)
- **Registro manual de pagamento**, **quitação/antecipação** com desconto e **conciliação OFX**
- **Webhook Boleto-API** (`/financeiro/webhooks/boleto-api/`) — baixa idempotente por evento, assinatura **HMAC-SHA256**

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

## 🔄 Ciclo Mensal de Cobrança

Três telas dedicadas, orquestradas pelo **Hub "Cobrança do Mês"** (`/financeiro/cobranca/`):

| Passo | Tela | O que faz |
|-------|------|-----------|
| **1. Gerar Boletos** (HU-24) | `/financeiro/boletos/` | Geração em massa por escopo (todos / imobiliária / contrato), quantidade por contrato, Folha/Carnê, intermediárias, com bloqueio por reajuste (HU-06) |
| **2. Gerar Remessa** (HU-23) | `/financeiro/remessa/` | Agrupa por banco/layout (1 arquivo = 1 conta), "Gerar e Baixar", ZIP em lote, marcação de envio. Contas C6/Sicoob (Boleto-API) **não entram no CNAB** — conciliam por webhook |
| **3. Receber Retorno** (HU-23) | `/financeiro/retorno/` | Upload do `.ret` que **já processa a baixa**; rejeições devolvem o boleto para "Gerado" (RN-18) |
| **Fechamento** (HU-26) | `/financeiro/cobranca/conciliacao/` | % conciliado, recebido por origem, aging clicável e reinclusão de rejeitados |

> Detalhes no [Manual do Contador](docs/manual_contador.md) e nas [Histórias de Usuário](docs/analise/historias-usuario/).

---

## 🛠️ Tecnologias

**Backend:** Python 3.11+ · Django 4.2.7 · PostgreSQL · Gunicorn
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

```env
SECRET_KEY=sua-chave-secreta
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://user:password@localhost:5432/gestao_contrato

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
EVENT_WEBHOOK_SECRET=segredo-hmac-do-webhook   # assina X-Signature (HMAC-SHA256)

# Webhook PIX
PIX_WEBHOOK_TOKEN=seu-token-pix

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
│   └── management/commands/  # gerar_dados_teste, setup
├── contratos/                # Contrato, TabelaJurosContrato, PrestacaoIntermediaria, IndiceReajuste
│   └── services/             # rescisao_service, cessao_service
├── financeiro/               # Parcela, Reajuste, EventoPIX, EventoCobrancaApi, ArquivoRemessa/Retorno
│   └── services/             # boleto_service, boleto_api_client, cnab_service, carne_service,
│                             # indices_economicos_service, ofx_service, reajuste_service, relatorio_service
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

**Status:** ✅ **1683 testes** · **Meta de cobertura:** > 80%

Cobertura ampla das HUs (cobrança CNAB, Boleto-API, portal, PWA, relatórios BI, webhooks) e serviços. Detalhes em [/tests/README.md](tests/README.md).

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

**Versão 3.1** · 1683 testes · Última atualização: 2026-07-03

Cobrança Registrada C6/Sicoob (Boleto-API) · Hub Cobrança do Mês · Conciliação & Saúde · Índices com número-índice/acumulados

</div>
