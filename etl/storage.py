"""Camada bronze: persistência do JSON cru no data lake (API S3).

O cliente é genérico: funciona com RustFS local, AWS S3, GCS (interoperável)
ou Cloudflare R2. Nada aqui depende do fornecedor — só do protocolo S3.

A ideia do data lake é guardar o dado *como veio* da origem, com o mínimo de
transformação. Se amanhã descobrirmos que precisávamos de um campo que foi
descartado na silver, o bronze permite reprocessar tudo sem chamar a API de
novo (e sem depender de a API ainda devolver aquele histórico).
"""

from __future__ import annotations

import gzip
import json
import logging
from datetime import datetime
from typing import Any

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import ClientError

log = logging.getLogger(__name__)


def build_client(
    endpoint: str,
    access_key: str,
    secret_key: str,
    *,
    secure: bool = False,
) -> BaseClient:
    """Cria um cliente S3 apontando para qualquer storage compatível."""
    scheme = "https" if secure else "http"
    return boto3.client(
        "s3",
        endpoint_url=f"{scheme}://{endpoint}",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1",
        config=Config(
            signature_version="s3v4",
            # path-style evita depender de DNS por bucket (ex.: bucket.localhost)
            s3={"addressing_style": "path"},
            retries={"max_attempts": 5, "mode": "standard"},
            connect_timeout=10,
            read_timeout=60,
        ),
    )


def ensure_bucket(client: BaseClient, bucket: str) -> None:
    """Cria o bucket se ele não existir (idempotente)."""
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") not in {"404", "NoSuchBucket"}:
            raise
        client.create_bucket(Bucket=bucket)
        log.info("Bucket %s criado", bucket)


def build_partition_key(prefix: str, moment: datetime) -> str:
    """Monta a chave particionada por data/hora: `prefixo/dt=YYYY-MM-DD/hora=HH/...`."""
    if moment.tzinfo is None:
        raise ValueError("O timestamp de ingestão precisa ser timezone-aware (UTC).")
    return f"{prefix.rstrip('/')}/dt={moment:%Y-%m-%d}/hora={moment:%H}/mercado.json.gz"


def upload_json(client: BaseClient, bucket: str, key: str, payload: Any) -> str:
    """Grava o payload como JSON comprimido (gzip) e devolve a chave."""
    body = gzip.compress(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType="application/json",
        ContentEncoding="gzip",
    )
    log.info(
        "Gravado em s3://%s/%s (%d bytes comprimidos, %d registros)",
        bucket,
        key,
        len(body),
        len(payload) if isinstance(payload, list) else 1,
    )
    return key


def download_json(client: BaseClient, bucket: str, key: str) -> Any:
    """Lê de volta um objeto JSON gzip da camada bronze."""
    response = client.get_object(Bucket=bucket, Key=key)
    return json.loads(gzip.decompress(response["Body"].read()))


def object_exists(client: BaseClient, bucket: str, key: str) -> bool:
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError:
        return False
