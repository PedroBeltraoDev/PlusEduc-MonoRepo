from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SubjectPerformance(BaseModel):
    subject: str
    average: float
    count: int


class StudentPerformanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    studentId: str
    averageGrade: float
    totalActivities: int
    completedActivities: int
    subjectPerformance: list[SubjectPerformance]


class StudentAttendanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    studentId: str
    attendanceRate: int
    totalClasses: int
    attendedClasses: int
    absences: int


class RecommendationEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal: str
    detail: str
    weight: float


class PedagogicalRecommendationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    studentId: str
    studentName: str
    priority: str
    recommendedSubject: str
    recommendedTopic: str
    recommendedDifficulty: str
    recommendedQuestionsCount: int
    rationale: str
    evidences: list[RecommendationEvidence]
    generatedAt: datetime


class ClassroomSubjectPerformance(BaseModel):
    subject: str
    average: float
    studentsCount: int


class ClassroomPerformanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    classroomId: str
    averageGrade: float
    studentsCount: int
    subjectPerformance: list[ClassroomSubjectPerformance]
