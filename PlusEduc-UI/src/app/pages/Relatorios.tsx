import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router";
import { ChevronLeft, ChevronRight, FileSpreadsheet, FileText, FileType2, Loader2, Search } from "lucide-react";
import { toast } from "sonner";
import { classroomsService } from "@/services";
import { reportsService } from "@/services/reports";
import type { ExportFormat, ReportCatalogItem, ReportColumn, ReportFilters, ReportResult } from "@/services/reports";
import type { Classroom } from "@/types";
import { FiltersBar } from "@/app/components/FiltersBar";

const PAGE_SIZE = 15;
const FORMATS: { format: ExportFormat; label: string; icon: typeof FileText }[] = [
  { format: "csv", label: "CSV", icon: FileType2 },
  { format: "xlsx", label: "Excel", icon: FileSpreadsheet },
  { format: "pdf", label: "PDF", icon: FileText },
];
const STATUS_LABEL: Record<string, string> = { boletim: "Situação do aluno", "entregas-atividades": "Entregas", "historico-operacoes": "Resultado" };

const normalize = (value: unknown) =>
  String(value ?? "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();

function formatCell(column: ReportColumn, value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "-";
  if (column.type === "percent") return `${value}%`;
  if (column.type === "decimal" && typeof value === "number") return value.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (column.type === "number" && typeof value === "number" && !Number.isInteger(value)) return value.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (column.type === "date" && typeof value === "string") return value.slice(0, 10).split("-").reverse().join("/");
  if (column.type === "datetime" && typeof value === "string") {
    const [date, time] = value.split(" ");
    return `${date.split("-").reverse().join("/")} ${time?.slice(0, 5) ?? ""}`.trim();
  }
  return String(value);
}

export function Relatorios() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [catalog, setCatalog] = useState<ReportCatalogItem[]>([]);
  const [classrooms, setClassrooms] = useState<Classroom[]>([]);
  const [type, setType] = useState(searchParams.get("tipo") ?? "boletim");
  const [filters, setFilters] = useState<ReportFilters>({});
  const [report, setReport] = useState<ReportResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState<ExportFormat | null>(null);
  const [text, setText] = useState("");
  const [page, setPage] = useState(0);

  useEffect(() => {
    reportsService.getCatalog().then(setCatalog).catch((err) => toast.error(err instanceof Error ? err.message : "Não foi possível carregar os relatórios."));
    classroomsService.getAllClassrooms().then((items) => setClassrooms(items.filter((item) => item.active !== false))).catch(() => setClassrooms([]));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    reportsService
      .runReport(type, filters)
      .then((result) => {
        if (!cancelled) {
          setReport(result);
          setPage(0);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setReport(null);
          setError(err instanceof Error ? err.message : "Não foi possível gerar o relatório.");
        }
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [type, filters]);

  const current = catalog.find((item) => item.type === type);
  const rows = useMemo(() => {
    if (!report) return [];
    const tokens = normalize(text.trim()).split(/\s+/).filter(Boolean);
    if (tokens.length === 0) return report.rows;
    // Todas as palavras precisam aparecer na linha, em qualquer coluna e em qualquer ordem.
    return report.rows.filter((row) => {
      const haystack = report.columns.map((column) => normalize(formatCell(column, row[column.key]))).join(" ");
      return tokens.every((token) => haystack.includes(token));
    });
  }, [report, text]);
  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const visible = rows.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);

  const selectType = (next: string) => {
    setType(next);
    setFilters({});
    setText("");
    setSearchParams({ tipo: next }, { replace: true });
  };

  const handleExport = async (format: ExportFormat) => {
    try {
      setExporting(format);
      const filename = await reportsService.exportReport(type, format, filters);
      toast.success(`Arquivo ${filename} gerado.`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Não foi possível exportar o relatório.");
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold text-[#0A2463] dark:text-white">Relatórios</h1>
        <p className="mt-1 text-gray-600 dark:text-gray-300">Consulte, filtre e exporte os dados consolidados do sistema.</p>
      </header>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5" role="tablist" aria-label="Tipos de relatório">
        {catalog.map((item) => (
          <button
            key={item.type}
            type="button"
            role="tab"
            aria-selected={item.type === type}
            onClick={() => selectType(item.type)}
            className={`rounded-xl border p-4 text-left transition ${
              item.type === type
                ? "border-[#1E5AA8] bg-blue-50 shadow-sm dark:bg-blue-950/30"
                : "border-gray-200 bg-white hover:border-[#1E5AA8] dark:border-gray-700 dark:bg-gray-800"
            }`}
          >
            <span className="block font-semibold text-[#0A2463] dark:text-white">{item.title}</span>
            <span className="mt-1 block text-xs text-gray-500 dark:text-gray-400">{item.description}</span>
          </button>
        ))}
      </div>

      <FiltersBar
        filters={filters}
        onChange={setFilters}
        classrooms={classrooms}
        statusOptions={current?.statusOptions}
        statusLabel={STATUS_LABEL[type] ?? "Situação"}
        hideClassroomAndSubject={type === "historico-operacoes"}
      />

      <section className="rounded-2xl bg-white p-5 shadow-sm dark:bg-gray-800">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-[#0A2463] dark:text-white">{report?.title ?? current?.title ?? "Relatório"}</h2>
            {report && (
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {report.total} registro(s) • gerado em {new Date(report.generatedAt).toLocaleString("pt-BR")}
              </p>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-gray-500 dark:text-gray-400">Exportar com os filtros acima:</span>
            {FORMATS.map(({ format, label, icon: Icon }) => (
              <button
                key={format}
                type="button"
                onClick={() => void handleExport(format)}
                disabled={exporting !== null || loading || !report || report.total === 0}
                className="inline-flex items-center gap-2 rounded-lg bg-[#1E5AA8] px-3 py-2 text-sm font-semibold text-white transition hover:bg-[#0A2463] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {exporting === format ? <Loader2 className="h-4 w-4 animate-spin" /> : <Icon className="h-4 w-4" />}
                {label}
              </button>
            ))}
          </div>
        </div>

        {report && report.summary.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {report.summary.map((item) => (
              <span key={item.label} className="rounded-full bg-blue-50 px-3 py-1 text-sm text-[#0A2463] dark:bg-blue-950/40 dark:text-blue-100">
                {item.label}: <strong>{item.value}</strong>
              </span>
            ))}
          </div>
        )}

        <div className="relative mt-4 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            value={text}
            onChange={(event) => {
              setText(event.target.value);
              setPage(0);
            }}
            placeholder="Pesquisar nas linhas do relatório"
            aria-label="Pesquisar nas linhas do relatório"
            className="w-full rounded-lg border border-gray-300 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
          />
        </div>

        {loading && (
          <div className="mt-6 flex items-center gap-2 text-gray-500 dark:text-gray-400">
            <Loader2 className="h-5 w-5 animate-spin" /> Gerando relatório...
          </div>
        )}
        {error && <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">{error}</div>}

        {report && !loading && (
          <>
            {rows.length === 0 ? (
              <p className="py-10 text-center text-gray-500 dark:text-gray-400">Nenhum registro para os filtros e a pesquisa atuais.</p>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[720px] text-left text-sm">
                  <thead className="bg-gray-50 dark:bg-gray-900/50">
                    <tr>
                      {report.columns.map((column) => (
                        <th key={column.key} className={`px-3 py-2 font-semibold text-gray-600 dark:text-gray-300 ${column.type === "text" ? "" : "text-right"}`}>
                          {column.label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                    {visible.map((row, index) => (
                      <tr key={`${page}-${index}`}>
                        {report.columns.map((column) => (
                          <td key={column.key} className={`px-3 py-2 text-gray-700 dark:text-gray-200 ${column.type === "text" ? "" : "text-right tabular-nums"}`}>
                            {formatCell(column, row[column.key])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {rows.length > PAGE_SIZE && (
              <div className="mt-4 flex items-center justify-between text-sm text-gray-600 dark:text-gray-300">
                <span>
                  Página {page + 1} de {pages} • {rows.length} linha(s)
                </span>
                <div className="flex gap-2">
                  <button type="button" onClick={() => setPage((value) => Math.max(0, value - 1))} disabled={page === 0} aria-label="Página anterior" className="rounded-lg border border-gray-300 p-2 disabled:opacity-40 dark:border-gray-600">
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                  <button type="button" onClick={() => setPage((value) => Math.min(pages - 1, value + 1))} disabled={page >= pages - 1} aria-label="Próxima página" className="rounded-lg border border-gray-300 p-2 disabled:opacity-40 dark:border-gray-600">
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )}
            {report.total > report.rows.length && (
              <p className="mt-2 text-xs text-gray-500">Exibindo os primeiros {report.rows.length} de {report.total} registros; use os filtros para refinar.</p>
            )}
          </>
        )}
      </section>
    </div>
  );
}
