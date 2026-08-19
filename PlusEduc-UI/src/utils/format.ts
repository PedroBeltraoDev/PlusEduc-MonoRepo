// Utilitários de formatação

/**
 * Formata uma data para o padrão brasileiro (DD/MM/AAAA)
 */
export function formatDate(date: string | Date | null | undefined): string {
  if (!date) return '-';
  const d = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(d.getTime())) return '-';
  return d.toLocaleDateString('pt-BR');
}

/**
 * Formata uma data com hora para o padrão brasileiro
 */
export function formatDateTime(date: string | Date | null | undefined): string {
  if (!date) return '-';
  const d = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(d.getTime())) return '-';
  return d.toLocaleString('pt-BR');
}

/**
 * Formata um número como porcentagem
 */
export function formatPercentage(value: number | null | undefined): string {
  if (value == null) return '0%';
  return `${value}%`;
}

/**
 * Formata uma nota (0-10) com uma casa decimal
 */
export function formatGrade(grade: number | null | undefined): string {
  if (grade == null) return '-';
  return grade.toFixed(1);
}

/**
 * Gera iniciais a partir do nome completo
 */
export function getInitials(name: string | null | undefined): string {
  if (!name) return 'NN';
  return name
    .split(' ')
    .filter(word => word.length > 0)
    .map(word => word.charAt(0))
    .join('')
    .toUpperCase()
    .substring(0, 2) || 'NN';
}

/**
 * Trunca um texto se for muito longo
 */
export function truncateText(text: string | null | undefined, maxLength: number = 50): string {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}