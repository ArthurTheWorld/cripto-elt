"""Testes da composição de caminhos na camada bronze."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from etl.storage import build_partition_key


def test_particao_por_data_e_hora():
    momento = datetime(2026, 10, 31, 14, 30, tzinfo=timezone.utc)

    chave = build_partition_key("coingecko/mercado", momento)

    assert chave == "coingecko/mercado/dt=2026-10-31/hora=14/mercado.json.gz"


def test_prefixo_com_barra_final_nao_duplica_barra():
    momento = datetime(2026, 1, 5, 3, 0, tzinfo=timezone.utc)

    chave = build_partition_key("coingecko/mercado/", momento)

    assert chave.startswith("coingecko/mercado/dt=")
    assert "//" not in chave


def test_timestamp_sem_timezone_e_erro():
    with pytest.raises(ValueError, match="timezone-aware"):
        build_partition_key("coingecko", datetime(2026, 1, 1, 0, 0))
