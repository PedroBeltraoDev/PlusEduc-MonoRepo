import { apiClient } from './api';
import type { Teacher } from '@/types';

class TeachersService {
  async getByEmail(email: string): Promise<Teacher> {
    return apiClient.get<Teacher>(`/teachers/email/${encodeURIComponent(email)}`);
  }
}

export const teachersService = new TeachersService();
