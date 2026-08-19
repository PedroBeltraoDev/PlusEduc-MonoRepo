import logging

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.core.config import Settings

logger = logging.getLogger(__name__)


class MongoConnection:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: MongoClient | None = None
        self._database = None

    def connect(self) -> None:
        self._client = MongoClient(
            self._settings.mongodb_uri,
            connectTimeoutMS=self._settings.mongodb_connect_timeout_ms,
            serverSelectionTimeoutMS=self._settings.mongodb_server_selection_timeout_ms,
            tz_aware=True,
        )
        try:
            self._client.admin.command("ping")
            self._database = self._client[self._settings.mongodb_database]
            logger.info("Conexão MongoDB inicializada")
        except PyMongoError as exc:
            logger.warning("MongoDB indisponível durante o startup: %s", type(exc).__name__)
            if self._settings.mongodb_required:
                self.close()
                raise

    def health(self) -> str:
        if self._client is None:
            return "not_configured"
        try:
            self._client.admin.command("ping")
            return "ok"
        except PyMongoError as exc:
            logger.debug("Falha no ping MongoDB: %s", type(exc).__name__)
            return "degraded"

    @property
    def database(self):
        if self._database is None:
            raise RuntimeError("MongoDB não está conectado")
        return self._database

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
        self._client = None
        self._database = None
