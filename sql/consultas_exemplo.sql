-- Consultas de exemplo para explorar o pipeline.
-- Conexão: localhost:5433 | db: warehouse | user: dw | senha: dw12345

-- 1) Top 10 por valor de mercado (último snapshot)
select posicao, simbolo, nome, preco_usd, market_cap_usd,
       participacao_market_cap_pct, variacao_24h_pct
from marts.mart_ranking_mercado
order by posicao
limit 10;

-- 2) Últimas 24 horas de uma moeda
select ingested_at, preco_usd, volume_24h_usd, variacao_24h_pct
from marts.fct_mercado
where moeda_id = 'bitcoin'
order by ingested_at desc
limit 24;

-- 3) Maiores altas e baixas do último snapshot
select simbolo, nome, variacao_24h_pct, preco_usd
from marts.mart_ranking_mercado
where variacao_24h_pct is not null
order by variacao_24h_pct desc
limit 5;

-- 4) Cobertura da ingestão (quantas moedas por snapshot)
select ingested_at, count(*) as moedas
from marts.fct_mercado
group by ingested_at
order by ingested_at desc
limit 10;

-- 5) Volume negociado agregado por snapshot
select ingested_at, round(sum(volume_24h_usd) / 1e9, 2) as volume_bi_usd
from marts.fct_mercado
group by ingested_at
order by ingested_at desc
limit 10;

-- 6) O bruto, direto da camada raw (para auditoria)
select ingested_at, row_count, loaded_at,
       jsonb_array_length(payload) as moedas_no_payload
from raw.coingecko_mercado
order by ingested_at desc
limit 5;
