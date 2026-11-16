import { apiClient } from './api';
import type { PendingTeacher, Teacher } from '@/types';

class TeachersService {
  async getByEmail(email: string): Promise<Teacher> {
    return apiClient.get<Teacher>(`/teachers/email/${encodeURIComponent(email)}`);
  }

  async listActive(): Promise<Teacher[]> {
    return apiClient.get<Teacher[]>('/teachers');
  }

  // Cadastros públicos aguardando aprovação (somente ADMIN).
  async listPending(): Promise<PendingTeacher[]> {
    return apiClient.get<PendingTeacher[]>('/teachers/pending');
  }

  async approve(teacherId: string): Promise<Teacher> {
    return apiClient.post<Teacher>(`/teachers/${encodeURIComponent(teacherId)}/approve`);
  }

  async reject(teacherId: string): Promise<void> {
    await apiClient.post<void>(`/teachers/${encodeURIComponent(teacherId)}/reject`);
  }
}

export const teachersService = new TeachersService();
