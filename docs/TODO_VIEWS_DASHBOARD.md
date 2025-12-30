# TODO - Visões e Dashboards

## Visão Geral

Este documento detalha as telas e dashboards para os dois níveis de acesso do sistema:
- **Contabilidade**: Visão consolidada de múltiplas imobiliárias
- **Imobiliária**: Visão detalhada dos contratos e operações

---

## 1. DASHBOARD CONTABILIDADE

### 1.1 Visão Geral (Home)
- [ ] Card: Total de imobiliárias gerenciadas
- [ ] Card: Total de contratos ativos (todas imobiliárias)
- [ ] Card: Valor total a receber (consolidado)
- [ ] Card: Valor total em atraso (consolidado)
- [ ] Gráfico: Recebimentos mensais (últimos 12 meses)
- [ ] Gráfico: Inadimplência por imobiliária (pizza/barras)
- [ ] Lista: Top 5 imobiliárias por faturamento
- [ ] Lista: Alertas de reajustes pendentes

### 1.2 Relatório Consolidado por Imobiliária
- [ ] Tabela com todas imobiliárias:
  - Nome/Razão Social
  - CNPJ
  - Qtd. Contratos Ativos
  - Valor Total Contratos
  - Valor Recebido (mês)
  - Valor a Receber
  - Valor em Atraso
  - % Inadimplência
- [ ] Filtros: Período, Status
- [ ] Exportar: PDF, Excel

### 1.3 Relatório de Reajustes Pendentes
- [ ] Lista de contratos com reajuste próximo (30/60/90 dias)
- [ ] Agrupamento por imobiliária
- [ ] Status do reajuste (Pendente, Criado, Aplicado)
- [ ] Ação: Notificar imobiliária
- [ ] Exportar: PDF, Excel

### 1.4 Relatório de Inadimplência Geral
- [ ] Tabela de parcelas vencidas (todas imobiliárias):
  - Imobiliária
  - Contrato
  - Comprador
  - Parcela
  - Vencimento
  - Valor
  - Dias em Atraso
  - Juros + Multa
- [ ] Filtros: Imobiliária, Período, Dias de atraso
- [ ] Totalizadores por imobiliária
- [ ] Exportar: PDF, Excel

### 1.5 Configurações da Contabilidade
- [ ] Dados cadastrais
- [ ] Lista de imobiliárias vinculadas
- [ ] Adicionar/Remover imobiliária
- [ ] Usuários com acesso
- [ ] Configurações de notificação

---

## 2. DASHBOARD IMOBILIÁRIA

### 2.1 Visão Geral (Home)
- [ ] Card: Contratos Ativos
- [ ] Card: Contratos Quitados
- [ ] Card: Valor a Receber (total)
- [ ] Card: Valor em Atraso
- [ ] Card: Recebido no Mês
- [ ] Card: Próximos Vencimentos (7 dias)
- [ ] Gráfico: Recebimentos x Previsão (últimos 6 meses)
- [ ] Gráfico: Status dos Contratos (pizza)
- [ ] Lista: Parcelas vencendo hoje
- [ ] Lista: Parcelas vencidas (top 10 por valor)
- [ ] Alerta: Contratos com reajuste pendente

### 2.2 Gestão de Contratos

#### 2.2.1 Lista de Contratos
- [ ] Tabela com filtros:
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

## 3. COMPONENTES COMPARTILHADOS

### 3.1 Header/Navbar
- [ ] Logo
- [ ] Menu principal
- [ ] Notificações (badge)
- [ ] Perfil do usuário
- [ ] Troca de imobiliária (para contabilidade)

### 3.2 Sidebar
- [ ] Menu de navegação
- [ ] Ícones + Labels
- [ ] Indicadores de pendências
- [ ] Recolhível

### 3.3 Widgets Reutilizáveis
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

### 3.4 Notificações
- [ ] Toast de sucesso/erro
- [ ] Alertas no dashboard
- [ ] Badge de contagem
- [ ] Centro de notificações

---

## 4. ESTRUTURA DE ARQUIVOS (DJANGO)

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

## 5. APIs NECESSÁRIAS

### 5.1 Contabilidade
- [ ] `GET /api/contabilidade/dashboard/` - Dados do dashboard
- [ ] `GET /api/contabilidade/imobiliarias/` - Lista de imobiliárias
- [ ] `GET /api/contabilidade/relatorios/consolidado/` - Relatório consolidado
- [ ] `GET /api/contabilidade/relatorios/reajustes/` - Reajustes pendentes
- [ ] `GET /api/contabilidade/relatorios/inadimplencia/` - Inadimplência geral

### 5.2 Imobiliária
- [ ] `GET /api/imobiliaria/dashboard/` - Dados do dashboard
- [ ] `GET /api/contratos/` - Lista de contratos
- [ ] `POST /api/contratos/` - Criar contrato
- [ ] `GET /api/contratos/{id}/` - Detalhes do contrato
- [ ] `PUT /api/contratos/{id}/` - Atualizar contrato
- [ ] `GET /api/contratos/{id}/parcelas/` - Parcelas do contrato
- [ ] `GET /api/contratos/{id}/intermediarias/` - Intermediárias
- [ ] `GET /api/contratos/{id}/reajustes/` - Histórico reajustes
- [ ] `POST /api/contratos/{id}/reajustes/` - Aplicar reajuste
- [ ] `GET /api/parcelas/` - Lista de parcelas (filtros)
- [ ] `POST /api/parcelas/{id}/pagamento/` - Registrar pagamento
- [ ] `POST /api/parcelas/{id}/boleto/` - Gerar boleto
- [ ] `POST /api/boletos/lote/` - Gerar boletos em lote
- [ ] `GET /api/relatorios/prestacoes-pagar/` - Relatório
- [ ] `GET /api/relatorios/prestacoes-pagas/` - Relatório
- [ ] `GET /api/relatorios/posicao/` - Relatório
- [ ] `GET /api/relatorios/previsao/` - Relatório

---

## 6. PERMISSÕES

### 6.1 Níveis de Acesso

| Perfil | Descrição |
|--------|-----------|
| **Administrador Contabilidade** | Acesso total a todas imobiliárias |
| **Operador Contabilidade** | Visualização de relatórios consolidados |
| **Administrador Imobiliária** | Acesso total à sua imobiliária |
| **Gerente Imobiliária** | Gestão de contratos e relatórios |
| **Operador Imobiliária** | Operações básicas (pagamentos, boletos) |
| **Visualizador** | Apenas consultas |

### 6.2 Matriz de Permissões

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

## 7. CRONOGRAMA SUGERIDO

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
