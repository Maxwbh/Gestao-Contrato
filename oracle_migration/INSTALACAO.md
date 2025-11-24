# Guia de Instalação - Sistema de Gestão de Contratos Oracle 23c / APEX 24

## Informações do Desenvolvedor

- **Nome:** Maxwell da Silva Oliveira
- **Email:** maxwbh@gmail.com
- **LinkedIn:** https://www.linkedin.com/in/maxwbh/
- **GitHub:** https://github.com/Maxwbh/
- **Empresa:** M&S do Brasil LTDA
- **Site:** https://msbrasil.inf.br

---

## Requisitos do Sistema

### Hardware Mínimo
- CPU: 2 cores
- RAM: 8 GB
- Disco: 50 GB livres

### Software
- **Oracle Database 23c** (23ai) ou Oracle Database 21c XE
- **Oracle APEX 24.1** ou superior
- **Oracle REST Data Services (ORDS)** 24.1
- **Docker** (para BRcobranca API)

---

## Passo 1: Instalar Oracle Database 23c

### Opção A: Oracle 23c Free (Docker)

```bash
# Baixar e executar container Oracle 23c Free
docker run -d --name oracle23c \
  -p 1521:1521 \
  -p 5500:5500 \
  -e ORACLE_PWD=SenhaOracle123 \
  container-registry.oracle.com/database/free:latest

# Aguardar inicialização (pode levar 10-15 minutos)
docker logs -f oracle23c
```

### Opção B: Instalação Local

1. Baixe o Oracle Database 23c Free de: https://www.oracle.com/database/free/
2. Execute o instalador e siga as instruções
3. Configure o listener e o serviço

---

## Passo 2: Instalar Oracle APEX

```bash
# Conectar ao Oracle como SYS
sqlplus sys/SenhaOracle123@localhost:1521/FREEPDB1 as sysdba

# Instalar APEX (se ainda não instalado)
@apexins.sql SYSAUX SYSAUX TEMP /i/

# Configurar conta ADMIN do APEX
@apxchpwd.sql
```

---

## Passo 3: Instalar ORDS

```bash
# Baixe ORDS de https://www.oracle.com/tools/ords/ords-downloads.html

# Configurar ORDS
java -jar ords.war install advanced

# Iniciar ORDS
java -jar ords.war standalone

# APEX estará disponível em: http://localhost:8080/ords/apex
```

---

## Passo 4: Instalar BRcobranca API

```bash
# Executar container BRcobranca
docker run -d --name brcobranca \
  -p 9292:9292 \
  akretion/boleto_cnab_api

# Verificar se está rodando
curl http://localhost:9292/api/boleto
```

---

## Passo 5: Criar Schema e Instalar Scripts

### Método Automático

```bash
cd /caminho/para/oracle_migration

# Conectar como SYS e executar instalação completa
sqlplus sys/SenhaOracle123@localhost:1521/FREEPDB1 as sysdba @install.sql
```

### Método Manual

```bash
# Conectar como SYS
sqlplus sys/SenhaOracle123@localhost:1521/FREEPDB1 as sysdba

# Criar usuário
CREATE USER gestao_contrato IDENTIFIED BY "GestaoContrato2024!"
    DEFAULT TABLESPACE users QUOTA UNLIMITED ON users;

GRANT CREATE SESSION, CREATE TABLE, CREATE VIEW,
      CREATE SEQUENCE, CREATE PROCEDURE, CREATE TRIGGER TO gestao_contrato;
GRANT EXECUTE ON UTL_HTTP TO gestao_contrato;

# Conectar como o novo usuário
CONNECT gestao_contrato/GestaoContrato2024!@localhost:1521/FREEPDB1

# Executar scripts na ordem
@ddl/01_create_tables.sql
@triggers/01_audit_triggers.sql
@packages/pkg_contrato.sql
@packages/pkg_boleto.sql
@packages/pkg_brcobranca.sql
@views/01_views.sql
```

---

## Passo 6: Configurar ACL para HTTP

Para que o package `pkg_brcobranca` consiga acessar a API externa:

```sql
-- Conectar como SYS
CONNECT sys/SenhaOracle123@localhost:1521/FREEPDB1 as sysdba

BEGIN
  -- Criar ACL
  DBMS_NETWORK_ACL_ADMIN.CREATE_ACL(
    acl => 'brcobranca_acl.xml',
    description => 'ACL para BRcobranca API',
    principal => 'GESTAO_CONTRATO',
    is_grant => TRUE,
    privilege => 'connect'
  );

  -- Adicionar privilégio de resolução de nome
  DBMS_NETWORK_ACL_ADMIN.ADD_PRIVILEGE(
    acl => 'brcobranca_acl.xml',
    principal => 'GESTAO_CONTRATO',
    is_grant => TRUE,
    privilege => 'resolve'
  );

  -- Associar ao host
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

---

## Passo 7: Criar Workspace APEX

1. Acesse o APEX Admin: http://localhost:8080/ords/apex_admin
2. Login: ADMIN / (senha definida anteriormente)
3. Vá em: **Manage Workspaces > Create Workspace**
4. Configure:
   - Workspace Name: `GESTAO_CONTRATO`
   - Schema: `GESTAO_CONTRATO`
   - Workspace Admin: `admin` / `Admin123!`

---

## Passo 8: Criar Aplicação APEX

1. Acesse o Workspace: http://localhost:8080/ords/f?p=gestao_contrato
2. Login com o admin do workspace
3. Vá em: **App Builder > Create**
4. Escolha: **New Application**
5. Configure:
   - Name: `Sistema de Gestão de Contratos`
   - Theme: Universal Theme
   - Authentication: Application Express Authentication

6. Adicione as páginas conforme documentado em `apex/create_apex_application.sql`

---

## Passo 9: Configurar URL do BRcobranca

```sql
-- No SQL Workshop ou SQL*Plus
BEGIN
  pkg_brcobranca.set_api_url('http://localhost:9292');
END;
/
```

---

## Verificação da Instalação

### Verificar Objetos Criados

```sql
SELECT object_type, COUNT(*)
FROM user_objects
GROUP BY object_type
ORDER BY object_type;
```

### Verificar Packages

```sql
SELECT object_name, status
FROM user_objects
WHERE object_type IN ('PACKAGE', 'PACKAGE BODY')
ORDER BY object_name;
```

### Testar Conexão BRcobranca

```sql
DECLARE
  v_response CLOB;
BEGIN
  v_response := APEX_WEB_SERVICE.make_rest_request(
    p_url => 'http://localhost:9292/api/boleto',
    p_http_method => 'GET'
  );
  DBMS_OUTPUT.PUT_LINE('Status: ' || APEX_WEB_SERVICE.g_status_code);
END;
/
```

---

## Migração de Dados (Opcional)

Se você possui dados no sistema Django/PostgreSQL:

### Exportar do PostgreSQL

```bash
# No servidor PostgreSQL
psql -d gestao_contrato -c "\COPY core_contabilidade TO '/tmp/contabilidade.csv' CSV HEADER"
psql -d gestao_contrato -c "\COPY core_imobiliaria TO '/tmp/imobiliaria.csv' CSV HEADER"
# ... repetir para outras tabelas
```

### Importar no Oracle

Use SQL*Loader ou External Tables conforme documentado em `data_migration/01_migration_postgresql_oracle.sql`

---

## Solução de Problemas

### Erro: ORA-24247 (network access denied)

```sql
-- Verificar ACLs existentes
SELECT * FROM dba_network_acls;
SELECT * FROM dba_network_acl_privileges;

-- Recriar ACL se necessário
```

### Erro: Package INVALID

```sql
-- Recompilar packages
ALTER PACKAGE pkg_contrato COMPILE;
ALTER PACKAGE pkg_contrato COMPILE BODY;

-- Ver erros de compilação
SHOW ERRORS PACKAGE BODY pkg_contrato;
```

### BRcobranca não responde

```bash
# Verificar container
docker ps -a | grep brcobranca

# Reiniciar se necessário
docker restart brcobranca

# Ver logs
docker logs brcobranca
```

---

## Suporte

Para suporte técnico, entre em contato:

- **Email:** maxwbh@gmail.com
- **LinkedIn:** https://www.linkedin.com/in/maxwbh/
- **GitHub:** https://github.com/Maxwbh/

---

**M&S do Brasil LTDA** - Sistema de Gestão de Contratos
© 2024 - Todos os direitos reservados
