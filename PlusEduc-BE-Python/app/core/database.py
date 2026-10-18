import logging

from pymongo import MongoClient
from pymongo.errors import OperationFailure, PyMongoError

from app.core.config import Settings

logger = logging.getLogger(__name__)

# Campos filtrados pelos repositórios (inclusive as duas grafias, snake_case e camelCase, que o
# legado usa dentro de $or: cada ramo do $or precisa do próprio índice, senão a consulta vira scan).
PERFORMANCE_INDEXES: dict[str, tuple[str, ...]] = {
    "users": ("email",),
    "teachers": ("email",),
    "students": ("email", "class_id", "classId"),
    "classrooms": ("teacher_id", "students"),
    "grades": ("studentId", "classroomId", "activityId"),
    "activities": ("classroom_id", "classroomId", "student_id", "studentId", "created_by"),
    "activity_submissions": ("activity_id", "activityId", "student_id", "studentId"),
}


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
            matricula_index_exists = any(
                index.get("key", {}).get("matricula") == 1 and index.get("unique") is True
                for index in self._database["students"].list_indexes()
            )
            if not matricula_index_exists:
                self._database["students"].create_index(
                    "matricula",
                    unique=True,
                    sparse=True,
                    name="students_matricula_unique",
                )
            self.ensure_performance_indexes()
            logger.info("Conexão MongoDB inicializada")
        except PyMongoError as exc:
            logger.warning("MongoDB indisponível durante o startup: %s", type(exc).__name__)
            if self._settings.mongodb_required:
                self.close()
                raise

    def ensure_performance_indexes(self) -> None:
        """Cria índices simples nas coleções que já existem (nunca cria coleções novas).

        Um índice equivalente já existente (outro nome ou opções, como ``unique``) é respeitado.
        """
        existing = set(self._database.list_collection_names())
        for collection, fields in PERFORMANCE_INDEXES.items():
            if collection not in existing:
                continue
            for field in fields:
                try:
                    self._database[collection].create_index(field)
                except OperationFailure as exc:
                    logger.debug("Índice %s.%s não criado: %s", collection, field, exc.code)

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
