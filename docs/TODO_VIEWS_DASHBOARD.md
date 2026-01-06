# TODO - Visões e Dashboards

**Desenvolvedor:** Maxwell Oliveira (@maxwbh)
**Email:** maxwbh@gmail.com
**LinkedIn:** /maxwbh
**Empresa:** M&S do Brasil LTDA - www.msbrasil.inf.br

---

## Visão Geral

Este documento detalha as telas e dashboards para os três níveis de acesso do sistema:
- **Contabilidade**: Visão consolidada de múltiplas imobiliárias
- **Imobiliária**: Visão detalhada dos contratos e operações
- **Comprador (Portal)**: Acesso do comprador aos seus contratos e boletos

---

## 1. DASHBOARD CONTABILIDADE ✅ IMPLEMENTADO

### 1.1 Visão Geral (Home)
- [x] Card: Total de imobiliárias gerenciadas ✅
- [x] Card: Total de contratos ativos (todas imobiliárias) ✅
- [x] Card: Valor total a receber (consolidado) ✅
- [x] Card: Valor total em atraso (consolidado) ✅
- [x] Gráfico: Recebimentos mensais (últimos 12 meses) ✅ API disponível
- [x] Gráfico: Inadimplência por imobiliária (pizza/barras) ✅ API disponível
- [x] Lista: Estatísticas por imobiliária ✅
- [x] Lista: Alertas de reajustes pendentes ✅

### 1.2 Relatório Consolidado por Imobiliária
- [x] Tabela com todas imobiliárias: ✅
  - Nome/Razão Social
  - CNPJ
  - Qtd. Contratos Ativos
  - Valor Total Contratos
  - Valor Recebido (mês)
  - Valor a Receber
  - Valor em Atraso
  - % Inadimplência
- [x] Filtros: Contabilidade ✅
- [ ] Exportar: PDF, Excel (pendente template)

### 1.3 Relatório de Reajustes Pendentes
- [x] Lista de contratos com reajuste próximo ✅ RelatorioPrevisaoReajustesView
- [x] Agrupamento por imobiliária ✅
- [x] Status do reajuste (Pendente, Aplicado) ✅
- [ ] Ação: Notificar imobiliária
- [x] Exportar: CSV, JSON ✅

### 1.4 Relatório de Inadimplência Geral
- [x] Tabela de parcelas vencidas ✅ RelatorioPrestacoesAPagarView
- [x] Filtros: Imobiliária, Período ✅
- [x] Totalizadores ✅
- [x] Exportar: CSV, JSON ✅

### 1.5 Configurações da Contabilidade
- [ ] Dados cadastrais
- [ ] Lista de imobiliárias vinculadas
- [ ] Adicionar/Remover imobiliária
- [ ] Usuários com acesso
- [ ] Configurações de notificação

---

## 2. DASHBOARD IMOBILIÁRIA ✅ IMPLEMENTADO

### 2.1 Visão Geral (Home)
- [x] Card: Contratos Ativos ✅
- [x] Card: Contratos Quitados ✅
- [x] Card: Valor a Receber (total) ✅
- [x] Card: Valor em Atraso ✅
- [x] Card: Recebido no Mês ✅
- [x] Card: Próximos Vencimentos ✅
- [x] Lista: Parcelas vencendo ✅
- [x] Lista: Parcelas vencidas (top por valor) ✅
- [x] Alerta: Contratos com reajuste pendente ✅
- [x] Alerta: Contratos com boleto bloqueado ✅ NOVO
- [x] Lista: Prestações intermediárias pendentes ✅ NOVO

### 2.2 Gestão de Contratos

#### 2.2.1 Lista de Contratos
- [x] Tabela com filtros: ✅
  - Número do Contrato
  - Comprador
  - Imóvel
  - Status (Ativo, Quitado, Cancelado, Suspenso)
  - Valor Total
  - Saldo Devedor
  - Próximo Vencimento
  - Situação Reajuste
- [ ] Filtros: Status, Período, Comprador, Imóvel
- [ ] Busca rápida por número/comprador
- [ ] Ações: Ver, Editar, Gerar Boletos
- [ ] Exportar: PDF, Excel

#### 2.2.2 Detalhes do Contrato
- [ ] **Aba Dados Gerais**:
  - Informações do contrato
  - Dados do comprador
  - Dados do imóvel
  - Configurações de boleto
- [ ] **Aba Parcelas**:
  - Lista de todas as parcelas
  - Status (Paga, A Vencer, Vencida)
  - Ações: Registrar Pagamento, Gerar Boleto
  - Filtros por status
- [ ] **Aba Intermediárias**:
  - Lista de prestações intermediárias
  - Status e valores
  - Vincular/Gerar parcela
- [ ] **Aba Reajustes**:
  - Histórico de reajustes aplicados
  - Próximo reajuste previsto
  - Botão: Aplicar Reajuste
  - Simulador de reajuste
- [ ] **Aba Boletos**:
  - Lista de boletos gerados
  - Status (Gerado, Registrado, Pago, Cancelado)
  - Download PDF
  - Reenviar por email
- [ ] **Aba Pagamentos**:
  - Histórico completo de pagamentos
  - Forma de pagamento
  - Comprovantes
- [ ] **Aba Documentos**:
  - Upload de documentos
  - Contrato assinado
  - Comprovantes diversos

#### 2.2.3 Novo Contrato
- [ ] Wizard em etapas:
  1. Selecionar Imóvel
  2. Selecionar/Cadastrar Comprador
  3. Dados Financeiros (valor, entrada, parcelas)
  4. Configurar Intermediárias
  5. Configurar Reajuste
  6. Configurar Boleto
  7. Revisão e Confirmação
- [ ] Validações em tempo real
- [ ] Cálculo automático de parcelas
- [ ] Preview do cronograma

### 2.3 Gestão de Parcelas

#### 2.3.1 Parcelas a Receber
- [ ] Tabela:
  - Contrato
  - Comprador
  - Nº Parcela
  - Tipo (Normal/Intermediária)
  - Vencimento
  - Valor
  - Status Boleto
  - Ações
- [ ] Filtros: Período, Status, Tipo, Contrato
- [ ] Seleção múltipla para ações em lote
- [ ] Ações em lote:
  - Gerar boletos selecionados
  - Enviar por email
  - Exportar lista
- [ ] Totalizadores

#### 2.3.2 Parcelas Vencidas
- [ ] Mesma estrutura de "Parcelas a Receber"
- [ ] Colunas adicionais:
  - Dias em Atraso
  - Juros Acumulado
  - Multa
  - Valor Total Devido
- [ ] Ações: Notificar comprador, Gerar boleto atualizado

#### 2.3.3 Registrar Pagamento
- [ ] Modal/Página:
  - Dados da parcela
  - Valor original
  - Juros/Multa calculados
  - Desconto (se aplicável)
  - Valor a pagar
  - Valor recebido
  - Data do pagamento
  - Forma de pagamento
  - Upload comprovante
  - Observações

### 2.4 Gestão de Boletos

#### 2.4.1 Geração em Lote
- [ ] Selecionar período de vencimento
- [ ] Selecionar contratos/parcelas
- [ ] Verificar bloqueios de reajuste
- [ ] Confirmar conta bancária
- [ ] Progresso de geração
- [ ] Resultado: sucesso/falhas
- [ ] Download em lote (ZIP)

#### 2.4.2 Remessas CNAB
- [ ] Lista de remessas geradas
- [ ] Gerar nova remessa
- [ ] Selecionar boletos pendentes
- [ ] Download arquivo CNAB
- [ ] Marcar como enviada

#### 2.4.3 Retornos CNAB
- [ ] Upload arquivo retorno
- [ ] Processamento automático
- [ ] Lista de ocorrências
- [ ] Confirmações de pagamento
- [ ] Rejeições e motivos

### 2.5 Gestão de Reajustes

#### 2.5.1 Contratos Pendentes de Reajuste
- [ ] Lista de contratos no período de reajuste
- [ ] Dias para o reajuste
- [ ] Índice configurado
- [ ] Valor atual do índice
- [ ] Impacto estimado
- [ ] Ação: Aplicar Reajuste

#### 2.5.2 Aplicar Reajuste
- [ ] Selecionar contrato(s)
- [ ] Escolher índice (ou manual)
- [ ] Período de apuração
- [ ] Percentual a aplicar
- [ ] Preview: parcelas afetadas
- [ ] Preview: valores antes/depois
- [ ] Confirmar aplicação
- [ ] Gerar relatório de reajuste

#### 2.5.3 Histórico de Reajustes
- [ ] Lista de todos reajustes aplicados
- [ ] Filtros: Contrato, Período, Índice
- [ ] Detalhes: parcelas afetadas, valores

### 2.6 Relatórios

#### 2.6.1 Prestações a Pagar
- [ ] Filtros completos
- [ ] Agrupamento: Contrato, Período, Tipo
- [ ] Totalizadores
- [ ] Exportar: PDF, Excel, CSV

#### 2.6.2 Prestações Pagas
- [ ] Filtros por período de pagamento
- [ ] Forma de pagamento
- [ ] Totalizadores
- [ ] Exportar: PDF, Excel, CSV

#### 2.6.3 Posição de Contratos
- [ ] Visão consolidada de cada contrato
- [ ] Progresso de pagamento
- [ ] Saldo devedor
- [ ] Exportar: PDF, Excel

#### 2.6.4 Previsão de Recebimentos
- [ ] Projeção para os próximos meses
- [ ] Considerar reajustes futuros
- [ ] Gráfico de fluxo de caixa
- [ ] Exportar: PDF, Excel

#### 2.6.5 Inadimplência
- [ ] Aging de parcelas vencidas
- [ ] Por faixa de atraso (30, 60, 90, 120+ dias)
- [ ] Por comprador
- [ ] Valor total em risco
- [ ] Exportar: PDF, Excel

### 2.7 Cadastros

#### 2.7.1 Compradores
- [ ] Lista com busca/filtros
- [ ] Cadastro completo (PF/PJ)
- [ ] Documentos
- [ ] Contratos vinculados
- [ ] Histórico de pagamentos

#### 2.7.2 Imóveis
- [ ] Lista com busca/filtros
- [ ] Cadastro por tipo
- [ ] Status (Disponível, Vendido, Reservado)
- [ ] Localização/Mapa
- [ ] Fotos
- [ ] Contratos vinculados

#### 2.7.3 Contas Bancárias
- [ ] Lista de contas
- [ ] Configurações por banco
- [ ] Conta principal
- [ ] Configurações de boleto
- [ ] Sequencial nosso número

### 2.8 Configurações

#### 2.8.1 Dados da Imobiliária
- [ ] Razão Social / Nome Fantasia
- [ ] CNPJ
- [ ] Endereço completo
- [ ] Contatos
- [ ] Logo

#### 2.8.2 Configurações de Boleto
- [ ] Multa padrão
- [ ] Juros padrão
- [ ] Dias de carência
- [ ] Desconto antecipação
- [ ] Instruções padrão

#### 2.8.3 Notificações
- [ ] Email de lembrete de vencimento
- [ ] Dias de antecedência
- [ ] Email de boleto gerado
- [ ] SMS/WhatsApp

#### 2.8.4 Usuários
- [ ] Lista de usuários
- [ ] Níveis de acesso
- [ ] Adicionar/Remover
- [ ] Permissões por módulo

---

## 3. PORTAL DO COMPRADOR ✅ IMPLEMENTADO

### 3.1 Auto-Cadastro
- [x] Formulário de auto-cadastro via CPF/CNPJ ✅
- [x] Validação de CPF/CNPJ existente no sistema ✅
- [x] Criação automática de usuário ✅
- [x] Vinculação com registro de Comprador ✅
- [x] Definição de senha pelo usuário ✅

### 3.2 Login/Autenticação
- [x] Login com CPF/CNPJ como username ✅
- [x] Autenticação via Django Auth ✅
- [x] Logout ✅
- [x] Registro de log de acesso ✅

### 3.3 Dashboard do Comprador
- [x] Card: Total de contratos ✅
- [x] Card: Parcelas em aberto ✅
- [x] Card: Total a pagar ✅
- [x] Lista: Contratos ativos ✅
- [x] Lista: Próximos vencimentos (5 próximas parcelas) ✅
- [x] Lista: Parcelas vencidas ✅
- [x] Resumo: Valor pago / A pagar ✅

### 3.4 Meus Contratos
- [x] Lista de contratos vinculados ao comprador ✅
- [x] Detalhes de cada contrato ✅
  - Dados do imóvel
  - Valores (entrada, total, saldo devedor)
  - Status do contrato
  - Lista de parcelas
  - Parcelas pagas vs pendentes
  - Próximo vencimento
- [x] Filtro por status (Ativo, Quitado) ✅

### 3.5 Meus Boletos
- [x] Lista de boletos disponíveis ✅
- [x] Filtros: Status, Período ✅
- [x] Download de boleto individual ✅
- [x] Visualização em nova aba ✅
- [x] Status do boleto (Pendente, Pago, Vencido) ✅

### 3.6 Meus Dados
- [x] Visualização dos dados pessoais ✅
- [x] Edição de dados de contato ✅
  - Email
  - Telefone
  - Celular
- [x] Dados não editáveis exibidos (CPF/CNPJ, Nome) ✅

### 3.7 Segurança
- [x] Alterar senha ✅
- [x] Validação de senha atual ✅
- [x] Confirmação de nova senha ✅
- [x] Requisitos mínimos de senha ✅

### 3.8 APIs do Portal
- [x] `GET /portal/api/contratos/` - Lista contratos do comprador ✅
- [x] `GET /portal/api/parcelas/` - Lista parcelas do comprador ✅
- [x] `GET /portal/api/dashboard/` - Dados do dashboard ✅

### 3.9 Modelos do Portal
- [x] `AcessoComprador` - Vincula Comprador ao User ✅
- [x] `LogAcessoComprador` - Registro de acessos ✅

### 3.10 URLs do Portal
```python
/portal/                     # Redirect para dashboard
/portal/cadastro/            # Auto-cadastro
/portal/login/               # Login
/portal/logout/              # Logout
/portal/dashboard/           # Dashboard
/portal/contratos/           # Lista de contratos
/portal/contratos/<id>/      # Detalhe do contrato
/portal/boletos/             # Lista de boletos
/portal/boletos/<id>/download/   # Download boleto
/portal/boletos/<id>/visualizar/ # Visualizar boleto
/portal/meus-dados/          # Dados pessoais
/portal/alterar-senha/       # Alterar senha
/portal/api/contratos/       # API contratos
/portal/api/parcelas/        # API parcelas
/portal/api/dashboard/       # API dashboard
```

---

## 4. COMPONENTES COMPARTILHADOS

### 4.1 Header/Navbar
- [ ] Logo
- [ ] Menu principal
- [ ] Notificações (badge)
- [ ] Perfil do usuário
- [ ] Troca de imobiliária (para contabilidade)

### 4.2 Sidebar
- [ ] Menu de navegação
- [ ] Ícones + Labels
- [ ] Indicadores de pendências
- [ ] Recolhível

### 4.3 Widgets Reutilizáveis
- [ ] Card de resumo (valor + label + ícone)
- [ ] Tabela paginada com filtros
- [ ] Gráfico de barras
- [ ] Gráfico de pizza
- [ ] Gráfico de linha (série temporal)
- [ ] Lista de alertas
- [ ] Modal de confirmação
- [ ] Modal de formulário
- [ ] Stepper/Wizard
- [ ] Upload de arquivo
- [ ] Seletor de período

### 4.4 Notificações
- [ ] Toast de sucesso/erro
- [ ] Alertas no dashboard
- [ ] Badge de contagem
- [ ] Centro de notificações

---

## 5. ESTRUTURA DE ARQUIVOS (DJANGO)

```
views/
├── contabilidade/
│   ├── dashboard.py
│   ├── imobiliarias.py
│   ├── relatorios.py
│   └── configuracoes.py
├── imobiliaria/
│   ├── dashboard.py
│   ├── contratos.py
│   ├── parcelas.py
│   ├── boletos.py
│   ├── reajustes.py
│   ├── relatorios.py
│   ├── cadastros.py
│   └── configuracoes.py
└── shared/
    ├── mixins.py
    ├── permissions.py
    └── utils.py

templates/
├── contabilidade/
│   ├── dashboard.html
│   ├── imobiliarias/
│   │   ├── lista.html
│   │   └── detalhes.html
│   └── relatorios/
│       ├── consolidado.html
│       ├── reajustes.html
│       └── inadimplencia.html
├── imobiliaria/
│   ├── dashboard.html
│   ├── contratos/
│   │   ├── lista.html
│   │   ├── detalhes.html
│   │   ├── novo.html
│   │   └── partials/
│   │       ├── _parcelas.html
│   │       ├── _intermediarias.html
│   │       ├── _reajustes.html
│   │       ├── _boletos.html
│   │       └── _pagamentos.html
│   ├── parcelas/
│   │   ├── a_receber.html
│   │   ├── vencidas.html
│   │   └── registrar_pagamento.html
│   ├── boletos/
│   │   ├── geracao.html
│   │   ├── remessas.html
│   │   └── retornos.html
│   ├── reajustes/
│   │   ├── pendentes.html
│   │   ├── aplicar.html
│   │   └── historico.html
│   ├── relatorios/
│   │   ├── prestacoes_pagar.html
│   │   ├── prestacoes_pagas.html
│   │   ├── posicao.html
│   │   ├── previsao.html
│   │   └── inadimplencia.html
│   ├── cadastros/
│   │   ├── compradores.html
│   │   ├── imoveis.html
│   │   └── contas_bancarias.html
│   └── configuracoes/
│       ├── dados.html
│       ├── boleto.html
│       ├── notificacoes.html
│       └── usuarios.html
├── components/
│   ├── _card_resumo.html
│   ├── _tabela_paginada.html
│   ├── _grafico.html
│   ├── _modal.html
│   ├── _wizard.html
│   └── _filtros.html
└── base/
    ├── base.html
    ├── _header.html
    ├── _sidebar.html
    └── _footer.html
```

---

## 6. APIs NECESSÁRIAS

### 6.1 Contabilidade ✅ PARCIALMENTE IMPLEMENTADO
- [x] `GET /api/contabilidade/dashboard/` - Dados do dashboard ✅ api_dashboard_contabilidade
- [ ] `GET /api/contabilidade/imobiliarias/` - Lista de imobiliárias
- [ ] `GET /api/contabilidade/relatorios/consolidado/` - Relatório consolidado
- [x] `GET /api/contabilidade/relatorios/reajustes/` - Reajustes pendentes ✅ RelatorioPrevisaoReajustesView
- [x] `GET /api/contabilidade/relatorios/inadimplencia/` - Inadimplência geral ✅ RelatorioPrestacoesAPagarView

### 6.2 Imobiliária ✅ PARCIALMENTE IMPLEMENTADO
- [ ] `GET /api/imobiliaria/dashboard/` - Dados do dashboard
- [ ] `GET /api/contratos/` - Lista de contratos
- [ ] `POST /api/contratos/` - Criar contrato
- [ ] `GET /api/contratos/{id}/` - Detalhes do contrato
- [ ] `PUT /api/contratos/{id}/` - Atualizar contrato
- [ ] `GET /api/contratos/{id}/parcelas/` - Parcelas do contrato
- [x] `GET /api/contratos/{id}/intermediarias/` - Intermediárias ✅ api_intermediarias_contrato
- [ ] `GET /api/contratos/{id}/reajustes/` - Histórico reajustes
- [ ] `POST /api/contratos/{id}/reajustes/` - Aplicar reajuste
- [ ] `GET /api/parcelas/` - Lista de parcelas (filtros)
- [ ] `POST /api/parcelas/{id}/pagamento/` - Registrar pagamento
- [x] `POST /api/parcelas/{id}/boleto/` - Gerar boleto ✅ gerar_boleto_parcela
- [x] `POST /api/boletos/lote/` - Gerar boletos em lote ✅ gerar_boletos_contrato
- [x] `GET /api/relatorios/prestacoes-pagar/` - Relatório ✅ RelatorioPrestacoesAPagarView
- [x] `GET /api/relatorios/prestacoes-pagas/` - Relatório ✅ RelatorioPrestacoesPageasView
- [x] `GET /api/relatorios/posicao/` - Relatório ✅ RelatorioPosicaoContratosView
- [x] `GET /api/relatorios/previsao/` - Relatório ✅ RelatorioPrevisaoReajustesView
- [x] `GET /api/relatorios/resumo/` - Resumo API ✅ api_relatorio_resumo
- [x] `GET /relatorios/exportar/<tipo>/` - Exportar CSV/JSON ✅ exportar_relatorio

### 6.3 Portal do Comprador ✅ IMPLEMENTADO
- [x] `GET /portal/api/contratos/` - Lista contratos do comprador ✅
- [x] `GET /portal/api/parcelas/` - Lista parcelas do comprador ✅
- [x] `GET /portal/api/dashboard/` - Dados do dashboard ✅

---

## 7. PERMISSÕES

### 7.1 Níveis de Acesso

| Perfil | Descrição |
|--------|-----------|
| **Administrador Contabilidade** | Acesso total a todas imobiliárias |
| **Operador Contabilidade** | Visualização de relatórios consolidados |
| **Administrador Imobiliária** | Acesso total à sua imobiliária |
| **Gerente Imobiliária** | Gestão de contratos e relatórios |
| **Operador Imobiliária** | Operações básicas (pagamentos, boletos) |
| **Visualizador** | Apenas consultas |

### 7.2 Matriz de Permissões

| Funcionalidade | Admin Cont. | Op. Cont. | Admin Imob. | Gerente | Operador | Visualizador |
|----------------|:-----------:|:---------:|:-----------:|:-------:|:--------:|:------------:|
| Dashboard Contab. | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Gerenciar Imobiliárias | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Dashboard Imob. | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Criar Contrato | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| Editar Contrato | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| Registrar Pagamento | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ |
| Gerar Boleto | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ |
| Aplicar Reajuste | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| Relatórios | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Configurações | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Gerenciar Usuários | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |

---

## 8. CRONOGRAMA SUGERIDO

### Fase 1: Fundação
1. Estrutura base de templates
2. Sistema de autenticação e permissões
3. Componentes compartilhados
4. APIs básicas

### Fase 2: Dashboard Imobiliária
1. Dashboard principal
2. Lista de contratos
3. Detalhes do contrato
4. Gestão de parcelas

### Fase 3: Operações Financeiras
1. Registrar pagamentos
2. Geração de boletos
3. Remessas/Retornos CNAB
4. Aplicação de reajustes

### Fase 4: Relatórios Imobiliária
1. Prestações a pagar/pagas
2. Posição de contratos
3. Previsão de recebimentos
4. Inadimplência

### Fase 5: Dashboard Contabilidade
1. Dashboard consolidado
2. Gestão de imobiliárias
3. Relatórios consolidados

### Fase 6: Refinamentos
1. Notificações
2. Exportações
3. Otimizações
4. Testes de usabilidade

---

*Documento criado em: 30/12/2024*
*Última atualização: 30/12/2024*

---

## RESUMO DE IMPLEMENTAÇÃO

### Implementado ✅
- Dashboard Contabilidade (views, APIs, relatórios)
- Dashboard Imobiliária (views básicas, alertas)
- Portal do Comprador (completo)
  - Auto-cadastro via CPF/CNPJ
  - Login/Logout
  - Dashboard
  - Meus Contratos
  - Meus Boletos
  - Meus Dados
  - Alterar Senha
  - APIs
- Gestão de Prestações Intermediárias (CRUD completo)
- Controle de bloqueio de boletos por reajuste
- Views de relatórios (Prestações a Pagar/Pagas, Posição, Previsão)
- Exportação de relatórios (CSV, JSON, PDF, Excel)
- Tasks Celery para automação

### Pendente
- Templates HTML (frontend)
- Componentes compartilhados (sidebar, navbar, widgets)
- Sistema de notificações
- Wizard de novo contrato
- Remessas/Retornos CNAB
- Configurações avançadas
