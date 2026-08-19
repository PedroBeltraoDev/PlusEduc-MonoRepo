import bcrypt


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str | bytes) -> bool:
    if not plain_password or not password_hash:
        return False
    encoded_hash = (
        password_hash.encode("utf-8")
        if isinstance(password_hash, str)
        else password_hash
    )
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), encoded_hash)
    except (ValueError, TypeError):
        return False
