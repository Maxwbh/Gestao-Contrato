/*
==============================================================================
Sistema de Gestao de Contratos - Oracle 23c
Script DDL Complementar - Tabelas Adicionais
==============================================================================
Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
LinkedIn: https://www.linkedin.com/in/maxwbh/
GitHub: https://github.com/Maxwbh/
Empresa: M&S do Brasil LTDA
Site: msbrasil.inf.br
==============================================================================
Este script adiciona tabelas que estavam faltando no DDL principal:
- Log do sistema
- Auditoria
- Parâmetros gerais
- Boletos (separado de parcelas)
- Valores de índices
- Códigos de ocorrência CNAB
- Configuração de notificações automáticas
==============================================================================
*/

-- ============================================================================
-- TABELA: PARAMETROS DO SISTEMA
-- ============================================================================
CREATE TABLE gc_parametro (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave                VARCHAR2(100) NOT NULL UNIQUE,
    valor                VARCHAR2(4000),
    descricao            VARCHAR2(500),
    tipo                 VARCHAR2(20) DEFAULT 'STRING', -- STRING, NUMBER, BOOLEAN, JSON, DATE
    editavel             NUMBER(1) DEFAULT 1,
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT chk_param_tipo CHECK (tipo IN ('STRING', 'NUMBER', 'BOOLEAN', 'JSON', 'DATE'))
);

CREATE INDEX idx_param_chave ON gc_parametro(chave);

COMMENT ON TABLE gc_parametro IS 'Parametros gerais de configuracao do sistema';

-- Inserir parâmetros padrão
INSERT INTO gc_parametro (chave, valor, descricao, tipo) VALUES
    ('NOME_SISTEMA', 'Sistema de Gestão de Contratos', 'Nome exibido no sistema', 'STRING');
INSERT INTO gc_parametro (chave, valor, descricao, tipo) VALUES
    ('VERSAO', '1.0.0', 'Versao atual do sistema', 'STRING');
INSERT INTO gc_parametro (chave, valor, descricao, tipo) VALUES
    ('DIAS_ALERTA_VENCIMENTO', '7', 'Dias antes do vencimento para alertar', 'NUMBER');
INSERT INTO gc_parametro (chave, valor, descricao, tipo) VALUES
    ('PERCENTUAL_MULTA_PADRAO', '2.00', 'Percentual de multa padrao', 'NUMBER');
INSERT INTO gc_parametro (chave, valor, descricao, tipo) VALUES
    ('PERCENTUAL_JUROS_PADRAO', '0.033', 'Percentual de juros ao dia padrao', 'NUMBER');
INSERT INTO gc_parametro (chave, valor, descricao, tipo) VALUES
    ('DIAS_CARENCIA_ENCARGOS', '0', 'Dias de carencia antes de aplicar encargos', 'NUMBER');
INSERT INTO gc_parametro (chave, valor, descricao, tipo) VALUES
    ('FORMATO_NUMERO_CONTRATO', '{ANO}/{SEQ}', 'Formato do numero do contrato', 'STRING');
INSERT INTO gc_parametro (chave, valor, descricao, tipo) VALUES
    ('PROXIMO_SEQUENCIAL', '1', 'Proximo sequencial para numero de contrato', 'NUMBER');
INSERT INTO gc_parametro (chave, valor, descricao, tipo) VALUES
    ('TIMEZONE', 'America/Sao_Paulo', 'Fuso horario do sistema', 'STRING');
INSERT INTO gc_parametro (chave, valor, descricao, tipo) VALUES
    ('BRCOBRANCA_URL', 'http://localhost:9292', 'URL da API BRcobranca', 'STRING');
INSERT INTO gc_parametro (chave, valor, descricao, tipo) VALUES
    ('BRCOBRANCA_TIMEOUT', '30', 'Timeout da API BRcobranca em segundos', 'NUMBER');
INSERT INTO gc_parametro (chave, valor, descricao, tipo) VALUES
    ('BRCOBRANCA_RETENTATIVAS', '3', 'Numero de retentativas em caso de falha', 'NUMBER');

COMMIT;

-- ============================================================================
-- TABELA: LOG DO SISTEMA
-- ============================================================================
CREATE TABLE gc_log (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nivel                VARCHAR2(10) NOT NULL, -- DEBUG, INFO, WARNING, ERROR, CRITICAL
    processo             VARCHAR2(100) NOT NULL,
    mensagem             CLOB NOT NULL,
    dados                CLOB, -- JSON com dados adicionais
    usuario              VARCHAR2(100),
    ip_origem            VARCHAR2(45),
    user_agent           VARCHAR2(500),
    sessao_id            VARCHAR2(100),
    duracao_ms           NUMBER(10),
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT chk_log_nivel CHECK (nivel IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'))
);

CREATE INDEX idx_log_nivel ON gc_log(nivel);
CREATE INDEX idx_log_processo ON gc_log(processo);
CREATE INDEX idx_log_criado ON gc_log(criado_em);
CREATE INDEX idx_log_usuario ON gc_log(usuario);

COMMENT ON TABLE gc_log IS 'Log geral de eventos e erros do sistema';

-- Particionamento por data (opcional para produção)
-- ALTER TABLE gc_log MODIFY PARTITION BY RANGE (criado_em) INTERVAL (NUMTODSINTERVAL(30, 'DAY'))
-- (PARTITION p_inicial VALUES LESS THAN (TIMESTAMP '2024-01-01 00:00:00'));

-- ============================================================================
-- TABELA: LOG DE ERROS
-- ============================================================================
CREATE TABLE gc_log_erro (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    processo             VARCHAR2(100) NOT NULL,
    mensagem             CLOB NOT NULL,
    dados                CLOB,
    stack_trace          CLOB,
    usuario              VARCHAR2(100),
    resolvido            NUMBER(1) DEFAULT 0,
    data_resolucao       TIMESTAMP,
    resolvido_por        VARCHAR2(100),
    observacao_resolucao CLOB,
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT chk_erro_resolvido CHECK (resolvido IN (0, 1))
);

CREATE INDEX idx_log_erro_processo ON gc_log_erro(processo);
CREATE INDEX idx_log_erro_resolvido ON gc_log_erro(resolvido);
CREATE INDEX idx_log_erro_criado ON gc_log_erro(criado_em);

COMMENT ON TABLE gc_log_erro IS 'Log de erros do sistema para rastreamento e resolucao';

-- ============================================================================
-- TABELA: AUDITORIA
-- ============================================================================
CREATE TABLE gc_auditoria (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tabela               VARCHAR2(100) NOT NULL,
    operacao             VARCHAR2(10) NOT NULL, -- INSERT, UPDATE, DELETE
    registro_id          NUMBER NOT NULL,
    dados_antigos        CLOB, -- JSON com valores anteriores
    dados_novos          CLOB, -- JSON com valores novos
    campos_alterados     VARCHAR2(4000), -- Lista de campos alterados
    usuario              VARCHAR2(100),
    usuario_apex_id      NUMBER,
    ip_origem            VARCHAR2(45),
    aplicacao            VARCHAR2(100) DEFAULT 'APEX',
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT chk_audit_operacao CHECK (operacao IN ('INSERT', 'UPDATE', 'DELETE'))
);

CREATE INDEX idx_audit_tabela ON gc_auditoria(tabela);
CREATE INDEX idx_audit_operacao ON gc_auditoria(operacao);
CREATE INDEX idx_audit_registro ON gc_auditoria(tabela, registro_id);
CREATE INDEX idx_audit_usuario ON gc_auditoria(usuario);
CREATE INDEX idx_audit_criado ON gc_auditoria(criado_em);

COMMENT ON TABLE gc_auditoria IS 'Trilha de auditoria para rastreamento de alteracoes';

-- ============================================================================
-- TABELA: INDICES DE REAJUSTE (Cadastro Base)
-- ============================================================================
-- Nota: A tabela gc_indice_reajuste original armazena valores mensais
-- Criamos uma tabela separada para o cadastro dos índices

CREATE TABLE gc_indice (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sigla                VARCHAR2(10) NOT NULL UNIQUE,
    nome                 VARCHAR2(100) NOT NULL,
    descricao            VARCHAR2(500),
    fonte_padrao         VARCHAR2(100),
    url_fonte            VARCHAR2(500),
    ativo                NUMBER(1) DEFAULT 1,
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT chk_indice_ativo CHECK (ativo IN (0, 1))
);

CREATE INDEX idx_indice_sigla ON gc_indice(sigla);

COMMENT ON TABLE gc_indice IS 'Cadastro base dos indices de reajuste';

-- Inserir índices padrão
INSERT INTO gc_indice (sigla, nome, descricao, fonte_padrao) VALUES
    ('IPCA', 'Índice de Preços ao Consumidor Amplo', 'Principal índice de inflação do Brasil, medido pelo IBGE', 'IBGE');
INSERT INTO gc_indice (sigla, nome, descricao, fonte_padrao) VALUES
    ('IGPM', 'Índice Geral de Preços do Mercado', 'Calculado pela FGV, usado em contratos de aluguel', 'FGV');
INSERT INTO gc_indice (sigla, nome, descricao, fonte_padrao) VALUES
    ('INCC', 'Índice Nacional de Custo da Construção', 'Mede a variação de custos da construção civil', 'FGV');
INSERT INTO gc_indice (sigla, nome, descricao, fonte_padrao) VALUES
    ('IGPDI', 'Índice Geral de Preços - Disponibilidade Interna', 'Calculado pela FGV', 'FGV');
INSERT INTO gc_indice (sigla, nome, descricao, fonte_padrao) VALUES
    ('INPC', 'Índice Nacional de Preços ao Consumidor', 'Mede inflação para famílias de baixa renda', 'IBGE');
INSERT INTO gc_indice (sigla, nome, descricao, fonte_padrao) VALUES
    ('TR', 'Taxa Referencial', 'Taxa de referência do sistema financeiro', 'BACEN');
INSERT INTO gc_indice (sigla, nome, descricao, fonte_padrao) VALUES
    ('SELIC', 'Taxa SELIC', 'Taxa básica de juros da economia', 'BACEN');

COMMIT;

-- ============================================================================
-- TABELA: VALORES DOS INDICES (Histórico Mensal)
-- ============================================================================
CREATE TABLE gc_valor_indice (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    indice_id            NUMBER NOT NULL,
    data_referencia      DATE NOT NULL, -- Primeiro dia do mês
    valor                NUMBER(10,6) NOT NULL, -- Valor percentual do mês
    valor_acumulado_ano  NUMBER(12,6), -- Acumulado no ano
    valor_acumulado_12m  NUMBER(12,6), -- Acumulado 12 meses
    fonte                VARCHAR2(100),
    data_importacao      TIMESTAMP,
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_valor_indice FOREIGN KEY (indice_id) REFERENCES gc_indice(id),
    CONSTRAINT uk_valor_indice_ref UNIQUE (indice_id, data_referencia)
);

CREATE INDEX idx_valor_indice_data ON gc_valor_indice(indice_id, data_referencia);

COMMENT ON TABLE gc_valor_indice IS 'Valores mensais dos indices de reajuste';

-- ============================================================================
-- TABELA: BOLETOS (Separado de Parcelas)
-- ============================================================================
CREATE TABLE gc_boleto (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    parcela_id           NUMBER NOT NULL,
    conta_bancaria_id    NUMBER NOT NULL,
    -- Identificação
    nosso_numero         VARCHAR2(30) NOT NULL,
    numero_documento     VARCHAR2(30),
    -- Valores
    valor                NUMBER(12,2) NOT NULL,
    valor_desconto       NUMBER(12,2) DEFAULT 0,
    valor_multa          NUMBER(12,2) DEFAULT 0,
    valor_juros          NUMBER(12,2) DEFAULT 0,
    valor_pago           NUMBER(12,2),
    -- Datas
    vencimento           DATE NOT NULL,
    data_emissao         DATE DEFAULT SYSDATE,
    data_processamento   DATE,
    data_pagamento       DATE,
    data_credito         DATE,
    -- Códigos
    codigo_barras        VARCHAR2(50),
    linha_digitavel      VARCHAR2(60),
    -- PIX
    pix_copia_cola       CLOB,
    pix_qrcode_base64    CLOB,
    pix_txid             VARCHAR2(100),
    -- Arquivo
    arquivo_pdf          BLOB,
    arquivo_pdf_nome     VARCHAR2(255),
    -- Status
    status               VARCHAR2(20) DEFAULT 'PENDENTE', -- PENDENTE, REGISTRADO, PAGO, CANCELADO, VENCIDO, PROTESTADO
    registrado           NUMBER(1) DEFAULT 0,
    data_registro        TIMESTAMP,
    -- Remessa/Retorno
    remessa_id           NUMBER,
    retorno_id           NUMBER,
    codigo_ocorrencia    VARCHAR2(10),
    descricao_ocorrencia VARCHAR2(255),
    -- Instruções
    instrucao1           VARCHAR2(255),
    instrucao2           VARCHAR2(255),
    instrucao3           VARCHAR2(255),
    local_pagamento      VARCHAR2(255) DEFAULT 'Pagável em qualquer banco até o vencimento',
    -- Controle
    tentativas_registro  NUMBER(3) DEFAULT 0,
    erro_registro        CLOB,
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_boleto_parcela FOREIGN KEY (parcela_id) REFERENCES gc_parcela(id),
    CONSTRAINT fk_boleto_conta FOREIGN KEY (conta_bancaria_id) REFERENCES gc_conta_bancaria(id),
    CONSTRAINT fk_boleto_remessa FOREIGN KEY (remessa_id) REFERENCES gc_arquivo_remessa(id),
    CONSTRAINT fk_boleto_retorno FOREIGN KEY (retorno_id) REFERENCES gc_arquivo_retorno(id),
    CONSTRAINT chk_boleto_registrado CHECK (registrado IN (0, 1)),
    CONSTRAINT chk_boleto_status CHECK (status IN ('PENDENTE', 'REGISTRADO', 'PAGO', 'CANCELADO', 'VENCIDO', 'PROTESTADO', 'BAIXADO'))
);

CREATE INDEX idx_boleto_parcela ON gc_boleto(parcela_id);
CREATE INDEX idx_boleto_conta ON gc_boleto(conta_bancaria_id);
CREATE INDEX idx_boleto_nosso_numero ON gc_boleto(nosso_numero);
CREATE INDEX idx_boleto_vencimento ON gc_boleto(vencimento);
CREATE INDEX idx_boleto_status ON gc_boleto(status);
CREATE INDEX idx_boleto_remessa ON gc_boleto(remessa_id);

COMMENT ON TABLE gc_boleto IS 'Boletos gerados para as parcelas dos contratos';

-- ============================================================================
-- TABELA: CODIGOS DE OCORRENCIA CNAB
-- ============================================================================
CREATE TABLE gc_codigo_ocorrencia (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    banco                VARCHAR2(3) NOT NULL,
    layout               VARCHAR2(10) NOT NULL, -- CNAB_240, CNAB_400
    tipo                 VARCHAR2(20) NOT NULL, -- REMESSA, RETORNO
    codigo               VARCHAR2(10) NOT NULL,
    descricao            VARCHAR2(255) NOT NULL,
    tipo_ocorrencia      VARCHAR2(30), -- ENTRADA, CONFIRMACAO, LIQUIDACAO, BAIXA, REJEICAO, etc
    acao_automatica      VARCHAR2(50), -- PAGAR, CANCELAR, REJEITAR, etc
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_ocorr_banco FOREIGN KEY (banco) REFERENCES gc_banco(codigo),
    CONSTRAINT uk_codigo_ocorrencia UNIQUE (banco, layout, tipo, codigo)
);

CREATE INDEX idx_ocorr_banco ON gc_codigo_ocorrencia(banco, layout, tipo);

COMMENT ON TABLE gc_codigo_ocorrencia IS 'Codigos de ocorrencia CNAB por banco';

-- Inserir códigos básicos (exemplo Banco do Brasil CNAB 240)
INSERT INTO gc_codigo_ocorrencia (banco, layout, tipo, codigo, descricao, tipo_ocorrencia) VALUES
    ('001', 'CNAB_240', 'RETORNO', '02', 'Entrada Confirmada', 'CONFIRMACAO');
INSERT INTO gc_codigo_ocorrencia (banco, layout, tipo, codigo, descricao, tipo_ocorrencia) VALUES
    ('001', 'CNAB_240', 'RETORNO', '03', 'Entrada Rejeitada', 'REJEICAO');
INSERT INTO gc_codigo_ocorrencia (banco, layout, tipo, codigo, descricao, tipo_ocorrencia) VALUES
    ('001', 'CNAB_240', 'RETORNO', '06', 'Liquidação', 'LIQUIDACAO');
INSERT INTO gc_codigo_ocorrencia (banco, layout, tipo, codigo, descricao, tipo_ocorrencia) VALUES
    ('001', 'CNAB_240', 'RETORNO', '09', 'Baixa', 'BAIXA');
INSERT INTO gc_codigo_ocorrencia (banco, layout, tipo, codigo, descricao, tipo_ocorrencia) VALUES
    ('001', 'CNAB_240', 'RETORNO', '17', 'Liquidação após baixa', 'LIQUIDACAO');

-- Bradesco
INSERT INTO gc_codigo_ocorrencia (banco, layout, tipo, codigo, descricao, tipo_ocorrencia) VALUES
    ('237', 'CNAB_240', 'RETORNO', '02', 'Entrada Confirmada', 'CONFIRMACAO');
INSERT INTO gc_codigo_ocorrencia (banco, layout, tipo, codigo, descricao, tipo_ocorrencia) VALUES
    ('237', 'CNAB_240', 'RETORNO', '03', 'Entrada Rejeitada', 'REJEICAO');
INSERT INTO gc_codigo_ocorrencia (banco, layout, tipo, codigo, descricao, tipo_ocorrencia) VALUES
    ('237', 'CNAB_240', 'RETORNO', '06', 'Liquidação Normal', 'LIQUIDACAO');
INSERT INTO gc_codigo_ocorrencia (banco, layout, tipo, codigo, descricao, tipo_ocorrencia) VALUES
    ('237', 'CNAB_240', 'RETORNO', '09', 'Baixado Automaticamente', 'BAIXA');

-- Sicoob
INSERT INTO gc_codigo_ocorrencia (banco, layout, tipo, codigo, descricao, tipo_ocorrencia) VALUES
    ('756', 'CNAB_240', 'RETORNO', '02', 'Entrada Confirmada', 'CONFIRMACAO');
INSERT INTO gc_codigo_ocorrencia (banco, layout, tipo, codigo, descricao, tipo_ocorrencia) VALUES
    ('756', 'CNAB_240', 'RETORNO', '03', 'Entrada Rejeitada', 'REJEICAO');
INSERT INTO gc_codigo_ocorrencia (banco, layout, tipo, codigo, descricao, tipo_ocorrencia) VALUES
    ('756', 'CNAB_240', 'RETORNO', '06', 'Liquidação', 'LIQUIDACAO');
INSERT INTO gc_codigo_ocorrencia (banco, layout, tipo, codigo, descricao, tipo_ocorrencia) VALUES
    ('756', 'CNAB_240', 'RETORNO', '09', 'Baixa', 'BAIXA');

COMMIT;

-- ============================================================================
-- TABELA: DETALHE DO RETORNO CNAB
-- ============================================================================
CREATE TABLE gc_retorno_detalhe (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    retorno_id           NUMBER NOT NULL,
    banco                VARCHAR2(3) NOT NULL,
    -- Identificação
    nosso_numero         VARCHAR2(30) NOT NULL,
    numero_documento     VARCHAR2(30),
    -- Ocorrência
    codigo_ocorrencia    VARCHAR2(10) NOT NULL,
    -- Valores
    valor_titulo         NUMBER(12,2),
    valor_pago           NUMBER(12,2),
    valor_juros          NUMBER(12,2),
    valor_multa          NUMBER(12,2),
    valor_desconto       NUMBER(12,2),
    valor_abatimento     NUMBER(12,2),
    valor_iof            NUMBER(12,2),
    valor_tarifa         NUMBER(12,2),
    -- Datas
    data_ocorrencia      DATE,
    data_credito         DATE,
    data_pagamento       DATE,
    -- Processamento
    status               VARCHAR2(20) DEFAULT 'PENDENTE', -- PENDENTE, PROCESSADO, ERRO
    boleto_id            NUMBER,
    parcela_id           NUMBER,
    mensagem_erro        CLOB,
    processado_em        TIMESTAMP,
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_ret_det_retorno FOREIGN KEY (retorno_id) REFERENCES gc_arquivo_retorno(id) ON DELETE CASCADE,
    CONSTRAINT fk_ret_det_banco FOREIGN KEY (banco) REFERENCES gc_banco(codigo),
    CONSTRAINT fk_ret_det_boleto FOREIGN KEY (boleto_id) REFERENCES gc_boleto(id),
    CONSTRAINT fk_ret_det_parcela FOREIGN KEY (parcela_id) REFERENCES gc_parcela(id)
);

CREATE INDEX idx_ret_det_retorno ON gc_retorno_detalhe(retorno_id);
CREATE INDEX idx_ret_det_nosso_num ON gc_retorno_detalhe(nosso_numero);
CREATE INDEX idx_ret_det_status ON gc_retorno_detalhe(status);

COMMENT ON TABLE gc_retorno_detalhe IS 'Detalhes (registros) do arquivo de retorno CNAB';

-- ============================================================================
-- TABELA: CONFIGURACAO DE NOTIFICACOES AUTOMATICAS
-- ============================================================================
CREATE TABLE gc_config_notificacao_auto (
    id                           NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    imobiliaria_id               NUMBER NOT NULL,
    -- Antes do vencimento
    dias_antes_vencimento        NUMBER(3) DEFAULT 5,
    enviar_antes_vencimento      NUMBER(1) DEFAULT 1,
    template_antes_id            NUMBER,
    -- No dia do vencimento
    enviar_no_vencimento         NUMBER(1) DEFAULT 1,
    template_vencimento_id       NUMBER,
    -- Após vencimento (cobrança)
    dias_apos_vencimento         NUMBER(3) DEFAULT 3,
    enviar_apos_vencimento       NUMBER(1) DEFAULT 1,
    template_cobranca_id         NUMBER,
    -- Recobrança
    intervalo_recobranca         NUMBER(3) DEFAULT 7,
    maximo_recobrancas           NUMBER(3) DEFAULT 3,
    -- Canais
    usar_email                   NUMBER(1) DEFAULT 1,
    usar_sms                     NUMBER(1) DEFAULT 0,
    usar_whatsapp                NUMBER(1) DEFAULT 0,
    -- Controle
    ativo                        NUMBER(1) DEFAULT 1,
    criado_em                    TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em                TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT fk_cfg_notif_imob FOREIGN KEY (imobiliaria_id) REFERENCES gc_imobiliaria(id),
    CONSTRAINT fk_cfg_notif_tpl_antes FOREIGN KEY (template_antes_id) REFERENCES gc_template_notificacao(id),
    CONSTRAINT fk_cfg_notif_tpl_venc FOREIGN KEY (template_vencimento_id) REFERENCES gc_template_notificacao(id),
    CONSTRAINT fk_cfg_notif_tpl_cobr FOREIGN KEY (template_cobranca_id) REFERENCES gc_template_notificacao(id),
    CONSTRAINT uk_cfg_notif_imob UNIQUE (imobiliaria_id)
);

COMMENT ON TABLE gc_config_notificacao_auto IS 'Configuracao de envio automatico de notificacoes por imobiliaria';

-- ============================================================================
-- TABELA: FILA DE JOBS/TAREFAS
-- ============================================================================
CREATE TABLE gc_job_queue (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo                 VARCHAR2(50) NOT NULL, -- GERAR_BOLETO, ENVIAR_REMESSA, PROCESSAR_RETORNO, ENVIAR_NOTIFICACAO, APLICAR_REAJUSTE
    prioridade           NUMBER(2) DEFAULT 5, -- 1=Alta, 5=Normal, 10=Baixa
    status               VARCHAR2(20) DEFAULT 'PENDENTE', -- PENDENTE, PROCESSANDO, CONCLUIDO, ERRO, CANCELADO
    dados_entrada        CLOB, -- JSON com parâmetros
    dados_saida          CLOB, -- JSON com resultado
    erro_mensagem        CLOB,
    tentativas           NUMBER(3) DEFAULT 0,
    max_tentativas       NUMBER(3) DEFAULT 3,
    agendado_para        TIMESTAMP DEFAULT SYSTIMESTAMP,
    iniciado_em          TIMESTAMP,
    concluido_em         TIMESTAMP,
    criado_em            TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT chk_job_status CHECK (status IN ('PENDENTE', 'PROCESSANDO', 'CONCLUIDO', 'ERRO', 'CANCELADO'))
);

CREATE INDEX idx_job_status ON gc_job_queue(status, prioridade, agendado_para);
CREATE INDEX idx_job_tipo ON gc_job_queue(tipo);

COMMENT ON TABLE gc_job_queue IS 'Fila de tarefas assincronas do sistema';

-- ============================================================================
-- ATUALIZAR TABELA gc_banco COM CAMPO ATIVO
-- ============================================================================
ALTER TABLE gc_banco ADD (
    nome_curto   VARCHAR2(30),
    ativo        NUMBER(1) DEFAULT 1
);

UPDATE gc_banco SET nome_curto = SUBSTR(nome, 1, 30), ativo = 1;

COMMENT ON COLUMN gc_banco.nome_curto IS 'Nome abreviado do banco';
COMMENT ON COLUMN gc_banco.ativo IS 'Indica se o banco esta ativo para uso';

-- ============================================================================
-- ATUALIZAR TABELA gc_contabilidade COM CAMPOS FALTANTES
-- ============================================================================
ALTER TABLE gc_contabilidade ADD (
    nome_fantasia        VARCHAR2(200),
    inscricao_estadual   VARCHAR2(20),
    logradouro           VARCHAR2(200),
    numero               VARCHAR2(10),
    complemento          VARCHAR2(100),
    bairro               VARCHAR2(100),
    cidade               VARCHAR2(100),
    estado               VARCHAR2(2),
    cep                  VARCHAR2(10),
    crc                  VARCHAR2(30)
);

-- Copiar nome para nome_fantasia se vazio
UPDATE gc_contabilidade SET nome_fantasia = nome WHERE nome_fantasia IS NULL;

-- ============================================================================
-- ATUALIZAR TABELA gc_imobiliaria COM CAMPOS FALTANTES
-- ============================================================================
ALTER TABLE gc_imobiliaria ADD (
    celular              VARCHAR2(20),
    site                 VARCHAR2(255),
    creci                VARCHAR2(30),
    percentual_multa     NUMBER(5,2) DEFAULT 2.00,
    percentual_juros_dia NUMBER(8,6) DEFAULT 0.033,
    dias_carencia        NUMBER(3) DEFAULT 0
);

-- ============================================================================
-- ATUALIZAR TABELA gc_conta_bancaria COM CAMPOS FALTANTES
-- ============================================================================
ALTER TABLE gc_conta_bancaria ADD (
    agencia_dv           VARCHAR2(2),
    conta_dv             VARCHAR2(2),
    variacao_carteira    VARCHAR2(5),
    codigo_cedente       VARCHAR2(20),
    nosso_numero_inicio  NUMBER(15) DEFAULT 1,
    nosso_numero_fim     NUMBER(15) DEFAULT 99999999999
);

-- ============================================================================
-- ATUALIZAR TABELA gc_imovel COM CAMPOS FALTANTES
-- ============================================================================
ALTER TABLE gc_imovel ADD (
    quadra               VARCHAR2(20),
    lote                 VARCHAR2(20),
    cartorio             VARCHAR2(200)
);

-- ============================================================================
-- ATUALIZAR TABELA gc_comprador COM FK IMOBILIARIA
-- ============================================================================
ALTER TABLE gc_comprador ADD (
    imobiliaria_id       NUMBER,
    orgao_emissor        VARCHAR2(20)
);

ALTER TABLE gc_comprador ADD CONSTRAINT fk_compr_imob
    FOREIGN KEY (imobiliaria_id) REFERENCES gc_imobiliaria(id);

CREATE INDEX idx_compr_imob ON gc_comprador(imobiliaria_id);

-- ============================================================================
-- ATUALIZAR TABELA gc_contrato COM CAMPOS FALTANTES
-- ============================================================================
ALTER TABLE gc_contrato ADD (
    quantidade_parcelas  NUMBER(5),
    valor_parcela_atual  NUMBER(12,2),
    primeiro_vencimento  DATE,
    ultimo_vencimento    DATE,
    indice_reajuste      VARCHAR2(10),
    periodicidade_reajuste NUMBER(3) DEFAULT 12,
    proximo_reajuste     DATE
);

-- Copiar dados existentes
UPDATE gc_contrato SET
    quantidade_parcelas = numero_parcelas,
    valor_parcela_atual = valor_parcela_original,
    primeiro_vencimento = data_primeiro_vencimento,
    indice_reajuste = tipo_correcao
WHERE quantidade_parcelas IS NULL;

-- ============================================================================
-- ATUALIZAR TABELA gc_parcela COM CAMPOS FALTANTES
-- ============================================================================
ALTER TABLE gc_parcela ADD (
    valor_parcela        NUMBER(12,2),
    status               VARCHAR2(20) DEFAULT 'PENDENTE',
    boleto_gerado        NUMBER(1) DEFAULT 0
);

-- Copiar dados existentes
UPDATE gc_parcela SET
    valor_parcela = valor_atual,
    status = CASE WHEN pago = 1 THEN 'PAGO' ELSE 'PENDENTE' END,
    boleto_gerado = CASE WHEN nosso_numero IS NOT NULL THEN 1 ELSE 0 END
WHERE valor_parcela IS NULL;

-- ============================================================================
-- ATUALIZAR TABELA gc_notificacao COM CAMPOS FALTANTES
-- ============================================================================
ALTER TABLE gc_notificacao ADD (
    imobiliaria_id       NUMBER,
    comprador_id         NUMBER,
    contrato_id          NUMBER,
    erro_mensagem        CLOB
);

ALTER TABLE gc_notificacao ADD CONSTRAINT fk_notif_imob
    FOREIGN KEY (imobiliaria_id) REFERENCES gc_imobiliaria(id);
ALTER TABLE gc_notificacao ADD CONSTRAINT fk_notif_comprador
    FOREIGN KEY (comprador_id) REFERENCES gc_comprador(id);
ALTER TABLE gc_notificacao ADD CONSTRAINT fk_notif_contrato
    FOREIGN KEY (contrato_id) REFERENCES gc_contrato(id);

-- ============================================================================
-- TABELA: SESSAO/LOGIN DE USUARIOS
-- ============================================================================
CREATE TABLE gc_sessao_usuario (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario              VARCHAR2(100) NOT NULL,
    apex_session_id      NUMBER,
    ip_origem            VARCHAR2(45),
    user_agent           VARCHAR2(500),
    data_login           TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    data_logout          TIMESTAMP,
    data_ultimo_acesso   TIMESTAMP DEFAULT SYSTIMESTAMP,
    ativa                NUMBER(1) DEFAULT 1,
    CONSTRAINT chk_sessao_ativa CHECK (ativa IN (0, 1))
);

CREATE INDEX idx_sessao_usuario ON gc_sessao_usuario(usuario, ativa);
CREATE INDEX idx_sessao_apex ON gc_sessao_usuario(apex_session_id);

COMMENT ON TABLE gc_sessao_usuario IS 'Registro de sessoes de login dos usuarios';

COMMIT;

-- ============================================================================
-- TRIGGERS DE AUDITORIA
-- ============================================================================

-- Trigger genérico para auditoria (exemplo para gc_contrato)
CREATE OR REPLACE TRIGGER trg_gc_contrato_audit
    AFTER INSERT OR UPDATE OR DELETE ON gc_contrato
    FOR EACH ROW
DECLARE
    v_operacao VARCHAR2(10);
    v_dados_antigos CLOB;
    v_dados_novos CLOB;
    v_campos_alterados VARCHAR2(4000);
BEGIN
    IF INSERTING THEN
        v_operacao := 'INSERT';
        v_dados_novos := '{"id":' || :NEW.id || ',"numero_contrato":"' || :NEW.numero_contrato || '"}';
    ELSIF UPDATING THEN
        v_operacao := 'UPDATE';
        v_dados_antigos := '{"id":' || :OLD.id || ',"numero_contrato":"' || :OLD.numero_contrato || '"}';
        v_dados_novos := '{"id":' || :NEW.id || ',"numero_contrato":"' || :NEW.numero_contrato || '"}';
        -- Detectar campos alterados
        v_campos_alterados := '';
        IF :OLD.status != :NEW.status THEN v_campos_alterados := v_campos_alterados || 'status,'; END IF;
        IF :OLD.valor_total != :NEW.valor_total THEN v_campos_alterados := v_campos_alterados || 'valor_total,'; END IF;
        v_campos_alterados := RTRIM(v_campos_alterados, ',');
    ELSIF DELETING THEN
        v_operacao := 'DELETE';
        v_dados_antigos := '{"id":' || :OLD.id || ',"numero_contrato":"' || :OLD.numero_contrato || '"}';
    END IF;

    INSERT INTO gc_auditoria (tabela, operacao, registro_id, dados_antigos, dados_novos, campos_alterados, usuario)
    VALUES ('GC_CONTRATO', v_operacao, NVL(:NEW.id, :OLD.id), v_dados_antigos, v_dados_novos, v_campos_alterados,
            NVL(SYS_CONTEXT('APEX$SESSION', 'APP_USER'), USER));
EXCEPTION
    WHEN OTHERS THEN
        NULL; -- Não falhar a operação principal por erro na auditoria
END;
/

-- ============================================================================
-- PROCEDURE: REGISTRAR LOG
-- ============================================================================
CREATE OR REPLACE PROCEDURE prc_registrar_log(
    p_nivel      IN VARCHAR2,
    p_processo   IN VARCHAR2,
    p_mensagem   IN CLOB,
    p_dados      IN CLOB DEFAULT NULL
) AS
    PRAGMA AUTONOMOUS_TRANSACTION;
BEGIN
    INSERT INTO gc_log (nivel, processo, mensagem, dados, usuario, sessao_id)
    VALUES (
        p_nivel,
        p_processo,
        p_mensagem,
        p_dados,
        NVL(SYS_CONTEXT('APEX$SESSION', 'APP_USER'), USER),
        SYS_CONTEXT('APEX$SESSION', 'APP_SESSION')
    );
    COMMIT;
EXCEPTION
    WHEN OTHERS THEN
        ROLLBACK;
END prc_registrar_log;
/

-- ============================================================================
-- PROCEDURE: REGISTRAR ERRO
-- ============================================================================
CREATE OR REPLACE PROCEDURE prc_registrar_erro(
    p_processo   IN VARCHAR2,
    p_mensagem   IN CLOB,
    p_dados      IN CLOB DEFAULT NULL
) AS
    PRAGMA AUTONOMOUS_TRANSACTION;
BEGIN
    INSERT INTO gc_log_erro (processo, mensagem, dados, stack_trace, usuario)
    VALUES (
        p_processo,
        p_mensagem,
        p_dados,
        DBMS_UTILITY.FORMAT_ERROR_BACKTRACE,
        NVL(SYS_CONTEXT('APEX$SESSION', 'APP_USER'), USER)
    );
    COMMIT;
EXCEPTION
    WHEN OTHERS THEN
        ROLLBACK;
END prc_registrar_erro;
/

COMMIT;

-- Fim do script DDL complementar

