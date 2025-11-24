# Sistema de Gestão de Contratos de Venda de Imóveis

Sistema completo desenvolvido em Python/Django para gerenciamento de contratos de venda de imóveis (lotes, terrenos, casas) com funcionalidades avançadas de gestão financeira, reajustes automáticos e notificações.

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

### 3. Gestão Financeira
- ✅ Geração automática de parcelas mês a mês
- ✅ Cálculo automático de juros e multa por atraso
- ✅ Registro de pagamentos
- ✅ Controle de saldo devedor
- ✅ Histórico completo de pagamentos

### 4. Sistema de Reajuste Automático
- ✅ Integração com API do Banco Central do Brasil
- ✅ Busca automática de índices IPCA, IGP-M e SELIC
- ✅ Reajuste automático a cada período configurado
- ✅ Possibilidade de reajuste manual
- ✅ Histórico de reajustes aplicados

### 5. Sistema de Notificações
- ✅ Notificações por **E-mail**
- ✅ Notificações por **SMS** (via Twilio)
- ✅ Notificações por **WhatsApp** (via Twilio)
- ✅ Templates personalizáveis
- ✅ Envio automático antes do vencimento
- ✅ Configuração individual por comprador

### 6. Recursos Adicionais
- ✅ Dashboard com estatísticas
- ✅ Interface administrativa completa (Django Admin)
- ✅ Sistema de busca e filtros avançados
- ✅ Tarefas agendadas (Celery)
- ✅ Design responsivo baseado em Bootstrap 5
- ✅ Pronto para deploy no Render

## 🛠️ Tecnologias Utilizadas

### Backend
- **Python 3.11+**
- **Django 4.2.7** - Framework web
- **PostgreSQL** - Banco de dados
- **Redis** - Cache e broker para Celery
- **Celery** - Tarefas assíncronas e agendadas
- **Gunicorn** - Servidor WSGI para produção

### Frontend
- **Bootstrap 5** - Framework CSS
- **Font Awesome** - Ícones
- **JavaScript** - Interatividade

### APIs e Serviços
- **Banco Central do Brasil API** - Índices econômicos (IPCA, IGP-M, SELIC)
- **Twilio** - SMS e WhatsApp
- **SMTP** - E-mail

## 📦 Instalação e Configuração

### Pré-requisitos
- Python 3.11 ou superior
- PostgreSQL 12+ (para produção)
- Redis 6+ (para Celery)
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
REDIS_URL=redis://localhost:6379/0

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
```

### 5. Execute as Migrações
```bash
python manage.py migrate
```

### 6. Crie um Superusuário
```bash
python manage.py createsuperuser
```

### 7. Colete os Arquivos Estáticos
```bash
python manage.py collectstatic
```

### 8. Execute o Servidor de Desenvolvimento
```bash
python manage.py runserver
```

Acesse: `http://localhost:8000`

### 9. Execute o Celery (em outro terminal) - Opcional

**Nota:** O Celery é opcional para desenvolvimento. Você pode executar as tarefas manualmente.

```bash
# Worker
celery -A gestao_contrato worker --loglevel=info

# Beat (agendador)
celery -A gestao_contrato beat --loglevel=info
```

### 10. Ou Execute Tarefas Manualmente (Alternativa ao Celery)

```bash
# Processar reajustes
python manage.py processar_reajustes

# Criar notificações de vencimento
python manage.py enviar_notificacoes

# Processar notificações pendentes
python manage.py processar_notificacoes_pendentes
```

## 🚀 Deploy no Render

### ⚠️ IMPORTANTE: Plano Gratuito vs Plano Pago

Este projeto está configurado para funcionar no **Plano Gratuito** do Render.

#### Plano Gratuito (Free Tier)
- ✅ Web Service (Django)
- ✅ PostgreSQL Database
- ✅ Redis Instance
- ❌ **Background Workers NÃO suportados** (Celery)

**Funcionalidades automáticas afetadas:**
- Reajustes automáticos de parcelas
- Envio automático de notificações

**Solução:** Execute manualmente via Django Admin ou Management Commands.

👉 **[Leia o guia completo: DEPLOY_RENDER.md](./DEPLOY_RENDER.md)**

#### Plano Pago (Starter $7/mês+)
- ✅ Todas as funcionalidades do Free
- ✅ Background Workers (Celery)
- ✅ Tarefas automáticas funcionam
- ✅ Sem sleep após inatividade

### Configuração Automática (Plano Gratuito)

O projeto está configurado para deploy automático no Render usando o arquivo `render.yaml`.

1. Faça fork ou clone este repositório no GitHub
2. Acesse [render.com](https://render.com)
3. Crie uma nova aplicação "Blueprint"
4. Conecte seu repositório GitHub
5. Selecione o branch: `master`
6. O Render criará automaticamente:
   - ✅ Web Service (Django + Gunicorn)
   - ✅ PostgreSQL Database
   - ✅ Redis Instance

### Variáveis de Ambiente no Render

Configure as seguintes variáveis de ambiente no painel do Render:

```
SECRET_KEY=(será gerada automaticamente)
DEBUG=False
ALLOWED_HOSTS=.onrender.com

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
```

## 📖 Estrutura do Projeto

```
Gestao-Contrato/
├── gestao_contrato/          # Configurações do projeto
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py
├── core/                      # App principal
│   ├── models.py             # Contabilidade, Imobiliária, Imóvel, Comprador
│   ├── admin.py
│   ├── views.py
│   └── urls.py
├── contratos/                 # App de contratos
│   ├── models.py             # Modelo de Contrato
│   ├── admin.py
│   ├── views.py
│   └── urls.py
├── financeiro/                # App financeiro
│   ├── models.py             # Parcela, Reajuste, HistoricoPagamento
│   ├── admin.py
│   ├── views.py
│   ├── tasks.py              # Tarefas Celery (reajustes)
│   └── urls.py
├── notificacoes/              # App de notificações
│   ├── models.py             # Notificacao, Templates, Configurações
│   ├── admin.py
│   ├── views.py
│   ├── services.py           # Serviços de envio
│   ├── tasks.py              # Tarefas Celery (notificações)
│   └── urls.py
├── templates/                 # Templates HTML
│   ├── base.html
│   └── ...
├── static/                    # Arquivos estáticos
├── media/                     # Upload de arquivos
├── requirements.txt           # Dependências Python
├── build.sh                   # Script de build (Render)
├── render.yaml               # Configuração Render
├── .env.example              # Exemplo de variáveis de ambiente
└── README.md                 # Este arquivo
```

## 🔧 Configuração de Serviços

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
5. Configure no `.env`:
```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=seu-token
TWILIO_PHONE_NUMBER=+5511999999999
TWILIO_WHATSAPP_NUMBER=whatsapp:+5511999999999
```

**Alternativas mais baratas para SMS:**
- Zenvia: https://www.zenvia.com
- TotalVoice: https://www.totalvoice.com.br
- SMS Dev: https://smsdev.com.br

## 📱 Como Usar

### 1. Acesse o Admin
```
http://localhost:8000/admin/
```

### 2. Cadastre uma Contabilidade
- Navegue até "Contabilidades"
- Clique em "Adicionar Contabilidade"
- Preencha os dados e salve

### 3. Cadastre uma Imobiliária
- Navegue até "Imobiliárias"
- Selecione a contabilidade responsável
- Preencha dados bancários (para boletos)

### 4. Cadastre Imóveis
- Navegue até "Imóveis"
- Selecione a imobiliária
- Defina o tipo (Lote, Terreno, Casa, etc.)

### 5. Cadastre Compradores
- Navegue até "Compradores"
- Configure preferências de notificação

### 6. Crie um Contrato
- Navegue até "Contratos"
- Selecione: Imóvel, Comprador e Imobiliária
- Configure: valor total, número de parcelas, dia de vencimento
- Defina: tipo de correção (IPCA/IGP-M/SELIC), juros e multa
- Salve: as parcelas serão geradas automaticamente

### 7. Gerencie Parcelas
- Acesse "Parcelas" para visualizar todas as parcelas
- Registre pagamentos
- Visualize parcelas vencidas
- Atualizar juros e multa automaticamente

### 8. Configure Notificações
- Acesse "Templates de Notificação"
- Personalize mensagens para e-mail, SMS e WhatsApp
- Configure quando enviar (X dias antes do vencimento)

## 🔄 Tarefas Automáticas (Celery)

O sistema executa automaticamente:

### Diariamente às 01:00
- **Processamento de Reajustes**: Verifica contratos que precisam de reajuste e aplica automaticamente

### Diariamente às 08:00
- **Envio de Notificações**: Envia notificações de parcelas a vencer

### Manual
- Reajustes manuais via Django Admin
- Atualização de juros e multa

## 📊 API do Banco Central

O sistema busca automaticamente os índices econômicos na API do Banco Central:

- **IPCA**: Série 433
- **IGP-M**: Série 189
- **SELIC**: Série 432

Não é necessária autenticação. A API é pública e gratuita.

## 🐛 Troubleshooting

### Erro ao enviar e-mail
- Verifique se a senha de app do Gmail está correta
- Confirme se a verificação em duas etapas está ativada

### Celery não está executando tarefas
- Verifique se o Redis está rodando: `redis-cli ping`
- Confirme se o worker do Celery está ativo
- Verifique os logs: `celery -A gestao_contrato worker --loglevel=debug`

### Erro ao buscar índices econômicos
- Verifique sua conexão com a internet
- Confirme se a API do BCB está disponível: https://api.bcb.gov.br


## 🤝 Contato

Para dúvidas ou suporte:

**Maxwell da Silva Oliveira**
- E-mail: maxwbh@gmail.com
- LinkedIn: https://www.linkedin.com/in/maxwbh/
- GitHub: https://github.com/Maxwbh/

**M&S do Brasil LTDA**
- Site: https://msbrasil.inf.br

---

**Desenvolvido com ❤️ por Maxwell da Silva Oliveira**
