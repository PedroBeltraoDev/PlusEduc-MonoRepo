// Cliente HTTP para consumir a API PlusEduc

import type { AuthResponse } from '@/types';
import { AUTH_KEYS, SESSION_EXPIRED_FLAG } from './authKeys';
import { clearSession, isAccessTokenExpired, persistSession } from './session';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

// Mensagens do servidor (em inglês ou genéricas) traduzidas para o usuário.
const FRIENDLY_MESSAGES: Record<string, string> = {
  'Invalid email or password': 'E-mail ou senha inválidos.',
  'Access denied': 'Você não tem permissão para realizar esta ação.',
  'Email already in use': 'Este e-mail já está em uso por outra conta.',
  'Authentication required': 'Sua sessão expirou. Entre novamente.',
  'Session revoked': 'Sua sessão foi encerrada. Entre novamente.',
  'Erro de validação da requisição': 'Confira os campos preenchidos e tente novamente.',
  'Erro interno do servidor': 'O servidor encontrou um erro. Tente novamente em instantes.',
};

// Renova o token de acesso quando faltar menos que isto para ele vencer.
const REFRESH_MARGIN_MS = 30_000;

// Rotas de /auth que não usam a sessão (login, cadastro, renovação, saída, recuperação de senha).
function isPublicAuthRoute(endpoint: string): boolean {
  return endpoint.startsWith('/auth/') && endpoint !== '/auth/profile' && endpoint !== '/auth/change-password';
}

// Renovação da sessão com o refresh token (RF01). Uma única renovação por vez, mesmo que várias
// requisições recebam 401 ao mesmo tempo: o refresh token vale uma vez só, e duas renovações
// paralelas com o mesmo token fariam o servidor encerrar a sessão por "reuso".
let refreshInFlight: Promise<boolean> | null = null;

export function refreshSession(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;
  const refreshToken = localStorage.getItem(AUTH_KEYS.refreshToken);
  if (!refreshToken) return Promise.resolve(false);

  refreshInFlight = (async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refreshToken }),
      });
      if (!response.ok) return false;
      persistSession((await response.json()) as AuthResponse);
      return true;
    } catch {
      return false;
    } finally {
      // libera depois que todos os que esperavam já receberam o resultado
      setTimeout(() => {
        refreshInFlight = null;
      }, 0);
    }
  })();
  return refreshInFlight;
}

// Sessão inválida (refresh recusado, usuário desativado...): limpa o login e volta para a entrada.
function endSession(): void {
  clearSession();
  try {
    sessionStorage.setItem(SESSION_EXPIRED_FLAG, '1');
  } catch {
    // sem sessionStorage: a tela de login só não mostra o aviso
  }
  window.dispatchEvent(new Event('pluseduc:session-ended'));
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

// Erro de uma chamada à API, com o status HTTP (ex.: 403 para tratar "sem permissão" na tela).
export class HttpError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = 'HttpError';
  }
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
    const token = localStorage.getItem(AUTH_KEYS.accessToken);
    return {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
    };
  }

  // Token de acesso vencido (ou quase) pelo relógio: renova antes de chamar, em vez de esperar o 401.
  private async ensureFreshToken(endpoint: string): Promise<void> {
    if (isPublicAuthRoute(endpoint) || !localStorage.getItem(AUTH_KEYS.accessToken)) return;
    if (isAccessTokenExpired(REFRESH_MARGIN_MS)) {
      await refreshSession();
    }
  }

  async request<T>(
    endpoint: string,
    options: RequestInit = {},
    retried = false,
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    if (!retried) {
      await this.ensureFreshToken(endpoint);
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
      // 401 numa chamada autenticada: tenta renovar a sessão uma vez e repete a requisição, sem
      // perder o que o usuário estava fazendo. O login em si (401 por senha errada) segue normal.
      if (response.status === 401 && !isPublicAuthRoute(endpoint) && localStorage.getItem(AUTH_KEYS.accessToken)) {
        if (!retried && (await refreshSession())) {
          return this.request<T>(endpoint, options, true);
        }
        endSession();
        throw new HttpError('Sua sessão expirou. Entre novamente.', 401);
      }
      if (response.status === 429) {
        throw new HttpError(error.message || 'Muitas tentativas. Aguarde alguns minutos.', 429);
      }
      if (response.status === 422 && Array.isArray(error.details) && error.details.length > 0) {
        throw new HttpError(describeValidation(error.details), 422);
      }
      throw new HttpError(FRIENDLY_MESSAGES[error.message] ?? (error.message || 'Erro na API'), response.status);
    }

    // Para respostas vazias (204 No Content)
    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  /** Download autenticado (PDF, CSV...) com a mesma renovação de sessão das demais chamadas. */
  async download(endpoint: string): Promise<Response> {
    await this.ensureFreshToken(endpoint);
    const send = () => fetch(`${API_BASE_URL}${endpoint}`, { headers: this.getAuthHeaders() });
    let response = await send();
    if (response.status === 401 && (await refreshSession())) {
      response = await send();
    }
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new HttpError(body?.message ?? 'Não foi possível baixar o arquivo.', response.status);
    }
    return response;
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
