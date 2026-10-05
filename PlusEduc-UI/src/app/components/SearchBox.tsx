import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { BookOpen, GraduationCap, Loader2, Search, Users } from "lucide-react";
import { reportsService } from "@/services/reports";
import type { SearchHit } from "@/services/reports";

export const SEARCH_TYPE_LABEL: Record<SearchHit["type"], string> = { students: "Aluno", classrooms: "Turma", activities: "Atividade" };
export const SEARCH_TYPE_ICON = { students: GraduationCap, classrooms: Users, activities: BookOpen } as const;

// Pesquisa global do professor: alunos, turmas e atividades (sem diferenciar acentos nem maiúsculas).
export function SearchBox() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const term = query.trim();
    if (term.length < 2) {
      setHits([]);
      setTotal(0);
      setError(null);
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(() => {
      setLoading(true);
      reportsService
        .search(term, undefined, 8)
        .then((result) => {
          if (cancelled) return;
          setHits(result.results);
          setTotal(result.total);
          setError(null);
        })
        .catch((err) => !cancelled && setError(err instanceof Error ? err.message : "Erro na pesquisa"))
        .finally(() => !cancelled && setLoading(false));
    }, 300);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [query]);

  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      if (container.current && !container.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const go = (url: string) => {
    setOpen(false);
    setQuery("");
    navigate(url);
  };

  const term = query.trim();
  return (
    <div ref={container} className="relative w-full max-w-md">
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
      <input
        value={query}
        onChange={(event) => {
          setQuery(event.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={(event) => {
          if (event.key === "Escape") setOpen(false);
          if (event.key === "Enter" && term.length >= 2) go(`/busca?q=${encodeURIComponent(term)}`);
        }}
        placeholder="Pesquisar alunos, turmas e atividades"
        aria-label="Pesquisar alunos, turmas e atividades"
        role="combobox"
        aria-expanded={open && term.length >= 2}
        className="w-full rounded-lg border border-gray-300 bg-white py-2 pl-9 pr-9 text-sm text-gray-900 outline-none focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
      />
      {loading && <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-gray-400" />}
      {open && term.length >= 2 && (
        <div className="absolute left-0 right-0 top-full z-40 mt-2 overflow-hidden rounded-xl border border-gray-200 bg-white shadow-xl dark:border-gray-600 dark:bg-gray-800" role="listbox">
          {error ? (
            <p className="p-4 text-sm text-red-600">{error}</p>
          ) : hits.length === 0 && !loading ? (
            <p className="p-4 text-sm text-gray-500 dark:text-gray-400">Nenhum resultado para “{term}”.</p>
          ) : (
            <>
              <ul className="max-h-80 overflow-y-auto">
                {hits.map((hit) => {
                  const Icon = SEARCH_TYPE_ICON[hit.type];
                  return (
                    <li key={`${hit.type}-${hit.id}`}>
                      <button type="button" role="option" aria-selected="false" onClick={() => go(hit.url)} className="flex w-full items-center gap-3 px-4 py-2 text-left transition hover:bg-gray-50 dark:hover:bg-gray-700">
                        <Icon className="h-4 w-4 shrink-0 text-[#1E5AA8] dark:text-[#4FC3F7]" />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-medium text-[#0A2463] dark:text-white">{hit.title}</span>
                          {hit.subtitle && <span className="block truncate text-xs text-gray-500 dark:text-gray-400">{hit.subtitle}</span>}
                        </span>
                        <span className="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-300">{SEARCH_TYPE_LABEL[hit.type]}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
              <button type="button" onClick={() => go(`/busca?q=${encodeURIComponent(term)}`)} className="w-full border-t border-gray-100 px-4 py-2 text-left text-sm font-semibold text-[#1E5AA8] hover:bg-gray-50 dark:border-gray-700 dark:text-[#4FC3F7] dark:hover:bg-gray-700">
                Ver todos os {total} resultado(s)
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
