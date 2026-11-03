import re

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_email_format(value: str | None) -> str | None:
    """Recusa e-mail sem arroba, sem domínio ou com espaços (a Sprint 09 achou cadastros com \"abc\")."""
    if value is None:
        return value
    if not _EMAIL.match(value.strip()):
        raise ValueError("E-mail inválido")
    return value
