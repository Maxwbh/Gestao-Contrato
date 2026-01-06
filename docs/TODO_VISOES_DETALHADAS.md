# TODO - Visões Detalhadas por Perfil de Usuário

**Desenvolvedor:** Maxwell Oliveira (@maxwbh)
**Email:** maxwbh@gmail.com
**LinkedIn:** /maxwbh
**Empresa:** M&S do Brasil LTDA - www.msbrasil.inf.br

---

## Cenário de Negócio

Uma **Contabilidade** gerencia os boletos de pagamento de múltiplas **Incorporadoras/Imobiliárias** que vendem lotes em planos de:
- **Prazo máximo:** 360 meses (30 anos)
- **Prestações intermediárias:** Até 30 parcelas
- **Reajuste:** A cada 12-24 meses (configurável por contrato)
- **Dia de vencimento:** Definido no contrato de venda

---

## 1. VISÃO CONTABILIDADE

### 1.1 Dashboard Consolidado

#### 1.1.1 Visão Geral de Vencimentos - TODAS as Incorporadoras
- [ ] **Card:** Total de contratos ativos (todas incorporadoras)
- [ ] **Card:** Valor total a vencer na semana
- [ ] **Card:** Valor total a vencer no mês
- [ ] **Card:** Valor vencido (inadimplência)
- [ ] **Card:** Próximos reajustes pendentes

#### 1.1.2 Tabela: Contratos a Vencer/Vencidos por Período
```
Filtros:
- Incorporadora: [Todas] / [Selecionar específica]
- Período: [Esta semana] / [Este mês] / [Próximos 3 meses] / [Personalizado]
- Status: [A vencer] / [Vencidos] / [Todos]

Colunas:
| Incorporadora | Nº Contrato | Comprador | Parcela | Vencimento | Valor | Status | Dias | Ações |
```

- [ ] Implementar view `ContabilidadeVencimentosView`
- [ ] Implementar filtro por período (semana/mês/trimestre)
- [ ] Implementar filtro por incorporadora
- [ ] Implementar ordenação por data de vencimento
- [ ] Implementar ordenação por valor
- [ ] Implementar exportação para Excel/PDF
- [ ] Implementar paginação

#### 1.1.3 API: Vencimentos Consolidados
```python
GET /api/contabilidade/vencimentos/
    ?periodo=semana|mes|trimestre|custom
    &data_inicio=YYYY-MM-DD
    &data_fim=YYYY-MM-DD
    &imobiliaria_id=<id>
    &status=a_vencer|vencido|todos
```

- [ ] Implementar `api_contabilidade_vencimentos()`
- [ ] Retornar totalizadores por período
- [ ] Retornar lista paginada de parcelas
- [ ] Incluir dados da incorporadora em cada item

---

### 1.2 Geração de Boletos - Contabilidade

#### 1.2.1 Gerar Boleto Individual por Contrato
```
Fluxo:
1. Selecionar contrato específico
2. Visualizar parcelas disponíveis para geração
3. Selecionar: [Mês corrente] / [Próximos X meses]
4. Sistema limita automaticamente até a data do próximo reajuste
5. Confirmar geração
```

- [ ] Implementar view `GerarBoletoContratoView`
- [ ] Calcular limite máximo de meses (até próximo reajuste)
- [ ] Mostrar preview das parcelas que serão geradas
- [ ] Mostrar alerta se houver reajuste pendente
- [ ] Implementar geração em lote por contrato

#### 1.2.2 Gerar Boletos por Incorporadora
```
Fluxo:
1. Selecionar incorporadora
2. Selecionar período: [Mês corrente] / [Próximos X meses]
3. Sistema lista todos os contratos elegíveis
4. Filtrar contratos específicos (opcional)
5. Sistema respeita limite de reajuste de cada contrato
6. Confirmar geração em lote
```

- [ ] Implementar view `GerarBoletosImobiliariaView`
- [ ] Listar contratos elegíveis com resumo
- [ ] Mostrar quantidade de boletos por contrato
- [ ] Calcular valor total a ser gerado
- [ ] Implementar geração assíncrona (Celery task)
- [ ] Mostrar progresso de geração
- [ ] Gerar relatório de boletos gerados/bloqueados

#### 1.2.3 Gerar Boletos em Massa (Todas Incorporadoras)
```
Fluxo:
1. Selecionar período: [Mês corrente] / [Próximos X meses]
2. Filtrar por incorporadora (opcional)
3. Sistema lista todas as parcelas elegíveis
4. Respeita limite de reajuste de cada contrato
5. Confirmar geração em lote
6. Processar em background
```

- [ ] Implementar view `GerarBoletosMassaView`
- [ ] Implementar task Celery `gerar_boletos_massa`
- [ ] Implementar notificação de conclusão (email/sistema)
- [ ] Gerar relatório consolidado de geração

#### 1.2.4 Regra de Limite por Reajuste
```python
def calcular_limite_geracao_boletos(contrato):
    """
    Calcula até qual parcela boletos podem ser gerados.

    Regra: Só pode gerar boletos até o último mês do ciclo atual.
           Se reajuste pendente, bloqueia geração do próximo ciclo.

    Exemplo:
    - Contrato com reajuste a cada 12 meses
    - Ciclo atual: 1 (meses 1-12)
    - Pode gerar boletos: parcelas 1 a 12
    - Para gerar parcela 13+: precisa aplicar reajuste
    """
    pass
```

- [ ] Implementar `calcular_limite_geracao_boletos()`
- [ ] Integrar com views de geração de boleto
- [ ] Mostrar alerta visual quando próximo do limite
- [ ] Enviar notificação automática 30 dias antes do limite

#### 1.2.5 APIs de Geração de Boletos
```python
# Gerar boleto individual
POST /api/contabilidade/boletos/gerar/contrato/
{
    "contrato_id": 123,
    "periodo": "mes_corrente" | "proximos_x_meses",
    "quantidade_meses": 3  # se proximos_x_meses
}

# Gerar boletos por incorporadora
POST /api/contabilidade/boletos/gerar/imobiliaria/
{
    "imobiliaria_id": 456,
    "periodo": "mes_corrente" | "proximos_x_meses",
    "quantidade_meses": 3,
    "contratos_ids": [1, 2, 3]  # opcional, filtra contratos
}

# Gerar boletos em massa
POST /api/contabilidade/boletos/gerar/massa/
{
    "periodo": "mes_corrente" | "proximos_x_meses",
    "quantidade_meses": 3,
    "imobiliaria_ids": [1, 2]  # opcional
}
```

- [ ] Implementar `api_gerar_boleto_contrato()`
- [ ] Implementar `api_gerar_boletos_imobiliaria()`
- [ ] Implementar `api_gerar_boletos_massa()`

---

### 1.3 Relatórios Contabilidade

#### 1.3.1 Relatório de Vencimentos por Período
- [ ] Implementar relatório semanal
- [ ] Implementar relatório mensal
- [ ] Implementar relatório trimestral
- [ ] Agrupar por incorporadora
- [ ] Agrupar por status (a vencer/vencido)
- [ ] Exportar PDF/Excel

#### 1.3.2 Relatório de Boletos Gerados
- [ ] Por período
- [ ] Por incorporadora
- [ ] Por status (gerado/registrado/pago/vencido)
- [ ] Totalizadores

#### 1.3.3 Relatório de Inadimplência
- [ ] Por incorporadora
- [ ] Por faixa de atraso (30/60/90/120+ dias)
- [ ] Valor total em risco
- [ ] Evolução mensal

#### 1.3.4 Relatório de Reajustes
- [ ] Contratos com reajuste pendente
- [ ] Contratos próximos do reajuste (30/60/90 dias)
- [ ] Histórico de reajustes aplicados

---

## 2. VISÃO INCORPORADORA/IMOBILIÁRIA

### 2.1 Dashboard Incorporadora

#### 2.1.1 Visão Geral de Vencimentos
- [ ] **Card:** Contratos ativos
- [ ] **Card:** Valor a vencer na semana
- [ ] **Card:** Valor a vencer no mês
- [ ] **Card:** Valor vencido
- [ ] **Card:** Recebido no mês
- [ ] **Gráfico:** Fluxo de entrada (últimos 12 meses)

#### 2.1.2 Tabela: Contratos a Vencer/Vencidos
```
Filtros:
- Período: [Esta semana] / [Este mês] / [Próximos 3 meses] / [Personalizado]
- Status: [A vencer] / [Vencidos] / [Todos]
- Comprador: [Buscar por nome/CPF]

Colunas:
| Nº Contrato | Comprador | Imóvel | Parcela | Vencimento | Valor | Status | Dias | Ações |
```

- [ ] Implementar view `ImobiliariaVencimentosView`
- [ ] Implementar filtros por período
- [ ] Implementar busca por comprador
- [ ] Implementar ações rápidas (ver contrato, gerar boleto)

#### 2.1.3 API: Vencimentos da Incorporadora
```python
GET /api/imobiliaria/{id}/vencimentos/
    ?periodo=semana|mes|trimestre|custom
    &data_inicio=YYYY-MM-DD
    &data_fim=YYYY-MM-DD
    &status=a_vencer|vencido|todos
    &comprador_id=<id>
```

- [ ] Implementar `api_imobiliaria_vencimentos()`

---

### 2.2 Fluxo de Caixa - Incorporadora

#### 2.2.1 Visão de Entradas Previstas
```
Meses:     | Jan    | Fev    | Mar    | Abr    | Mai    | Jun    |
-----------+--------+--------+--------+--------+--------+--------+
Previsto   | 50.000 | 52.000 | 48.000 | 55.000 | 53.000 | 51.000 |
Recebido   | 48.000 | 50.000 | 45.000 | --     | --     | --     |
Pendente   | 2.000  | 2.000  | 3.000  | 55.000 | 53.000 | 51.000 |
```

- [ ] Implementar view `FluxoCaixaImobiliariaView`
- [ ] Calcular previsão mensal baseada em parcelas
- [ ] Mostrar recebido vs previsto
- [ ] Mostrar pendências acumuladas
- [ ] Gráfico de evolução

#### 2.2.2 Pendências Detalhadas
- [ ] Listar parcelas vencidas por comprador
- [ ] Calcular juros e multa acumulados
- [ ] Ações: enviar cobrança, gerar boleto atualizado

#### 2.2.3 API: Fluxo de Caixa
```python
GET /api/imobiliaria/{id}/fluxo-caixa/
    ?ano=2024
    ?meses=12
```

- [ ] Implementar `api_fluxo_caixa_imobiliaria()`
- [ ] Retornar previsão por mês
- [ ] Retornar realizado por mês
- [ ] Retornar pendências

---

### 2.3 Relatórios Incorporadora

#### 2.3.1 Relatório de Contratos
- [ ] Posição geral de todos os contratos
- [ ] Filtrar por status (ativo/quitado/cancelado)
- [ ] Progresso de pagamento

#### 2.3.2 Relatório de Recebimentos
- [ ] Por período
- [ ] Por comprador
- [ ] Forma de pagamento

#### 2.3.3 Relatório de Inadimplência
- [ ] Compradores inadimplentes
- [ ] Valor em atraso
- [ ] Tempo de atraso

---

## 3. VISÃO CONTRATANTE (Portal do Comprador)

### 3.1 Dashboard do Contratante

#### 3.1.1 Resumo do Contrato
- [ ] **Card:** Valor total do contrato
- [ ] **Card:** Valor já pago
- [ ] **Card:** Saldo devedor
- [ ] **Card:** Próximo vencimento
- [ ] **Barra:** Progresso de pagamento (%)

#### 3.1.2 Parcelas a Vencer/Vencidas
```
Filtros:
- Período: [Esta semana] / [Este mês] / [Próximos 3 meses] / [Todas]
- Status: [A vencer] / [Vencidas] / [Todas]

Colunas:
| Parcela | Vencimento | Valor | Status | Dias | Boleto | Ações |
```

- [ ] Implementar view `PortalContratoVencimentosView`
- [ ] Mostrar parcelas próximas do vencimento
- [ ] Destacar parcelas vencidas
- [ ] Mostrar juros/multa calculados

#### 3.1.3 API: Vencimentos do Contratante
```python
GET /portal/api/vencimentos/
    ?periodo=semana|mes|trimestre|todas
    ?status=a_vencer|vencido|todos
```

- [ ] Implementar `api_portal_vencimentos()`

---

### 3.2 Boletos do Contratante

#### 3.2.1 Lista de Boletos Gerados
```
Filtros:
- Status: [Pendente] / [Pago] / [Vencido] / [Todos]
- Período: [Este mês] / [Últimos 3 meses] / [Todos]

Colunas:
| Parcela | Vencimento | Valor | Status | Ações |

Ações:
- Visualizar boleto (PDF)
- Download boleto
- Copiar linha digitável
- Copiar PIX (se disponível)
```

- [ ] Implementar view `PortalBoletosListView`
- [ ] Filtrar por status
- [ ] Download individual
- [ ] Copiar linha digitável

#### 3.2.2 Detalhe do Boleto
- [ ] Visualizar PDF do boleto
- [ ] Mostrar linha digitável
- [ ] Mostrar QR Code PIX (se disponível)
- [ ] Mostrar instruções de pagamento
- [ ] Botão de download

#### 3.2.3 API: Boletos do Contratante
```python
GET /portal/api/boletos/
    ?status=pendente|pago|vencido|todos

GET /portal/api/boletos/{id}/
GET /portal/api/boletos/{id}/download/
GET /portal/api/boletos/{id}/linha-digitavel/
```

- [ ] Implementar `api_portal_boletos_lista()`
- [ ] Implementar `api_portal_boleto_detalhe()`
- [ ] Implementar `api_portal_boleto_download()`

---

### 3.3 Segunda Via de Boleto

#### 3.3.1 Solicitar Segunda Via
```
Fluxo:
1. Selecionar parcela vencida
2. Sistema calcula juros + multa
3. Mostrar valor atualizado
4. Gerar novo boleto com valor corrigido
5. Disponibilizar para download/visualização
```

- [ ] Implementar view `PortalSegundaViaView`
- [ ] Calcular encargos automaticamente
- [ ] Gerar boleto atualizado
- [ ] Enviar por email (opcional)

---

## 4. TAREFAS AUTOMÁTICAS (CELERY)

### 4.1 Notificações de Vencimento

#### 4.1.1 Alertas para Contabilidade
- [ ] `alerta_vencimentos_semana()` - Segunda-feira
- [ ] `alerta_vencimentos_mes()` - Primeiro dia útil
- [ ] `alerta_reajustes_pendentes()` - Diário

#### 4.1.2 Alertas para Incorporadora
- [ ] `alerta_inadimplencia_diario()` - Diário
- [ ] `resumo_recebimentos_semanal()` - Segunda-feira

#### 4.1.3 Alertas para Contratante
- [ ] `lembrete_vencimento_7dias()` - 7 dias antes
- [ ] `lembrete_vencimento_3dias()` - 3 dias antes
- [ ] `lembrete_vencimento_hoje()` - No dia
- [ ] `aviso_parcela_vencida()` - 1 dia após vencimento

### 4.2 Geração Automática de Boletos
- [ ] `gerar_boletos_mes_seguinte()` - Dia 25 de cada mês
- [ ] Respeitar limite de reajuste
- [ ] Gerar apenas para contratos sem boleto pendente

### 4.3 Relatórios Automáticos
- [ ] `relatorio_diario_contabilidade()` - Fim do dia
- [ ] `relatorio_semanal_incorporadoras()` - Segunda-feira
- [ ] `relatorio_mensal_consolidado()` - Primeiro dia útil

---

## 5. TEMPLATES NECESSÁRIOS

### 5.1 Contabilidade
```
templates/contabilidade/
├── dashboard.html
├── vencimentos/
│   ├── lista.html
│   ├── semana.html
│   ├── mes.html
│   └── trimestre.html
├── boletos/
│   ├── gerar_contrato.html
│   ├── gerar_imobiliaria.html
│   ├── gerar_massa.html
│   └── resultado.html
└── relatorios/
    ├── vencimentos.html
    ├── inadimplencia.html
    └── reajustes.html
```

### 5.2 Incorporadora
```
templates/imobiliaria/
├── dashboard.html
├── vencimentos/
│   └── lista.html
├── fluxo_caixa/
│   ├── visao_geral.html
│   └── pendencias.html
└── relatorios/
    ├── contratos.html
    ├── recebimentos.html
    └── inadimplencia.html
```

### 5.3 Portal do Comprador
```
templates/portal/
├── dashboard.html
├── contrato/
│   ├── resumo.html
│   └── vencimentos.html
├── boletos/
│   ├── lista.html
│   ├── detalhe.html
│   └── segunda_via.html
└── partials/
    ├── _card_resumo.html
    ├── _tabela_parcelas.html
    └── _boleto_card.html
```

---

## 6. APIS NECESSÁRIAS

### 6.1 Contabilidade
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/contabilidade/vencimentos/` | Lista vencimentos consolidados |
| GET | `/api/contabilidade/dashboard/` | Dados do dashboard |
| POST | `/api/contabilidade/boletos/gerar/contrato/` | Gerar boleto por contrato |
| POST | `/api/contabilidade/boletos/gerar/imobiliaria/` | Gerar boletos por incorporadora |
| POST | `/api/contabilidade/boletos/gerar/massa/` | Gerar boletos em massa |
| GET | `/api/contabilidade/relatorios/vencimentos/` | Relatório de vencimentos |
| GET | `/api/contabilidade/relatorios/inadimplencia/` | Relatório de inadimplência |

### 6.2 Incorporadora
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/imobiliaria/{id}/vencimentos/` | Lista vencimentos |
| GET | `/api/imobiliaria/{id}/fluxo-caixa/` | Fluxo de caixa |
| GET | `/api/imobiliaria/{id}/pendencias/` | Pendências detalhadas |
| GET | `/api/imobiliaria/{id}/dashboard/` | Dados do dashboard |

### 6.3 Portal do Comprador
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/portal/api/vencimentos/` | Lista vencimentos do comprador |
| GET | `/portal/api/boletos/` | Lista boletos |
| GET | `/portal/api/boletos/{id}/` | Detalhe do boleto |
| GET | `/portal/api/boletos/{id}/download/` | Download do boleto |
| POST | `/portal/api/boletos/segunda-via/` | Gerar segunda via |

---

## 7. PRIORIDADE DE IMPLEMENTAÇÃO

### Fase 1 - Essencial (Alta Prioridade)
1. [ ] Dashboard Contabilidade com vencimentos
2. [ ] Geração de boleto individual por contrato
3. [ ] Limite de geração por reajuste
4. [ ] Dashboard Incorporadora com vencimentos
5. [ ] Portal do Comprador - lista de boletos

### Fase 2 - Importante (Média Prioridade)
1. [ ] Geração de boletos por incorporadora
2. [ ] Geração de boletos em massa
3. [ ] Fluxo de caixa da incorporadora
4. [ ] Segunda via de boleto
5. [ ] Relatórios básicos

### Fase 3 - Complementar (Baixa Prioridade)
1. [ ] Alertas automáticos (Celery)
2. [ ] Geração automática de boletos
3. [ ] Relatórios avançados
4. [ ] Exportações PDF/Excel
5. [ ] Notificações por email

---

## 8. CONSIDERAÇÕES TÉCNICAS

### 8.1 Performance
- [ ] Implementar cache para dashboards
- [ ] Paginação em todas as listagens
- [ ] Índices no banco de dados para queries de vencimento
- [ ] Processamento assíncrono para geração em massa

### 8.2 Segurança
- [ ] Validar acesso por nível (contabilidade/incorporadora/comprador)
- [ ] Filtrar dados por tenant (incorporadora)
- [ ] Audit log para geração de boletos
- [ ] Rate limiting nas APIs

### 8.3 UX
- [ ] Loading states para operações longas
- [ ] Feedback visual para ações
- [ ] Confirmação antes de operações em massa
- [ ] Filtros persistentes por sessão

---

## 9. STATUS DE IMPLEMENTAÇÃO

### Funcionalidades Implementadas ✅

#### 9.1 Core
- [x] Modelos base (Contabilidade, Imobiliária, Comprador, Imóvel)
- [x] Modelos de contrato (Contrato, PrestacaoIntermediaria)
- [x] Modelos financeiros (Parcela, Reajuste, ContaBancaria)
- [x] Validações de negócio nos modelos (`clean()` methods)
- [x] Bloqueio de boletos por reajuste pendente (`pode_gerar_boleto()`)

#### 9.2 Serviços
- [x] BoletoService - Geração de boletos via BRCobranca API
- [x] CNABService - Geração de remessa CNAB 240/400
- [x] CNABService - Processamento de retorno CNAB 240/400
- [x] CNABService - Fallback local quando API indisponível
- [x] ReajusteService - Busca e aplicação de índices
- [x] ReajusteService - Simulação e aplicação de reajustes
- [x] RelatorioService - Geração de relatórios

#### 9.3 APIs REST Implementadas
- [x] `GET /api/imobiliarias/` - Lista imobiliárias com estatísticas
- [x] `GET /api/imobiliaria/{id}/dashboard/` - Dashboard completo
- [x] `GET /api/contratos/` - Lista contratos com paginação e filtros
- [x] `GET /api/contratos/{id}/` - Detalhes do contrato
- [x] `GET /api/contratos/{id}/parcelas/` - Parcelas do contrato
- [x] `GET /api/contratos/{id}/reajustes/` - Histórico de reajustes
- [x] `GET /api/parcelas/` - Lista parcelas com filtros avançados
- [x] `POST /api/parcelas/{id}/pagamento/` - Registrar pagamento

#### 9.4 Testes Implementados
- [x] Testes de validações de modelos (test_validations.py)
- [x] Testes de APIs REST (test_api_rest.py)
- [x] Testes de BoletoService (test_boleto_service.py)
- [x] Testes de ReajusteService (test_reajuste_service.py)
- [x] Testes de CNABService (test_cnab_service.py)
- [x] Testes de integração contrato/reajuste

#### 9.5 Integrações
- [x] BRCobranca Fork: https://github.com/Maxwbh/brcobranca
- [x] Docker: `docker run -p 9292:9292 maxwbh/brcobranca`

### Próximos Passos (Por Ordem de Prioridade)

1. **Dashboard Contabilidade** (Fase 1)
   - View de vencimentos consolidados
   - Filtros por período e incorporadora

2. **Geração de Boletos com Limite de Reajuste** (Fase 1)
   - Interface para geração individual
   - Implementar `calcular_limite_geracao_boletos()`

3. **Portal do Comprador** (Fase 1)
   - Lista de boletos
   - Download e segunda via

4. **Tasks Celery** (Fase 2)
   - Alertas de vencimento
   - Geração automática de boletos

---

*Documento criado em: 06/01/2026*
*Última atualização: 06/01/2026*
