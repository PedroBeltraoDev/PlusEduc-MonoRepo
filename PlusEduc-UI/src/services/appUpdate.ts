// Atualização do aplicativo de desktop (PlusEduc.exe): consulta o backend local, que verifica as releases do GitHub

import { apiClient } from './api';

export type UpdateCheckStatus =
  | 'disabled'
  | 'pending'
  | 'up_to_date'
  | 'available'
  | 'no_release'
  | 'offline'
  | 'rate_limited'
  | 'error';

export interface AppUpdateStatus {
  currentVersion: string;
  status: UpdateCheckStatus;
  message: string;
  updateAvailable: boolean;
  latestVersion: string | null;
  releaseUrl: string | null;
  releaseNotes: string | null;
  installerSize: number | null;
  canInstall: boolean;
  checkedAt: string | null;
  download: {
    state: 'idle' | 'downloading' | 'launching' | 'error';
    progress: number;
    error: string | null;
  };
}

class AppUpdateService {
  getStatus(): Promise<AppUpdateStatus> {
    return apiClient.get<AppUpdateStatus>('/app/update');
  }

  check(): Promise<AppUpdateStatus> {
    return apiClient.post<AppUpdateStatus>('/app/update/check');
  }

  // O cabeçalho próprio impede que outro site acione a instalação no endereço local (exige checagem CORS)
  install(): Promise<AppUpdateStatus> {
    return apiClient.request<AppUpdateStatus>('/app/update/install', {
      method: 'POST',
      headers: { 'X-PlusEduc-Update': '1' },
    });
  }
}

export const appUpdateService = new AppUpdateService();
