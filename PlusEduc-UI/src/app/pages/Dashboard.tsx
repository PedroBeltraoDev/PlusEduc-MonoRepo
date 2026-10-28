import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router";
import {
  AlertCircle,
  AlertTriangle,
  CalendarCheck,
  CheckCircle,
  ClipboardList,
  Clock,
  GraduationCap,
  History,
  Loader2,
  Send,
  TrendingUp,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { activitiesService, classroomsService } from "@/services";
import { reportsService } from "@/services/reports";
import type { DashboardOverview, ReportFilters } from "@/services/reports";
import type { Activity, Classroom } from "@/types";
import { formatDate } from "@/utils";
import { FiltersBar } from "@/app/components/FiltersBar";

const BLUE = "#1E5AA8";
const LIGHT_BLUE = "#4FC3F7";
const GREEN = "#4CAF50";
const ORANGE = "#FF9800";
const AXIS = "#6B7280";
const MONTHS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

const monthLabel = (value: string) => {
  const [year, month] = value.split("-");
  return `${MONTHS[Number(month) - 1] ?? month}/${year.slice(2)}`;
};
const decimal = (value: number | null | undefined, digits = 1) =>
  value === null || value === undefined ? "-" : value.toLocaleString("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: 2 });
const shorten = (value: string, max = 24) => (value.length > max ? `${value.slice(0, max - 1)}…` : value);
const compactClassroom = (name: string) =>
  name.replace(/^Turma /, "").replace("Ano do Ensino Fundamental", "Ano (EF)").replace("Ano do Ensino Médio", "Ano (EM)");
const TICKS = [0, 2, 4, 6, 8, 10];

function ChartCard({ title, subtitle, empty, children }: { title: string; subtitle?: string; empty: boolean; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl bg-white p-5 shadow-sm dark:bg-gray-800">
      <h2 className="text-lg font-semibold text-[#0A2463] dark:text-white">{title}</h2>
      {subtitle && <p className="mb-3 text-sm text-gray-500 dark:text-gray-400">{subtitle}</p>}
      {empty ? <p className="py-10 text-center text-sm text-gray-500 dark:text-gray-400">Sem dados para os filtros selecionados.</p> : children}
    </section>
  );
}

export function Dashboard() {
  const navigate = useNavigate();
  const [classrooms, setClassrooms] = useState<Classroom[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [filters, setFilters] = useState<ReportFilters>({});
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    classroomsService.getAllClassrooms().then((items) => setClassrooms(items.filter((item) => item.active !== false))).catch(() => setClassrooms([]));
    activitiesService.getAllActivities().then(setActivities).catch(() => setActivities([]));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    reportsService
      .getDashboard(filters)
      .then((overview) => !cancelled && setData(overview))
      .catch((err) => !cancelled && setError(err instanceof Error ? err.message : "Erro ao carregar o dashboard"))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [filters, reloadKey]);

  const recentActivities = useMemo(
    () =>
      activities
        .filter((item) => (!filters.classroomId || item.classroomId === filters.classroomId) && (!filters.subject || item.subject === filters.subject))
        .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
        .slice(0, 5),
    [activities, filters.classroomId, filters.subject],
  );

  const activityStatus = (activity: Activity) => {
    const participation = activity.participation;
    if (!participation || participation.totalStudents === 0) return { label: "Sem alunos", color: "text-gray-500", Icon: Clock };
    const label = `${participation.completedStudents}/${participation.totalStudents} entregaram`;
    if (participation.completedStudents === participation.totalStudents) return { label, color: "text-[#4CAF50]", Icon: CheckCircle };
    if (participation.completedStudents === 0) return { label, color: "text-[#FF9800]", Icon: Clock };
    return { label, color: "text-[#1E5AA8] dark:text-[#4FC3F7]", Icon: Clock };
  };

  const kpis = data?.kpis;
  const delivered = data?.participation.delivered ?? 0;
  const expected = delivered + (data?.participation.pending ?? 0);
  const cards = kpis
    ? [
        { icon: GraduationCap, label: "Alunos", value: String(kpis.students), detail: `${kpis.classrooms} turma(s)`, color: "bg-[#4FC3F7]" },
        { icon: ClipboardList, label: "Atividades", value: String(kpis.activities), detail: "Criadas no período e filtros", color: "bg-[#FF9800]" },
        { icon: TrendingUp, label: "Média geral", value: decimal(kpis.averageGrade, 1), detail: `${kpis.gradeLaunches} lançamento(s)`, color: "bg-[#4CAF50]" },
        { icon: CalendarCheck, label: "Frequência", value: kpis.attendanceRate === null ? "-" : `${kpis.attendanceRate}%`, detail: "Presenças registradas", color: "bg-[#1E5AA8]" },
        { icon: Send, label: "Taxa de entrega", value: kpis.submissionRate === null ? "-" : `${kpis.submissionRate}%`, detail: `${delivered} de ${expected} entregas`, color: "bg-[#7E57C2]" },
        { icon: AlertTriangle, label: "Alunos em atenção", value: String(kpis.studentsAtRisk), detail: "Média < 6,0 ou frequência < 75%", color: "bg-[#E53935]" },
      ]
    : [];

  const classroomChart = (data?.averageByClassroom ?? []).map((item) => ({ ...item, label: shorten(compactClassroom(item.name), 24) }));
  const subjectChart = (data?.averageBySubject ?? []).map((item) => ({ ...item, label: shorten(item.name, 22) }));
  const monthlyChart = (data?.monthlyAverage ?? []).map((item) => ({ ...item, label: monthLabel(item.month) }));
  const participation = [
    { name: "Entregues", value: delivered, color: GREEN },
    { name: "Pendentes", value: data?.participation.pending ?? 0, color: ORANGE },
  ];
  const hasParticipation = participation.some((item) => item.value > 0);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-[#0A2463] dark:text-white">Dashboard</h1>
          <p className="mt-1 text-gray-600 dark:text-gray-300">Indicadores calculados a partir das notas, frequências e atividades reais do sistema.</p>
        </div>
        <Link to="/relatorios" className="rounded-lg border border-[#1E5AA8] px-4 py-2 text-sm font-semibold text-[#1E5AA8] transition hover:bg-[#1E5AA8] hover:text-white dark:border-[#4FC3F7] dark:text-[#4FC3F7]">
          Ver relatórios e exportar
        </Link>
      </header>

      <FiltersBar filters={filters} onChange={setFilters} classrooms={classrooms} />

      {error && (
        <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">
          <AlertCircle className="h-5 w-5" />
          <span>{error}</span>
          <button type="button" onClick={() => setReloadKey((key) => key + 1)} className="ml-auto rounded-lg bg-[#1E5AA8] px-3 py-1 text-sm font-semibold text-white">
            Tentar novamente
          </button>
        </div>
      )}

      {loading && !data && (
        <div className="flex items-center gap-2 py-10 text-gray-500 dark:text-gray-400">
          <Loader2 className="h-6 w-6 animate-spin text-[#1E5AA8]" /> Carregando indicadores...
        </div>
      )}

      {data && (
        <div className={loading ? "space-y-6 opacity-60 transition-opacity" : "space-y-6 transition-opacity"} aria-busy={loading}>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-6">
            {cards.map(({ icon: Icon, label, value, detail, color }) => (
              <div key={label} className="rounded-2xl bg-white p-4 shadow-sm dark:bg-gray-800">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm text-gray-600 dark:text-gray-300">{label}</p>
                    <p className="mt-1 text-2xl font-bold text-[#0A2463] dark:text-white">{value}</p>
                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{detail}</p>
                  </div>
                  <div className={`${color} shrink-0 rounded-lg p-2.5`}>
                    <Icon className="h-5 w-5 text-white" />
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <ChartCard title="Média por turma" subtitle="Nota de 0 a 10; passe o mouse para ver o nome completo." empty={classroomChart.length === 0}>
              <div style={{ height: Math.max(240, classroomChart.length * 30 + 40) }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={classroomChart} layout="vertical" margin={{ left: 8, right: 24 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" domain={[0, 10]} ticks={TICKS} tick={{ fill: AXIS, fontSize: 12 }} />
                    <YAxis type="category" dataKey="label" width={120} tick={{ fill: AXIS, fontSize: 11 }} />
                    <Tooltip formatter={(value: number) => [decimal(value, 2), "Média"]} labelFormatter={(_, payload) => payload?.[0]?.payload?.name ?? ""} />
                    <Bar dataKey="average" fill={BLUE} radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            <ChartCard title="Média por disciplina" subtitle="Disciplinas com o mesmo nome (com ou sem acento) são agrupadas." empty={subjectChart.length === 0}>
              <div style={{ height: Math.max(240, subjectChart.length * 34 + 40) }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={subjectChart} layout="vertical" margin={{ left: 8, right: 24 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" domain={[0, 10]} ticks={TICKS} tick={{ fill: AXIS, fontSize: 12 }} />
                    <YAxis type="category" dataKey="label" width={140} tick={{ fill: AXIS, fontSize: 11 }} />
                    <Tooltip formatter={(value: number) => [decimal(value, 2), "Média"]} labelFormatter={(_, payload) => payload?.[0]?.payload?.name ?? ""} />
                    <Bar dataKey="average" fill={GREEN} radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            <ChartCard title="Evolução da média" subtitle="Média das notas lançadas em cada mês." empty={monthlyChart.length === 0}>
              <div style={{ height: 260 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={monthlyChart} margin={{ left: 0, right: 16, top: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="label" tick={{ fill: AXIS, fontSize: 12 }} />
                    <YAxis domain={[0, 10]} ticks={TICKS} tick={{ fill: AXIS, fontSize: 12 }} />
                    <Tooltip formatter={(value: number) => [decimal(value, 2), "Média"]} />
                    <Line type="monotone" dataKey="average" stroke={BLUE} strokeWidth={2} dot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            <ChartCard title="Distribuição das notas" subtitle="Quantidade de lançamentos por faixa de nota." empty={(kpis?.gradeLaunches ?? 0) === 0}>
              <div style={{ height: 260 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.distribution} margin={{ left: 0, right: 16, top: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="range" tick={{ fill: AXIS, fontSize: 12 }} />
                    <YAxis allowDecimals={false} tick={{ fill: AXIS, fontSize: 12 }} />
                    <Tooltip formatter={(value: number) => [value, "Lançamentos"]} />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                      {data.distribution.map((bucket, index) => (
                        <Cell key={bucket.range} fill={index < 3 ? "#E53935" : index === 3 ? LIGHT_BLUE : GREEN} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            <ChartCard title="Entrega de atividades" subtitle="Submissões recebidas em relação ao esperado (alunos × atividades)." empty={!hasParticipation}>
              <div style={{ height: 260 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={participation} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} paddingAngle={2}>
                      {participation.map((item) => (
                        <Cell key={item.name} fill={item.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            <section className="rounded-2xl bg-white p-5 shadow-sm dark:bg-gray-800">
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-lg font-semibold text-[#0A2463] dark:text-white">Alunos em atenção</h2>
                <Link to="/relatorios?tipo=alunos-atencao" className="text-sm font-semibold text-[#1E5AA8] hover:underline dark:text-[#4FC3F7]">
                  Ver todos
                </Link>
              </div>
              {data.atRisk.length === 0 ? (
                <p className="py-10 text-center text-sm text-gray-500 dark:text-gray-400">Nenhum aluno em atenção para estes filtros.</p>
              ) : (
                <ul className="mt-3 divide-y divide-gray-100 dark:divide-gray-700">
                  {data.atRisk.slice(0, 6).map((student) => (
                    <li key={student.studentId} className="py-2">
                      <p className="font-medium text-[#0A2463] dark:text-white">{student.studentName}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {student.classroomName} • média {decimal(student.average)} • frequência {student.attendanceRate === null ? "-" : `${student.attendanceRate}%`}
                      </p>
                      <p className="text-xs text-red-600 dark:text-red-400">{student.reasons.join("; ")}</p>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <section className="rounded-2xl bg-white p-5 shadow-sm dark:bg-gray-800">
              <h2 className="mb-3 text-lg font-semibold text-[#0A2463] dark:text-white">Atividades recentes</h2>
              {recentActivities.length === 0 ? (
                <p className="py-8 text-center text-sm text-gray-500 dark:text-gray-400">Nenhuma atividade encontrada.</p>
              ) : (
                <div className="space-y-2">
                  {recentActivities.map((activity) => {
                    const status = activityStatus(activity);
                    return (
                      <button
                        key={activity.id}
                        type="button"
                        onClick={() => navigate(`/atividades/${activity.id}`)}
                        className="flex w-full items-center gap-3 rounded-lg bg-gray-50 p-3 text-left transition hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-[#1E5AA8] dark:bg-gray-700 dark:hover:bg-gray-600"
                      >
                        <status.Icon className={`h-5 w-5 shrink-0 ${status.color}`} />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate font-semibold text-[#0A2463] dark:text-white">{activity.title}</span>
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {formatDate(activity.createdAt)} • {activity.subject} • {activity.difficultyLevel}
                          </span>
                        </span>
                        <span className={`shrink-0 text-sm font-medium ${status.color}`}>{status.label}</span>
                      </button>
                    );
                  })}
                </div>
              )}
            </section>

            <section className="rounded-2xl bg-white p-5 shadow-sm dark:bg-gray-800">
              <div className="mb-3 flex items-center justify-between gap-2">
                <h2 className="flex items-center gap-2 text-lg font-semibold text-[#0A2463] dark:text-white">
                  <History className="h-5 w-5" /> Últimas operações
                </h2>
                <Link to="/historico" className="text-sm font-semibold text-[#1E5AA8] hover:underline dark:text-[#4FC3F7]">
                  Histórico completo
                </Link>
              </div>
              {data.recentOperations.length === 0 ? (
                <p className="py-8 text-center text-sm text-gray-500 dark:text-gray-400">Nenhuma operação registrada ainda.</p>
              ) : (
                <ul className="divide-y divide-gray-100 dark:divide-gray-700">
                  {data.recentOperations.map((entry) => (
                    <li key={entry.id} className="py-2">
                      <p className="text-sm text-gray-800 dark:text-gray-100">{entry.summary}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {new Date(entry.timestamp).toLocaleString("pt-BR")} • {entry.actionLabel}
                        {!entry.success && <span className="ml-1 font-semibold text-red-600">• falhou ({entry.status})</span>}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          <p className="text-xs text-gray-500 dark:text-gray-400">
            Atualizado em {new Date(data.generatedAt).toLocaleString("pt-BR")}
            {Object.keys(data.filters).length > 0 && ` • Filtros: ${Object.entries(data.filters).map(([k, v]) => `${k}: ${v}`).join(" | ")}`}
          </p>
        </div>
      )}
    </div>
  );
}
