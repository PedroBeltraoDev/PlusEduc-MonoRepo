import { Bell, ClipboardCheck, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router";
import { activitiesService } from "@/services";
import type { PendingCorrection } from "@/types";

export function NotificationBell() {
  const [pending, setPending] = useState<PendingCorrection[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadPending = async () => {
    try {
      const items = await activitiesService.getPendingCorrections();
      setPending(items);
    } catch (error) {
      console.error("Erro ao carregar notificações de correção:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadPending();
    const interval = window.setInterval(() => void loadPending(), 30000);
    return () => window.clearInterval(interval);
  }, []);

  const count = pending.reduce((total, item) => total + item.questions.length, 0);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => {
          setOpen((current) => !current);
          if (!open) void loadPending();
        }}
        aria-label={count ? `${count} correções pendentes` : "Notificações"}
        aria-expanded={open}
        className="relative rounded-lg border border-gray-200 bg-white p-2.5 text-[#0A2463] shadow-sm transition hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700"
      >
        <Bell className="h-5 w-5" />
        {count > 0 ? (
          <span className="absolute -right-1.5 -top-1.5 flex min-h-5 min-w-5 items-center justify-center rounded-full bg-[#F44336] px-1 text-[10px] font-bold text-white">
            {count > 99 ? "99+" : count}
          </span>
        ) : null}
      </button>

      {open ? (
        <div className="absolute right-0 top-full z-50 mt-3 w-[min(22rem,calc(100vw-2rem))] overflow-hidden rounded-xl border border-gray-200 bg-white shadow-xl dark:border-gray-700 dark:bg-gray-800">
          <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3 dark:border-gray-700">
            <div>
              <p className="font-semibold text-[#0A2463] dark:text-white">Notificações</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Correções de questões abertas</p>
            </div>
            {count > 0 ? <span className="rounded-full bg-orange-100 px-2 py-1 text-xs font-bold text-orange-700 dark:bg-orange-950/40 dark:text-orange-300">{count}</span> : null}
          </div>

          {loading ? (
            <div className="flex items-center gap-2 px-4 py-6 text-sm text-gray-500 dark:text-gray-400">
              <Loader2 className="h-4 w-4 animate-spin" /> Carregando...
            </div>
          ) : pending.length === 0 ? (
            <div className="px-4 py-6 text-center text-sm text-gray-500 dark:text-gray-400">
              Nenhuma correção pendente.
            </div>
          ) : (
            <div className="max-h-80 overflow-y-auto">
              {pending.slice(0, 5).map((item) => (
                <Link
                  key={item.submissionId}
                  to="/atividades"
                  onClick={() => setOpen(false)}
                  className="flex gap-3 border-b border-gray-100 px-4 py-3 transition hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700/60"
                >
                  <ClipboardCheck className="mt-0.5 h-5 w-5 shrink-0 text-[#FF9800]" />
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-semibold text-gray-800 dark:text-gray-100">{item.activityTitle}</span>
                    <span className="mt-1 block text-xs text-gray-500 dark:text-gray-400">{item.studentName} • {item.questions.length} questão{item.questions.length === 1 ? "" : "ões"}</span>
                  </span>
                </Link>
              ))}
            </div>
          )}

          <div className="border-t border-gray-200 p-3 dark:border-gray-700">
            <Link
              to="/atividades"
              onClick={() => setOpen(false)}
              className="block rounded-lg bg-[#1E5AA8] px-3 py-2 text-center text-sm font-semibold text-white transition hover:bg-[#0A2463]"
            >
              Ver todas as pendências
            </Link>
          </div>
        </div>
      ) : null}
    </div>
  );
}
