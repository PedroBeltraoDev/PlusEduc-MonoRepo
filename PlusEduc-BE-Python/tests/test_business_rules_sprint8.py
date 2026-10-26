"""Regras de negócio revisadas na Sprint 08 (repositórios em memória, sem MongoDB)."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.auth import UserPrincipal
from app.schemas.grade import GradeCreateRequest, GradeUpdateRequest
from app.schemas.student import StudentCreateRequest, StudentUpdateRequest
from app.services.classroom_service import ClassroomService
from app.services.grade_service import GradeService

TEACHER = UserPrincipal(user_id="u1", email="prof@example.com", role="TEACHER")


class FakeStudents:
    def __init__(self):
        self.items = {
            "s1": {"_id": "s1", "name": "Aluno Um", "class_id": "c1", "active": True},
            "s2": {"_id": "s2", "name": "Aluno Dois", "class_id": "c2", "active": True},
            "s3": {"_id": "s3", "name": "Aluno Sem Turma", "active": True},
            "s4": {"_id": "s4", "name": "Aluno Só Na Lista", "active": True},
        }

    def find_by_id(self, student_id):
        return self.items.get(student_id)

    def update(self, student_id, updates):
        self.items[student_id].update(updates)
        return self.items[student_id]


class FakeClassrooms:
    def __init__(self):
        self.items = {
            "c1": {"_id": "c1", "name": "Turma 1", "students": ["s1"]},
            "c2": {"_id": "c2", "name": "Turma 2", "students": ["s2"]},
            "c3": {"_id": "c3", "name": "Turma 3", "students": ["s4"]},
        }

    def find_by_id(self, classroom_id):
        return self.items.get(classroom_id)

    def update(self, classroom_id, updates):
        self.items[classroom_id].update(updates)
        return self.items[classroom_id]


class FakeGrades:
    def __init__(self):
        self.items = {}

    def insert(self, document):
        document["_id"] = f"g{len(self.items) + 1}"
        self.items[document["_id"]] = document
        return document

    def find_by_id(self, grade_id):
        return self.items.get(grade_id)

    def update(self, grade_id, updates):
        self.items[grade_id].update(updates)
        return self.items[grade_id]


@pytest.fixture
def grades_service():
    return GradeService(FakeGrades(), FakeStudents(), FakeClassrooms())


def grade_request(student_id="s1", classroom_id="c1", when=None, **extra):
    return GradeCreateRequest(studentId=student_id, classroomId=classroom_id, grade=7.5, subject="Matemática",
                              date=when or datetime.now(timezone.utc), **extra)


# --- nota só para aluno matriculado na turma -------------------------------------------------
def test_grade_for_enrolled_student_is_accepted(grades_service):
    assert grades_service.create(grade_request("s1", "c1"), TEACHER).grade == 7.5


def test_grade_is_accepted_when_enrollment_is_only_in_the_classroom_list(grades_service):
    assert grades_service.create(grade_request("s4", "c3"), TEACHER).studentId == "s4"


@pytest.mark.parametrize("student_id,classroom_id", [("s2", "c1"), ("s3", "c1"), ("s1", "c3")])
def test_grade_for_student_outside_the_classroom_is_rejected(grades_service, student_id, classroom_id):
    with pytest.raises(HTTPException) as error:
        grades_service.create(grade_request(student_id, classroom_id), TEACHER)
    assert error.value.status_code == 400
    assert "não está matriculado" in error.value.detail
    assert grades_service.repository.items == {}


def test_editing_an_old_grade_of_a_transferred_student_is_still_allowed(grades_service):
    created = grades_service.create(grade_request("s1", "c1"), TEACHER)
    grades_service.student_repository.items["s1"]["class_id"] = "c2"  # aluno transferido depois do lançamento
    grades_service.classroom_repository.items["c1"]["students"] = []
    updated = grades_service.update(created.id, GradeUpdateRequest(grade=9.0), TEACHER)
    assert updated.grade == 9.0


def test_moving_a_grade_to_a_classroom_without_the_student_is_rejected(grades_service):
    created = grades_service.create(grade_request("s1", "c1"), TEACHER)
    with pytest.raises(HTTPException) as error:
        grades_service.update(created.id, GradeUpdateRequest(classroomId="c2"), TEACHER)
    assert error.value.status_code == 400


# --- data do lançamento ----------------------------------------------------------------------
def test_grade_dated_in_the_future_is_rejected(grades_service):
    with pytest.raises(HTTPException) as error:
        grades_service.create(grade_request(when=datetime.now(timezone.utc) + timedelta(days=30)), TEACHER)
    assert error.value.status_code == 422
    assert "futuro" in error.value.detail


def test_grade_dated_today_or_in_the_past_is_accepted(grades_service):
    grades_service.create(grade_request(when=datetime.now(timezone.utc) + timedelta(hours=3)), TEACHER)  # tolerância de fuso
    grades_service.create(grade_request(when=datetime(2026, 8, 21, tzinfo=timezone.utc)), TEACHER)
    assert len(grades_service.repository.items) == 2


def test_editing_a_grade_date_to_the_future_is_rejected(grades_service):
    created = grades_service.create(grade_request(), TEACHER)
    with pytest.raises(HTTPException) as error:
        grades_service.update(created.id, GradeUpdateRequest(date=datetime.now(timezone.utc) + timedelta(days=10)), TEACHER)
    assert error.value.status_code == 422


# --- um aluno, uma turma ---------------------------------------------------------------------
@pytest.fixture
def classroom_service():
    return ClassroomService(FakeClassrooms(), FakeStudents(), teacher_repository=None)


def test_enrolling_in_another_classroom_removes_the_student_from_the_previous_one(classroom_service):
    classroom_service.enroll("c2", "s1")
    classrooms = classroom_service.repository.items
    assert "s1" not in classrooms["c1"]["students"]
    assert "s1" in classrooms["c2"]["students"]
    assert classroom_service.student_repository.items["s1"]["class_id"] == "c2"
    assert classrooms["c2"]["students"].count("s1") == 1


def test_enrolling_again_in_the_same_classroom_does_not_duplicate(classroom_service):
    classroom_service.enroll("c1", "s1")
    assert classroom_service.repository.items["c1"]["students"] == ["s1"]


def test_enrolling_a_student_without_classroom_keeps_other_classrooms_untouched(classroom_service):
    classroom_service.enroll("c1", "s3")
    assert classroom_service.repository.items["c2"]["students"] == ["s2"]
    assert set(classroom_service.repository.items["c1"]["students"]) == {"s1", "s3"}


# --- data de nascimento ----------------------------------------------------------------------
@pytest.mark.parametrize("value", ["2031-03-04", "1850-01-01", "2999-12-31T00:00:00Z"])
def test_birth_date_in_the_future_or_before_1900_is_rejected(value):
    with pytest.raises(ValidationError):
        StudentCreateRequest(name="Aluno Teste", email="a@b.com", birthDate=value)
    with pytest.raises(ValidationError):
        StudentUpdateRequest(birthDate=value)


@pytest.mark.parametrize("value", [None, "", "2011-02-03", "2010-01-01T00:00:00Z", "03/02/2011"])
def test_valid_or_legacy_birth_dates_are_kept(value):
    assert StudentCreateRequest(name="Aluno Teste", email="a@b.com", birthDate=value).birthDate == value
