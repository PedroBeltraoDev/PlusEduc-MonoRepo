// Rotas exclusivas do administrador.
import { apiClient } from './api';
import type { TeacherRequest } from '@/types';

class AdminService {
  listTeacherRequests(): Promise<TeacherRequest[]> {
    return apiClient.get<TeacherRequest[]>('/admin/teacher-requests');
  }

  approveTeacher(userId: string): Promise<void> {
    return apiClient.post<void>(`/admin/teacher-requests/${userId}/approve`);
  }

  rejectTeacher(userId: string): Promise<void> {
    return apiClient.post<void>(`/admin/teacher-requests/${userId}/reject`);
  }
}

export const adminService = new AdminService();
