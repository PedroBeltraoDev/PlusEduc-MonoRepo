from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.core.config import Settings

ALGORITHM = "HS256"


class TokenError(ValueError):
    """Erro controlado de token inválido ou expirado."""


def _secret(settings: Settings) -> str:
    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET não configurado")
    return settings.jwt_secret


def _create_token(subject: str, settings: Settings, expiration_ms: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(milliseconds=expiration_ms),
    }
    return jwt.encode(payload, _secret(settings), algorithm=ALGORITHM)


def create_access_token(subject: str, settings: Settings) -> str:
    return _create_token(subject, settings, settings.jwt_expiration_ms)


def create_refresh_token(subject: str, settings: Settings) -> str:
    return _create_token(subject, settings, settings.jwt_refresh_expiration_ms)


def decode_token(token: str, settings: Settings) -> dict[str, Any]:
    try:
        return jwt.decode(token, _secret(settings), algorithms=[ALGORITHM])
    except ExpiredSignatureError as exc:
        raise TokenError("Token expirado") from exc
    except InvalidTokenError as exc:
        raise TokenError("Token inválido") from exc
