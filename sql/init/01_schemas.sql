-- Executado automaticamente na primeira inicialização do Postgres do warehouse.
-- O dbt também cria schemas, mas deixá-los prontos evita surpresa na primeira run.
create schema if not exists raw;
create schema if not exists staging;
create schema if not exists marts;
create schema if not exists analytics;
