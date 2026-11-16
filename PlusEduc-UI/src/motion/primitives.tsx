// Componentes reutilizáveis do Ultra Motion. Cada um tem um comportamento próprio da sua função:
// páginas entram com profundidade, listas entram em sequência curta, números mudam com mola discreta,
// painéis expandem com mola suave. Nada aqui roda em loop contínuo.
import { useEffect, useRef, type ReactNode } from 'react';
import { AnimatePresence, animate, motion, useInView, type HTMLMotionProps } from 'motion/react';
import { useMotion } from './MotionProvider';

/** Entrada de página (troca de rota). Sem animação de saída: a navegação nunca espera a anterior. */
export function PageTransition({ routeKey, children, className }: { routeKey: string; children: ReactNode; className?: string }) {
  const m = useMotion();
  return (
    <motion.div
      key={routeKey}
      className={className}
      initial={m.reduced ? false : { opacity: 0, y: m.distance, ...(m.depthBlur ? { filter: 'blur(6px)' } : {}) }}
      animate={{ opacity: 1, y: 0, ...(m.depthBlur ? { filter: 'blur(0px)' } : {}) }}
      transition={m.enter}
      style={{ willChange: 'auto' }}
    >
      {children}
    </motion.div>
  );
}

type RevealProps = HTMLMotionProps<'div'> & { delay?: number; from?: 'below' | 'left' | 'right' | 'scale' };

/** Bloco que aparece uma vez (no primeiro render). Atualizações de dados não repetem a animação. */
export function Reveal({ delay = 0, from = 'below', children, ...rest }: RevealProps) {
  const m = useMotion();
  const offset = from === 'left' ? { x: -m.distance } : from === 'right' ? { x: m.distance } : from === 'scale' ? { scale: 0.96 } : { y: m.distance };
  return (
    <motion.div
      initial={m.reduced ? false : { opacity: 0, ...offset }}
      animate={{ opacity: 1, x: 0, y: 0, scale: 1 }}
      transition={{ ...m.enter, delay: m.reduced ? 0 : delay }}
      {...rest}
    >
      {children}
    </motion.div>
  );
}

/** Item de lista que entra em sequência curta (o atraso tem teto para listas longas). */
export function StaggerItem({ index, children, ...rest }: HTMLMotionProps<'div'> & { index: number }) {
  const m = useMotion();
  const delay = Math.min(index, m.staggerLimit) * m.stagger;
  return (
    <motion.div
      initial={m.reduced || m.profile === 'performance' ? false : { opacity: 0, y: m.distance * 0.75 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ ...m.enter, delay }}
      {...rest}
    >
      {children}
    </motion.div>
  );
}

/**
 * Número que muda com transição discreta (contagem curta). Escreve direto no texto do elemento,
 * sem re-renderizar o componente a cada quadro. A contagem inicial só acontece quando o número
 * entra na tela pela primeira vez.
 */
export function AnimatedNumber({
  value,
  decimals = 0,
  suffix = '',
  className,
  locale = 'pt-BR',
}: {
  value: number;
  decimals?: number;
  suffix?: string;
  className?: string;
  locale?: string;
}) {
  const m = useMotion();
  const ref = useRef<HTMLSpanElement>(null);
  const previous = useRef<number | null>(null);
  const inView = useInView(ref, { once: true });
  const format = (n: number) => `${n.toLocaleString(locale, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}${suffix}`;

  useEffect(() => {
    const node = ref.current;
    if (!node || !Number.isFinite(value)) return;
    const from = previous.current ?? (m.decorative && inView ? 0 : value);
    previous.current = value;
    if (m.reduced || m.profile === 'performance' || from === value || !inView) {
      node.textContent = format(value);
      return;
    }
    const controls = animate(from, value, {
      duration: m.duration * 1.6,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (latest) => {
        node.textContent = format(latest);
      },
    });
    return () => controls.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, inView, m.reduced, m.profile]);

  return (
    <span ref={ref} className={className} aria-live="off">
      {format(Number.isFinite(value) ? value : 0)}
    </span>
  );
}

/** Painel que abre/fecha com mola suave (expansão de cards, detalhes, filtros). */
export function Collapse({ open, children, className }: { open: boolean; children: ReactNode; className?: string }) {
  const m = useMotion();
  return (
    <AnimatePresence initial={false}>
      {open && (
        <motion.div
          key="collapse"
          className={className}
          initial={m.reduced ? false : { height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={m.reduced ? { opacity: 0, transition: { duration: 0 } } : { height: 0, opacity: 0 }}
          transition={m.gentle}
          style={{ overflow: 'hidden' }}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/** Troca de conteúdo (abas, modos de formulário) com fade + deslocamento lateral curto. */
export function SwapContent({ swapKey, children, direction = 1, className }: { swapKey: string; children: ReactNode; direction?: 1 | -1; className?: string }) {
  const m = useMotion();
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={swapKey}
        className={className}
        initial={m.reduced ? false : { opacity: 0, x: 18 * direction }}
        animate={{ opacity: 1, x: 0 }}
        exit={m.reduced ? { opacity: 0, transition: { duration: 0 } } : { opacity: 0, x: -14 * direction, transition: { duration: m.duration * 0.45 } }}
        transition={m.snappy}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}

/** Mensagem de feedback (erro, sucesso) que entra sem empurrar o layout de forma brusca. */
export function FeedbackMessage({ show, tone, children, messageKey }: { show: boolean; tone: 'error' | 'success' | 'info'; children: ReactNode; messageKey?: string }) {
  const m = useMotion();
  const shake = tone === 'error' && m.profile === 'ultra' && !m.reduced;
  return (
    <AnimatePresence initial={false}>
      {show && (
        <motion.div
          key={messageKey ?? tone}
          role={tone === 'error' ? 'alert' : 'status'}
          initial={m.reduced ? false : { opacity: 0, height: 0, y: -6 }}
          animate={{ opacity: 1, height: 'auto', y: 0, x: shake ? [0, -6, 5, -3, 2, 0] : 0 }}
          exit={{ opacity: 0, height: 0, transition: { duration: m.duration * 0.5 } }}
          transition={{ ...m.snappy, x: { duration: 0.4 } }}
          style={{ overflow: 'hidden' }}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
