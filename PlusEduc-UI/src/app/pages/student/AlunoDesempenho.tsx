import {
  AlertCircle,
  Award,
  BarChart3,
  CheckCircle2,
  ClipboardCheck,
  Loader2,
  Target,
  TrendingUp,
} from "lucide-react";
import { useApi } from "@/hooks/useApi";
import { studentPortalService } from "@/services";

function formatGrade(value: number) {
  return value.toFixed(1);
}

function getSubjectStatus(average: number) {
  if (average >= 7) {
    return {
      label: "Bom progresso",
      className: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
      barClassName: "bg-emerald-500",
    };
  }

  if (average >= 5) {
    return {
      label: "Pode melhorar",
      className: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
      barClassName: "bg-amber-500",
    };
  }

  return {
    label: "Precisa de reforço",
    className: "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300",
    barClassName: "bg-rose-500",
  };
}

export function AlunoDesempenho() {
  const { data: performance, loading, error } = useApi(() => studentPortalService.getPerformance());

  const subjects = [...(performance?.subjectPerformance || [])].sort(
    (first, second) => second.average - first.average,
  );
  const subjectsNeedingAttention = subjects.filter((subject) => subject.average < 7);
  const strongestSubject = subjects[0];
  const averagePercent = Math.min(Math.max((performance?.averageGrade || 0) * 10, 0), 100);

  return (
    <div className="space-y-6">
      <header>
        <div className="flex items-start gap-3">
          <div className="rounded-xl bg-[#1E5AA8] p-3 text-white shadow-sm">
            <BarChart3 className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-[#0A2463] dark:text-white">Meu Desempenho</h1>
            <p className="mt-1 text-gray-600 dark:text-gray-300">
              Um resumo simples para acompanhar seus avanços e saber onde concentrar os estudos.
            </p>
          </div>
        </div>
      </header>

      {loading && (
        <div className="flex items-center gap-2 rounded-2xl bg-white p-6 text-gray-600 shadow-sm dark:bg-gray-800 dark:text-gray-300">
          <Loader2 className="h-5 w-5 animate-spin text-[#1E5AA8]" />
          Carregando seu desempenho...
        </div>
      )}

      {error && (
        <div className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-5 text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-300">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
          <div>
            <p className="font-semibold">Não foi possível carregar o desempenho</p>
            <p className="mt-1 text-sm">{error}</p>
          </div>
        </div>
      )}

      {!loading && !error && performance && (
        <>
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-2xl bg-gradient-to-br from-[#0A2463] to-[#1E5AA8] p-5 text-white shadow-sm">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-blue-100">Média geral</p>
                <Award className="h-5 w-5 text-blue-200" />
              </div>
              <p className="mt-4 text-4xl font-bold">{formatGrade(performance.averageGrade)}</p>
              <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/20">
                <div className="h-full rounded-full bg-[#4FC3F7]" style={{ width: `${averagePercent}%` }} />
              </div>
              <p className="mt-2 text-xs text-blue-100">de 10 pontos possíveis</p>
            </div>

            <div className="rounded-2xl bg-white p-5 shadow-sm dark:bg-gray-800">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Frequência</p>
                <CheckCircle2 className="h-5 w-5 text-emerald-500" />
              </div>
              <p className="mt-4 text-4xl font-bold text-[#0A2463] dark:text-white">{performance.attendanceRate}%</p>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                {performance.attendedClasses} de {performance.totalClasses} registros presentes
              </p>
            </div>

            <div className="rounded-2xl bg-white p-5 shadow-sm dark:bg-gray-800">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Atividades</p>
                <ClipboardCheck className="h-5 w-5 text-[#1E5AA8]" />
              </div>
              <p className="mt-4 text-4xl font-bold text-[#0A2463] dark:text-white">{performance.completedActivities}</p>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                de {performance.totalActivities} atividades registradas
              </p>
            </div>

            <div className="rounded-2xl bg-white p-5 shadow-sm dark:bg-gray-800">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Destaque</p>
                <TrendingUp className="h-5 w-5 text-amber-500" />
              </div>
              <p className="mt-4 truncate text-xl font-bold text-[#0A2463] dark:text-white">
                {strongestSubject?.subject || "Ainda sem dados"}
              </p>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                {strongestSubject ? `Média ${formatGrade(strongestSubject.average)}` : "Registre notas para acompanhar"}
              </p>
            </div>
          </section>

          {subjects.length === 0 ? (
            <section className="rounded-2xl bg-white p-8 text-center shadow-sm dark:bg-gray-800">
              <Target className="mx-auto h-12 w-12 text-gray-400" />
              <h2 className="mt-4 text-lg font-semibold text-[#0A2463] dark:text-white">Ainda não há dados suficientes</h2>
              <p className="mx-auto mt-2 max-w-xl text-gray-600 dark:text-gray-300">
                Quando suas primeiras notas forem registradas, esta tela mostrará sua evolução por disciplina.
              </p>
            </section>
          ) : (
            <div className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
              <section className="rounded-2xl bg-white p-5 shadow-sm dark:bg-gray-800">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <h2 className="text-lg font-semibold text-[#0A2463] dark:text-white">Desempenho por disciplina</h2>
                    <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Veja onde você está avançando mais.</p>
                  </div>
                  <BarChart3 className="h-5 w-5 text-[#1E5AA8]" />
                </div>

                <div className="mt-6 space-y-5">
                  {subjects.map((subject) => {
                    const status = getSubjectStatus(subject.average);
                    const subjectPercent = Math.min(Math.max(subject.average * 10, 0), 100);
                    return (
                      <div key={subject.subject}>
                        <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                          <span className="font-semibold text-gray-700 dark:text-gray-200">{subject.subject}</span>
                          <div className="flex items-center gap-2">
                            <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${status.className}`}>{status.label}</span>
                            <span className="font-bold text-[#0A2463] dark:text-white">{formatGrade(subject.average)}</span>
                          </div>
                        </div>
                        <div className="mt-2 h-3 overflow-hidden rounded-full bg-gray-100 dark:bg-gray-700">
                          <div className={`h-full rounded-full transition-all ${status.barClassName}`} style={{ width: `${subjectPercent}%` }} />
                        </div>
                        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                          {subject.count} {subject.count === 1 ? "nota registrada" : "notas registradas"}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </section>

              <section className="rounded-2xl bg-white p-5 shadow-sm dark:bg-gray-800">
                <div className="flex items-center gap-3">
                  <div className="rounded-xl bg-amber-100 p-2.5 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
                    <Target className="h-5 w-5" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-[#0A2463] dark:text-white">Foco de melhoria</h2>
                    <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Conteúdos para revisar com calma.</p>
                  </div>
                </div>

                {subjectsNeedingAttention.length > 0 ? (
                  <div className="mt-5 space-y-3">
                    {subjectsNeedingAttention.map((subject) => (
                      <div key={subject.subject} className="rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-900/50 dark:bg-amber-950/20">
                        <div className="flex items-center justify-between gap-3">
                          <p className="font-semibold text-amber-900 dark:text-amber-200">{subject.subject}</p>
                          <span className="text-lg font-bold text-amber-700 dark:text-amber-300">{formatGrade(subject.average)}</span>
                        </div>
                        <p className="mt-1 text-sm text-amber-800/80 dark:text-amber-200/80">
                          Revise os conteúdos desta disciplina e peça ajuda quando necessário.
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="mt-5 rounded-xl bg-emerald-50 p-4 text-emerald-800 dark:bg-emerald-950/20 dark:text-emerald-200">
                    <p className="font-semibold">Você está indo muito bem.</p>
                    <p className="mt-1 text-sm">Continue mantendo uma rotina de estudos e participação.</p>
                  </div>
                )}
              </section>
            </div>
          )}

          <section className="rounded-2xl border border-blue-100 bg-blue-50 p-5 dark:border-blue-900/40 dark:bg-blue-950/20">
            <div className="flex items-start gap-3">
              <Target className="mt-0.5 h-5 w-5 shrink-0 text-[#1E5AA8] dark:text-blue-300" />
              <div>
                <h2 className="font-semibold text-[#0A2463] dark:text-blue-100">Como usar este resumo</h2>
                <p className="mt-1 text-sm leading-6 text-blue-900/80 dark:text-blue-200/80">
                  Use os pontos de atenção para escolher o próximo assunto de estudo. Acompanhar esta tela com seus pais ou professores ajuda a transformar cada nota em um próximo passo claro.
                </p>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
