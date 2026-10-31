{{ config(
    materialized='incremental',
    unique_key=['ingested_at', 'moeda_id'],
    on_schema_change='append_new_columns'
) }}

/*
  Fato: cada linha é o estado de uma moeda em um snapshot horário.

  Incremental de verdade: só processa snapshots mais novos que o máximo já
  carregado. O `unique_key` torna a carga idempotente (delete+insert no
  Postgres), então rodar a DAG duas vezes para a mesma hora não duplica.
*/

select
    ingested_at,
    moeda_id,
    simbolo,
    nome,
    preco_usd,
    market_cap_usd,
    ranking_market_cap,
    volume_24h_usd,
    variacao_24h_pct,
    oferta_circulante,
    atualizado_em
from {{ ref('stg_coingecko__mercado') }}

{% if is_incremental() %}
where ingested_at > (
    select coalesce(max(ingested_at), '1900-01-01 00:00:00+00'::timestamptz)
    from {{ this }}
)
{% endif %}
