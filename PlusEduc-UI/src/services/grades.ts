// Serviço do módulo Notas e Frequência (professor)

import { apiClient } from './api';
import type { GradeRecord } from '@/types';

export interface GradeStudentSummary {
  studentId: string;
  studentName: string;
  average: number;
  launches: number;
  totalClasses: number;
  attendedClasses: number;
  absences: number;
  attendanceRate: number;
  lastLaunchAt?: string | null;
}

export interface GradeClassroomSummary {
  classroomId: string;
  classroomName: string;
  subject?: string | null;
  studentsCount: number;
  totalLaunches: number;
  averageGrade: number;
  attendanceRate: number;
  students: GradeStudentSummary[];
}

export interface ActivityGradesLaunch {
  activityId: string;
  activityTitle: string;
  launched: number;
  alreadyLaunched: number;
  awaitingCorrection: number;
  notSubmitted: number;
}

export interface GradeFormData {
  studentId: string;
  classroomId: string;
  subject: string;
  activityType: string;
  grade: number;
  attendance: boolean | null;
  observations?: string;
  date: string;
}

class GradesService {
  getClassroomSummary(classroomId: string, subject?: string): Promise<GradeClassroomSummary> {
    const query = subject ? `?subject=${encodeURIComponent(subject)}` : '';
    return apiClient.get<GradeClassroomSummary>(`/grades/classroom/${classroomId}/summary${query}`);
  }

  getByStudent(studentId: string): Promise<GradeRecord[]> {
    return apiClient.get<GradeRecord[]>(`/grades/student/${studentId}`);
  }

  create(data: GradeFormData): Promise<GradeRecord> {
    return apiClient.post<GradeRecord>('/grades', this.toPayload(data));
  }

  update(id: string, data: GradeFormData): Promise<GradeRecord> {
    return apiClient.put<GradeRecord>(`/grades/${id}`, this.toPayload(data));
  }

  delete(id: string): Promise<void> {
    return apiClient.delete(`/grades/${id}`);
  }

  launchFromActivity(activityId: string): Promise<ActivityGradesLaunch> {
    return apiClient.post<ActivityGradesLaunch>(`/grades/from-activity/${activityId}`);
  }

  private toPayload(data: GradeFormData) {
    const { observations, attendance, ...rest } = data;
    return {
      ...rest,
      ...(attendance === null ? {} : { attendance }),
      ...(observations?.trim() ? { observations: observations.trim() } : {}),
    };
  }
}

export const gradesService = new GradesService();
