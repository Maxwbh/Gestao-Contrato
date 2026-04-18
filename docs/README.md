# Documentação — Sistema de Gestão de Contratos

Desenvolvido por **Maxwell da Silva Oliveira** (maxwbh@gmail.com) — M&S do Brasil LTDA

---

## Índice

### Principal
- **[README.md](../README.md)** — Visão geral, instalação, funcionalidades
- **[SISTEMA.md](../SISTEMA.md)** — Documentação técnica do sistema (o que está implementado)
- **[ROADMAP.md](../ROADMAP.md)** — Pendentes, prioridades e plano de testes (novas implementações)

### Deploy e Infraestrutura
- **[Guia Completo de Deploy](deployment/DEPLOY.md)** — Render, Docker, VPS
- **[Render.com](deployment/RENDER.md)** — Configuração passo a passo
- **[Render sem Shell](deployment/RENDER_NO_SHELL.md)** — Alternativas para plano gratuito

### Desenvolvimento
- **[Setup Local](development/SETUP.md)** — Configuração do ambiente de desenvolvimento
- **[Dados de Teste](development/TEST_DATA.md)** — Como gerar dados de teste
- **[Testes](../tests/README.md)** — Estrutura de testes e como executar

### APIs e Integrações
- **[BRCobrança](api/BRCOBRANCA.md)** — Guia completo de integração com boletos
- **[BRCobrança — Campos de Referência](api/BRCOBRANCA_CAMPOS_REFERENCIA.md)** — Campos por banco
- **[Validação API Customizada](api/VALIDACAO_API_CUSTOMIZADA.md)** — Detalhes da validação
- **[ViaCEP](api/VIACEP_INTEGRACAO.md)** — Busca de endereços por CEP

### Arquitetura
- **[Estrutura de Dados](architecture/ESTRUTURA_DADOS.md)** — Modelos e relacionamentos

### Compliance e Regulamentações
- **[LGPD](compliance/LGPD.md)** — Tratamento de dados pessoais sensíveis
- **[CNPJ Alfanumérico 2026](compliance/CNPJ_2026.md)** — Preparação para o novo formato

### Troubleshooting
- **[Problemas Comuns](troubleshooting/COMMON_ISSUES.md)** — Soluções para erros frequentes

---

## Histórico de Atualizações

- **2026-03-30**: Consolidação de TODOs em `ROADMAP.md`; remoção de arquivos defasados
- **2025-11-26**: Reorganização completa da documentação
- **2025-11-24**: Correção de erros 500 na geração de boletos
- **2025-11-23**: Implementação inicial
