# Sistema de Gestão de Contratos - Migração Oracle 23c / APEX 24

## Informações do Desenvolvedor

- **Nome:** Maxwell da Silva Oliveira
- **Email:** maxwbh@gmail.com
- **LinkedIn:** https://www.linkedin.com/in/maxwbh/
- **GitHub:** https://github.com/Maxwbh/
- **Empresa:** M&S do Brasil LTDA
- **Site:** https://msbrasil.inf.br

---

## Visão Geral

Este diretório contém os scripts necessários para migrar o Sistema de Gestão de Contratos de Django/PostgreSQL para Oracle 23c com Oracle APEX 24.

## Estrutura de Diretórios

```
oracle_migration/
├── ddl/                          # Scripts de criação de tabelas
│   └── 01_create_tables.sql      # DDL principal (tabelas, constraints, índices)
│
├── triggers/                     # Triggers do sistema
│   └── 01_audit_triggers.sql     # Triggers de auditoria e auto-atualização
│
├── packages/                     # Packages PL/SQL
│   ├── pkg_contrato.sql          # Lógica de negócio de contratos
│   ├── pkg_boleto.sql            # Gerenciamento de boletos
│   └── pkg_brcobranca.sql        # Integração com API BRcobranca
│
├── views/                        # Views para APEX
│   └── 01_views.sql              # Views de consulta e LOVs
│
├── procedures/                   # Procedures avulsas
│
├── data_migration/               # Scripts de migração de dados
│   └── 01_migration_postgresql_oracle.sql
│
├── apex/                         # Aplicação APEX
│   └── install_apex_app.sql      # Script de instalação APEX
│
└── README.md                     # Este arquivo
```

## Pré-requisitos

### Oracle Database 23c
- Oracle Database 23c (23ai) ou superior
- Oracle APEX 24.1 ou superior
- Usuário com privilégios de DBA para instalação

### BRcobranca API
A geração de boletos e arquivos CNAB utiliza a API BRcobranca (Ruby/Docker).

```bash
# Executar container Docker
docker run -d -p 9292:9292 akretion/boleto_cnab_api
```

### Network ACL (para chamadas HTTP)
Para o package `pkg_brcobranca` funcionar, é necessário configurar ACL:

```sql
BEGIN
  DBMS_NETWORK_ACL_ADMIN.CREATE_ACL(
    acl => 'brcobranca_acl.xml',
    description => 'ACL para BRcobranca API',
    principal => 'GESTAO_CONTRATO',
    is_grant => TRUE,
    privilege => 'connect'
  );

  DBMS_NETWORK_ACL_ADMIN.ADD_PRIVILEGE(
    acl => 'brcobranca_acl.xml',
    principal => 'GESTAO_CONTRATO',
    is_grant => TRUE,
    privilege => 'resolve'
  );

  DBMS_NETWORK_ACL_ADMIN.ASSIGN_ACL(
    acl => 'brcobranca_acl.xml',
    host => 'localhost',
    lower_port => 9292,
    upper_port => 9292
  );
  COMMIT;
END;
/
```

## Instalação

### 1. Criar Schema

```sql
-- Conectar como SYS ou DBA
CREATE USER gestao_contrato IDENTIFIED BY "SuaSenhaSegura"
  DEFAULT TABLESPACE users
  QUOTA UNLIMITED ON users;

GRANT CREATE SESSION TO gestao_contrato;
GRANT CREATE TABLE TO gestao_contrato;
GRANT CREATE VIEW TO gestao_contrato;
GRANT CREATE SEQUENCE TO gestao_contrato;
GRANT CREATE PROCEDURE TO gestao_contrato;
GRANT CREATE TRIGGER TO gestao_contrato;
GRANT CREATE TYPE TO gestao_contrato;
GRANT EXECUTE ON UTL_HTTP TO gestao_contrato;
```

### 2. Executar Scripts DDL

```bash
# Conectar ao schema
sqlplus gestao_contrato/SuaSenhaSegura@localhost:1521/XEPDB1

# Executar na ordem:
@ddl/01_create_tables.sql
@triggers/01_audit_triggers.sql
@packages/pkg_contrato.sql
@packages/pkg_boleto.sql
@packages/pkg_brcobranca.sql
@views/01_views.sql
```

### 3. Verificar Instalação

```sql
-- Verificar objetos criados
SELECT object_type, COUNT(*)
FROM user_objects
GROUP BY object_type
ORDER BY object_type;

-- Verificar packages compilados
SELECT object_name, status
FROM user_objects
WHERE object_type IN ('PACKAGE', 'PACKAGE BODY');
```

### 4. Configurar BRcobranca URL

```sql
-- Definir URL da API BRcobranca
BEGIN
  pkg_brcobranca.set_api_url('http://localhost:9292');
END;
/
```

## Migração de Dados

Se você possui dados no sistema Django/PostgreSQL, siga estas etapas:

### Exportar do PostgreSQL

```bash
# Conectar ao PostgreSQL e exportar CSVs
psql -d gestao_contrato -f oracle_migration/data_migration/export_postgresql.sql
```

### Importar no Oracle

```sql
-- Executar package de migração
BEGIN
  pkg_migration.migrar_tudo(p_limpar_destino => TRUE);
END;
/

-- Validar migração
DECLARE
  v_erros NUMBER;
  v_avisos NUMBER;
BEGIN
  pkg_migration.validar_migracao(v_erros, v_avisos);
  DBMS_OUTPUT.PUT_LINE('Erros: ' || v_erros || ', Avisos: ' || v_avisos);
END;
/
```

## Oracle APEX

### Criar Workspace

1. Acesse o APEX Admin (apex.oracle.com ou localhost:8080/apex)
2. Crie um novo Workspace associado ao schema `GESTAO_CONTRATO`
3. Crie um usuário administrador do Workspace

### Importar Aplicação

A aplicação APEX será criada usando o App Builder com as seguintes páginas principais:

- **Dashboard** - Visão geral do sistema
- **Contratos** - CRUD de contratos
- **Parcelas** - Gerenciamento de parcelas
- **Boletos** - Geração e gestão de boletos
- **CNAB** - Remessa e Retorno
- **Notificações** - Configuração e envio
- **Cadastros** - Contabilidades, Imobiliárias, Compradores, Imóveis
- **Configurações** - Email, SMS, WhatsApp

## Packages PL/SQL

### PKG_CONTRATO
Gerenciamento de contratos e parcelas:
- `gerar_parcelas` - Gera parcelas do contrato
- `calcular_progresso` - Calcula % de pagamento
- `calcular_valor_pago` - Total pago
- `calcular_saldo_devedor` - Saldo pendente
- `registrar_pagamento` - Registra pagamento
- `aplicar_reajuste` - Aplica correção monetária

### PKG_BOLETO
Gerenciamento de boletos:
- `gerar_numero_documento` - Gera número do documento
- `obter_proximo_nosso_numero` - Sequencial nosso número
- `registrar_boleto_gerado` - Registra boleto na parcela
- `cancelar_boleto` - Cancela boleto
- `criar_arquivo_remessa` - Cria arquivo CNAB

### PKG_BRCOBRANCA
Integração com API BRcobranca:
- `gerar_boleto_brcobranca` - Gera boleto via API
- `gerar_boletos_lote` - Geração em lote
- `gerar_remessa_brcobranca` - Gera arquivo remessa
- `processar_retorno_brcobranca` - Processa arquivo retorno

## Views Principais

| View | Descrição |
|------|-----------|
| `vw_contrato_detalhado` | Contratos com todos os relacionamentos |
| `vw_parcela_detalhada` | Parcelas com cálculos |
| `vw_parcelas_vencidas` | Parcelas em atraso |
| `vw_parcelas_a_vencer` | Parcelas próximos 30 dias |
| `vw_dashboard_imobiliaria` | Resumo por imobiliária |
| `vw_boletos` | Boletos gerados |
| `vw_arquivos_remessa` | Arquivos CNAB remessa |
| `vw_arquivos_retorno` | Arquivos CNAB retorno |

## Tabelas Principais

| Tabela | Descrição |
|--------|-----------|
| `gc_contabilidade` | Contabilidades |
| `gc_imobiliaria` | Imobiliárias/Beneficiários |
| `gc_conta_bancaria` | Contas bancárias |
| `gc_imovel` | Imóveis (lotes, terrenos, etc.) |
| `gc_comprador` | Compradores (PF/PJ) |
| `gc_contrato` | Contratos de venda |
| `gc_parcela` | Parcelas dos contratos |
| `gc_reajuste` | Histórico de reajustes |
| `gc_indice_reajuste` | Índices econômicos |

## Suporte

Para suporte técnico:
- Email: maxwbh@gmail.com
- LinkedIn: https://www.linkedin.com/in/maxwbh/

## Changelog

### v1.0.0 (2024)
- Migração inicial do sistema Django/PostgreSQL para Oracle 23c
- Packages PL/SQL para lógica de negócio
- Integração com BRcobranca API
- Views otimizadas para APEX 24

---

**M&S do Brasil LTDA** - Sistema de Gestão de Contratos
