import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, BookOpen, CheckCircle2, ClipboardPen, Loader2, Plus, Save, Trash2 } from "lucide-react";
import { Link, useNavigate } from "react-router";
import { toast, Toaster } from "sonner";
import { activitiesService, classroomsService, subjectTopicsService, subjectsService } from "@/services";
import type { Classroom, GeneratedQuestion, Subject, SubjectTopic } from "@/types";
import type { CreateActivityRequest } from "@/services/activities";

const difficultyOptions = [
  { label: "Fácil", value: "FACIL" },
  { label: "Médio", value: "MEDIO" },
  { label: "Difícil", value: "DIFICIL" },
];

const questionTypeOptions = [
  { label: "Múltipla escolha", value: "MULTIPLA_ESCOLHA" },
  { label: "Discursiva", value: "DISCURSIVA" },
  { label: "Verdadeiro ou Falso", value: "VERDADEIRO_FALSO" },
];

const normalizeSubjectKey = (value: string) =>
  value.trim().toLocaleLowerCase("pt-BR").normalize("NFD").replace(/[\u0300-\u036f]/g, "");

function createBlankQuestion(type: GeneratedQuestion["questionType"] = "MULTIPLA_ESCOLHA"): GeneratedQuestion {
  return {
    questionText: "",
    questionType: type,
    options: type === "DISCURSIVA" ? [] : ["", "", "", ""],
    correctAnswer: type === "DISCURSIVA" ? null : "A",
    explanation: "",
    difficultyLevel: "MEDIO",
  };
}

export function NovaAtividade() {
  const navigate = useNavigate();
  const [classrooms, setClassrooms] = useState<Classroom[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [subjectTopics, setSubjectTopics] = useState<SubjectTopic[]>([]);
  const [loadingClassrooms, setLoadingClassrooms] = useState(true);
  const [loadingSubjects, setLoadingSubjects] = useState(true);
  const [loadingSubjectTopics, setLoadingSubjectTopics] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const [form, setForm] = useState<CreateActivityRequest>({
    title: "",
    subject: "",
    topic: "",
    difficultyLevel: "MEDIO",
    questionsCount: 1,
    format: "MISTO",
    classroomId: "",
    studentId: "",
    disabilityAdaptations: [],
    questions: [createBlankQuestion()],
  });

  useEffect(() => {
    async function loadClassrooms() {
      try {
        const data = await classroomsService.getAllClassrooms();
        setClassrooms(data);
        setForm(prev => ({
          ...prev,
          classroomId: prev.classroomId || data[0]?.id || "",
        }));
      } catch (error) {
        console.error(error);
        toast.error("Não foi possível carregar as turmas.");
      } finally {
        setLoadingClassrooms(false);
      }
    }

    loadClassrooms();
  }, []);

  useEffect(() => {
    async function loadSubjectCatalog() {
      try {
        const [catalogTopics, catalogSubjects] = await Promise.all([
          subjectTopicsService.getAll(),
          subjectsService.getAll(),
        ]);
        const activeSubjects = catalogSubjects.filter((subject) => subject.active !== false);
        const activeSubjectKeys = new Set(activeSubjects.map((subject) => normalizeSubjectKey(subject.name)));
        setSubjects(activeSubjects);
        setSubjectTopics(catalogTopics.filter((item) => activeSubjectKeys.has(normalizeSubjectKey(item.subject))));
      } catch (error) {
        console.error(error);
        toast.error("Não foi possível carregar o catálogo de matérias e tópicos.");
      } finally {
        setLoadingSubjects(false);
        setLoadingSubjectTopics(false);
      }
    }

    loadSubjectCatalog();
  }, []);

  const selectedClassroom = useMemo(
    () => classrooms.find(classroom => classroom.id === form.classroomId) ?? null,
    [classrooms, form.classroomId],
  );

  const selectedSubjectTopics = useMemo(
    () => subjectTopics.find((item) => normalizeSubjectKey(item.subject) === normalizeSubjectKey(form.subject))?.topics ?? [],
    [subjectTopics, form.subject],
  );

  const handleFieldChange = <K extends keyof CreateActivityRequest>(field: K, value: CreateActivityRequest[K]) => {
    setForm(prev => ({ ...prev, [field]: value }));
  };

  const updateQuestion = (index: number, updater: (question: GeneratedQuestion) => GeneratedQuestion) => {
    setForm(prev => {
      const nextQuestions = [...(prev.questions ?? [])];
      nextQuestions[index] = updater(nextQuestions[index]);
      return {
        ...prev,
        questions: nextQuestions,
        questionsCount: nextQuestions.length,
      };
    });
  };

  const addQuestion = () => {
    setForm(prev => {
      const nextQuestions = [...(prev.questions ?? []), createBlankQuestion()];
      return {
        ...prev,
        questions: nextQuestions,
        questionsCount: nextQuestions.length,
      };
    });
  };

  const removeQuestion = (index: number) => {
    setForm(prev => {
      const nextQuestions = (prev.questions ?? []).filter((_, currentIndex) => currentIndex !== index);
      return {
        ...prev,
        questions: nextQuestions.length ? nextQuestions : [createBlankQuestion()],
        questionsCount: nextQuestions.length || 1,
      };
    });
  };

  const updateOption = (questionIndex: number, optionIndex: number, value: string) => {
    updateQuestion(questionIndex, (question) => {
      const nextOptions = [...question.options];
      nextOptions[optionIndex] = value;
      return { ...question, options: nextOptions };
    });
  };

  const handleQuestionTypeChange = (questionIndex: number, type: GeneratedQuestion["questionType"]) => {
    updateQuestion(questionIndex, (question) => ({
      ...question,
      questionType: type,
      options: type === "DISCURSIVA"
        ? []
        : type === "VERDADEIRO_FALSO"
          ? ["Verdadeiro", "Falso"]
          : question.options.length ? question.options : ["", "", "", ""],
      correctAnswer: type === "DISCURSIVA" ? null : type === "VERDADEIRO_FALSO" ? "Verdadeiro" : "A",
    }));
  };

  const validateForm = () => {
    if (!form.title.trim() || !form.subject.trim() || !form.topic.trim() || !form.classroomId) {
      toast.error("Preencha título, matéria, tópico e turma.");
      return false;
    }

    const questions = form.questions ?? [];
    for (const [index, question] of questions.entries()) {
      if (!question.questionText.trim()) {
        toast.error(`Preencha o enunciado da questão ${index + 1}.`);
        return false;
      }

      if (question.questionType !== "DISCURSIVA") {
        if (question.options.some(option => !option.trim())) {
          toast.error(`Complete todas as opções da questão ${index + 1}.`);
          return false;
        }
        if (!question.correctAnswer) {
          toast.error(`Defina a resposta correta da questão ${index + 1}.`);
          return false;
        }
      }
    }

    return true;
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      return;
    }

    try {
      setSubmitting(true);
      await activitiesService.createActivity({
        ...form,
        title: form.title.trim(),
        subject: form.subject.trim(),
        topic: form.topic.trim(),
        studentId: form.studentId?.trim() || undefined,
      });
      toast.success("Atividade manual criada com sucesso.");
      navigate("/atividades");
    } catch (error) {
      console.error(error);
      toast.error(error instanceof Error ? error.message : "Falha ao criar atividade.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <Toaster position="top-right" />
      <div className="space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <Link
              to="/atividades"
              className="inline-flex items-center gap-2 text-sm text-[#1E5AA8] dark:text-[#7FC8F8] mb-3 hover:underline"
            >
              <ArrowLeft className="w-4 h-4" />
              Voltar para atividades
            </Link>
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-[#1E5AA8] dark:bg-[#4FC3F7] rounded-lg">
                <ClipboardPen className="w-6 h-6 text-white dark:text-gray-900" />
              </div>
              <h1 className="text-3xl font-bold text-[#0A2463] dark:text-white">Nova Atividade Manual</h1>
            </div>
            <p className="text-gray-600 dark:text-gray-300">
              Monte sua própria atividade, escolha o tipo de questão e marque a resposta correta antes de salvar.
            </p>
          </div>

          <button
            onClick={handleSubmit}
            disabled={submitting || loadingClassrooms || loadingSubjects || subjects.length === 0}
            className="bg-[#1E5AA8] hover:bg-[#0A2463] disabled:opacity-60 disabled:cursor-not-allowed text-white px-5 py-3 rounded-lg font-semibold flex items-center gap-2 shadow-md hover:shadow-lg transition-all"
          >
            {submitting ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
            {submitting ? "Salvando..." : "Salvar Atividade"}
          </button>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
          <div className="xl:col-span-2 space-y-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 space-y-4 transition-colors">
              <h2 className="text-lg font-bold text-[#0A2463] dark:text-white">Dados principais</h2>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Título</label>
                <input
                  type="text"
                  value={form.title}
                  onChange={(event) => handleFieldChange("title", event.target.value)}
                  placeholder="Ex: Lista de exercícios - Vetores"
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Turma</label>
                  <select
                    value={form.classroomId}
                    onChange={(event) => handleFieldChange("classroomId", event.target.value)}
                    disabled={loadingClassrooms}
                    className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition"
                  >
                    {loadingClassrooms ? <option>Carregando...</option> : null}
                    {!loadingClassrooms && classrooms.length === 0 ? <option value="">Nenhuma turma encontrada</option> : null}
                    {classrooms.map((classroom) => (
                      <option key={classroom.id} value={classroom.id}>
                        {classroom.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Dificuldade</label>
                  <select
                    value={form.difficultyLevel}
                    onChange={(event) => handleFieldChange("difficultyLevel", event.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition"
                  >
                    {difficultyOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Matéria</label>
                  <select
                    value={form.subject}
                    onChange={(event) => {
                      handleFieldChange("subject", event.target.value);
                      handleFieldChange("topic", "");
                    }}
                    disabled={loadingSubjects || subjects.length === 0}
                    className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <option value="">
                      {loadingSubjects ? "Carregando..." : subjects.length ? "Selecione uma matéria" : "Cadastre uma matéria primeiro"}
                    </option>
                    {subjects.map((item) => (
                      <option key={item.id} value={item.name}>{item.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Tópico</label>
                  <input
                    list="manual-activity-topics"
                    value={form.topic}
                    onChange={(event) => handleFieldChange("topic", event.target.value)}
                    disabled={!form.subject || loadingSubjectTopics}
                    placeholder={form.subject ? (selectedSubjectTopics.length ? "Digite ou selecione um tópico" : "Digite o tópico da atividade") : "Escolha a matéria primeiro"}
                    className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition disabled:cursor-not-allowed disabled:opacity-60"
                  />
                  <datalist id="manual-activity-topics">
                    {selectedSubjectTopics.map((topic) => (
                      <option key={topic} value={topic} />
                    ))}
                  </datalist>
                </div>
              </div>
              {subjects.length === 0 && !loadingSubjects ? (
                <Link to="/materias-topicos" className="text-sm font-semibold text-[#1E5AA8] hover:underline dark:text-[#7FC8F8]">
                  Cadastre matérias e tópicos para liberar a criação de atividades.
                </Link>
              ) : null}
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 space-y-4 transition-colors">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-[#0A2463] dark:text-white">Questões</h2>
                <button
                  onClick={addQuestion}
                  className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-[#E3F2FD] hover:bg-[#D0E7FB] text-[#0A2463] font-semibold transition"
                >
                  <Plus className="w-4 h-4" />
                  Adicionar
                </button>
              </div>

              <div className="space-y-4">
                {(form.questions ?? []).map((question, questionIndex) => (
                  <div key={questionIndex} className="rounded-xl border border-gray-200 dark:border-gray-700 p-4 bg-gray-50 dark:bg-gray-900/30 space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-[#0A2463] dark:text-white">Questão {questionIndex + 1}</span>
                      <button
                        onClick={() => removeQuestion(questionIndex)}
                        className="text-red-500 hover:text-red-600 transition"
                        title="Remover questão"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Tipo</label>
                      <select
                        value={question.questionType}
                        onChange={(event) => handleQuestionTypeChange(questionIndex, event.target.value as GeneratedQuestion["questionType"])}
                        className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition"
                      >
                        {questionTypeOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Enunciado</label>
                      <textarea
                        value={question.questionText}
                        onChange={(event) => updateQuestion(questionIndex, current => ({ ...current, questionText: event.target.value }))}
                        rows={4}
                        placeholder="Digite o enunciado da questão"
                        className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition resize-none"
                      />
                    </div>

                    {question.questionType !== "DISCURSIVA" ? (
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-gray-700 dark:text-gray-200">Opções e resposta correta</span>
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            Marque a alternativa correta
                          </span>
                        </div>
                        {(question.options ?? []).map((option, optionIndex) => {
                          const label = question.questionType === "VERDADEIRO_FALSO"
                            ? option
                            : String.fromCharCode(65 + optionIndex);
                          const optionValue = question.questionType === "VERDADEIRO_FALSO" ? option : label;

                          return (
                            <div key={`${questionIndex}-${optionIndex}`} className="flex items-center gap-3">
                              <button
                                type="button"
                                onClick={() => updateQuestion(questionIndex, current => ({ ...current, correctAnswer: optionValue }))}
                                className={`flex h-6 w-6 items-center justify-center rounded-full border transition ${
                                  question.correctAnswer === optionValue
                                    ? "border-[#1E5AA8] bg-[#1E5AA8] text-white"
                                    : "border-gray-300 text-gray-400"
                                }`}
                                title="Definir como correta"
                              >
                                {question.correctAnswer === optionValue ? <CheckCircle2 className="w-4 h-4" /> : null}
                              </button>
                              <span className="w-7 text-sm font-semibold text-[#0A2463] dark:text-white">{label}</span>
                              {question.questionType === "VERDADEIRO_FALSO" ? (
                                <div className="flex-1 px-4 py-3 rounded-lg bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-800 dark:text-gray-100">
                                  {option}
                                </div>
                              ) : (
                                <input
                                  type="text"
                                  value={option}
                                  onChange={(event) => updateOption(questionIndex, optionIndex, event.target.value)}
                                  placeholder={`Opção ${label}`}
                                  className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition"
                                />
                              )}
                            </div>
                          );
                        })}
                      </div>
                    ) : null}

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Comentário pedagógico</label>
                      <textarea
                        value={question.explanation ?? ""}
                        onChange={(event) => updateQuestion(questionIndex, current => ({ ...current, explanation: event.target.value }))}
                        rows={3}
                        placeholder="Explique o objetivo da questão ou o raciocínio esperado"
                        className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition resize-none"
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="xl:col-span-3">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 space-y-5 transition-colors sticky top-6">
              <div className="flex items-center gap-2 mb-4 pb-4 border-b border-gray-200 dark:border-gray-600">
                <BookOpen className="w-5 h-5 text-[#1E5AA8] dark:text-[#4FC3F7]" />
                <h2 className="text-lg font-bold text-[#0A2463] dark:text-white">Preview da atividade</h2>
              </div>

              <div className="bg-white dark:bg-gray-700 border-2 border-gray-200 dark:border-gray-600 rounded-lg p-8 min-h-[650px] shadow-inner transition-colors">
                <div className="flex items-start justify-between mb-8 pb-6 border-b-2 border-[#1E5AA8] dark:border-[#4FC3F7]">
                  <div>
                    <h3 className="text-2xl font-bold text-[#0A2463] dark:text-white mb-2">
                      {form.title || "Sua nova atividade"}
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-300">
                      Turma: {selectedClassroom?.name || "Selecione uma turma"} | Tópico: {form.topic || "Defina um tópico"}
                    </p>
                    <p className="text-sm text-gray-600 dark:text-gray-300">
                      Matéria: {form.subject || "Defina uma matéria"} | Dificuldade: {difficultyOptions.find(option => option.value === form.difficultyLevel)?.label || form.difficultyLevel}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-bold text-[#0A2463] dark:text-white">PlusEduc</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Criação manual</p>
                  </div>
                </div>

                <div className="space-y-8">
                  {(form.questions ?? []).map((question, questionIndex) => (
                    <div key={`preview-${questionIndex}`}>
                      <div className="flex items-start gap-3">
                        <span className="font-bold text-[#1E5AA8] text-lg">{questionIndex + 1}.</span>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="px-2 py-1 rounded-full bg-[#E3F2FD] text-[#0A2463] text-xs font-semibold">
                              {questionTypeOptions.find(option => option.value === question.questionType)?.label || question.questionType}
                            </span>
                          </div>

                          <p className="text-gray-800 dark:text-gray-200 leading-relaxed mb-4">
                            {question.questionText || "O enunciado da questão aparecerá aqui."}
                          </p>

                          {question.questionType !== "DISCURSIVA" ? (
                            <div className="space-y-2 ml-4">
                              {(question.options ?? []).map((option, optionIndex) => {
                                const label = question.questionType === "VERDADEIRO_FALSO"
                                  ? option
                                  : `${String.fromCharCode(65 + optionIndex)})`;
                                const optionValue = question.questionType === "VERDADEIRO_FALSO" ? option : String.fromCharCode(65 + optionIndex);
                                const isCorrect = question.correctAnswer === optionValue;

                                return (
                                  <div
                                    key={`${questionIndex}-preview-option-${optionIndex}`}
                                    className={`flex items-start gap-3 p-3 rounded-lg border ${
                                      isCorrect
                                        ? "border-[#1E5AA8] bg-[#EAF4FF] dark:bg-[#1E3A5F]"
                                        : "border-transparent hover:bg-gray-50 dark:hover:bg-gray-600"
                                    }`}
                                  >
                                    <span className="mt-1 text-[#1E5AA8]">{isCorrect ? "✓" : "○"}</span>
                                    <span className="text-gray-700 dark:text-gray-300">
                                      {question.questionType === "VERDADEIRO_FALSO" ? label : `${label} ${option || "Opção em edição"}`}
                                    </span>
                                  </div>
                                );
                              })}
                            </div>
                          ) : (
                            <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-600 rounded-lg min-h-[120px] border border-gray-200 dark:border-gray-500 transition-colors">
                              <p className="text-xs text-gray-500 dark:text-gray-400 italic">Espaço para resposta do aluno</p>
                            </div>
                          )}

                          {question.explanation ? (
                            <div className="mt-4 rounded-lg bg-[#F3F7FC] dark:bg-gray-600/70 p-4 border border-[#D4E3F5] dark:border-gray-500">
                              <p className="text-xs uppercase tracking-wide text-[#1E5AA8] dark:text-[#7FC8F8] font-bold mb-2">
                                Comentário pedagógico
                              </p>
                              <p className="text-sm text-gray-700 dark:text-gray-200">{question.explanation}</p>
                            </div>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
