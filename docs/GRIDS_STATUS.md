# Grids do Sistema — Status e Significados

**Última atualização:** 2026-04-22

Todas as tabelas do sistema usam [AG Grid](https://www.ag-grid.com/) com tema Material.
Este documento descreve cada grid, suas colunas de Status e o significado de cada valor.

---

## Legenda de Cores

| Badge         | Cor          | Significado geral                              |
|---------------|--------------|------------------------------------------------|
| `bg-success`  | Verde        | Concluído, ativo, pago, aprovado, entregue     |
| `bg-danger`   | Vermelho     | Erro, vencido, cancelado, protestado, falhou   |
| `bg-warning`  | Amarelo      | Pendente, aguardando, processando              |
| `bg-primary`  | Azul         | Enviado, ativo, informação positiva            |
| `bg-info`     | Ciano        | Em processamento, parcial, informação neutra   |
| `bg-secondary`| Cinza        | Inativo, neutro, sem dados                     |
| `bg-dark`     | Cinza escuro | Status especial (ex: Cancelado/Baixado)        |

---

## 1. Parcelas — Lista Geral

**Template:** `templates/financeiro/listar_parcelas.html`
**URL:** `/financeiro/parcelas/`

Grid com todas as prestações do sistema filtráveis por imobiliária, contrato, vencimento e status.

### Coluna: Status da Parcela

| Valor exibido | Cor      | Condição no sistema                        | O que significa                     |
|---------------|----------|--------------------------------------------|-------------------------------------|
| **Pago**      | Verde    | `parcela.pago = True`                      | Parcela quitada, pagamento registrado |
| **Vencida**   | Vermelho | `parcela.pago = False` e `data_vencimento < hoje` | Em atraso — gera juros e multa |
| **A Vencer**  | Azul     | `parcela.pago = False` e `data_vencimento >= hoje` | Ainda dentro do prazo              |

### Coluna: Boleto

| Valor exibido  | Cor          | Código interno  | O que significa                                           |
|----------------|--------------|-----------------|-----------------------------------------------------------|
| **—**          | Cinza claro  | `(sem boleto)`  | Boleto ainda não foi gerado                               |
| **Gerado**     | Azul         | `GERADO`        | PDF gerado no sistema, aguardando registro no banco       |
| **Registrado** | Ciano        | `REGISTRADO`    | Registrado na CIP/banco, pronto para pagamento            |
| **Pago**       | Verde        | `PAGO`          | Confirmação de pagamento recebida pelo banco               |
| **Vencido**    | Amarelo      | `VENCIDO`       | Data de vencimento ultrapassada sem pagamento             |
| **Cancelado**  | Cinza escuro | `CANCELADO`     | Boleto anulado manualmente ou por novo boleto emitido     |
| **Baixado**    | Amarelo      | `BAIXADO`       | Baixado no banco (liquidação por acordo ou cancelamento)  |
| **Protestado** | Vermelho     | `PROTESTADO`    | Enviado a protesto em cartório                            |

---

## 2. Parcelas do Mês

**Template:** `templates/financeiro/parcelas_mes.html`
**URL:** `/financeiro/parcelas-mes/`

Grid com as parcelas vencendo ou vencidas no mês selecionado. Usada para acompanhamento operacional.

### Coluna: Status

| Valor exibido | Cor      | Condição                                      | O que significa         |
|---------------|----------|-----------------------------------------------|-------------------------|
| **Pago**      | Verde    | `pago = True`                                 | Quitada                 |
| **Vencida**   | Vermelho | `pago = False` e data passada                 | Em atraso               |
| **A Vencer**  | Azul     | `pago = False` e data futura ou no dia        | Aguardando pagamento    |

---

## 3. Contratos

**Template:** `templates/contratos/contrato_list.html`
**URL:** `/contratos/`

Grid com todos os contratos de compra e venda cadastrados no sistema.

### Coluna: Status do Contrato

| Valor exibido | Cor      | Código interno | O que significa                                             |
|---------------|----------|----------------|-------------------------------------------------------------|
| **Ativo**     | Verde    | `ATIVO`        | Contrato em vigor, parcelas sendo cobradas normalmente      |
| **Quitado**   | Azul     | `QUITADO`      | Todas as parcelas pagas, contrato encerrado com sucesso     |
| **Cancelado** | Vermelho | `CANCELADO`    | Rescindido — comprador ou vendedor desistiu                 |
| **Suspenso**  | Amarelo  | `SUSPENSO`     | Temporariamente paralisado (ex: pendência jurídica)         |

### Coluna: Reajuste

| Valor exibido    | Cor      | O que significa                                                          |
|------------------|----------|--------------------------------------------------------------------------|
| **— (sem badge)**| —        | Nenhum reajuste pendente no mês corrente                                 |
| **Este mês**     | Amarelo  | Reajuste vence no mês corrente, ainda não aplicado (`meses_atraso = 0`) |
| **N mês(es)**    | Vermelho | Reajuste vencido há N meses sem ser aplicado (`meses_atraso > 0`)       |

---

## 4. Arquivos de Remessa (CNAB)

**Template:** `templates/financeiro/cnab/listar_remessas.html`
**URL:** `/financeiro/cnab/remessa/`

Grid com os arquivos CNAB gerados para envio ao banco (instrução de cobrança).

### Coluna: Status da Remessa

| Valor exibido  | Cor      | Código interno | O que significa                                             |
|----------------|----------|----------------|-------------------------------------------------------------|
| **Gerado**     | Ciano    | `GERADO`       | Arquivo gerado no sistema, ainda não enviado ao banco       |
| **Enviado**    | Azul     | `ENVIADO`      | Arquivo transmitido ao banco, aguardando processamento      |
| **Processado** | Verde    | `PROCESSADO`   | Banco processou os boletos — registros ativos na CIP        |
| **Erro**       | Vermelho | `ERRO`         | Falha no envio ou rejeição pelo banco — verificar log       |

---

## 5. Arquivos de Retorno (CNAB)

**Template:** `templates/financeiro/cnab/listar_retornos.html`
**URL:** `/financeiro/cnab/retorno/`

Grid com os arquivos de retorno enviados pelo banco (confirmações de pagamento).

### Coluna: Status do Retorno

| Valor exibido  | Cor      | Código interno        | O que significa                                                  |
|----------------|----------|-----------------------|------------------------------------------------------------------|
| **Pendente**   | Amarelo  | `PENDENTE`            | Arquivo recebido, aguardando processamento no sistema            |
| **Processado** | Verde    | `PROCESSADO`          | Todos os registros processados, baixas realizadas                |
| **Parcial**    | Ciano    | `PROCESSADO_PARCIAL`  | Parte dos registros processada — alguns com erro (ver detalhes)  |
| **Erro**       | Vermelho | `ERRO`                | Falha no parse do arquivo — formato inválido ou incompatível     |

---

## 6. Histórico de Reajustes

**Template:** `templates/financeiro/listar_reajustes.html`
**URL:** `/financeiro/reajustes/`

Grid com todos os ciclos de reajuste aplicados ou pendentes em cada contrato.

### Coluna: Status do Reajuste

| Valor exibido             | Cor      | Condição                             | O que significa                                      |
|---------------------------|----------|--------------------------------------|------------------------------------------------------|
| **Aplicado**              | Verde    | `reajuste.aplicado = True`           | Percentual aplicado, parcelas atualizadas             |
| **Aplicado + Manual**     | Verde + Cinza | `aplicado = True` e `aplicado_manual = True` | Aplicado com % informado manualmente (não calculado pelo sistema) |
| **Pendente**              | Amarelo  | `reajuste.aplicado = False`          | Ciclo venceu mas reajuste ainda não foi executado    |

---

## 7. Notificações

**Template:** `templates/notificacoes/listar.html`
**URL:** `/notificacoes/`

Grid com o histórico de todas as notificações disparadas (e-mail, SMS, WhatsApp).

### Coluna: Status

| Valor exibido  | Cor      | Código interno | O que significa                                            |
|----------------|----------|----------------|------------------------------------------------------------|
| **Pendente**   | Amarelo  | `PENDENTE`     | Na fila, ainda não processada pelo sistema                 |
| **Enviada**    | Verde    | `ENVIADA`      | Disparada com sucesso ao provedor (e-mail/SMS/WhatsApp)    |
| **Erro**       | Vermelho | `ERRO`         | Falha no envio — ver mensagem de erro no tooltip           |
| **Cancelada**  | Cinza    | `CANCELADA`    | Cancelada antes do envio (ex: parcela paga antes do disparo) |

---

## 8. Painel de Mensagens (WhatsApp / SMS / E-mail)

**Template:** `templates/notificacoes/painel_mensagens.html`
**URL:** `/notificacoes/painel/`

Grid detalhado com rastreamento de envio e entrega de cada mensagem.

### Coluna: Status de Envio

| Valor exibido  | Cor      | Código interno | O que significa                            |
|----------------|----------|----------------|--------------------------------------------|
| **Pendente**   | Amarelo  | `PENDENTE`     | Aguardando processamento na fila           |
| **Enviada**    | Verde    | `ENVIADA`      | Aceita pelo provedor de envio              |
| **Erro**       | Vermelho | `ERRO`         | Rejeitada ou falha no provedor             |
| **Cancelada**  | Cinza    | `CANCELADA`    | Cancelada antes de ser processada          |

### Coluna: Entrega (rastreamento em tempo real)

Rastreamento da mensagem após o envio — atualizado via webhook dos provedores.

| Valor exibido      | Cor      | Código interno  | O que significa                                              |
|--------------------|----------|-----------------|--------------------------------------------------------------|
| **—**              | Cinza    | `(vazio)`       | Sem informação de entrega ainda                              |
| **Enfileirado**    | Amarelo  | `queued`        | Aceito pelo provedor, aguardando transmissão                 |
| **Aceito**         | Amarelo  | `accepted`      | Aceito pelo gateway, em processamento                        |
| **Enviando**       | Ciano    | `sending`       | Em trânsito para o dispositivo do destinatário               |
| **Enviado**        | Azul     | `sent`          | Chegou ao servidor de destino (confirmação de rota)          |
| **Entregue**       | Verde    | `delivered`     | Confirmação de entrega no dispositivo (Evolution/Z-API/Twilio) |
| **Lido**           | Verde    | `read`          | Lido pelo destinatário (WhatsApp — dois checks azuis)        |
| **Aberto**         | Ciano    | `opened`        | E-mail aberto (rastreamento por pixel de leitura)            |
| **Clicado**        | Verde    | `clicked`       | Link dentro do e-mail clicado pelo destinatário              |
| **Não entregue**   | Vermelho | `undelivered`   | Falha na entrega (número inválido, bloqueado)                |
| **Falhou**         | Vermelho | `failed`        | Erro técnico na transmissão pelo provedor                    |
| **Bounce (NDR)**   | Vermelho | `bounced`       | E-mail rejeitado pelo servidor de destino (caixa cheia, domínio inválido) |

---

## 9. Templates de Notificação

**Template:** `templates/notificacoes/template_list.html`
**URL:** `/notificacoes/templates/`

Grid com os modelos de mensagem cadastrados para cada tipo de notificação.

### Coluna: Status

| Valor exibido | Cor    | O que significa                                              |
|---------------|--------|--------------------------------------------------------------|
| **Ativo**     | Verde  | Template em uso — será selecionado nos disparos automáticos  |
| **Inativo**   | Cinza  | Desativado — não será usado nos disparos, mas mantido no histórico |

### Coluna: Canais

| Badge         | Cor         | O que significa                          |
|---------------|-------------|------------------------------------------|
| **Email**     | Azul        | Template tem corpo HTML para e-mail      |
| **SMS**       | Ciano       | Template tem corpo de texto para SMS     |
| **WA**        | Verde (#25D366) | Template tem corpo para WhatsApp    |

---

## 10. Configurações de E-mail (SMTP)

**Template:** `templates/notificacoes/config_email_list.html`
**URL:** `/notificacoes/email/`

Grid com as configurações de servidor SMTP cadastradas.

### Coluna: Status

| Valor exibido | Cor   | O que significa                                |
|---------------|-------|------------------------------------------------|
| **Ativo**     | Verde | Configuração em uso para envio de e-mails      |
| **Inativo**   | Cinza | Desativada — não será usada nos envios         |

### Coluna: Segurança

| Valor exibido | Cor   | O que significa                        |
|---------------|-------|----------------------------------------|
| **TLS**       | Verde | Conexão criptografada via STARTTLS     |
| **SSL**       | Ciano | Conexão criptografada via SSL/TLS nativo |
| **Nenhuma**   | Cinza | Sem criptografia (não recomendado)     |

---

## 11. Configurações de WhatsApp

**Template:** `templates/notificacoes/config_whatsapp_list.html`
**URL:** `/notificacoes/whatsapp/`

Grid com as integrações de WhatsApp cadastradas (Evolution API, Z-API, Twilio, Meta).

### Coluna: Status

| Valor exibido | Cor   | O que significa                                      |
|---------------|-------|------------------------------------------------------|
| **Ativo**     | Verde | Provedor em uso para envio de mensagens WhatsApp     |
| **Inativo**   | Cinza | Desativado — não será usado nos envios               |

### Coluna: Provedor

| Valor exibido               | Cor      | O que é                                             |
|-----------------------------|----------|-----------------------------------------------------|
| **Evolution API (self-hosted)** | Verde | Instância própria, auto-hospedada                   |
| **Z-API**                   | Amarelo  | Serviço SaaS brasileiro de WhatsApp Business        |
| **Twilio**                  | Azul     | Plataforma global de comunicação em nuvem           |
| **Meta (WhatsApp Business API)** | Ciano | API oficial Meta/WhatsApp para empresas            |

---

## 12. Índices de Reajuste

**Template:** `templates/contratos/indice_list.html`
**URL:** `/contratos/indices/`

Grid com os valores mensais dos índices econômicos importados do IBGE/BCB/FGV.

### Coluna: Tipo de Índice

| Badge     | Cor      | O que é                                                           |
|-----------|----------|-------------------------------------------------------------------|
| **IPCA**  | Azul     | Índice de Preços ao Consumidor Amplo (IBGE)                       |
| **IGPM**  | Verde    | Índice Geral de Preços do Mercado (FGV)                           |
| **INCC**  | Ciano    | Índice Nacional do Custo da Construção (FGV)                      |
| **INPC**  | Vermelho | Índice Nacional de Preços ao Consumidor (IBGE)                    |
| **TR**    | Escuro   | Taxa Referencial (BCB)                                            |
| **SELIC** | Amarelo  | Taxa SELIC (BCB)                                                  |
| **IGPDI** | Amarelo  | Índice Geral de Preços — Disponibilidade Interna (FGV)            |

---

## 13. Compradores

**Template:** `templates/core/comprador_list.html`
**URL:** `/core/compradores/`

Grid com todos os compradores cadastrados no sistema.

### Coluna: Notificações

Indica quais canais de notificação estão habilitados para o comprador:

| Badge         | Cor   | O que significa                                    |
|---------------|-------|----------------------------------------------------|
| **Envelope**  | Azul  | Recebe notificações por e-mail (`notificar_email`) |
| **SMS**       | Verde | Recebe notificações por SMS (`notificar_sms`)      |
| **WhatsApp**  | Verde | Recebe notificações por WhatsApp (`notificar_whatsapp`) |
| **—**         | Cinza | Sem nenhum canal habilitado                        |

---

## 14. Acessos de Usuários

**Template:** `templates/core/acesso_list.html`
**URL:** `/core/acessos/`

Grid com os usuários e suas permissões por imobiliária.

### Colunas: Pode Editar / Pode Excluir

| Badge         | Cor      | O que significa                     |
|---------------|----------|-------------------------------------|
| **✓ (check)** | Verde    | Permissão concedida                 |
| **✗ (x)**     | Cinza    | Permissão negada                    |

---

## Resumo Rápido de Todos os Status

| Grid                  | Status possíveis                                                                                                 |
|-----------------------|------------------------------------------------------------------------------------------------------------------|
| Parcela               | Pago · Vencida · A Vencer                                                                                        |
| Boleto (da parcela)   | — · Gerado · Registrado · Pago · Vencido · Cancelado · Baixado · Protestado                                     |
| Contrato (status)     | Ativo · Quitado · Cancelado · Suspenso                                                                           |
| Contrato (reajuste)   | — · Este mês · N mês(es)                                                                                        |
| Remessa CNAB          | Gerado · Enviado · Processado · Erro                                                                             |
| Retorno CNAB          | Pendente · Processado · Parcial · Erro                                                                           |
| Reajuste              | Aplicado · Aplicado (Manual) · Pendente                                                                          |
| Notificação           | Pendente · Enviada · Erro · Cancelada                                                                            |
| Entrega (mensagem)    | Enfileirado · Aceito · Enviando · Enviado · Entregue · Lido · Aberto · Clicado · Não entregue · Falhou · Bounce |
| Template Notificação  | Ativo · Inativo                                                                                                  |
| Config E-mail         | Ativo · Inativo                                                                                                  |
| Config WhatsApp       | Ativo · Inativo                                                                                                  |
