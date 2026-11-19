"""Limite de tentativas em memória para login, cadastro e recuperação de senha.

Janela deslizante por chave (ex.: ``login:<ip>:<email>``). Só as falhas contam no login, então um
usuário que acerta a senha não é bloqueado. Para vários processos/servidores, troque por um
armazenamento compartilhado (Redis); para um único processo Uvicorn isto basta.
"""

from __future__ import annotations

import threading
import time
from collections import deque

from fastapi import HTTPException, Request, status


class RateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str, window: float, now: float) -> deque[float]:
        events = self._events.setdefault(key, deque())
        while events and now - events[0] > window:
            events.popleft()
        return events

    def is_blocked(self, key: str, limit: int, window: float) -> float:
        """Devolve os segundos restantes de bloqueio (0 quando liberado)."""
        now = time.monotonic()
        with self._lock:
            events = self._prune(key, window, now)
            if len(events) >= limit:
                return max(1.0, window - (now - events[0]))
            return 0.0

    def hit(self, key: str, window: float) -> None:
        now = time.monotonic()
        with self._lock:
            self._prune(key, window, now).append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)

    def check_and_hit(self, key: str, limit: int, window: float) -> None:
        retry = self.is_blocked(key, limit, window)
        if retry:
            raise too_many(retry)
        self.hit(key, window)


def too_many(retry_after: float) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Muitas tentativas. Aguarde alguns minutos e tente novamente.",
        headers={"Retry-After": str(int(retry_after))},
    )


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def limiter_of(request: Request) -> RateLimiter | None:
    settings = request.app.state.settings
    if not getattr(settings, "rate_limit_enabled", True):
        return None
    limiter = getattr(request.app.state, "rate_limiter", None)
    if limiter is None:
        limiter = RateLimiter()
        request.app.state.rate_limiter = limiter
    return limiter
