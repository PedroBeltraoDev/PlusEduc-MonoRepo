// Serviço de autenticação

import { apiClient, storeTokens } from './api';
import { AUTH_KEYS } from './authKeys';
import type {
  AuthResponse,
  LoginRequest,
  ProfileUpdateRequest,
  RegisterTeacherRequest,
  StudentRegistrationRequest,
  TeacherRegistrationResponse,
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

  // Cadastro de professor fica pendente até um administrador aprovar: não abre sessão.
  async registerTeacher(data: RegisterTeacherRequest): Promise<TeacherRegistrationResponse> {
    return apiClient.post<TeacherRegistrationResponse>('/auth/register/teacher', data);
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<AuthResponse> {
    const response = await apiClient.post<AuthResponse>('/auth/change-password', { currentPassword, newPassword });
    this.persistSession(response);
    return response;
  }

  async forgotPassword(email: string): Promise<{ message: string; demoCode?: string | null }> {
    return apiClient.post<{ message: string; demoCode?: string | null }>('/auth/forgot-password', { email });
  }

  async resetPassword(data: { email: string; code: string; newPassword: string }): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>('/auth/reset-password', data);
  }

  logout(): void {
    // Revoga o refresh token no servidor (sem esperar a resposta) e limpa a sessão local.
    const refreshToken = localStorage.getItem(AUTH_KEYS.refreshToken);
    if (refreshToken) {
      void apiClient.post('/auth/logout', { refreshToken }).catch(() => undefined);
    }
    Object.values(AUTH_KEYS).forEach((key) => localStorage.removeItem(key));
  }

  isAuthenticated(): boolean {
    const token = localStorage.getItem(AUTH_KEYS.accessToken);
    const expiresIn = localStorage.getItem(AUTH_KEYS.expiresIn);
    const loginTime = localStorage.getItem(AUTH_KEYS.loginTime);

    if (!token || !expiresIn || !loginTime) {
      return false;
    }

    // Access token vencido não encerra a sessão: o cliente HTTP renova com o refresh token.
    if (localStorage.getItem(AUTH_KEYS.refreshToken)) {
      return true;
    }
    const tokenExpiration = parseInt(loginTime) + parseInt(expiresIn) * 1000;
    if (Date.now() >= tokenExpiration) {
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
    if (!response.accessToken) return;

    storeTokens(response);
    localStorage.setItem(AUTH_KEYS.userId, response.userId);
    localStorage.setItem(AUTH_KEYS.userEmail, response.userEmail);
    localStorage.setItem(AUTH_KEYS.role, response.role);

    if (response.studentId) {
      localStorage.setItem(AUTH_KEYS.studentId, response.studentId);
    } else {
      localStorage.removeItem(AUTH_KEYS.studentId);
    }

    if (response.name) {
      localStorage.setItem(AUTH_KEYS.userName, response.name);
    } else {
      localStorage.removeItem(AUTH_KEYS.userName);
    }
  }
}

export const authService = new AuthService();
