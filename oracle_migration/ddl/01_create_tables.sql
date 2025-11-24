/*
==============================================================================
Sistema de Gestao de Contratos - Migracao para Oracle 23c
Script DDL - Criacao de Tabelas
==============================================================================
Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
Data: 2024
Oracle Version: 23c (23ai)
APEX Version: 24.1
==============================================================================
*/

-- Definir schema
-- ALTER SESSION SET CURRENT_SCHEMA = GESTAO_CONTRATO;

-- ============================================================================
-- LOOKUP TABLES (TIPOS E STATUS)
-- ============================================================================

-- Tipos de Valor (Multa, Juros, Desconto)
CREATE TABLE gc_tipo_valor (
    codigo         VARCHAR2(10) PRIMARY KEY,
    descricao      VARCHAR2(50) NOT NULL
);

INSERT INTO gc_tipo_valor VALUES ('PERCENTUAL', 'Percentual (%)');
INSERT INTO gc_tipo_valor VALUES ('REAL', 'Valor em Reais (R$)');

-- Tipos de Titulo para Boleto
CREATE TABLE gc_tipo_titulo (
    codigo         VARCHAR2(5) PRIMARY KEY,
    descricao      VARCHAR2(100) NOT NULL
);

INSERT INTO gc_tipo_titulo VALUES ('AP', 'AP - Apolice de Seguro');
INSERT INTO gc_tipo_titulo VALUES ('BDP', 'BDP - Boleto de Proposta');
INSERT INTO gc_tipo_titulo VALUES ('CC', 'CC - Cartao de Credito');
INSERT INTO gc_tipo_titulo VALUES ('CH', 'CH - Cheque');
INSERT INTO gc_tipo_titulo VALUES ('DM', 'DM - Duplicata Mercantil');
INSERT INTO gc_tipo_titulo VALUES ('DS', 'DS - Duplicata de Servico');
INSERT INTO gc_tipo_titulo VALUES ('FAT', 'FAT - Fatura');
INSERT INTO gc_tipo_titulo VALUES ('NF', 'NF - Nota Fiscal');
INSERT INTO gc_tipo_titulo VALUES ('NP', 'NP - Nota Promissoria');
INSERT INTO gc_tipo_titulo VALUES ('RC', 'RC - Recibo');
INSERT INTO gc_tipo_titulo VALUES ('O', 'O - Outros');

-- Layout CNAB
CREATE TABLE gc_layout_cnab (
    codigo         VARCHAR2(10) PRIMARY KEY,
    descricao      VARCHAR2(50) NOT NULL
);

INSERT INTO gc_layout_cnab VALUES ('CNAB_240', 'Layout 240');
INSERT INTO gc_layout_cnab VALUES ('CNAB_400', 'Layout 400');
INSERT INTO gc_layout_cnab VALUES ('CNAB_444', 'Layout 444 (CNAB 400 + Chave NFE)');

-- Bancos Brasileiros
CREATE TABLE gc_banco (
    codigo         VARCHAR2(3) PRIMARY KEY,
    nome           VARCHAR2(100) NOT NULL
);

INSERT INTO gc_banco VALUES ('001', 'Banco do Brasil');
INSERT INTO gc_banco VALUES ('004', 'Banco do Nordeste - BNB');
INSERT INTO gc_banco VALUES ('021', 'Banestes');
INSERT INTO gc_banco VALUES ('033', 'Santander');
INSERT INTO gc_banco VALUES ('041', 'Banrisul');
INSERT INTO gc_banco VALUES ('070', 'BRB - Banco de Brasilia');
INSERT INTO gc_banco VALUES ('077', 'Banco Inter');
INSERT INTO gc_banco VALUES ('104', 'Caixa Economica Federal');
INSERT INTO gc_banco VALUES ('133', 'Cresol');
INSERT INTO gc_banco VALUES ('136', 'Unicred');
INSERT INTO gc_banco VALUES ('208', 'BTG Pactual');
INSERT INTO gc_banco VALUES ('237', 'Bradesco');
INSERT INTO gc_banco VALUES ('260', 'Nubank');
INSERT INTO gc_banco VALUES ('290', 'PagBank / PagSeguro');
INSERT INTO gc_banco VALUES ('323', 'Mercado Pago');
INSERT INTO gc_banco VALUES ('336', 'C6 Bank');
INSERT INTO gc_banco VALUES ('341', 'Itau');
INSERT INTO gc_banco VALUES ('422', 'Safra');
INSERT INTO gc_banco VALUES ('748', 'Sicredi');
INSERT INTO gc_banco VALUES ('756', 'Sicoob / Bancoob');
INSERT INTO gc_banco VALUES ('000', 'Outros');

-- Estados Brasileiros
CREATE TABLE gc_uf (
    sigla          VARCHAR2(2) PRIMARY KEY,
    nome           VARCHAR2(50) NOT NULL
);

INSERT INTO gc_uf VALUES ('AC', 'Acre');
INSERT INTO gc_uf VALUES ('AL', 'Alagoas');
INSERT INTO gc_uf VALUES ('AP', 'Amapa');
INSERT INTO gc_uf VALUES ('AM', 'Amazonas');
INSERT INTO gc_uf VALUES ('BA', 'Bahia');
INSERT INTO gc_uf VALUES ('CE', 'Ceara');
INSERT INTO gc_uf VALUES ('DF', 'Distrito Federal');
INSERT INTO gc_uf VALUES ('ES', 'Espirito Santo');
INSERT INTO gc_uf VALUES ('GO', 'Goias');
INSERT INTO gc_uf VALUES ('MA', 'Maranhao');
INSERT INTO gc_uf VALUES ('MT', 'Mato Grosso');
INSERT INTO gc_uf VALUES ('MS', 'Mato Grosso do Sul');
INSERT INTO gc_uf VALUES ('MG', 'Minas Gerais');
INSERT INTO gc_uf VALUES ('PA', 'Para');
INSERT INTO gc_uf VALUES ('PB', 'Paraiba');
INSERT INTO gc_uf VALUES ('PR', 'Parana');
INSERT INTO gc_uf VALUES ('PE', 'Pernambuco');
INSERT INTO gc_uf VALUES ('PI', 'Piaui');
INSERT INTO gc_uf VALUES ('RJ', 'Rio de Janeiro');
INSERT INTO gc_uf VALUES ('RN', 'Rio Grande do Norte');
INSERT INTO gc_uf VALUES ('RS', 'Rio Grande do Sul');
INSERT INTO gc_uf VALUES ('RO', 'Rondonia');
INSERT INTO gc_uf VALUES ('RR', 'Roraima');
INSERT INTO gc_uf VALUES ('SC', 'Santa Catarina');
INSERT INTO gc_uf VALUES ('SP', 'Sao Paulo');
INSERT INTO gc_uf VALUES ('SE', 'Sergipe');
INSERT INTO gc_uf VALUES ('TO', 'Tocantins');

-- Tipos de Imovel
CREATE TABLE gc_tipo_imovel (
    codigo         VARCHAR2(20) PRIMARY KEY,
    descricao      VARCHAR2(50) NOT NULL
);

INSERT INTO gc_tipo_imovel VALUES ('LOTE', 'Lote');
INSERT INTO gc_tipo_imovel VALUES ('TERRENO', 'Terreno');
INSERT INTO gc_tipo_imovel VALUES ('CASA', 'Casa');
INSERT INTO gc_tipo_imovel VALUES ('APARTAMENTO', 'Apartamento');
INSERT INTO gc_tipo_imovel VALUES ('COMERCIAL', 'Comercial');

-- Status do Contrato
CREATE TABLE gc_status_contrato (
    codigo         VARCHAR2(20) PRIMARY KEY,
    descricao      VARCHAR2(50) NOT NULL
);

INSERT INTO gc_status_contrato VALUES ('ATIVO', 'Ativo');
INSERT INTO gc_status_contrato VALUES ('QUITADO', 'Quitado');
INSERT INTO gc_status_contrato VALUES ('CANCELADO', 'Cancelado');
INSERT INTO gc_status_contrato VALUES ('SUSPENSO', 'Suspenso');

-- Tipos de Correcao Monetaria
CREATE TABLE gc_tipo_correcao (
    codigo         VARCHAR2(10) PRIMARY KEY,
    descricao      VARCHAR2(100) NOT NULL
);

INSERT INTO gc_tipo_correcao VALUES ('IPCA', 'IPCA - Indice de Precos ao Consumidor Amplo');
INSERT INTO gc_tipo_correcao VALUES ('IGPM', 'IGP-M - Indice Geral de Precos do Mercado');
INSERT INTO gc_tipo_correcao VALUES ('INCC', 'INCC - Indice Nacional de Custo da Construcao');
INSERT INTO gc_tipo_correcao VALUES ('IGPDI', 'IGP-DI - Indice Geral de Precos - Disponibilidade Interna');
INSERT INTO gc_tipo_correcao VALUES ('INPC', 'INPC - Indice Nacional de Precos ao Consumidor');
INSERT INTO gc_tipo_correcao VALUES ('TR', 'TR - Taxa Referencial');
INSERT INTO gc_tipo_correcao VALUES ('SELIC', 'SELIC - Taxa Basica de Juros');
INSERT INTO gc_tipo_correcao VALUES ('FIXO', 'Valor Fixo (sem correcao)');

-- Status do Boleto
CREATE TABLE gc_status_boleto (
    codigo         VARCHAR2(15) PRIMARY KEY,
    descricao      VARCHAR2(50) NOT NULL
);

INSERT INTO gc_status_boleto VALUES ('NAO_GERADO', 'Nao Gerado');
INSERT INTO gc_status_boleto VALUES ('GERADO', 'Gerado');
INSERT INTO gc_status_boleto VALUES ('REGISTRADO', 'Registrado no Banco');
INSERT INTO gc_status_boleto VALUES ('PAGO', 'Pago');
INSERT INTO gc_status_boleto VALUES ('VENCIDO', 'Vencido');
INSERT INTO gc_status_boleto VALUES ('CANCELADO', 'Cancelado');
INSERT INTO gc_status_boleto VALUES ('PROTESTADO', 'Protestado');
INSERT INTO gc_status_boleto VALUES ('BAIXADO', 'Baixado');

-- Formas de Pagamento
CREATE TABLE gc_forma_pagamento (
    codigo         VARCHAR2(20) PRIMARY KEY,
    descricao      VARCHAR2(50) NOT NULL
);

INSERT INTO gc_forma_pagamento VALUES ('DINHEIRO', 'Dinheiro');
INSERT INTO gc_forma_pagamento VALUES ('PIX', 'PIX');
INSERT INTO gc_forma_pagamento VALUES ('TRANSFERENCIA', 'Transferencia Bancaria');
INSERT INTO gc_forma_pagamento VALUES ('BOLETO', 'Boleto');
INSERT INTO gc_forma_pagamento VALUES ('CARTAO_CREDITO', 'Cartao de Credito');
INSERT INTO gc_forma_pagamento VALUES ('CARTAO_DEBITO', 'Cartao de Debito');
INSERT INTO gc_forma_pagamento VALUES ('CHEQUE', 'Cheque');

-- Tipos de Notificacao
CREATE TABLE gc_tipo_notificacao (
    codigo         VARCHAR2(20) PRIMARY KEY,
    descricao      VARCHAR2(50) NOT NULL
);

INSERT INTO gc_tipo_notificacao VALUES ('EMAIL', 'E-mail');
INSERT INTO gc_tipo_notificacao VALUES ('SMS', 'SMS');
INSERT INTO gc_tipo_notificacao VALUES ('WHATSAPP', 'WhatsApp');

-- Status da Notificacao
CREATE TABLE gc_status_notificacao (
    codigo         VARCHAR2(20) PRIMARY KEY,
    descricao      VARCHAR2(50) NOT NULL
);

INSERT INTO gc_status_notificacao VALUES ('PENDENTE', 'Pendente');
INSERT INTO gc_status_notificacao VALUES ('ENVIADA', 'Enviada');
INSERT INTO gc_status_notificacao VALUES ('ERRO', 'Erro');
INSERT INTO gc_status_notificacao VALUES ('CANCELADA', 'Cancelada');

-- Tipos de Template
CREATE TABLE gc_tipo_template (
    codigo         VARCHAR2(30) PRIMARY KEY,
    descricao      VARCHAR2(100) NOT NULL
);

INSERT INTO gc_tipo_template VALUES ('BOLETO_CRIADO', 'Boleto Criado');
INSERT INTO gc_tipo_template VALUES ('BOLETO_5_DIAS', 'Boleto - 5 dias para vencer');
INSERT INTO gc_tipo_template VALUES ('BOLETO_VENCE_AMANHA', 'Boleto - Vence amanha');
INSERT INTO gc_tipo_template VALUES ('BOLETO_VENCEU_ONTEM', 'Boleto - Venceu ontem');
INSERT INTO gc_tipo_template VALUES ('BOLETO_VENCIDO', 'Boleto Vencido');
INSERT INTO gc_tipo_template VALUES ('PAGAMENTO_CONFIRMADO', 'Pagamento Confirmado');
INSERT INTO gc_tipo_template VALUES ('CONTRATO_CRIADO', 'Contrato Criado');
INSERT INTO gc_tipo_template VALUES ('LEMBRETE_PARCELA', 'Lembrete de Parcela');
INSERT INTO gc_tipo_template VALUES ('CUSTOM', 'Personalizado');

COMMIT;

-- ============================================================================
-- TABELA: CONTABILIDADES
-- ============================================================================
CREATE TABLE gc_contabilidade (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome                 VARCHAR2(200) NOT NULL,
    razao_social         VARCHAR2(200) NOT NULL,
    cnpj                 VARCHAR2(20) UNIQUE,
    endereco             CLOB,
    telefone             VARCHAR2(20) NOT NULL,
    email                VARCHAR2(254) NOT NULL,
    responsavel          VARCHAR2(200) NOT NULL,
    ativo                NUMBER(1) DEFAULT 1 NOT NULL,
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT chk_contab_ativo CHECK (ativo IN (0, 1))
);

CREATE INDEX idx_contab_nome ON gc_contabilidade(nome);
CREATE INDEX idx_contab_ativo ON gc_contabilidade(ativo);

COMMENT ON TABLE gc_contabilidade IS 'Contabilidades que gerenciam loteamentos';
COMMENT ON COLUMN gc_contabilidade.cnpj IS 'Suporta formato numerico atual e alfanumerico (2026)';

-- ============================================================================
-- TABELA: IMOBILIARIAS
-- ============================================================================
CREATE TABLE gc_imobiliaria (
    id                           NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contabilidade_id             NUMBER NOT NULL,
    nome                         VARCHAR2(200) NOT NULL,
    razao_social                 VARCHAR2(200) NOT NULL,
    cnpj                         VARCHAR2(20) NOT NULL UNIQUE,
    -- Endereco estruturado
    cep                          VARCHAR2(9),
    logradouro                   VARCHAR2(200),
    numero                       VARCHAR2(10),
    complemento                  VARCHAR2(100),
    bairro                       VARCHAR2(100),
    cidade                       VARCHAR2(100),
    estado                       VARCHAR2(2),
    endereco                     CLOB, -- Legacy
    -- Contato
    telefone                     VARCHAR2(20) NOT NULL,
    email                        VARCHAR2(254) NOT NULL,
    responsavel_financeiro       VARCHAR2(200) NOT NULL,
    banco                        VARCHAR2(100),
    agencia                      VARCHAR2(20),
    conta                        VARCHAR2(20),
    pix                          VARCHAR2(100),
    -- Configuracoes de Boleto
    tipo_valor_multa             VARCHAR2(10) DEFAULT 'PERCENTUAL',
    percentual_multa_padrao      NUMBER(10,2) DEFAULT 0,
    tipo_valor_juros             VARCHAR2(10) DEFAULT 'PERCENTUAL',
    percentual_juros_padrao      NUMBER(10,4) DEFAULT 0,
    dias_para_encargos_padrao    NUMBER(5) DEFAULT 0,
    boleto_sem_valor             NUMBER(1) DEFAULT 0,
    parcela_no_documento         NUMBER(1) DEFAULT 0,
    campo_desconto_abatimento_pdf NUMBER(1) DEFAULT 0,
    -- Descontos
    tipo_valor_desconto          VARCHAR2(10) DEFAULT 'PERCENTUAL',
    percentual_desconto_padrao   NUMBER(10,2) DEFAULT 0,
    dias_para_desconto_padrao    NUMBER(5) DEFAULT 0,
    tipo_valor_desconto2         VARCHAR2(10) DEFAULT 'PERCENTUAL',
    desconto2_padrao             NUMBER(10,2) DEFAULT 0,
    dias_para_desconto2_padrao   NUMBER(5) DEFAULT 0,
    tipo_valor_desconto3         VARCHAR2(10) DEFAULT 'PERCENTUAL',
    desconto3_padrao             NUMBER(10,2) DEFAULT 0,
    dias_para_desconto3_padrao   NUMBER(5) DEFAULT 0,
    -- Instrucoes
    instrucao_padrao             VARCHAR2(255),
    tipo_titulo                  VARCHAR2(5) DEFAULT 'RC',
    aceite                       NUMBER(1) DEFAULT 0,
    ativo                        NUMBER(1) DEFAULT 1 NOT NULL,
    criado_em                    TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em                TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_imob_contab FOREIGN KEY (contabilidade_id) REFERENCES gc_contabilidade(id),
    CONSTRAINT fk_imob_estado FOREIGN KEY (estado) REFERENCES gc_uf(sigla),
    CONSTRAINT fk_imob_tipo_multa FOREIGN KEY (tipo_valor_multa) REFERENCES gc_tipo_valor(codigo),
    CONSTRAINT fk_imob_tipo_juros FOREIGN KEY (tipo_valor_juros) REFERENCES gc_tipo_valor(codigo),
    CONSTRAINT fk_imob_tipo_desc FOREIGN KEY (tipo_valor_desconto) REFERENCES gc_tipo_valor(codigo),
    CONSTRAINT fk_imob_tipo_titulo FOREIGN KEY (tipo_titulo) REFERENCES gc_tipo_titulo(codigo),
    CONSTRAINT chk_imob_ativo CHECK (ativo IN (0, 1))
);

CREATE INDEX idx_imob_contab ON gc_imobiliaria(contabilidade_id);
CREATE INDEX idx_imob_nome ON gc_imobiliaria(nome);
CREATE INDEX idx_imob_ativo ON gc_imobiliaria(ativo);

COMMENT ON TABLE gc_imobiliaria IS 'Imobiliarias/Beneficiarios dos contratos';

-- ============================================================================
-- TABELA: CONTAS BANCARIAS
-- ============================================================================
CREATE TABLE gc_conta_bancaria (
    id                         NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    imobiliaria_id             NUMBER NOT NULL,
    banco                      VARCHAR2(3) NOT NULL,
    descricao                  VARCHAR2(150) NOT NULL,
    principal                  NUMBER(1) DEFAULT 0,
    agencia                    VARCHAR2(10) NOT NULL,
    conta                      VARCHAR2(20) NOT NULL,
    convenio                   VARCHAR2(20),
    carteira                   VARCHAR2(5),
    nosso_numero_atual         NUMBER(15) DEFAULT 0,
    modalidade                 VARCHAR2(5),
    tipo_pix                   VARCHAR2(20),
    chave_pix                  VARCHAR2(100),
    cobranca_registrada        NUMBER(1) DEFAULT 1,
    prazo_baixa                NUMBER(5) DEFAULT 0,
    prazo_protesto             NUMBER(5) DEFAULT 0,
    layout_cnab                VARCHAR2(10) DEFAULT 'CNAB_240',
    numero_remessa_cnab_atual  NUMBER(10) DEFAULT 0,
    ativo                      NUMBER(1) DEFAULT 1 NOT NULL,
    criado_em                  TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em              TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_conta_imob FOREIGN KEY (imobiliaria_id) REFERENCES gc_imobiliaria(id),
    CONSTRAINT fk_conta_banco FOREIGN KEY (banco) REFERENCES gc_banco(codigo),
    CONSTRAINT fk_conta_layout FOREIGN KEY (layout_cnab) REFERENCES gc_layout_cnab(codigo),
    CONSTRAINT chk_conta_principal CHECK (principal IN (0, 1)),
    CONSTRAINT chk_conta_ativo CHECK (ativo IN (0, 1))
);

CREATE INDEX idx_conta_imob ON gc_conta_bancaria(imobiliaria_id);
CREATE INDEX idx_conta_principal ON gc_conta_bancaria(principal);

COMMENT ON TABLE gc_conta_bancaria IS 'Contas bancarias das imobiliarias para geracao de boletos';

-- ============================================================================
-- TABELA: IMOVEIS
-- ============================================================================
CREATE TABLE gc_imovel (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    imobiliaria_id       NUMBER NOT NULL,
    tipo                 VARCHAR2(20) DEFAULT 'LOTE' NOT NULL,
    identificacao        VARCHAR2(100) NOT NULL,
    loteamento           VARCHAR2(200),
    -- Endereco estruturado
    cep                  VARCHAR2(9),
    logradouro           VARCHAR2(200),
    numero               VARCHAR2(10),
    complemento          VARCHAR2(100),
    bairro               VARCHAR2(100),
    cidade               VARCHAR2(100),
    estado               VARCHAR2(2),
    endereco             CLOB, -- Legacy
    -- Geolocalizacao
    latitude             NUMBER(10,7),
    longitude            NUMBER(10,7),
    -- Dados do imovel
    area                 NUMBER(10,2) NOT NULL,
    valor                NUMBER(12,2),
    matricula            VARCHAR2(100),
    inscricao_municipal  VARCHAR2(100),
    observacoes          CLOB,
    disponivel           NUMBER(1) DEFAULT 1 NOT NULL,
    ativo                NUMBER(1) DEFAULT 1 NOT NULL,
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_imovel_imob FOREIGN KEY (imobiliaria_id) REFERENCES gc_imobiliaria(id),
    CONSTRAINT fk_imovel_tipo FOREIGN KEY (tipo) REFERENCES gc_tipo_imovel(codigo),
    CONSTRAINT fk_imovel_estado FOREIGN KEY (estado) REFERENCES gc_uf(sigla),
    CONSTRAINT chk_imovel_disp CHECK (disponivel IN (0, 1)),
    CONSTRAINT chk_imovel_ativo CHECK (ativo IN (0, 1))
);

CREATE INDEX idx_imovel_imob ON gc_imovel(imobiliaria_id);
CREATE INDEX idx_imovel_loteamento ON gc_imovel(loteamento);
CREATE INDEX idx_imovel_disp_ativo ON gc_imovel(disponivel, ativo);

COMMENT ON TABLE gc_imovel IS 'Imoveis (lotes, terrenos, casas, etc.)';

-- ============================================================================
-- TABELA: COMPRADORES
-- ============================================================================
CREATE TABLE gc_comprador (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo_pessoa          VARCHAR2(2) DEFAULT 'PF' NOT NULL,
    nome                 VARCHAR2(200) NOT NULL,
    -- Pessoa Fisica
    cpf                  VARCHAR2(14),
    rg                   VARCHAR2(20),
    data_nascimento      DATE,
    estado_civil         VARCHAR2(20),
    profissao            VARCHAR2(100),
    -- Pessoa Juridica
    cnpj                 VARCHAR2(20),
    nome_fantasia        VARCHAR2(200),
    inscricao_estadual   VARCHAR2(20),
    inscricao_municipal  VARCHAR2(20),
    responsavel_legal    VARCHAR2(200),
    responsavel_cpf      VARCHAR2(14),
    -- Endereco estruturado
    cep                  VARCHAR2(9),
    logradouro           VARCHAR2(200),
    numero               VARCHAR2(10),
    complemento          VARCHAR2(100),
    bairro               VARCHAR2(100),
    cidade               VARCHAR2(100),
    estado               VARCHAR2(2),
    endereco             CLOB, -- Legacy
    -- Contato
    telefone             VARCHAR2(20) NOT NULL,
    celular              VARCHAR2(20) NOT NULL,
    email                VARCHAR2(254) NOT NULL,
    -- Preferencias de Notificacao
    notificar_email      NUMBER(1) DEFAULT 1,
    notificar_sms        NUMBER(1) DEFAULT 0,
    notificar_whatsapp   NUMBER(1) DEFAULT 0,
    -- Conjuge
    conjuge_nome         VARCHAR2(200),
    conjuge_cpf          VARCHAR2(14),
    conjuge_rg           VARCHAR2(20),
    observacoes          CLOB,
    ativo                NUMBER(1) DEFAULT 1 NOT NULL,
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_compr_estado FOREIGN KEY (estado) REFERENCES gc_uf(sigla),
    CONSTRAINT chk_compr_tipo CHECK (tipo_pessoa IN ('PF', 'PJ')),
    CONSTRAINT chk_compr_ativo CHECK (ativo IN (0, 1))
);

CREATE INDEX idx_compr_tipo ON gc_comprador(tipo_pessoa);
CREATE INDEX idx_compr_cpf ON gc_comprador(cpf);
CREATE INDEX idx_compr_cnpj ON gc_comprador(cnpj);
CREATE INDEX idx_compr_nome ON gc_comprador(nome);

COMMENT ON TABLE gc_comprador IS 'Compradores (Pessoa Fisica ou Juridica)';

-- ============================================================================
-- TABELA: INDICES DE REAJUSTE
-- ============================================================================
CREATE TABLE gc_indice_reajuste (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo_indice          VARCHAR2(10) NOT NULL,
    ano                  NUMBER(4) NOT NULL,
    mes                  NUMBER(2) NOT NULL,
    valor                NUMBER(8,4) NOT NULL,
    valor_acumulado_ano  NUMBER(10,4),
    valor_acumulado_12m  NUMBER(10,4),
    fonte                VARCHAR2(100) DEFAULT '',
    data_importacao      TIMESTAMP,
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_indice_tipo FOREIGN KEY (tipo_indice) REFERENCES gc_tipo_correcao(codigo),
    CONSTRAINT uk_indice_periodo UNIQUE (tipo_indice, ano, mes),
    CONSTRAINT chk_indice_ano CHECK (ano BETWEEN 1990 AND 2100),
    CONSTRAINT chk_indice_mes CHECK (mes BETWEEN 1 AND 12)
);

CREATE INDEX idx_indice_tipo_ano_mes ON gc_indice_reajuste(tipo_indice, ano, mes);

COMMENT ON TABLE gc_indice_reajuste IS 'Indices de reajuste mensais (IPCA, IGPM, etc.)';

-- ============================================================================
-- TABELA: CONTRATOS
-- ============================================================================
CREATE TABLE gc_contrato (
    id                           NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    imovel_id                    NUMBER NOT NULL,
    comprador_id                 NUMBER NOT NULL,
    imobiliaria_id               NUMBER NOT NULL,
    numero_contrato              VARCHAR2(50) NOT NULL UNIQUE,
    data_contrato                DATE DEFAULT SYSDATE NOT NULL,
    data_primeiro_vencimento     DATE NOT NULL,
    -- Valores
    valor_total                  NUMBER(12,2) NOT NULL,
    valor_entrada                NUMBER(12,2) DEFAULT 0,
    valor_financiado             NUMBER(12,2),
    valor_parcela_original       NUMBER(12,2),
    -- Parcelas
    numero_parcelas              NUMBER(5) NOT NULL,
    dia_vencimento               NUMBER(2) NOT NULL,
    -- Juros e Multa
    percentual_juros_mora        NUMBER(5,2) DEFAULT 1.00,
    percentual_multa             NUMBER(5,2) DEFAULT 2.00,
    -- Correcao Monetaria
    tipo_correcao                VARCHAR2(10) DEFAULT 'IPCA',
    prazo_reajuste_meses         NUMBER(5) DEFAULT 12,
    data_ultimo_reajuste         DATE,
    status                       VARCHAR2(20) DEFAULT 'ATIVO',
    -- Configuracoes de Boleto
    usar_config_boleto_imobiliaria NUMBER(1) DEFAULT 1,
    conta_bancaria_padrao_id     NUMBER,
    tipo_valor_multa             VARCHAR2(10) DEFAULT 'PERCENTUAL',
    valor_multa_boleto           NUMBER(10,2) DEFAULT 0,
    tipo_valor_juros             VARCHAR2(10) DEFAULT 'PERCENTUAL',
    valor_juros_boleto           NUMBER(10,4) DEFAULT 0,
    dias_carencia_boleto         NUMBER(5) DEFAULT 0,
    tipo_valor_desconto          VARCHAR2(10) DEFAULT 'PERCENTUAL',
    valor_desconto_boleto        NUMBER(10,2) DEFAULT 0,
    dias_desconto_boleto         NUMBER(5) DEFAULT 0,
    instrucao_boleto_1           VARCHAR2(255),
    instrucao_boleto_2           VARCHAR2(255),
    instrucao_boleto_3           VARCHAR2(255),
    observacoes                  CLOB,
    criado_em                    TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em                TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_contrato_imovel FOREIGN KEY (imovel_id) REFERENCES gc_imovel(id),
    CONSTRAINT fk_contrato_comprador FOREIGN KEY (comprador_id) REFERENCES gc_comprador(id),
    CONSTRAINT fk_contrato_imob FOREIGN KEY (imobiliaria_id) REFERENCES gc_imobiliaria(id),
    CONSTRAINT fk_contrato_tipo_corr FOREIGN KEY (tipo_correcao) REFERENCES gc_tipo_correcao(codigo),
    CONSTRAINT fk_contrato_status FOREIGN KEY (status) REFERENCES gc_status_contrato(codigo),
    CONSTRAINT fk_contrato_conta FOREIGN KEY (conta_bancaria_padrao_id) REFERENCES gc_conta_bancaria(id),
    CONSTRAINT chk_contrato_parcelas CHECK (numero_parcelas BETWEEN 1 AND 600),
    CONSTRAINT chk_contrato_dia_venc CHECK (dia_vencimento BETWEEN 1 AND 31),
    CONSTRAINT chk_contrato_valor CHECK (valor_total > 0)
);

CREATE INDEX idx_contrato_numero ON gc_contrato(numero_contrato);
CREATE INDEX idx_contrato_status ON gc_contrato(status);
CREATE INDEX idx_contrato_data ON gc_contrato(data_contrato);
CREATE INDEX idx_contrato_imovel ON gc_contrato(imovel_id);
CREATE INDEX idx_contrato_comprador ON gc_contrato(comprador_id);
CREATE INDEX idx_contrato_imob ON gc_contrato(imobiliaria_id);

COMMENT ON TABLE gc_contrato IS 'Contratos de venda de imoveis';

-- ============================================================================
-- TABELA: PARCELAS
-- ============================================================================
CREATE TABLE gc_parcela (
    id                       NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contrato_id              NUMBER NOT NULL,
    numero_parcela           NUMBER(5) NOT NULL,
    data_vencimento          DATE NOT NULL,
    -- Valores
    valor_original           NUMBER(12,2) NOT NULL,
    valor_atual              NUMBER(12,2) NOT NULL,
    valor_juros              NUMBER(12,2) DEFAULT 0,
    valor_multa              NUMBER(12,2) DEFAULT 0,
    valor_desconto           NUMBER(12,2) DEFAULT 0,
    -- Status de Pagamento
    pago                     NUMBER(1) DEFAULT 0,
    data_pagamento           DATE,
    valor_pago               NUMBER(12,2),
    observacoes              CLOB,
    -- Dados do Boleto
    conta_bancaria_id        NUMBER,
    nosso_numero             VARCHAR2(30),
    numero_documento         VARCHAR2(25),
    codigo_barras            VARCHAR2(50),
    linha_digitavel          VARCHAR2(60),
    boleto_pdf               BLOB,
    boleto_pdf_nome          VARCHAR2(255),
    boleto_url               VARCHAR2(500),
    status_boleto            VARCHAR2(15) DEFAULT 'NAO_GERADO',
    data_geracao_boleto      TIMESTAMP,
    data_registro_boleto     TIMESTAMP,
    data_pagamento_boleto    TIMESTAMP,
    valor_boleto             NUMBER(12,2),
    valor_pago_boleto        NUMBER(12,2),
    banco_pagador            VARCHAR2(10),
    agencia_pagadora         VARCHAR2(10),
    motivo_rejeicao          VARCHAR2(255),
    -- PIX
    pix_copia_cola           CLOB,
    pix_qrcode               CLOB,
    criado_em                TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_parcela_contrato FOREIGN KEY (contrato_id) REFERENCES gc_contrato(id) ON DELETE CASCADE,
    CONSTRAINT fk_parcela_conta FOREIGN KEY (conta_bancaria_id) REFERENCES gc_conta_bancaria(id),
    CONSTRAINT fk_parcela_status FOREIGN KEY (status_boleto) REFERENCES gc_status_boleto(codigo),
    CONSTRAINT uk_parcela_contrato UNIQUE (contrato_id, numero_parcela),
    CONSTRAINT chk_parcela_pago CHECK (pago IN (0, 1)),
    CONSTRAINT chk_parcela_valor CHECK (valor_original > 0)
);

CREATE INDEX idx_parcela_contrato ON gc_parcela(contrato_id);
CREATE INDEX idx_parcela_vencimento ON gc_parcela(data_vencimento);
CREATE INDEX idx_parcela_pago ON gc_parcela(pago);
CREATE INDEX idx_parcela_status ON gc_parcela(status_boleto);
CREATE INDEX idx_parcela_nosso_num ON gc_parcela(nosso_numero);

COMMENT ON TABLE gc_parcela IS 'Parcelas dos contratos';

-- ============================================================================
-- TABELA: REAJUSTES
-- ============================================================================
CREATE TABLE gc_reajuste (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contrato_id          NUMBER NOT NULL,
    data_reajuste        DATE DEFAULT SYSDATE NOT NULL,
    indice_tipo          VARCHAR2(10) NOT NULL,
    percentual           NUMBER(8,4) NOT NULL,
    parcela_inicial      NUMBER(5) NOT NULL,
    parcela_final        NUMBER(5) NOT NULL,
    aplicado_manual      NUMBER(1) DEFAULT 0,
    observacoes          CLOB,
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_reajuste_contrato FOREIGN KEY (contrato_id) REFERENCES gc_contrato(id) ON DELETE CASCADE,
    CONSTRAINT chk_reajuste_manual CHECK (aplicado_manual IN (0, 1))
);

CREATE INDEX idx_reajuste_contrato ON gc_reajuste(contrato_id, data_reajuste);

COMMENT ON TABLE gc_reajuste IS 'Historico de reajustes aplicados nos contratos';

-- ============================================================================
-- TABELA: HISTORICO DE PAGAMENTOS
-- ============================================================================
CREATE TABLE gc_historico_pagamento (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    parcela_id           NUMBER NOT NULL,
    data_pagamento       DATE NOT NULL,
    valor_pago           NUMBER(12,2) NOT NULL,
    valor_parcela        NUMBER(12,2) NOT NULL,
    valor_juros          NUMBER(12,2) DEFAULT 0,
    valor_multa          NUMBER(12,2) DEFAULT 0,
    valor_desconto       NUMBER(12,2) DEFAULT 0,
    forma_pagamento      VARCHAR2(20) DEFAULT 'DINHEIRO',
    comprovante          BLOB,
    comprovante_nome     VARCHAR2(255),
    observacoes          CLOB,
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_hist_pag_parcela FOREIGN KEY (parcela_id) REFERENCES gc_parcela(id) ON DELETE CASCADE,
    CONSTRAINT fk_hist_pag_forma FOREIGN KEY (forma_pagamento) REFERENCES gc_forma_pagamento(codigo)
);

CREATE INDEX idx_hist_pag_parcela ON gc_historico_pagamento(parcela_id, data_pagamento);

COMMENT ON TABLE gc_historico_pagamento IS 'Historico de pagamentos das parcelas';

-- ============================================================================
-- TABELA: ARQUIVOS DE REMESSA CNAB
-- ============================================================================
CREATE TABLE gc_arquivo_remessa (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conta_bancaria_id    NUMBER NOT NULL,
    numero_remessa       NUMBER(10) NOT NULL,
    layout               VARCHAR2(10) DEFAULT 'CNAB_240',
    arquivo              BLOB,
    arquivo_nome         VARCHAR2(100) NOT NULL,
    status               VARCHAR2(15) DEFAULT 'GERADO',
    data_geracao         TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    data_envio           TIMESTAMP,
    quantidade_boletos   NUMBER(10) DEFAULT 0,
    valor_total          NUMBER(14,2) DEFAULT 0,
    observacoes          CLOB,
    erro_mensagem        CLOB,
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_remessa_conta FOREIGN KEY (conta_bancaria_id) REFERENCES gc_conta_bancaria(id),
    CONSTRAINT uk_remessa_conta_num UNIQUE (conta_bancaria_id, numero_remessa)
);

CREATE INDEX idx_remessa_status ON gc_arquivo_remessa(status);
CREATE INDEX idx_remessa_data ON gc_arquivo_remessa(data_geracao);

COMMENT ON TABLE gc_arquivo_remessa IS 'Arquivos de remessa CNAB enviados ao banco';

-- ============================================================================
-- TABELA: ITENS DE REMESSA
-- ============================================================================
CREATE TABLE gc_item_remessa (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    arquivo_remessa_id   NUMBER NOT NULL,
    parcela_id           NUMBER NOT NULL,
    nosso_numero         VARCHAR2(30) NOT NULL,
    valor                NUMBER(12,2) NOT NULL,
    data_vencimento      DATE NOT NULL,
    processado           NUMBER(1) DEFAULT 0,
    codigo_ocorrencia    VARCHAR2(10),
    descricao_ocorrencia VARCHAR2(255),
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_item_rem_arquivo FOREIGN KEY (arquivo_remessa_id) REFERENCES gc_arquivo_remessa(id) ON DELETE CASCADE,
    CONSTRAINT fk_item_rem_parcela FOREIGN KEY (parcela_id) REFERENCES gc_parcela(id),
    CONSTRAINT uk_item_rem UNIQUE (arquivo_remessa_id, parcela_id)
);

CREATE INDEX idx_item_rem_arquivo ON gc_item_remessa(arquivo_remessa_id);

COMMENT ON TABLE gc_item_remessa IS 'Itens (boletos) incluidos no arquivo de remessa';

-- ============================================================================
-- TABELA: ARQUIVOS DE RETORNO CNAB
-- ============================================================================
CREATE TABLE gc_arquivo_retorno (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conta_bancaria_id    NUMBER NOT NULL,
    arquivo              BLOB,
    arquivo_nome         VARCHAR2(100) NOT NULL,
    layout               VARCHAR2(10) DEFAULT 'CNAB_240',
    status               VARCHAR2(20) DEFAULT 'PENDENTE',
    data_upload          TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    data_processamento   TIMESTAMP,
    processado_por_id    NUMBER,
    total_registros      NUMBER(10) DEFAULT 0,
    registros_processados NUMBER(10) DEFAULT 0,
    registros_erro       NUMBER(10) DEFAULT 0,
    valor_total_pago     NUMBER(14,2) DEFAULT 0,
    observacoes          CLOB,
    erro_mensagem        CLOB,
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_retorno_conta FOREIGN KEY (conta_bancaria_id) REFERENCES gc_conta_bancaria(id)
);

CREATE INDEX idx_retorno_status ON gc_arquivo_retorno(status);
CREATE INDEX idx_retorno_data ON gc_arquivo_retorno(data_upload);

COMMENT ON TABLE gc_arquivo_retorno IS 'Arquivos de retorno CNAB recebidos do banco';

-- ============================================================================
-- TABELA: ITENS DE RETORNO
-- ============================================================================
CREATE TABLE gc_item_retorno (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    arquivo_retorno_id   NUMBER NOT NULL,
    parcela_id           NUMBER,
    nosso_numero         VARCHAR2(30) NOT NULL,
    numero_documento     VARCHAR2(25),
    codigo_ocorrencia    VARCHAR2(10) NOT NULL,
    descricao_ocorrencia VARCHAR2(255),
    tipo_ocorrencia      VARCHAR2(20) DEFAULT 'OUTROS',
    valor_titulo         NUMBER(12,2),
    valor_pago           NUMBER(12,2),
    valor_juros          NUMBER(12,2),
    valor_multa          NUMBER(12,2),
    valor_desconto       NUMBER(12,2),
    valor_tarifa         NUMBER(12,2),
    data_ocorrencia      DATE,
    data_credito         DATE,
    processado           NUMBER(1) DEFAULT 0,
    erro_processamento   CLOB,
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_item_ret_arquivo FOREIGN KEY (arquivo_retorno_id) REFERENCES gc_arquivo_retorno(id) ON DELETE CASCADE,
    CONSTRAINT fk_item_ret_parcela FOREIGN KEY (parcela_id) REFERENCES gc_parcela(id)
);

CREATE INDEX idx_item_ret_arquivo ON gc_item_retorno(arquivo_retorno_id);
CREATE INDEX idx_item_ret_nosso_num ON gc_item_retorno(nosso_numero);
CREATE INDEX idx_item_ret_tipo ON gc_item_retorno(tipo_ocorrencia);

COMMENT ON TABLE gc_item_retorno IS 'Itens processados do arquivo de retorno CNAB';

-- ============================================================================
-- TABELA: CONFIGURACAO DE EMAIL
-- ============================================================================
CREATE TABLE gc_config_email (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome                 VARCHAR2(100) NOT NULL,
    host                 VARCHAR2(255) NOT NULL,
    porta                NUMBER(5) DEFAULT 587,
    usuario              VARCHAR2(255) NOT NULL,
    senha                VARCHAR2(255) NOT NULL,
    usar_tls             NUMBER(1) DEFAULT 1,
    usar_ssl             NUMBER(1) DEFAULT 0,
    email_remetente      VARCHAR2(254) NOT NULL,
    nome_remetente       VARCHAR2(100) DEFAULT 'Sistema de Gestao de Contratos',
    ativo                NUMBER(1) DEFAULT 1,
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL
);

COMMENT ON TABLE gc_config_email IS 'Configuracoes de servidor SMTP para envio de emails';

-- ============================================================================
-- TABELA: CONFIGURACAO DE SMS
-- ============================================================================
CREATE TABLE gc_config_sms (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome                 VARCHAR2(100) NOT NULL,
    provedor             VARCHAR2(50) DEFAULT 'TWILIO',
    account_sid          VARCHAR2(255) NOT NULL,
    auth_token           VARCHAR2(255) NOT NULL,
    numero_remetente     VARCHAR2(20) NOT NULL,
    ativo                NUMBER(1) DEFAULT 1,
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL
);

COMMENT ON TABLE gc_config_sms IS 'Configuracoes de servico de SMS';

-- ============================================================================
-- TABELA: CONFIGURACAO DE WHATSAPP
-- ============================================================================
CREATE TABLE gc_config_whatsapp (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome                 VARCHAR2(100) NOT NULL,
    provedor             VARCHAR2(50) DEFAULT 'TWILIO',
    account_sid          VARCHAR2(255) NOT NULL,
    auth_token           VARCHAR2(255) NOT NULL,
    numero_remetente     VARCHAR2(20) NOT NULL,
    ativo                NUMBER(1) DEFAULT 1,
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL
);

COMMENT ON TABLE gc_config_whatsapp IS 'Configuracoes de servico de WhatsApp';

-- ============================================================================
-- TABELA: NOTIFICACOES
-- ============================================================================
CREATE TABLE gc_notificacao (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    parcela_id           NUMBER,
    tipo                 VARCHAR2(20) NOT NULL,
    destinatario         VARCHAR2(255) NOT NULL,
    assunto              VARCHAR2(255),
    mensagem             CLOB NOT NULL,
    status               VARCHAR2(20) DEFAULT 'PENDENTE',
    data_agendamento     TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    data_envio           TIMESTAMP,
    tentativas           NUMBER(5) DEFAULT 0,
    erro_mensagem        CLOB,
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_notif_parcela FOREIGN KEY (parcela_id) REFERENCES gc_parcela(id),
    CONSTRAINT fk_notif_tipo FOREIGN KEY (tipo) REFERENCES gc_tipo_notificacao(codigo),
    CONSTRAINT fk_notif_status FOREIGN KEY (status) REFERENCES gc_status_notificacao(codigo)
);

CREATE INDEX idx_notif_status_data ON gc_notificacao(status, data_agendamento);
CREATE INDEX idx_notif_parcela ON gc_notificacao(parcela_id);

COMMENT ON TABLE gc_notificacao IS 'Notificacoes enviadas aos compradores';

-- ============================================================================
-- TABELA: TEMPLATES DE NOTIFICACAO
-- ============================================================================
CREATE TABLE gc_template_notificacao (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome                 VARCHAR2(100) NOT NULL,
    codigo               VARCHAR2(30) DEFAULT 'CUSTOM',
    tipo                 VARCHAR2(20) NOT NULL,
    assunto              VARCHAR2(255),
    corpo                CLOB NOT NULL,
    corpo_html           CLOB,
    imobiliaria_id       NUMBER,
    ativo                NUMBER(1) DEFAULT 1,
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_template_tipo FOREIGN KEY (tipo) REFERENCES gc_tipo_notificacao(codigo),
    CONSTRAINT fk_template_codigo FOREIGN KEY (codigo) REFERENCES gc_tipo_template(codigo),
    CONSTRAINT fk_template_imob FOREIGN KEY (imobiliaria_id) REFERENCES gc_imobiliaria(id),
    CONSTRAINT uk_template UNIQUE (codigo, imobiliaria_id, tipo)
);

CREATE INDEX idx_template_codigo ON gc_template_notificacao(codigo);

COMMENT ON TABLE gc_template_notificacao IS 'Templates para notificacoes com suporte a TAGs';

-- ============================================================================
-- TABELA: CONTROLE DE ACESSO DE USUARIOS
-- ============================================================================
CREATE TABLE gc_acesso_usuario (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id           NUMBER NOT NULL,
    contabilidade_id     NUMBER NOT NULL,
    imobiliaria_id       NUMBER NOT NULL,
    pode_editar          NUMBER(1) DEFAULT 1,
    pode_excluir         NUMBER(1) DEFAULT 0,
    ativo                NUMBER(1) DEFAULT 1,
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_acesso_contab FOREIGN KEY (contabilidade_id) REFERENCES gc_contabilidade(id),
    CONSTRAINT fk_acesso_imob FOREIGN KEY (imobiliaria_id) REFERENCES gc_imobiliaria(id),
    CONSTRAINT uk_acesso_usuario UNIQUE (usuario_id, contabilidade_id, imobiliaria_id)
);

CREATE INDEX idx_acesso_usuario ON gc_acesso_usuario(usuario_id, ativo);
CREATE INDEX idx_acesso_contab ON gc_acesso_usuario(contabilidade_id, ativo);
CREATE INDEX idx_acesso_imob ON gc_acesso_usuario(imobiliaria_id, ativo);

COMMENT ON TABLE gc_acesso_usuario IS 'Controle de acesso de usuarios as imobiliarias';
COMMENT ON COLUMN gc_acesso_usuario.usuario_id IS 'ID do usuario do APEX (APEX_USERS ou APEX_WORKSPACE_APEX_USERS)';

COMMIT;

-- Fim do script DDL
