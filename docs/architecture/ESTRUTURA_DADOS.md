# Estrutura de Dados - Sistema Gestão de Contratos

Documentação da estrutura de dados do sistema de gestão de contratos imobiliários.

**Desenvolvedor:** Maxwell da Silva Oliveira
**Empresa:** M&S do Brasil LTDA
**Última atualização:** Novembro 2025

---

## Índice

1. [Módulo Core](#módulo-core)
2. [Módulo Contratos](#módulo-contratos)
3. [Módulo Financeiro](#módulo-financeiro)
4. [Módulo Notificações](#módulo-notificações)
5. [Relacionamentos](#relacionamentos)
6. [Configurações de Boleto](#configurações-de-boleto)

---

## Módulo Core

### Contabilidade
Representa um escritório de contabilidade que gerencia múltiplas imobiliárias.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | AutoField | Chave primária |
| nome | CharField(200) | Nome do escritório |
| razao_social | CharField(200) | Razão social |
| cnpj | CharField(20) | CNPJ formatado |
| endereco | TextField | Endereço completo |
| telefone | CharField(20) | Telefone principal |
| email | EmailField | E-mail principal |
| responsavel | CharField(200) | Nome do responsável |
| ativo | BooleanField | Status de ativo |
| criado_em | DateTimeField | Data de criação |
| atualizado_em | DateTimeField | Data de atualização |

### Imobiliária
Representa uma imobiliária vinculada a uma contabilidade.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | AutoField | Chave primária |
| contabilidade | ForeignKey | Ref. para Contabilidade |
| nome | CharField(200) | Nome fantasia |
| razao_social | CharField(200) | Razão social |
| cnpj | CharField(20) | CNPJ formatado |
| cep | CharField(10) | CEP |
| logradouro | CharField(255) | Logradouro |
| numero | CharField(10) | Número |
| complemento | CharField(100) | Complemento |
| bairro | CharField(100) | Bairro |
| cidade | CharField(100) | Cidade |
| estado | CharField(2) | UF |
| telefone | CharField(20) | Telefone |
| email | EmailField | E-mail |
| responsavel_financeiro | CharField(200) | Responsável financeiro |

**Configurações de Boleto Padrão:**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| tipo_valor_multa | CharField(10) | PERCENTUAL ou VALOR |
| percentual_multa_padrao | DecimalField(10,2) | Valor/percentual da multa |
| tipo_valor_juros | CharField(10) | PERCENTUAL ou VALOR |
| percentual_juros_padrao | DecimalField(10,4) | Juros ao dia |
| dias_para_encargos_padrao | IntegerField | Dias sem encargos após vencimento |
| tipo_valor_desconto | CharField(10) | PERCENTUAL ou VALOR |
| percentual_desconto_padrao | DecimalField(10,2) | Valor/percentual do desconto |
| dias_para_desconto_padrao | IntegerField | Dias antes do vencimento para desconto |
| instrucao_padrao | CharField(255) | Instrução padrão do boleto |
| tipo_titulo | CharField(5) | Tipo do título (DM, RC, etc.) |
| aceite | BooleanField | Aceite do boleto |

### ContaBancaria
Conta bancária de uma imobiliária para emissão de boletos.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | AutoField | Chave primária |
| imobiliaria | ForeignKey | Ref. para Imobiliária |
| banco | CharField(3) | Código do banco (001, 237, etc.) |
| descricao | CharField(150) | Descrição da conta |
| principal | BooleanField | Se é a conta principal |
| agencia | CharField(10) | Número da agência |
| conta | CharField(20) | Número da conta |
| convenio | CharField(20) | Código do convênio |
| carteira | CharField(5) | Carteira de cobrança |
| nosso_numero_atual | IntegerField | Sequencial do nosso número |
| modalidade | CharField(5) | Modalidade da carteira |
| cobranca_registrada | BooleanField | Se usa cobrança registrada |
| prazo_baixa | IntegerField | Dias para baixa automática |
| prazo_protesto | IntegerField | Dias para protesto |
| layout_cnab | CharField(10) | Layout CNAB (240 ou 400) |
| numero_remessa_cnab_atual | IntegerField | Sequencial de remessa |
| tipo_pix | CharField(20) | Tipo da chave PIX |
| chave_pix | CharField(100) | Chave PIX |
| ativo | BooleanField | Status de ativo |

**Configurações por Banco (BRCobranca):**

| Banco | Código | Convênio | Carteira Padrão | Campos Específicos |
|-------|--------|----------|-----------------|-------------------|
| Banco do Brasil | 001 | 7 dígitos (obrigatório) | 18 | - |
| Santander | 033 | 7 dígitos (obrigatório) | 102 | - |
| Caixa | 104 | 6 dígitos (obrigatório) | 1 | emissao='4' |
| Bradesco | 237 | opcional | 06 | nosso_numero max 11 |
| Itaú | 341 | max 5 dígitos | 175 | seu_numero |
| Sicredi | 748 | max 5 dígitos (obrigatório) | 3 | posto, byte_idt |
| Sicoob | 756 | max 7 dígitos (obrigatório) | 1 | variacao='01' |

### Comprador
Pessoa física ou jurídica que adquire um imóvel.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | AutoField | Chave primária |
| tipo_pessoa | CharField(2) | PF ou PJ |
| nome | CharField(200) | Nome/Razão social |
| cpf | CharField(14) | CPF (obrigatório para PF) |
| cnpj | CharField(18) | CNPJ (para PJ) |
| rg | CharField(20) | RG |
| data_nascimento | DateField | Data de nascimento |
| estado_civil | CharField(15) | Estado civil |
| profissao | CharField(100) | Profissão |
| cep | CharField(10) | CEP |
| logradouro | CharField(255) | Logradouro |
| numero | CharField(10) | Número |
| complemento | CharField(100) | Complemento |
| bairro | CharField(100) | Bairro |
| cidade | CharField(100) | Cidade |
| estado | CharField(2) | UF |
| telefone | CharField(20) | Telefone |
| celular | CharField(20) | Celular |
| email | EmailField | E-mail |
| notificar_email | BooleanField | Receber notificações por e-mail |
| notificar_sms | BooleanField | Receber notificações por SMS |
| notificar_whatsapp | BooleanField | Receber notificações por WhatsApp |
| conjuge_nome | CharField(200) | Nome do cônjuge |
| conjuge_cpf | CharField(14) | CPF do cônjuge |

### Imovel
Representa um imóvel (lote, terreno, casa, etc.).

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | AutoField | Chave primária |
| imobiliaria | ForeignKey | Ref. para Imobiliária |
| tipo | CharField(20) | LOTE, TERRENO, CASA, etc. |
| identificacao | CharField(100) | Identificação (Quadra X, Lote Y) |
| loteamento | CharField(200) | Nome do loteamento |
| endereco | TextField | Endereço completo |
| area | DecimalField(10,2) | Área em m² |
| matricula | CharField(50) | Matrícula do imóvel |
| inscricao_municipal | CharField(50) | Inscrição municipal |
| disponivel | BooleanField | Se está disponível para venda |
| ativo | BooleanField | Status de ativo |

---

## Módulo Contratos

### Contrato
Contrato de venda de imóvel parcelado.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | AutoField | Chave primária |
| imovel | ForeignKey | Ref. para Imóvel |
| comprador | ForeignKey | Ref. para Comprador |
| imobiliaria | ForeignKey | Ref. para Imobiliária |
| numero_contrato | CharField(50) | Número único do contrato |
| data_contrato | DateField | Data de assinatura |
| data_primeiro_vencimento | DateField | Vencimento da 1ª parcela |
| valor_total | DecimalField(12,2) | Valor total do contrato |
| valor_entrada | DecimalField(12,2) | Valor de entrada |
| numero_parcelas | IntegerField | Quantidade de parcelas |
| dia_vencimento | IntegerField | Dia do mês (1-31) |
| percentual_juros_mora | DecimalField(5,2) | Juros de mora (%) |
| percentual_multa | DecimalField(5,2) | Multa (%) |
| tipo_correcao | CharField(10) | IPCA, IGPM, INCC, etc. |
| prazo_reajuste_meses | IntegerField | Intervalo de reajuste |
| data_ultimo_reajuste | DateField | Data do último reajuste |
| status | CharField(20) | ATIVO, QUITADO, CANCELADO |
| valor_financiado | DecimalField(12,2) | Calculado: valor_total - valor_entrada |
| valor_parcela_original | DecimalField(12,2) | Calculado: valor_financiado / numero_parcelas |

**Configurações de Boleto Personalizadas:**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| usar_config_boleto_imobiliaria | BooleanField | Se usa config da imobiliária |
| conta_bancaria_padrao | ForeignKey | Conta bancária preferencial |
| tipo_valor_multa | CharField(10) | PERCENTUAL ou VALOR |
| valor_multa_boleto | DecimalField(10,2) | Multa personalizada |
| tipo_valor_juros | CharField(10) | PERCENTUAL ou VALOR |
| valor_juros_boleto | DecimalField(10,4) | Juros personalizado |
| dias_carencia_boleto | IntegerField | Dias sem encargos |
| tipo_valor_desconto | CharField(10) | PERCENTUAL ou VALOR |
| valor_desconto_boleto | DecimalField(10,2) | Desconto personalizado |
| dias_desconto_boleto | IntegerField | Dias para desconto |
| instrucao_boleto_1 | CharField(255) | Instrução 1 |
| instrucao_boleto_2 | CharField(255) | Instrução 2 |
| instrucao_boleto_3 | CharField(255) | Instrução 3 |

**Métodos importantes:**

- `get_config_boleto()`: Retorna configurações de boleto (personalizadas ou da imobiliária)
- `get_conta_bancaria()`: Retorna conta bancária preferencial
- `gerar_parcelas()`: Gera todas as parcelas do contrato
- `gerar_boletos_parcelas()`: Gera boletos para parcelas pendentes

### IndiceReajuste
Índices de reajuste (IPCA, IGPM, etc.) por mês/ano.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | AutoField | Chave primária |
| tipo_indice | CharField(10) | IPCA, IGPM, INCC, etc. |
| ano | IntegerField | Ano |
| mes | IntegerField | Mês (1-12) |
| valor | DecimalField(10,4) | Valor do índice (%) |
| valor_acumulado_ano | DecimalField(10,4) | Acumulado no ano |
| valor_acumulado_12m | DecimalField(10,4) | Acumulado 12 meses |
| fonte | CharField(50) | Fonte do índice |
| data_importacao | DateTimeField | Data de importação |

---

## Módulo Financeiro

### Parcela
Parcela de um contrato com dados de boleto.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | AutoField | Chave primária |
| contrato | ForeignKey | Ref. para Contrato |
| numero_parcela | IntegerField | Número da parcela |
| data_vencimento | DateField | Data de vencimento |
| valor_original | DecimalField(12,2) | Valor original |
| valor_atual | DecimalField(12,2) | Valor com reajustes |
| valor_juros | DecimalField(12,2) | Juros calculados |
| valor_multa | DecimalField(12,2) | Multa calculada |
| valor_desconto | DecimalField(12,2) | Desconto aplicado |
| valor_pago | DecimalField(12,2) | Valor efetivamente pago |
| data_pagamento | DateField | Data do pagamento |
| pago | BooleanField | Se está paga |

**Dados do Boleto:**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| conta_bancaria | ForeignKey | Conta usada para o boleto |
| nosso_numero | CharField(30) | Nosso número do boleto |
| numero_documento | CharField(30) | Número do documento |
| codigo_barras | CharField(50) | Código de barras |
| linha_digitavel | CharField(60) | Linha digitável |
| boleto_pdf | FileField | Arquivo PDF do boleto |
| boleto_url | URLField | URL externa do boleto |
| status_boleto | CharField(15) | NAO_GERADO, GERADO, REGISTRADO, etc. |
| data_geracao_boleto | DateTimeField | Data de geração |
| data_registro_boleto | DateTimeField | Data de registro no banco |
| data_pagamento_boleto | DateTimeField | Data de pagamento confirmado |
| valor_boleto | DecimalField(12,2) | Valor do boleto |
| pix_copia_cola | TextField | Código PIX copia e cola |
| pix_qrcode | TextField | QR Code PIX (base64) |

**Status do Boleto:**

| Status | Descrição |
|--------|-----------|
| NAO_GERADO | Boleto não foi gerado |
| GERADO | Boleto gerado localmente |
| REGISTRADO | Boleto registrado no banco |
| PAGO | Boleto pago |
| VENCIDO | Boleto vencido sem pagamento |
| CANCELADO | Boleto cancelado |
| REJEITADO | Boleto rejeitado pelo banco |

---

## Módulo Notificações

### ConfiguracaoEmail
Configuração de servidor SMTP para envio de e-mails.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | AutoField | Chave primária |
| imobiliaria | ForeignKey | Ref. para Imobiliária |
| nome | CharField(100) | Nome da configuração |
| servidor_smtp | CharField(255) | Servidor SMTP |
| porta | IntegerField | Porta (25, 465, 587) |
| usuario | CharField(255) | Usuário SMTP |
| senha | CharField(255) | Senha (criptografada) |
| usar_tls | BooleanField | Usar TLS |
| usar_ssl | BooleanField | Usar SSL |
| email_remetente | EmailField | E-mail de origem |
| nome_remetente | CharField(100) | Nome exibido |
| ativo | BooleanField | Se está ativo |

### TemplateNotificacao
Templates de e-mail para notificações automáticas.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | AutoField | Chave primária |
| imobiliaria | ForeignKey | Ref. para Imobiliária |
| tipo | CharField(50) | BOLETO_CRIADO, VENCIMENTO, etc. |
| nome | CharField(100) | Nome do template |
| assunto | CharField(255) | Assunto do e-mail |
| corpo_html | TextField | Corpo HTML com variáveis |
| corpo_texto | TextField | Corpo texto puro |
| ativo | BooleanField | Se está ativo |

**Variáveis disponíveis nos templates:**

- `{{ comprador_nome }}` - Nome do comprador
- `{{ numero_contrato }}` - Número do contrato
- `{{ numero_parcela }}` - Número da parcela
- `{{ valor_parcela }}` - Valor da parcela
- `{{ data_vencimento }}` - Data de vencimento
- `{{ linha_digitavel }}` - Linha digitável do boleto
- `{{ codigo_barras }}` - Código de barras
- `{{ imovel }}` - Identificação do imóvel

### HistoricoNotificacao
Histórico de notificações enviadas.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | AutoField | Chave primária |
| parcela | ForeignKey | Ref. para Parcela |
| tipo | CharField(50) | Tipo da notificação |
| destinatario | EmailField | E-mail do destinatário |
| assunto | CharField(255) | Assunto enviado |
| enviado_em | DateTimeField | Data/hora do envio |
| sucesso | BooleanField | Se foi enviado com sucesso |
| erro | TextField | Mensagem de erro (se houver) |

---

## Relacionamentos

```
Contabilidade
    └── Imobiliária (1:N)
            ├── ContaBancaria (1:N)
            ├── Imovel (1:N)
            │       └── Contrato (1:N)
            │               ├── Parcela (1:N)
            │               └── conta_bancaria_padrao (N:1)
            ├── ConfiguracaoEmail (1:N)
            └── TemplateNotificacao (1:N)

Comprador
    └── Contrato (1:N)
            └── Parcela (1:N)
                    └── HistoricoNotificacao (1:N)
```

---

## Configurações de Boleto

### Hierarquia de Configurações

1. **Contrato com configuração personalizada** (`usar_config_boleto_imobiliaria=False`)
   - Usa campos do próprio contrato
   - Permite diferentes configurações por contrato

2. **Contrato com configuração da Imobiliária** (`usar_config_boleto_imobiliaria=True`)
   - Usa campos padrão da imobiliária
   - Configuração centralizada

### Fluxo de Geração de Boleto

```
1. Parcela.gerar_boleto()
   │
   ├── 2. Obter conta bancária
   │       ├── Contrato.conta_bancaria_padrao (se definida)
   │       └── Imobiliária.contas_bancarias.filter(principal=True)
   │
   ├── 3. Obter configurações
   │       └── Contrato.get_config_boleto()
   │               ├── Se usar_config_boleto_imobiliaria: usa Imobiliária
   │               └── Senão: usa campos do Contrato
   │
   ├── 4. BoletoService._montar_dados_boleto()
   │       ├── Dados do cedente (imobiliária)
   │       ├── Dados do sacado (comprador)
   │       ├── Dados bancários (conta)
   │       ├── Multa, juros, desconto (config_boleto)
   │       └── Instruções (config_boleto)
   │
   ├── 5. API BRCobranca
   │       ├── /api/boleto/validate - Validação
   │       ├── /api/boleto - Geração PDF
   │       └── /api/boleto/nosso_numero - Nosso número formatado
   │
   └── 6. Salvar dados na Parcela
           ├── nosso_numero
           ├── codigo_barras
           ├── linha_digitavel
           ├── boleto_pdf
           └── status_boleto
```

---

## API BRCobranca

### Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | /api/boleto | Gera boleto individual (PDF) |
| GET | /api/boleto/validate | Valida dados do boleto |
| GET | /api/boleto/nosso_numero | Obtém nosso número formatado |
| POST | /api/boleto/multi | Gera múltiplos boletos |
| POST | /api/remessa | Gera arquivo CNAB |
| POST | /api/retorno | Processa arquivo de retorno |

### Parâmetros

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| bank | String | Nome do banco (itau, bradesco, etc.) |
| type | String | Formato de saída (pdf, jpg, png) |
| data | JSON | Dados do boleto em formato JSON |

### Exemplo de dados do boleto

```json
{
  "cedente": "Imobiliária LTDA",
  "documento_cedente": "12345678000100",
  "agencia": "1234",
  "conta_corrente": "12345",
  "convenio": "1234567",
  "carteira": "18",
  "nosso_numero": "1",
  "documento_numero": "CTR-2025-0001/001",
  "data_documento": "2025/11/23",
  "data_vencimento": "2025/12/23",
  "valor": 1500.00,
  "sacado": "João da Silva",
  "sacado_documento": "12345678909",
  "sacado_endereco": "Rua Principal, 100",
  "instrucao1": "Pagável em qualquer banco até o vencimento"
}
```

---

*Documentação gerada automaticamente - Sistema Gestão de Contratos v1.0*
