import { useCallback } from 'react';
import { useTheme } from 'next-themes';
import { useMotion } from './MotionProvider';

/** Troca claro/escuro com transição de cor curta nas superfícies (desligada no movimento reduzido). */
export function useSmoothTheme() {
  const { theme, setTheme } = useTheme();
  const m = useMotion();
  const switchTheme = useCallback(
    (next: 'light' | 'dark') => {
      if (next === theme) return;
      const root = document.documentElement;
      if (!m.reduced && m.profile !== 'performance') {
        root.classList.add('pe-theme-transition');
        window.setTimeout(() => root.classList.remove('pe-theme-transition'), 320);
      }
      setTheme(next);
    },
    [theme, setTheme, m.reduced, m.profile],
  );
  return { theme, switchTheme };
}
