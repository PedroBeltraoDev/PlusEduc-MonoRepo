// Serviço de gerenciamento de turmas

import { apiClient } from './api';
import type { Classroom, PaginatedResponse } from '@/types';

export interface CreateClassroomRequest {
  name: string;
  year: number;
  gradeLevel: string;
  teacherId: string;
  subjects: string[];
}

export interface UpdateClassroomRequest extends Partial<CreateClassroomRequest> {
  active?: boolean;
}

export interface ClassroomPerformance {
  classroomId: string;
  averageGrade: number;
  studentsCount: number;
  subjectPerformance: {
    subject: string;
    average: number;
    studentsCount: number;
  }[];
}

export interface ClassroomAttendance {
  classroomId: string;
  attendanceRate: number;
  totalClasses: number;
  averageAttendedClasses: number;
  studentsCount: number;
}

class ClassroomsService {
  // Criar turma
  async createClassroom(data: CreateClassroomRequest): Promise<Classroom> {
    return apiClient.post<Classroom>('/classrooms', data);
  }

  // Listar todas as turmas
  async getAllClassrooms(): Promise<Classroom[]> {
    return apiClient.get<Classroom[]>('/classrooms');
  }

  // Listar turmas com paginação
  async getClassroomsPaginated(
    page: number = 0,
    size: number = 10,
    sort?: string
  ): Promise<PaginatedResponse<Classroom>> {
    const params = new URLSearchParams({
      page: page.toString(),
      size: size.toString(),
      ...(sort && { sort })
    });

    return apiClient.get<PaginatedResponse<Classroom>>(`/classrooms/paginated?${params}`);
  }

  // Buscar turma por ID
  async getClassroomById(id: string): Promise<Classroom> {
    return apiClient.get<Classroom>(`/classrooms/${id}`);
  }

  // Buscar turmas por professor
  async getClassroomsByTeacher(teacherId: string): Promise<Classroom[]> {
    return apiClient.get<Classroom[]>(`/classrooms/teacher/${teacherId}`);
  }

  // Buscar turmas por ano
  async getClassroomsByYear(year: number): Promise<Classroom[]> {
    return apiClient.get<Classroom[]>(`/classrooms/year/${year}`);
  }

  // Atualizar turma
  async updateClassroom(id: string, data: UpdateClassroomRequest): Promise<Classroom> {
    return apiClient.put<Classroom>(`/classrooms/${id}`, data);
  }

  // Deletar turma
  async deleteClassroom(id: string): Promise<void> {
    return apiClient.delete(`/classrooms/${id}`);
  }

  // Matricular aluno na turma
  async enrollStudent(classroomId: string, studentId: string): Promise<void> {
    return apiClient.post(`/classrooms/${classroomId}/enroll/${studentId}`);
  }

  // Remover aluno da turma
  async unenrollStudent(classroomId: string, studentId: string): Promise<void> {
    return apiClient.delete(`/classrooms/${classroomId}/unenroll/${studentId}`);
  }

  // Obter desempenho da turma
  async getClassroomPerformance(id: string): Promise<ClassroomPerformance> {
    return apiClient.get<ClassroomPerformance>(`/classrooms/${id}/performance`);
  }

  // Obter frequência da turma
  async getClassroomAttendance(id: string): Promise<ClassroomAttendance> {
    return apiClient.get<ClassroomAttendance>(`/classrooms/${id}/attendance`);
  }

  // Buscar turmas (com filtros)
  async searchClassrooms(query: string): Promise<Classroom[]> {
    const allClassrooms = await this.getAllClassrooms();
    return allClassrooms.filter(classroom =>
      classroom.name.toLowerCase().includes(query.toLowerCase()) ||
      classroom.gradeLevel.toLowerCase().includes(query.toLowerCase()) ||
      classroom.subjects.some(subject =>
        subject.toLowerCase().includes(query.toLowerCase())
      )
    );
  }

  // Obter estatísticas das turmas
  async getClassroomsStats() {
    const classrooms = await this.getAllClassrooms();
    const activeClassrooms = classrooms.filter(c => c.active);

    // Calcular estatísticas
    const totalStudents = classrooms.reduce((acc, c) => acc + c.studentIds.length, 0);
    const averageStudentsPerClass = classrooms.length > 0 ? totalStudents / classrooms.length : 0;

    // Agrupar por ano
    const classroomsByYear = classrooms.reduce((acc, c) => {
      acc[c.year] = (acc[c.year] || 0) + 1;
      return acc;
    }, {} as Record<number, number>);

    // Disciplinas mais comuns
    const subjectCount = classrooms.reduce((acc, c) => {
      c.subjects.forEach(subject => {
        acc[subject] = (acc[subject] || 0) + 1;
      });
      return acc;
    }, {} as Record<string, number>);

    const mostCommonSubjects = Object.entries(subjectCount)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 5)
      .map(([subject, count]) => ({ subject, count }));

    return {
      total: classrooms.length,
      active: activeClassrooms.length,
      inactive: classrooms.length - activeClassrooms.length,
      totalStudents,
      averageStudentsPerClass: Math.round(averageStudentsPerClass * 100) / 100,
      classroomsByYear,
      mostCommonSubjects
    };
  }
}

export const classroomsService = new ClassroomsService();