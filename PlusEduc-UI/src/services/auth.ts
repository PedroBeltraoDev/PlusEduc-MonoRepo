// Serviço de autenticação

import { apiClient } from './api';
import type {
  AuthResponse,
  LoginRequest,
  ProfileUpdateRequest,
  RegisterTeacherRequest,
  StudentRegistrationRequest,
  User,
} from '@/types';

const AUTH_KEYS = {
  accessToken: 'accessToken',
  refreshToken: 'refreshToken',
  tokenType: 'tokenType',
  expiresIn: 'expiresIn',
  loginTime: 'loginTime',
  userId: 'userId',
  userEmail: 'userEmail',
  role: 'role',
  studentId: 'studentId',
  userName: 'userName',
} as const;

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

  async registerTeacher(data: RegisterTeacherRequest): Promise<AuthResponse> {
    const response = await apiClient.post<AuthResponse>('/auth/register/teacher', data);
    this.persistSession(response);
    return response;
  }

  logout(): void {
    Object.values(AUTH_KEYS).forEach((key) => localStorage.removeItem(key));
  }

  isAuthenticated(): boolean {
    const token = localStorage.getItem(AUTH_KEYS.accessToken);
    const expiresIn = localStorage.getItem(AUTH_KEYS.expiresIn);
    const loginTime = localStorage.getItem(AUTH_KEYS.loginTime);

    if (!token || !expiresIn || !loginTime) {
      return false;
    }

    const currentTime = Date.now();
    const tokenExpiration = parseInt(loginTime) + parseInt(expiresIn) * 1000;

    if (currentTime >= tokenExpiration) {
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

    localStorage.setItem(AUTH_KEYS.accessToken, response.accessToken);
    localStorage.setItem(AUTH_KEYS.refreshToken, response.refreshToken);
    localStorage.setItem(AUTH_KEYS.tokenType, response.tokenType);
    localStorage.setItem(AUTH_KEYS.expiresIn, response.expiresIn.toString());
    localStorage.setItem(AUTH_KEYS.loginTime, Date.now().toString());
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
