-- Teste singular do dbt: falha se houver mais de uma linha para o mesmo
-- (snapshot, moeda). Pega o caso clássico de reprocessamento duplicando dados.
select
    ingested_at,
    moeda_id,
    count(*) as ocorrencias
from {{ ref('fct_mercado') }}
group by ingested_at, moeda_id
having count(*) > 1
