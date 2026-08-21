from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.main import app
from app.services.curriculum import curriculum_subjects_for_grade, normalize_curriculum_key

TEACHER_EMAIL = "demo.matematica@professor.local"
PASSWORD = "Demo@123"


def test_subject_assignment_is_unique_and_available_subjects_shrink():
    classroom_id = ObjectId()
    grade_level = "6º Ano do Ensino Fundamental"
    curriculum = curriculum_subjects_for_grade(grade_level)

    try:
        with TestClient(app) as client:
            classrooms = app.state.classroom_repository.collection
            teachers = app.state.teacher_repository.collection
            teacher = teachers.find_one({"email": TEACHER_EMAIL, "active": True})
            assert teacher is not None
            classrooms.insert_one(
                {
                    "_id": classroom_id,
                    "name": "Turma temporária - teste curricular",
                    "year": 2026,
                    "grade_level": grade_level,
                    "teacher_id": str(teacher["_id"]),
                    "students": [],
                    "subjectTeachers": [],
                    "subjects": curriculum,
                    "active": True,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            login = client.post("/api/auth/login", json={"email": TEACHER_EMAIL, "password": PASSWORD})
            assert login.status_code == 200, login.text
            headers = {"Authorization": f"Bearer {login.json()['accessToken']}"}

            available = client.get(f"/api/subjects/available?classroomId={classroom_id}", headers=headers)
            assert available.status_code == 200, available.text
            items = available.json()
            assert len(items) == len(curriculum)
            selected = items[0]

            created = client.post(
                "/api/subjects/assignments",
                headers=headers,
                json={"classroomId": str(classroom_id), "subjectId": selected["id"]},
            )
            assert created.status_code == 201, created.text

            after = client.get(f"/api/subjects/available?classroomId={classroom_id}", headers=headers)
            assert after.status_code == 200, after.text
            assert normalize_curriculum_key(selected["name"]) not in {
                normalize_curriculum_key(item["name"]) for item in after.json()
            }

            duplicate = client.post(
                "/api/subjects/assignments",
                headers=headers,
                json={"classroomId": str(classroom_id), "subjectId": selected["id"]},
            )
            assert duplicate.status_code == 409, duplicate.text
    finally:
        cleanup_client = MongoClient("mongodb://localhost:27017")
        cleanup_db = cleanup_client["escola_db"]
        cleanup_db["classrooms"].delete_one({"_id": classroom_id})
        teacher = cleanup_db["teachers"].find_one({"email": TEACHER_EMAIL, "active": True})
        if teacher is not None:
            cleanup_db["teachers"].update_one(
                {"_id": teacher["_id"]},
                {"$pull": {"classrooms": str(classroom_id), "classroomIds": str(classroom_id)}},
            )
        cleanup_client.close()
