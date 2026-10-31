-- Teste singular do dbt: nenhum preço pode ser zero ou negativo.
select *
from {{ ref('fct_mercado') }}
where preco_usd is null
   or preco_usd <= 0
