"""Cria (ou reativa) uma conta de ADMINISTRADOR do PlusEduc.

O administrador aprova os cadastros públicos de professor (RF04), vê o histórico de todos os usuários e
tem acesso às mesmas telas de gestão do professor. O sistema não cria administrador sozinho: rode este
script uma vez por instalação.

Uso (a partir de PlusEduc-BE-Python, com o .venv ativo):

    python scripts/create_admin.py --email admin@escola.local --name "Coordenação"

A senha é lida de PLUSEDUC_ADMIN_PASSWORD ou pedida no terminal (nunca vai como argumento, para não
ficar no histórico do shell). O banco é o de MONGODB_URI / MONGODB_DATABASE (o mesmo .env da API).
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from pymongo import MongoClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings  # noqa: E402
from app.core.passwords import hash_password  # noqa: E402
from app.schemas.validators import validate_email_format  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Cria ou reativa uma conta ADMIN do PlusEduc")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default="Administrador")
    args = parser.parse_args()

    email = args.email.strip().lower()
    try:
        validate_email_format(email)
    except ValueError:
        print(f"E-mail inválido: {email}", file=sys.stderr)
        return 2

    password = os.getenv("PLUSEDUC_ADMIN_PASSWORD") or getpass.getpass("Senha do administrador (mín. 6): ")
    if len(password) < 6:
        print("A senha precisa ter pelo menos 6 caracteres.", file=sys.stderr)
        return 2

    settings = get_settings()
    client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
    users = client[settings.mongodb_database]["users"]
    now = datetime.now(timezone.utc)
    existing = users.find_one({"email": email})
    if existing and existing.get("role") not in (None, "ADMIN"):
        print(f"{email} já pertence a uma conta {existing.get('role')}; use outro e-mail.", file=sys.stderr)
        return 1
    users.update_one(
        {"email": email},
        {
            "$set": {
                "email": email,
                "password": hash_password(password),
                "role": "ADMIN",
                "name": args.name,
                "active": True,
                "updatedAt": now,
            },
            "$setOnInsert": {"createdAt": now},
            "$unset": {"pendingApproval": ""},
        },
        upsert=True,
    )
    action = "atualizada" if existing else "criada"
    print(f"Conta ADMIN {action}: {email} (banco {settings.mongodb_database})")
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
