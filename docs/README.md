# Documentação — Sistema de Gestão de Contratos

Desenvolvido por **Maxwell da Silva Oliveira** (maxwbh@gmail.com) — M&S do Brasil LTDA

---

## Índice

### Análise de Produto (HUs + Mockups) ⭐ centralizado
- **[Hub de Análise](analise/README.md)** — Histórias de Usuário, mockups/protótipos e análise de negócio em um só lugar
- **[Índice Mestre das HUs](analise/historias-usuario/INDICE.md)** — matriz de rastreabilidade, personas e fluxo macro

### Principal
- **[README.md](../README.md)** — Visão geral, instalação, funcionalidades
- **[SISTEMA.md](../SISTEMA.md)** — Documentação técnica do sistema (o que está implementado)
- **[ROADMAP.md](../ROADMAP.md)** — Pendentes, prioridades e plano de testes (novas implementações)

### Manuais do Usuário Final
- **[Manual do Contador (Administrador)](manual_contador.md)** — Acesso completo: contratos, financeiro, relatórios, administração
- **[Manual da Imobiliária / Vendedor](manual_imobiliaria.md)** — Acesso filtrado por imobiliária: contratos, boletos, reajustes
- **[Manual do Comprador](manual_comprador.md)** — Portal do comprador: boletos, histórico, simulador

### Deploy e Infraestrutura
- **[Guia Completo de Deploy](deployment/DEPLOY.md)** — Render, Docker, VPS
- **[Render.com](deployment/RENDER.md)** — Configuração passo a passo
- **[Render sem Shell](deployment/RENDER_NO_SHELL.md)** — Alternativas para plano gratuito
- **[Variáveis de Ambiente](deployment/ENV_PARAMETROS.md)** — Todas as variáveis necessárias
- **[CronJob / Tarefas Agendadas](deployment/CRONJOB.md)** — Reajustes, notificações, CNAB

### Desenvolvimento
- **[Setup Local](development/SETUP.md)** — Configuração do ambiente de desenvolvimento
- **[Dados de Teste](development/TEST_DATA.md)** — Como gerar dados de teste
- **[Histórias de Usuário](analise/README.md)** — centralizadas em `docs/analise/` ⭐
- **[Testes](../tests/README.md)** — Estrutura de testes e como executar

### APIs e Integrações
- **[Boleto-API — HUs da Cobrança Registrada (BAPI-01..41)](api/BOLETO_API_HUS.md)** — épico multi-método C6/Sicoob: credenciais cifradas, webhook, estados, Pix Automático, painel de conciliação
- **[Boleto-API — Cenários de Teste (boleto fake)](analise/CENARIOS_TESTE_BOLETO_API.md)** — massa de dados e ciclo de vida sem API de banco
- **[BRCobrança](api/BRCOBRANCA.md)** — Guia completo de integração com boletos
- **[BRCobrança — Campos de Referência](api/BRCOBRANCA_CAMPOS_REFERENCIA.md)** — Campos por banco
- **[Validação API Customizada](api/VALIDACAO_API_CUSTOMIZADA.md)** — Detalhes da validação
- **[ViaCEP](api/VIACEP_INTEGRACAO.md)** — Busca de endereços por CEP

### Arquitetura
- **[Estrutura de Dados](architecture/ESTRUTURA_DADOS.md)** — Modelos e relacionamentos
- **[Grids do Sistema](GRIDS_STATUS.md)** — Status de parcelas, boletos e CNAB nas tabelas AG Grid

### Compliance e Regulamentações
- **[LGPD](compliance/LGPD.md)** — Tratamento de dados pessoais sensíveis
- **[CNPJ Alfanumérico 2026](compliance/CNPJ_2026.md)** — Formato IN RFB nº 2229/2024 — implementado ✅

### Portal do Comprador
- **[Documentação Técnica](portal_comprador/PORTAL_COMPRADOR.md)** — Modelos, rotas, APIs, segurança
- **[Guia do Usuário](portal_comprador/GUIA_USUARIO.md)** — Manual de uso para o comprador
- **[Roadmap](portal_comprador/ROADMAP_PORTAL.md)** — Funcionalidades pendentes e priorizadas

### Troubleshooting
- **[Problemas Comuns](troubleshooting/COMMON_ISSUES.md)** — Soluções para erros frequentes

---

## Histórico de Atualizações

- **2026-05-25**: CNPJ alfanumérico 2026 implementado (IN RFB 2229/2024); manuais do usuário final (Contador, Imobiliária, Comprador); Importação de Contratos via IA (34.7); 1335 testes passando
- **2026-04-20**: Portal do Comprador expandido — historico unificado, simulador antecipação, upload comprovante, PWA, push notifications
- **2026-03-30**: Consolidação de TODOs em `ROADMAP.md`; remoção de arquivos defasados
- **2025-11-26**: Reorganização completa da documentação
- **2025-11-24**: Correção de erros 500 na geração de boletos
- **2025-11-23**: Implementação inicial
