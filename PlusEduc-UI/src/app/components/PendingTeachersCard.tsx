import { useCallback, useEffect, useState } from "react";
import { Check, Loader2, UserCheck, X } from "lucide-react";
import { toast } from "sonner";
import { teachersService } from "@/services";
import type { PendingTeacher } from "@/types";
import { formatDateTime } from "@/utils";

// Cadastros públicos de professor aguardando aprovação (RF04). Só aparece para o ADMIN.
export function PendingTeachersCard() {
  const [items, setItems] = useState<PendingTeacher[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      setItems(await teachersService.listPending());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível carregar os cadastros pendentes.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const decide = async (teacher: PendingTeacher, approve: boolean) => {
    if (!approve && !window.confirm(`Recusar o cadastro de ${teacher.name}? O pedido será removido.`)) {
      return;
    }
    try {
      setBusyId(teacher.id);
      if (approve) {
        await teachersService.approve(teacher.id);
        toast.success(`${teacher.name} aprovado(a). O acesso já está liberado.`);
      } else {
        await teachersService.reject(teacher.id);
        toast.success(`Cadastro de ${teacher.name} recusado.`);
      }
      setItems((current) => current.filter((item) => item.id !== teacher.id));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Não foi possível concluir a operação.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section className="rounded-2xl bg-white p-6 shadow-sm transition-colors dark:bg-gray-800">
      <div className="flex items-start gap-4 border-b border-gray-200 pb-5 dark:border-gray-700">
        <div className="rounded-xl bg-[#1E5AA8]/10 p-3 text-[#1E5AA8] dark:bg-blue-400/10 dark:text-[#4FC3F7]">
          <UserCheck className="h-6 w-6" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-[#0A2463] dark:text-white">Cadastros de professores pendentes</h2>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
            Professores que se cadastraram pela tela de login só entram depois da sua aprovação.
          </p>
        </div>
      </div>

      <div className="mt-6">
        {loading ? (
          <p className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
            <Loader2 className="h-4 w-4 animate-spin" /> Carregando cadastros...
          </p>
        ) : error ? (
          <p role="alert" className="text-sm text-red-600 dark:text-red-400">{error}</p>
        ) : items.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">Nenhum cadastro aguardando aprovação.</p>
        ) : (
          <ul className="divide-y divide-gray-200 dark:divide-gray-700">
            {items.map((teacher) => (
              <li key={teacher.id} className="flex flex-col gap-3 py-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="font-semibold text-[#0A2463] dark:text-white">{teacher.name}</p>
                  <p className="break-all text-sm text-gray-600 dark:text-gray-300">{teacher.email}</p>
                  {teacher.createdAt && (
                    <p className="text-xs text-gray-500 dark:text-gray-400">Pedido em {formatDateTime(teacher.createdAt)}</p>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => void decide(teacher, true)}
                    disabled={busyId === teacher.id}
                    className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-60"
                  >
                    <Check className="h-4 w-4" /> Aprovar
                  </button>
                  <button
                    type="button"
                    onClick={() => void decide(teacher, false)}
                    disabled={busyId === teacher.id}
                    className="inline-flex items-center gap-1 rounded-lg border border-rose-300 px-3 py-2 text-sm font-semibold text-rose-700 transition hover:bg-rose-50 disabled:opacity-60 dark:border-rose-800 dark:text-rose-300 dark:hover:bg-rose-950/30"
                  >
                    <X className="h-4 w-4" /> Recusar
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
