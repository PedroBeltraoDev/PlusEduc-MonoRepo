// Utilitários de formatação

/**
 * Formata uma data para o padrão brasileiro (DD/MM/AAAA)
 */
export function formatDate(date: string | Date | null | undefined): string {
  if (!date) return '-';
  const d = typeof date === 'string' ? parseDateValue(date) : date;
  if (isNaN(d.getTime())) return '-';
  return d.toLocaleDateString('pt-BR');
}

/**
 * Converte o texto de uma data. Data sem hora ("2012-08-14", como a data de nascimento) é tratada como data local:
 * `new Date("2012-08-14")` seria meia-noite UTC, que no Brasil (UTC-3) ainda é o dia anterior.
 */
export function parseDateValue(value: string): Date {
  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value.trim());
  if (dateOnly) {
    return new Date(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3]));
  }
  return new Date(value);
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