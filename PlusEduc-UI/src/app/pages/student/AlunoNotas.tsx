import { BookOpen, CalendarCheck, ClipboardCheck, Loader2, TrendingUp } from "lucide-react";
import { useApi } from "@/hooks/useApi";
import { studentPortalService } from "@/services";
import { activityTypeLabel, formatDate } from "@/utils";

const MIN_PASSING_GRADE = 6;

export function AlunoNotas() {
  const { data: grades, loading, error } = useApi(() => studentPortalService.getGrades());
  const { data: performance } = useApi(() => studentPortalService.getPerformance());

  const hasGrades = (grades?.length ?? 0) > 0;
  const hasAttendance = (performance?.totalClasses ?? 0) > 0;

  const summaryCards = [
    {
      icon: TrendingUp,
      label: "Média geral",
      value: performance && hasGrades ? performance.averageGrade.toFixed(1) : "-",
      detail: hasGrades ? `Mínimo ${MIN_PASSING_GRADE.toFixed(1)}` : "Sem notas ainda",
      tone: performance && hasGrades && performance.averageGrade < MIN_PASSING_GRADE ? "text-red-600" : "text-emerald-600",
    },
    {
      icon: CalendarCheck,
      label: "Frequência",
      value: performance && hasAttendance ? `${performance.attendanceRate}%` : "-",
      detail: hasAttendance
        ? `${performance?.attendedClasses} presença(s) • ${performance?.absences} falta(s)`
        : "Sem presença registrada",
      tone: performance && hasAttendance && performance.attendanceRate < 75 ? "text-red-600" : "text-emerald-600",
    },
    {
      icon: ClipboardCheck,
      label: "Lançamentos",
      value: String(grades?.length ?? 0),
      detail: "Notas registradas pelos professores",
      tone: "text-[#1E5AA8]",
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[#0A2463] dark:text-white">Minhas Notas</h1>
        <p className="text-gray-600 dark:text-gray-300">Acompanhe suas notas e sua frequência por disciplina.</p>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-gray-500">
          <Loader2 className="h-5 w-5 animate-spin" />
          Carregando notas...
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>
      )}

      {!loading && !error && (
        <section className="grid gap-4 sm:grid-cols-3" aria-label="Resumo das notas">
          {summaryCards.map(({ icon: Icon, label, value, detail, tone }) => (
            <div key={label} className="rounded-2xl bg-white p-5 shadow-sm dark:bg-gray-800">
              <div className="flex items-center gap-2 text-sm font-medium text-gray-500 dark:text-gray-400">
                <Icon className="h-4 w-4" />
                {label}
              </div>
              <p className={`mt-2 text-3xl font-bold ${tone}`}>{value}</p>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{detail}</p>
            </div>
          ))}
        </section>
      )}

      {!loading && grades?.length === 0 && (
        <div className="rounded-2xl bg-white p-8 text-center shadow-sm dark:bg-gray-800">
          <BookOpen className="mx-auto h-12 w-12 text-gray-400" />
          <p className="mt-4 text-gray-600 dark:text-gray-300">Nenhuma nota registrada ainda.</p>
        </div>
      )}

      {hasGrades && (
        <div className="overflow-x-auto rounded-2xl bg-white shadow-sm dark:bg-gray-800">
          <table className="w-full min-w-[640px] text-left">
            <thead className="bg-gray-50 dark:bg-gray-900/50">
              <tr>
                {["Disciplina", "Nota", "Tipo", "Presença", "Data"].map((heading) => (
                  <th key={heading} className="px-4 py-3 text-sm font-semibold text-gray-600 dark:text-gray-300">
                    {heading}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {grades?.map((grade) => (
                <tr key={grade.id}>
                  <td className="px-4 py-3 font-medium text-[#0A2463] dark:text-white">{grade.subject}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-3 py-1 font-semibold ${
                        grade.grade >= MIN_PASSING_GRADE
                          ? "bg-[#E8F5E9] text-green-700 dark:bg-green-900/30 dark:text-green-300"
                          : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-200"
                      }`}
                    >
                      {grade.grade.toFixed(1)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-300">
                    {activityTypeLabel(grade.activityType)}
                    {grade.activityId ? (
                      <span className="ml-2 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-800 dark:bg-blue-900/30 dark:text-blue-200">
                        Atividade online
                      </span>
                    ) : null}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {grade.attendance === true ? (
                      <span className="font-semibold text-emerald-700 dark:text-emerald-300">Presente</span>
                    ) : grade.attendance === false ? (
                      <span className="font-semibold text-red-600">Faltou</span>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500 dark:text-gray-400">{formatDate(grade.date)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
