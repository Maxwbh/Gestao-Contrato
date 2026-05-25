# Sistema de Gestão de Contratos de Venda de Imóveis

Sistema completo desenvolvido em Python/Django para gerenciamento de contratos de venda de imóveis (lotes, terrenos, casas) com funcionalidades avançadas de gestão financeira, reajustes automáticos, notificações e relatórios automáticos.

## 👨‍💻 Desenvolvedor

**Maxwell da Silva Oliveira**
- **E-mail:** maxwbh@gmail.com
- **LinkedIn:** [linkedin.com/in/maxwbh](https://www.linkedin.com/in/maxwbh/)
- **GitHub:** [github.com/Maxwbh](https://github.com/Maxwbh/)
- **Empresa:** M&S do Brasil LTDA
- **Site:** [msbrasil.inf.br](https://msbrasil.inf.br)

## 📋 Sobre o Sistema

Sistema desenvolvido para contabilidades que gerenciam múltiplos loteamentos, permitindo o controle completo de:

- **Contabilidades** → Gerenciam múltiplas imobiliárias
- **Imobiliárias** → Responsáveis financeiros/beneficiários dos contratos
- **Imóveis** → Lotes, terrenos, casas, apartamentos e imóveis comerciais
- **Compradores** → Clientes que adquirem os imóveis
- **Contratos** → Gestão completa com parcelas, reajustes e notificações

## 🚀 Funcionalidades Principais

### 1. Gestão de Entidades
- ✅ Cadastro de Contabilidades
- ✅ Cadastro de Imobiliárias/Beneficiários
- ✅ Cadastro de Imóveis (com tipos: Lote, Terreno, Casa, Apartamento, Comercial)
- ✅ Cadastro de Compradores (com preferências de notificação)

### 2. Sistema de Contratos
- ✅ Criação de contratos de venda
- ✅ Configuração de número de parcelas
- ✅ Definição de dia de vencimento
- ✅ Cálculo de juros e multa
- ✅ Tipos de correção monetária: IPCA, IGP-M, SELIC ou Fixo
- ✅ Prazo de reajuste configurável (padrão: 12 meses)
- ✅ **Juros Escalantes** (HU-360): tabela por ciclo com PMT recalculado e bloqueio cascata
- ✅ **Rescisão Contratual** (G-11): fruição + multa penal/adm + mora pro rata
- ✅ **Cessão de Direitos** (G-12): taxa 3% sobre saldo devedor com novo contrato

### 3. Gestão Financeira
- ✅ Geração automática de parcelas mês a mês
- ✅ Cálculo automático de juros e multa por atraso
- ✅ Registro de pagamentos
- ✅ Controle de saldo devedor
- ✅ Histórico completo de pagamentos
- ✅ **Boletos bancários** via BRCobrança API (integração CNAB)
- ✅ **CNAB Remessa** (G-08): geração de arquivo para banco com rastreamento de nosso número
- ✅ **CNAB Retorno** (G-09): processamento automático de entradas e liquidações bancárias

### 4. Sistema de Reajuste Automático
- ✅ Integração com API do Banco Central do Brasil
- ✅ Busca automática de índices IPCA, IGP-M e SELIC
- ✅ Reajuste automático a cada período configurado
- ✅ Possibilidade de reajuste manual
- ✅ Histórico de reajustes aplicados

### 5. Portal do Comprador
- ✅ Acesso web individual por CPF/senha para compradores
- ✅ Dashboard com resumo de contratos e parcelas
- ✅ Listagem e detalhe de contratos (isolamento por comprador)
- ✅ Segunda via de boletos diretamente no portal
- ✅ APIs JSON para linha digitável, PDF e status de parcelas
- ✅ Isolamento de segurança: comprador só acessa seus próprios dados
- ✅ **Upload de comprovantes de pagamento** com validação magic bytes (PDF/JPG/PNG/WebP)
- ✅ **PWA Instalável** (34.6): manifest.json + service worker com cache offline
- ✅ **Web Push Notifications** (34.6): alertas de vencimento via VAPID/browser push
- ✅ **Mobile-first**: meta tags Apple/Android, theme-color, `display: standalone`

### 6. Sistema de Notificações e Relatórios
- ✅ Notificações por **E-mail**
- ✅ Notificações por **SMS** (via Twilio)
- ✅ Notificações por **WhatsApp** (via Twilio)
- ✅ Templates personalizáveis com TAGs `%%TAG%%`
- ✅ Envio automático antes do vencimento (D-5, D-3, D-1, D0)
- ✅ Régua de inadimplência (D+3, D+7, D+15)
- ✅ **Relatório Semanal** por imobiliária: KPIs de recebimentos, inadimplência e a vencer
- ✅ **Relatório Mensal Consolidado** por contabilidade: tabela por imobiliária com totais
- ✅ Templates HTML responsivos configuráveis pelo Admin
- ✅ **Relatório Agendado de Inadimplência** (34.5): e-mail diário/semanal automático com tabela de parcelas vencidas
- ✅ **Relatório de Posição de Contratos** (34.5): e-mail com anexo Excel ou PDF gerado por `RelatorioService`
- ✅ **API BI** `GET /financeiro/api/relatorios/posicao/` (34.5): JSON/CSV para Power BI, Looker, Metabase — autenticada por Bearer token
- ✅ **Dashboard Executivo** (34.5): gráfico de barras+linha receita prevista/realizada/inadimplência 12 meses, KPIs consolidados, tenant isolation

### 7. Tarefas Automáticas via API (cron-job.org)
- ✅ Endpoints `POST /api/tasks/` autenticados com `X-Task-Token`
- ✅ **Relatório Semanal** → `POST /api/tasks/relatorio-semanal/`
- ✅ **Relatório Mensal** → `POST /api/tasks/relatorio-mensal/` (dia 1 às 09:00 UTC)
- ✅ **Notificações de vencimento** → `POST /api/tasks/notificacoes/`
- ✅ **Inadimplentes** → `POST /api/tasks/inadimplentes/`
- ✅ **Reajustes** → `POST /api/tasks/reajustes/`
- ✅ **Boletos** → `POST /api/tasks/boletos/`

### 8. Segurança Reforçada
- ✅ Comparação de tokens em tempo constante (`hmac.compare_digest`) — previne timing attacks no webhook PIX e API BI
- ✅ `select_for_update()` + `transaction.atomic()` em pagamentos, aprovações de comprovantes e minutas de contrato
- ✅ Deduplicação atômica de eventos PIX via `IntegrityError` (constraint única no BD)
- ✅ Validação de magic bytes em uploads de comprovantes (detecta arquivos disfarçados por extensão)
- ✅ Isolamento de tenant em todas as views financeiras (`get_imobiliarias_usuario()`)
- ✅ API BI fail-closed: retorna 503 quando `BI_API_TOKEN` não configurado em produção

### 9. Importação de Contratos via IA
- ✅ **Upload de PDF ou fotos** (múltiplas imagens) via drag-and-drop — máx 20 MB por arquivo
- ✅ **Extração automática** por Claude API (`claude-opus-4-7`): todos os campos do contrato, Imobiliária, Comprador, Imóvel e Prestações Intermediárias extraídos como JSON estruturado
- ✅ **Nível de confiança** por campo (`ALTO/MEDIO/BAIXO`) — campos incertos destacados no formulário de revisão
- ✅ **Match inteligente** de entidades existentes por CNPJ/CPF/matrícula antes de propor criação de novas
- ✅ **Revisão humana** obrigatória antes do cadastro — formulário pré-preenchido editável
- ✅ **Criação atômica** de todas as entidades em `transaction.atomic()` (Imobiliária → Comprador → Imóvel → Contrato → Intermediárias)
- ✅ **Idempotente** — duplo-submit redireciona sem duplicar entidades

### 10. Recursos Adicionais
- ✅ Dashboard com estatísticas
- ✅ Interface administrativa completa (Django Admin)
- ✅ Sistema de busca e filtros avançados
- ✅ Design responsivo baseado em Bootstrap 5
- ✅ Pronto para deploy no Render (Free Tier)

## 🛠️ Tecnologias Utilizadas

### Backend
- **Python 3.11+**
- **Django 4.2.7** - Framework web
- **PostgreSQL** - Banco de dados
- **Gunicorn** - Servidor WSGI para produção

### Frontend
- **Bootstrap 5** - Framework CSS
- **Font Awesome** - Ícones
- **JavaScript** - Interatividade

### APIs e Serviços
- **Banco Central do Brasil API** - Índices econômicos (IPCA, IGP-M, SELIC)
- **BRCobrança API** - Geração de boletos e arquivos CNAB (Docker self-hosted)
- **Twilio** - SMS e WhatsApp
- **cron-job.org** - Agendador de tarefas HTTP (substitui Celery no free tier)
- **SMTP** - E-mail

## 📦 Instalação e Configuração

### Pré-requisitos
- Python 3.11 ou superior
- PostgreSQL 12+ (para produção)
- Docker (para BRCobrança API)
- Git

### 1. Clone o Repositório
```bash
git clone https://github.com/Maxwbh/Gestao-Contrato.git
cd Gestao-Contrato
```

### 2. Crie um Ambiente Virtual
```bash
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Instale as Dependências
```bash
pip install -r requirements.txt
```

### 4. Configure as Variáveis de Ambiente
```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas configurações:
```env
SECRET_KEY=sua-chave-secreta-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DATABASE_URL=postgresql://user:password@localhost:5432/gestao_contrato

# Token para autenticação das APIs de tarefas (cron-job.org)
TASK_TOKEN=seu-token-secreto

# Configurações de E-mail
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=seu-email@gmail.com
EMAIL_HOST_PASSWORD=sua-senha-de-app

# Twilio (SMS e WhatsApp)
TWILIO_ACCOUNT_SID=seu-account-sid
TWILIO_AUTH_TOKEN=seu-auth-token
TWILIO_PHONE_NUMBER=+5511999999999
TWILIO_WHATSAPP_NUMBER=whatsapp:+5511999999999

# Webhook PIX (token de autenticação para POST /financeiro/api/webhook/pix/)
PIX_WEBHOOK_TOKEN=seu-token-pix

# API BI — Power BI / Looker / Metabase (34.5)
BI_API_TOKEN=seu-token-bi-secreto
RELATORIO_INADIMPLENCIA_EMAILS=financeiro@empresa.com,diretoria@empresa.com
RELATORIO_POSICAO_EMAILS=financeiro@empresa.com

# PWA Web Push — VAPID (34.6)
# Gerar: python -c "from py_vapid import Vapid; v=Vapid(); v.generate_keys(); print(v.public_key, v.private_key)"
VAPID_PUBLIC_KEY=sua-chave-publica-vapid
VAPID_PRIVATE_KEY=sua-chave-privada-vapid
VAPID_CLAIMS_EMAIL=admin@suaempresa.com
```

### 5. Execute as Migrações
```bash
python manage.py migrate
```

### 6. Crie os Templates de E-mail Padrão
```bash
python manage.py criar_templates_relatorio
python manage.py criar_templates_padrao   # templates de boleto/notificação
```

### 7. Crie um Superusuário
```bash
python manage.py createsuperuser
```

### 8. Colete os Arquivos Estáticos
```bash
python manage.py collectstatic
```

### 9. Execute o Servidor de Desenvolvimento
```bash
python manage.py runserver
```

Acesse: `http://localhost:8000`

### 10. Inicie a BRCobrança API (Docker)

```bash
docker-compose up -d brcobranca
```

## 🚀 Deploy no Render

### ⚠️ IMPORTANTE: Plano Gratuito — sem Celery

Este projeto está configurado para funcionar no **Plano Gratuito** do Render usando **cron-job.org** no lugar do Celery para tarefas agendadas.

#### Plano Gratuito (Free Tier)
- ✅ Web Service (Django)
- ✅ PostgreSQL Database
- ✅ Tarefas agendadas via **cron-job.org** (HTTP POST autenticado)
- ❌ Background Workers (Celery) — não suportado

#### Como funciona o agendamento no Free Tier

1. Crie uma conta gratuita em **cron-job.org**
2. Configure cada tarefa como `POST` com header `X-Task-Token: <seu-token>`
3. Configure o mesmo token em `TASK_TOKEN` nas variáveis do Render

| Job | URL | Cron |
|-----|-----|------|
| `gestao-relatorio-semanal` | `.../api/tasks/relatorio-semanal/` | `0 9 * * 1` (toda segunda às 09h UTC) |
| `gestao-relatorio-mensal` | `.../api/tasks/relatorio-mensal/` | `0 9 1 * *` (dia 1 às 09h UTC) |
| `gestao-notificacoes` | `.../api/tasks/notificacoes/` | `0 8 * * *` (diário) |
| `gestao-inadimplentes` | `.../api/tasks/inadimplentes/` | `0 8 * * *` (diário) |
| `gestao-reajustes` | `.../api/tasks/reajustes/` | `0 1 * * *` (01h UTC) |
| `gestao-boletos` | `.../api/tasks/boletos/` | `0 7 * * *` (07h UTC) |

### Configuração Automática

O `build.sh` executa automaticamente:
1. `pip install -r requirements.txt`
2. `python manage.py migrate`
3. `python manage.py criar_templates_relatorio` (templates de relatório)
4. `python manage.py criar_templates_padrao` (templates de boleto/notificação)
5. `python manage.py collectstatic`
6. Criação dos superusuários `maxwbh` e `admin`

### Variáveis de Ambiente no Render

```
SECRET_KEY=(gerar aleatório)
DEBUG=False
ALLOWED_HOSTS=.onrender.com

# Autenticação das APIs de tarefas
TASK_TOKEN=mesmo-token-configurado-no-cronjob

# E-mail
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=seu-email@gmail.com
EMAIL_HOST_PASSWORD=sua-senha-de-app

# Twilio
TWILIO_ACCOUNT_SID=seu-account-sid
TWILIO_AUTH_TOKEN=seu-auth-token
TWILIO_PHONE_NUMBER=+5511999999999
TWILIO_WHATSAPP_NUMBER=whatsapp:+5511999999999

# PIX Webhook
PIX_WEBHOOK_TOKEN=token-secreto-gerado-aleatoriamente

# API BI (Power BI / Looker / Metabase)
BI_API_TOKEN=token-secreto-bi
RELATORIO_INADIMPLENCIA_EMAILS=financeiro@empresa.com
RELATORIO_POSICAO_EMAILS=financeiro@empresa.com

# PWA Web Push (VAPID)
VAPID_PUBLIC_KEY=...
VAPID_PRIVATE_KEY=...
VAPID_CLAIMS_EMAIL=admin@empresa.com
```

## 📖 Estrutura do Projeto

```
Gestao-Contrato/
├── gestao_contrato/          # Configurações do projeto
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/                      # App principal
│   ├── models.py             # Contabilidade, Imobiliária, Imóvel, Comprador
│   ├── tasks.py              # Endpoints das tarefas agendadas
│   ├── views.py
│   └── urls.py
├── contratos/                 # App de contratos
│   ├── models.py             # Contrato, TabelaJurosContrato, PrestacaoIntermediaria, MinutaContrato, TipoAmortizacao
│   └── services/
│       ├── rescisao_service.py
│       └── cessao_service.py
├── financeiro/                # App financeiro
│   ├── models.py             # Parcela, Reajuste, HistoricoPagamento, EventoPIX, ArquivoRemessa, ArquivoRetorno, AcessoBoletoPublico
│   ├── tasks.py              # Celery: relatório inadimplência e posição contratos (34.5)
│   ├── services/
│   │   ├── boleto_service.py
│   │   ├── carne_service.py          # Geração de carnê PDF
│   │   ├── cnab_service.py           # Remessa e Retorno CNAB
│   │   ├── indices_economicos_service.py  # Busca BCB (IPCA/IGP-M/SELIC)
│   │   ├── ofx_service.py            # Importação de extrato OFX
│   │   ├── reajuste_service.py       # Simulação e aplicação de reajuste
│   │   ├── recibo_service.py         # Geração de recibo PDF
│   │   └── relatorio_service.py      # RelatorioService + FiltroRelatorio + exports Excel/PDF
│   ├── management/commands/
│   │   ├── enviar_relatorio_inadimplencia.py  # --frequencia diario|semanal
│   │   └── enviar_relatorio_posicao.py        # --formato excel|pdf
│   └── urls.py
├── notificacoes/              # App de notificações
│   ├── models.py             # Notificacao, TemplateNotificacao, RegraNotificacao
│   ├── relatorio_templates.py # HTML dos relatórios semanal/mensal
│   ├── management/commands/
│   │   └── criar_templates_relatorio.py
│   └── urls.py
├── portal_comprador/          # Portal web para compradores
│   ├── models.py             # AcessoComprador, PushSubscriptionPortal (34.6)
│   ├── tasks.py              # Celery: push de vencimentos via VAPID (34.6)
│   ├── views.py              # Dashboard, contratos, boletos, manifest, SW, push API
│   └── urls.py
├── accounts/                  # Autenticação e permissões
├── docs/                      # Documentação organizada
├── tests/                     # 1328 testes
│   ├── unit/                  # Testes unitários por app
│   ├── integration/           # Testes de integração
│   ├── functional/            # Testes end-to-end
│   └── fixtures/              # Factories e dados de teste
├── templates/                 # Templates HTML
├── static/
│   └── js/
│       └── portal-sw.js      # Service worker PWA (cache offline + Web Push)
├── build.sh                   # Script de build (Render)
├── render.yaml               # Configuração Render
├── docker-compose.yml         # Desenvolvimento local
└── Dockerfile.brcobranca      # BRCobrança API customizada
```

## 🔧 Configuração de Serviços

### Templates de E-mail (Admin)

Acesse `/notificacoes/templates/` no Admin para configurar os templates HTML dos relatórios:

| Código | Uso | Tags disponíveis |
|--------|-----|-----------------|
| `gestao-relatorio-semanal` | Relatório semanal por imobiliária | `%%NOMEIMOBILIARIA%%`, `%%PERIODORELATORIO%%`, `%%VALORRECEBIMENTOS%%`, `%%VALORINADIMPLENTES%%`, `%%VALORAVENCER%%` |
| `gestao-relatorio-mensal` | Relatório mensal consolidado | `%%NOMECONTABILIDADE%%`, `%%MESREFERENCIA%%`, `%%QTDCONTRATOSATIVOS%%`, `%%TABELAIMOBILIARIAS%%` |

Deixe o campo **Imobiliária** em branco para template global. Templates por imobiliária têm prioridade sobre o global.

### E-mail (Gmail)

1. Ative a verificação em duas etapas na sua conta Google
2. Gere uma "Senha de app" em: https://myaccount.google.com/apppasswords
3. Configure no `.env`:
```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=seu-email@gmail.com
EMAIL_HOST_PASSWORD=sua-senha-de-app-gerada
```

### SMS e WhatsApp (Twilio)

1. Crie uma conta em: https://www.twilio.com
2. Obtenha o Account SID e Auth Token
3. Configure um número de telefone Twilio
4. Para WhatsApp, ative o WhatsApp Sandbox ou configure WhatsApp Business API

## 📱 Como Usar

### 1. Acesse o Admin
```
http://localhost:8000/admin/
```

### 2. Cadastre uma Contabilidade
- Navegue até "Contabilidades" → Adicionar → Preencha e salve

### 3. Cadastre uma Imobiliária
- Selecione a contabilidade responsável
- Preencha dados bancários (para boletos CNAB)

### 4. Crie um Contrato
- Selecione: Imóvel, Comprador e Imobiliária
- Configure: valor total, número de parcelas, dia de vencimento
- Defina: tipo de correção (IPCA/IGP-M/SELIC/Fixo), juros e multa
- As parcelas são geradas automaticamente

### 5. Configure Notificações
- Acesse "Templates de Notificação"
- Personalize mensagens para e-mail, SMS e WhatsApp usando TAGs `%%TAG%%`
- Configure a Régua de Notificação (dias antes/após o vencimento)

### 6. Configure os Relatórios Automáticos
- Acesse "Templates de Notificação" → filtre por `gestao-relatorio-semanal` / `gestao-relatorio-mensal`
- Edite o HTML do corpo do e-mail conforme necessário
- Configure os cronjobs no cron-job.org com o `TASK_TOKEN` correto

## 📊 API do Banco Central

O sistema busca automaticamente os índices econômicos na API do Banco Central:

- **IPCA**: Série 433
- **IGP-M**: Série 189
- **SELIC**: Série 432

Não é necessária autenticação. A API é pública e gratuita.

## 🐛 Troubleshooting

### Relatório não é enviado pelo cron-job
- Verifique se o `TASK_TOKEN` no Render bate com o header `X-Task-Token` no cron-job.org
- Confirme que o método é `POST` (não `GET`)
- Verifique os logs em `Parâmetros do Sistema` → `TASK_TOKEN`

### Templates de relatório não encontrados
```bash
python manage.py criar_templates_relatorio --forcar
```

### Erro ao enviar e-mail
- Verifique se a senha de app do Gmail está correta
- Confirme se a verificação em duas etapas está ativada

### Erro ao buscar índices econômicos
- Verifique sua conexão com a internet
- Confirme se a API do BCB está disponível: https://api.bcb.gov.br

## 🧪 Testes

O projeto utiliza **pytest** com estrutura moderna organizada por tipo:

```bash
# Executar todos os testes
pytest

# Apenas testes unitários (rápido)
pytest tests/unit/

# Apenas testes de integração
pytest tests/integration/

# Com cobertura
pytest --cov=. --cov-report=html

# Verbose
pytest -v
```

**Meta de cobertura:** > 80% | **Status atual:** ✅ 1328 testes passando

### Cobertura por área

| Área | Arquivo(s) | Testes |
|------|-----------|--------|
| Smoke Tests (todos os endpoints GET) | `test_smoke.py` | 117 |
| Financeiro — CNAB Remessa/Retorno | `test_hu_boleto_remessa.py` | 57 |
| Contratos — Rescisão e Cessão | `test_hu_rescisao_cessao.py` | 34 |
| Contratos — Juros Escalantes HU-360 | `test_hu_360_juros_escalantes.py` | 33 |
| Financeiro — CNAB Service | `test_cnab_service.py` | 29 |
| Portal do Comprador — Auth | `test_auth.py` | 29 |
| Core — CRUD Views | `test_crud_views.py` | 30 |
| Notificações — Views | `test_views.py` | 26 |
| Financeiro — REST API | `test_rest_api_views.py` | 26 |
| **HU Fluxo Completo** | `test_hu_fluxo_completo.py` | **24** |
| Contratos — Parcelas/Reajuste | `test_hu_parcelas_reajuste.py` | 24 |
| **HU Portal E2E** | `test_hu_portal_e2e.py` | **23** |
| Contratos — CRUD Views | `test_crud_views.py` | 23 |
| Contratos — Models | `test_contrato_models.py` | 23 |
| Accounts — Auth | `test_auth_views.py` | 23 |
| Validators | `test_validators.py` | 23 |
| Portal — Views | `test_views.py` | 21 |
| Financeiro — Parcela/Reajuste | `test_parcela_reajuste.py` | 21 |
| Financeiro — CNAB Views | `test_cnab_views.py` | 21 |
| **HU CNAB Remessa→Retorno E2E** | `test_hu_cnab_e2e.py` | **13** |
| **Relatórios BI — API + Dashboard** | `test_hu_relatorios_bi.py` | **27** |
| **Webhook PIX — Dedup + Timing** | `test_hu_webhook_pix.py` | **32** |
| **Portal Expandido — Comprovantes** | `test_hu_portal_expandido.py` | **24** |
| **PWA — Manifest + SW + Push** | `test_hu_pwa.py` | **16** |
| E2E / Integração | `test_fluxo_contrato_completo.py`, etc. | 14+ |
| Demais testes unitários | (outros arquivos) | 200+ |

Ver documentação completa em [/tests/README.md](/tests/README.md)

## 🐳 Docker e APIs Customizadas

Este projeto utiliza versões **customizadas** do BRCobrança mantidas por Maxwell da Silva Oliveira:

### Repositórios Oficiais
- **API REST:** https://github.com/Maxwbh/boleto_cnab_api
- **Biblioteca Ruby:** https://github.com/Maxwbh/brcobranca

⚠️ **IMPORTANTE:** Use APENAS estes repositórios. Não use os forks originais.

### Docker Compose (Desenvolvimento)

```bash
# Iniciar todos os serviços (PostgreSQL, BRCobrança API)
docker-compose up -d

# Aplicar migrações e criar templates
python manage.py migrate
python manage.py criar_templates_relatorio

# Criar superusuário
python manage.py createsuperuser

# Acessar o sistema
# http://localhost:8000
```

## 🔧 Ferramentas de Desenvolvimento

- **black** - Formatação de código
- **isort** - Ordenação de imports
- **flake8** - Linting
- **pylint** - Análise estática
- **mypy** - Type checking
- **pytest** - Framework de testes
- **factory-boy** - Geração de dados de teste

Configurado via `pyproject.toml`

---

## 🤝 Contato

**Maxwell da Silva Oliveira**
- E-mail: maxwbh@gmail.com
- LinkedIn: https://www.linkedin.com/in/maxwbh/
- GitHub: https://github.com/Maxwbh/

**M&S do Brasil LTDA**
- Site: https://msbrasil.inf.br

---

**Desenvolvido por:** Maxwell da Silva Oliveira (maxwbh@gmail.com)
**Empresa:** M&S do Brasil LTDA
**Website:** https://msbrasil.inf.br
**Licença:** Proprietary

**Última atualização:** 2026-05-25 — 1328 testes | Importação de Contratos via IA (34.7) — upload PDF/imagens → Claude extrai → revisão → cadastro completo | PWA Portal do Comprador (34.6) | Relatórios BI + Dashboard Executivo (34.5)
