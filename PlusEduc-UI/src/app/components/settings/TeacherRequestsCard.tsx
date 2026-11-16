import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Check, Loader2, UserPlus, X } from "lucide-react";
import { toast } from "sonner";
import { adminService } from "@/services";
import type { TeacherRequest } from "@/types";
import { useMotion } from "@/motion/MotionProvider";
import { formatDate } from "@/utils/format";

/** Pedidos de cadastro de professor aguardando aprovação (somente ADMIN). */
export function TeacherRequestsCard() {
  const m = useMotion();
  const [items, setItems] = useState<TeacherRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setItems(await adminService.listTeacherRequests());
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Não foi possível carregar os pedidos.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const decide = async (item: TeacherRequest, approve: boolean) => {
    try {
      setBusy(item.userId);
      await (approve ? adminService.approveTeacher(item.userId) : adminService.rejectTeacher(item.userId));
      setItems((current) => current.filter((entry) => entry.userId !== item.userId));
      toast.success(approve ? `Acesso de ${item.name ?? item.email} aprovado.` : `Pedido de ${item.name ?? item.email} recusado.`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Não foi possível concluir a ação.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className="rounded-2xl bg-white p-6 shadow-sm transition-colors dark:bg-gray-800" aria-labelledby="teacher-requests-title">
      <div className="flex items-start gap-4 border-b border-gray-200 pb-5 dark:border-gray-700">
        <div className="rounded-xl bg-[#1E5AA8]/10 p-3 text-[#1E5AA8] dark:bg-blue-400/10 dark:text-[#4FC3F7]">
          <UserPlus className="h-6 w-6" />
        </div>
        <div>
          <h2 id="teacher-requests-title" className="text-lg font-semibold text-[#0A2463] dark:text-white">Pedidos de acesso de professores</h2>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
            Cadastros feitos pela tela de login só entram no sistema depois da sua aprovação.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="mt-5 space-y-3" aria-busy="true" aria-label="Carregando pedidos">
          <div className="pe-skeleton h-14" />
          <div className="pe-skeleton h-14" />
        </div>
      ) : items.length === 0 ? (
        <p className="mt-5 rounded-xl bg-gray-50 p-4 text-sm text-gray-600 dark:bg-gray-700/60 dark:text-gray-300">
          Nenhum pedido aguardando aprovação.
        </p>
      ) : (
        <ul className="mt-5 space-y-3">
          <AnimatePresence initial={false}>
            {items.map((item) => (
              <motion.li
                key={item.userId}
                layout={!m.reduced}
                initial={m.reduced ? false : { opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: 24, transition: { duration: m.duration * 0.6 } }}
                transition={m.snappy}
                className="flex flex-col gap-3 rounded-xl border border-gray-200 p-4 sm:flex-row sm:items-center dark:border-gray-700"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-gray-900 dark:text-gray-100">{item.name || "Sem nome"}</p>
                  <p className="truncate text-sm text-gray-500 dark:text-gray-400">
                    {item.email}
                    {item.createdAt ? ` • pedido em ${formatDate(item.createdAt)}` : ""}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={busy === item.userId}
                    onClick={() => decide(item, false)}
                    className="inline-flex items-center gap-1 rounded-lg border border-rose-200 px-3 py-2 text-sm font-medium text-rose-700 hover:bg-rose-50 disabled:opacity-60 dark:border-rose-900 dark:text-rose-300 dark:hover:bg-rose-950/40"
                  >
                    <X className="h-4 w-4" /> Recusar
                  </button>
                  <button
                    type="button"
                    disabled={busy === item.userId}
                    onClick={() => decide(item, true)}
                    className="inline-flex items-center gap-1 rounded-lg bg-[#1E5AA8] px-3 py-2 text-sm font-semibold text-white hover:bg-[#0A2463] disabled:opacity-60"
                  >
                    {busy === item.userId ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />} Aprovar
                  </button>
                </div>
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      )}
    </section>
  );
}
