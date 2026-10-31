"""Testes do contrato de dados e da validação do snapshot."""

from __future__ import annotations

import copy

import pytest

from etl import coingecko


def test_normalize_mantem_apenas_campos_do_contrato(mercado_bruto):
    registros = coingecko.normalize(mercado_bruto)

    assert len(registros) == 4  # a moeda sem market_cap é descartada
    assert set(registros[0]) == set(coingecko.CONTRACT_FIELDS)
    assert "high_24h" not in registros[0]


def test_normalize_descarta_registro_incompleto(mercado_bruto):
    registros = coingecko.normalize(mercado_bruto)
    ids = {registro["id"] for registro in registros}

    assert "moeda-quebrada" not in ids
    assert ids == {"bitcoin", "ethereum", "tether", "solana"}


def test_normalize_ignora_itens_que_nao_sao_dicionario(mercado_bruto):
    entrada = mercado_bruto + ["lixo", 42, None]

    registros = coingecko.normalize(entrada)

    assert len(registros) == 4


def test_normalize_preserva_valores_da_origem(mercado_bruto):
    bitcoin = next(r for r in coingecko.normalize(mercado_bruto) if r["id"] == "bitcoin")

    assert bitcoin["symbol"] == "btc"
    assert bitcoin["current_price"] == 67234.12
    assert bitcoin["last_updated"] == "2026-10-31T09:00:00.000Z"


def test_validate_aceita_snapshot_saudavel(mercado_bruto):
    registros = coingecko.normalize(mercado_bruto)

    coingecko.validate(registros, min_records=4)  # não deve levantar


def test_validate_rejeita_snapshot_vazio():
    with pytest.raises(ValueError, match="Snapshot vazio"):
        coingecko.validate([], min_records=1)


def test_validate_rejeita_poucas_moedas(mercado_bruto):
    registros = coingecko.normalize(mercado_bruto)

    with pytest.raises(ValueError, match="Snapshot suspeito"):
        coingecko.validate(registros, min_records=50)


def test_validate_rejeita_ids_duplicados(mercado_bruto):
    registros = coingecko.normalize(mercado_bruto)
    registros.append(copy.deepcopy(registros[0]))

    with pytest.raises(ValueError, match="duplicados"):
        coingecko.validate(registros, min_records=1)


def test_validate_rejeita_preco_invalido(mercado_bruto):
    registros = coingecko.normalize(mercado_bruto)
    registros[0]["current_price"] = 0

    with pytest.raises(ValueError, match="Preços inválidos"):
        coingecko.validate(registros, min_records=1)
