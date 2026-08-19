import bcrypt
import pytest
from fastapi.testclient import TestClient

from app.core.jwt import create_access_token
from app.main import create_app


class FakeClassroomRepository:
    def __init__(self):
        self.items = [
            {
                "_id": "class-1",
                "name": "Turma A",
                "year": 2026,
                "grade_level": "5º Ano",
                "teacher_id": "teacher-1",
                "students": ["student-1"],
                "subjects": ["Matemática"],
                "active": True,
            },
            {
                "_id": "class-empty",
                "name": "Turma Vazia",
                "year": 2026,
                "grade_level": "6º Ano",
                "teacher_id": "teacher-1",
                "students": [],
                "subjects": [],
                "active": True,
            },
        ]

    def find_by_id(self, classroom_id):
        return next((item for item in self.items if str(item.get("_id")) == classroom_id), None)

    def find_active(self):
        return [item for item in self.items if item.get("active") is True]

    def find_active_by_teacher(self, teacher_id):
        return [item for item in self.find_active() if item.get("teacher_id") == teacher_id]

    def find_active_by_student(self, student_id):
        return [item for item in self.find_active() if student_id in item.get("students", [])]

    def find_active_by_year(self, year):
        return [item for item in self.find_active() if item.get("year") == year]

    def exists_by_name_and_year(self, name, year, exclude_id=None):
        return any(
            item.get("name") == name and item.get("year") == year and str(item.get("_id")) != exclude_id
            for item in self.items
        )

    def count_active_by_teacher(self, teacher_id, exclude_id=None):
        return sum(
            item.get("teacher_id") == teacher_id
            and item.get("active") is True
            and str(item.get("_id")) != exclude_id
            for item in self.items
        )

    def insert(self, document):
        document["_id"] = "class-created"
        self.items.append(document)
        return document

    def update(self, classroom_id, updates):
        item = self.find_by_id(classroom_id)
        if item:
            item.update(updates)
        return item

    def soft_delete(self, classroom_id, updated_at):
        item = self.find_by_id(classroom_id)
        if not item:
            return False
        item["active"] = False
        return True


class FakeStudentRepository:
    def __init__(self):
        self.items = [
            {"_id": "student-1", "name": "Aluno 1", "email": "a@example.com", "class_id": "class-1", "learning_gaps": [], "active": True},
            {"_id": "student-2", "name": "Aluno 2", "email": "b@example.com", "class_id": None, "learning_gaps": [], "active": True},
        ]

    def find_by_id(self, student_id):
        return next((item for item in self.items if str(item.get("_id")) == student_id), None)

    def update(self, student_id, updates):
        item = self.find_by_id(student_id)
        if item:
            item.update(updates)
        return item

    def find_by_email(self, email):
        return next((item for item in self.items if item.get("email") == email), None)

    def find_active(self):
        return [item for item in self.items if item.get("active") is True]

    def find_active_by_class(self, class_id):
        return [item for item in self.find_active() if item.get("class_id") == class_id]

    def find_active_by_learning_gap_subject(self, subject):
        return []

    def insert(self, document):
        document["_id"] = "student-created"
        self.items.append(document)
        return document

    def soft_delete(self, student_id, updated_at):
        return True


class FakeTeacherRepository:
    def __init__(self):
        self.items = [{"_id": "teacher-1", "name": "Professor", "email": "p@example.com", "subjects": ["Matemática"], "classrooms": [], "active": True}]

    def find_by_id(self, teacher_id):
        return next((item for item in self.items if str(item.get("_id")) == teacher_id), None)

    def find_by_email(self, email):
        return next((item for item in self.items if item.get("email") == email), None)

    def find_active(self):
        return [item for item in self.items if item.get("active") is True]

    def find_active_by_email(self, email):
        return self.find_by_email(email)

    def find_active_by_subject(self, subject):
        return []

    def count_all(self):
        return len(self.items)

    def insert(self, document):
        document["_id"] = "teacher-created"
        return document

    def update(self, teacher_id, updates):
        return self.find_by_id(teacher_id)

    def soft_delete(self, teacher_id, updated_at):
        return True


class FakeGradeRepository:
    def __init__(self):
        self.items = [
            {"_id": "grade-1", "classroomId": "class-1", "studentId": "student-1", "subject": "Matemática", "grade": 8},
            {"_id": "grade-2", "classroomId": "class-1", "studentId": "student-1", "subject": "Matemática", "gradeValue": 6},
            {"_id": "grade-3", "classroomId": "class-1", "studentId": "student-1", "subject": "Português", "grade": 10},
        ]

    def find_by_classroom(self, classroom_id):
        return [item for item in self.items if item.get("classroomId") == classroom_id]


class FakeUserRepository:
    def find_active_by_email(self, email):
        return {"_id": "user-1", "email": email, "role": "TEACHER", "active": True}


class FakeClassroomContext:
    def __init__(self, settings):
        self.classrooms = FakeClassroomRepository()
        self.students = FakeStudentRepository()
        self.teachers = FakeTeacherRepository()
        self.users = FakeUserRepository()
        self.grades = FakeGradeRepository()
        self.client = TestClient(
            create_app(
                settings,
                user_repository=self.users,
                student_repository=self.students,
                teacher_repository=self.teachers,
                classroom_repository=self.classrooms,
                grade_repository=self.grades,
            )
        )
        self.client.__enter__()
        self.headers = {"Authorization": f"Bearer {create_access_token('teacher@example.com', settings)}"}

    def close(self):
        self.client.__exit__(None, None, None)


@pytest.fixture
def classroom_context(settings):
    context = FakeClassroomContext(settings)
    yield context
    context.close()


def test_classroom_crud_and_response_contract(classroom_context):
    response = classroom_context.client.post(
        "/api/classrooms",
        headers=classroom_context.headers,
        json={"name": "Nova Turma", "year": 2026, "gradeLevel": "7º Ano", "teacherId": "teacher-1", "subjects": ["História"]},
    )
    assert response.status_code == 201
    assert response.json()["id"] == "class-created"
    assert response.json()["studentIds"] == []
    assert response.json()["teacherName"] == "Professor"

    listed = classroom_context.client.get("/api/classrooms", headers=classroom_context.headers)
    assert listed.status_code == 200
    assert {item["id"] for item in listed.json()} == {"class-1", "class-empty", "class-created"}

    updated = classroom_context.client.put(
        "/api/classrooms/class-empty",
        headers=classroom_context.headers,
        json={"gradeLevel": "6º Ano Integral"},
    )
    assert updated.status_code == 200
    assert updated.json()["gradeLevel"] == "6º Ano Integral"


def test_classroom_duplicate_and_invalid_students_are_rejected(classroom_context):
    duplicate = classroom_context.client.post(
        "/api/classrooms",
        headers=classroom_context.headers,
        json={"name": "Turma A", "year": 2026, "gradeLevel": "5º Ano", "teacherId": "teacher-1", "subjects": []},
    )
    assert duplicate.status_code == 409

    missing_student = classroom_context.client.post(
        "/api/classrooms",
        headers=classroom_context.headers,
        json={"name": "Turma Nova", "year": 2026, "gradeLevel": "5º Ano", "teacherId": "teacher-1", "studentIds": ["missing"], "subjects": []},
    )
    assert missing_student.status_code == 400


def test_enroll_and_unenroll_keep_student_class_reference_consistent(classroom_context):
    enrolled = classroom_context.client.post(
        "/api/classrooms/class-empty/enroll/student-2",
        headers=classroom_context.headers,
    )
    assert enrolled.status_code == 204
    assert "student-2" in classroom_context.classrooms.find_by_id("class-empty")["students"]

    assert classroom_context.students.find_by_id("student-2")["class_id"] == "class-empty"

    unenrolled = classroom_context.client.delete(
        "/api/classrooms/class-empty/unenroll/student-2",
        headers=classroom_context.headers,
    )
    assert unenrolled.status_code == 204
    assert "student-2" not in classroom_context.classrooms.find_by_id("class-empty")["students"]

    assert classroom_context.students.find_by_id("student-2")["class_id"] is None


def test_delete_with_students_is_blocked_and_empty_classroom_is_soft_deleted(classroom_context):
    blocked = classroom_context.client.delete("/api/classrooms/class-1", headers=classroom_context.headers)
    assert blocked.status_code == 400

    deleted = classroom_context.client.delete("/api/classrooms/class-empty", headers=classroom_context.headers)
    assert deleted.status_code == 204
    assert classroom_context.classrooms.find_by_id("class-empty")["active"] is False


def test_searches_by_teacher_and_student(classroom_context):
    by_teacher = classroom_context.client.get("/api/classrooms/teacher/teacher-1", headers=classroom_context.headers)
    assert by_teacher.status_code == 200
    assert by_teacher.json()

    by_student = classroom_context.client.get("/api/classrooms/student/student-1", headers=classroom_context.headers)
    assert by_student.status_code == 200
    assert [item["id"] for item in by_student.json()] == ["class-1"]


def test_classroom_endpoints_require_authentication(classroom_context):
    response = classroom_context.client.get("/api/classrooms")
    assert response.status_code == 401


def test_classroom_performance_aggregates_real_grades(classroom_context):
    response = classroom_context.client.get(
        "/api/classrooms/class-1/performance",
        headers=classroom_context.headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["classroomId"] == "class-1"
    assert payload["averageGrade"] == 8.0
    assert payload["studentsCount"] == 1
    assert {item["subject"]: item["average"] for item in payload["subjectPerformance"]} == {
        "Matemática": 7.0,
        "Português": 10.0,
    }
    assert all(item["studentsCount"] == 1 for item in payload["subjectPerformance"])


def test_classroom_performance_without_grades_returns_empty_breakdown(classroom_context):
    response = classroom_context.client.get(
        "/api/classrooms/class-empty/performance",
        headers=classroom_context.headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "classroomId": "class-empty",
        "averageGrade": 0.0,
        "studentsCount": 0,
        "subjectPerformance": [],
    }
