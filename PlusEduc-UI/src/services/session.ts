// Sessão do usuário guardada no localStorage (compartilhada pelo cliente HTTP e pelo serviço de autenticação).

import type { AuthResponse } from '@/types';
import { AUTH_KEYS } from './authKeys';

export function persistSession(response: AuthResponse): void {
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

export function clearSession(): void {
  Object.values(AUTH_KEYS).forEach((key) => localStorage.removeItem(key));
}

// O token de acesso venceu pelo relógio local (o servidor continua sendo quem decide).
export function isAccessTokenExpired(marginMs = 0): boolean {
  const expiresIn = localStorage.getItem(AUTH_KEYS.expiresIn);
  const loginTime = localStorage.getItem(AUTH_KEYS.loginTime);
  if (!expiresIn || !loginTime) return true;
  return Date.now() + marginMs >= parseInt(loginTime, 10) + parseInt(expiresIn, 10) * 1000;
}
