// Cliente HTTP para consumir a API PlusEduc

import { AUTH_KEYS, SESSION_EXPIRED_FLAG } from './authKeys';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

// Mensagens padrão do backend (em inglês) traduzidas para o usuário.
const FRIENDLY_MESSAGES: Record<string, string> = {
  'Invalid email or password': 'E-mail ou senha inválidos.',
  'Access denied': 'Você não tem permissão para realizar esta ação.',
  'Authentication required': 'Sua sessão expirou. Entre novamente.',
  'Session revoked': 'Sua sessão foi encerrada. Entre novamente.',
  'Erro de validação da requisição': 'Confira os campos preenchidos e tente novamente.',
  'Erro interno do servidor': 'O servidor encontrou um erro. Tente novamente em instantes.',
};

// Renova o access token quando faltar menos que isto para ele vencer.
const REFRESH_MARGIN_MS = 60_000;

// Sessão inválida (refresh recusado, usuário desativado...): limpa o login e volta para a entrada.
function endSession(): void {
  Object.values(AUTH_KEYS).forEach((key) => localStorage.removeItem(key));
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

export class HttpError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = 'HttpError';
  }
}

interface TokenPair {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
  name?: string | null;
}

export function storeTokens(tokens: TokenPair): void {
  localStorage.setItem(AUTH_KEYS.accessToken, tokens.accessToken);
  localStorage.setItem(AUTH_KEYS.refreshToken, tokens.refreshToken);
  localStorage.setItem(AUTH_KEYS.tokenType, tokens.tokenType);
  localStorage.setItem(AUTH_KEYS.expiresIn, String(tokens.expiresIn));
  localStorage.setItem(AUTH_KEYS.loginTime, Date.now().toString());
}

function accessExpiresAt(): number {
  const expiresIn = Number(localStorage.getItem(AUTH_KEYS.expiresIn));
  const loginTime = Number(localStorage.getItem(AUTH_KEYS.loginTime));
  if (!expiresIn || !loginTime) return 0;
  return loginTime + expiresIn * 1000;
}

// Uma única renovação em andamento por vez: requisições simultâneas aguardam a mesma promessa
// (o refresh token é rotativo; duas renovações paralelas derrubariam a sessão por "reuso").
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
      storeTokens((await response.json()) as TokenPair);
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

class ApiClient {
  private getAuthHeaders(): HeadersInit {
    const token = localStorage.getItem('accessToken');
    return {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
    };
  }

  private async ensureFreshToken(endpoint: string): Promise<void> {
    if (endpoint.startsWith('/auth/') || !localStorage.getItem(AUTH_KEYS.accessToken)) return;
    const expiresAt = accessExpiresAt();
    if (expiresAt && expiresAt - Date.now() < REFRESH_MARGIN_MS) {
      await refreshSession();
    }
  }

  async request<T>(
    endpoint: string,
    options: RequestInit = {},
    retried = false,
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    await this.ensureFreshToken(endpoint);

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
      if (response.status === 401 && !endpoint.startsWith('/auth/') && localStorage.getItem(AUTH_KEYS.accessToken)) {
        if (!retried && (await refreshSession())) {
          return this.request<T>(endpoint, options, true);
        }
        endSession();
        throw new HttpError('Sua sessão expirou. Entre novamente.', 401);
      }
      if (response.status === 429) {
        throw new HttpError(error.message || 'Muitas tentativas. Aguarde alguns minutos.', 429);
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
