import { apiClient } from "./api";
import type { Subject, SubjectClassroom, SubjectStudentPerformance } from "@/types";

export interface CreateSubjectRequest {
  name: string;
}

export interface SubjectPerformanceSort {
  sortBy: "name" | "grade";
  order: "asc" | "desc";
}

class SubjectsService {
  async getAll(): Promise<Subject[]> {
    return apiClient.get<Subject[]>("/subjects");
  }

  async create(data: CreateSubjectRequest): Promise<Subject> {
    return apiClient.post<Subject>("/subjects", data);
  }

  async delete(subjectId: string): Promise<void> {
    return apiClient.delete(`/subjects/${subjectId}`);
  }

  async getClassrooms(subjectId: string): Promise<SubjectClassroom[]> {
    return apiClient.get<SubjectClassroom[]>(`/subjects/${subjectId}/classrooms`);
  }

  async getPerformance(subjectId: string, classroomId: string, sort: SubjectPerformanceSort): Promise<SubjectStudentPerformance[]> {
    const params = new URLSearchParams({ sortBy: sort.sortBy, order: sort.order });
    return apiClient.get<SubjectStudentPerformance[]>(`/subjects/${subjectId}/classrooms/${classroomId}/performance?${params.toString()}`);
  }
}

export const subjectsService = new SubjectsService();
