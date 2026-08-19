import httpx
import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from pymongo import MongoClient
from pypdf import PdfReader

from app.core.auth import UserPrincipal
from app.core.config import Settings
from app.dependencies import get_current_user
from app.main import create_app
from app.schemas.activity import GeneratedQuestion
from app.services.activity_service import ActivityService
from app.services.gemini_service import GeminiGenerationError, GeminiGenerationRequest, GeminiService


@pytest.fixture
def ai_pdf_real_context():
    settings = Settings(
        app_env="test-real-ai-pdf",
        mongodb_uri="mongodb://localhost:27017",
        mongodb_database="escola_db",
        mongodb_required=True,
        mongodb_server_selection_timeout_ms=3000,
        mongodb_connect_timeout_ms=3000,
        jwt_secret="test-ai-pdf-secret",
        gemini_api_key="",
        ai_demo_fallback_enabled=True,
    )
    mongo = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000)
    try:
        mongo.admin.command("ping")
        db = mongo[settings.mongodb_database]
        for collection in ["activities", "students", "teachers", "classrooms"]:
            assert collection in db.list_collection_names(), f"Collection {collection} não existe"
        student = db.students.find_one({})
        teacher = db.teachers.find_one({})
        classroom = db.classrooms.find_one({})
        assert student and teacher and classroom, "Dados reais são necessários"
        user = UserPrincipal(
            user_id=str(teacher["_id"]),
            email=str(teacher.get("email", "teacher@local")),
            role="TEACHER",
            student_id=None,
        )
        app = create_app(settings)
        app.dependency_overrides[get_current_user] = lambda: user
        with TestClient(app) as client:
            yield client, db, str(classroom["_id"]), str(student["_id"])
    finally:
        mongo.close()


def manual_activity_payload(classroom_id: str, student_id: str | None = None):
    return {
        "title": "Atividade PDF de Teste",
        "subject": "Matemática",
        "topic": "Equações",
        "difficultyLevel": "MEDIO",
        "questionsCount": 2,
        "format": "MULTIPLA_ESCOLHA",
        "classroomId": classroom_id,
        "studentId": student_id,
        "questions": [
            {
                "questionText": "Quanto é 2 + 2?",
                "questionType": "MULTIPLA_ESCOLHA",
                "options": ["A) 4", "B) 5", "C) 6", "D) 7"],
                "correctAnswer": "A",
                "explanation": "A soma de dois com dois resulta em quatro.",
                "difficultyLevel": "MEDIO",
            },
            {
                "questionText": "Explique o conceito de equação.",
                "questionType": "DISCURSIVA",
                "options": [],
                "correctAnswer": "Uma igualdade com incógnita.",
                "explanation": "A resposta deve apresentar o conceito.",
                "difficultyLevel": "MEDIO",
            },
        ],
    }


def test_gemini_provider_builds_payload_and_parses_json(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "candidates": [{
                    "content": {
                        "parts": [{"text": '''```json
[{"questionText":"Questão gerada","questionType":"DISCURSIVA","options":[],"correctAnswer":"resposta","explanation":"explicação","difficultyLevel":"MEDIO"}]
```'''}]
                    }
                }]
            }

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return FakeResponse()

    monkeypatch.setattr(httpx, "post", fake_post)
    service = GeminiService(api_key="configured-key")
    result = service.generate(GeminiGenerationRequest(
        subject="Matemática",
        topic="Equações",
        difficulty_level="MEDIO",
        questions_count=1,
        format="DISCURSIVA",
        learning_gaps="Matemática - Equações",
        disability_adaptations=("Dislexia",),
        additional_instructions="Use exemplos curtos",
    ))

    assert captured["url"] == "https://generativelanguage.googleapis.com/v1/models/gemini-3.5-flash-lite:generateContent"
    assert captured["kwargs"]["headers"]["X-goog-api-key"] == "configured-key"
    assert captured["kwargs"]["json"]["generationConfig"]["responseMimeType"] == "application/json"
    assert "Matemática - Equações" in captured["kwargs"]["json"]["contents"][0]["parts"][0]["text"]
    assert result[0].questionText == "Questão gerada"


def test_gemini_timeout_is_controlled(monkeypatch):
    def timeout(*args, **kwargs):
        raise httpx.ReadTimeout("read timed out")

    monkeypatch.setattr(httpx, "post", timeout)
    service = GeminiService(api_key="configured-key", read_timeout_seconds=0.01)
    with pytest.raises(GeminiGenerationError, match="Tempo limite"):
        service.generate(GeminiGenerationRequest("Matemática", "Equações", "MEDIO", 1, "DISCURSIVA"))


def test_learning_gap_text_is_included_in_generation_prompt():
    student = {"learningGaps": [{"subject": "Matemática", "topic": "Frações"}, {"subject": "Português", "topic": "Leitura"}]}
    learning_gaps = ActivityService.learning_gaps_text(student)
    prompt = GeminiService.build_prompt(GeminiGenerationRequest("Matemática", "Frações", "MEDIO", 1, "DISCURSIVA", learning_gaps=learning_gaps))
    assert "Matemática - Frações" in prompt
    assert "Português - Leitura" in prompt


def test_generate_activity_uses_deterministic_fallback_without_key(ai_pdf_real_context):
    client, db, classroom_id, _ = ai_pdf_real_context
    response = client.post("/api/activities/generate", json={
        "classroomId": classroom_id,
        "subject": "Matemática",
        "topic": "Equações",
        "difficultyLevel": "MEDIO",
        "questionsCount": 3,
        "format": "MULTIPLA_ESCOLHA",
        "disabilityAdaptations": ["TDAH"],
        "additionalInstructions": "Use situações cotidianas",
    })
    assert response.status_code == 201, response.text
    payload = response.json()
    activity_id = payload["id"]
    try:
        assert payload["generatedByAi"] is True
        assert payload["aiProvider"] == "Demo Educacional"
        assert payload["questionsCount"] == 3
        assert len(payload["questions"]) == 3
        assert payload["questions"][0]["questionType"] == "MULTIPLA_ESCOLHA"
        assert db.activities.find_one({"_id": ObjectId(activity_id)}) is not None
    finally:
        db.activities.delete_one({"_id": ObjectId(activity_id)})


def test_pdf_with_and_without_answers_returns_blob_compatible_binary(ai_pdf_real_context):
    client, db, classroom_id, _ = ai_pdf_real_context
    created = client.post("/api/activities", json=manual_activity_payload(classroom_id))
    assert created.status_code == 201, created.text
    activity_id = created.json()["id"]
    try:
        without_answers = client.get(f"/api/activities/{activity_id}/export-pdf?includeAnswers=false")
        with_answers = client.get(f"/api/activities/{activity_id}/export-pdf?includeAnswers=true")
        assert without_answers.status_code == 200
        assert with_answers.status_code == 200
        assert without_answers.headers["content-type"].startswith("application/pdf")
        assert with_answers.headers["content-type"].startswith("application/pdf")
        assert without_answers.headers["content-disposition"].startswith("attachment;")
        assert without_answers.content.startswith(b"%PDF")
        assert with_answers.content.startswith(b"%PDF")
        without_text = "\n".join(page.extract_text() or "" for page in PdfReader(__import__("io").BytesIO(without_answers.content)).pages)
        with_text = "\n".join(page.extract_text() or "" for page in PdfReader(__import__("io").BytesIO(with_answers.content)).pages)
        assert "[CORRETA]" not in without_text
        assert "[CORRETA]" in with_text
    finally:
        db.activities.delete_one({"_id": ObjectId(activity_id)})
