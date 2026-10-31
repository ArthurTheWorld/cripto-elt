{{ config(materialized='table') }}

/*
  Ranking do snapshot mais recente, com participação de mercado calculada.

  Este é o tipo de tabela que alimenta dashboard: "quem é o top 10 hoje e
  quanto do mercado cada uma representa".
*/

with ultimo_snapshot as (

    select max(ingested_at) as ingested_at
    from {{ ref('fct_mercado') }}

),

atual as (

    select f.*
    from {{ ref('fct_mercado') }} f
    inner join ultimo_snapshot u
        on f.ingested_at = u.ingested_at

),

totais as (

    select sum(market_cap_usd) as market_cap_total
    from atual

)

select
    a.moeda_id,
    a.simbolo,
    a.nome,
    a.preco_usd,
    a.market_cap_usd,
    a.volume_24h_usd,
    a.variacao_24h_pct,
    a.ingested_at,
    round(100 * a.market_cap_usd / nullif(t.market_cap_total, 0), 4) as participacao_market_cap_pct,
    row_number() over (order by a.market_cap_usd desc)                as posicao
from atual a
cross join totais t
