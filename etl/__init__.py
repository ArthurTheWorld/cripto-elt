"""Pipeline ELT de mercado de criptomoedas.

Módulos:
    config    -- leitura das variáveis de ambiente
    coingecko -- extração e validação do snapshot da API
    storage   -- gravação/leitura do JSON na camada bronze (S3)
    warehouse -- carga do snapshot bruto no Postgres (camada raw)
"""

__version__ = "1.0.0"
