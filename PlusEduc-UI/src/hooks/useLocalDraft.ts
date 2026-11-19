import { useCallback, useEffect, useRef, useState } from 'react';

const PREFIX = 'pluseduc:draft:';
const MAX_AGE_MS = 1000 * 60 * 60 * 24 * 14; // rascunhos esquecidos somem em 14 dias

interface StoredDraft<T> {
  savedAt: number;
  value: T;
}

function read<T>(key: string | null): { value: T; savedAt: number } | null {
  if (!key) return null;
  try {
    const raw = localStorage.getItem(PREFIX + key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredDraft<T>;
    if (!parsed || typeof parsed.savedAt !== 'number' || Date.now() - parsed.savedAt > MAX_AGE_MS) {
      localStorage.removeItem(PREFIX + key);
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

/** Remove rascunhos vencidos de qualquer usuário (chamado de vez em quando, sem custo relevante). */
function pruneExpired(): void {
  try {
    for (let i = localStorage.length - 1; i >= 0; i -= 1) {
      const name = localStorage.key(i);
      if (!name?.startsWith(PREFIX)) continue;
      const parsed = JSON.parse(localStorage.getItem(name) ?? 'null') as StoredDraft<unknown> | null;
      if (!parsed || Date.now() - parsed.savedAt > MAX_AGE_MS) localStorage.removeItem(name);
    }
  } catch {
    // armazenamento indisponível
  }
}

/**
 * Rascunho local isolado por usuário e por item (ex.: `${userId}:${activityId}`). Atualizar a página
 * não perde o que foi digitado; o rascunho é apagado ao concluir o envio. ``key`` nulo desliga.
 */
export function useLocalDraft<T>(key: string | null, initial: T, delayMs = 400) {
  const [value, setValue] = useState<T>(() => read<T>(key)?.value ?? initial);
  const [savedAt, setSavedAt] = useState<number | null>(() => read<T>(key)?.savedAt ?? null);
  const restored = useRef(Boolean(read<T>(key)));
  const skipNextSave = useRef(true);

  // Troca de chave (outra atividade/usuário): carrega o rascunho correspondente.
  useEffect(() => {
    const stored = read<T>(key);
    restored.current = Boolean(stored);
    skipNextSave.current = true;
    setValue(stored?.value ?? initial);
    setSavedAt(stored?.savedAt ?? null);
    pruneExpired();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  useEffect(() => {
    if (!key) return;
    if (skipNextSave.current) {
      skipNextSave.current = false;
      return;
    }
    const timer = window.setTimeout(() => {
      try {
        const now = Date.now();
        localStorage.setItem(PREFIX + key, JSON.stringify({ savedAt: now, value } satisfies StoredDraft<T>));
        setSavedAt(now);
      } catch {
        // cota cheia ou armazenamento bloqueado: segue sem rascunho
      }
    }, delayMs);
    return () => window.clearTimeout(timer);
  }, [key, value, delayMs]);

  const clear = useCallback(() => {
    if (!key) return;
    try {
      localStorage.removeItem(PREFIX + key);
    } catch {
      // nada a fazer
    }
    setSavedAt(null);
  }, [key]);

  return { value, setValue, savedAt, restored: restored.current, clear };
}
