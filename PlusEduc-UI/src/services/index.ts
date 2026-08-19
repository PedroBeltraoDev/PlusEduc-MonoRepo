// Exporta todos os serviços da API

export { apiClient } from './api';
export { authService } from './auth';
export { studentsService } from './students';
export { classroomsService } from './classrooms';
export { activitiesService } from './activities';
export { studentPortalService } from './studentPortal';

export type { PaginatedResponse, ApiError } from './api';
export type { CreateStudentRequest, UpdateStudentRequest } from './students';
export type { CreateClassroomRequest, UpdateClassroomRequest } from './classrooms';
export type { CreateActivityRequest, UpdateActivityRequest, ActivityFilterParams } from './activities';