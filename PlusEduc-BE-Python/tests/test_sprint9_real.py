"""Sprint 9 (MongoDB real, banco de testes): excluir a atividade apaga as respostas dela, sem órfãs."""
import pytest
from pymongo import MongoClient

from app.core.config import Settings
from app.core.database import MongoConnection
from app.repositories.activity_submission_repository import ActivitySubmissionRepository
from tests.database import TEST_DATABASE


@pytest.fixture
def submissions():
    settings = Settings(app_env="test-sprint9", mongodb_uri="mongodb://localhost:27017", mongodb_database=TEST_DATABASE,
                        mongodb_required=True, mongodb_server_selection_timeout_ms=3000, mongodb_connect_timeout_ms=3000, jwt_secret="x" * 32)
    mongo = MongoConnection(settings)
    mongo.connect()
    client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000)
    collection = client[TEST_DATABASE].activity_submissions
    ids = ["sprint9-atividade-apagada", "sprint9-atividade-mantida"]
    collection.delete_many({"activity_id": {"$in": ids}})
    try:
        yield ActivitySubmissionRepository(mongo), collection, ids
    finally:
        collection.delete_many({"activity_id": {"$in": ids}})
        client.close()
        mongo.close()


def test_delete_by_activity_removes_only_that_activitys_submissions(submissions):
    repo, collection, (apagada, mantida) = submissions
    collection.insert_many([{"activity_id": apagada, "student_id": "s1"}, {"activity_id": apagada, "student_id": "s2"}, {"activity_id": mantida, "student_id": "s1"}])
    assert repo.delete_by_activity(apagada) == 2
    assert collection.count_documents({"activity_id": apagada}) == 0
    assert collection.count_documents({"activity_id": mantida}) == 1
    assert repo.delete_by_activity(apagada) == 0
