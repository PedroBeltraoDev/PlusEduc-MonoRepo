import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { ArrowLeft, CheckCircle2, Clock3, Download, Loader2, Send, XCircle } from "lucide-react";
import { toast } from "sonner";
import { useApi } from "@/hooks/useApi";
import { studentPortalService } from "@/services";
import type { QuestionAnswer, QuestionResult } from "@/types";

function optionLabel(index: number) {
  return String.fromCharCode(65 + index);
}

function isDiscursiveQuestion(questionType: string) {
  return ["DISCURSIVA", "DISSERTATIVA", "ABERTA", "OPEN_ENDED"].includes(questionType.trim().toUpperCase());
}

export function AlunoAtividadeDetalhe() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const { data: activity, loading, error, refetch } = useApi(
    () => studentPortalService.getActivity(id!),
    [id]
  );

  const handleSelect = (questionIndex: number, value: string) => {
    setAnswers((prev) => ({ ...prev, [questionIndex]: value }));
  };

  const handleSubmit = async () => {
    if (!id || !activity?.questions?.length) return;

    const payload: QuestionAnswer[] = activity.questions.map((q) => ({
      questionIndex: q.questionIndex,
      selectedAnswer: answers[q.questionIndex] ?? "",
    }));

    if (payload.some((a) => !a.selectedAnswer?.trim())) {
      toast.error("Preencha todas as questões antes de enviar.");
      return;
    }

    try {
      setSubmitting(true);
      await studentPortalService.submitActivity(id, payload);
      toast.success("Atividade enviada!");
      refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao enviar");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!id || !activity) return;
    try {
      setDownloading(true);
      await studentPortalService.downloadActivityPdf(id, activity.title);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao baixar PDF");
    } finally {
      setDownloading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-gray-500">
        <Loader2 className="h-5 w-5 animate-spin" />
        Carregando...
      </div>
    );
  }

  if (error || !activity) {
    return (
      <div className="space-y-4">
        <Link to="/aluno/atividades" className="inline-flex items-center gap-2 text-[#1E5AA8]">
          <ArrowLeft className="h-4 w-4" />
          Voltar
        </Link>
        <p className="text-red-600">{error || "Atividade não encontrada"}</p>
      </div>
    );
  }

  if (activity.submitted) {
    return (
      <div className="space-y-6">
        <button
          onClick={() => navigate("/aluno/atividades?tab=feitas")}
          className="inline-flex items-center gap-2 text-[#1E5AA8] hover:underline"
        >
          <ArrowLeft className="h-4 w-4" />
          Voltar às atividades feitas
        </button>

        <div className="rounded-2xl bg-white p-6 shadow-sm dark:bg-gray-800">
          <h1 className="text-2xl font-bold text-[#0A2463] dark:text-white">{activity.title}</h1>
          <p className="mt-2 text-gray-600 dark:text-gray-300">
            {activity.pendingCount ? `${activity.correctCount}/${activity.totalQuestions} acertos (${activity.scorePercent}%) • ${activity.pendingCount} aguardando correção` : `${activity.subject} • ${activity.correctCount}/${activity.totalQuestions} acertos (${activity.scorePercent}%)`}
          </p>
        </div>

        <div className="space-y-4">
          {activity.results?.map((result) => (
            <ResultCard key={result.questionIndex} result={result} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Link to="/aluno/atividades" className="inline-flex items-center gap-2 text-[#1E5AA8] hover:underline">
        <ArrowLeft className="h-4 w-4" />
        Voltar às atividades
      </Link>

      <div className="rounded-2xl bg-white p-6 shadow-sm dark:bg-gray-800">
        <h1 className="text-2xl font-bold text-[#0A2463] dark:text-white">{activity.title}</h1>
        <p className="mt-2 text-gray-600 dark:text-gray-300">
          {activity.subject} • {activity.topic} • {activity.difficultyLevel}
        </p>
        <button
          onClick={handleDownloadPdf}
          disabled={downloading}
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-[#1E5AA8] px-4 py-2 text-white hover:bg-[#0A2463] disabled:opacity-60"
        >
          {downloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
          Baixar PDF
        </button>
      </div>

      <div className="space-y-4">
        {activity.questions?.map((question, idx) => (
          <div key={question.questionIndex} className="rounded-2xl bg-white p-6 shadow-sm dark:bg-gray-800">
            <h2 className="font-semibold text-[#0A2463] dark:text-white">
              Questão {idx + 1}
            </h2>
            <p className="mt-2 text-gray-700 dark:text-gray-300">{question.questionText}</p>

            <div className="mt-4">
              {isDiscursiveQuestion(question.questionType) ? (
                <textarea
                  value={answers[question.questionIndex] ?? ""}
                  onChange={(event) => handleSelect(question.questionIndex, event.target.value)}
                  rows={5}
                  placeholder="Digite sua resposta..."
                  className="w-full resize-y rounded-lg border border-gray-300 bg-white p-4 text-gray-900 outline-none transition focus:border-[#1E5AA8] focus:ring-2 focus:ring-[#1E5AA8]/30 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                  aria-label={`Resposta da questão ${idx + 1}`}
                />
              ) : (
                <div className="space-y-2">
                  {question.options?.map((option, optionIndex) => {
                    const label = optionLabel(optionIndex);
                    const selected = answers[question.questionIndex] === option;
                    return (
                      <label
                        key={optionIndex}
                        className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition ${
                          selected
                            ? "border-[#1E5AA8] bg-blue-50 dark:bg-blue-900/20"
                            : "border-gray-200 hover:border-gray-300 dark:border-gray-600"
                        }`}
                      >
                        <input
                          type="radio"
                          name={`question-${question.questionIndex}`}
                          checked={selected}
                          onChange={() => handleSelect(question.questionIndex, option)}
                          className="h-4 w-4 accent-[#1E5AA8]"
                        />
                        <span className="font-medium text-[#1E5AA8]">{label})</span>
                        <span className="text-gray-700 dark:text-gray-300">{option}</span>
                      </label>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={handleSubmit}
        disabled={submitting}
        className="inline-flex items-center gap-2 rounded-lg bg-[#4CAF50] px-6 py-3 font-semibold text-white hover:bg-green-700 disabled:opacity-60"
      >
        {submitting ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
        Enviar atividade
      </button>
    </div>
  );
}

function ResultCard({ result }: { result: QuestionResult }) {
  const pending = result.reviewStatus === "PENDING";
  const reviewed = result.reviewStatus === "REVIEWED";
  const cardClass = pending
    ? "border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-900/20"
    : result.correct
      ? "border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/20"
      : "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20";

  return (
    <div className={`rounded-2xl border p-5 ${cardClass}`}>
      <div className="flex items-start gap-2">
        {pending ? (
          <Clock3 className="h-5 w-5 shrink-0 text-amber-600" />
        ) : result.correct ? (
          <CheckCircle2 className="h-5 w-5 shrink-0 text-green-600" />
        ) : (
          <XCircle className="h-5 w-5 shrink-0 text-red-600" />
        )}
        <div className="flex-1">
          <p className="font-semibold text-[#0A2463] dark:text-white">
            Questão {result.questionIndex + 1} — {pending ? "Aguardando correção" : result.correct ? "Correta" : "Incorreta"}
          </p>
          <p className="mt-1 text-gray-700 dark:text-gray-300">{result.questionText}</p>
          <p className="mt-3 text-sm">
            <span className="font-medium">Sua resposta:</span> {result.selectedAnswer}
          </p>
          {!pending && !result.correct && result.correctAnswer && (
            <p className="mt-1 text-sm text-green-700 dark:text-green-300">
              <span className="font-medium">Resposta correta:</span> {result.correctAnswer}
            </p>
          )}
          {reviewed && result.teacherFeedback ? (
            <div className="mt-3 rounded-lg bg-white/70 p-3 text-sm text-gray-700 dark:bg-gray-800/60 dark:text-gray-200">
              <span className="font-medium">Feedback do professor:</span> {result.teacherFeedback}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
