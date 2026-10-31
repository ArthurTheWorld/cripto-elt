"""DAG do pipeline ELT de mercado de criptomoedas.

Fluxo
-----
1. `extract_to_lake`  -> busca a API, valida o contrato e grava o JSON cru
                          (gzip) no lake, particionado por dt/hora.
2. `load_to_warehouse` -> lê o objeto do lake e faz UPSERT do snapshot em
                          `raw.coingecko_mercado` (JSONB).
3. `dbt_run`          -> dbt transforma: staging (view) -> marts (tabelas).
4. `dbt_test`         -> roda os testes de qualidade; se falhar, a DAG falha.

Decisão de design: as tasks trocam *referências* (a chave do objeto no lake),
não o dataframe inteiro. XCom serve para metadados pequenos — mandar 100
linhas por XCom é o erro clássico que estoura o banco de metadados do Airflow.
"""

from __future__ import annotations

import logging
from datetime import timedelta

import pendulum
from airflow.decorators import dag, task
from airflow.models.baseoperator import chain
from airflow.operators.bash import BashOperator

from etl import coingecko, storage, warehouse
from etl.config import Settings

log = logging.getLogger(__name__)

DBT_DIR = "/opt/airflow/dbt"
PREFIXO_BRONZE = "coingecko/mercado"

DOC_MD = """
## ELT do mercado de criptomoedas

Pipeline em camadas (medallion):

```mermaid
graph LR
    API[CoinGecko API] -->|JSON| BRONZE[(RustFS / S3<br/>bronze)]
    BRONZE -->|UPSERT| RAW[(Postgres<br/>raw)]
    RAW -->|dbt| STG[staging<br/>view]
    STG -->|dbt| MART[marts<br/>tabelas]
```

**Camadas**
| Camada | Onde | O que contém |
|---|---|---|
| bronze | RustFS / S3 | JSON cru, imutável, particionado por `dt`/`hora` |
| raw | Postgres | mesmo JSON, em `jsonb`, com UPSERT idempotente |
| staging | dbt (view) | JSON explodido, tipado, deduplicado |
| marts | dbt (tabela) | `fct_mercado`, `dim_moedas`, `mart_ranking_mercado` |

**Idempotência:** `ingested_at` vem do `data_interval_start` da DAG, então
reprocessar a mesma hora sobrescreve o snapshot em vez de duplicar.

**Qualidade:** validação de contrato na extração + testes dbt (`not_null`,
unicidade composta, preço positivo, frescor da fonte).
"""


@dag(
    dag_id="cripto_elt",
    description="CoinGecko -> lake S3 (bronze) -> Postgres (raw) -> dbt (staging/marts)",
    schedule="0 * * * *",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "luiza",
        "retries": 3,
        "retry_delay": timedelta(minutes=2),
        "retry_exponential_backoff": True,
        "max_retry_delay": timedelta(minutes=20),
    },
    tags=["cripto", "elt", "s3", "dbt"],
    doc_md=DOC_MD,
)
def cripto_elt():
    @task(task_id="extract_to_lake")
    def extract_to_lake(**context) -> dict:
        settings = Settings.from_env()
        quantidade = settings.coingecko_per_page

        bruto = coingecko.fetch_market_snapshot(
            url=settings.coingecko_api_url,
            params={"per_page": str(quantidade)},
            api_key=settings.coingecko_api_key,
        )
        registros = coingecko.normalize(bruto)
        coingecko.validate(registros, min_records=max(10, quantidade // 2))

        ingested_at = context["data_interval_start"]
        chave = storage.build_partition_key(PREFIXO_BRONZE, ingested_at)

        cliente = storage.build_client(
            settings.s3_endpoint,
            settings.s3_access_key,
            settings.s3_secret_key,
            secure=settings.s3_secure,
        )
        storage.ensure_bucket(cliente, settings.s3_bucket)
        storage.upload_json(cliente, settings.s3_bucket, chave, registros)

        return {
            "bucket": settings.s3_bucket,
            "key": chave,
            "row_count": len(registros),
            "ingested_at": ingested_at.isoformat(),
        }

    @task(task_id="load_to_warehouse")
    def load_to_warehouse(bronze: dict) -> dict:
        settings = Settings.from_env()

        cliente = storage.build_client(
            settings.s3_endpoint,
            settings.s3_access_key,
            settings.s3_secret_key,
            secure=settings.s3_secure,
        )
        payload = storage.download_json(cliente, bronze["bucket"], bronze["key"])

        conn = warehouse.connect(settings)
        try:
            warehouse.ensure_schema(conn)
            row_count = warehouse.load_snapshot(
                conn,
                ingested_at=pendulum.parse(bronze["ingested_at"]),
                payload=payload,
            )
            total_snapshots = warehouse.count_snapshots(conn)
        finally:
            conn.close()

        return {"row_count": row_count, "snapshots": total_snapshots}

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_DIR} && dbt run --profiles-dir . --target prod",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && dbt test --profiles-dir . --target prod",
        retries=1,
    )

    chain(
        load_to_warehouse(extract_to_lake()),
        dbt_run,
        dbt_test,
    )


cripto_elt()
