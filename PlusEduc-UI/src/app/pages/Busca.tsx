import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { Loader2, Search } from "lucide-react";
import { reportsService } from "@/services/reports";
import type { SearchHit, SearchResult } from "@/services/reports";
import { SEARCH_TYPE_ICON, SEARCH_TYPE_LABEL } from "@/app/components/SearchBox";

const TABS: { value: string; label: string }[] = [
  { value: "", label: "Tudo" },
  { value: "students", label: "Alunos" },
  { value: "classrooms", label: "Turmas" },
  { value: "activities", label: "Atividades" },
];

export function Busca() {
  const [params, setParams] = useSearchParams();
  const initial = params.get("q") ?? "";
  const [text, setText] = useState(initial);
  const [type, setType] = useState("");
  const [result, setResult] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const q = (params.get("q") ?? "").trim();

  useEffect(() => {
    setText(params.get("q") ?? "");
  }, [params]);

  useEffect(() => {
    if (q.length < 2) {
      setResult(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    reportsService
      .search(q, type || undefined, 100)
      .then((response) => !cancelled && setResult(response))
      .catch((err) => !cancelled && setError(err instanceof Error ? err.message : "Erro na pesquisa"))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [q, type]);

  const grouped = (["students", "classrooms", "activities"] as SearchHit["type"][])
    .map((kind) => ({ kind, items: (result?.results ?? []).filter((hit) => hit.type === kind) }))
    .filter((group) => group.items.length > 0);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold text-[#0A2463] dark:text-white">Pesquisa</h1>
        <p className="mt-1 text-gray-600 dark:text-gray-300">Localize alunos (nome, matrícula ou e-mail), turmas e atividades (título, matéria ou tópico). Acentos e maiúsculas não importam.</p>
      </header>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          setParams(text.trim() ? { q: text.trim() } : {});
        }}
        className="flex max-w-2xl gap-2"
      >
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input value={text} onChange={(event) => setText(event.target.value)} placeholder="Digite ao menos 2 letras" aria-label="Termo da pesquisa" className="w-full rounded-lg border border-gray-300 bg-white py-2.5 pl-9 pr-3 outline-none focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100" />
        </div>
        <button type="submit" className="rounded-lg bg-[#1E5AA8] px-5 py-2.5 font-semibold text-white transition hover:bg-[#0A2463]">
          Pesquisar
        </button>
      </form>

      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Filtrar por tipo">
        {TABS.map((tab) => (
          <button
            key={tab.value}
            type="button"
            role="tab"
            aria-selected={type === tab.value}
            onClick={() => setType(tab.value)}
            className={`rounded-full px-4 py-1.5 text-sm font-semibold transition ${type === tab.value ? "bg-[#1E5AA8] text-white" : "bg-white text-gray-600 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-300"}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {q.length < 2 && <p className="text-gray-500 dark:text-gray-400">Digite um termo com pelo menos 2 caracteres para pesquisar.</p>}
      {loading && (
        <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
          <Loader2 className="h-5 w-5 animate-spin" /> Pesquisando...
        </div>
      )}
      {error && <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>}

      {result && !loading && (
        <>
          <p className="text-sm text-gray-600 dark:text-gray-300">
            {result.total} resultado(s) para “{result.query}”.
          </p>
          {grouped.length === 0 && <p className="rounded-2xl bg-white p-8 text-center text-gray-500 shadow-sm dark:bg-gray-800">Nenhum resultado encontrado.</p>}
          {grouped.map(({ kind, items }) => {
            const Icon = SEARCH_TYPE_ICON[kind];
            return (
              <section key={kind} className="rounded-2xl bg-white p-5 shadow-sm dark:bg-gray-800">
                <h2 className="mb-2 flex items-center gap-2 text-lg font-semibold text-[#0A2463] dark:text-white">
                  <Icon className="h-5 w-5" /> {SEARCH_TYPE_LABEL[kind]}s ({items.length})
                </h2>
                <ul className="divide-y divide-gray-100 dark:divide-gray-700">
                  {items.map((hit) => (
                    <li key={hit.id}>
                      <Link to={hit.url} className="block py-2 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                        <span className="block font-medium text-[#0A2463] dark:text-white">{hit.title}</span>
                        {hit.subtitle && <span className="text-sm text-gray-500 dark:text-gray-400">{hit.subtitle}</span>}
                      </Link>
                    </li>
                  ))}
                </ul>
              </section>
            );
          })}
        </>
      )}
    </div>
  );
}
