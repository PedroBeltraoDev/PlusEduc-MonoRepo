"""Professor descartável para os testes no MongoDB real.

Cria (e depois remove) um professor aprovado com conta de acesso, em vez de depender de contas
que só existem no banco de quem escreveu o teste.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

from app.core.passwords import hash_password

PASSWORD = "Teste@12345"


@contextmanager
def temporary_teacher(db, *, name: str = "Professor Temporário de Teste", with_classroom: bool = False, grade_level: str = "6º Ano do Ensino Fundamental"):
    token = uuid4().hex[:10]
    email = f"prof.teste.{token}@professor.local"
    now = datetime.now(timezone.utc)
    user_id = db.users.insert_one({
        "email": email, "password": hash_password(PASSWORD), "role": "TEACHER", "active": True,
        "tokenVersion": 0, "name": name, "createdAt": now,
    }).inserted_id
    teacher_id = db.teachers.insert_one({
        "name": name, "email": email, "subjects": [], "classrooms": [], "active": True,
        "approval_status": "APPROVED", "created_at": now, "updated_at": now,
    }).inserted_id
    classroom_id = None
    if with_classroom:
        classroom_id = db.classrooms.insert_one({
            "name": f"Turma temporária {token}", "year": now.year, "grade_level": grade_level,
            "teacher_id": str(teacher_id), "students": [], "subjectTeachers": [], "subjects": [],
            "active": True, "created_at": now, "updated_at": now,
        }).inserted_id
    try:
        yield {"email": email, "password": PASSWORD, "teacher_id": str(teacher_id), "user_id": str(user_id),
               "classroom_id": str(classroom_id) if classroom_id else None}
    finally:
        db.users.delete_one({"_id": user_id})
        db.teachers.delete_one({"_id": teacher_id})
        db.refresh_tokens.delete_many({"email": email})
        if classroom_id is not None:
            db.classrooms.delete_one({"_id": classroom_id})
