"""Cliente da API CoinGecko: extração, normalização e validação do snapshot.

Por que validar aqui e não só no dbt?
-------------------------------------
A validação na origem (contrato de dados) impede que uma mudança silenciosa
da API contamine as camadas seguintes. Se a CoinGecko renomear um campo, o
pipeline falha alto e cedo — em vez de gravar `null` no lake e o erro só
aparecer três dias depois num dashboard.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)

DEFAULT_URL = "https://api.coingecko.com/api/v3/coins/markets"

DEFAULT_PARAMS: dict[str, str] = {
    "vs_currency": "usd",
    "order": "market_cap_desc",
    "per_page": "100",
    "page": "1",
    "sparkline": "false",
    "price_change_percentage": "24h",
}

# Contrato de dados: tudo que a camada silver consome.
CONTRACT_FIELDS: tuple[str, ...] = (
    "id",
    "symbol",
    "name",
    "current_price",
    "market_cap",
    "market_cap_rank",
    "total_volume",
    "price_change_percentage_24h",
    "circulating_supply",
    "last_updated",
)

# Sem estes campos o registro é descartado (não tem como modelar a linha).
REQUIRED_FIELDS: tuple[str, ...] = (
    "id",
    "symbol",
    "name",
    "current_price",
    "market_cap",
    "last_updated",
)


def build_session(total_retries: int = 5, backoff_factor: float = 1.0) -> requests.Session:
    """Sessão HTTP com retry exponencial para 429/5xx e respeitando Retry-After."""
    retry = Retry(
        total=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)

    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(
        {
            "Accept": "application/json",
            "User-Agent": "cripto-elt/1.0 (+pipeline de estudo)",
        }
    )
    return session


def fetch_market_snapshot(
    *,
    url: str = DEFAULT_URL,
    params: dict[str, str] | None = None,
    api_key: str = "",
    timeout: int = 30,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    """Baixa o snapshot atual de mercado e devolve a lista crua de moedas."""
    http = session or build_session()
    query = {**DEFAULT_PARAMS, **(params or {})}

    headers: dict[str, str] = {}
    if api_key:
        # A demo key da CoinGecko vai no header (não na query string).
        headers["x-cg-demo-api-key"] = api_key

    log.info("GET %s params=%s", url, query)
    response = http.get(url, params=query, headers=headers, timeout=timeout)

    if response.status_code == 429:
        raise RuntimeError(
            "CoinGecko respondeu 429 (rate limit). Reduza a frequência do DAG "
            "ou configure COINGECKO_API_KEY para aumentar o limite."
        )

    response.raise_for_status()
    payload = response.json()

    if not isinstance(payload, list):
        raise ValueError(
            f"Resposta inesperada da CoinGecko: esperava uma lista, "
            f"recebi {type(payload).__name__}."
        )

    log.info("CoinGecko devolveu %d moedas", len(payload))
    return payload


def normalize(payload: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Seleciona apenas os campos do contrato e descarta registros incompletos."""
    itens = list(payload)
    registros: list[dict[str, Any]] = []

    for item in itens:
        if not isinstance(item, dict):
            continue
        if any(item.get(campo) is None for campo in REQUIRED_FIELDS):
            continue

        registro = {campo: item.get(campo) for campo in CONTRACT_FIELDS}

        if not registro["id"] or not registro["symbol"]:
            continue

        registros.append(registro)

    log.info("Normalização: %d registros válidos de %d recebidos", len(registros), len(itens))
    return registros


def validate(registros: list[dict[str, Any]], *, min_records: int = 50) -> None:
    """Garante que o snapshot é utilizável antes de gravar qualquer coisa.

    Levanta ValueError com mensagem acionável — o Airflow marca a task como
    falha e o retry acontece, mas nada de lixo chega à camada bronze.
    """
    if not registros:
        raise ValueError("Snapshot vazio: nenhuma moeda válida retornada pela API.")

    ids = [registro["id"] for registro in registros]
    duplicados = {moeda for moeda in ids if ids.count(moeda) > 1}
    if duplicados:
        raise ValueError(f"Snapshot com ids duplicados: {sorted(duplicados)[:5]}")

    if len(registros) < min_records:
        raise ValueError(
            f"Snapshot suspeito: apenas {len(registros)} moedas "
            f"(mínimo esperado: {min_records})."
        )

    precos_invalidos = [
        registro["id"]
        for registro in registros
        if not isinstance(registro["current_price"], (int, float))
        or registro["current_price"] <= 0
    ]
    if precos_invalidos:
        raise ValueError(
            f"Preços inválidos para: {precos_invalidos[:5]} "
            f"(total: {len(precos_invalidos)})."
        )
