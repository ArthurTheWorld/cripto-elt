"""Camada raw do warehouse: carga idempotente do snapshot bruto no Postgres.

A tabela `raw.coingecko_mercado` guarda o payload inteiro em JSONB. O dbt
"explode" esse JSON nas camadas seguintes (staging -> marts), o que mantém
o Postgres como fonte da verdade modelada e o data lake como arquivo histórico.

Idempotência
------------
A chave primária é `ingested_at`, que vem do `data_interval_start` da DAG
(não do relógio da máquina). Rodar a DAG de novo para a mesma hora faz
UPSERT do mesmo snapshot em vez de duplicar linhas — e o `dbt test` valida
que não existem duplicatas.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import psycopg2
from psycopg2 import sql

from etl.config import Settings

log = logging.getLogger(__name__)

SCHEMA = "raw"
TABLE = "coingecko_mercado"

DDL = f"""
create schema if not exists {SCHEMA};

create table if not exists {SCHEMA}.{TABLE} (
    ingested_at timestamptz not null,
    source      text        not null default 'coingecko',
    row_count   integer     not null,
    payload     jsonb       not null,
    loaded_at   timestamptz not null default now(),
    constraint {TABLE}_pk primary key (ingested_at)
);

create index if not exists idx_{TABLE}_loaded_at on {SCHEMA}.{TABLE} (loaded_at desc);
"""

UPSERT = f"""
insert into {SCHEMA}.{TABLE} (ingested_at, source, row_count, payload)
values (%s, %s, %s, %s::jsonb)
on conflict (ingested_at) do update
   set payload   = excluded.payload,
       row_count = excluded.row_count,
       source    = excluded.source,
       loaded_at = now();
"""


def connect(settings: Settings):
    """Abre uma conexão com o data warehouse (autocommit desligado)."""
    conn = psycopg2.connect(settings.dw_dsn)
    log.info("Conectado ao warehouse %s:%s/%s", settings.dw_host, settings.dw_port, settings.dw_db)
    return conn


def ensure_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(DDL)
    conn.commit()
    log.info("Schema raw.%s garantido", TABLE)


def load_snapshot(
    conn,
    *,
    ingested_at: datetime,
    payload: list[dict[str, Any]],
    source: str = "coingecko",
) -> int:
    """Faz UPSERT de um snapshot e devolve o row_count gravado."""
    if ingested_at.tzinfo is None:
        raise ValueError("ingested_at precisa ser timezone-aware.")

    with conn.cursor() as cur:
        cur.execute(
            UPSERT,
            (
                ingested_at,
                source,
                len(payload),
                json.dumps(payload, ensure_ascii=False),
            ),
        )
    conn.commit()

    log.info(
        "Snapshot de %s gravado em raw.%s (%d moedas)",
        ingested_at.isoformat(),
        TABLE,
        len(payload),
    )
    return len(payload)


def count_snapshots(conn) -> int:
    with conn.cursor() as cur:
        cur.execute(sql.SQL("select count(*) from {}.{}").format(
            sql.Identifier(SCHEMA), sql.Identifier(TABLE)
        ))
        return int(cur.fetchone()[0])
