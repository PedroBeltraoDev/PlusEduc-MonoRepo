import { useMemo, useState } from "react";
import { ArrowLeft, CheckCircle2, ChevronDown, ChevronUp, ClipboardCheck, Download, Info, Loader2, RotateCcw, Users, XCircle } from "lucide-react";
import { Link, useParams } from "react-router";
import { toast } from "sonner";
import { useApi } from "@/hooks/useApi";
import { activitiesService } from "@/services";

function optionLabel(index: number) {
  return String.fromCharCode(65 + index);
}

function normalizeAnswer(value: string) {
  return value.trim().toLowerCase().replace(/\s+/g, " ");
}

function answerText(value: string) {
  return normalizeAnswer(value).replace(/^[a-z]\s*[\)\]\.,:\-]\s*/, "");
}

type AnswerStatus = "correct" | "incorrect" | "unavailable";

function checkAnswer(selected: string, correct: string | null | undefined, options: string[]) {
  if (!selected || !correct) return "unavailable" as const;

  const normalizedSelected = normalizeAnswer(selected);
  const normalizedCorrect = normalizeAnswer(correct);
  const correctLetter = normalizedCorrect.match(/^([a-z])(?:\s*[\)\]\.,:\-]|$)/)?.[1];
  const selectedOptionIndex = options.findIndex((option) => normalizeAnswer(option) === normalizedSelected);

  if (correctLetter && selectedOptionIndex >= 0) {
    return optionLabel(selectedOptionIndex).toLowerCase() === correctLetter ? "correct" : "incorrect";
  }

  return answerText(selected) === answerText(correct) ? "correct" : "incorrect";
}

export function ProfessorAtividadeDetalhe() {
  const { id } = useParams<{ id: string }>();
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [graded, setGraded] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [expandedParticipantList, setExpandedParticipantList] = useState<"completed" | "pending" | null>(null);

  const { data: activity, loading, error } = useApi(
    () => activitiesService.getActivityById(id!),
    [id],
  );

  const questions = activity?.questions ?? [];
  const answeredCount = useMemo(
    () => questions.filter((_, index) => Boolean(answers[index]?.trim())).length,
    [answers, questions],
  );

  const answerResults = useMemo<Record<number, AnswerStatus>>(() => {
    if (!graded) return {};

    return questions.reduce<Record<number, AnswerStatus>>((results, question, index) => {
      results[index] = checkAnswer(answers[index] ?? "", question.correctAnswer, question.options ?? []);
      return results;
    }, {});
  }, [answers, graded, questions]);

  const correctCount = Object.values(answerResults).filter((status) => status === "correct").length;
  const incorrectCount = Object.values(answerResults).filter((status) => status === "incorrect").length;
  const unavailableCount = Object.values(answerResults).filter((status) => status === "unavailable").length;

  const handleSelect = (questionIndex: number, value: string) => {
    setGraded(false);
    setAnswers((previous) => ({ ...previous, [questionIndex]: value }));
  };

  const handleGrade = () => {
    if (answeredCount < questions.length) {
      toast.error("Responda todas as questões antes de conferir.");
      return;
    }

    setGraded(true);
    toast.success("Respostas conferidas localmente. Nada foi enviado ao servidor.");
  };

  const handleReset = () => {
    setAnswers({});
    setGraded(false);
    toast.success("Respostas locais limpas.");
  };

  const handleDownloadPdf = async () => {
    if (!activity) return;

    try {
      setDownloading(true);
      await activitiesService.downloadActivityPDF(activity.id, false);
      toast.success("PDF baixado com sucesso.");
    } catch (downloadError) {
      toast.error(downloadError instanceof Error ? downloadError.message : "Erro ao baixar PDF");
    } finally {
      setDownloading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
        <Loader2 className="h-5 w-5 animate-spin" />
        Carregando atividade...
      </div>
    );
  }

  if (error || !activity) {
    return (
      <div className="space-y-4">
        <Link to="/atividades" className="inline-flex items-center gap-2 text-[#1E5AA8] hover:underline">
          <ArrowLeft className="h-4 w-4" />
          Voltar para atividades
        </Link>
        <div className="rounded-xl border border-red-200 bg-red-50 p-5 text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">
          {error || "Atividade não encontrada."}
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link to="/atividades" className="inline-flex items-center gap-2 text-[#1E5AA8] hover:underline">
          <ArrowLeft className="h-4 w-4" />
          Voltar para atividades
        </Link>
        <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800 dark:bg-amber-900/30 dark:text-amber-200">
          Modo professor
        </span>
      </div>

      <section className="rounded-2xl bg-white p-5 shadow-sm dark:bg-gray-800 sm:p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <h1 className="break-words text-2xl font-bold text-[#0A2463] dark:text-white">{activity.title}</h1>
            <p className="mt-2 break-words text-gray-600 dark:text-gray-300">
              {activity.subject} • {activity.topic} • {activity.difficultyLevel}
            </p>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {activity.questionsCount} questão(ões) • {activity.classroomName || "Atividade da turma"}
            </p>
            {activity.participation ? (
              <p className="mt-2 text-sm font-semibold text-[#1E5AA8] dark:text-[#4FC3F7]">
                Participação: {activity.participation.completedStudents} de {activity.participation.totalStudents} alunos fizeram • {activity.participation.pendingStudents} ainda não fizeram
              </p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={handleDownloadPdf}
            disabled={downloading}
            className="inline-flex w-full shrink-0 items-center justify-center gap-2 rounded-lg border border-[#1E5AA8] px-4 py-2 text-sm font-semibold text-[#1E5AA8] transition-colors hover:bg-[#1E5AA8] hover:text-white disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
          >
            {downloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            Baixar PDF
          </button>
        </div>
      </section>

      {activity.participation ? (
        <section className="rounded-2xl bg-white p-5 shadow-sm dark:bg-gray-800 sm:p-6">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <Users className="h-5 w-5 text-[#1E5AA8] dark:text-[#4FC3F7]" />
                <h2 className="font-semibold text-[#0A2463] dark:text-white">Acompanhamento da turma</h2>
              </div>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
                A atividade está disponível para {activity.participation.totalStudents} aluno(s).
              </p>
            </div>
            <div className="flex flex-wrap gap-2 text-xs font-semibold">
              <span className="rounded-full bg-green-100 px-3 py-1 text-green-800 dark:bg-green-900/30 dark:text-green-200">
                {activity.participation.completedStudents} fizeram
              </span>
              <span className="rounded-full bg-amber-100 px-3 py-1 text-amber-800 dark:bg-amber-900/30 dark:text-amber-200">
                {activity.participation.pendingStudents} não fizeram
              </span>
            </div>
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {(["completed", "pending"] as const).map((listType) => {
              const isExpanded = expandedParticipantList === listType;
              const participants = activity.participation?.[listType] ?? [];
              const label = listType === "completed" ? "Alunos que fizeram" : "Alunos que não fizeram";
              return (
                <button
                  key={listType}
                  type="button"
                  onClick={() => setExpandedParticipantList(isExpanded ? null : listType)}
                  className="flex items-center justify-between rounded-xl border border-gray-200 bg-gray-50 p-4 text-left transition hover:border-[#1E5AA8] dark:border-gray-700 dark:bg-gray-700/50 dark:hover:border-[#4FC3F7]"
                  aria-expanded={isExpanded}
                >
                  <span>
                    <span className="block text-sm font-semibold text-[#0A2463] dark:text-white">{label}</span>
                    <span className="mt-1 block text-xs text-gray-500 dark:text-gray-300">{participants.length} aluno(s)</span>
                  </span>
                  {isExpanded ? <ChevronUp className="h-5 w-5 text-[#1E5AA8] dark:text-[#4FC3F7]" /> : <ChevronDown className="h-5 w-5 text-[#1E5AA8] dark:text-[#4FC3F7]" />}
                </button>
              );
            })}
          </div>

          {expandedParticipantList ? (
            <div className="mt-4 rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-700/50">
              {(() => {
                const participants = activity.participation?.[expandedParticipantList] ?? [];
                return participants.length ? (
                  <ul className="grid gap-2 sm:grid-cols-2">
                    {participants.map((participant) => (
                      <li key={participant.studentId} className="rounded-lg bg-white px-3 py-2 dark:bg-gray-800">
                        <p className="font-medium text-gray-800 dark:text-gray-100">{participant.studentName}</p>
                        {expandedParticipantList === "completed" && participant.submittedAt ? (
                          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Enviada em {new Date(participant.submittedAt).toLocaleString("pt-BR")}</p>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-gray-500 dark:text-gray-300">Nenhum aluno nesta lista.</p>
                );
              })()}
            </div>
          ) : null}
        </section>
      ) : null}

      <div className="flex items-start gap-3 rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-800 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-200">
        <Info className="mt-0.5 h-5 w-5 shrink-0" />
        <p>
          Você está no modo de professor. As respostas ficam apenas nesta tela para demonstração ou revisão em sala de aula e não serão enviadas nem finalizarão a atividade.
        </p>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-white p-4 shadow-sm dark:bg-gray-800">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-200">
          Respondidas localmente: <span className="font-bold text-[#1E5AA8]">{answeredCount}</span> de {questions.length}
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={handleGrade}
            disabled={answeredCount < questions.length || questions.length === 0}
            className="inline-flex items-center gap-2 rounded-lg bg-[#4CAF50] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <ClipboardCheck className="h-4 w-4" />
            Responder
          </button>
          <button
            type="button"
            onClick={handleReset}
            disabled={answeredCount === 0}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700 transition-colors hover:border-[#1E5AA8] hover:text-[#1E5AA8] disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:text-gray-200"
          >
            <RotateCcw className="h-4 w-4" />
            Limpar respostas
          </button>
        </div>
      </div>

      {graded ? (
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-800">
          <div className="flex flex-wrap items-center gap-3">
            <p className="font-semibold text-[#0A2463] dark:text-white">
              Resultado local: {correctCount} acerto(s) de {questions.length}
            </p>
            <span className="text-sm text-green-700 dark:text-green-300">{correctCount} certo(s)</span>
            <span className="text-sm text-red-700 dark:text-red-300">{incorrectCount} errado(s)</span>
            {unavailableCount > 0 ? (
              <span className="text-sm text-amber-700 dark:text-amber-300">{unavailableCount} para revisão manual</span>
            ) : null}
          </div>
        </div>
      ) : null}

      <div className="space-y-4">
        {questions.map((question, index) => {
          const options = question.options ?? [];
          const currentAnswer = answers[index] ?? "";
          const answerStatus = graded ? answerResults[index] : undefined;

          return (
            <section key={`${question.questionText}-${index}`} className="rounded-2xl bg-white p-5 shadow-sm dark:bg-gray-800 sm:p-6">
              <h2 className="font-semibold text-[#0A2463] dark:text-white">Questão {index + 1}</h2>
              <p className="mt-2 whitespace-pre-wrap break-words text-gray-700 dark:text-gray-300">{question.questionText}</p>

              {options.length > 0 ? (
                <div className="mt-4 space-y-2">
                  {options.map((option, optionIndex) => {
                    const selected = currentAnswer === option;
                    return (
                      <label
                        key={`${option}-${optionIndex}`}
                        className={`flex min-w-0 cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors ${
                          selected && answerStatus === "correct"
                            ? "border-green-500 bg-green-50 dark:bg-green-900/20"
                            : selected && answerStatus === "incorrect"
                              ? "border-red-500 bg-red-50 dark:bg-red-900/20"
                              : selected
                                ? "border-[#1E5AA8] bg-blue-50 dark:bg-blue-900/20"
                                : "border-gray-200 hover:border-gray-300 dark:border-gray-600"
                        }`}
                      >
                        <input
                          type="radio"
                          name={`question-${index}`}
                          checked={selected}
                          onChange={() => handleSelect(index, option)}
                          className="mt-1 h-4 w-4 shrink-0 accent-[#1E5AA8]"
                        />
                        <span className="shrink-0 font-medium text-[#1E5AA8]">{optionLabel(optionIndex)})</span>
                        <span className="min-w-0 break-words text-gray-700 dark:text-gray-300">{option}</span>
                      </label>
                    );
                  })}
                </div>
              ) : (
                <textarea
                  value={currentAnswer}
                  onChange={(event) => handleSelect(index, event.target.value)}
                  rows={4}
                  placeholder="Digite uma resposta para revisar em sala..."
                  className="mt-4 w-full resize-y rounded-lg border border-gray-300 bg-white px-4 py-3 text-gray-900 outline-none transition focus:border-[#1E5AA8] focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                />
              )}

              {graded && answerStatus ? (
                <div className={`mt-4 flex items-start gap-2 rounded-lg p-3 text-sm ${
                  answerStatus === "correct"
                    ? "bg-green-50 text-green-800 dark:bg-green-900/20 dark:text-green-200"
                    : answerStatus === "incorrect"
                      ? "bg-red-50 text-red-800 dark:bg-red-900/20 dark:text-red-200"
                      : "bg-amber-50 text-amber-800 dark:bg-amber-900/20 dark:text-amber-200"
                }`}>
                  {answerStatus === "correct" ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> : <XCircle className="mt-0.5 h-4 w-4 shrink-0" />}
                  <div>
                    <p className="font-semibold">
                      {answerStatus === "correct" ? "Você acertou." : answerStatus === "incorrect" ? "Você errou." : "Revisão manual necessária."}
                    </p>
                    {answerStatus === "incorrect" && question.correctAnswer ? (
                      <p className="mt-1">Resposta correta: {question.correctAnswer}</p>
                    ) : null}
                    {answerStatus === "unavailable" ? (
                      <p className="mt-1">Esta questão não possui gabarito automático disponível.</p>
                    ) : null}
                  </div>
                </div>
              ) : null}
            </section>
          );
        })}
      </div>
    </div>
  );
}
