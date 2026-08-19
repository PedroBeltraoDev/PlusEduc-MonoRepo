// Serviço de gerenciamento de atividades

import { apiClient } from './api';
import type { Activity, GenerateActivityRequest, GeneratedQuestion, PaginatedResponse } from '@/types';

export interface CreateActivityRequest {
  title: string;
  subject: string;
  topic: string;
  difficultyLevel: string;
  questionsCount: number;
  format: string;
  content?: string;
  classroomId: string;
  studentId?: string;
  disabilityAdaptations?: string[];
  questions?: GeneratedQuestion[];
  pdfUrl?: string;
}

export interface UpdateActivityRequest extends Partial<CreateActivityRequest> {}

export interface ActivityFilterParams {
  subject?: string;
  difficultyLevel?: string;
  format?: string;
  generatedByAi?: boolean;
  classroomId?: string;
  studentId?: string;
  page?: number;
  size?: number;
}

class ActivitiesService {
  // Criar atividade
  async createActivity(data: CreateActivityRequest): Promise<Activity> {
    return apiClient.post<Activity>('/activities', data);
  }

  // Listar todas as atividades
  async getAllActivities(): Promise<Activity[]> {
    return apiClient.get<Activity[]>('/activities');
  }

  // Listar atividades com paginação
  async getActivitiesPaginated(
    page: number = 0,
    size: number = 10,
    sort?: string
  ): Promise<PaginatedResponse<Activity>> {
    const params = new URLSearchParams({
      page: page.toString(),
      size: size.toString(),
      ...(sort && { sort })
    });

    return apiClient.get<PaginatedResponse<Activity>>(`/activities/paginated?${params}`);
  }

  // Buscar atividade por ID
  async getActivityById(id: string): Promise<Activity> {
    return apiClient.get<Activity>(`/activities/${id}`);
  }

  // Buscar atividades por turma
  async getActivitiesByClassroom(classroomId: string): Promise<Activity[]> {
    return apiClient.get<Activity[]>(`/activities/classroom/${classroomId}`);
  }

  // Buscar atividades por aluno
  async getActivitiesByStudent(studentId: string): Promise<Activity[]> {
    return apiClient.get<Activity[]>(`/activities/student/${studentId}`);
  }

  // Filtrar atividades
  async filterActivities(filters: ActivityFilterParams): Promise<Activity[]> {
    const params = new URLSearchParams();

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== '') {
        params.append(key, value.toString());
      }
    });

    return apiClient.get<Activity[]>(`/activities/filter?${params}`);
  }

  // Gerar atividade com IA
  async generateActivity(data: GenerateActivityRequest): Promise<Activity> {
    return apiClient.post<Activity>('/activities/generate', data);
  }

  // Atualizar atividade
  async updateActivity(id: string, data: UpdateActivityRequest): Promise<Activity> {
    return apiClient.put<Activity>(`/activities/${id}`, data);
  }

  // Deletar atividade
  async deleteActivity(id: string): Promise<void> {
    return apiClient.delete(`/activities/${id}`);
  }

  // Exportar atividade em PDF
  async exportActivityToPDF(id: string, includeAnswers: boolean = false): Promise<Blob> {
    const response = await fetch(`/api/activities/${id}/export-pdf?includeAnswers=${includeAnswers}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Erro ao exportar atividade para PDF');
    }

    return response.blob();
  }

  // Fazer download do PDF
  async downloadActivityPDF(id: string, includeAnswers: boolean = false): Promise<void> {
    try {
      const blob = await this.exportActivityToPDF(id, includeAnswers);
      const activity = await this.getActivityById(id);

      // Criar link temporário para download
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${activity.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.pdf`;
      document.body.appendChild(link);
      link.click();

      // Limpar recursos
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Erro ao fazer download do PDF:', error);
      throw error;
    }
  }

  // Buscar atividades (com filtros de texto)
  async searchActivities(query: string): Promise<Activity[]> {
    const allActivities = await this.getAllActivities();
    return allActivities.filter(activity =>
      activity.title.toLowerCase().includes(query.toLowerCase()) ||
      activity.subject.toLowerCase().includes(query.toLowerCase()) ||
      activity.topic.toLowerCase().includes(query.toLowerCase())
    );
  }

  // Obter estatísticas das atividades
  async getActivitiesStats() {
    const activities = await this.getAllActivities();

    // Estatísticas por dificuldade
    const difficultyStats = activities.reduce((acc, activity) => {
      acc[activity.difficultyLevel] = (acc[activity.difficultyLevel] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    // Estatísticas por formato
    const formatStats = activities.reduce((acc, activity) => {
      acc[activity.format] = (acc[activity.format] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    // Estatísticas por disciplina
    const subjectStats = activities.reduce((acc, activity) => {
      acc[activity.subject] = (acc[activity.subject] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    // Atividades geradas por IA
    const aiGenerated = activities.filter(a => a.generatedByAi).length;
    const manualCreated = activities.length - aiGenerated;

    // Atividades por mês (últimos 6 meses)
    const sixMonthsAgo = new Date();
    sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);

    const activitiesByMonth = activities
      .filter(a => new Date(a.createdAt) >= sixMonthsAgo)
      .reduce((acc, activity) => {
        const month = new Date(activity.createdAt).toLocaleString('pt-BR', { month: 'long', year: 'numeric' });
        acc[month] = (acc[month] || 0) + 1;
        return acc;
      }, {} as Record<string, number>);

    return {
      total: activities.length,
      aiGenerated,
      manualCreated,
      difficultyStats,
      formatStats,
      subjectStats,
      activitiesByMonth
    };
  }

  // Obter atividades recentes
  async getRecentActivities(limit: number = 5): Promise<Activity[]> {
    const activities = await this.getAllActivities();
    return activities
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      .slice(0, limit);
  }
}

export const activitiesService = new ActivitiesService();
