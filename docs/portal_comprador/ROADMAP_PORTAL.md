# ROADMAP — Portal do Comprador

**Desenvolvedor:** Maxwell da Silva Oliveira (maxwbh@gmail.com)
**Última atualização:** 2026-04-19

> Roadmap específico do Portal do Comprador. Para documentação técnica do que já está implementado, consulte **[PORTAL_COMPRADOR.md](PORTAL_COMPRADOR.md)**.

---

## Legenda

- **P1** Crítico — segurança, bloqueio de uso
- **P2** Alto — funcionalidade importante para o comprador
- **P3** Médio — melhoria significativa de UX
- **P4** Baixo — nice to have
- 🏦 **Débito Técnico** — identificado, fora do horizonte atual

---

## 0. CONCLUÍDO ✅

| # | Item | Referência |
|---|------|------------|
| 0.1 | Auto-cadastro por CPF/CNPJ + validação de e-mail do contrato | `auto_cadastro` |
| 0.2 | Login/logout por CPF/CNPJ + senha | `login_comprador` |
| 0.3 | Dashboard com KPIs consolidados de todos os contratos | `dashboard` |
| 0.4 | Lista de contratos (suporte a N contratos por comprador) | `meus_contratos` |
| 0.5 | Detalhe de contrato com parcelas e intermediárias | `detalhe_contrato` |
| 0.6 | Lista de boletos com filtros (todos/a pagar/vencidos/pagos) | `meus_boletos` |
| 0.7 | Paginação em meus_boletos (20/página, navegação prev/next) | `meus_boletos` + template |
| 0.8 | Botão de download de boleto (GERADO/REGISTRADO/VENCIDO) | `meus_boletos.html` |
| 0.9 | Download e visualização inline de PDF | `download_boleto`, `visualizar_boleto` |
| 0.10 | Edição de dados pessoais (endereço, e-mail, telefone) | `meus_dados` |
| 0.11 | Alteração de senha com validação de senha atual | `alterar_senha` |
| 0.12 | Auditoria de acessos (IP, UA, página) | `LogAcessoComprador` |
| 0.13 | Enforcement de `AcessoComprador.ativo` (login e middleware) | `get_comprador_from_request` |
| 0.14 | API P1: parcelas por contrato, resumo financeiro | `api_parcelas_contrato`, `api_resumo_financeiro` |
| 0.15 | API P2: vencimentos e boletos com filtros + paginação | `api_portal_vencimentos`, `api_portal_boletos` |
| 0.16 | API P3: segunda via com rate-limit (10/min) + linha digitável | `api_portal_segunda_via`, `api_portal_linha_digitavel` |
| 0.17 | Layout mobile-first com Materialize CSS | `portal_base.html` |
| 0.18 | Testes unitários + integração (60 testes) | `tests/unit/portal_comprador/` |

---

## 1. SEGURANÇA E AUTENTICAÇÃO (P1)

| # | Item | Status | Descrição |
|---|------|--------|-----------|
| 1.1 | Fluxo "Esqueci minha senha" | ⏳ Pendente | Token por e-mail → página de redefinição → troca sem login. Hoje o comprador bloqueado precisa contatar suporte. |
| 1.2 | Verificação de e-mail no auto-cadastro | ⏳ Pendente | Campos `email_verificado` e `token_verificacao` existem no modelo mas nunca são usados. Enviar token + exigir confirmação antes de liberar login. |
| 1.3 | Rate limiting em login | ⏳ Pendente | Hoje não há limite — ataques de força bruta possíveis. Aplicar `portal_rate_limit` com janela por IP (ex: 5 tentativas/5 min). |
| 1.4 | Política de senha forte | ⏳ Pendente | Mínimo atual é 6 caracteres, sem exigência de complexidade. Alinhar com `django.contrib.auth.password_validation`. |
| 1.5 | Logout automático por inatividade | ⏳ Pendente | Sessão sem expiração configurada (padrão Django: 2 semanas). Reduzir para 30–60 min para dados financeiros. |

### P2
| # | Item | Status | Descrição |
|---|------|--------|-----------|
| 1.6 | 2FA opcional (TOTP) | 🏦 Débito Técnico — pós-2050 | `django-otp` com app autenticador. Ativação voluntária em "Meus Dados". |
| 1.7 | Notificação de login suspeito | ⏳ Pendente | E-mail quando login vem de IP/país novo (comparar com histórico de `LogAcessoComprador`). |

---

## 2. PAGAMENTO (P1/P2)

| # | Item | Status | Descrição |
|---|------|--------|-----------|
| 2.1 | Exibir PIX Copia-e-Cola + QR code | 🏦 Débito Técnico — 2050 | Campos `pix_copia_cola` e `pix_qrcode` já existem em `Parcela`. Renderizar QR + botão "copiar código". |
| 2.2 | Botão "Segunda Via" no portal | ⏳ Pendente | A API P3 existe (`api_portal_segunda_via`) mas não há botão UI. Adicionar em `meus_boletos.html` para parcelas vencidas. |
| 2.3 | Confirmação de pagamento em tempo real | ⏳ Pendente | Polling ou webhook do BRCobrança → atualizar UI sem refresh. |

### P2
| # | Item | Status | Descrição |
|---|------|--------|-----------|
| 2.4 | Carnê de boletos em PDF (multi-parcelas) | ⏳ Pendente | Service `gerar_carne` já existe no `BoletoService` — expor no portal para download consolidado. |
| 2.5 | Histórico de pagamentos exportável (PDF/Excel) | ⏳ Pendente | Gerar extrato formatado para uso contábil/IR. |

---

## 3. DOCUMENTOS E CONTRATO 🏦 Débito Técnico — pós-2050

| # | Item | Status | Descrição |
|---|------|--------|-----------|
| 3.1 | Download do contrato PDF assinado | 🏦 pós-2050 | Campo para upload admin → comprador baixa no portal. |
| 3.2 | Download da escritura (quando disponível) | 🏦 pós-2050 | Vincular a campo de upload admin em `Contrato`. |
| 3.3 | Informe de rendimentos anual | 🏦 pós-2050 | PDF gerado automaticamente para IR, com valores pagos no ano fiscal. |

---

## 4. NOTIFICAÇÕES E ENGAJAMENTO (P2)

| # | Item | Status | Descrição |
|---|------|--------|-----------|
| 4.1 | Histórico de notificações no portal | ⏳ Pendente | Lista `Notificacao` enviadas (e-mail/SMS/WhatsApp) com status de entrega. |
| 4.2 | Preferências granulares de notificação | ⏳ Pendente | Hoje são 3 flags boolean (email/sms/whatsapp). Adicionar: X dias antes do vencimento, no vencimento, após vencimento. |
| 4.3 | Banner de parcelas próximas (7 dias) | ⏳ Pendente | Alerta visual no dashboard além do existente para vencidas. |

### P3
| # | Item | Status | Descrição |
|---|------|--------|-----------|
| 4.4 | Push notifications (PWA) | ⏳ Pendente | Requer service worker + VAPID keys. Depende de 7.1. |
| 4.5 | Lembrete configurável no Google Calendar | ⏳ Pendente | Botão "Adicionar ao Calendário" com `.ics` por parcela. |

---

## 5. UX E INTERFACE (P2)

| # | Item | Status | Descrição |
|---|------|--------|-----------|
| 5.1 | Busca/filtro em meus_contratos | ⏳ Pendente | Hoje só ordena — adicionar busca por número/imóvel e filtro por status. |
| 5.2 | Exibir total de parcelas em atraso + acumulado por contrato | ⏳ Pendente | Relevante para compradores com N contratos — saber qual tem mais atraso. |
| 5.3 | Ordenação de parcelas no detalhe do contrato | ⏳ Pendente | Hoje é só por número — permitir por vencimento, status. |
| 5.4 | Modo escuro (opcional) | ⏳ Pendente | CSS variables já preparadas. Toggle em "Meus Dados". |

### P3
| # | Item | Status | Descrição |
|---|------|--------|-----------|
| 5.5 | Gráfico de evolução dos pagamentos | ⏳ Pendente | Chart.js ou similar: pagamentos mensais, saldo devedor ao longo do tempo. |
| 5.6 | Simulador de quitação antecipada | ⏳ Pendente | Input: "Quanto pagar hoje para quitar?" → calcula desconto de juros futuros. |
| 5.7 | Upload de comprovantes pelo comprador | ⏳ Pendente | Caso de pagamento fora do sistema — admin confirma depois. |

---

## 6. SUPORTE E COMUNICAÇÃO 🏦 Débito Técnico — pós-2050

| # | Item | Status | Descrição |
|---|------|--------|-----------|
| 6.1 | Chat / sistema de tickets | 🏦 pós-2050 | Comprador abre ticket → imobiliária responde. Vincular a `Contrato`. |
| 6.2 | FAQ dinâmica | 🏦 pós-2050 | Gerenciada pela imobiliária, contextualizada (dúvidas sobre reajuste, boleto, etc). |
| 6.3 | Botão "Falar com a imobiliária" (WhatsApp/e-mail) | 🏦 pós-2050 | Link direto com contexto (número do contrato pré-preenchido). |

---

## 7. INFRAESTRUTURA E PERFORMANCE (P3)

| # | Item | Status | Descrição |
|---|------|--------|-----------|
| 7.1 | PWA (Progressive Web App) | ⏳ Pendente | `manifest.json` + service worker → instalável, funciona offline para visualização. |
| 7.2 | Cache de boletos em CDN | ⏳ Pendente | PDFs estáticos via CloudFront/Cloudflare — reduzir latência no download. |
| 7.3 | Query otimização em dashboard para >50 contratos | ⏳ Pendente | Testar e, se necessário, denormalizar KPIs em tabela agregada. |

### P4
| # | Item | Status | Descrição |
|---|------|--------|-----------|
| 7.4 | App nativo (React Native / Flutter) | 🏦 Débito Técnico | Custo alto vs PWA. Reavaliar após PWA em produção. |

---

## 8. ADMINISTRAÇÃO E OBSERVABILIDADE 🏦 Débito Técnico — pós-2050

| # | Item | Status | Descrição |
|---|------|--------|-----------|
| 8.1 | Dashboard admin de uso do portal | 🏦 pós-2050 | Compradores ativos, logins/dia, páginas mais acessadas, taxa de adoção. |
| 8.2 | Impersonation ("entrar como comprador") | 🏦 pós-2050 | Admin acessa o portal como um comprador específico para suporte. Registrar como log especial. |
| 8.3 | Bulk de operações sobre acessos | 🏦 pós-2050 | Ativar/desativar em lote, enviar convite para cadastro em massa. |
| 8.4 | Alertas de anomalia | 🏦 pós-2050 | Login de país estranho, sequência de tentativas falhas, etc — notificar admin. |

---

## 9. LGPD E COMPLIANCE 🏦 Débito Técnico — 3200

| # | Item | Status | Descrição |
|---|------|--------|-----------|
| 9.1 | Aceite explícito de Termos e Política de Privacidade | 🏦 3200 | Checkbox obrigatório no auto-cadastro com versionamento. |
| 9.2 | Exportar dados pessoais (direito de acesso) | 🏦 3200 | Botão "Baixar meus dados" → ZIP com JSON + PDFs. |
| 9.3 | Solicitação de exclusão/anonimização | 🏦 3200 | Fluxo de request → validação admin (pode conflitar com obrigação fiscal de 5 anos). |
| 9.4 | Log de consentimento | 🏦 3200 | Rastrear quando comprador aceitou cada versão dos termos. |

---

## Priorização Sugerida (Próximas Sprints)

### Sprint 1 — Segurança
- 1.1 Esqueci minha senha
- 1.2 Verificação de e-mail (ativar campos já existentes no modelo)
- 1.3 Rate limit em login
- 1.4 Política de senha forte

### Sprint 2 — Pagamento e boletos
- 2.2 Botão "Segunda Via" no portal (API já existe, falta UI)
- 2.4 Carnê PDF (service já existe, falta exposição no portal)
- 2.5 Histórico de pagamentos exportável

### Sprint 3 — UX e contratos
- 5.1 Busca/filtro em meus_contratos
- 5.2 Aggregado de atraso por contrato
- 4.1 Histórico de notificações no portal
- 4.3 Banner de parcelas próximas (7 dias)

### Sprint 4 — Engajamento e notificações
- 4.2 Preferências granulares de notificação
- 1.7 Notificação de login suspeito
- 5.5 Gráfico de evolução dos pagamentos

### Sprint 5 — PWA e infraestrutura
- 7.1 PWA (manifest + service worker)
- 4.4 Push notifications
- 7.2 CDN para PDFs
