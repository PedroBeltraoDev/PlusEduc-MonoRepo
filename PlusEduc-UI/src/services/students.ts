// Serviço de gerenciamento de alunos

import { apiClient } from './api';
import type {
  Student,
  LearningGap,
  PaginatedResponse,
  StudentPerformance,
  StudentAttendance,
  PedagogicalRecommendation
} from '@/types';

export interface CreateStudentRequest {
  name: string;
  email: string;
  birthDate?: string | null;
  classId?: string;
  active?: boolean;
  learningGaps?: LearningGap[];
}

export interface UpdateStudentRequest extends Partial<CreateStudentRequest> {
  learningGaps?: LearningGap[];
}

class StudentsService {
  // Criar aluno
  async createStudent(data: CreateStudentRequest): Promise<Student> {
    return apiClient.post<Student>('/students', data);
  }

  // Listar todos os alunos
  async getAllStudents(): Promise<Student[]> {
    return apiClient.get<Student[]>('/students');
  }

  // Listar alunos ativos sem turma para gestão pelo professor
  async getUnassignedStudents(): Promise<Student[]> {
    return apiClient.get<Student[]>('/students/unassigned');
  }

  // Listar alunos com paginação
  async getStudentsPaginated(
    page: number = 0,
    size: number = 10,
    sort?: string
  ): Promise<PaginatedResponse<Student>> {
    const params = new URLSearchParams({
      page: page.toString(),
      size: size.toString(),
      ...(sort && { sort })
    });

    return apiClient.get<PaginatedResponse<Student>>(`/students/paginated?${params}`);
  }

  // Buscar aluno por ID
  async getStudentById(id: string): Promise<Student> {
    return apiClient.get<Student>(`/students/${id}`);
  }

  // Buscar alunos por turma
  async getStudentsByClass(classId: string): Promise<Student[]> {
    return apiClient.get<Student[]>(`/students/class/${classId}`);
  }

  // Buscar alunos por lacuna de aprendizagem
  async getStudentsByLearningGap(subject: string): Promise<Student[]> {
    return apiClient.get<Student[]>(`/students/learning-gap/${subject}`);
  }

  // Atualizar aluno
  async updateStudent(id: string, data: UpdateStudentRequest): Promise<Student> {
    return apiClient.put<Student>(`/students/${id}`, data);
  }

  // Deletar aluno
  async deleteStudent(id: string): Promise<void> {
    return apiClient.delete(`/students/${id}`);
  }

  // Obter desempenho do aluno
  async getStudentPerformance(id: string): Promise<StudentPerformance> {
    return apiClient.get<StudentPerformance>(`/students/${id}/performance`);
  }

  // Obter frequência do aluno
  async getStudentAttendance(id: string): Promise<StudentAttendance> {
    return apiClient.get<StudentAttendance>(`/students/${id}/attendance`);
  }

  // Obter recomendação pedagógica explicável baseada em lacunas e desempenho
  async getPedagogicalRecommendation(id: string): Promise<PedagogicalRecommendation> {
    return apiClient.get<PedagogicalRecommendation>(`/students/${id}/pedagogical-recommendation`);
  }

  // Buscar alunos (com filtros)
  async searchStudents(query: string): Promise<Student[]> {
    const allStudents = await this.getAllStudents();
    return allStudents.filter(student =>
      student.name.toLowerCase().includes(query.toLowerCase()) ||
      student.email.toLowerCase().includes(query.toLowerCase())
    );
  }

  async enableStudentAccess(studentId: string, password: string): Promise<void> {
    await apiClient.post(`/students/${studentId}/enable-access`, { password });
  }

  // Obter estatísticas dos alunos
  async getStudentsStats() {
    const students = await this.getAllStudents();
    const activeStudents = students.filter(s => s.active);

    return {
      total: students.length,
      active: activeStudents.length,
      inactive: students.length - activeStudents.length,
      withLearningGaps: students.filter(s => (s.learningGaps?.length || 0) > 0).length
    };
  }
}

export const studentsService = new StudentsService();
