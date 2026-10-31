-- Teste singular do dbt: um snapshot com poucas moedas indica falha parcial
-- da API (ex.: paginação quebrada), mesmo que a carga "tenha funcionado".
select
    ingested_at,
    count(*) as moedas
from {{ ref('fct_mercado') }}
group by ingested_at
having count(*) < 50
