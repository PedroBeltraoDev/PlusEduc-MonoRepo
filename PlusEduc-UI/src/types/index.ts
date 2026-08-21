// Tipos baseados na API PlusEduc Backend

// Learning Gaps (Lacunas de Aprendizagem)
export interface LearningGap {
  subject: string;
  topic: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH';
  description: string;
  identifiedDate: string | null;
  improvementStatus: 'IDENTIFIED' | 'IN_PROGRESS' | 'IMPROVED' | 'RESOLVED';
}

// Student (Aluno)
export interface Student {
  id: string;
  name: string;
  email: string;
  matricula?: string | null;
  birthDate: string | null;
  classId?: string | null;
  className?: string | null;
  _class?: string | null; // Campo do MongoDB para nome da turma
  learningGaps: LearningGap[] | null;
  active: boolean;
  createdAt: string | null;
  updatedAt: string | null;
}

// Teacher (Professor)
export interface Teacher {
  id: string;
  name: string;
  email: string;
  subjects: string[];
  classroomIds: string[];
  active: boolean;
}

// Classroom (Turma)
export interface SubjectTeacherSummary {
  subjectId: string;
  subjectName: string;
  teacherId: string;
  teacherName?: string | null;
}

export interface Classroom {
  id: string;
  name: string;
  year: number;
  gradeLevel: string;
  teacherId: string;
  studentIds: string[];
  subjects: string[];
  subjectTeachers?: SubjectTeacherSummary[];
  active: boolean;
}

// Grade (Nota)
export interface Grade {
  id: string;
  studentId: string;
  classroomId: string;
  subject: string;
  gradeValue: number;
  attendance: boolean;
  date: string;
  activityType: 'EXAM' | 'ASSIGNMENT' | 'QUIZ' | 'PROJECT' | 'PARTICIPATION';
  observations?: string;
}

// Activity (Atividade)
export interface ActivityParticipant {
  studentId: string;
  studentName: string;
  submittedAt?: string | null;
}

export interface ActivityParticipation {
  totalStudents: number;
  completedStudents: number;
  pendingStudents: number;
  completed: ActivityParticipant[];
  pending: ActivityParticipant[];
}

export interface Activity {
  id: string;
  title: string;
  subject: string;
  topic: string;
  difficultyLevel: string;
  questionsCount: number;
  format: string;
  classroomId?: string | null;
  classroomName?: string | null;
  studentId?: string | null;
  studentName?: string | null;
  disabilityAdaptations?: string[];
  questions?: GeneratedQuestion[];
  content: string;
  generatedByAi: boolean;
  aiProvider?: string;
  createdBy: string;
  creatorName?: string | null;
  pdfUrl?: string | null;
  createdAt: string;
  participation?: ActivityParticipation | null;
}

export interface SubjectTopic {
  id: string;
  subject: string;
  topics: string[];
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface GeneratedQuestion {
  questionText: string;
  questionType: 'MULTIPLA_ESCOLHA' | 'DISCURSIVA' | 'VERDADEIRO_FALSO';
  options: string[];
  correctAnswer?: string | null;
  explanation?: string | null;
  difficultyLevel?: string | null;
}

// User (Usuário)
export interface User {
  id: string;
  email: string;
  role: 'TEACHER' | 'ADMIN' | 'STUDENT';
  active: boolean;
  createdAt: string;
}

// Auth
export interface AuthResponse {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
  userId: string;
  userEmail: string;
  role: 'TEACHER' | 'ADMIN' | 'STUDENT';
  studentId?: string | null;
  name?: string | null;
}

export interface ProfileUpdateRequest {
  name: string;
  email: string;
}

// Portal do Aluno
export interface StudentPortalProfile {
  studentId: string;
  userId: string;
  name: string;
  email: string;
  classId: string;
  className: string;
}

export interface StudentClassroom {
  id: string;
  name: string;
  year: number;
  gradeLevel: string;
  subjects: string[];
}

export interface Classmate {
  id: string;
  name: string;
  email: string;
}

export interface TeacherSummary {
  id: string;
  name: string;
  email: string;
  subjects: string[];
}

export interface StudentActivity {
  id: string;
  title: string;
  subject: string;
  topic: string;
  difficultyLevel: string;
  format: string;
  classroomId?: string;
  classroomName?: string;
  submitted: boolean;
  createdAt: string;
}

export interface StudentQuestion {
  questionIndex: number;
  questionText: string;
  questionType: string;
  options: string[];
}

export interface QuestionAnswer {
  questionIndex: number;
  selectedAnswer: string;
}

export interface QuestionResult {
  questionIndex: number;
  questionText: string;
  questionType: string;
  options: string[];
  selectedAnswer: string;
  correctAnswer: string | null;
  correct: boolean;
  reviewStatus?: "AUTO_GRADED" | "PENDING" | "REVIEWED" | string;
  teacherFeedback?: string | null;
  reviewedBy?: string | null;
  reviewedAt?: string | null;
}

export interface StudentSubmissionResult {
  correctCount: number;
  totalQuestions: number;
  scorePercent: number;
  pendingCount?: number;
  results: QuestionResult[];
}

export interface PendingQuestion {
  questionIndex: number;
  questionText: string;
  selectedAnswer: string;
  reviewStatus: string;
}

export interface PendingCorrection {
  submissionId: string;
  activityId: string;
  activityTitle: string;
  subject?: string | null;
  topic?: string | null;
  classroomName?: string | null;
  studentId: string;
  studentName: string;
  submittedAt?: string | null;
  questions: PendingQuestion[];
}

export interface StudentActivityDetail {
  id: string;
  title: string;
  subject: string;
  topic: string;
  difficultyLevel: string;
  format: string;
  classroomName?: string;
  submitted: boolean;
  questions: StudentQuestion[];
  correctCount?: number | null;
  totalQuestions?: number | null;
  scorePercent?: number | null;
  pendingCount?: number | null;
  results: QuestionResult[];
  submittedAt?: string | null;
  createdAt: string;
}

export interface GradeRecord {
  id: string;
  studentId: string;
  classroomId: string;
  subject: string;
  grade: number;
  attendance: boolean;
  activityType: string;
  observations?: string;
  date: string;
  createdAt?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterTeacherRequest {
  name: string;
  email: string;
  password: string;
  subjects: string[];
}

export interface StudentRegistrationRequest {
  name: string;
  email: string;
  password: string;
}

// Activity Generation
export interface GenerateActivityRequest {
  subject: string;
  topic: string;
  difficultyLevel: string;
  questionsCount: number;
  format: string;
  classroomId: string;
  studentId?: string;
  disabilityAdaptations?: string[];
  additionalInstructions?: string;
}

// Performance & Attendance
export interface StudentPerformance {
  studentId: string;
  averageGrade: number;
  totalActivities: number;
  completedActivities: number;
  subjectPerformance: {
    subject: string;
    average: number;
    count: number;
  }[];
}

export interface PedagogicalRecommendationEvidence {
  signal: string;
  detail: string;
  weight: number;
}

export interface PedagogicalRecommendation {
  studentId: string;
  studentName: string;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  recommendedSubject: string;
  recommendedTopic: string;
  recommendedDifficulty: string;
  recommendedQuestionsCount: number;
  rationale: string;
  evidences: PedagogicalRecommendationEvidence[];
  generatedAt: string;
}

export interface StudentAttendance {
  studentId: string;
  attendanceRate: number;
  totalClasses: number;
  attendedClasses: number;
  absences: number;
}

export interface Subject {
  id: string;
  name: string;
  active: boolean;
  area?: string | null;
  gradeLevels?: string[] | null;
  curriculumKey?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface SubjectClassroom {
  id: string;
  name: string;
  year?: number | null;
  gradeLevel?: string | null;
  studentCount: number;
  averageGrade: number;
}

export interface SubjectStudentPerformance {
  studentId: string;
  studentName: string;
  studentEmail?: string | null;
  averageGrade: number;
  gradeCount: number;
  lastGrade?: number | null;
}

export interface StudentPortalPerformance {
  studentId: string;
  averageGrade: number;
  totalActivities: number;
  completedActivities: number;
  subjectPerformance: {
    subject: string;
    average: number;
    count: number;
  }[];
  attendanceRate: number;
  totalClasses: number;
  attendedClasses: number;
  absences: number;
}

// Dashboard Statistics
export interface DashboardStats {
  totalStudents: number;
  totalTeachers: number;
  totalClassrooms: number;
  totalActivities: number;
  averagePerformance: number;
  attendanceRate: number;
}

// Utility types
export type Theme = 'light' | 'dark' | 'system';
export type LoadingState = 'idle' | 'loading' | 'success' | 'error';

// API Response wrapper
export interface ApiResponse<T> {
  data: T;
  message?: string;
}

// Paginated response
export interface PaginatedResponse<T> {
  content: T[];
  totalPages: number;
  totalElements: number;
  size: number;
  number: number;
  first: boolean;
  last: boolean;
}
