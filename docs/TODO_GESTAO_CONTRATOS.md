# TODO - Sistema de Gestão de Contratos

## Visão Geral do Projeto

Sistema de gestão de contratos imobiliários com as seguintes características:
- **Prazo máximo:** 360 meses (30 anos)
- **Prestações intermediárias:** Até 30 parcelas intermediárias
- **Reajuste:** A cada 12 meses por índices oficiais (INPC, IGPM, etc.)
- **Boletos:** Emissão mensal, bloqueada após 12º mês até aplicação do reajuste
- **Relatórios:** Prestações a pagar e prestações pagas

---

## 1. MODELO DE DADOS

### 1.1 Contrato - Ajustes Necessários
- [x] Adicionar campo `numero_maximo_parcelas` (validação até 360 meses) ✅ IMPLEMENTADO
- [x] Adicionar campo `quantidade_intermediarias` (máximo 30) ✅ IMPLEMENTADO
- [x] Adicionar campo `ultimo_mes_boleto_gerado` (controle de limite 12 meses) ✅ IMPLEMENTADO
- [x] Adicionar campo `bloqueio_boleto_reajuste` (boolean - bloqueia geração após 12º mês) ✅ IMPLEMENTADO
- [x] Adicionar validação: `prazo_reajuste_meses` padrão = 12 ✅ IMPLEMENTADO

### 1.2 Nova Model: PrestacaoIntermediaria ✅ IMPLEMENTADO
```python
class PrestacaoIntermediaria(models.Model):
    contrato = ForeignKey(Contrato)
    numero_sequencial = PositiveIntegerField()  # 1 a 30
    mes_vencimento = PositiveIntegerField()     # Mês relativo ao início do contrato
    valor = DecimalField()
    paga = BooleanField(default=False)
    data_pagamento = DateField(null=True)
    parcela_vinculada = ForeignKey(Parcela, null=True)  # Parcela gerada para esta intermediária
    valor_reajustado = DecimalField(null=True)  # Valor após reajuste
```

### 1.3 Parcela - Ajustes Necessários
- [x] Adicionar campo `tipo_parcela` (NORMAL, INTERMEDIARIA, ENTRADA) ✅ IMPLEMENTADO
- [x] Adicionar campo `ciclo_reajuste` (1 = meses 1-12, 2 = meses 13-24, etc.) ✅ IMPLEMENTADO

### 1.4 Reajuste - Ajustes Necessários
- [x] Adicionar campo `ciclo` (número do ciclo de 12 meses) ✅ IMPLEMENTADO
- [x] Adicionar campo `data_limite_boleto` (data até quando boletos podem ser gerados) ✅ IMPLEMENTADO
- [x] Adicionar campo `aplicado` e `data_aplicacao` ✅ IMPLEMENTADO
- [x] Adicionar validação de aplicação obrigatória antes de liberar próximo ciclo ✅ IMPLEMENTADO

---

## 2. REGRAS DE NEGÓCIO

### 2.1 Criação de Contrato
- [ ] Validar prazo máximo de 360 meses
- [ ] Validar máximo de 30 prestações intermediárias
- [ ] Calcular valor das parcelas mensais considerando:
  - Valor financiado
  - Número de parcelas normais
  - Prestações intermediárias (deduzir do financiamento ou somar)
- [ ] Definir índice de reajuste (INPC, IGPM, INCC, etc.)
- [ ] Gerar cronograma de reajustes

### 2.2 Geração de Parcelas
- [ ] Gerar parcelas mensais (até 360)
- [ ] Gerar parcelas intermediárias nas datas configuradas
- [ ] Marcar ciclo de reajuste em cada parcela
- [ ] Calcular datas de vencimento considerando:
  - Dia de vencimento definido no contrato
  - Ajuste para meses com menos dias
  - Feriados e fins de semana (próximo dia útil)

### 2.3 Controle de Reajuste (CRÍTICO)
```
REGRA: Só é possível emitir boleto até o 12º mês de cada ciclo.
       No 13º mês, a emissão só é liberada APÓS aplicação do reajuste.
```

- [ ] Implementar verificação `pode_gerar_boleto(parcela)`:
  ```python
  def pode_gerar_boleto(parcela):
      ciclo_atual = parcela.ciclo_reajuste
      reajuste_aplicado = Reajuste.objects.filter(
          contrato=parcela.contrato,
          ciclo=ciclo_atual
      ).exists()

      # Primeiro ciclo (meses 1-12): sempre pode gerar
      if ciclo_atual == 1:
          return True

      # Ciclos seguintes: só se reajuste foi aplicado
      return reajuste_aplicado
  ```

- [ ] Implementar alerta automático quando:
  - Faltam 30 dias para fim do ciclo de 12 meses
  - Reajuste ainda não foi aplicado
  - Existem parcelas do próximo ciclo sem boleto

- [ ] Implementar bloqueio na view de geração de boleto:
  - Mostrar mensagem clara: "Reajuste pendente para o ciclo X"
  - Botão para aplicar reajuste
  - Lista de índices disponíveis para o período

### 2.4 Aplicação de Reajuste
- [ ] Buscar índice automaticamente da API do Banco Central
- [ ] Permitir seleção manual de índice se automático falhar
- [ ] Calcular novo valor das parcelas:
  ```
  valor_reajustado = valor_atual * (1 + indice/100)
  ```
- [ ] Aplicar reajuste em TODAS as parcelas futuras (não pagas)
- [ ] Registrar histórico de reajuste aplicado
- [ ] Liberar geração de boletos do próximo ciclo

### 2.5 Emissão de Boletos
- [ ] Verificar se reajuste está aplicado (conforme regra 2.3)
- [ ] Gerar boleto via BRCobrança API (já implementado)
- [ ] Registrar ciclo de reajuste no boleto
- [ ] Enviar notificação ao comprador (já implementado)

---

## 3. PRESTAÇÕES INTERMEDIÁRIAS

### 3.1 Configuração
- [ ] Tela para configurar prestações intermediárias no contrato:
  - Quantidade (1 a 30)
  - Valor de cada intermediária
  - Mês de vencimento relativo (ex: mês 6, 12, 18, 24...)
  - Opção: valor fixo ou % do financiamento

### 3.2 Geração
- [ ] Gerar parcelas do tipo INTERMEDIARIA junto com as normais
- [ ] Respeitar ordem de vencimento
- [ ] Calcular impacto no valor das parcelas normais (se aplicável)

### 3.3 Reajuste de Intermediárias
- [ ] Aplicar mesmo índice de reajuste das parcelas normais
- [ ] Intermediárias futuras devem ser reajustadas
- [ ] Manter histórico de valores originais vs reajustados

---

## 4. RELATÓRIOS

### 4.1 Relatório: Prestações a Pagar
- [ ] **Filtros:**
  - Contrato específico ou todos
  - Período (data inicial/final de vencimento)
  - Status: Todas, Vencidas, A vencer
  - Tipo: Normal, Intermediária, Todas
  - Imobiliária/Comprador

- [ ] **Colunas:**
  - Nº Contrato
  - Comprador
  - Nº Parcela
  - Tipo (Normal/Intermediária)
  - Data Vencimento
  - Valor Original
  - Valor Atual (reajustado)
  - Dias em Atraso (se vencida)
  - Juros/Multa Acumulados
  - Valor Total Devido
  - Status Boleto

- [ ] **Totalizadores:**
  - Total de parcelas a pagar
  - Valor total a receber
  - Valor total vencido
  - Valor total a vencer

- [ ] **Exportação:**
  - PDF
  - Excel (XLSX)
  - CSV

### 4.2 Relatório: Prestações Pagas
- [ ] **Filtros:**
  - Contrato específico ou todos
  - Período de pagamento (data inicial/final)
  - Forma de pagamento
  - Tipo: Normal, Intermediária, Todas
  - Imobiliária/Comprador

- [ ] **Colunas:**
  - Nº Contrato
  - Comprador
  - Nº Parcela
  - Tipo (Normal/Intermediária)
  - Data Vencimento
  - Data Pagamento
  - Valor Original
  - Valor Pago
  - Juros Pagos
  - Multa Paga
  - Desconto Aplicado
  - Forma de Pagamento

- [ ] **Totalizadores:**
  - Total de parcelas pagas
  - Valor total recebido
  - Total de juros recebidos
  - Total de multas recebidas
  - Total de descontos concedidos

- [ ] **Exportação:**
  - PDF
  - Excel (XLSX)
  - CSV

### 4.3 Relatório: Posição de Contratos
- [ ] **Visão geral de cada contrato:**
  - Valor total do contrato
  - Valor já pago
  - Saldo devedor (original)
  - Saldo devedor (reajustado)
  - Próxima parcela a vencer
  - Status do reajuste (aplicado/pendente)
  - % de conclusão

### 4.4 Relatório: Previsão de Reajustes
- [ ] **Contratos com reajuste próximo:**
  - Data do próximo reajuste
  - Índice a ser aplicado
  - Valor estimado do reajuste
  - Parcelas afetadas
  - Status: Pendente/Aplicado

---

## 5. TELAS E INTERFACES

### 5.1 Dashboard de Contratos
- [ ] Resumo: contratos ativos, valor a receber, inadimplência
- [ ] Alertas de reajuste pendente
- [ ] Gráfico de recebimentos mensais
- [ ] Lista de parcelas vencendo nos próximos 30 dias

### 5.2 Tela de Contrato
- [ ] Aba: Dados Gerais (já existe)
- [ ] Aba: Parcelas (já existe)
- [ ] Aba: Prestações Intermediárias (NOVO)
- [ ] Aba: Histórico de Reajustes (NOVO)
- [ ] Aba: Boletos Gerados (já existe parcialmente)
- [ ] Aba: Relatórios do Contrato (NOVO)

### 5.3 Tela de Reajuste
- [ ] Listar contratos com reajuste pendente
- [ ] Selecionar índice de reajuste
- [ ] Visualizar prévia do impacto
- [ ] Aplicar reajuste em lote ou individual
- [ ] Histórico de reajustes aplicados

### 5.4 Tela de Geração de Boletos em Lote
- [ ] Filtrar parcelas por período
- [ ] Mostrar status de reajuste de cada parcela
- [ ] Bloquear seleção de parcelas com reajuste pendente
- [ ] Gerar boletos selecionados

---

## 6. TAREFAS AUTOMÁTICAS (CELERY)

### 6.1 Busca de Índices
- [ ] `buscar_indices_economicos()` - Diário
  - Consultar API do Banco Central
  - Armazenar INPC, IGPM, INCC, IGPDI, TR, SELIC
  - Notificar se índice não disponível

### 6.2 Alertas de Reajuste
- [ ] `verificar_reajustes_pendentes()` - Diário
  - Identificar contratos no 12º mês do ciclo
  - Enviar alerta para administradores
  - Gerar relatório de reajustes pendentes

### 6.3 Geração Automática de Boletos
- [ ] `gerar_boletos_automaticos()` - Mensal
  - Gerar boletos para parcelas do próximo mês
  - Respeitar regra de bloqueio por reajuste
  - Registrar falhas e notificar

### 6.4 Atualização de Multa/Juros
- [ ] `atualizar_encargos_parcelas()` - Diário
  - Recalcular juros e multa de parcelas vencidas
  - Atualizar campo valor_atual

---

## 7. VALIDAÇÕES E REGRAS DE NEGÓCIO

### 7.1 Validações de Contrato
- [ ] `numero_parcelas` deve ser entre 1 e 360
- [ ] `quantidade_intermediarias` deve ser entre 0 e 30
- [ ] `prazo_reajuste_meses` padrão 12, mínimo 1, máximo 24
- [ ] Soma das intermediárias não pode exceder valor financiado
- [ ] Data de vencimento deve ser dia válido (1-28 recomendado)

### 7.2 Validações de Parcela
- [ ] Não permitir pagamento menor que valor mínimo
- [ ] Não permitir boleto para parcela já paga
- [ ] Não permitir boleto se reajuste pendente (ciclo > 1)

### 7.3 Validações de Reajuste
- [ ] Índice deve existir para o período
- [ ] Reajuste não pode ser aplicado retroativamente
- [ ] Deve seguir sequência de ciclos (não pular ciclos)

---

## 8. INTEGRAÇÕES

### 8.1 BRCobrança (Já Implementado)
- [x] Geração de boletos
- [x] Suporte a múltiplos bancos
- [ ] Arquivo de remessa CNAB 240/400
- [ ] Processamento de arquivo retorno

### 8.2 Banco Central do Brasil
- [ ] Consulta automática de índices via API
- [ ] Fallback para consulta manual se API indisponível

### 8.3 Notificações (Parcialmente Implementado)
- [x] E-mail de boleto gerado
- [ ] SMS/WhatsApp de lembrete de vencimento
- [ ] Alerta de reajuste pendente para admin

---

## 9. CRONOGRAMA DE IMPLEMENTAÇÃO SUGERIDO

### Fase 1: Fundação
1. Ajustar modelo Contrato com novos campos
2. Criar modelo PrestacaoIntermediaria
3. Ajustar modelo Parcela com tipo e ciclo
4. Implementar validações básicas
5. Criar migrations

### Fase 2: Regras de Reajuste
1. Implementar lógica de ciclos de reajuste
2. Implementar bloqueio de boleto por reajuste
3. Criar tela de aplicação de reajuste
4. Integrar busca automática de índices

### Fase 3: Prestações Intermediárias
1. Criar formulário de configuração
2. Implementar geração automática
3. Ajustar cálculos de reajuste
4. Testes de integração

### Fase 4: Relatórios
1. Implementar relatório de prestações a pagar
2. Implementar relatório de prestações pagas
3. Implementar relatório de posição de contratos
4. Criar exportações (PDF, Excel, CSV)

### Fase 5: Automação
1. Configurar tasks Celery
2. Implementar alertas automáticos
3. Implementar geração automática de boletos
4. Testes de carga e performance

### Fase 6: Refinamento
1. Testes de usuário
2. Ajustes de usabilidade
3. Documentação
4. Deploy em produção

---

## 10. OBSERVAÇÕES TÉCNICAS

### Stack Atual do Projeto
- **Backend:** Django 4.2.7, Python 3.11+
- **Banco de Dados:** PostgreSQL
- **Fila de Tarefas:** Celery + Redis
- **Boletos:** BRCobrança API
- **Frontend:** Bootstrap 5, JavaScript

### Modelos Existentes Relevantes
- `core/models.py`: Contabilidade, Imobiliária, ContaBancaria, Imovel, Comprador
- `contratos/models.py`: Contrato, IndiceReajuste
- `financeiro/models.py`: Parcela, Reajuste, HistoricoPagamento, StatusBoleto

### Arquivos Chave
- `/home/user/Gestao-Contrato/contratos/models.py` - Modelo de Contrato
- `/home/user/Gestao-Contrato/financeiro/models.py` - Modelo de Parcela e Reajuste
- `/home/user/Gestao-Contrato/financeiro/services/boleto_service.py` - Serviço de Boleto

---

*Documento criado em: 30/12/2025*
*Última atualização: 30/12/2025*
