import { apiClient } from "./api";
import type { SubjectTopic } from "@/types";

export interface CreateSubjectTopicRequest {
  subject: string;
  topic?: string;
}

export interface UpdateSubjectTopicRequest {
  subject: string;
  topics: string[];
}

class SubjectTopicsService {
  async getAll(): Promise<SubjectTopic[]> {
    return apiClient.get<SubjectTopic[]>("/subject-topics");
  }

  async create(data: CreateSubjectTopicRequest): Promise<SubjectTopic> {
    return apiClient.post<SubjectTopic>("/subject-topics", data);
  }

  async update(id: string, data: UpdateSubjectTopicRequest): Promise<SubjectTopic> {
    return apiClient.put<SubjectTopic>(`/subject-topics/${id}`, data);
  }

  async delete(id: string): Promise<void> {
    return apiClient.delete(`/subject-topics/${id}`);
  }
}

export const subjectTopicsService = new SubjectTopicsService();
