# Criado manualmente para garantir que as tabelas CNAB existam em produção.
#
# Contexto: financeiro.0001_initial foi aplicado em produção ANTES de os modelos
# ArquivoRemessa, ItemRemessa, ArquivoRetorno e ItemRetorno serem adicionados a ele.
# O resultado é: django_migrations tem 0001_initial marcado como aplicado, mas as
# tabelas CNAB nunca foram criadas no banco.
#
# Solução: usar CREATE TABLE IF NOT EXISTS — idempotente, não falha se já existir.

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("financeiro", "0005_parcela_amortizacao_juros_embutido"),
        ("core", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TABLE IF NOT EXISTS financeiro_arquivoremessa (
                    id          bigserial    PRIMARY KEY,
                    criado_em   timestamptz  NOT NULL,
                    atualizado_em timestamptz NOT NULL,
                    numero_remessa integer   NOT NULL,
                    layout      varchar(10)  NOT NULL DEFAULT 'CNAB_240',
                    arquivo     varchar(100) NOT NULL DEFAULT '',
                    nome_arquivo varchar(100) NOT NULL DEFAULT '',
                    status      varchar(15)  NOT NULL DEFAULT 'GERADO',
                    data_geracao timestamptz NOT NULL,
                    data_envio  timestamptz  NULL,
                    quantidade_boletos integer NOT NULL DEFAULT 0,
                    valor_total numeric(14,2) NOT NULL DEFAULT 0.00,
                    observacoes text         NOT NULL DEFAULT '',
                    erro_mensagem text       NOT NULL DEFAULT '',
                    conta_bancaria_id bigint NOT NULL
                        REFERENCES core_contabancaria(id) ON DELETE RESTRICT
                        DEFERRABLE INITIALLY DEFERRED
                );
                CREATE UNIQUE INDEX IF NOT EXISTS
                    financeiro_arquivoremessa_conta_num_uniq
                    ON financeiro_arquivoremessa (conta_bancaria_id, numero_remessa);

                CREATE TABLE IF NOT EXISTS financeiro_itemremessa (
                    id          bigserial    PRIMARY KEY,
                    criado_em   timestamptz  NOT NULL,
                    atualizado_em timestamptz NOT NULL,
                    nosso_numero varchar(30)  NOT NULL DEFAULT '',
                    valor       numeric(12,2) NOT NULL,
                    data_vencimento date      NOT NULL,
                    processado  boolean      NOT NULL DEFAULT false,
                    codigo_ocorrencia varchar(10) NOT NULL DEFAULT '',
                    descricao_ocorrencia varchar(255) NOT NULL DEFAULT '',
                    arquivo_remessa_id bigint NOT NULL
                        REFERENCES financeiro_arquivoremessa(id) ON DELETE CASCADE
                        DEFERRABLE INITIALLY DEFERRED,
                    parcela_id  bigint       NOT NULL
                        REFERENCES financeiro_parcela(id) ON DELETE RESTRICT
                        DEFERRABLE INITIALLY DEFERRED
                );
                CREATE UNIQUE INDEX IF NOT EXISTS
                    financeiro_itemremessa_remessa_parcela_uniq
                    ON financeiro_itemremessa (arquivo_remessa_id, parcela_id);

                CREATE TABLE IF NOT EXISTS financeiro_arquivoretorno (
                    id          bigserial    PRIMARY KEY,
                    criado_em   timestamptz  NOT NULL,
                    atualizado_em timestamptz NOT NULL,
                    arquivo     varchar(100) NOT NULL DEFAULT '',
                    nome_arquivo varchar(100) NOT NULL DEFAULT '',
                    layout      varchar(10)  NOT NULL DEFAULT 'CNAB_240',
                    status      varchar(20)  NOT NULL DEFAULT 'PENDENTE',
                    data_upload timestamptz  NOT NULL,
                    data_processamento timestamptz NULL,
                    total_registros integer  NOT NULL DEFAULT 0,
                    registros_processados integer NOT NULL DEFAULT 0,
                    registros_erro integer   NOT NULL DEFAULT 0,
                    valor_total_pago numeric(14,2) NOT NULL DEFAULT 0.00,
                    observacoes text         NOT NULL DEFAULT '',
                    erro_mensagem text       NOT NULL DEFAULT '',
                    conta_bancaria_id bigint NOT NULL
                        REFERENCES core_contabancaria(id) ON DELETE RESTRICT
                        DEFERRABLE INITIALLY DEFERRED,
                    processado_por_id integer NULL
                        REFERENCES auth_user(id) ON DELETE SET NULL
                        DEFERRABLE INITIALLY DEFERRED
                );

                CREATE TABLE IF NOT EXISTS financeiro_itemretorno (
                    id          bigserial    PRIMARY KEY,
                    criado_em   timestamptz  NOT NULL,
                    atualizado_em timestamptz NOT NULL,
                    nosso_numero varchar(30)  NOT NULL DEFAULT '',
                    numero_documento varchar(25) NOT NULL DEFAULT '',
                    codigo_ocorrencia varchar(10) NOT NULL DEFAULT '',
                    descricao_ocorrencia varchar(255) NOT NULL DEFAULT '',
                    tipo_ocorrencia varchar(20) NOT NULL DEFAULT 'OUTROS',
                    valor_titulo numeric(12,2) NULL,
                    valor_pago  numeric(12,2) NULL,
                    valor_juros numeric(12,2) NULL,
                    valor_multa numeric(12,2) NULL,
                    valor_desconto numeric(12,2) NULL,
                    valor_tarifa numeric(12,2) NULL,
                    data_ocorrencia date       NULL,
                    data_credito date          NULL,
                    processado  boolean       NOT NULL DEFAULT false,
                    erro_processamento text   NOT NULL DEFAULT '',
                    arquivo_retorno_id bigint NOT NULL
                        REFERENCES financeiro_arquivoretorno(id) ON DELETE CASCADE
                        DEFERRABLE INITIALLY DEFERRED,
                    parcela_id  bigint        NULL
                        REFERENCES financeiro_parcela(id) ON DELETE SET NULL
                        DEFERRABLE INITIALLY DEFERRED
                );
                CREATE INDEX IF NOT EXISTS financeiro_ir_nosso_idx
                    ON financeiro_itemretorno (nosso_numero);
                CREATE INDEX IF NOT EXISTS financeiro_ir_tipo_idx
                    ON financeiro_itemretorno (tipo_ocorrencia);
            """,
            reverse_sql="""
                DROP TABLE IF EXISTS financeiro_itemretorno;
                DROP TABLE IF EXISTS financeiro_arquivoretorno;
                DROP TABLE IF EXISTS financeiro_itemremessa;
                DROP TABLE IF EXISTS financeiro_arquivoremessa;
            """,
        ),
    ]
