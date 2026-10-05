import { useEffect, useState } from "react";
import { ChevronDown, ChevronLeft, ChevronRight, ChevronUp, FilterX, History, Loader2, Search } from "lucide-react";
import { reportsService } from "@/services/reports";
import type { AuditFilters, AuditLogEntry, AuditLogPage } from "@/services/reports";
import { useAuth } from "@/contexts/AuthContext";
import { activityTypeLabel, formatDate } from "@/utils";

const PAGE_SIZE = 15;
const ENTITIES: [string, string][] = [
  ["grade", "Nota"],
  ["classroom", "Turma"],
  ["student", "Aluno"],
  ["activity", "Atividade"],
  ["submission", "Submissão"],
  ["correction", "Correção"],
  ["auth", "Autenticação"],
  ["teacher", "Professor"],
  ["subject", "Matéria"],
];
const ACTIONS: [string, string][] = [
  ["CREATE", "Criação"],
  ["UPDATE", "Alteração"],
  ["DELETE", "Exclusão"],
  ["LAUNCH_FROM_ACTIVITY", "Lançamento por atividade"],
  ["ENROLL", "Matrícula em turma"],
  ["UNENROLL", "Remoção de turma"],
  ["GENERATE", "Geração de atividade"],
  ["SUBMIT", "Envio de atividade"],
  ["REVIEW", "Correção de questão"],
  ["LOGIN", "Login"],
  ["LOGIN_FAILED", "Login recusado"],
  ["REGISTER", "Cadastro de usuário"],
  ["PASSWORD_RESET", "Redefinição de senha"],
  ["ACCESS_DENIED", "Acesso negado"],
];
const FIELD_LABELS: Record<string, string> = {
  grade: "Nota",
  attendance: "Presença",
  subject: "Disciplina",
  activityType: "Tipo",
  observations: "Observações",
  date: "Data",
};
const inputClass =
  "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100";

const show = (value: unknown, key?: string) => {
  if (value === null || value === undefined || value === "") return "-";
  if (value === true) return "Presente";
  if (value === false) return "Faltou";
  if (key === "grade" && typeof value === "number") return value.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 2 });
  if (key === "date" && typeof value === "string") return formatDate(value);
  if (key === "activityType" && typeof value === "string") return activityTypeLabel(value);
  return String(value);
};

function Details({ entry }: { entry: AuditLogEntry }) {
  const before = entry.details.before as Record<string, unknown> | undefined;
  const after = entry.details.after as Record<string, unknown> | undefined;
  if (before || after) {
    const keys = Array.from(new Set([...Object.keys(before ?? {}), ...Object.keys(after ?? {})])).filter((key) => key in FIELD_LABELS);
    return (
      <table className="text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-500">
            <th className="pr-6">Campo</th>
            {before && <th className="pr-6">Antes</th>}
            {after && <th>Depois</th>}
          </tr>
        </thead>
        <tbody>
          {keys.map((key) => {
            const changed = before && after && show(before[key], key) !== show(after[key], key);
            return (
              <tr key={key} className={changed ? "font-semibold text-[#0A2463] dark:text-white" : "text-gray-600 dark:text-gray-300"}>
                <td className="pr-6">{FIELD_LABELS[key]}</td>
                {before && <td className="pr-6">{show(before[key], key)}</td>}
                {after && <td>{show(after[key], key)}</td>}
              </tr>
            );
          })}
        </tbody>
      </table>
    );
  }
  const pairs = Object.entries(entry.details);
  return pairs.length === 0 ? (
    <p className="text-sm text-gray-500">Sem detalhes adicionais.</p>
  ) : (
    <dl className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
      {pairs.map(([key, value]) => (
        <div key={key} className="flex gap-2">
          <dt className="text-gray-500">{key}:</dt>
          <dd className="break-all text-gray-800 dark:text-gray-100">{typeof value === "object" ? JSON.stringify(value) : String(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

export function Historico() {
  const { role } = useAuth();
  const [filters, setFilters] = useState<AuditFilters>({});
  const [page, setPage] = useState(0);
  const [data, setData] = useState<AuditLogPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setFilters((current) => (current.q === (query || undefined) ? current : { ...current, q: query || undefined }));
      setPage(0);
    }, 350);
    return () => window.clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    reportsService
      .getAuditLogs(filters, page, PAGE_SIZE)
      .then((result) => !cancelled && setData(result))
      .catch((err) => !cancelled && setError(err instanceof Error ? err.message : "Não foi possível carregar o histórico."))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [filters, page]);

  const set = (patch: Partial<AuditFilters>) => {
    setFilters((current) => ({ ...current, ...patch }));
    setPage(0);
  };
  const hasFilters = Object.values(filters).some(Boolean) || query !== "";

  return (
    <div className="space-y-6">
      <header className="flex items-start gap-3">
        <div className="rounded-xl bg-[#1E5AA8] p-3 text-white shadow-sm">
          <History className="h-6 w-6" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-[#0A2463] dark:text-white">Histórico de operações</h1>
          <p className="mt-1 text-gray-600 dark:text-gray-300">
            Registro de cada operação que alterou dados (notas, turmas, alunos, atividades, logins). {role === "ADMIN" ? "Você vê as operações de todos os usuários." : "Você vê as operações feitas com o seu usuário."}
          </p>
        </div>
      </header>

      <section className="rounded-2xl bg-white p-4 shadow-sm dark:bg-gray-800" aria-label="Filtros do histórico">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-7">
          <label className="block text-xs font-medium text-gray-600 dark:text-gray-300 lg:col-span-2">
            Pesquisar
            <div className="relative mt-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Descrição, usuário ou id" className={`${inputClass} pl-9`} />
            </div>
          </label>
          <label className="block text-xs font-medium text-gray-600 dark:text-gray-300">
            Entidade
            <select value={filters.entity ?? ""} onChange={(event) => set({ entity: event.target.value || undefined })} className={`${inputClass} mt-1`}>
              <option value="">Todas</option>
              {ENTITIES.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-xs font-medium text-gray-600 dark:text-gray-300">
            Ação
            <select value={filters.action ?? ""} onChange={(event) => set({ action: event.target.value || undefined })} className={`${inputClass} mt-1`}>
              <option value="">Todas</option>
              {ACTIONS.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-xs font-medium text-gray-600 dark:text-gray-300">
            Resultado
            <select value={filters.success ?? ""} onChange={(event) => set({ success: event.target.value || undefined })} className={`${inputClass} mt-1`}>
              <option value="">Todos</option>
              <option value="true">Sucesso</option>
              <option value="false">Falha</option>
            </select>
          </label>
          <>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-300">
              De
              <input type="date" value={filters.from ?? ""} max={filters.to || undefined} onChange={(event) => set({ from: event.target.value || undefined })} className={`${inputClass} mt-1`} />
            </label>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-300">
              Até
              <input type="date" value={filters.to ?? ""} min={filters.from || undefined} onChange={(event) => set({ to: event.target.value || undefined })} className={`${inputClass} mt-1`} />
            </label>
          </>
        </div>
        {hasFilters && (
          <button
            type="button"
            onClick={() => {
              setFilters({});
              setQuery("");
              setPage(0);
            }}
            className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-[#1E5AA8] hover:underline dark:text-[#4FC3F7]"
          >
            <FilterX className="h-4 w-4" /> Limpar filtros
          </button>
        )}
      </section>

      <section className="overflow-hidden rounded-2xl bg-white shadow-sm dark:bg-gray-800">
        {loading && !data && (
          <div className="flex items-center gap-2 p-6 text-gray-500 dark:text-gray-400">
            <Loader2 className="h-5 w-5 animate-spin" /> Carregando histórico...
          </div>
        )}
        {error && <div className="m-4 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">{error}</div>}
        {data && (
          <>
            <div className="flex items-center justify-between border-b border-gray-200 px-5 py-3 text-sm text-gray-600 dark:border-gray-700 dark:text-gray-300">
              <span>{data.total} operação(ões)</span>
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            </div>
            {data.items.length === 0 ? (
              <p className="py-12 text-center text-gray-500 dark:text-gray-400">Nenhuma operação encontrada para os filtros atuais.</p>
            ) : (
              <ul className="divide-y divide-gray-100 dark:divide-gray-700">
                {data.items.map((entry) => {
                  const open = openId === entry.id;
                  return (
                    <li key={entry.id} className="px-5 py-3">
                      <button type="button" onClick={() => setOpenId(open ? null : entry.id)} aria-expanded={open} className="flex w-full items-start gap-3 text-left">
                        <span
                          className={`mt-0.5 shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                            entry.success ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-200" : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-200"
                          }`}
                        >
                          {entry.success ? "Sucesso" : `Falha ${entry.status}`}
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block text-gray-900 dark:text-gray-100">{entry.summary}</span>
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {new Date(entry.timestamp).toLocaleString("pt-BR")} • {entry.actionLabel} • {entry.entityLabel} • {entry.actorEmail ?? "usuário não identificado"}
                          </span>
                        </span>
                        {open ? <ChevronUp className="h-5 w-5 shrink-0 text-gray-400" /> : <ChevronDown className="h-5 w-5 shrink-0 text-gray-400" />}
                      </button>
                      {open && (
                        <div className="mt-3 space-y-2 rounded-lg bg-gray-50 p-4 dark:bg-gray-900/40">
                          <Details entry={entry} />
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            {entry.method} {entry.path} {entry.entityId ? `• id ${entry.entityId}` : ""}
                          </p>
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
            {data.totalPages > 1 && (
              <div className="flex items-center justify-between border-t border-gray-200 px-5 py-3 text-sm text-gray-600 dark:border-gray-700 dark:text-gray-300">
                <span>
                  Página {data.page + 1} de {data.totalPages}
                </span>
                <div className="flex gap-2">
                  <button type="button" onClick={() => setPage((value) => Math.max(0, value - 1))} disabled={page === 0} aria-label="Página anterior" className="rounded-lg border border-gray-300 p-2 disabled:opacity-40 dark:border-gray-600">
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                  <button type="button" onClick={() => setPage((value) => Math.min(data.totalPages - 1, value + 1))} disabled={page >= data.totalPages - 1} aria-label="Próxima página" className="rounded-lg border border-gray-300 p-2 disabled:opacity-40 dark:border-gray-600">
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}
