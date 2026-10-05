import { useMemo } from "react";
import { FilterX } from "lucide-react";
import type { ReportFilters } from "@/services/reports";
import type { Classroom } from "@/types";

const inputClass =
  "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100";

interface FiltersBarProps {
  filters: ReportFilters;
  onChange: (next: ReportFilters) => void;
  classrooms: Classroom[];
  statusOptions?: { value: string; label: string }[];
  statusLabel?: string;
  hideClassroomAndSubject?: boolean;
}

export function FiltersBar({ filters, onChange, classrooms, statusOptions, statusLabel = "Situação", hideClassroomAndSubject }: FiltersBarProps) {
  const subjects = useMemo(() => {
    const source = filters.classroomId ? classrooms.filter((item) => item.id === filters.classroomId) : classrooms;
    return Array.from(new Set(source.flatMap((item) => item.subjects ?? []))).sort((a, b) => a.localeCompare(b, "pt-BR"));
  }, [classrooms, filters.classroomId]);

  const hasFilters = Object.values(filters).some(Boolean);
  const set = (patch: Partial<ReportFilters>) => onChange({ ...filters, ...patch });

  return (
    <section className="rounded-2xl bg-white p-4 shadow-sm dark:bg-gray-800" aria-label="Filtros">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
        {!hideClassroomAndSubject && (
          <>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-300 lg:col-span-2">
              Turma
              <select
                value={filters.classroomId ?? ""}
                onChange={(event) => set({ classroomId: event.target.value || undefined, subject: undefined })}
                className={`${inputClass} mt-1`}
              >
                <option value="">Todas as turmas</option>
                {classrooms.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-300">
              Disciplina
              <select value={filters.subject ?? ""} onChange={(event) => set({ subject: event.target.value || undefined })} className={`${inputClass} mt-1`}>
                <option value="">Todas</option>
                {subjects.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
          </>
        )}
        <label className="block text-xs font-medium text-gray-600 dark:text-gray-300">
          De
          <input type="date" value={filters.from ?? ""} max={filters.to || undefined} onChange={(event) => set({ from: event.target.value || undefined })} className={`${inputClass} mt-1`} />
        </label>
        <label className="block text-xs font-medium text-gray-600 dark:text-gray-300">
          Até
          <input type="date" value={filters.to ?? ""} min={filters.from || undefined} onChange={(event) => set({ to: event.target.value || undefined })} className={`${inputClass} mt-1`} />
        </label>
        {statusOptions && statusOptions.length > 0 && (
          <label className="block text-xs font-medium text-gray-600 dark:text-gray-300">
            {statusLabel}
            <select value={filters.status ?? ""} onChange={(event) => set({ status: event.target.value || undefined })} className={`${inputClass} mt-1`}>
              <option value="">Todas</option>
              {statusOptions.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
      {hasFilters && (
        <button
          type="button"
          onClick={() => onChange({})}
          className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-[#1E5AA8] hover:underline dark:text-[#4FC3F7]"
        >
          <FilterX className="h-4 w-4" />
          Limpar filtros
        </button>
      )}
    </section>
  );
}
