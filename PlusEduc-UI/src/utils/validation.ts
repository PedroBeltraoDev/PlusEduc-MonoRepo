// Utilitários de validação

/**
 * Valida se um email está em formato correto
 */
export function isValidEmail(email: string | null | undefined): boolean {
  if (!email) return false;
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Valida se uma nota está no intervalo válido (0-10)
 */
export function isValidGrade(grade: number | null | undefined): boolean {
  if (grade == null) return false;
  return grade >= 0 && grade <= 10;
}

/**
 * Valida se um nome tem pelo menos 2 caracteres
 */
export function isValidName(name: string | null | undefined): boolean {
  if (!name) return false;
  return name.trim().length >= 2;
}

/**
 * Valida se uma matrícula está no formato correto (números)
 */
export function isValidMatricula(matricula: string | null | undefined): boolean {
  if (!matricula) return false;
  const matriculaRegex = /^\d{6,}$/;
  return matriculaRegex.test(matricula);
}

/**
 * Valida se uma data não é futura demais (máximo 1 ano à frente)
 */
export function isValidFutureDate(date: Date | null | undefined): boolean {
  if (!date || isNaN(date.getTime())) return false;
  const maxDate = new Date();
  maxDate.setFullYear(maxDate.getFullYear() + 1);
  return date <= maxDate;
}

/**
 * Valida se uma data não é muito antiga (mínimo 1950)
 */
export function isValidPastDate(date: Date | null | undefined): boolean {
  if (!date || isNaN(date.getTime())) return false;
  const minDate = new Date('1950-01-01');
  return date >= minDate;
}