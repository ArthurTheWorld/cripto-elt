"""Fixtures compartilhadas dos testes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def mercado_bruto() -> list[dict]:
    """Resposta simulada da CoinGecko (5 moedas, uma delas inválida)."""
    with open(FIXTURES / "mercado_exemplo.json", encoding="utf-8") as arquivo:
        return json.load(arquivo)
