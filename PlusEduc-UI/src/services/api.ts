// Cliente HTTP para consumir a API PlusEduc

import type { AuthResponse } from '@/types';
import { AUTH_KEYS, SESSION_EXPIRED_FLAG } from './authKeys';
import { clearSession, isAccessTokenExpired, persistSession } from './session';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

// Mensagens padrão do backend (em inglês) traduzidas para o usuário.
const FRIENDLY_MESSAGES: Record<string, string> = {
  'Invalid email or password': 'E-mail ou senha inválidos.',
  'Access denied': 'Você não tem permissão para realizar esta ação.',
  'Email already in use': 'Este e-mail já está em uso por outra conta.',
};

// Renovação da sessão com o refresh token (RF01). Uma única renovação por vez, mesmo que várias
// requisições recebam 401 ao mesmo tempo; se falhar, a sessão é encerrada.
let refreshInFlight: Promise<boolean> | null = null;

function refreshSession(): Promise<boolean> {
  const refreshToken = localStorage.getItem(AUTH_KEYS.refreshToken);
  if (!refreshToken) return Promise.resolve(false);
  if (!refreshInFlight) {
    refreshInFlight = fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refreshToken }),
    })
      .then(async (response) => {
        if (!response.ok) return false;
        persistSession((await response.json()) as AuthResponse);
        return true;
      })
      .catch(() => false)
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

// Sessão inválida (token vencido, usuário desativado...): limpa o login e volta para a tela de entrada.
function endSession(): void {
  clearSession();
  try {
    sessionStorage.setItem(SESSION_EXPIRED_FLAG, '1');
  } catch {
    // sem sessionStorage: a tela de login só não mostra o aviso
  }
  if (window.location.pathname !== '/login') {
    window.location.assign('/login');
  }
}

// Interface para resposta de erro da API
interface ApiError {
  timestamp: string;
  status: number;
  error: string;
  message: string;
  details?: { loc?: (string | number)[]; msg?: string; type?: string }[];
}

const FIELD_LABELS: Record<string, string> = {
  name: 'Nome', email: 'E-mail', password: 'Senha', newPassword: 'Nova senha', title: 'Título', topic: 'Tópico', subject: 'Matéria',
  grade: 'Nota', date: 'Data', birthDate: 'Data de nascimento', classId: 'Turma', classroomId: 'Turma', studentId: 'Aluno', year: 'Ano', code: 'Código',
  observations: 'Observações', questionsCount: 'Quantidade de questões',
};

// Transforma o erro 422 do servidor (em inglês, por campo) em uma frase que o usuário entende.
function describeValidation(details: NonNullable<ApiError['details']>): string {
  const parts = details.map((detail) => {
    const field = String(detail.loc?.[detail.loc.length - 1] ?? '');
    const label = FIELD_LABELS[field] ?? 'Campo';
    const msg = detail.msg ?? '';
    const min = msg.match(/at least (\d+) character/);
    const max = msg.match(/at most (\d+) character/);
    if (detail.type === 'missing') return `${label} é obrigatório.`;
    if (min) return `${label} deve ter pelo menos ${min[1]} caracteres.`;
    if (max) return `${label} deve ter no máximo ${max[1]} caracteres.`;
    if (msg.startsWith('Value error, ')) return `${label}: ${msg.replace('Value error, ', '')}.`;
    return `${label} está inválido.`;
  });
  return Array.from(new Set(parts)).join(' ');
}

// Interface para resposta paginada
interface PaginatedResponse<T> {
  content: T[];
  totalPages: number;
  totalElements: number;
  size: number;
  number: number;
  first: boolean;
  last: boolean;
}

class ApiClient {
  private getAuthHeaders(): HeadersInit {
    const token = localStorage.getItem('accessToken');
    return {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
    };
  }

  async request<T>(
    endpoint: string,
    options: RequestInit = {},
    retried = false,
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const isAuthRoute = endpoint.startsWith('/auth/') && endpoint !== '/auth/profile' && endpoint !== '/auth/change-password';

    // Token de acesso vencido pelo relógio: renova antes de chamar, em vez de esperar o 401.
    if (!isAuthRoute && !retried && localStorage.getItem(AUTH_KEYS.accessToken) && isAccessTokenExpired(30_000)) {
      await refreshSession();
    }

    const response = await fetch(url, {
      ...options,
      headers: {
        ...this.getAuthHeaders(),
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        timestamp: new Date().toISOString(),
        status: response.status,
        error: response.statusText,
        message: 'Erro na comunicação com o servidor'
      }));
      // 401 numa chamada autenticada: tenta renovar a sessão uma vez; sem sucesso, volta ao login.
      // O login em si (401 por senha errada) segue normal.
      if (response.status === 401 && !isAuthRoute && localStorage.getItem(AUTH_KEYS.accessToken)) {
        if (!retried && (await refreshSession())) {
          return this.request<T>(endpoint, options, true);
        }
        endSession();
        throw new Error('Sua sessão expirou. Entre novamente.');
      }
      if (response.status === 422 && Array.isArray(error.details) && error.details.length > 0) {
        throw new Error(describeValidation(error.details));
      }
      throw new Error(FRIENDLY_MESSAGES[error.message] ?? (error.message || 'Erro na API'));
    }

    // Para respostas vazias (204 No Content)
    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  // Métodos HTTP
  get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  post<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  put<T>(endpoint: string, data: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}

export const apiClient = new ApiClient();
export type { PaginatedResponse, ApiError };