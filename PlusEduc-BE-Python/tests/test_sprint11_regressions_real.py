"""Regressões encontradas na revisão de código da Sprint 11 (MongoDB real, banco de TEST_DATABASE).

Aluno cadastrado pela escola (tela de Turmas) não tinha como entrar no portal: a rota de liberação de acesso existia,
mas nenhuma tela a usava, e o autocadastro com o mesmo e-mail criava um segundo registro de aluno, fora da turma.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.core.config import get_settings
from app.core.passwords import hash_password
from app.main import create_app
from tests.database import TEST_DATABASE


def test_student_created_by_school_gets_portal_access_only_through_staff():
    token = uuid4().hex[:10]
    admin_email = f"admin.s11.{token}@pluseduc.local"
    student_email = f"aluno.s11.{token}@aluno.local"
    password = "Senha@123"
    mongo = MongoClient("mongodb://localhost:27017")
    db = mongo[TEST_DATABASE]
    app = create_app(get_settings().model_copy(update={"mongodb_database": TEST_DATABASE}))
    try:
        db.users.insert_one({"email": admin_email, "password": hash_password(password), "role": "ADMIN", "active": True})
        with TestClient(app) as client:
            admin = {"Authorization": f"Bearer {client.post('/api/auth/login', json={'email': admin_email, 'password': password}).json()['accessToken']}"}

            created = client.post("/api/students", headers=admin, json={"name": "Aluno Sem Portal", "email": student_email, "birthDate": "2012-05-06"})
            assert created.status_code == 201, created.text
            student_id = created.json()["id"]
            assert created.json()["hasPortalAccess"] is False

            # o autocadastro com o mesmo e-mail é recusado (antes criava um segundo aluno, sem turma)
            signup = client.post("/api/auth/register/student", json={"name": "Aluno Sem Portal", "email": student_email, "password": password})
            assert signup.status_code == 409, signup.text
            assert "liberar seu acesso" in signup.json()["message"]
            assert db.students.count_documents({"email": student_email}) == 1

            # a equipe libera o acesso; o aluno entra no portal com o próprio cadastro
            enabled = client.post(f"/api/students/{student_id}/enable-access", headers=admin, json={"password": password})
            assert enabled.status_code == 204, enabled.text
            login = client.post("/api/auth/login", json={"email": student_email, "password": password})
            assert login.status_code == 200 and login.json()["studentId"] == student_id
            assert client.get(f"/api/students/{student_id}", headers=admin).json()["hasPortalAccess"] is True
            again = client.post(f"/api/students/{student_id}/enable-access", headers=admin, json={"password": password})
            assert again.status_code == 400  # "Aluno já possui acesso ao portal"
    finally:
        db.users.delete_many({"email": {"$in": [admin_email, student_email]}})
        db.students.delete_many({"email": student_email})
        db.refresh_tokens.delete_many({"email": {"$in": [admin_email, student_email]}})
        mongo.close()


# --- PDF com adaptação para baixa visão (revisão da Sprint 11) ----------------------------------------------------
class _NoRepository:
    def find_by_id(self, _id):
        return None


def _font_sizes(pdf_bytes: bytes) -> set[float]:
    import io
    import re

    from pypdf import PdfReader

    content = b"".join(page.get_contents().get_data() for page in PdfReader(io.BytesIO(pdf_bytes)).pages)
    return {float(size) for size in re.findall(rb"/[\w+]+ ([\d.]+) Tf", content)}


def test_low_vision_pdf_really_uses_a_larger_font():
    """O PDF dizia "fonte ampliada para baixa visão", mas usava o tamanho normal."""
    from app.services.activity_pdf_service import LOW_VISION_SCALE, ActivityPdfService

    activity = {
        "title": "Frações — revisão",
        "subject": "Matemática",
        "topic": "Frações",
        "content": {"questions": [{"questionText": "Quanto é 1/2 + 1/4?", "questionType": "MULTIPLA_ESCOLHA",
                                    "options": ["2/6", "3/4"], "correctAnswer": "B"}]},
    }
    service = ActivityPdfService(_NoRepository(), _NoRepository())
    normal = _font_sizes(service.generate(activity, include_answers=False))
    ampliado = _font_sizes(service.generate({**activity, "disability_adaptations": ["Baixa visão"]}, include_answers=False))
    corpo, titulo = 9.5, 15.0  # tamanhos do texto e do título no PDF normal
    assert {corpo, titulo} <= normal
    assert round(corpo * LOW_VISION_SCALE, 1) in ampliado and round(titulo * LOW_VISION_SCALE, 1) in ampliado
    assert corpo not in ampliado
