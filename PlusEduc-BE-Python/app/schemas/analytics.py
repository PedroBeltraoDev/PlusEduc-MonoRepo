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
