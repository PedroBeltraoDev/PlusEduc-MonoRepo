from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException

from app.core.auth import UserPrincipal
from app.repositories.activity_repository import ActivityRepository
from app.repositories.activity_submission_repository import ActivitySubmissionRepository
from app.repositories.classroom_repository import ClassroomRepository
from app.repositories.grade_repository import GradeRepository
from app.repositories.student_repository import StudentRepository
from app.repositories.teacher_repository import TeacherRepository
from app.schemas.activity import ActivityResponse
from app.schemas.activity_submission import ActivitySubmissionRequest, StudentSubmissionResult
from app.schemas.student_portal_schema import (
    Classmate,
    StudentActivity,
    StudentActivityDetail,
    StudentClassroom,
    StudentPortalGrade,
    StudentPortalPerformance,
    StudentPortalProfile,
    StudentQuestion,
    TeacherSummary,
)
from app.services.activity_pdf_service import ActivityPdfService
from app.services.activity_service import ActivityService
from app.services.activity_submission_service import ActivitySubmissionService
from app.services.grade_service import GradeService
from app.services.student_analytics_service import StudentAnalyticsService


class StudentPortalService:
    def __init__(
        self,
        student_repository: StudentRepository,
        classroom_repository: ClassroomRepository,
        teacher_repository: TeacherRepository,
        activity_repository: ActivityRepository,
        activity_submission_repository: ActivitySubmissionRepository,
        grade_repository: GradeRepository,
        mongo,
    ) -> None:
        self.student_repository = student_repository
        self.classroom_repository = classroom_repository
        self.teacher_repository = teacher_repository
        self.activity_repository = activity_repository
        self.activity_submission_repository = activity_submission_repository
        self.grade_repository = grade_repository
        self.mongo = mongo

    def current_student(self, current_user: UserPrincipal) -> dict[str, Any]:
        if current_user.role.upper() != "STUDENT":
            raise HTTPException(status_code=403, detail="Acesso permitido apenas para alunos")
        student = None
        if current_user.student_id:
            student = self.student_repository.find_by_id(current_user.student_id)
        if not student and hasattr(self.student_repository, "find_by_user_id_and_active"):
            student = self.student_repository.find_by_user_id_and_active(current_user.user_id)
        if not student and hasattr(self.student_repository, "find_active_by_email"):
            student = self.student_repository.find_active_by_email(current_user.email)
        if not student:
            raise HTTPException(status_code=400, detail="Perfil de aluno não encontrado. Solicite ao professor a liberação do acesso.")
        if student.get("active", True) is False:
            raise HTTPException(status_code=400, detail="Perfil de aluno não encontrado. Solicite ao professor a liberação do acesso.")
        return student

    def profile(self, current_user: UserPrincipal) -> StudentPortalProfile:
        student = self.current_student(current_user)
        class_id = self._first(student, "classId", "class_id")
        return StudentPortalProfile(
            studentId=self._id(student),
            userId=self._first(student, "userId", "user_id") or current_user.user_id,
            name=student.get("name", ""),
            email=student.get("email", current_user.email),
            classId=str(class_id) if class_id else None,
            className=self.class_name(class_id),
        )

    def classroom(self, current_user: UserPrincipal) -> StudentClassroom:
        student = self.current_student(current_user)
        class_id = self._first(student, "classId", "class_id")
        if not class_id:
            raise HTTPException(status_code=400, detail="Aluno não está vinculado a uma turma")
        classroom = self.classroom_repository.find_by_id(str(class_id))
        if not classroom or classroom.get("active", True) is False:
            raise HTTPException(status_code=404, detail=f"Turma não encontrada: {class_id}")
        return StudentClassroom(
            id=self._id(classroom),
            name=classroom.get("name", ""),
            year=int(classroom.get("year", 0)),
            gradeLevel=classroom.get("gradeLevel", classroom.get("grade_level", "")),
            subjects=classroom.get("subjects", []) or [],
        )

    def classmates(self, current_user: UserPrincipal) -> list[Classmate]:
        student = self.current_student(current_user)
        class_id = self._first(student, "classId", "class_id")
        if not class_id:
            return []
        students = self.student_repository.find_active_by_class_flexible(str(class_id))
        return sorted(
            [
                Classmate(id=self._id(item), name=item.get("name", ""), email=item.get("email", ""))
                for item in students
                if self._id(item) != self._id(student)
            ],
            key=lambda item: item.name.lower(),
        )

    def teachers(self, current_user: UserPrincipal) -> list[TeacherSummary]:
        student = self.current_student(current_user)
        class_id = self._first(student, "classId", "class_id")
        if not class_id:
            return []
        classroom = self.classroom_repository.find_by_id(str(class_id))
        if not classroom or classroom.get("active", True) is False:
            raise HTTPException(status_code=404, detail=f"Turma não encontrada: {class_id}")
        classroom_subjects = classroom.get("subjects", []) or []
        found: dict[str, dict[str, Any]] = {}
        teacher_reference = self._first(classroom, "teacherId", "teacher_id")
        if teacher_reference:
            teacher = self.teacher_repository.find_by_id(str(teacher_reference))
            if teacher and teacher.get("active", True) is not False:
                found[self._id(teacher)] = teacher
            teacher = self.teacher_repository.find_active_by_email(str(teacher_reference))
            if teacher:
                found[self._id(teacher)] = teacher
        for teacher in self.teacher_repository.find_active():
            classroom_ids = teacher.get("classroomIds", teacher.get("classroom_ids", [])) or []
            if str(class_id) in {str(value) for value in classroom_ids}:
                found[self._id(teacher)] = teacher
        result = []
        for teacher in found.values():
            subjects = teacher.get("subjects", []) or classroom_subjects
            result.append(TeacherSummary(
                id=self._id(teacher),
                name=teacher.get("name", ""),
                email=teacher.get("email", ""),
                subjects=subjects,
            ))
        return sorted(result, key=lambda item: item.name.lower())

    def activities(self, current_user: UserPrincipal) -> list[StudentActivity]:
        student = self.current_student(current_user)
        accessible = self.accessible_activities(student)
        submitted_ids = {
            str(item.get("activity_id", item.get("activityId")))
            for item in self.activity_submission_repository.find_by_student(self._id(student))
        }
        result = [self.to_student_activity(item, self._id(item) in submitted_ids) for item in accessible]
        return sorted(result, key=lambda item: item.createdAt or datetime.min, reverse=True)

    def activity_detail(self, activity_id: str, current_user: UserPrincipal) -> StudentActivityDetail:
        student = self.current_student(current_user)
        activity = self.find_accessible_activity(student, activity_id)
        activity_service = self._activity_service()
        questions = activity_service.parse_questions(activity.get("content"))
        submission = self.activity_submission_repository.find_by_activity_student(activity_id, self._id(student))
        base = {
            "id": self._id(activity),
            "title": activity.get("title", ""),
            "subject": activity.get("subject", ""),
            "topic": activity.get("topic", ""),
            "difficultyLevel": self._first(activity, "difficulty_level", "difficultyLevel") or "",
            "format": activity.get("format", ""),
            "classroomName": self.class_name(self._first(activity, "classroom_id", "classroomId")),
            "createdAt": self._first(activity, "created_at", "createdAt"),
        }
        if submission:
            stored = ActivitySubmissionService.parse_stored_result(submission.get("content", "{}"))
            return StudentActivityDetail(
                **base,
                submitted=True,
                questions=[],
                correctCount=stored.correctCount,
                totalQuestions=stored.totalQuestions,
                scorePercent=stored.scorePercent,
                pendingCount=stored.pendingCount,
                results=stored.results,
                submittedAt=self._first(submission, "submitted_at", "submittedAt"),
            )
        hidden_questions = [
            StudentQuestion(
                questionIndex=index,
                questionText=question.questionText,
                questionType=question.questionType,
                options=question.options or [],
            )
            for index, question in enumerate(questions)
        ]
        return StudentActivityDetail(**base, submitted=False, questions=hidden_questions, results=[])

    def submit_activity(self, activity_id: str, payload: ActivitySubmissionRequest, current_user: UserPrincipal) -> StudentSubmissionResult:
        student = self.current_student(current_user)
        activity = self.find_accessible_activity(student, activity_id)
        service = self._submission_service()
        return service.submit_for_student(activity_id, payload, self._id(student), activity=activity)

    def grades(self, current_user: UserPrincipal) -> list[StudentPortalGrade]:
        student = self.current_student(current_user)
        repository_items = self.grade_repository.find_by_student(self._id(student))
        from app.services.grade_service import GradeService
        return [GradeService.to_response(item) for item in repository_items]

    def performance(self, current_user: UserPrincipal) -> StudentPortalPerformance:
        student = self.current_student(current_user)
        analytics = StudentAnalyticsService(
            self.student_repository,
            self.grade_repository,
            self.classroom_repository,
        )
        performance = analytics.performance(self._id(student))
        attendance = analytics.attendance(self._id(student))
        return StudentPortalPerformance(
            studentId=performance.studentId,
            averageGrade=performance.averageGrade,
            totalActivities=performance.totalActivities,
            completedActivities=performance.completedActivities,
            subjectPerformance=performance.subjectPerformance,
            attendanceRate=attendance.attendanceRate,
            totalClasses=attendance.totalClasses,
            attendedClasses=attendance.attendedClasses,
            absences=attendance.absences,
        )

    def export_pdf(self, activity_id: str, current_user: UserPrincipal) -> bytes:
        student = self.current_student(current_user)
        activity = self.find_accessible_activity(student, activity_id)
        return ActivityPdfService(
            self.student_repository,
            self.classroom_repository,
        ).generate(activity, include_answers=False)

    def accessible_activities(self, student: dict[str, Any]) -> list[dict[str, Any]]:
        student_id = self._id(student)
        direct = self.activity_repository.find_by_student(student_id)
        class_id = self._first(student, "classId", "class_id")
        classroom_activities = self.activity_repository.find_by_classroom(str(class_id)) if class_id else []
        result: dict[str, dict[str, Any]] = {self._id(item): item for item in direct}
        for item in classroom_activities:
            assigned_student = self._first(item, "student_id", "studentId")
            if not assigned_student:
                result.setdefault(self._id(item), item)
        return list(result.values())

    def find_accessible_activity(self, student: dict[str, Any], activity_id: str) -> dict[str, Any]:
        for activity in self.accessible_activities(student):
            if self._id(activity) == str(activity_id):
                return activity
        raise HTTPException(status_code=404, detail=f"Atividade não encontrada: {activity_id}")

    def to_student_activity(self, activity: dict[str, Any], submitted: bool) -> StudentActivity:
        classroom_id = self._first(activity, "classroom_id", "classroomId")
        return StudentActivity(
            id=self._id(activity),
            title=activity.get("title", ""),
            subject=activity.get("subject", ""),
            topic=activity.get("topic", ""),
            difficultyLevel=self._first(activity, "difficulty_level", "difficultyLevel") or "",
            format=activity.get("format", ""),
            classroomId=str(classroom_id) if classroom_id else None,
            classroomName=self.class_name(classroom_id),
            submitted=submitted,
            createdAt=self._first(activity, "created_at", "createdAt"),
        )

    def class_name(self, class_id: Any) -> str | None:
        if not class_id:
            return None
        classroom = self.classroom_repository.find_by_id(str(class_id))
        return classroom.get("name") if classroom else None

    def _activity_service(self) -> ActivityService:
        return ActivityService(
            self.activity_repository,
            self.student_repository,
            self.classroom_repository,
            self.mongo,
            getattr(self.mongo, "settings", None),
        )

    def _submission_service(self) -> ActivitySubmissionService:
        return ActivitySubmissionService(
            self.activity_repository,
            self.activity_submission_repository,
            self._activity_service(),
        )

    @staticmethod
    def _first(document: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            value = document.get(key)
            if value is not None:
                return value
        return None

    @staticmethod
    def _id(document: dict[str, Any]) -> str:
        return str(document.get("_id", document.get("id", "")))
