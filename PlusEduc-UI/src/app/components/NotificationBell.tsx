import { Bell, ClipboardCheck } from "lucide-react";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { Link } from "react-router";
import { AnimatePresence, motion } from "motion/react";
import { activitiesService } from "@/services";
import type { PendingCorrection } from "@/types";
import { useMotion } from "@/motion/MotionProvider";

// ---- fonte única das pendências ---------------------------------------------------------
// O layout mostra dois sinos (celular e computador). Antes cada um fazia a própria consulta a cada
// 30 s; agora há uma só consulta compartilhada, pausada enquanto a aba está em segundo plano.
const POLL_MS = 30_000;
type Snapshot = { pending: PendingCorrection[]; loading: boolean };
let snapshot: Snapshot = { pending: [], loading: true };
const listeners = new Set<() => void>();
let timer: number | null = null;
let inFlight: Promise<void> | null = null;

function emit(next: Snapshot) {
  snapshot = next;
  listeners.forEach((listener) => listener());
}

function refresh(): Promise<void> {
  if (inFlight) return inFlight;
  inFlight = activitiesService
    .getPendingCorrections()
    .then((pending) => emit({ pending, loading: false }))
    .catch((error) => {
      console.error("Erro ao carregar notificações de correção:", error);
      emit({ ...snapshot, loading: false });
    })
    .finally(() => {
      inFlight = null;
    });
  return inFlight;
}

function onVisibility() {
  if (document.visibilityState === "visible") void refresh();
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  if (listeners.size === 1) {
    void refresh();
    timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void refresh();
    }, POLL_MS);
    document.addEventListener("visibilitychange", onVisibility);
  }
  return () => {
    listeners.delete(listener);
    if (listeners.size === 0) {
      if (timer !== null) window.clearInterval(timer);
      timer = null;
      document.removeEventListener("visibilitychange", onVisibility);
    }
  };
}

const getSnapshot = () => snapshot;

export function NotificationBell() {
  const m = useMotion();
  const { pending, loading } = useSyncExternalStore(subscribe, getSnapshot);
  const [open, setOpen] = useState(false);
  const [pulse, setPulse] = useState(0);
  const container = useRef<HTMLDivElement>(null);
  const previousCount = useRef<number | null>(null);

  const count = pending.reduce((total, item) => total + item.questions.length, 0);

  // Pulso só quando chega pendência nova (não a cada atualização).
  useEffect(() => {
    if (previousCount.current !== null && count > previousCount.current) setPulse((value) => value + 1);
    previousCount.current = count;
  }, [count]);

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: MouseEvent) => {
      if (container.current && !container.current.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="relative" ref={container}>
      <button
        type="button"
        onClick={() => {
          setOpen((current) => !current);
          if (!open) void refresh();
        }}
        aria-label={count ? `${count} correções pendentes` : "Notificações"}
        aria-expanded={open}
        aria-haspopup="true"
        className="relative rounded-lg border border-gray-200 bg-white p-2.5 text-[#0A2463] shadow-sm transition hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700"
      >
        <motion.span
          key={`bell-${pulse}`}
          className="block"
          animate={pulse && m.decorative ? { rotate: [0, -14, 11, -7, 4, 0] } : undefined}
          transition={{ duration: 0.6 }}
        >
          <Bell className="h-5 w-5" />
        </motion.span>
        <AnimatePresence>
          {count > 0 && (
            <motion.span
              key="badge"
              initial={m.reduced ? false : { scale: 0 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0 }}
              transition={m.snappy}
              className="absolute -right-1.5 -top-1.5 flex min-h-5 min-w-5 items-center justify-center rounded-full bg-[#F44336] px-1 text-[10px] font-bold text-white"
            >
              {pulse > 0 && <span key={pulse} className="pe-ping-once absolute inset-0 rounded-full bg-[#F44336]" aria-hidden="true" />}
              <span className="relative">{count > 99 ? "99+" : count}</span>
            </motion.span>
          )}
        </AnimatePresence>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            key="panel"
            role="region"
            aria-label="Notificações"
            initial={m.reduced ? { opacity: 0 } : { opacity: 0, y: -8, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98, transition: { duration: m.duration * 0.45 } }}
            transition={m.snappy}
            style={{ transformOrigin: "top right" }}
            className="absolute right-0 top-full z-50 mt-3 w-[min(22rem,calc(100vw-2rem))] overflow-hidden rounded-xl border border-gray-200 bg-white shadow-xl dark:border-gray-700 dark:bg-gray-800"
          >
            <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3 dark:border-gray-700">
              <div>
                <p className="font-semibold text-[#0A2463] dark:text-white">Notificações</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Correções de questões abertas</p>
              </div>
              {count > 0 ? <span className="rounded-full bg-orange-100 px-2 py-1 text-xs font-bold text-orange-700 dark:bg-orange-950/40 dark:text-orange-300">{count}</span> : null}
            </div>

            {/* Altura mínima fixa: trocar "carregando" por lista não faz o painel saltar. */}
            <div className="min-h-[5.5rem]" aria-live="polite">
              {loading ? (
                <div className="space-y-2 p-4" aria-busy="true">
                  <div className="pe-skeleton h-10" />
                  <div className="pe-skeleton h-10" />
                </div>
              ) : pending.length === 0 ? (
                <div className="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                  Tudo em dia: nenhuma correção pendente.
                </div>
              ) : (
                <div className="max-h-80 overflow-y-auto">
                  {pending.slice(0, 5).map((item, index) => (
                    <motion.div
                      key={item.submissionId}
                      initial={m.reduced ? false : { opacity: 0, x: 10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ ...m.snappy, delay: Math.min(index, 5) * m.stagger }}
                    >
                      <Link
                        to={`/atividades/${item.activityId}`}
                        onClick={() => setOpen(false)}
                        className="flex gap-3 border-b border-gray-100 px-4 py-3 transition hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700/60"
                      >
                        <ClipboardCheck className="mt-0.5 h-5 w-5 shrink-0 text-[#FF9800]" />
                        <span className="min-w-0">
                          <span className="block truncate text-sm font-semibold text-gray-800 dark:text-gray-100">{item.activityTitle}</span>
                          <span className="mt-1 block text-xs text-gray-500 dark:text-gray-400">{item.studentName} • {item.questions.length} {item.questions.length === 1 ? "questão" : "questões"}</span>
                        </span>
                      </Link>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>

            <div className="border-t border-gray-200 p-3 dark:border-gray-700">
              <Link
                to="/atividades"
                onClick={() => setOpen(false)}
                className="block rounded-lg bg-[#1E5AA8] px-3 py-2 text-center text-sm font-semibold text-white transition hover:bg-[#0A2463]"
              >
                Ver todas as pendências
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
