"""Configuração central do pipeline, sempre lida de variáveis de ambiente.

Nada de segredo hardcoded: localmente as variáveis vêm do arquivo `.env`
(via docker-compose); em produção viriam do Airflow Connections, Secrets
Backend ou do orquestrador de nuvem.

Os nomes são genéricos (`S3_*`) de propósito: o storage é qualquer serviço
compatível com S3 — RustFS local, AWS S3, GCS ou Cloudflare R2.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _get_str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw else default


def _get_bool(name: str, default: bool = False) -> bool:
    return _get_str(name, str(default)).lower() in {"1", "true", "yes", "sim"}


@dataclass(frozen=True)
class Settings:
    """Configuração imutável do pipeline (um objeto por execução)."""

    # --- Data lake (API S3) ---
    s3_endpoint: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str
    s3_secure: bool

    # --- Postgres / data warehouse ---
    dw_host: str
    dw_port: int
    dw_db: str
    dw_user: str
    dw_password: str

    # --- CoinGecko ---
    coingecko_api_url: str
    coingecko_api_key: str
    coingecko_per_page: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            s3_endpoint=_get_str("S3_ENDPOINT", "localhost:9000"),
            s3_access_key=_get_str("S3_ACCESS_KEY", "admin"),
            s3_secret_key=_get_str("S3_SECRET_KEY", "admin12345"),
            s3_bucket=_get_str("S3_BUCKET", "bronze"),
            s3_secure=_get_bool("S3_SECURE", False),
            dw_host=_get_str("DW_HOST", "localhost"),
            dw_port=_get_int("DW_PORT", 5432),
            dw_db=_get_str("DW_DB", "warehouse"),
            dw_user=_get_str("DW_USER", "dw"),
            dw_password=_get_str("DW_PASSWORD", "dw12345"),
            coingecko_api_url=_get_str(
                "COINGECKO_API_URL",
                "https://api.coingecko.com/api/v3/coins/markets",
            ),
            coingecko_api_key=_get_str("COINGECKO_API_KEY", ""),
            coingecko_per_page=_get_int("COINGECKO_PER_PAGE", 100),
        )

    @property
    def dw_dsn(self) -> str:
        """String de conexão no formato esperado pelo psycopg2."""
        return (
            f"host={self.dw_host} port={self.dw_port} dbname={self.dw_db} "
            f"user={self.dw_user} password={self.dw_password}"
        )
