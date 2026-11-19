from datetime import datetime, timedelta, timezone
from typing import Any

import uuid

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.core.config import Settings

ALGORITHM = "HS256"
ACCESS_TOKEN = "access"
REFRESH_TOKEN = "refresh"


class TokenError(ValueError):
    """Erro controlado de token inválido ou expirado."""


def _secret(settings: Settings) -> str:
    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET não configurado")
    return settings.jwt_secret


def _create_token(
    subject: str,
    settings: Settings,
    expiration_ms: int,
    token_type: str,
    extra: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + timedelta(milliseconds=expiration_ms),
        "jti": uuid.uuid4().hex,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, _secret(settings), algorithm=ALGORITHM)


def create_access_token(subject: str, settings: Settings, token_version: int = 0) -> str:
    """``ver`` acompanha ``users.tokenVersion``: trocar a senha ou desativar a conta invalida o token."""
    return _create_token(subject, settings, settings.jwt_expiration_ms, ACCESS_TOKEN, {"ver": token_version})


def create_refresh_token(
    subject: str,
    settings: Settings,
    token_version: int = 0,
    family: str | None = None,
) -> str:
    """Refresh token rotativo: ``fam`` identifica a cadeia de renovações de um mesmo login."""
    return _create_token(
        subject,
        settings,
        settings.jwt_refresh_expiration_ms,
        REFRESH_TOKEN,
        {"ver": token_version, "fam": family or uuid.uuid4().hex},
    )


def decode_token(token: str, settings: Settings, expected_type: str = ACCESS_TOKEN) -> dict[str, Any]:
    """Valida assinatura, validade e finalidade do token (acesso x refresh)."""
    try:
        payload = jwt.decode(token, _secret(settings), algorithms=[ALGORITHM])
    except ExpiredSignatureError as exc:
        raise TokenError("Token expirado") from exc
    except InvalidTokenError as exc:
        raise TokenError("Token inválido") from exc
    # O refresh token (7 dias) não pode abrir a API: só serve para renovar o acesso.
    if payload.get("type") != expected_type:
        raise TokenError("Tipo de token inválido")
    return payload
