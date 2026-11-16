// Perfis do PlusEduc Ultra Motion: cada perfil define a "física" e o quanto de efeito decorativo é usado.
// Tudo é animado com transform/opacity (camada de composição da GPU), sem limite artificial de FPS:
// o navegador desenha no ritmo do monitor (60, 120, 144, 240 Hz...).

export type MotionProfile = 'ultra' | 'balanced' | 'performance';

export interface SpringConfig {
  type: 'spring';
  stiffness: number;
  damping: number;
  mass: number;
}

export interface MotionTokens {
  profile: MotionProfile;
  /** Mola das entradas de página e blocos grandes. */
  enter: SpringConfig;
  /** Mola curta para microinterações (botões, indicadores, chips). */
  snappy: SpringConfig;
  /** Mola suave para expansão de cards e painéis. */
  gentle: SpringConfig;
  /** Deslocamento (px) das entradas. */
  distance: number;
  /** Intervalo entre itens de listas que entram em sequência (s). */
  stagger: number;
  /** Máximo de itens animados em sequência (o resto aparece junto, sem atraso acumulado). */
  staggerLimit: number;
  /** Duração-base (s) para animações por tempo (fade, contadores). */
  duration: number;
  /** Desfoque de profundidade nas entradas (só no Ultra; desligado em telas pequenas). */
  depthBlur: boolean;
  /** Microinterações de hover/press em cartões e botões. */
  hover: boolean;
  /** Elementos decorativos (brilhos, órbitas). */
  decorative: boolean;
}

const spring = (stiffness: number, damping: number, mass = 1): SpringConfig => ({ type: 'spring', stiffness, damping, mass });

export const PROFILE_TOKENS: Record<MotionProfile, MotionTokens> = {
  ultra: {
    profile: 'ultra',
    enter: spring(260, 26, 0.9),
    snappy: spring(520, 32, 0.7),
    gentle: spring(180, 24, 1),
    distance: 14,
    stagger: 0.045,
    staggerLimit: 12,
    duration: 0.42,
    depthBlur: true,
    hover: true,
    decorative: true,
  },
  balanced: {
    profile: 'balanced',
    enter: spring(340, 32, 0.8),
    snappy: spring(600, 38, 0.7),
    gentle: spring(260, 30, 0.9),
    distance: 8,
    stagger: 0.03,
    staggerLimit: 8,
    duration: 0.3,
    depthBlur: false,
    hover: true,
    decorative: false,
  },
  performance: {
    profile: 'performance',
    enter: spring(700, 50, 0.6),
    snappy: spring(800, 55, 0.6),
    gentle: spring(600, 50, 0.6),
    distance: 0,
    stagger: 0,
    staggerLimit: 0,
    duration: 0.16,
    depthBlur: false,
    hover: false,
    decorative: false,
  },
};

export const PROFILE_LABELS: Record<MotionProfile, { title: string; description: string }> = {
  ultra: {
    title: 'Ultra',
    description: 'Animações completas, molas expressivas e microinterações refinadas.',
  },
  balanced: {
    title: 'Equilibrado',
    description: 'Fluidez preservada com menos efeitos decorativos e menor custo.',
  },
  performance: {
    title: 'Desempenho',
    description: 'Transições curtas e mínimas, ideal para computadores mais simples.',
  },
};

/**
 * Sugestão inicial conforme o aparelho (só quando o usuário ainda não escolheu um perfil).
 * Usa apenas sinais que o navegador já expõe; não roda nenhum teste de desempenho.
 */
export function suggestedProfile(): MotionProfile {
  if (typeof navigator === 'undefined') return 'ultra';
  const nav = navigator as Navigator & { deviceMemory?: number; connection?: { saveData?: boolean } };
  const cores = nav.hardwareConcurrency ?? 8;
  const memory = nav.deviceMemory ?? 8;
  if (nav.connection?.saveData || cores <= 2 || memory <= 2) return 'performance';
  if (cores <= 4 || memory <= 4) return 'balanced';
  return 'ultra';
}

export function downgrade(profile: MotionProfile): MotionProfile {
  return profile === 'ultra' ? 'balanced' : 'performance';
}
