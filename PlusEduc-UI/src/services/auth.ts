// Serviço de autenticação

import { apiClient } from './api';
import { AUTH_KEYS } from './authKeys';
import { clearSession, isAccessTokenExpired, persistSession } from './session';
import type {
  AuthResponse,
  LoginRequest,
  ProfileUpdateRequest,
  RegisterTeacherRequest,
  StudentRegistrationRequest,
  TeacherRegistrationPending,
  User,
} from '@/types';


class AuthService {
  async login(credentials: LoginRequest): Promise<AuthResponse> {
    const response = await apiClient.post<AuthResponse>('/auth/login', credentials);
    this.persistSession(response);
    return response;
  }

  async updateProfile(data: ProfileUpdateRequest): Promise<AuthResponse> {
    const response = await apiClient.put<AuthResponse>('/auth/profile', data);
    this.persistSession(response);
    return response;
  }

  async registerStudent(data: StudentRegistrationRequest): Promise<AuthResponse> {
    const response = await apiClient.post<AuthResponse>('/auth/register/student', data);
    this.persistSession(response);
    return response;
  }

  // Com a aprovação ligada (padrão), o servidor devolve 202 sem tokens: o professor só entra depois do ADMIN aprovar.
  async registerTeacher(data: RegisterTeacherRequest): Promise<AuthResponse | TeacherRegistrationPending> {
    const response = await apiClient.post<AuthResponse | TeacherRegistrationPending>('/auth/register/teacher', data);
    if ('accessToken' in response) {
      this.persistSession(response);
    }
    return response;
  }

  async changePassword(data: { currentPassword: string; newPassword: string }): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>('/auth/change-password', data);
  }

  async forgotPassword(email: string): Promise<{ message: string; demoCode?: string | null }> {
    return apiClient.post<{ message: string; demoCode?: string | null }>('/auth/forgot-password', { email });
  }

  async resetPassword(data: { email: string; code: string; newPassword: string }): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>('/auth/reset-password', data);
  }

  logout(): void {
    clearSession();
  }

  // Com o token de acesso vencido a sessão continua enquanto houver refresh token: a próxima chamada
  // à API renova os tokens (ou leva ao login, se o servidor recusar a renovação).
  isAuthenticated(): boolean {
    const token = localStorage.getItem(AUTH_KEYS.accessToken);
    if (!token) {
      return false;
    }
    if (isAccessTokenExpired() && !localStorage.getItem(AUTH_KEYS.refreshToken)) {
      this.logout();
      return false;
    }
    return true;
  }

  getAccessToken(): string | null {
    return localStorage.getItem(AUTH_KEYS.accessToken);
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(AUTH_KEYS.refreshToken);
  }

  getRole(): User['role'] | null {
    const role = localStorage.getItem(AUTH_KEYS.role);
    if (role === 'TEACHER' || role === 'ADMIN' || role === 'STUDENT') {
      return role;
    }
    return null;
  }

  getStudentId(): string | null {
    return localStorage.getItem(AUTH_KEYS.studentId);
  }

  getUserId(): string | null {
    return localStorage.getItem(AUTH_KEYS.userId);
  }

  getUserEmail(): string | null {
    return localStorage.getItem(AUTH_KEYS.userEmail);
  }

  getUserName(): string | null {
    return localStorage.getItem(AUTH_KEYS.userName);
  }

  isStudent(): boolean {
    return this.getRole() === 'STUDENT';
  }

  isEducator(): boolean {
    const role = this.getRole();
    return role === 'TEACHER' || role === 'ADMIN';
  }

  getHomePath(): string {
    return this.isStudent() ? '/aluno' : '/dashboard';
  }

  isTokenExpiring(): boolean {
    const expiresIn = localStorage.getItem(AUTH_KEYS.expiresIn);
    const loginTime = localStorage.getItem(AUTH_KEYS.loginTime);

    if (!expiresIn || !loginTime) {
      return true;
    }

    const currentTime = Date.now();
    const tokenExpiration = parseInt(loginTime) + parseInt(expiresIn) * 1000;
    const fifteenMinutes = 15 * 60 * 1000;

    return tokenExpiration - currentTime < fifteenMinutes;
  }

  private persistSession(response: AuthResponse): void {
    persistSession(response);
  }
}

export const authService = new AuthService();
