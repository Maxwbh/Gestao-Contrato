/*
==============================================================================
Sistema de Gestao de Contratos - Migracao para Oracle 23c
Script de Views - Consultas para APEX
==============================================================================
Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Linkedin: https://www.linkedin.com/in/maxwbh/
GitHub: https://github.com/Maxwbh/
Empresa: M&S do Brasil LTDA
Site: msbrasil.inf.br
==============================================================================
*/

-- ============================================================================
-- VIEW: Contratos com detalhes completos
-- ============================================================================
CREATE OR REPLACE VIEW vw_contrato_detalhado AS
SELECT
    c.id,
    c.numero_contrato,
    c.data_contrato,
    c.data_primeiro_vencimento,
    c.valor_total,
    c.valor_entrada,
    c.valor_financiado,
    c.valor_parcela_original,
    c.numero_parcelas,
    c.dia_vencimento,
    c.percentual_juros_mora,
    c.percentual_multa,
    c.tipo_correcao,
    tc.descricao AS tipo_correcao_desc,
    c.prazo_reajuste_meses,
    c.data_ultimo_reajuste,
    c.status,
    sc.descricao AS status_desc,
    c.observacoes,
    c.criado_em,
    c.atualizado_em,
    -- Imovel
    i.id AS imovel_id,
    i.identificacao AS imovel_identificacao,
    i.loteamento AS imovel_loteamento,
    i.tipo AS imovel_tipo,
    ti.descricao AS imovel_tipo_desc,
    i.cidade AS imovel_cidade,
    i.estado AS imovel_estado,
    i.area AS imovel_area,
    -- Comprador
    comp.id AS comprador_id,
    comp.nome AS comprador_nome,
    comp.tipo_pessoa AS comprador_tipo,
    COALESCE(comp.cpf, comp.cnpj) AS comprador_documento,
    comp.email AS comprador_email,
    comp.celular AS comprador_celular,
    -- Imobiliaria
    imob.id AS imobiliaria_id,
    imob.nome AS imobiliaria_nome,
    imob.cnpj AS imobiliaria_cnpj,
    -- Contabilidade
    contab.id AS contabilidade_id,
    contab.nome AS contabilidade_nome,
    -- Calculos
    pkg_contrato.calcular_progresso(c.id) AS progresso_pagamento,
    pkg_contrato.calcular_valor_pago(c.id) AS valor_pago_total,
    pkg_contrato.calcular_saldo_devedor(c.id) AS saldo_devedor,
    pkg_contrato.obter_data_proximo_reajuste(c.id) AS data_proximo_reajuste,
    -- Estatisticas de parcelas
    (SELECT COUNT(*) FROM gc_parcela p WHERE p.contrato_id = c.id) AS total_parcelas,
    (SELECT COUNT(*) FROM gc_parcela p WHERE p.contrato_id = c.id AND p.pago = 1) AS parcelas_pagas,
    (SELECT COUNT(*) FROM gc_parcela p WHERE p.contrato_id = c.id AND p.pago = 0 AND p.data_vencimento < TRUNC(SYSDATE)) AS parcelas_vencidas
FROM gc_contrato c
JOIN gc_imovel i ON i.id = c.imovel_id
JOIN gc_comprador comp ON comp.id = c.comprador_id
JOIN gc_imobiliaria imob ON imob.id = c.imobiliaria_id
JOIN gc_contabilidade contab ON contab.id = imob.contabilidade_id
LEFT JOIN gc_tipo_correcao tc ON tc.codigo = c.tipo_correcao
LEFT JOIN gc_status_contrato sc ON sc.codigo = c.status
LEFT JOIN gc_tipo_imovel ti ON ti.codigo = i.tipo;

COMMENT ON VIEW vw_contrato_detalhado IS 'View completa de contratos com todos os relacionamentos';

-- ============================================================================
-- VIEW: Parcelas com detalhes
-- ============================================================================
CREATE OR REPLACE VIEW vw_parcela_detalhada AS
SELECT
    p.id,
    p.contrato_id,
    c.numero_contrato,
    p.numero_parcela,
    p.numero_parcela || '/' || c.numero_parcelas AS parcela_formatada,
    p.data_vencimento,
    p.valor_original,
    p.valor_atual,
    p.valor_juros,
    p.valor_multa,
    p.valor_desconto,
    p.valor_atual + NVL(p.valor_juros, 0) + NVL(p.valor_multa, 0) - NVL(p.valor_desconto, 0) AS valor_total,
    p.pago,
    CASE p.pago WHEN 1 THEN 'Pago' ELSE 'Pendente' END AS status_pagamento,
    p.data_pagamento,
    p.valor_pago,
    p.observacoes,
    -- Boleto
    p.nosso_numero,
    p.numero_documento,
    p.codigo_barras,
    p.linha_digitavel,
    p.status_boleto,
    sb.descricao AS status_boleto_desc,
    p.data_geracao_boleto,
    p.data_registro_boleto,
    p.valor_boleto,
    p.pix_copia_cola,
    -- Calculos
    CASE
        WHEN p.pago = 1 THEN 0
        WHEN TRUNC(SYSDATE) > p.data_vencimento THEN TRUNC(SYSDATE) - p.data_vencimento
        ELSE 0
    END AS dias_atraso,
    CASE
        WHEN p.pago = 0 AND TRUNC(SYSDATE) > p.data_vencimento THEN 'Vencida'
        WHEN p.pago = 0 AND TRUNC(SYSDATE) = p.data_vencimento THEN 'Vence Hoje'
        WHEN p.pago = 0 AND TRUNC(SYSDATE) + 5 >= p.data_vencimento THEN 'Proxima a Vencer'
        WHEN p.pago = 0 THEN 'A Vencer'
        ELSE 'Paga'
    END AS situacao,
    -- Comprador
    comp.id AS comprador_id,
    comp.nome AS comprador_nome,
    comp.email AS comprador_email,
    comp.celular AS comprador_celular,
    -- Imobiliaria
    imob.id AS imobiliaria_id,
    imob.nome AS imobiliaria_nome,
    p.criado_em,
    p.atualizado_em
FROM gc_parcela p
JOIN gc_contrato c ON c.id = p.contrato_id
JOIN gc_comprador comp ON comp.id = c.comprador_id
JOIN gc_imobiliaria imob ON imob.id = c.imobiliaria_id
LEFT JOIN gc_status_boleto sb ON sb.codigo = p.status_boleto;

COMMENT ON VIEW vw_parcela_detalhada IS 'View completa de parcelas com calculos e relacionamentos';

-- ============================================================================
-- VIEW: Parcelas vencidas (para cobranca)
-- ============================================================================
CREATE OR REPLACE VIEW vw_parcelas_vencidas AS
SELECT
    p.*,
    comp.nome AS comprador_nome,
    comp.email AS comprador_email,
    comp.celular AS comprador_celular,
    comp.notificar_email,
    comp.notificar_sms,
    comp.notificar_whatsapp,
    c.numero_contrato,
    imob.nome AS imobiliaria_nome
FROM vw_parcela_detalhada p
JOIN gc_contrato c ON c.id = p.contrato_id
JOIN gc_comprador comp ON comp.id = c.comprador_id
JOIN gc_imobiliaria imob ON imob.id = c.imobiliaria_id
WHERE p.pago = 0
  AND p.data_vencimento < TRUNC(SYSDATE)
ORDER BY p.dias_atraso DESC, p.data_vencimento;

COMMENT ON VIEW vw_parcelas_vencidas IS 'Parcelas vencidas para cobranca';

-- ============================================================================
-- VIEW: Parcelas a vencer (proximos 30 dias)
-- ============================================================================
CREATE OR REPLACE VIEW vw_parcelas_a_vencer AS
SELECT *
FROM vw_parcela_detalhada
WHERE pago = 0
  AND data_vencimento BETWEEN TRUNC(SYSDATE) AND TRUNC(SYSDATE) + 30
ORDER BY data_vencimento;

COMMENT ON VIEW vw_parcelas_a_vencer IS 'Parcelas a vencer nos proximos 30 dias';

-- ============================================================================
-- VIEW: Dashboard - Resumo por imobiliaria
-- ============================================================================
CREATE OR REPLACE VIEW vw_dashboard_imobiliaria AS
SELECT
    imob.id AS imobiliaria_id,
    imob.nome AS imobiliaria_nome,
    contab.nome AS contabilidade_nome,
    -- Contratos
    COUNT(DISTINCT c.id) AS total_contratos,
    SUM(CASE WHEN c.status = 'ATIVO' THEN 1 ELSE 0 END) AS contratos_ativos,
    SUM(CASE WHEN c.status = 'QUITADO' THEN 1 ELSE 0 END) AS contratos_quitados,
    SUM(CASE WHEN c.status = 'CANCELADO' THEN 1 ELSE 0 END) AS contratos_cancelados,
    -- Valores
    SUM(c.valor_total) AS valor_total_contratos,
    SUM(c.valor_financiado) AS valor_total_financiado,
    -- Parcelas
    COUNT(p.id) AS total_parcelas,
    SUM(CASE WHEN p.pago = 1 THEN 1 ELSE 0 END) AS parcelas_pagas,
    SUM(CASE WHEN p.pago = 0 AND p.data_vencimento < TRUNC(SYSDATE) THEN 1 ELSE 0 END) AS parcelas_vencidas,
    SUM(CASE WHEN p.pago = 0 AND p.data_vencimento >= TRUNC(SYSDATE) THEN 1 ELSE 0 END) AS parcelas_a_vencer,
    -- Valores recebidos
    NVL(SUM(CASE WHEN p.pago = 1 THEN p.valor_pago ELSE 0 END), 0) AS valor_recebido,
    NVL(SUM(CASE WHEN p.pago = 0 THEN p.valor_atual ELSE 0 END), 0) AS valor_a_receber,
    NVL(SUM(CASE WHEN p.pago = 0 AND p.data_vencimento < TRUNC(SYSDATE) THEN p.valor_atual ELSE 0 END), 0) AS valor_vencido,
    -- Imoveis
    (SELECT COUNT(*) FROM gc_imovel i WHERE i.imobiliaria_id = imob.id AND i.ativo = 1) AS total_imoveis,
    (SELECT COUNT(*) FROM gc_imovel i WHERE i.imobiliaria_id = imob.id AND i.disponivel = 1 AND i.ativo = 1) AS imoveis_disponiveis
FROM gc_imobiliaria imob
JOIN gc_contabilidade contab ON contab.id = imob.contabilidade_id
LEFT JOIN gc_contrato c ON c.imobiliaria_id = imob.id
LEFT JOIN gc_parcela p ON p.contrato_id = c.id
WHERE imob.ativo = 1
GROUP BY imob.id, imob.nome, contab.nome;

COMMENT ON VIEW vw_dashboard_imobiliaria IS 'Resumo dashboard por imobiliaria';

-- ============================================================================
-- VIEW: Boletos gerados
-- ============================================================================
CREATE OR REPLACE VIEW vw_boletos AS
SELECT
    p.id AS parcela_id,
    p.contrato_id,
    c.numero_contrato,
    p.numero_parcela,
    p.nosso_numero,
    p.numero_documento,
    p.data_vencimento,
    p.valor_boleto,
    p.status_boleto,
    sb.descricao AS status_desc,
    p.data_geracao_boleto,
    p.data_registro_boleto,
    p.data_pagamento_boleto,
    p.valor_pago_boleto,
    p.codigo_barras,
    p.linha_digitavel,
    p.pix_copia_cola,
    p.motivo_rejeicao,
    -- Conta bancaria
    cb.id AS conta_bancaria_id,
    b.nome AS banco_nome,
    cb.agencia,
    cb.conta,
    -- Comprador
    comp.nome AS comprador_nome,
    COALESCE(comp.cpf, comp.cnpj) AS comprador_documento,
    -- Imobiliaria
    imob.nome AS imobiliaria_nome
FROM gc_parcela p
JOIN gc_contrato c ON c.id = p.contrato_id
JOIN gc_comprador comp ON comp.id = c.comprador_id
JOIN gc_imobiliaria imob ON imob.id = c.imobiliaria_id
LEFT JOIN gc_conta_bancaria cb ON cb.id = p.conta_bancaria_id
LEFT JOIN gc_banco b ON b.codigo = cb.banco
LEFT JOIN gc_status_boleto sb ON sb.codigo = p.status_boleto
WHERE p.nosso_numero IS NOT NULL;

COMMENT ON VIEW vw_boletos IS 'Boletos gerados com detalhes';

-- ============================================================================
-- VIEW: Arquivos CNAB Remessa
-- ============================================================================
CREATE OR REPLACE VIEW vw_arquivos_remessa AS
SELECT
    ar.id,
    ar.numero_remessa,
    ar.layout,
    ar.arquivo_nome,
    ar.status,
    ar.data_geracao,
    ar.data_envio,
    ar.quantidade_boletos,
    ar.valor_total,
    ar.observacoes,
    ar.erro_mensagem,
    -- Conta bancaria
    cb.id AS conta_bancaria_id,
    b.nome AS banco_nome,
    cb.agencia,
    cb.conta,
    cb.descricao AS conta_descricao,
    -- Imobiliaria
    imob.id AS imobiliaria_id,
    imob.nome AS imobiliaria_nome
FROM gc_arquivo_remessa ar
JOIN gc_conta_bancaria cb ON cb.id = ar.conta_bancaria_id
JOIN gc_banco b ON b.codigo = cb.banco
JOIN gc_imobiliaria imob ON imob.id = cb.imobiliaria_id
ORDER BY ar.data_geracao DESC;

COMMENT ON VIEW vw_arquivos_remessa IS 'Arquivos de remessa CNAB';

-- ============================================================================
-- VIEW: Arquivos CNAB Retorno
-- ============================================================================
CREATE OR REPLACE VIEW vw_arquivos_retorno AS
SELECT
    ar.id,
    ar.arquivo_nome,
    ar.layout,
    ar.status,
    ar.data_upload,
    ar.data_processamento,
    ar.total_registros,
    ar.registros_processados,
    ar.registros_erro,
    ar.valor_total_pago,
    ar.observacoes,
    ar.erro_mensagem,
    -- Conta bancaria
    cb.id AS conta_bancaria_id,
    b.nome AS banco_nome,
    cb.agencia,
    cb.conta,
    cb.descricao AS conta_descricao,
    -- Imobiliaria
    imob.id AS imobiliaria_id,
    imob.nome AS imobiliaria_nome
FROM gc_arquivo_retorno ar
JOIN gc_conta_bancaria cb ON cb.id = ar.conta_bancaria_id
JOIN gc_banco b ON b.codigo = cb.banco
JOIN gc_imobiliaria imob ON imob.id = cb.imobiliaria_id
ORDER BY ar.data_upload DESC;

COMMENT ON VIEW vw_arquivos_retorno IS 'Arquivos de retorno CNAB';

-- ============================================================================
-- VIEW: Notificacoes pendentes
-- ============================================================================
CREATE OR REPLACE VIEW vw_notificacoes_pendentes AS
SELECT
    n.id,
    n.tipo,
    tn.descricao AS tipo_desc,
    n.destinatario,
    n.assunto,
    n.mensagem,
    n.status,
    sn.descricao AS status_desc,
    n.data_agendamento,
    n.tentativas,
    n.erro_mensagem,
    -- Parcela
    p.id AS parcela_id,
    p.numero_parcela,
    p.data_vencimento,
    c.numero_contrato,
    comp.nome AS comprador_nome
FROM gc_notificacao n
LEFT JOIN gc_parcela p ON p.id = n.parcela_id
LEFT JOIN gc_contrato c ON c.id = p.contrato_id
LEFT JOIN gc_comprador comp ON comp.id = c.comprador_id
LEFT JOIN gc_tipo_notificacao tn ON tn.codigo = n.tipo
LEFT JOIN gc_status_notificacao sn ON sn.codigo = n.status
WHERE n.status IN ('PENDENTE', 'ERRO')
ORDER BY n.data_agendamento;

COMMENT ON VIEW vw_notificacoes_pendentes IS 'Notificacoes pendentes de envio';

-- ============================================================================
-- VIEW: Indices de reajuste
-- ============================================================================
CREATE OR REPLACE VIEW vw_indices_reajuste AS
SELECT
    ir.id,
    ir.tipo_indice,
    tc.descricao AS tipo_indice_desc,
    ir.ano,
    ir.mes,
    TO_CHAR(ir.mes, '00') || '/' || ir.ano AS periodo,
    ir.valor,
    ir.valor_acumulado_ano,
    ir.valor_acumulado_12m,
    ir.fonte,
    ir.data_importacao,
    ir.criado_em
FROM gc_indice_reajuste ir
LEFT JOIN gc_tipo_correcao tc ON tc.codigo = ir.tipo_indice
ORDER BY ir.ano DESC, ir.mes DESC, ir.tipo_indice;

COMMENT ON VIEW vw_indices_reajuste IS 'Indices de reajuste com descricao';

-- ============================================================================
-- VIEW: Compradores com contratos
-- ============================================================================
CREATE OR REPLACE VIEW vw_comprador_contratos AS
SELECT
    comp.id,
    comp.nome,
    comp.tipo_pessoa,
    CASE comp.tipo_pessoa WHEN 'PF' THEN 'Pessoa Fisica' ELSE 'Pessoa Juridica' END AS tipo_pessoa_desc,
    COALESCE(comp.cpf, comp.cnpj) AS documento,
    comp.email,
    comp.celular,
    comp.cidade,
    comp.estado,
    comp.ativo,
    -- Totais
    COUNT(DISTINCT c.id) AS total_contratos,
    SUM(CASE WHEN c.status = 'ATIVO' THEN 1 ELSE 0 END) AS contratos_ativos,
    NVL(SUM(c.valor_total), 0) AS valor_total_contratos,
    -- Parcelas
    COUNT(p.id) AS total_parcelas,
    SUM(CASE WHEN p.pago = 1 THEN 1 ELSE 0 END) AS parcelas_pagas,
    SUM(CASE WHEN p.pago = 0 AND p.data_vencimento < TRUNC(SYSDATE) THEN 1 ELSE 0 END) AS parcelas_vencidas
FROM gc_comprador comp
LEFT JOIN gc_contrato c ON c.comprador_id = comp.id
LEFT JOIN gc_parcela p ON p.contrato_id = c.id
GROUP BY comp.id, comp.nome, comp.tipo_pessoa, comp.cpf, comp.cnpj,
         comp.email, comp.celular, comp.cidade, comp.estado, comp.ativo;

COMMENT ON VIEW vw_comprador_contratos IS 'Compradores com resumo de contratos';

-- ============================================================================
-- VIEW: LOV - Imobiliarias ativas
-- ============================================================================
CREATE OR REPLACE VIEW vw_lov_imobiliarias AS
SELECT
    i.id,
    i.nome,
    i.cnpj,
    c.nome AS contabilidade_nome,
    i.nome || ' (' || c.nome || ')' AS display_value
FROM gc_imobiliaria i
JOIN gc_contabilidade c ON c.id = i.contabilidade_id
WHERE i.ativo = 1 AND c.ativo = 1
ORDER BY i.nome;

-- ============================================================================
-- VIEW: LOV - Contas bancarias ativas
-- ============================================================================
CREATE OR REPLACE VIEW vw_lov_contas_bancarias AS
SELECT
    cb.id,
    cb.descricao,
    b.nome AS banco_nome,
    cb.agencia,
    cb.conta,
    cb.principal,
    i.nome AS imobiliaria_nome,
    b.nome || ' - Ag: ' || cb.agencia || ' Cc: ' || cb.conta || ' (' || cb.descricao || ')' AS display_value
FROM gc_conta_bancaria cb
JOIN gc_banco b ON b.codigo = cb.banco
JOIN gc_imobiliaria i ON i.id = cb.imobiliaria_id
WHERE cb.ativo = 1 AND i.ativo = 1
ORDER BY cb.principal DESC, b.nome, cb.descricao;

-- ============================================================================
-- VIEW: LOV - Compradores ativos
-- ============================================================================
CREATE OR REPLACE VIEW vw_lov_compradores AS
SELECT
    id,
    nome,
    tipo_pessoa,
    COALESCE(cpf, cnpj) AS documento,
    nome || ' - ' || COALESCE(cpf, cnpj) AS display_value
FROM gc_comprador
WHERE ativo = 1
ORDER BY nome;

-- ============================================================================
-- VIEW: LOV - Imoveis disponiveis
-- ============================================================================
CREATE OR REPLACE VIEW vw_lov_imoveis AS
SELECT
    i.id,
    i.identificacao,
    i.loteamento,
    i.tipo,
    ti.descricao AS tipo_desc,
    i.cidade,
    i.estado,
    i.area,
    i.valor,
    i.disponivel,
    im.nome AS imobiliaria_nome,
    COALESCE(i.loteamento || ' - ', '') || i.identificacao || ' (' || ti.descricao || ')' AS display_value
FROM gc_imovel i
JOIN gc_imobiliaria im ON im.id = i.imobiliaria_id
LEFT JOIN gc_tipo_imovel ti ON ti.codigo = i.tipo
WHERE i.ativo = 1
ORDER BY i.loteamento, i.identificacao;

COMMIT;
