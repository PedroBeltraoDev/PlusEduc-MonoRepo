from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.analytics import SubjectPerformance
from app.schemas.grade import GradeResponse


class StudentPortalProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    studentId: str
    userId: str | None = None
    name: str
    email: str
    classId: str | None = None
    className: str | None = None


class StudentClassroom(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    year: int
    gradeLevel: str
    subjects: list[str] = Field(default_factory=list)


class Classmate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    email: str


class TeacherSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    email: str
    subjects: list[str] = Field(default_factory=list)


class StudentActivity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    subject: str
    topic: str
    difficultyLevel: str
    format: str
    classroomId: str | None = None
    classroomName: str | None = None
    submitted: bool
    createdAt: datetime | None = None


class StudentQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questionIndex: int
    questionText: str
    questionType: str
    options: list[str] = Field(default_factory=list)


class StudentActivityDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    subject: str
    topic: str
    difficultyLevel: str
    format: str
    classroomName: str | None = None
    submitted: bool
    questions: list[StudentQuestion] = Field(default_factory=list)
    correctCount: int | None = None
    totalQuestions: int | None = None
    scorePercent: int | None = None
    results: list[object] = Field(default_factory=list)
    submittedAt: datetime | None = None
    createdAt: datetime | None = None


class StudentPortalPerformance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    studentId: str
    averageGrade: float
    totalActivities: int
    completedActivities: int
    subjectPerformance: list[SubjectPerformance] = Field(default_factory=list)
    attendanceRate: int
    totalClasses: int
    attendedClasses: int
    absences: int


StudentPortalGrade = GradeResponse
