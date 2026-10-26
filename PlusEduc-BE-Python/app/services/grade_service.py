from datetime import datetime, timedelta, timezone
from functools import partial
from typing import Any

from fastapi import HTTPException

from app.compute import GroupStats, stats_by
from app.core.auth import UserPrincipal
from app.core.parallel import run_parallel
from app.repositories.activity_repository import ActivityRepository
from app.repositories.activity_submission_repository import ActivitySubmissionRepository
from app.repositories.classroom_repository import ClassroomRepository
from app.repositories.grade_repository import GradeRepository
from app.repositories.student_repository import StudentRepository
from app.schemas.grade import (
    ActivityGradesLaunchResponse,
    GradeClassroomSummaryResponse,
    GradeCreateRequest,
    GradeResponse,
    GradeStudentSummary,
    GradeUpdateRequest,
)
from app.services.activity_submission_service import ActivitySubmissionService


def _subject_key(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _as_naive_utc(value: Any) -> datetime | None:
    # Datas antigas (seed) ficam como texto ISO; as novas, como datetime. Normaliza as duas.
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value


class GradeService:
    def __init__(
        self,
        repository: GradeRepository,
        student_repository: StudentRepository,
        classroom_repository: ClassroomRepository,
        activity_repository: ActivityRepository | None = None,
        submission_repository: ActivitySubmissionRepository | None = None,
    ) -> None:
        self.repository = repository
        self.student_repository = student_repository
        self.classroom_repository = classroom_repository
        self.activity_repository = activity_repository
        self.submission_repository = submission_repository

    def create(self, request: GradeCreateRequest, current_user: UserPrincipal) -> GradeResponse:
        self.validate_references(request.studentId, request.classroomId, require_enrollment=True)
        self.validate_date(request.date)
        document = {
            "studentId": request.studentId,
            "classroomId": request.classroomId,
            "grade": request.grade,
            "attendance": request.attendance,
            "subject": request.subject,
            "activityType": request.activityType,
            "observations": request.observations,
            "activityId": request.activityId,
            "date": request.date,
            "createdAt": datetime.now(timezone.utc),
        }
        document = {key: value for key, value in document.items() if value is not None}
        return self.to_response(self.repository.insert(document))

    def list_all(self) -> list[GradeResponse]:
        return [self.to_response(item) for item in self.repository.find_all()]

    def get(self, grade_id: str) -> GradeResponse:
        item = self.repository.find_by_id(grade_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Nota não encontrada: {grade_id}")
        return self.to_response(item)

    def update(self, grade_id: str, request: GradeUpdateRequest, current_user: UserPrincipal) -> GradeResponse:
        current = self.repository.find_by_id(grade_id)
        if not current:
            raise HTTPException(status_code=404, detail=f"Nota não encontrada: {grade_id}")
        values = request.model_dump(exclude_unset=True)
        student_id = values.get("studentId", current.get("studentId"))
        classroom_id = values.get("classroomId", current.get("classroomId"))
        # A matrícula só é exigida quando o lançamento muda de aluno ou de turma: ajustar uma nota
        # antiga de quem já foi transferido de turma continua permitido.
        moved = "studentId" in values or "classroomId" in values
        self.validate_references(student_id, classroom_id, require_enrollment=moved)
        if values.get("date") is not None:
            self.validate_date(values["date"])
        updates = {key: value for key, value in values.items() if value is not None}
        updated = self.repository.update(grade_id, updates)
        return self.to_response(updated)

    def delete(self, grade_id: str) -> None:
        if not self.repository.delete(grade_id):
            raise HTTPException(status_code=404, detail=f"Nota não encontrada: {grade_id}")

    def by_student(self, student_id: str) -> list[GradeResponse]:
        if not self.student_repository.find_by_id(student_id):
            raise HTTPException(status_code=404, detail=f"Aluno não encontrado: {student_id}")
        return [self.to_response(item) for item in self.repository.find_by_student(student_id)]

    def by_classroom(self, classroom_id: str) -> list[GradeResponse]:
        if not self.classroom_repository.find_by_id(classroom_id):
            raise HTTPException(status_code=404, detail=f"Turma não encontrada: {classroom_id}")
        return [self.to_response(item) for item in self.repository.find_by_classroom(classroom_id)]

    def average_by_student(self, student_id: str) -> float:
        if not self.student_repository.find_by_id(student_id):
            raise HTTPException(status_code=404, detail=f"Aluno não encontrado: {student_id}")
        grades = self.repository.find_by_student(student_id)
        if not grades:
            return 0.0
        values = [float(item.get("grade", item.get("gradeValue", 0))) for item in grades]
        return sum(values) / len(values)

    def classroom_summary(self, classroom_id: str, subject: str | None = None) -> GradeClassroomSummaryResponse:
        classroom = self.classroom_repository.find_by_id(classroom_id)
        if not classroom:
            raise HTTPException(status_code=404, detail=f"Turma não encontrada: {classroom_id}")
        grades, enrolled = run_parallel(
            lambda: self.repository.find_by_classroom(classroom_id),
            lambda: self.student_repository.find_active_by_class(classroom_id),
        )
        if subject:
            grades = [item for item in grades if _subject_key(item.get("subject")) == _subject_key(subject)]

        by_student = stats_by(
            grades,
            lambda item: str(item.get("studentId", item.get("student_id", ""))),
            lambda item: _as_naive_utc(item.get("date")),
        )

        rows: list[GradeStudentSummary] = []
        enrolled_stats: list[GroupStats] = []
        for student in enrolled:
            student_id = str(student.get("_id", student.get("id")))
            item = by_student.get(student_id, GroupStats())
            enrolled_stats.append(item)
            rows.append(GradeStudentSummary(
                studentId=student_id,
                studentName=str(student.get("name", "")),
                average=round(item.average, 2),
                launches=item.count,
                totalClasses=item.recorded,
                attendedClasses=item.attended,
                absences=item.absences,
                attendanceRate=item.attendance_rate,
                lastLaunchAt=item.last,
            ))
        rows.sort(key=lambda row: row.studentName.lower())

        class_stats = GroupStats.combine(enrolled_stats)
        return GradeClassroomSummaryResponse(
            classroomId=classroom_id,
            classroomName=str(classroom.get("name", "")),
            subject=subject or None,
            studentsCount=len(rows),
            totalLaunches=class_stats.count,
            averageGrade=round(class_stats.average, 2),
            attendanceRate=class_stats.attendance_rate,
            students=rows,
        )

    def launch_from_activity(self, activity_id: str, current_user: UserPrincipal) -> ActivityGradesLaunchResponse:
        if self.activity_repository is None or self.submission_repository is None:
            raise HTTPException(status_code=500, detail="Lançamento por atividade indisponível nesta configuração")
        activity = self.activity_repository.find_by_id(activity_id)
        if not activity:
            raise HTTPException(status_code=404, detail=f"Atividade não encontrada: {activity_id}")

        classroom_id = activity.get("classroom_id", activity.get("classroomId"))
        classroom_id = str(classroom_id) if classroom_id else None
        target_student = activity.get("student_id", activity.get("studentId"))
        if classroom_id:
            load_students = partial(self.student_repository.find_active_by_class, classroom_id)
        elif target_student:
            load_students = partial(self.student_repository.find_by_ids, [target_student])
        else:
            raise HTTPException(status_code=400, detail="Atividade sem turma ou aluno associado")

        loaded, submission_items, launched_items = run_parallel(
            load_students,
            lambda: self.submission_repository.find_by_activity(activity_id),
            lambda: self.repository.find_by_activity(activity_id),
        )
        if classroom_id:
            students = {str(item.get("_id")): item for item in loaded}
            recipients = list(students)
        else:
            students = loaded
            recipients = [str(target_student)]
        if target_student:
            recipients = [item for item in recipients if item == str(target_student)]

        submissions = {str(item.get("student_id", item.get("studentId"))): item for item in submission_items}
        already = {str(item.get("studentId", item.get("student_id"))) for item in launched_items}

        launched = already_launched = awaiting = not_submitted = 0
        new_grades: list[dict[str, Any]] = []
        for student_id in recipients:
            submission = submissions.get(student_id)
            if submission is None:
                not_submitted += 1
                continue
            if student_id in already:
                already_launched += 1
                continue
            stored = ActivitySubmissionService.parse_stored_result(submission.get("content", "{}"))
            if stored.pendingCount > 0:
                awaiting += 1
                continue
            student = students.get(student_id)
            student_classroom = classroom_id or str((student or {}).get("class_id", (student or {}).get("classId", "")) or "")
            if not student or not student_classroom:
                not_submitted += 1
                continue
            new_grades.append({
                "studentId": student_id,
                "classroomId": student_classroom,
                "grade": round(stored.scorePercent / 10, 1),
                "subject": activity.get("subject"),
                "activityType": "ASSIGNMENT",
                "observations": f"Atividade: {activity.get('title', '')}"[:500],
                "activityId": activity_id,
                "date": submission.get("submitted_at", submission.get("submittedAt")) or datetime.now(timezone.utc),
                "createdAt": datetime.now(timezone.utc),
            })
            launched += 1
        self.repository.insert_many(new_grades)

        return ActivityGradesLaunchResponse(
            activityId=activity_id,
            activityTitle=str(activity.get("title", "")),
            launched=launched,
            alreadyLaunched=already_launched,
            awaitingCorrection=awaiting,
            notSubmitted=not_submitted,
        )

    def validate_references(self, student_id: str, classroom_id: str, require_enrollment: bool = False) -> None:
        student = self.student_repository.find_by_id(student_id)
        if not student:
            raise HTTPException(status_code=400, detail=f"Aluno não encontrado: {student_id}")
        classroom = self.classroom_repository.find_by_id(classroom_id)
        if not classroom:
            raise HTTPException(status_code=400, detail=f"Turma não encontrada: {classroom_id}")
        if require_enrollment and not self.is_enrolled(student, classroom, student_id, classroom_id):
            raise HTTPException(status_code=400, detail="O aluno não está matriculado na turma informada")

    @staticmethod
    def is_enrolled(student: dict[str, Any], classroom: dict[str, Any], student_id: str, classroom_id: str) -> bool:
        # A matrícula existe em dois lugares (class_id do aluno e lista de alunos da turma): vale qualquer um.
        if str(student.get("class_id", student.get("classId")) or "") == str(classroom_id):
            return True
        members = classroom.get("students", classroom.get("student_ids", classroom.get("studentIds", []))) or []
        return str(student_id) in {str(member) for member in members}

    @staticmethod
    def validate_date(value: datetime) -> None:
        # Tolerância de um dia para diferenças de fuso entre o navegador e o servidor.
        limit = datetime.now(timezone.utc) + timedelta(days=1)
        moment = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if moment > limit:
            raise HTTPException(status_code=422, detail="A data do lançamento não pode estar no futuro")

    @staticmethod
    def to_response(document: dict[str, Any]) -> GradeResponse:
        raw_id = document.get("_id", document.get("id"))
        value = document.get("grade", document.get("gradeValue"))
        return GradeResponse(
            id=str(raw_id),
            studentId=str(document.get("studentId", document.get("student_id", ""))),
            classroomId=str(document.get("classroomId", document.get("classroom_id", ""))),
            subject=document.get("subject"),
            grade=float(value),
            gradeValue=float(value),
            attendance=document.get("attendance"),
            date=document.get("date"),
            activityType=document.get("activityType", document.get("activity_type")),
            observations=document.get("observations"),
            activityId=document.get("activityId", document.get("activity_id")),
            createdAt=document.get("createdAt", document.get("created_at")),
        )
