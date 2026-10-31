{{ config(materialized='table') }}

/*
  Dimensão de moedas: um registro por moeda, com os atributos mais recentes
  conhecidos. `distinct on` pega a versão mais nova de cada moeda.
*/

select distinct on (moeda_id)
    moeda_id,
    simbolo,
    nome,
    atualizado_em
from {{ ref('stg_coingecko__mercado') }}
order by moeda_id, ingested_at desc
