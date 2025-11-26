# Documentação do Sistema de Gestão de Contratos

Sistema desenvolvido por **Maxwell da Silva Oliveira** (maxwbh@gmail.com)
M&S do Brasil LTDA

## 📚 Índice da Documentação

### Documentação Principal
- **[README.md](../README.md)** - Visão geral do sistema
- **[DEPLOY.md](deployment/DEPLOY.md)** - Guia completo de deploy
- **[CONTRIBUTING.md](development/CONTRIBUTING.md)** - Guia para contribuidores

### Deploy e Infraestrutura
- **[Render](deployment/RENDER.md)** - Deploy no Render.com
- **[Docker](deployment/DOCKER.md)** - Containerização com Docker
- **[Environment](deployment/ENVIRONMENT.md)** - Variáveis de ambiente

### Desenvolvimento
- **[Setup Local](development/SETUP.md)** - Configuração do ambiente de desenvolvimento
- **[Testes](development/TESTING.md)** - Guia de testes
- **[Dados de Teste](development/TEST_DATA.md)** - Como gerar dados de teste

### APIs e Integrações
- **[BRCobranca](api/BRCOBRANCA.md)** - Integração com API de boletos
- **[Banco Central](api/BANCO_CENTRAL.md)** - Busca de índices econômicos
- **[ViaCEP](api/VIACEP.md)** - Busca de endereços

### Estruturas de Dados
- **[Modelos](architecture/MODELS.md)** - Estrutura de dados do sistema
- **[Banco de Dados](architecture/DATABASE.md)** - Schema e relacionamentos

### Compliance e Regulamentações
- **[LGPD e Dados Pessoais](compliance/LGPD.md)** - Tratamento de dados sensíveis
- **[CNPJ Alfanumérico 2026](compliance/CNPJ_2026.md)** - Preparação para novo formato

### Troubleshooting
- **[Problemas Comuns](troubleshooting/COMMON_ISSUES.md)** - Soluções para problemas frequentes
- **[Logs e Debugging](troubleshooting/DEBUGGING.md)** - Como debugar o sistema

---

## 🗂️ Estrutura de Diretórios

```
docs/
├── README.md                    # Este arquivo
├── api/                         # Documentação de APIs
│   ├── BRCOBRANCA.md
│   ├── BANCO_CENTRAL.md
│   └── VIACEP.md
├── architecture/                # Arquitetura do sistema
│   ├── MODELS.md
│   └── DATABASE.md
├── compliance/                  # Regulamentações e compliance
│   ├── LGPD.md
│   └── CNPJ_2026.md
├── deployment/                  # Deploy e infraestrutura
│   ├── DEPLOY.md
│   ├── RENDER.md
│   ├── DOCKER.md
│   └── ENVIRONMENT.md
├── development/                 # Desenvolvimento
│   ├── SETUP.md
│   ├── TESTING.md
│   ├── TEST_DATA.md
│   └── CONTRIBUTING.md
└── troubleshooting/             # Resolução de problemas
    ├── COMMON_ISSUES.md
    └── DEBUGGING.md
```

## 📝 Documentação Descontinuada

Os seguintes documentos foram consolidados e não são mais mantidos:
- ~~AVALIACAO_MELHORIAS.md~~ → Movido para issues do GitHub
- ~~CORRECAO_NECESSARIA_API.md~~ → Corrigido e documentado em api/BRCOBRANCA.md

## 🔄 Atualizações

- **2025-11-26**: Reorganização completa da documentação
- **2025-11-24**: Correção de erros 500 na geração de boletos
- **2025-11-23**: Implementação inicial
