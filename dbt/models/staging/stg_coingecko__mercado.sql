{{ config(materialized='view') }}

/*
  Staging: pega o JSONB da camada raw, "explode" o array em linhas e tipa
  cada campo. Nenhuma regra de negócio mora aqui — só limpeza e tipagem.

  `distinct on` garante uma linha por (snapshot, moeda), mesmo que a origem
  repita algum registro.
*/

with origem as (

    select ingested_at, payload
    from {{ source('raw', 'coingecko_mercado') }}

),

expandido as (

    select
        origem.ingested_at,
        jsonb_array_elements(origem.payload) as moeda
    from origem

),

tipado as (

    select
        ingested_at,
        moeda ->> 'id'                                            as moeda_id,
        upper(moeda ->> 'symbol')                                 as simbolo,
        moeda ->> 'name'                                          as nome,
        (moeda ->> 'current_price')::numeric(28, 8)               as preco_usd,
        (moeda ->> 'market_cap')::numeric(38, 2)                  as market_cap_usd,
        (moeda ->> 'market_cap_rank')::integer                    as ranking_market_cap,
        (moeda ->> 'total_volume')::numeric(38, 2)                as volume_24h_usd,
        (moeda ->> 'price_change_percentage_24h')::numeric(12, 4) as variacao_24h_pct,
        (moeda ->> 'circulating_supply')::numeric(38, 8)          as oferta_circulante,
        (moeda ->> 'last_updated')::timestamptz                   as atualizado_em
    from expandido

)

select distinct on (ingested_at, moeda_id)
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
from tipado
where moeda_id is not null
order by ingested_at, moeda_id, atualizado_em desc nulls last
