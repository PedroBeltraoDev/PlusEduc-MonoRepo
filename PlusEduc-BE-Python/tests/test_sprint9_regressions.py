"""Regressões dos bugs encontrados nos testes da Sprint 09 (repositórios em memória, sem MongoDB, exceto o último)."""

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.auth import UserPrincipal
from app.core.passwords import verify_password
from app.schemas.activity import ActivityCreateRequest
from app.schemas.auth import StudentRegistrationRequest, TeacherRegistrationRequest
from app.schemas.classroom import ClassroomCreateRequest
from app.schemas.student import StudentCreateRequest, StudentUpdateRequest
from app.schemas.student_portal_schema import Classmate
from app.schemas.teacher import TeacherCreateRequest, TeacherUpdateRequest
from app.services.activity_service import ActivityService
from app.services.classroom_service import ClassroomService
from app.services.student_service import StudentService
from app.services.teacher_service import TeacherService
from tests.test_students_teachers import FakeStudentRepository, FakeTeacherRepository, FakeUserRepository

ADMIN = UserPrincipal(user_id="u-admin", email="admin@example.com", role="ADMIN")
BAD_EMAILS = ["abc", "@@@", "sem-arroba", "a@b", "a b@c.com", "@dominio.com", "usuario@"]


# --- e-mail em formato válido ----------------------------------------------------------------
@pytest.mark.parametrize("email", BAD_EMAILS)
def test_every_signup_and_create_schema_rejects_invalid_email(email):
    with pytest.raises(ValidationError):
        StudentRegistrationRequest(name="Aluno Teste", email=email, password="senha-123")
    with pytest.raises(ValidationError):
        TeacherRegistrationRequest(name="Professor Teste", email=email, password="senha-123")
    with pytest.raises(ValidationError):
        StudentCreateRequest(name="Aluno Teste", email=email)
    with pytest.raises(ValidationError):
        StudentUpdateRequest(email=email)
    with pytest.raises(ValidationError):
        TeacherCreateRequest(name="Professor Teste", email=email, password="senha-123")
    with pytest.raises(ValidationError):
        TeacherUpdateRequest(email=email)


@pytest.mark.parametrize("email", ["lucas.carvalho@aluno.local", "ana@escola.com.br", "x@y.z"])
def test_valid_emails_are_kept(email):
    assert StudentRegistrationRequest(name="Aluno Teste", email=email, password="senha-123").email == email
    assert StudentUpdateRequest().email is None  # campo opcional na edição


# --- professores: senha com hash, login criado e desativado na exclusão ---------------------
def test_teacher_requires_a_password_of_at_least_six_characters():
    with pytest.raises(ValidationError):
        TeacherCreateRequest(name="Professor Teste", email="p@escola.com")
    with pytest.raises(ValidationError):
        TeacherCreateRequest(name="Professor Teste", email="p@escola.com", password="123")


def test_teacher_created_by_the_api_has_a_bcrypt_password_and_a_login():
    repo, users = FakeTeacherRepository(), FakeUserRepository()
    service = TeacherService(repo, users)
    created = service.create(TeacherCreateRequest(name="Professor Novo", email="novo@escola.com", password="senha-secreta"))
    stored = repo.find_by_id(created.id)
    assert stored["password"] != "senha-secreta" and verify_password("senha-secreta", stored["password"])
    login = users.find_active_by_email("novo@escola.com")
    assert login["role"] == "TEACHER" and verify_password("senha-secreta", login["password"])


def test_teacher_password_change_is_hashed_in_both_places_and_delete_disables_the_login():
    repo, users = FakeTeacherRepository(), FakeUserRepository()
    service = TeacherService(repo, users)
    created = service.create(TeacherCreateRequest(name="Professor Novo", email="novo@escola.com", password="senha-secreta"))
    service.update(created.id, TeacherUpdateRequest(password="outra-senha-9"))
    assert verify_password("outra-senha-9", repo.find_by_id(created.id)["password"])
    assert verify_password("outra-senha-9", users.users["novo@escola.com"]["password"])
    service.delete(created.id)
    assert users.find_active_by_email("novo@escola.com") is None


def test_teacher_cannot_reuse_an_email_that_already_has_a_login():
    users = FakeUserRepository()  # já tem teacher@example.com como usuário (sem registro de professor)
    with pytest.raises(HTTPException) as error:
        TeacherService(FakeTeacherRepository(), users).create(
            TeacherCreateRequest(name="Professor Novo", email="teacher@example.com", password="senha-secreta"))
    assert error.value.status_code == 409


# --- alunos: excluir desativa o login e libera a turma -------------------------------------
class ClassroomsWithMembers:
    def __init__(self):
        self.removed = []

    def exists_by_id(self, classroom_id):
        return True

    def remove_student(self, classroom_id, student_id):
        self.removed.append((classroom_id, student_id))


def test_deleting_a_student_disables_the_login_and_leaves_the_classroom_list():
    students, users, classrooms = FakeStudentRepository(), FakeUserRepository(), ClassroomsWithMembers()
    users.users["aluno@example.com"] = {"_id": "u-aluno", "email": "aluno@example.com", "role": "STUDENT", "password": "x", "active": True}
    StudentService(students, classrooms, users).delete("student-1")
    assert users.find_active_by_email("aluno@example.com") is None
    assert classrooms.removed == [("class-1", "student-1")]
    assert students.find_by_id("student-1")["active"] is False


# --- turma: professor responsável precisa existir -------------------------------------------
class ClassroomsRepo:
    def exists_by_name_and_year(self, name, year, exclude_id=None):
        return False

    def count_active_by_teacher(self, teacher_id, exclude_id=None):
        return 0

    def insert(self, document):
        document["_id"] = "class-new"
        return document


def test_classroom_with_unknown_teacher_is_rejected():
    service = ClassroomService(ClassroomsRepo(), FakeStudentRepository(), FakeTeacherRepository())
    body = ClassroomCreateRequest(name="Turma Nova", year=2026, gradeLevel="7º Ano do Ensino Fundamental", teacherId="nao-existe")
    with pytest.raises(HTTPException) as error:
        service.create(body)
    assert error.value.status_code == 400 and "Professor" in error.value.detail


# --- atividade: o aluno precisa ser da turma (RN10) -----------------------------------------
class ClassroomsForActivities:
    items = {"class-1": {"_id": "class-1", "students": ["student-1"]}, "c2": {"_id": "c2", "students": []}}

    def find_by_id(self, classroom_id):
        return self.items.get(classroom_id)


class ActivitiesRepo:
    def insert(self, document):
        document["_id"] = "act-1"
        return document


def activity_service():
    return ActivityService(ActivitiesRepo(), FakeStudentRepository(), ClassroomsForActivities(), mongo=None, activity_submission_repository=object())


def activity_body(classroom, student):
    return ActivityCreateRequest(title="Atividade de teste", subject="Matemática", topic="Frações", difficultyLevel="FACIL", questionsCount=1,
                                 format="MULTIPLA_ESCOLHA", classroomId=classroom, studentId=student)


def test_activity_for_a_student_of_another_classroom_is_rejected():
    with pytest.raises(HTTPException) as error:
        activity_service().create(activity_body("c2", "student-1"), ADMIN)
    assert error.value.status_code == 400


def test_activity_for_a_student_of_the_selected_classroom_is_accepted():
    service = activity_service()
    classroom = service.require_classroom("class-1")
    assert service.resolve_student_for_classroom("student-1", classroom)["_id"] == "student-1"


# --- privacidade: colegas de turma sem e-mail ----------------------------------------------
def test_classmate_payload_has_no_email():
    assert "email" not in Classmate.model_fields
