"""Banco usado pelos testes que acessam o MongoDB real.

Por padrão é o escola_db (ambiente de desenvolvimento). Para rodar a suíte contra um banco
descartável, sem tocar nos dados de demonstração, defina MONGODB_DATABASE (ou
TEST_MONGODB_DATABASE) antes de executar o pytest.
"""

import os

TEST_DATABASE = os.getenv("TEST_MONGODB_DATABASE") or os.getenv("MONGODB_DATABASE") or "escola_db"
