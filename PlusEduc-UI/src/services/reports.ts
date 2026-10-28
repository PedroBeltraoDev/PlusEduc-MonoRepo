// Serviços da Sprint 7: dashboard, relatórios, exportação, pesquisa e histórico de operações

import { apiClient } from './api';

export interface ReportFilters {
  classroomId?: string;
  subject?: string;
  from?: string;
  to?: string;
  status?: string;
  entity?: string;
  action?: string;
}

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  actorEmail?: string | null;
  actorName?: string | null;
  actorRole?: string | null;
  action: string;
  actionLabel: string;
  entity: string;
  entityLabel: string;
  entityId?: string | null;
  method: string;
  path: string;
  status: number;
  success: boolean;
  summary: string;
  details: Record<string, unknown>;
}

export interface AuditLogPage {
  items: AuditLogEntry[];
  total: number;
  page: number;
  size: number;
  totalPages: number;
}

export interface AuditFilters extends ReportFilters {
  success?: string;
  q?: string;
  actor?: string;
}

export interface DashboardOverview {
  generatedAt: string;
  filters: Record<string, string>;
  kpis: {
    students: number;
    classrooms: number;
    activities: number;
    gradeLaunches: number;
    averageGrade: number | null;
    attendanceRate: number | null;
    submissionRate: number | null;
    studentsAtRisk: number;
  };
  averageByClassroom: { id?: string | null; name: string; average: number; attendanceRate?: number | null; launches: number }[];
  averageBySubject: { name: string; average: number; attendanceRate?: number | null; launches: number }[];
  monthlyAverage: { month: string; average: number; launches: number }[];
  distribution: { range: string; count: number }[];
  participation: { delivered: number; pending: number };
  atRisk: { studentId: string; studentName: string; classroomName: string; average: number | null; attendanceRate: number | null; reasons: string[] }[];
  recentOperations: AuditLogEntry[];
}

export interface ReportColumn {
  key: string;
  label: string;
  type: 'text' | 'number' | 'decimal' | 'percent' | 'date' | 'datetime';
}

export interface ReportResult {
  type: string;
  title: string;
  description: string;
  generatedAt: string;
  filters: Record<string, string>;
  columns: ReportColumn[];
  rows: Record<string, string | number | null>[];
  summary: { label: string; value: string }[];
  total: number;
}

export interface ReportCatalogItem {
  type: string;
  title: string;
  description: string;
  statusOptions: { value: string; label: string }[];
}

export interface SearchHit {
  type: 'students' | 'classrooms' | 'activities';
  id: string;
  title: string;
  subtitle?: string | null;
  url: string;
}

export interface SearchResult {
  query: string;
  total: number;
  results: SearchHit[];
}

export type ExportFormat = 'csv' | 'xlsx' | 'pdf';

function queryString(params: Record<string, string | number | undefined>): string {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') query.set(key, String(value));
  });
  const text = query.toString();
  return text ? `?${text}` : '';
}

class ReportsService {
  getDashboard(filters: ReportFilters): Promise<DashboardOverview> {
    return apiClient.get<DashboardOverview>(`/dashboard/overview${queryString({ ...filters })}`);
  }

  getCatalog(): Promise<ReportCatalogItem[]> {
    return apiClient.get<ReportCatalogItem[]>('/reports');
  }

  runReport(type: string, filters: ReportFilters): Promise<ReportResult> {
    return apiClient.get<ReportResult>(`/reports/${type}${queryString({ ...filters })}`);
  }

  // Baixa o relatório no formato escolhido (o navegador recebe o arquivo gerado pelo backend).
  async exportReport(type: string, format: ExportFormat, filters: ReportFilters): Promise<string> {
    const response = await fetch(`/api/reports/${type}/export${queryString({ ...filters, format })}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('accessToken')}` },
    });
    if (!response.ok) {
      const error = await response.json().catch(() => null);
      throw new Error(error?.message || 'Não foi possível exportar o relatório.');
    }
    const blob = await response.blob();
    const disposition = response.headers.get('Content-Disposition') ?? '';
    const filename = /filename="?([^";]+)"?/.exec(disposition)?.[1] ?? `relatorio.${format}`;
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    return filename;
  }

  search(q: string, types?: string, limit = 20): Promise<SearchResult> {
    return apiClient.get<SearchResult>(`/search${queryString({ q, types, limit })}`);
  }

  getAuditLogs(filters: AuditFilters, page: number, size: number): Promise<AuditLogPage> {
    return apiClient.get<AuditLogPage>(`/audit-logs${queryString({ ...filters, page, size })}`);
  }
}

export const reportsService = new ReportsService();
