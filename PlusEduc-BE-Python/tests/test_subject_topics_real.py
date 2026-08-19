from uuid import uuid4

from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.core.config import Settings
from app.core.jwt import create_access_token
from app.main import create_app


class FakeUserRepository:
    def __init__(self, users: list[dict]):
        self.users = {item["email"]: item for item in users}

    def find_active_by_email(self, email: str):
        user = self.users.get(email)
        if user is None or user.get("active", True) is False:
            return None
        return user


def test_subject_topics_crud_on_real_mongodb():
    owner_email = f"catalog-test-{uuid4().hex}@example.com"
    settings = Settings(
        app_env="test-subject-topics",
        mongodb_uri="mongodb://localhost:27017",
        mongodb_database="escola_db",
        mongodb_required=True,
        mongodb_server_selection_timeout_ms=3000,
        mongodb_connect_timeout_ms=3000,
        jwt_secret="test-subject-topics-secret",
    )
    mongo = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000)
    user = {
        "_id": "catalog-test-user",
        "email": owner_email,
        "role": "TEACHER",
        "active": True,
    }
    token = create_access_token(owner_email, settings)
    headers = {"Authorization": f"Bearer {token}"}
    db = None
    owner_key = str(user["_id"]).lower()

    try:
        mongo.admin.command("ping")
        db = mongo[settings.mongodb_database]
        db.subject_topics.delete_many({"owner_key": owner_key})
        app = create_app(settings, user_repository=FakeUserRepository([user]))

        with TestClient(app) as client:
            created = client.post(
                "/api/subject-topics",
                json={"subject": "Matemática", "topic": "Equações"},
                headers=headers,
            )
            assert created.status_code == 201, created.text
            item = created.json()
            assert item["subject"] == "Matemática"
            assert item["topics"] == ["Equações"]
            item_id = item["id"]

            duplicate = client.post(
                "/api/subject-topics",
                json={"subject": " matemática ", "topic": "Funções"},
                headers=headers,
            )
            assert duplicate.status_code == 201, duplicate.text
            assert duplicate.json()["id"] == item_id
            assert duplicate.json()["topics"] == ["Equações", "Funções"]

            accent_duplicate = client.post(
                "/api/subject-topics",
                json={"subject": "Matematica", "topic": "Geometria"},
                headers=headers,
            )
            assert accent_duplicate.status_code == 201, accent_duplicate.text
            assert accent_duplicate.json()["id"] == item_id
            assert accent_duplicate.json()["topics"] == ["Equações", "Funções", "Geometria"]

            listed = client.get("/api/subject-topics", headers=headers)
            assert listed.status_code == 200, listed.text
            assert len(listed.json()) == 1

            updated = client.put(
                f"/api/subject-topics/{item_id}",
                json={"subject": "Matemática Básica", "topics": ["Funções"]},
                headers=headers,
            )
            assert updated.status_code == 200, updated.text
            assert updated.json()["subject"] == "Matemática Básica"
            assert updated.json()["topics"] == ["Funções"]

            deleted = client.delete(f"/api/subject-topics/{item_id}", headers=headers)
            assert deleted.status_code == 204, deleted.text
            assert client.get("/api/subject-topics", headers=headers).json() == []
    finally:
        if db is not None:
            db.subject_topics.delete_many({"owner_key": owner_key})
            db.subjects.delete_many({"created_by": owner_email})
        mongo.close()


def test_subject_topic_creation_syncs_subject_catalog():
    owner_email = f"catalog-sync-{uuid4().hex}@example.com"
    subject_name = f"Matemática {uuid4().hex[:8]}"
    settings = Settings(
        app_env="test-subject-topic-sync",
        mongodb_uri="mongodb://localhost:27017",
        mongodb_database="escola_db",
        mongodb_required=True,
        mongodb_server_selection_timeout_ms=3000,
        mongodb_connect_timeout_ms=3000,
        jwt_secret="test-subject-topic-sync-secret",
    )
    mongo = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000)
    user = {"_id": "catalog-sync-user", "email": owner_email, "role": "TEACHER", "active": True}
    token = create_access_token(owner_email, settings)
    headers = {"Authorization": f"Bearer {token}"}
    owner_key = user["_id"].lower()
    db = None

    try:
        mongo.admin.command("ping")
        db = mongo[settings.mongodb_database]
        app = create_app(settings, user_repository=FakeUserRepository([user]))
        with TestClient(app) as client:
            created = client.post(
                "/api/subject-topics",
                json={"subject": subject_name, "topic": "Tópico de sincronização"},
                headers=headers,
            )
            assert created.status_code == 201, created.text

            catalog = client.get("/api/subjects", headers=headers)
            assert catalog.status_code == 200, catalog.text
            assert any(item["name"] == subject_name for item in catalog.json())
    finally:
        if db is not None:
            db.subject_topics.delete_many({"owner_key": owner_key})
            db.subjects.delete_many({"created_by": owner_email})
        mongo.close()


def test_subject_topics_list_does_not_create_subject_catalog_entry():
    owner_email = f"topic-list-{uuid4().hex}@example.com"
    owner_key = "topic-list-test-user"
    subject_name = f"Materia sem efeito {uuid4().hex[:8]}"
    settings = Settings(
        app_env="test-subject-topic-list",
        mongodb_uri="mongodb://localhost:27017",
        mongodb_database="escola_db",
        mongodb_required=True,
        mongodb_server_selection_timeout_ms=3000,
        mongodb_connect_timeout_ms=3000,
        jwt_secret="test-subject-topic-list-secret",
    )
    mongo = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000)
    db = None

    try:
        mongo.admin.command("ping")
        db = mongo[settings.mongodb_database]
        db.subject_topics.delete_many({"owner_key": owner_key})
        db.subjects.delete_many({"name_normalized": subject_name.casefold()})
        db.subject_topics.insert_one({
            "subject": subject_name,
            "subject_normalized": subject_name.casefold(),
            "topics": ["Tópico"],
            "owner_key": owner_key,
            "created_by": owner_email,
        })
        user = {"_id": owner_key, "email": owner_email, "role": "TEACHER", "active": True}
        token = create_access_token(owner_email, settings)
        app = create_app(settings, user_repository=FakeUserRepository([user]))

        with TestClient(app) as client:
            listed = client.get("/api/subject-topics", headers={"Authorization": f"Bearer {token}"})
            assert listed.status_code == 200, listed.text
            assert listed.json()[0]["subject"] == subject_name
            assert db.subjects.find_one({"name_normalized": subject_name.casefold()}) is None
    finally:
        if db is not None:
            db.subject_topics.delete_many({"owner_key": owner_key})
            db.subjects.delete_many({"name_normalized": subject_name.casefold()})
        mongo.close()
