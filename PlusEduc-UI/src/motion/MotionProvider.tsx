import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { MotionConfig } from 'motion/react';
import { PROFILE_TOKENS, downgrade, suggestedProfile, type MotionProfile, type MotionTokens } from './profiles';

const STORAGE_KEY = 'pluseduc:motion';

interface StoredPreferences {
  profile: MotionProfile;
  /** Permite ao sistema reduzir os efeitos sozinho (aparelho modesto ou travadas detectadas). */
  autoAdjust: boolean;
  /** Desliga movimentos não essenciais, mesmo sem a preferência do sistema operacional. */
  reduceMotion: boolean;
}

interface MotionContextValue extends MotionTokens {
  /** Perfil escolhido pelo usuário (o efetivo pode ser menor por ajuste automático). */
  chosen: MotionProfile;
  autoAdjust: boolean;
  /** Movimento reduzido ativo (preferência do sistema ou do usuário). */
  reduced: boolean;
  /** Preferência "reduzir movimento" do sistema operacional. */
  systemReduced: boolean;
  userReduced: boolean;
  setProfile: (profile: MotionProfile) => void;
  setAutoAdjust: (value: boolean) => void;
  setUserReduced: (value: boolean) => void;
}

const DEFAULTS: StoredPreferences = { profile: 'ultra', autoAdjust: true, reduceMotion: false };

function readPreferences(): StoredPreferences {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULTS;
    const parsed = JSON.parse(raw) as Partial<StoredPreferences>;
    const profile = parsed.profile && parsed.profile in PROFILE_TOKENS ? parsed.profile : DEFAULTS.profile;
    return {
      profile,
      autoAdjust: parsed.autoAdjust ?? DEFAULTS.autoAdjust,
      reduceMotion: parsed.reduceMotion ?? DEFAULTS.reduceMotion,
    };
  } catch {
    return DEFAULTS;
  }
}

function writePreferences(value: StoredPreferences): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  } catch {
    // armazenamento bloqueado: a preferência vale só nesta página
  }
}

const RANK: Record<MotionProfile, number> = { performance: 0, balanced: 1, ultra: 2 };
const lowest = (...profiles: MotionProfile[]) => profiles.reduce((a, b) => (RANK[a] <= RANK[b] ? a : b));

function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => typeof window !== 'undefined' && window.matchMedia(query).matches);
  useEffect(() => {
    const media = window.matchMedia(query);
    const update = () => setMatches(media.matches);
    update();
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, [query]);
  return matches;
}

/**
 * Observa travadas longas da thread principal (sem loop de requestAnimationFrame: é um observador
 * passivo do próprio navegador). Muitas travadas seguidas = rebaixa um nível durante a sessão.
 */
function useJankGuard(enabled: boolean): number {
  const [downgrades, setDowngrades] = useState(0);
  useEffect(() => {
    if (!enabled || typeof PerformanceObserver === 'undefined') return;
    const supported = PerformanceObserver.supportedEntryTypes ?? [];
    const type = supported.includes('long-animation-frame') ? 'long-animation-frame' : supported.includes('longtask') ? 'longtask' : null;
    if (!type) return;
    let recent: number[] = [];
    const observer = new PerformanceObserver((list) => {
      const now = performance.now();
      for (const entry of list.getEntries()) {
        if (entry.duration >= 120) recent.push(entry.startTime);
      }
      recent = recent.filter((time) => now - time < 15_000);
      if (recent.length >= 8) {
        recent = [];
        setDowngrades((count) => Math.min(count + 1, 2));
      }
    });
    try {
      observer.observe({ type, buffered: false });
    } catch {
      return;
    }
    return () => observer.disconnect();
  }, [enabled]);
  return downgrades;
}

const MotionContext = createContext<MotionContextValue | null>(null);

export function MotionProvider({ children }: { children: ReactNode }) {
  const [prefs, setPrefs] = useState<StoredPreferences>(readPreferences);
  const systemReduced = useMediaQuery('(prefers-reduced-motion: reduce)');
  const smallScreen = useMediaQuery('(max-width: 640px)');
  const jankDowngrades = useJankGuard(prefs.autoAdjust && prefs.profile !== 'performance');

  // Mantém as abas/portais sincronizados (professor e aluno usam a mesma preferência local).
  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY) setPrefs(readPreferences());
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  const update = useCallback((patch: Partial<StoredPreferences>) => {
    setPrefs((current) => {
      const next = { ...current, ...patch };
      writePreferences(next);
      return next;
    });
  }, []);

  const effective = useMemo<MotionProfile>(() => {
    if (!prefs.autoAdjust) return prefs.profile;
    let profile = lowest(prefs.profile, suggestedProfile());
    for (let i = 0; i < jankDowngrades; i += 1) profile = downgrade(profile);
    return profile;
  }, [prefs.autoAdjust, prefs.profile, jankDowngrades]);

  const reduced = systemReduced || prefs.reduceMotion;

  const value = useMemo<MotionContextValue>(() => {
    const base = PROFILE_TOKENS[reduced ? 'performance' : effective];
    return {
      ...base,
      // Desfoque de profundidade custa mais em celulares: só em telas maiores.
      depthBlur: base.depthBlur && !smallScreen,
      chosen: prefs.profile,
      autoAdjust: prefs.autoAdjust,
      reduced,
      systemReduced,
      userReduced: prefs.reduceMotion,
      setProfile: (profile) => update({ profile }),
      setAutoAdjust: (autoAdjust) => update({ autoAdjust }),
      setUserReduced: (reduceMotion) => update({ reduceMotion }),
    };
  }, [effective, reduced, smallScreen, prefs, systemReduced, update]);

  // O CSS global (modais, menus, botões) lê estes atributos.
  useEffect(() => {
    const root = document.documentElement;
    root.dataset.motion = value.profile;
    root.dataset.reduceMotion = reduced ? 'true' : 'false';
  }, [value.profile, reduced]);

  return (
    <MotionContext.Provider value={value}>
      {/* reducedMotion "always": a biblioteca troca deslocamentos por mudanças instantâneas. */}
      <MotionConfig reducedMotion={reduced ? 'always' : 'never'} transition={value.enter}>
        {children}
      </MotionConfig>
    </MotionContext.Provider>
  );
}

export function useMotion(): MotionContextValue {
  const context = useContext(MotionContext);
  if (!context) {
    // Fora do provider (testes isolados): comportamento do perfil Desempenho, sem quebrar a tela.
    return {
      ...PROFILE_TOKENS.performance,
      chosen: 'performance',
      autoAdjust: false,
      reduced: true,
      systemReduced: false,
      userReduced: false,
      setProfile: () => undefined,
      setAutoAdjust: () => undefined,
      setUserReduced: () => undefined,
    };
  }
  return context;
}
