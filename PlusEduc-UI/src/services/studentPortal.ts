import { apiClient } from './api';
import type {
  Classmate,
  GradeRecord,
  QuestionAnswer,
  StudentActivity,
  StudentActivityDetail,
  StudentClassroom,
  StudentPortalPerformance,
  StudentPortalProfile,
  StudentSubmissionResult,
  TeacherSummary,
} from '@/types';

class StudentPortalService {
  async getProfile(): Promise<StudentPortalProfile> {
    return apiClient.get<StudentPortalProfile>('/student-portal/me');
  }

  async getClassroom(): Promise<StudentClassroom> {
    return apiClient.get<StudentClassroom>('/student-portal/classroom');
  }

  async getClassmates(): Promise<Classmate[]> {
    return apiClient.get<Classmate[]>('/student-portal/classmates');
  }

  async getTeachers(): Promise<TeacherSummary[]> {
    return apiClient.get<TeacherSummary[]>('/student-portal/teachers');
  }

  async getActivities(): Promise<StudentActivity[]> {
    return apiClient.get<StudentActivity[]>('/student-portal/activities');
  }

  async getActivity(id: string): Promise<StudentActivityDetail> {
    return apiClient.get<StudentActivityDetail>(`/student-portal/activities/${id}`);
  }

  async submitActivity(id: string, answers: QuestionAnswer[]): Promise<StudentSubmissionResult> {
    return apiClient.post<StudentSubmissionResult>(`/student-portal/activities/${id}/submissions`, { answers });
  }

  async getGrades(): Promise<GradeRecord[]> {
    return apiClient.get<GradeRecord[]>('/student-portal/grades');
  }

  async getPerformance(): Promise<StudentPortalPerformance> {
    return apiClient.get<StudentPortalPerformance>('/student-portal/performance');
  }

  async downloadActivityPdf(id: string, title: string): Promise<void> {
    const response = await fetch(`/api/student-portal/activities/${id}/export-pdf`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${localStorage.getItem('accessToken')}`,
      },
    });

    if (!response.ok) {
      throw new Error('Erro ao baixar PDF da atividade');
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }
}

export const studentPortalService = new StudentPortalService();
