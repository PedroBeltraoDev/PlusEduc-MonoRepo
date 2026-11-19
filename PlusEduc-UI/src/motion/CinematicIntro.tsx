// Abertura cinematográfica do PlusEduc (1,5 a 2,5 s). A aplicação já carrega por baixo enquanto ela
// toca: o login/autenticação não espera a animação. Aparece uma vez por sessão do navegador, tem botão
// "Pular" (e Esc), respeita o movimento reduzido e nunca bloqueia o usuário em caso de erro.
import { useCallback, useEffect, useRef, useState } from 'react';
import { AnimatePresence, m as motion, type Variants } from 'motion/react';
import { LogoMark } from '@/app/components/Logo';
import { loadFeatures, useMotion } from './MotionProvider';

const SEEN_KEY = 'pluseduc:intro:seen';
export const INTRO_ALWAYS_KEY = 'pluseduc:intro:always';
const HARD_LIMIT_MS = 4000; // trava de segurança: a abertura some mesmo se algo falhar

function shouldShow(): boolean {
  // Aba aberta em segundo plano: o navegador pausa os quadros e a abertura não teria sentido.
  if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return false;
  try {
    if (localStorage.getItem(INTRO_ALWAYS_KEY) === 'true') return true;
    return sessionStorage.getItem(SEEN_KEY) !== '1';
  } catch {
    return false;
  }
}

function markSeen(): void {
  try {
    sessionStorage.setItem(SEEN_KEY, '1');
  } catch {
    // sem sessionStorage: aparece de novo na próxima carga, sem prejuízo
  }
}

const TITLE = 'PlusEduc';

export function CinematicIntro() {
  const m = useMotion();
  const [visible, setVisible] = useState(() => shouldShow() && !m.reduced);
  // Os recursos de animação chegam num pacote à parte: a abertura só começa quando estão prontos.
  // Se demorarem (rede lenta), ela é pulada para não atrasar o acesso.
  const [ready, setReady] = useState(false);
  // Remoção garantida: depois de encerrar, a abertura sai da árvore mesmo que a animação de saída
  // não termine (antes ela podia ficar presa na tela para sempre).
  const [gone, setGone] = useState(() => !visible);
  useEffect(() => {
    if (visible) return;
    const timer = window.setTimeout(() => setGone(true), 900);
    return () => window.clearTimeout(timer);
  }, [visible]);
  useEffect(() => {
    if (!visible) return;
    let alive = true;
    const giveUp = window.setTimeout(() => {
      if (alive) {
        markSeen();
        setVisible(false);
      }
    }, 1200);
    void loadFeatures().then(() => {
      window.clearTimeout(giveUp);
      if (alive) setReady(true);
    });
    return () => {
      alive = false;
      window.clearTimeout(giveUp);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible]);
  const skipRef = useRef<HTMLButtonElement>(null);
  const full = m.profile === 'ultra';
  const total = full ? 2.2 : m.profile === 'balanced' ? 1.6 : 0.9;

  const finish = useCallback(() => {
    markSeen();
    setVisible(false);
  }, []);

  useEffect(() => {
    if (!visible) {
      markSeen();
      return;
    }
    if (!ready) return;
    const timer = window.setTimeout(finish, total * 1000);
    const safety = window.setTimeout(finish, HARD_LIMIT_MS);
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') finish();
    };
    window.addEventListener('keydown', onKey);
    return () => {
      window.clearTimeout(timer);
      window.clearTimeout(safety);
      window.removeEventListener('keydown', onKey);
    };
  }, [visible, ready, total, finish]);

  // Movimento reduzido ligado depois de abrir: encerra na hora.
  useEffect(() => {
    if (m.reduced && visible) finish();
  }, [m.reduced, visible, finish]);

  const s = full ? 1 : 0.7; // escala de tempo dos perfis mais leves
  const logoVariants = {
    orbits: {
      hidden: { opacity: 0, scale: 0.6, rotate: -40 },
      show: { opacity: 1, scale: 1, rotate: 0, transition: { ...m.gentle, delay: 0.05 * s } },
    },
    outerGears: {
      hidden: { opacity: 0, rotate: 30, scale: 0.85 },
      show: { opacity: 1, rotate: 0, scale: 1, transition: { ...m.gentle, delay: 0.18 * s } },
    },
    gear: {
      hidden: { opacity: 0, scale: 0.4 },
      show: { opacity: 1, scale: 1, transition: { ...m.enter, delay: 0.12 * s } },
    },
    book: {
      hidden: { pathLength: 0, opacity: 0 },
      show: { pathLength: 1, opacity: 1, transition: { duration: 0.55 * s, ease: [0.65, 0, 0.35, 1], delay: 0.35 * s } },
    },
    pages: {
      hidden: { opacity: 0 },
      show: { opacity: 1, transition: { duration: 0.3 * s, delay: 0.75 * s } },
    },
    center: {
      hidden: { scale: 0 },
      show: { scale: 1, transition: { ...m.snappy, delay: 0.6 * s } },
    },
  } satisfies Record<string, Variants>;

  if (gone) return null;

  // Enquanto os recursos de animação carregam: só o fundo, sem nenhum componente animado.
  if (!ready) {
    return visible ? <div aria-hidden="true" className="fixed inset-0 z-[100] bg-[#0A2463]" /> : null;
  }

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="intro"
          role="dialog"
          aria-modal="true"
          aria-label="Abertura do PlusEduc"
          className="fixed inset-0 z-[100] flex items-center justify-center overflow-hidden bg-[#0A2463]"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, scale: full ? 1.04 : 1, transition: { duration: 0.45 * s, ease: [0.4, 0, 0.2, 1] } }}
          onAnimationStart={() => skipRef.current?.focus({ preventScroll: true })}
          onClick={finish}
        >
          {/* Iluminação suave (gradientes estáticos; só a opacidade anima). */}
          <motion.div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                'radial-gradient(60% 50% at 50% 42%, rgba(79,195,247,0.28), transparent 70%), radial-gradient(80% 60% at 50% 110%, rgba(30,90,168,0.55), transparent 70%)',
            }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1, transition: { duration: 0.8 * s } }}
          />

          <div className="relative flex flex-col items-center px-6 text-center">
            {/* Disco claro atrás do logo dá profundidade sem sombra pesada. */}
            <motion.div
              className="relative rounded-full bg-white/95 p-4 shadow-[0_20px_60px_-15px_rgba(79,195,247,0.55)]"
              initial={{ opacity: 0, scale: 0.7, y: full ? 16 : 0, ...(m.depthBlur ? { filter: 'blur(8px)' } : {}) }}
              animate={{ opacity: 1, scale: 1, y: 0, ...(m.depthBlur ? { filter: 'blur(0px)' } : {}) }}
              transition={m.enter}
            >
              <motion.div initial="hidden" animate="show">
                <LogoMark size={112} variants={logoVariants} />
              </motion.div>
            </motion.div>

            <h1 className="mt-6 flex overflow-hidden text-4xl font-bold tracking-tight text-white sm:text-5xl" aria-label={TITLE}>
              {TITLE.split('').map((letter, index) => (
                <motion.span
                  key={index}
                  aria-hidden="true"
                  className="inline-block"
                  initial={{ y: '110%', opacity: 0 }}
                  animate={{ y: '0%', opacity: 1 }}
                  transition={{ ...m.snappy, delay: (0.55 + index * 0.035) * s }}
                >
                  {letter}
                </motion.span>
              ))}
            </h1>

            <motion.p
              className="mt-2 text-sm font-medium text-[#4FC3F7] sm:text-base"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ ...m.gentle, delay: 0.9 * s }}
            >
              Soluções Inteligentes para a Educação
            </motion.p>

            {/* Barra de progresso fina: só transform (scaleX). */}
            <div className="mt-8 h-0.5 w-40 overflow-hidden rounded-full bg-white/15" aria-hidden="true">
              <motion.div
                className="h-full origin-left bg-gradient-to-r from-[#4FC3F7] to-white"
                initial={{ scaleX: 0 }}
                animate={{ scaleX: 1 }}
                transition={{ duration: total, ease: 'linear' }}
              />
            </div>
          </div>

          <button
            ref={skipRef}
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              finish();
            }}
            className="absolute bottom-6 right-6 rounded-full border border-white/30 px-4 py-2 text-sm font-medium text-white/85 backdrop-blur-sm hover:bg-white/10 hover:text-white"
          >
            Pular
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
