// Constantes do projeto

// Cores do tema
export const COLORS = {
  primary: '#0A2463',
  secondary: '#1E5AA8',
  light: '#4FC3F7',
  orange: '#FF9800',
  green: '#4CAF50',
  background: '#F5F7FA',
} as const;

// Status das atividades
export const ACTIVITY_STATUS = {
  COMPLETED: 'Concluída',
  IN_PROGRESS: 'Em andamento',
  PENDING: 'Pendente',
  LATE: 'Atrasada',
} as const;

// Status das turmas
export const CLASS_STATUS = {
  ACTIVE: 'Ativa',
  PAUSED: 'Pausada',
  INACTIVE: 'Inativa',
} as const;

// Status dos alunos
export const STUDENT_STATUS = {
  ACTIVE: 'Ativo',
  INACTIVE: 'Inativo',
  TRANSFERRED: 'Transferido',
} as const;

// Períodos
export const PERIODS = {
  MORNING: 'Manhã',
  AFTERNOON: 'Tarde',
  EVENING: 'Noite',
} as const;

// Tipos de atividade
export const ACTIVITY_TYPES = {
  EXAM: 'Prova',
  ASSIGNMENT: 'Trabalho',
  EXERCISE: 'Exercício',
  PROJECT: 'Projeto',
} as const;

// Limites de dados
export const LIMITS = {
  MAX_STUDENTS_PER_CLASS: 40,
  MAX_GRADE: 10,
  MIN_GRADE: 0,
  MAX_NAME_LENGTH: 100,
  MAX_DESCRIPTION_LENGTH: 500,
} as const;

// Mensagens comuns
export const MESSAGES = {
  REQUIRED_FIELD: 'Este campo é obrigatório',
  INVALID_EMAIL: 'Email inválido',
  INVALID_GRADE: 'Nota deve estar entre 0 e 10',
  SAVE_SUCCESS: 'Salvo com sucesso!',
  SAVE_ERROR: 'Erro ao salvar. Tente novamente.',
  DELETE_CONFIRM: 'Tem certeza que deseja excluir?',
  NO_DATA: 'Nenhum dado encontrado',
} as const;