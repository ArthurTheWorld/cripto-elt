"""Testes da configuração lida do ambiente."""

from __future__ import annotations

from etl.config import Settings


def test_from_env_usa_defaults(monkeypatch):
    for variavel in (
        "S3_ENDPOINT",
        "S3_BUCKET",
        "DW_HOST",
        "DW_PORT",
        "DW_DB",
        "COINGECKO_PER_PAGE",
    ):
        monkeypatch.delenv(variavel, raising=False)

    settings = Settings.from_env()

    assert settings.s3_bucket == "bronze"
    assert settings.dw_port == 5432
    assert settings.coingecko_per_page == 100


def test_from_env_respeita_variaveis(monkeypatch):
    monkeypatch.setenv("DW_HOST", "dw.interno")
    monkeypatch.setenv("DW_PORT", "6543")
    monkeypatch.setenv("DW_DB", "analytics")
    monkeypatch.setenv("COINGECKO_PER_PAGE", "250")
    monkeypatch.setenv("S3_BUCKET", "lake-prod")

    settings = Settings.from_env()

    assert settings.dw_host == "dw.interno"
    assert settings.dw_port == 6543
    assert settings.dw_db == "analytics"
    assert settings.coingecko_per_page == 250
    assert settings.s3_bucket == "lake-prod"


def test_dsn_contem_todos_os_campos(monkeypatch):
    monkeypatch.setenv("DW_HOST", "dw")
    monkeypatch.setenv("DW_PORT", "5432")
    monkeypatch.setenv("DW_DB", "warehouse")
    monkeypatch.setenv("DW_USER", "dw")
    monkeypatch.setenv("DW_PASSWORD", "segredo")

    dsn = Settings.from_env().dw_dsn

    assert "host=dw" in dsn
    assert "dbname=warehouse" in dsn
    assert "password=segredo" in dsn
