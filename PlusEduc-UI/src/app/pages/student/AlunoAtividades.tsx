import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { CheckCircle2, ClipboardList, Loader2 } from "lucide-react";
import { useApiList } from "@/hooks/useApi";
import { studentPortalService } from "@/services";
import { formatDate } from "@/utils";

type Tab = "pendentes" | "feitas";

export function AlunoAtividades() {
  const [searchParams] = useSearchParams();
  const initialTab = searchParams.get("tab") === "feitas" ? "feitas" : "pendentes";
  const [tab, setTab] = useState<Tab>(initialTab);
  const { data: activities, loading, error } = useApiList(() => studentPortalService.getActivities());

  const { pendentes, feitas } = useMemo(() => {
    const list = activities ?? [];
    return {
      pendentes: list.filter((a) => !a.submitted),
      feitas: list.filter((a) => a.submitted),
    };
  }, [activities]);

  const lista = tab === "pendentes" ? pendentes : feitas;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[#0A2463] dark:text-white">Minhas Atividades</h1>
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => setTab("pendentes")}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
            tab === "pendentes"
              ? "bg-[#1E5AA8] text-white"
              : "bg-white text-gray-600 dark:bg-gray-800 dark:text-gray-300"
          }`}
        >
          Pendentes ({pendentes.length})
        </button>
        <button
          onClick={() => setTab("feitas")}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
            tab === "feitas"
              ? "bg-[#4CAF50] text-white"
              : "bg-white text-gray-600 dark:bg-gray-800 dark:text-gray-300"
          }`}
        >
          Feitas ({feitas.length})
        </button>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-gray-500">
          <Loader2 className="h-5 w-5 animate-spin" />
          Carregando...
        </div>
      )}

      {error && <p className="text-red-600">{error}</p>}

      {!loading && lista.length === 0 && (
        <div className="rounded-2xl bg-white p-8 text-center shadow-sm dark:bg-gray-800">
          <ClipboardList className="mx-auto h-12 w-12 text-gray-400" />
          <p className="mt-4 text-gray-600 dark:text-gray-300">
            {tab === "pendentes" ? "Nenhuma atividade pendente." : "Nenhuma atividade feita ainda."}
          </p>
        </div>
      )}

      <div className="grid gap-4">
        {lista.map((activity) => (
          <Link
            key={activity.id}
            to={`/aluno/atividades/${activity.id}${tab === "feitas" ? "?review=1" : ""}`}
            className="rounded-2xl bg-white p-5 shadow-sm transition hover:shadow-md dark:bg-gray-800"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-[#0A2463] dark:text-white">{activity.title}</h2>
                <p className="mt-1 text-sm text-gray-500">{activity.subject} • {activity.topic}</p>
                <p className="mt-2 text-xs text-gray-400">{formatDate(activity.createdAt)}</p>
              </div>
              {activity.submitted ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-300">
                  <CheckCircle2 className="h-3 w-3" />
                  Feita
                </span>
              ) : (
                <span className="rounded-full bg-orange-100 px-3 py-1 text-xs font-medium text-orange-700">
                  Pendente
                </span>
              )}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
