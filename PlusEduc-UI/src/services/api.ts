// Cliente HTTP para consumir a API PlusEduc

import { AUTH_KEYS, SESSION_EXPIRED_FLAG } from './authKeys';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

// Mensagens padrão do backend (em inglês) traduzidas para o usuário.
const FRIENDLY_MESSAGES: Record<string, string> = {
  'Invalid email or password': 'E-mail ou senha inválidos.',
  'Access denied': 'Você não tem permissão para realizar esta ação.',
};

// Sessão inválida (token vencido, usuário desativado...): limpa o login e volta para a tela de entrada.
function endSession(): void {
  Object.values(AUTH_KEYS).forEach((key) => localStorage.removeItem(key));
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
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;

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
      // 401 numa chamada autenticada = sessão encerrada; o login em si (401 por senha errada) segue normal.
      if (response.status === 401 && !endpoint.startsWith('/auth/') && localStorage.getItem(AUTH_KEYS.accessToken)) {
        endSession();
        throw new Error('Sua sessão expirou. Entre novamente.');
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