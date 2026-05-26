# Estrutura de Dados — Gestão de Contratos

**Desenvolvedor:** Maxwell da Silva Oliveira (maxwbh@gmail.com) — M&S do Brasil LTDA  
**Última atualização:** 2026-05-26  
**Status:** ✅ Revalidado contra os modelos Django (`core`, `contratos`, `financeiro`, `notificacoes`, `portal_comprador`)

---

## Índice

1. [Módulo Core](#1-módulo-core)
2. [Módulo Contratos](#2-módulo-contratos)
3. [Módulo Financeiro](#3-módulo-financeiro)
4. [Módulo Notificações](#4-módulo-notificações)
5. [Módulo Portal do Comprador](#5-módulo-portal-do-comprador)
6. [Diagrama de Relacionamentos](#6-diagrama-de-relacionamentos)
7. [Decisões de Design](#7-decisões-de-design)

---

## 1. Módulo Core

`core/models.py` — Entidades fundamentais do sistema.

---

### 1.1 TimeStampedModel *(abstrato)*

Base para todos os modelos que precisam de auditoria de criação/atualização.

| Campo | Tipo | Descrição |
|---|---|---|
| `criado_em` | DateTimeField (auto_now_add) | Data/hora de criação |
| `atualizado_em` | DateTimeField (auto_now) | Data/hora da última atualização |

---

### 1.2 Contabilidade

Empresa de contabilidade que gerencia as imobiliárias do sistema. Nível mais alto da hierarquia.

| Campo | Tipo | Regras |
|---|---|---|
| `nome` | CharField(200) | Obrigatório |
| `razao_social` | CharField(200) | Obrigatório |
| `cnpj` | CharField(20) | Único, opcional. Suporta CNPJ alfanumérico 2026 |
| `endereco` | TextField | Endereço completo |
| `telefone` | CharField(20) | — |
| `email` | EmailField | Validado |
| `responsavel` | CharField(200) | Nome do responsável |
| `ativo` | BooleanField | default=True |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

**Índices:** `ordering=['nome']`

---

### 1.3 Imobiliaria

Beneficiário dos contratos (PJ — Empresa/Imobiliária, ou PF — Vendedor Pessoa Física). Pertence a uma `Contabilidade`.

| Campo | Tipo | Regras |
|---|---|---|
| `contabilidade` | FK(Contabilidade, PROTECT) | Obrigatório |
| `tipo_pessoa` | CharField(2) | `PJ` ou `PF`, default=`PJ` |
| `nome` | CharField(200) | Razão Social ou Nome Completo |
| `razao_social` | CharField(200, blank) | Razão social / Nome fantasia (opcional PF) |
| `cnpj` | CharField(20) | Único, null/blank. Obrigatório para PJ. Alfanumérico 2026 |
| `cpf` | CharField(14) | null/blank. Obrigatório para PF |
| **Endereço estruturado** | | |
| `cep` | CharField(9, blank) | Formato: 99999-999 |
| `logradouro` | CharField(200, blank) | — |
| `numero` | CharField(10, blank) | — |
| `complemento` | CharField(100, blank) | — |
| `bairro` | CharField(100, blank) | — |
| `cidade` | CharField(100, blank) | — |
| `estado` | CharField(2, blank) | UF (choices 27 estados + DF) |
| `logo` | ImageField | upload_to='imobiliarias/logos/', null/blank |
| `endereco` | TextField(blank) | Campo legado; preferir campos acima |
| **Contato** | | |
| `telefone` | CharField(20) | — |
| `email` | EmailField | — |
| `responsavel_financeiro` | CharField(200) | — |
| **Dados bancários rápidos** *(legado)* | | Preferir ContaBancaria |
| `banco` | CharField(100, blank) | — |
| `agencia` | CharField(20, blank) | — |
| `conta` | CharField(20, blank) | — |
| `pix` | CharField(100, blank) | Chave PIX |
| **Configurações de Boleto (padrão)** | | Usadas quando `Contrato.usar_config_boleto_imobiliaria=True` |
| `tipo_valor_multa` | CharField(10) | choices: PERCENTUAL / REAL |
| `percentual_multa_padrao` | DecimalField(10,2) | default=0 |
| `tipo_valor_juros` | CharField(10) | choices: PERCENTUAL / REAL |
| `percentual_juros_padrao` | DecimalField(10,4) | 0,0333 = 1% a.m. |
| `dias_para_encargos_padrao` | IntegerField | Dias de carência; default=0 |
| `boleto_sem_valor` | BooleanField | Permite emissão sem valor; default=False |
| `parcela_no_documento` | BooleanField | Incluir nº parcela no campo Documento; default=False |
| `campo_desconto_abatimento_pdf` | BooleanField | Mostrar desconto no PDF; default=False |
| `tipo_valor_desconto` | CharField(10) | Desconto 1 |
| `percentual_desconto_padrao` | DecimalField(10,2) | default=0 |
| `dias_para_desconto_padrao` | IntegerField | default=0 |
| `tipo_valor_desconto2` | CharField(10) | Desconto 2 |
| `desconto2_padrao` | DecimalField(10,2) | default=0 |
| `dias_para_desconto2_padrao` | IntegerField | default=0 |
| `tipo_valor_desconto3` | CharField(10) | Desconto 3 |
| `desconto3_padrao` | DecimalField(10,2) | default=0 |
| `dias_para_desconto3_padrao` | IntegerField | default=0 |
| `instrucao_padrao` | CharField(255, blank) | Linha de instrução ao caixa |
| `tipo_titulo` | CharField(5) | choices: TipoTitulo (RC padrão) |
| `aceite` | BooleanField | default=False |
| `ativo` | BooleanField | default=True |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

**Nota:** `nome_fantasia` é uma `@property` que retorna `razao_social` (compatibilidade retroativa).  
**Validação `clean()`:** PJ exige CNPJ; PF exige CPF.

---

### 1.4 ContaBancaria

Conta bancária de uma imobiliária para emissão de boletos e geração de arquivos CNAB.

| Campo | Tipo | Regras |
|---|---|---|
| `imobiliaria` | FK(Imobiliaria, CASCADE) | — |
| `banco` | CharField(3) | choices: BancoBrasil (lista extensa) |
| `descricao` | CharField(150) | Ex: "Conta Principal", "Conta Boletos" |
| `principal` | BooleanField | Conta padrão da imobiliária; `save()` desativa outras |
| `agencia` | CharField(10) | Com dígito |
| `conta` | CharField(20) | Com dígito |
| **Dados para Boleto** | | |
| `convenio` | CharField(20, blank) | Código do cliente/convênio |
| `carteira` | CharField(5, blank) | Carteira de cobrança |
| `nosso_numero_atual` | IntegerField | Sequencial atual do nosso número |
| `modalidade` | CharField(5, blank) | — |
| **PIX** | | |
| `tipo_pix` | CharField(20, blank) | choices: CPF / CNPJ / EMAIL / TELEFONE / ALEATORIA |
| `chave_pix` | CharField(100, blank) | — |
| **Configuração de Cobrança** | | |
| `cobranca_registrada` | BooleanField | default=True |
| `prazo_baixa` | IntegerField | Dias para baixa após vencimento |
| `prazo_protesto` | IntegerField | Dias para protesto (0 = não protestar) |
| **Campos específicos por banco** | | |
| `posto` | CharField(2, blank) | Sicredi: obrigatório |
| `byte_idt` | CharField(1, blank) | Sicredi: obrigatório (geralmente "2") |
| `emissao` | CharField(1, blank) | Caixa Econômica: obrigatório (geralmente "4") |
| `codigo_beneficiario` | CharField(20, blank) | Caixa Econômica: obrigatório |
| **CNAB** | | |
| `layout_cnab` | CharField(10) | choices: CNAB_240 / CNAB_400 / CNAB_444 |
| `numero_remessa_cnab_atual` | IntegerField | Sequencial de remessa |
| `ativo` | BooleanField | default=True |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

**Índices:** `ordering=['-principal', 'banco', 'descricao']`

---

### 1.5 Imovel

Imóvel associado a uma imobiliária. Pode ter vértices de polígono e overlay de planta baixa.

| Campo | Tipo | Regras |
|---|---|---|
| `imobiliaria` | FK(Imobiliaria, PROTECT) | — |
| `tipo` | CharField(20) | choices: LOTE / TERRENO / CASA / APARTAMENTO / COMERCIAL |
| `identificacao` | CharField(100) | Ex: "Quadra A Lote 13", "Apt 301" |
| `loteamento` | CharField(200, blank) | Nome do loteamento/empreendimento |
| **Endereço estruturado** | | |
| `cep` | CharField(9, blank) | — |
| `logradouro` | CharField(200, blank) | — |
| `numero` | CharField(10, blank) | — |
| `complemento` | CharField(100, blank) | — |
| `bairro` | CharField(100, blank) | — |
| `cidade` | CharField(100, blank) | — |
| `estado` | CharField(2, blank) | UF |
| `endereco` | TextField(blank) | Campo legado |
| **Georreferenciamento** | | |
| `latitude` | DecimalField(10,7, null, blank) | Ex: -23.5505199 |
| `longitude` | DecimalField(10,7, null, blank) | Ex: -46.6333094 |
| **Dados do Imóvel** | | |
| `area` | DecimalField(10,2) | Área em m² |
| `valor` | DecimalField(12,2, null, blank) | Valor de venda |
| **Documentação** | | |
| `matricula` | CharField(100, blank) | Número de matrícula |
| `inscricao_municipal` | CharField(100, blank) | — |
| `observacoes` | TextField(blank) | — |
| `disponivel` | BooleanField | default=True |
| `ativo` | BooleanField | default=True |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

**Índices:** `[disponivel, ativo]`, `[loteamento]`  
**Ordering:** `['loteamento', 'identificacao']`

---

### 1.6 VerticePoligono

Vértice de polígono georreferenciado que define o contorno de um imóvel no mapa.

| Campo | Tipo | Regras |
|---|---|---|
| `imovel` | FK(Imovel, CASCADE) | related_name='vertices' |
| `ordem` | PositiveSmallIntegerField | Ordem do vértice |
| `latitude` | DecimalField(10,7) | — |
| `longitude` | DecimalField(10,7) | — |

**Constraints:** `unique_together=[imovel, ordem]`  
**Ordering:** `['imovel', 'ordem']`

---

### 1.7 LoteamentoOverlay

Planta baixa (imagem) georreferenciada para exibição como overlay no mapa. Os 4 campos lat/lng definem o retângulo SW–NE.

| Campo | Tipo | Regras |
|---|---|---|
| `nome_loteamento` | CharField(200, db_index) | Deve corresponder ao campo `loteamento` dos imóveis |
| `imagem` | ImageField | upload_to='loteamento/overlays/' (PNG/JPG) |
| `lat_sw` | DecimalField(10,7) | Latitude do canto Sudoeste |
| `lng_sw` | DecimalField(10,7) | Longitude do canto Sudoeste |
| `lat_ne` | DecimalField(10,7) | Latitude do canto Nordeste |
| `lng_ne` | DecimalField(10,7) | Longitude do canto Nordeste |
| `opacidade` | FloatField | 0–1, default=0.7 |
| `ativo` | BooleanField | default=True |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

---

### 1.8 Comprador

Comprador do imóvel (Pessoa Física ou Jurídica).

| Campo | Tipo | Regras |
|---|---|---|
| `tipo_pessoa` | CharField(2) | choices: PF / PJ, default=PF |
| `nome` | CharField(200) | Nome Completo (PF) ou Razão Social (PJ) |
| **Dados PF** | | |
| `cpf` | CharField(14, null, blank) | Obrigatório para PF. Formato: XXX.XXX.XXX-XX |
| `rg` | CharField(20, blank) | — |
| `data_nascimento` | DateField(null, blank) | — |
| `estado_civil` | CharField(50, blank) | choices: SOLTEIRO / CASADO / DIVORCIADO / VIUVO / UNIAO_ESTAVEL |
| `profissao` | CharField(100, blank) | — |
| **Dados PJ** | | |
| `cnpj` | CharField(20, null, blank) | Obrigatório para PJ. Alfanumérico 2026 |
| `nome_fantasia` | CharField(200, blank) | — |
| `inscricao_estadual` | CharField(20, blank) | — |
| `inscricao_municipal` | CharField(20, blank) | — |
| `responsavel_legal` | CharField(200, blank) | Nome do representante legal |
| `responsavel_cpf` | CharField(14, blank) | CPF do representante |
| **Endereço estruturado** | | |
| `cep` | CharField(9, blank) | — |
| `logradouro` | CharField(200, blank) | — |
| `numero` | CharField(10, blank) | — |
| `complemento` | CharField(100, blank) | — |
| `bairro` | CharField(100, blank) | — |
| `cidade` | CharField(100, blank) | — |
| `estado` | CharField(2, blank) | UF |
| `endereco` | TextField(blank) | Campo legado |
| **Contato** | | |
| `telefone` | CharField(20, blank) | — |
| `celular` | CharField(20, blank) | — |
| `email` | EmailField(blank) | — |
| **Preferências de Notificação** | | |
| `notificar_email` | BooleanField | default=True |
| `notificar_sms` | BooleanField | default=False |
| `notificar_whatsapp` | BooleanField | default=False |
| **Cônjuge** | | |
| `conjuge_nome` | CharField(200, blank) | — |
| `conjuge_cpf` | CharField(14, blank) | — |
| `conjuge_rg` | CharField(20, blank) | — |
| `observacoes` | TextField(blank) | — |
| `ativo` | BooleanField | default=True |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

**Índices:** `[tipo_pessoa]`, `[cpf]`, `[cnpj]`  
**Validação `clean()`:** PF exige CPF; PJ exige CNPJ.

---

### 1.9 AcessoUsuario

Controla quais usuários Django (`auth.User`) têm acesso a quais imobiliárias. Um usuário pode ter múltiplos acessos.

| Campo | Tipo | Regras |
|---|---|---|
| `usuario` | FK(auth.User, CASCADE) | — |
| `contabilidade` | FK(Contabilidade, CASCADE) | — |
| `imobiliaria` | FK(Imobiliaria, CASCADE) | Deve pertencer à contabilidade acima |
| `pode_editar` | BooleanField | default=True — permite criar/editar |
| `pode_excluir` | BooleanField | default=False — permite excluir |
| `ativo` | BooleanField | default=True |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

**Constraints:** `unique_together=[usuario, contabilidade, imobiliaria]`  
**Regras de acesso:** `staff=True` ou `superuser=True` → acesso total a todas as entidades (sem necessidade de AcessoUsuario).

---

### 1.10 ParametroSistema

Tabela de configurações globais do sistema (equivalente a variáveis de ambiente persistidas em banco).

| Campo | Tipo | Regras |
|---|---|---|
| `chave` | CharField(100, unique) | Ex: `EMAIL_HOST`, `BOLETO_TOKEN_DIAS_VALIDADE` |
| `valor` | TextField(blank) | Valor em texto |
| `tipo` | CharField(10) | choices: str / int / bool / secret |
| `grupo` | CharField(20) | choices: email / twilio / imap / teste / notificacao / tarefa / brcobranca / portal / aplicacao / bcb |
| `descricao` | CharField(300, blank) | Descrição humana da chave |
| `atualizado_em` | DateTimeField(auto_now) | — |
| `modificado_manualmente` | BooleanField | Protege de sobrescrita pelo sync do .env |

**Nota:** `get_valor_tipado()` retorna o valor convertido para int, bool ou str conforme `tipo`.

---

### 1.11 AcessoNegado

Registra tentativas de acesso negado (403/404) para detecção de varredura de IDs (AntiEnumeracaoMiddleware).

| Campo | Tipo | Regras |
|---|---|---|
| `ip` | GenericIPAddressField | — |
| `usuario` | FK(auth.User, null, blank, SET_NULL) | Usuário logado (ou null) |
| `url` | CharField(500) | URL acessada |
| `status_code` | PositiveSmallIntegerField | 403, 404, etc. |
| `timestamp` | DateTimeField(auto_now_add) | — |

**Índices:** `[ip, timestamp]`, `[timestamp]`

---

## 2. Módulo Contratos

`contratos/models.py` — Contratos de venda, índices de reajuste e entidades auxiliares.

---

### 2.1 Choices Globais

| Enum | Valores |
|---|---|
| `TipoCorrecao` | IPCA, IGPM, INCC, IGPDI, INPC, TR, SELIC, **FIXO** |
| `StatusContrato` | ATIVO, QUITADO, CANCELADO, **SUSPENSO** |
| `TipoAmortizacao` | **PRICE** (PMT constante), **SAC** (amortização constante) |
| `TipoPrestacao` | NORMAL, INTERMEDIARIA, ENTRADA |

---

### 2.2 IndiceReajuste

Armazena as variações mensais dos índices de correção (IPCA, IGP-M, INCC, etc.).

| Campo | Tipo | Regras |
|---|---|---|
| `tipo_indice` | CharField(10) | choices: IPCA / IGPM / INCC / IGPDI / INPC / TR / SELIC |
| `ano` | PositiveIntegerField | 1990–2100 |
| `mes` | PositiveIntegerField | 1–12 |
| `valor` | DecimalField(8,4) | Variação percentual do mês |
| `valor_acumulado_ano` | DecimalField(10,4, null) | Acumulado desde janeiro |
| `valor_acumulado_12m` | DecimalField(10,4, null) | Acumulado 12 meses |
| `numero_indice` | DecimalField(12,4, null) | Número-índice IBGE/FGV — prioridade no cálculo acumulado |
| `fonte` | CharField(100, blank) | Ex: "IBGE", "BCB", "FGV" |
| `data_importacao` | DateTimeField(null) | Quando foi importado automaticamente |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

**Constraints:** `unique_together=[tipo_indice, ano, mes]`  
**Método:** `get_acumulado_periodo()` — usa `numero_indice` (Método 1, preciso) ou produto de variações mensais (Método 2, fallback).

---

### 2.3 Contrato

Contrato de venda de imóvel. Entidade central do sistema.

| Campo | Tipo | Regras |
|---|---|---|
| **Relações** | | |
| `imovel` | FK(Imovel, PROTECT) | O imóvel deve pertencer à mesma imobiliária |
| `comprador` | FK(Comprador, PROTECT) | Um comprador pode ter contratos em múltiplas imobiliárias |
| `imobiliaria` | FK(Imobiliaria, PROTECT) | Beneficiário / cedente |
| **Identificação** | | |
| `numero_contrato` | CharField(50, unique) | — |
| `data_contrato` | DateField | Padrão: hoje |
| `data_primeiro_vencimento` | DateField | — |
| **Valores** | | |
| `valor_total` | DecimalField(12,2) | > 0 |
| `valor_entrada` | DecimalField(12,2) | default=0, < valor_total |
| `valor_financiado` | DecimalField(12,2, editable=False) | Calculado: total − entrada |
| `valor_parcela_original` | DecimalField(12,2, editable=False) | Calculado: financiado ÷ n_parcelas |
| **Configuração de Parcelas** | | |
| `numero_parcelas` | PositiveIntegerField | 1–360 (30 anos) |
| `dia_vencimento` | PositiveIntegerField | 1–31 |
| `quantidade_intermediarias` | PositiveIntegerField | 0–30, default=0 |
| **Controle de Ciclo** | | |
| `ciclo_reajuste_atual` | PositiveIntegerField | default=1 |
| `ultimo_mes_boleto_gerado` | PositiveIntegerField | default=0 |
| `bloqueio_boleto_reajuste` | BooleanField | default=False — trava geração até aplicar reajuste |
| **Juros e Multa Contratuais** | | |
| `percentual_juros_mora` | DecimalField(5,2) | Máx. 2% a.m.; default=1,00 |
| `percentual_multa` | DecimalField(5,2) | Máx. 2%; default=2,00 |
| **Correção Monetária** | | |
| `tipo_correcao` | CharField(10) | choices: TipoCorrecao |
| `prazo_reajuste_meses` | PositiveIntegerField | 1–120, default=12 |
| `data_ultimo_reajuste` | DateField(null) | — |
| `reajuste_piso` | DecimalField(8,4, null) | Percentual mínimo de reajuste |
| `reajuste_teto` | DecimalField(8,4, null) | Percentual máximo de reajuste |
| `spread_reajuste` | DecimalField(8,4, null) | Pontos percentuais extras (IPCA + spread) |
| `tipo_correcao_fallback` | CharField(10, blank) | Índice substituto se o principal for extinto |
| **Cláusulas Contratuais** | | |
| `percentual_fruicao` | DecimalField(6,4) | % a.m. de fruição em rescisão; default=0.5000 |
| `percentual_multa_rescisao_penal` | DecimalField(6,4) | Cláusula penal; default=10.0000 |
| `percentual_multa_rescisao_adm` | DecimalField(6,4) | Despesas adm.; default=12.0000 |
| `percentual_cessao` | DecimalField(6,4) | Taxa de cessão de direitos; default=3.0000 |
| **Amortização** | | |
| `tipo_amortizacao` | CharField(10) | choices: PRICE / SAC; default=PRICE |
| `intermediarias_reduzem_pmt` | BooleanField | default=False |
| `intermediarias_reajustadas` | BooleanField | default=True |
| **Status** | | |
| `status` | CharField(20) | choices: ATIVO / QUITADO / CANCELADO / SUSPENSO |
| **Configuração de Boleto do Contrato** | | |
| `usar_config_boleto_imobiliaria` | BooleanField | Se True, herda da imobiliária; default=True |
| `conta_bancaria_padrao` | FK(ContaBancaria, null, SET_NULL) | Conta para boletos deste contrato |
| `tipo_valor_multa` | CharField(10) | Multa personalizada |
| `valor_multa_boleto` | DecimalField(10,2) | — |
| `tipo_valor_juros` | CharField(10) | Juros personalizado |
| `valor_juros_boleto` | DecimalField(10,4) | — |
| `dias_carencia_boleto` | IntegerField | Dias sem encargos |
| `tipo_valor_desconto` | CharField(10) | — |
| `valor_desconto_boleto` | DecimalField(10,2) | — |
| `dias_desconto_boleto` | IntegerField | — |
| `instrucao_boleto_1` | CharField(255, blank) | Linha 1 |
| `instrucao_boleto_2` | CharField(255, blank) | Linha 2 |
| `instrucao_boleto_3` | CharField(255, blank) | Linha 3 |
| `observacoes` | TextField(blank) | — |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

**Índices:** `[numero_contrato]`, `[status]`, `[data_contrato]`

---

### 2.4 TabelaJurosContrato

Tabela de juros compostos escalantes por ciclo. Permite modelar contratos com taxa progressiva (ex: Ano 1: 0%, Ano 2: 0,60% a.m., etc.).

| Campo | Tipo | Regras |
|---|---|---|
| `contrato` | FK(Contrato, CASCADE) | related_name='tabela_juros' |
| `ciclo_inicio` | PositiveIntegerField | >= 1 |
| `ciclo_fim` | PositiveIntegerField(null) | >= ciclo_inicio; null = "este ciclo em diante" |
| `juros_mensal` | DecimalField(8,4) | Ex: 0.6000 = 0,60% a.m. |
| `observacoes` | CharField(200, blank) | Ex: "Conforme cláusula 8.2" |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

**Validação:** sem sobreposição de faixas para o mesmo contrato.

---

### 2.5 PrestacaoIntermediaria

Prestações intermediárias — parcelas especiais com valor diferenciado que vencem em meses específicos.

| Campo | Tipo | Regras |
|---|---|---|
| `contrato` | FK(Contrato, CASCADE) | related_name='intermediarias' |
| `numero_sequencial` | PositiveIntegerField | 1–30 |
| `mes_vencimento` | PositiveIntegerField | 1–360 (mês relativo ao início) |
| `valor` | DecimalField(12,2) | > 0 |
| `paga` | BooleanField | default=False |
| `data_pagamento` | DateField(null) | — |
| `valor_pago` | DecimalField(12,2, null) | — |
| `parcela_vinculada` | OneToOneField(financeiro.Parcela, null, SET_NULL) | Parcela gerada para esta intermediária |
| `valor_reajustado` | DecimalField(12,2, null) | Valor após reajustes |
| `observacoes` | TextField(blank) | — |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

**Constraints:** `unique_together=[contrato, numero_sequencial]`  
**Propriedades:** `valor_atual` (reajustado ou original), `data_vencimento` (calculado), `ciclo_reajuste`.

---

### 2.6 HistoricoReajusteIntermediaria

Auditoria de reajustes aplicados às prestações intermediárias.

| Campo | Tipo | Regras |
|---|---|---|
| `intermediaria` | FK(PrestacaoIntermediaria, CASCADE) | related_name='historico_reajustes' |
| `data_reajuste` | DateTimeField(auto_now_add) | — |
| `percentual` | DecimalField(8,4) | % aplicado |
| `valor_anterior` | DecimalField(12,2) | — |
| `valor_novo` | DecimalField(12,2) | — |

---

### 2.7 MinutaContrato

Versionamento de minutas do contrato para rastreabilidade legal.

| Campo | Tipo | Regras |
|---|---|---|
| `contrato` | FK(Contrato, CASCADE) | related_name='minutas' |
| `versao` | CharField(20) | Ex: "v1", "2024-01" |
| `titulo` | CharField(200) | — |
| `conteudo` | TextField | Texto completo ou descrição das alterações |
| `ativa` | BooleanField | Somente a versão ativa é a minuta vigente |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

**Constraints:** `unique_together=[contrato, versao]`  
**`save()`:** Ao marcar `ativa=True`, desativa automaticamente as demais versões (transação atômica com `SELECT FOR UPDATE`).

---

### 2.8 ContratoImportacao

Controla o ciclo de importação de contratos via IA (upload → extração → revisão → criação).

| Campo | Tipo | Regras |
|---|---|---|
| `arquivo_bytes` | BinaryField(null) | PDF do contrato em banco de dados |
| `arquivo_nome` | CharField(255, blank) | Nome original do arquivo |
| `status` | CharField(20) | choices: PENDENTE / EXTRAINDO / REVISAO / CONCLUIDO / ERRO |
| `dados_extraidos` | JSONField(null) | Dados extraídos pela IA |
| `erros_extracao` | TextField(blank) | Mensagens de erro |
| `contrato_criado` | OneToOneField(Contrato, null, SET_NULL) | Contrato criado a partir desta importação |
| `criado_por` | FK(auth.User, null, SET_NULL) | — |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

---

## 3. Módulo Financeiro

`financeiro/models.py` — Parcelas, reajustes, pagamentos, CNAB e PIX.

---

### 3.1 Choices Globais

| Enum | Valores |
|---|---|
| `StatusBoleto` | NAO_GERADO, GERADO, REGISTRADO, PAGO, VENCIDO, CANCELADO, PROTESTADO, BAIXADO |
| `TipoParcela` | NORMAL, INTERMEDIARIA, ENTRADA |

---

### 3.2 Parcela

Parcela mensal de um contrato. Ponto central do fluxo financeiro.

| Campo | Tipo | Regras |
|---|---|---|
| `contrato` | FK(contratos.Contrato, CASCADE) | — |
| `numero_parcela` | PositiveIntegerField | — |
| `data_vencimento` | DateField | — |
| `tipo_parcela` | CharField(15) | choices: TipoParcela; default=NORMAL |
| `ciclo_reajuste` | PositiveIntegerField | Ciclo de reajuste (1 = meses 1–12); default=1 |
| **Valores** | | |
| `valor_original` | DecimalField(12,2) | Valor inicial sem reajustes |
| `valor_atual` | DecimalField(12,2) | Valor após reajustes |
| `valor_juros` | DecimalField(12,2) | Juros por atraso; default=0 |
| `valor_multa` | DecimalField(12,2) | Multa por atraso; default=0 |
| `valor_desconto` | DecimalField(12,2) | Desconto concedido; default=0 |
| `amortizacao` | DecimalField(12,2, null) | Amortização de principal (Price/SAC) |
| `juros_embutido` | DecimalField(12,2, null) | Juros de financiamento embutidos (Price/SAC) |
| **Pagamento** | | |
| `pago` | BooleanField | default=False |
| `data_pagamento` | DateField(null) | — |
| `valor_pago` | DecimalField(12,2, null) | — |
| `observacoes` | TextField(blank) | — |
| **Boleto Bancário** | | |
| `conta_bancaria` | FK(ContaBancaria, null, SET_NULL) | Conta usada para gerar o boleto |
| `nosso_numero` | CharField(30, blank) | Sequencial bruto (conciliação CNAB) |
| `nosso_numero_formatado` | CharField(30, blank) | Completo com DV (conciliação OFX) |
| `nosso_numero_dv` | CharField(2, blank) | Dígito verificador isolado |
| `numero_documento` | CharField(25, blank) | — |
| `codigo_barras` | CharField(50, blank) | — |
| `linha_digitavel` | CharField(60, blank) | — |
| `boleto_pdf` | FileField | upload_to='boletos/%Y/%m/' (null/blank) |
| `boleto_pdf_db` | BinaryField(null, editable=False) | Cópia em BD — persiste em storage efêmero (Render) |
| `boleto_url` | URLField(500, blank) | URL externa |
| `status_boleto` | CharField(15) | choices: StatusBoleto; default=NAO_GERADO |
| `data_geracao_boleto` | DateTimeField(null) | — |
| `data_registro_boleto` | DateTimeField(null) | — |
| `data_pagamento_boleto` | DateTimeField(null) | — |
| `valor_boleto` | DecimalField(12,2, null) | Valor nominal do boleto gerado |
| `valor_pago_boleto` | DecimalField(12,2, null) | Valor efetivo pago via boleto |
| `banco_pagador` | CharField(10, blank) | Banco onde foi pago |
| `agencia_pagadora` | CharField(10, blank) | — |
| `motivo_rejeicao` | CharField(255, blank) | Motivo de rejeição/baixa |
| **Link Público** | | |
| `token_publico` | UUIDField(unique, default=uuid4) | Acesso sem login — `/b/<token>/` |
| `token_expira_em` | DateTimeField(null) | null = sem expiração |
| **PIX Híbrido** | | |
| `pix_copia_cola` | TextField(blank) | Código PIX copia e cola |
| `pix_qrcode` | TextField(blank) | QR Code PIX em base64 |
| `pix_txid` | CharField(35, blank, db_index) | txid para reconciliação webhook (BCB ate 35 chars) |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

**Constraints:**
- `unique_together=[contrato, numero_parcela]`
- `UniqueConstraint([conta_bancaria, nosso_numero] WHERE nosso_numero != '')` — evita baixa duplicada

**Índices compostos:** `[pago, data_vencimento]`, `[contrato, pago, data_vencimento]`

---

### 3.3 Reajuste

Registro de reajuste aplicado nas parcelas. Suporta 3 modos: Simples, Tabela Price e SAC.

| Campo | Tipo | Regras |
|---|---|---|
| `contrato` | FK(contratos.Contrato, CASCADE) | — |
| `data_reajuste` | DateField | — |
| `indice_tipo` | CharField(10) | Ex: IPCA, IGPM |
| `percentual` | DecimalField(8,4) | Percentual líquido aplicado |
| `parcela_inicial` | PositiveIntegerField | Primeira parcela afetada |
| `parcela_final` | PositiveIntegerField | Última parcela afetada |
| `ciclo` | PositiveIntegerField | Ciclo de reajuste (2 = após 12 meses...); default=1 |
| `data_limite_boleto` | DateField(null) | — |
| `periodo_referencia_inicio` | DateField(null) | Início do período cujo acumulado foi usado |
| `periodo_referencia_fim` | DateField(null) | Fim do período de referência |
| `percentual_bruto` | DecimalField(8,4, null) | Índice calculado antes de desconto/spread |
| `desconto_percentual` | DecimalField(8,4, null) | Redução em p.p. sobre o índice |
| `desconto_valor` | DecimalField(12,2, null) | Desconto fixo em R$ por parcela |
| `spread_aplicado` | DecimalField(8,4, null) | Spread em p.p. adicionado (snapshot do contrato) |
| `piso_aplicado` | DecimalField(8,4, null) | Piso vigente no momento |
| `teto_aplicado` | DecimalField(8,4, null) | Teto vigente no momento |
| `usuario` | FK(auth.User, null, SET_NULL) | Quem aplicou |
| `ip_address` | GenericIPAddressField(null) | IP do usuário |
| `aplicado_manual` | BooleanField | default=False |
| `aplicado` | BooleanField | default=False — se as parcelas já foram atualizadas |
| `data_aplicacao` | DateTimeField(null) | — |
| `observacoes` | TextField(blank) | — |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

**Índices:** `[contrato, data_reajuste]`, `[contrato, ciclo, aplicado]`  
**Propriedade:** `percentual_liquido` = percentual − desconto_percentual.

---

### 3.4 HistoricoPagamento

Auditoria completa de pagamentos registrados (suporta múltiplas origens).

| Campo | Tipo | Regras |
|---|---|---|
| `parcela` | FK(Parcela, CASCADE) | — |
| `data_pagamento` | DateField | — |
| `valor_pago` | DecimalField(12,2) | — |
| `valor_parcela` | DecimalField(12,2) | Valor da parcela no momento do pagamento |
| `valor_juros` | DecimalField(12,2) | default=0 |
| `valor_multa` | DecimalField(12,2) | default=0 |
| `valor_desconto` | DecimalField(12,2) | default=0 |
| `forma_pagamento` | CharField(50) | choices: DINHEIRO / PIX / TRANSFERENCIA / BOLETO / CARTAO_CREDITO / CARTAO_DEBITO / CHEQUE |
| `comprovante` | FileField(null) | upload_to='comprovantes/%Y/%m/' |
| `observacoes` | TextField(blank) | — |
| `antecipado` | BooleanField | default=False |
| `origem_pagamento` | CharField(20) | choices: MANUAL / CNAB / OFX / ANTECIPACAO / PIX_WEBHOOK / PORTAL_UPLOAD / SISTEMA |
| `item_retorno` | FK(ItemRetorno, null, SET_NULL) | Vínculo ao CNAB que gerou este pagamento |
| `fitid_ofx` | CharField(255, blank) | ID único da transação OFX (deduplicação) |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

---

### 3.5 ArquivoRemessa

Arquivo CNAB de remessa (boletos a registrar no banco).

| Campo | Tipo | Regras |
|---|---|---|
| `conta_bancaria` | FK(ContaBancaria, PROTECT) | — |
| `numero_remessa` | PositiveIntegerField | Sequencial por conta |
| `layout` | CharField(10) | choices: CNAB_240 / CNAB_400 |
| `arquivo` | FileField | upload_to='cnab/remessa/%Y/%m/' |
| `nome_arquivo` | CharField(100) | — |
| `status` | CharField(15) | choices: GERADO / ENVIADO / PROCESSADO / ERRO |
| `data_geracao` | DateTimeField(auto_now_add) | — |
| `data_envio` | DateTimeField(null) | — |
| `quantidade_boletos` | PositiveIntegerField | — |
| `valor_total` | DecimalField(14,2) | — |
| `observacoes` | TextField(blank) | — |
| `erro_mensagem` | TextField(blank) | — |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

**Constraints:** `unique_together=[conta_bancaria, numero_remessa]`

---

### 3.6 ItemRemessa

Um boleto (parcela) incluído em um arquivo de remessa.

| Campo | Tipo | Regras |
|---|---|---|
| `arquivo_remessa` | FK(ArquivoRemessa, CASCADE) | — |
| `parcela` | FK(Parcela, PROTECT) | — |
| `nosso_numero` | CharField(30) | — |
| `valor` | DecimalField(12,2) | — |
| `data_vencimento` | DateField | — |
| `processado` | BooleanField | — |
| `codigo_ocorrencia` | CharField(10, blank) | Código retornado pelo banco |
| `descricao_ocorrencia` | CharField(255, blank) | — |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

**Constraints:** `unique_together=[arquivo_remessa, parcela]`

---

### 3.7 ArquivoRetorno

Arquivo CNAB de retorno bancário (pagamentos e ocorrências).

| Campo | Tipo | Regras |
|---|---|---|
| `conta_bancaria` | FK(ContaBancaria, PROTECT) | — |
| `arquivo` | FileField | upload_to='cnab/retorno/%Y/%m/' |
| `nome_arquivo` | CharField(100) | — |
| `layout` | CharField(10) | choices: CNAB_240 / CNAB_400 |
| `status` | CharField(20) | choices: PENDENTE / PROCESSADO / PROCESSADO_PARCIAL / ERRO |
| `data_upload` | DateTimeField(auto_now_add) | — |
| `data_processamento` | DateTimeField(null) | — |
| `processado_por` | FK(auth.User, null) | — |
| `total_registros` | PositiveIntegerField | — |
| `registros_processados` | PositiveIntegerField | — |
| `registros_erro` | PositiveIntegerField | — |
| `valor_total_pago` | DecimalField(14,2) | — |
| `observacoes` | TextField(blank) | — |
| `erro_mensagem` | TextField(blank) | — |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

---

### 3.8 ItemRetorno

Ocorrência individual processada de um arquivo de retorno CNAB.

| Campo | Tipo | Regras |
|---|---|---|
| `arquivo_retorno` | FK(ArquivoRetorno, CASCADE) | — |
| `parcela` | FK(Parcela, null, SET_NULL) | null se parcela não encontrada |
| `nosso_numero` | CharField(30) | — |
| `numero_documento` | CharField(25, blank) | — |
| `codigo_ocorrencia` | CharField(10) | — |
| `descricao_ocorrencia` | CharField(255, blank) | — |
| `tipo_ocorrencia` | CharField(20) | choices: ENTRADA / LIQUIDACAO / BAIXA / REJEICAO / PROTESTO / TARIFA / OUTROS |
| `valor_titulo` | DecimalField(12,2, null) | — |
| `valor_pago` | DecimalField(12,2, null) | — |
| `valor_juros` | DecimalField(12,2, null) | — |
| `valor_multa` | DecimalField(12,2, null) | — |
| `valor_desconto` | DecimalField(12,2, null) | — |
| `valor_tarifa` | DecimalField(12,2, null) | — |
| `data_ocorrencia` | DateField(null) | — |
| `data_credito` | DateField(null) | — |
| `processado` | BooleanField | — |
| `erro_processamento` | TextField(blank) | — |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

---

### 3.9 AcessoBoletoPublico

Log de cada acesso ao boleto público via `/b/<token>/` (rastreabilidade S-03).

| Campo | Tipo | Regras |
|---|---|---|
| `parcela` | FK(Parcela, CASCADE) | — |
| `ip` | GenericIPAddressField | — |
| `user_agent` | CharField(300, blank) | — |
| `acessado_em` | DateTimeField(auto_now_add) | — |

---

### 3.10 EventoPIX

Log de eventos PIX recebidos via webhook do PSP. Garante idempotência por `EndToEndId`.

| Campo | Tipo | Regras |
|---|---|---|
| `end_to_end_id` | CharField(35, unique, db_index) | Deduplicação — padrão BCB |
| `txid` | CharField(35, blank, db_index) | — |
| `parcela` | FK(Parcela, null, SET_NULL) | null se não encontrada |
| `valor` | DecimalField(12,2) | — |
| `horario_pix` | DateTimeField | — |
| `pagador_nome` | CharField(200, blank) | — |
| `pagador_documento` | CharField(20, blank) | CPF/CNPJ do pagador |
| `info_pagador` | TextField(blank) | — |
| `status` | CharField(20) | choices: RECEBIDO / BAIXADO / DUPLICADO / SEM_PARCELA / ERRO |
| `erro` | TextField(blank) | — |
| `payload_raw` | TextField | JSON completo do PSP (auditoria) |
| `recebido_em` | DateTimeField(auto_now_add) | — |

---

## 4. Módulo Notificações

`notificacoes/models.py` — E-mail, SMS, WhatsApp, templates e régua de cobrança.

---

### 4.1 Choices Globais

| Enum | Valores |
|---|---|
| `TipoNotificacao` | EMAIL, SMS, WHATSAPP |
| `StatusNotificacao` | PENDENTE, ENVIADA, ERRO, CANCELADA |
| `StatusEntrega` | accepted, queued, sending, sent, delivered, undelivered, failed, read, clicked, bounced, opened |
| `TipoGatilho` | ANTES (antes do vencimento), APOS (após o vencimento) |

---

### 4.2 ConfiguracaoEmail

Configuração de servidor SMTP (escopo global — sem FK para imobiliária).

| Campo | Tipo | Regras |
|---|---|---|
| `nome` | CharField(100) | Nome da configuração |
| `host` | CharField(255) | Servidor SMTP (**campo é `host`, não `servidor_smtp`**) |
| `porta` | IntegerField | default=587 |
| `usuario` | CharField(255) | — |
| `senha` | CharField(255) | — |
| `usar_tls` | BooleanField | default=True |
| `usar_ssl` | BooleanField | default=False |
| `email_remetente` | EmailField | — |
| `nome_remetente` | CharField(100) | default='Sistema de Gestão de Contratos' |
| `ativo` | BooleanField | — |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

---

### 4.3 ConfiguracaoSMS

Configuração de serviço de SMS via Twilio, Nexmo ou AWS SNS.

| Campo | Tipo | Regras |
|---|---|---|
| `nome` | CharField(100) | — |
| `provedor` | CharField(50) | choices: TWILIO / NEXMO / AWS_SNS |
| `account_sid` | CharField(255) | — |
| `auth_token` | CharField(255) | — |
| `numero_remetente` | CharField(20) | Formato internacional |
| `ativo` | BooleanField | — |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

---

### 4.4 ConfiguracaoWhatsApp

Configuração de serviço de WhatsApp (múltiplos provedores).

| Campo | Tipo | Regras |
|---|---|---|
| `nome` | CharField(100) | — |
| `provedor` | CharField(50) | choices: TWILIO / META / EVOLUTION / ZAPI / BSP |
| `account_sid` | CharField(255, blank) | Twilio/Meta |
| `auth_token` | CharField(255, blank) | Twilio/Meta |
| `numero_remetente` | CharField(30, blank) | Ex: `whatsapp:+5511999999999` |
| `api_url` | URLField(blank) | Evolution / Z-API |
| `api_key` | CharField(255, blank) | Evolution / Z-API token |
| `instancia` | CharField(100, blank) | Nome da instância |
| `client_token` | CharField(255, blank) | Z-API: cabeçalho Client-Token |
| `modo_evolution` | CharField(10, blank) | choices: BAILEYS / CLOUD_API |
| `phone_number_id` | CharField(50, blank) | Meta Cloud API |
| `meta_access_token` | CharField(512, blank) | Meta Cloud API |
| `ativo` | BooleanField | — |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

---

### 4.5 Notificacao

Fila e histórico de notificações enviadas. Suporta e-mail, SMS e WhatsApp.

| Campo | Tipo | Regras |
|---|---|---|
| `parcela` | FK(financeiro.Parcela, null, blank) | Parcela relacionada (opcional) |
| `tipo` | CharField(20) | choices: TipoNotificacao |
| `destinatario` | CharField(255) | E-mail, telefone ou número WhatsApp |
| `assunto` | CharField(255, blank) | Assunto (e-mails) |
| `mensagem` | TextField | Corpo da mensagem |
| `status` | CharField(20) | choices: StatusNotificacao |
| `data_agendamento` | DateTimeField | default=now |
| `data_envio` | DateTimeField(null) | — |
| `tentativas` | IntegerField | default=0 |
| `erro_mensagem` | TextField(blank) | — |
| `external_id` | CharField(255, blank) | Twilio MessageSid ou Message-ID do e-mail |
| `status_entrega` | CharField(20, blank) | choices: StatusEntrega (webhook do provedor) |
| `data_confirmacao` | DateTimeField(null) | Quando o provedor confirmou entrega/falha |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

**Índices:** `[status, data_agendamento]`, `[parcela]`, `[external_id]`, `[parcela, status]`

---

### 4.6 TemplateNotificacao

Templates multi-canal com suporte a TAGs `%%TAG%%`.

| Campo | Tipo | Regras |
|---|---|---|
| `nome` | CharField(100) | — |
| `codigo` | CharField(30) | choices: TipoTemplate |
| `tipo` | CharField(20, null) | Legado — canal determinado pelos campos preenchidos |
| `assunto` | CharField(255, blank) | Assunto do e-mail |
| `corpo` | TextField(blank) | Corpo SMS (max. 255 chars) |
| `corpo_html` | TextField(blank) | HTML do e-mail |
| `corpo_whatsapp` | TextField(blank) | Texto WhatsApp |
| `corpo_whatsapp_interativo` | JSONField(null) | Payload de botões WhatsApp (max. 3) |
| `imobiliaria` | FK(core.Imobiliaria, null, blank) | null = template global |
| `ativo` | BooleanField | — |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

**Constraints:** `unique_together=[codigo, imobiliaria]`  
**Prioridade:** template da imobiliária -> template global.  
**Tipos disponíveis:** BOLETO_CRIADO, BOLETO_5_DIAS, BOLETO_VENCE_AMANHA, BOLETO_VENCEU_ONTEM, BOLETO_VENCIDO, PAGAMENTO_CONFIRMADO, CONTRATO_CRIADO, LEMBRETE_PARCELA, RELATORIO_MENSAL, RELATORIO_SEMANAL, GESTAO_RELATORIO_MENSAL, GESTAO_RELATORIO_SEMANAL, CUSTOM.

---

### 4.7 RegraNotificacao

Régua de cobrança configurável — define quando e como notificar sobre parcelas.

| Campo | Tipo | Regras |
|---|---|---|
| `nome` | CharField(100) | — |
| `ativo` | BooleanField | — |
| `tipo_gatilho` | CharField(5) | choices: ANTES / APOS (vencimento) |
| `dias_offset` | PositiveIntegerField | Dias antes/após o vencimento |
| `tipo_notificacao` | CharField(10) | choices: TipoNotificacao |
| `template` | FK(TemplateNotificacao, null, SET_NULL) | null = mensagem padrão do sistema |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

**Constraints:** `unique_together=[tipo_gatilho, dias_offset, tipo_notificacao]`

---

### 4.8 SessaoConversaWhatsApp

Sessão de conversa do comprador com o chatbot WhatsApp. Estado e contexto são persistidos para continuidade.

| Campo | Tipo | Regras |
|---|---|---|
| `comprador` | FK(core.Comprador, null, SET_NULL) | Identificado após validação do CPF |
| `numero_whatsapp` | CharField(30, db_index) | E.164 sem "+", ex: 5511999999999 |
| `instancia` | CharField(100) | Instância Evolution API |
| `estado` | CharField(30) | choices: INICIO / AGUARDA_CPF / MENU / AGUARDA_SELECAO_BOLETO / AGUARDA_COMPROVANTE / ENCERRADA |
| `dados` | JSONField | Contexto temporário (IDs de parcelas, tentativas, etc.) |
| `ativo` | BooleanField(db_index) | — |
| *(TimeStampedModel)* | | `criado_em`, `atualizado_em` |

---

### 4.9 ComprovantePendente *(proxy)*

Proxy de `Notificacao` para filtrar comprovantes enviados via WhatsApp aguardando revisão manual.

---

## 5. Módulo Portal do Comprador

`portal_comprador/models.py` — Autenticação e funcionalidades do portal exclusivo do comprador.

---

### 5.1 AcessoComprador

Vincula um `Comprador` a um usuário Django para acesso ao portal. Relação OneToOne em ambas as direções.

| Campo | Tipo | Regras |
|---|---|---|
| `comprador` | OneToOneField(core.Comprador, CASCADE) | related_name='acesso_portal' |
| `usuario` | OneToOneField(auth.User, CASCADE) | related_name='acesso_comprador' |
| `data_criacao` | DateTimeField(auto_now_add) | — |
| `ultimo_acesso` | DateTimeField(null) | Atualizado por `registrar_acesso()` |
| `email_verificado` | BooleanField | default=False |
| `token_verificacao` | CharField(100, null) | Token enviado por e-mail para verificação |
| `ativo` | BooleanField | default=True |

---

### 5.2 LogAcessoComprador

Log de acessos do comprador ao portal (página a página).

| Campo | Tipo | Regras |
|---|---|---|
| `acesso_comprador` | FK(AcessoComprador, CASCADE) | related_name='logs_acesso' |
| `data_acesso` | DateTimeField(auto_now_add) | — |
| `ip_acesso` | GenericIPAddressField(null) | — |
| `user_agent` | TextField(blank) | — |
| `pagina_acessada` | CharField(255, blank) | URL acessada |

**Ordering:** `['-data_acesso']`

---

### 5.3 ComprovantePagamentoUpload

Upload de comprovante de pagamento pelo comprador via portal. Aguarda validação pelo administrador antes de baixar a parcela.

| Campo | Tipo | Regras |
|---|---|---|
| `parcela` | FK(financeiro.Parcela, CASCADE) | — |
| `acesso_comprador` | FK(AcessoComprador, null, SET_NULL) | Quem enviou |
| `comprovante` | FileField | upload_to='comprovantes_portal/%Y/%m/' |
| `valor_informado` | DecimalField(12,2) | Valor declarado pelo comprador |
| `data_pagamento_informada` | DateField | — |
| `forma_pagamento` | CharField(15) | choices: PIX / TED / DINHEIRO / BOLETO / OUTRO |
| `observacoes_comprador` | TextField(blank) | — |
| `status` | CharField(15) | choices: PENDENTE / APROVADO / REJEITADO |
| `motivo_rejeicao` | TextField(blank) | — |
| `validado_em` | DateTimeField(null) | — |
| `validado_por` | FK(auth.User, null, SET_NULL) | Administrador que validou |
| `criado_em` | DateTimeField(auto_now_add) | — |
| `atualizado_em` | DateTimeField(auto_now) | — |

**Índices:** `[status, -criado_em]`, `[parcela, status]`  
**Método `aprovar()`:** transação atômica com `SELECT FOR UPDATE` na parcela — evita double-payment concorrente.

---

### 5.4 PushSubscriptionPortal

Assinatura Web Push do comprador para recebimento de notificações push no dispositivo.

| Campo | Tipo | Regras |
|---|---|---|
| `acesso_comprador` | FK(AcessoComprador, CASCADE) | related_name='push_subscriptions' |
| `endpoint` | TextField | URL do endpoint push do browser |
| `p256dh` | TextField | Chave pública p256dh |
| `auth` | TextField | Auth secret |
| `user_agent` | CharField(200, blank) | — |
| `ativo` | BooleanField | default=True |
| `criado_em` | DateTimeField(auto_now_add) | — |
| `atualizado_em` | DateTimeField(auto_now) | — |

**Constraints:** `unique_together=[acesso_comprador, endpoint]`

---

## 6. Diagrama de Relacionamentos

```
auth.User
   ├── AcessoUsuario ──────────────────── Imobiliaria ──── Contabilidade
   ├── AcessoComprador (O2O) ─────────────── Comprador
   ├── Reajuste (usuario FK)
   ├── ArquivoRetorno (processado_por FK)
   └── ComprovantePagamentoUpload (validado_por FK)

Contabilidade
   └── Imobiliaria
         ├── ContaBancaria ──┬── ArquivoRemessa ──── ItemRemessa ──► Parcela
         │                  └── ArquivoRetorno ──── ItemRetorno ──► Parcela
         ├── TemplateNotificacao
         └── Imovel
               ├── VerticePoligono
               └── Contrato
                     ├── TabelaJurosContrato
                     ├── PrestacaoIntermediaria
                     │     └── HistoricoReajusteIntermediaria
                     ├── MinutaContrato
                     ├── ContratoImportacao
                     ├── Reajuste
                     └── Parcela
                           ├── Notificacao
                           ├── HistoricoPagamento ──► ItemRetorno
                           ├── ItemRemessa
                           ├── ItemRetorno
                           ├── AcessoBoletoPublico
                           ├── EventoPIX
                           └── ComprovantePagamentoUpload (Portal)

LoteamentoOverlay  (vinculado por nome_loteamento, sem FK)

Comprador ◄── AcessoComprador (Portal)
                 ├── LogAcessoComprador
                 ├── ComprovantePagamentoUpload
                 └── PushSubscriptionPortal

Comprador ◄── SessaoConversaWhatsApp (Notificacoes)

ParametroSistema        (configurações globais do sistema)
AcessoNegado            (log de segurança — varredura de IDs)
ConfiguracaoEmail       (SMTP — escopo global)
ConfiguracaoSMS         (SMS — escopo global)
ConfiguracaoWhatsApp    (WA — escopo global)
RegraNotificacao        (régua de cobrança)
IndiceReajuste          (tabela IPCA/IGP-M/INCC/etc.)
```

---

## 7. Decisões de Design

### 7.1 Hierarquia multi-tenant

```
Contabilidade → Imobiliaria → Imovel / ContaBancaria
                            → Comprador (via Contrato)
```

- Usuário `staff=False` acessa somente as imobiliárias vinculadas via `AcessoUsuario`.
- Usuário `staff=True` ou `superuser=True` acessa tudo sem necessidade de `AcessoUsuario`.
- O `Comprador` não tem vínculo direto com a imobiliária — um mesmo comprador pode ter contratos em imobiliárias diferentes.

### 7.2 Configuração de Boleto em Cascata

1. `Contrato.usar_config_boleto_imobiliaria = True` → usa `Imobiliaria` (multa, juros, desconto, instrução)
2. `Contrato.usar_config_boleto_imobiliaria = False` → usa campos do próprio `Contrato`
3. `Contrato.conta_bancaria_padrao` → conta específica; se null → conta `principal=True` da imobiliária

### 7.3 Boleto PDF em Banco de Dados

Campo `Parcela.boleto_pdf_db` (BinaryField) armazena uma cópia do PDF. Motivo: o Render Free Tier não possui disco persistente — o FileField (`boleto_pdf`) pode se perder em deploys. O BinaryField persiste no PostgreSQL.

### 7.4 Token Público de Boleto

`Parcela.token_publico` (UUID) permite acesso à rota `/b/<token>/` sem autenticação. `token_expira_em` é opcional (null = sem expiração). O token é gerado automaticamente por `default=uuid.uuid4`.

### 7.5 CNPJ Alfanumérico 2026

Todos os campos CNPJ usam `CharField(max_length=20)` para suportar o formato formatado de 18 chars com folga. O validador `validar_cnpj()` em `core/validators.py` implementa o algoritmo mod-11 com `_CNPJ_CHAR_VALUES` (A=17...Z=42). Ver `docs/compliance/CNPJ_2026.md`.

### 7.6 Reajuste — Modos de Cálculo

| Condição | Modo | Descrição |
|---|---|---|
| `TabelaJurosContrato` definida + `tipo_amortizacao=PRICE` | Tabela Price | PMT_novo = PMT_atual × (1+IPCA) × (1+i)^prazo |
| `TabelaJurosContrato` definida + `tipo_amortizacao=SAC` | SAC | Saldo corrigido → nova tabela SAC com `n` restantes |
| Sem `TabelaJurosContrato` | Simples | Todas as parcelas a partir da inicial × (1+IPCA+spread) |

### 7.7 Bloqueio de Boleto por Reajuste Pendente

Regra de cascata: se qualquer ciclo entre 2 e o ciclo da parcela já venceu (hoje >= data_prevista) e ainda não foi aplicado, todos os boletos daquele ciclo em diante ficam bloqueados. O campo `Contrato.bloqueio_boleto_reajuste` é atualizado por `verificar_bloqueio_reajuste()`. Contratos com `tipo_correcao=FIXO` nunca são bloqueados.

### 7.8 Portal do Comprador — Autenticação Separada

O Portal usa a mesma tabela `auth_user` do Django, mas com uma "camada portal" via `AcessoComprador`. O login é feito com CPF (username) e senha. `LogAcessoComprador` registra cada acesso por página para auditoria.

### 7.9 WhatsApp — Chatbot com Estado Persistente

`SessaoConversaWhatsApp` persiste o estado da conversa entre mensagens (stateless webhook → stateful). O campo `dados` (JSONField) armazena contexto temporário: IDs de parcelas exibidas, tentativas de CPF, etc.

### 7.10 Intermediárias — Dois Modos de Impacto

- `intermediarias_reduzem_pmt=True`: valor deduzido do saldo antes do cálculo do PMT → parcelas mensais menores.
- `intermediarias_reduzem_pmt=False`: amortizações extras sobre o PMT cheio → sem redução das mensais.

O campo `intermediarias_reajustadas` controla se os valores são corrigidos a cada ciclo ou permanecem fixos.

### 7.11 Conciliação Bancária — Três Fontes

| Origem | Modelo | Campo chave |
|---|---|---|
| Retorno CNAB | `ItemRetorno` | `nosso_numero` → `Parcela.nosso_numero` |
| Extrato OFX | `HistoricoPagamento` | `fitid_ofx` (deduplicação) |
| PIX Webhook | `EventoPIX` | `end_to_end_id` (deduplicação BCB) |

Todos os pagamentos são registrados em `HistoricoPagamento` com `origem_pagamento` indicando a fonte.
