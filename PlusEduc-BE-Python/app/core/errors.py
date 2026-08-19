import logging
from datetime import datetime, timezone

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _error_body(status: int, error: str, message: str, details=None) -> dict:
    body = {
        "timestamp": _timestamp(),
        "status": status,
        "error": error,
        "message": message,
    }
    if details is not None:
        body["details"] = details
    return body


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "Erro HTTP"
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.status_code, "HTTP Error", detail),
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        {
            "loc": list(error.get("loc", [])),
            "msg": error.get("msg", "Valor inválido"),
            "type": error.get("type", "validation_error"),
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=_error_body(
            422,
            "Validation Error",
            "Erro de validação da requisição",
            details,
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Erro interno não tratado em %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=_error_body(500, "Internal Server Error", "Erro interno do servidor"),
    )
