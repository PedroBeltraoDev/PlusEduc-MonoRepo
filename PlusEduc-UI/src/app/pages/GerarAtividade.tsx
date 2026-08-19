import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, BookOpen, Brain, Download, Loader2, Send, Sparkles, Users, Wand2 } from "lucide-react";
import { Link } from "react-router";
import { toast, Toaster } from "sonner";
import { activitiesService, classroomsService, studentsService, subjectTopicsService, subjectsService } from "@/services";
import type { Activity, Classroom, GenerateActivityRequest, GeneratedQuestion, Student, Subject, SubjectTopic } from "@/types";

const difficultyOptions = [
  { label: "Fácil", value: "FACIL" },
  { label: "Médio", value: "MEDIO" },
  { label: "Difícil", value: "DIFICIL" },
];

const formatOptions = [
  { label: "Múltipla escolha", value: "MULTIPLA_ESCOLHA" },
  { label: "Discursiva", value: "DISCURSIVA" },
  { label: "Misto", value: "MISTO" },
];

const normalizeSubjectKey = (value: string) =>
  value.trim().toLocaleLowerCase("pt-BR").normalize("NFD").replace(/[\u0300-\u036f]/g, "");

const adaptationOptions = [
  { label: "Dislexia", value: "Dislexia" },
  { label: "Baixa Visão", value: "Baixa Visão" },
  { label: "TDAH", value: "TDAH" },
];

function getPreviewClassNames(adaptations: string[]) {
  const lowVision = adaptations.some(item => item.toLowerCase().includes("baixa"));
  const dyslexia = adaptations.some(item => item.toLowerCase().includes("dislexia"));
  const adhd = adaptations.some(item => item.toLowerCase().includes("tdah"));

  return {
    wrapper: [
      "bg-white dark:bg-gray-700 border-2 border-gray-200 dark:border-gray-600 rounded-lg p-4 sm:p-8 min-h-[500px] sm:min-h-[600px] shadow-inner transition-colors overflow-hidden",
      lowVision ? "text-[1.1rem]" : "",
      adhd ? "tracking-[0.01em]" : "",
    ].join(" "),
    questionText: [
      "text-gray-800 dark:text-gray-200 mb-4 break-words",
      adhd ? "leading-8" : "leading-relaxed",
      dyslexia ? "max-w-2xl" : "",
      lowVision ? "text-[1.05rem]" : "",
    ].join(" "),
    option: [
      "flex items-start gap-2 sm:gap-3 p-3 rounded-lg min-w-0 break-words hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors",
      adhd ? "mb-3" : "",
      lowVision ? "text-[1rem]" : "",
    ].join(" "),
  };
}

function renderQuestionTypeLabel(type: string) {
  switch (type) {
    case "MULTIPLA_ESCOLHA":
      return "Múltipla escolha";
    case "VERDADEIRO_FALSO":
      return "Verdadeiro ou falso";
    case "DISCURSIVA":
      return "Discursiva";
    default:
      return type;
  }
}

export function GerarAtividade() {
  const [classrooms, setClassrooms] = useState<Classroom[]>([]);
  const [classroomStudents, setClassroomStudents] = useState<Student[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [subjectTopics, setSubjectTopics] = useState<SubjectTopic[]>([]);
  const [loadingClassrooms, setLoadingClassrooms] = useState(true);
  const [loadingSubjects, setLoadingSubjects] = useState(true);
  const [loadingSubjectTopics, setLoadingSubjectTopics] = useState(true);
  const [loadingStudents, setLoadingStudents] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [generatedActivity, setGeneratedActivity] = useState<Activity | null>(null);
  const [generatedActivities, setGeneratedActivities] = useState<Activity[]>([]);
  const [deliveryMode, setDeliveryMode] = useState<"classroom" | "students">("classroom");
  const [selectedStudentIds, setSelectedStudentIds] = useState<string[]>([]);

  const [form, setForm] = useState<GenerateActivityRequest>({
    classroomId: "",
    subject: "",
    topic: "",
    difficultyLevel: "MEDIO",
    questionsCount: 5,
    format: "MISTO",
    disabilityAdaptations: [],
    additionalInstructions: "",
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

  useEffect(() => {
    async function loadStudents() {
      if (!form.classroomId) {
        setClassroomStudents([]);
        setSelectedStudentIds([]);
        return;
      }

      try {
        setLoadingStudents(true);
        const students = await studentsService.getStudentsByClass(form.classroomId);
        setClassroomStudents(students);
        setSelectedStudentIds(prev => prev.filter(id => students.some(student => student.id === id)));
      } catch (error) {
        console.error(error);
        setClassroomStudents([]);
        setSelectedStudentIds([]);
        toast.error("Não foi possível carregar os alunos da turma.");
      } finally {
        setLoadingStudents(false);
      }
    }

    loadStudents();
  }, [form.classroomId]);

  const previewAdaptations = form.disabilityAdaptations ?? [];
  const previewClasses = getPreviewClassNames(previewAdaptations);

  const handleChange = <K extends keyof GenerateActivityRequest>(field: K, value: GenerateActivityRequest[K]) => {
    setForm(prev => ({ ...prev, [field]: value }));
  };

  const toggleAdaptation = (value: string) => {
    const current = form.disabilityAdaptations ?? [];
    const next = current.includes(value)
      ? current.filter(item => item !== value)
      : [...current, value];
    handleChange("disabilityAdaptations", next);
  };

  const toggleStudent = (studentId: string) => {
    setSelectedStudentIds(prev =>
      prev.includes(studentId)
        ? prev.filter(id => id !== studentId)
        : [...prev, studentId],
    );
  };

  const handleGenerate = async () => {
    if (!form.classroomId || !form.subject.trim() || !form.topic.trim()) {
      toast.error("Preencha turma, matéria e tópico antes de gerar.");
      return;
    }

    if (deliveryMode === "students" && selectedStudentIds.length === 0) {
      toast.error("Selecione pelo menos um aluno para enviar a atividade.");
      return;
    }

    try {
      setSubmitting(true);
      const payload = {
        ...form,
        subject: form.subject.trim(),
        topic: form.topic.trim(),
        additionalInstructions: form.additionalInstructions?.trim() || undefined,
      };

      const activities = deliveryMode === "students"
        ? await Promise.all(
            selectedStudentIds.map(studentId =>
              activitiesService.generateActivity({
                ...payload,
                studentId,
              }),
            ),
          )
        : [await activitiesService.generateActivity(payload)];

      setGeneratedActivities(activities);
      setGeneratedActivity(activities[0] ?? null);
      const usedDemoFallback = activities.some(activity =>
        activity.aiProvider?.trim().toLowerCase().includes("demo"),
      );
      if (usedDemoFallback) {
        toast.warning(
          "Aviso: a API do Gemini não respondeu ou atingiu o limite de tokens. A atividade foi gerada em modo de demonstração.",
        );
      } else {
        toast.success(
          deliveryMode === "students"
            ? `Atividade enviada para ${activities.length} aluno(s).`
            : "Atividade enviada para a turma.",
        );
      }
    } catch (error) {
      console.error(error);
      const errorMessage = error instanceof Error ? error.message : "Falha ao gerar atividade.";
      const normalizedError = errorMessage.toLowerCase();
      const geminiUnavailable = ["gemini", "token", "cota", "quota", "limite", "fetch", "servidor"].some(
        term => normalizedError.includes(term),
      );
      if (geminiUnavailable) {
        toast.warning(
          "Aviso: a API do Gemini não respondeu ou atingiu o limite de tokens. Tente novamente mais tarde.",
        );
      } else {
        toast.error(errorMessage);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleDownload = async () => {
    if (!generatedActivity) {
      return;
    }

    try {
      await activitiesService.downloadActivityPDF(generatedActivity.id, false);
      toast.success("PDF baixado com sucesso.");
    } catch (error) {
      console.error(error);
      toast.error("Não foi possível baixar o PDF.");
    }
  };

  const handleShare = () => {
    if (!generatedActivity) {
      return;
    }

    toast.success(
      deliveryMode === "students"
        ? `Atividade disponível para ${generatedActivities.length} aluno(s) selecionado(s).`
        : `Atividade disponível para ${selectedClassroom?.name || "a turma"}.`,
    );
  };

  const previewQuestions: GeneratedQuestion[] = generatedActivity?.questions ?? [];

  return (
    <>
      <Toaster position="top-right" />
      <div className="space-y-4 sm:space-y-6 min-w-0">
        <div>
          <Link
            to="/atividades"
            className="inline-flex items-center gap-2 text-sm text-[#1E5AA8] dark:text-[#7FC8F8] mb-3 hover:underline"
          >
            <ArrowLeft className="w-4 h-4" />
            Voltar para atividades
          </Link>
          <div className="flex items-start sm:items-center gap-3 mb-3">
            <div className="p-2 bg-[#1E5AA8] dark:bg-[#4FC3F7] rounded-lg">
              <Wand2 className="w-6 h-6 text-white dark:text-gray-900" />
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold break-words text-[#0A2463] dark:text-white">Gerar Nova Atividade</h1>
          </div>
          <p className="text-gray-600 dark:text-gray-300">
            Gere atividades com IA e aplique adaptações inclusivas reais no conteúdo e no PDF.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 sm:gap-6 min-w-0">
          <div className="lg:col-span-2 min-w-0">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 sm:p-6 space-y-5 transition-colors min-w-0">
              <div className="flex items-center gap-2 mb-4 pb-4 border-b border-gray-200 dark:border-gray-600">
                <Sparkles className="w-5 h-5 text-[#1E5AA8] dark:text-[#4FC3F7]" />
                <h2 className="text-lg font-bold text-[#0A2463] dark:text-white">Configuração da IA</h2>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Turma</label>
                <select
                  value={form.classroomId}
                  onChange={(event) => {
                    handleChange("classroomId", event.target.value);
                    setGeneratedActivity(null);
                    setGeneratedActivities([]);
                  }}
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

              <div className="pt-4 border-t border-gray-200 dark:border-gray-600">
                <div className="flex items-center gap-2 mb-3">
                  <Users className="w-5 h-5 text-[#1E5AA8] dark:text-[#4FC3F7]" />
                  <h3 className="text-sm font-bold text-[#0A2463] dark:text-white">Destino da atividade</h3>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setDeliveryMode("classroom");
                      setSelectedStudentIds([]);
                    }}
                    className={`rounded-lg border px-3 py-2 text-sm font-semibold transition-colors ${
                      deliveryMode === "classroom"
                        ? "border-[#1E5AA8] bg-[#1E5AA8] text-white"
                        : "border-gray-300 text-gray-700 hover:border-[#1E5AA8] dark:border-gray-600 dark:text-gray-200"
                    }`}
                  >
                    Turma inteira
                  </button>
                  <button
                    type="button"
                    onClick={() => setDeliveryMode("students")}
                    className={`rounded-lg border px-3 py-2 text-sm font-semibold transition-colors ${
                      deliveryMode === "students"
                        ? "border-[#1E5AA8] bg-[#1E5AA8] text-white"
                        : "border-gray-300 text-gray-700 hover:border-[#1E5AA8] dark:border-gray-600 dark:text-gray-200"
                    }`}
                  >
                    Alunos específicos
                  </button>
                </div>

                {deliveryMode === "students" ? (
                  <div className="mt-4 rounded-lg border border-gray-200 dark:border-gray-600">
                    {loadingStudents ? (
                      <div className="flex items-center gap-2 p-4 text-sm text-gray-500 dark:text-gray-400">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Carregando alunos...
                      </div>
                    ) : classroomStudents.length === 0 ? (
                      <p className="p-4 text-sm text-gray-500 dark:text-gray-400">Esta turma ainda não tem alunos cadastrados.</p>
                    ) : (
                      <div className="max-h-56 overflow-y-auto divide-y divide-gray-200 dark:divide-gray-600">
                        {classroomStudents.map(student => (
                          <label
                            key={student.id}
                            className="flex cursor-pointer items-center gap-3 p-3 hover:bg-gray-50 dark:hover:bg-gray-700"
                          >
                            <input
                              type="checkbox"
                              checked={selectedStudentIds.includes(student.id)}
                              onChange={() => toggleStudent(student.id)}
                              className="h-5 w-5 rounded border-gray-300 text-[#1E5AA8] focus:ring-[#1E5AA8]"
                            />
                            <span className="min-w-0">
                              <span className="block truncate text-sm font-semibold text-gray-800 dark:text-gray-100">{student.name}</span>
                              <span className="block truncate text-xs text-gray-500 dark:text-gray-400">{student.email}</span>
                            </span>
                          </label>
                        ))}
                      </div>
                    )}
                  </div>
                ) : null}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Matéria</label>
                <select
                  value={form.subject}
                  onChange={(event) => {
                    handleChange("subject", event.target.value);
                    handleChange("topic", "");
                    setGeneratedActivity(null);
                    setGeneratedActivities([]);
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
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Tópico/Assunto</label>
                <input
                  list="ai-activity-topics"
                  value={form.topic}
                  onChange={(event) => handleChange("topic", event.target.value)}
                  disabled={!form.subject || loadingSubjectTopics}
                  placeholder={form.subject ? (selectedSubjectTopics.length ? "Digite ou selecione um tópico" : "Digite o tópico da atividade") : "Escolha a matéria primeiro"}
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition disabled:cursor-not-allowed disabled:opacity-60"
                />
                <datalist id="ai-activity-topics">
                  {selectedSubjectTopics.map((topic) => (
                    <option key={topic} value={topic} />
                  ))}
                </datalist>
              </div>
              {subjects.length === 0 && !loadingSubjects ? (
                <Link to="/materias-topicos" className="text-sm font-semibold text-[#1E5AA8] hover:underline dark:text-[#7FC8F8]">
                  Cadastre matérias e tópicos para liberar a geração de atividades.
                </Link>
              ) : null}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Dificuldade</label>
                  <select
                    value={form.difficultyLevel}
                    onChange={(event) => handleChange("difficultyLevel", event.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition"
                  >
                    {difficultyOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Formato</label>
                  <select
                    value={form.format}
                    onChange={(event) => handleChange("format", event.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition"
                  >
                    {formatOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Quantidade de questões</label>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={form.questionsCount}
                  onChange={(event) => handleChange("questionsCount", Number(event.target.value))}
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition"
                />
              </div>

              <div className="pt-4 border-t border-gray-200 dark:border-gray-600">
                <div className="flex items-center gap-2 mb-4">
                  <Brain className="w-5 h-5 text-[#1E5AA8] dark:text-[#4FC3F7]" />
                  <h3 className="text-sm font-bold text-[#0A2463] dark:text-white">Adaptações Inclusivas</h3>
                </div>
                <div className="space-y-3">
                  {adaptationOptions.map((adaptation) => (
                    <label key={adaptation.value} className="flex items-center gap-3 cursor-pointer group">
                      <input
                        type="checkbox"
                        checked={previewAdaptations.includes(adaptation.value)}
                        onChange={() => toggleAdaptation(adaptation.value)}
                        className="w-5 h-5 text-[#1E5AA8] border-gray-300 dark:border-gray-600 rounded focus:ring-2 focus:ring-[#1E5AA8] cursor-pointer"
                      />
                      <span className="text-sm text-gray-700 dark:text-gray-300 group-hover:text-[#0A2463] dark:group-hover:text-white transition">
                        {adaptation.label}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Instruções adicionais</label>
                <textarea
                  value={form.additionalInstructions}
                  onChange={(event) => handleChange("additionalInstructions", event.target.value)}
                  rows={4}
                  placeholder="Ex: priorize interpretação visual, comandos curtos e conexão com o cotidiano."
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition resize-none"
                />
              </div>

              <button
                onClick={handleGenerate}
                disabled={submitting || loadingClassrooms || loadingSubjectTopics || subjectTopics.length === 0}
                className="w-full mt-2 bg-[#1E5AA8] hover:bg-[#0A2463] disabled:opacity-60 disabled:cursor-not-allowed text-white py-4 rounded-lg font-semibold flex items-center justify-center gap-2 shadow-md hover:shadow-lg transition-all"
              >
                {submitting ? <Loader2 className="w-5 h-5 animate-spin" /> : <Wand2 className="w-5 h-5" />}
                {submitting
                  ? "Gerando atividade..."
                  : deliveryMode === "students"
                    ? "Gerar e enviar aos alunos"
                    : "Gerar e enviar para a turma"}
              </button>
            </div>
          </div>

          <div className="lg:col-span-3 min-w-0">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 sm:p-6 space-y-5 transition-colors min-w-0">
              <div className="flex items-center gap-2 mb-4 pb-4 border-b border-gray-200 dark:border-gray-600">
                <BookOpen className="w-5 h-5 text-[#1E5AA8] dark:text-[#4FC3F7]" />
                <h2 className="text-lg font-bold text-[#0A2463] dark:text-white">Preview do Documento</h2>
              </div>

              <div className={previewClasses.wrapper}>
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between mb-6 sm:mb-8 pb-4 sm:pb-6 border-b-2 border-[#1E5AA8] dark:border-[#4FC3F7]">
                  <div>
                    <h3 className="text-xl sm:text-2xl font-bold break-words text-[#0A2463] dark:text-white mb-2">
                      {generatedActivity?.title || `Lista de Exercícios - ${form.subject || "Sua matéria"}`}
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-300">
                      Turma: {selectedClassroom?.name || "Selecione uma turma"} | Tópico: {form.topic || "Defina um tópico"}
                    </p>
                    {deliveryMode === "students" ? (
                      <p className="text-sm text-gray-600 dark:text-gray-300">
                        Destino: {selectedStudentIds.length} aluno(s) selecionado(s)
                      </p>
                    ) : null}
                    <p className="text-sm text-gray-600 dark:text-gray-300">
                      Dificuldade: {difficultyOptions.find(option => option.value === form.difficultyLevel)?.label || form.difficultyLevel}
                      {" | "}Formato: {formatOptions.find(option => option.value === form.format)?.label || form.format}
                    </p>
                  </div>
                  <div className="text-left sm:text-right">
                    <p className="text-xs font-bold text-[#0A2463] dark:text-white">PlusEduc</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {generatedActivity?.generatedByAi ? "Gerado com IA" : "Preview"}
                    </p>
                  </div>
                </div>

                {previewQuestions.length > 0 ? (
                  <div className="space-y-8">
                    {previewQuestions.map((question, index) => (
                      <div key={`${question.questionText}-${index}`}>
                        <div className="flex items-start gap-2 sm:gap-3 min-w-0">
                          <span className="shrink-0 font-bold text-[#1E5AA8] text-lg">{index + 1}.</span>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-2">
                              <span className="px-2 py-1 rounded-full bg-[#E3F2FD] text-[#0A2463] text-xs font-semibold">
                                {renderQuestionTypeLabel(question.questionType)}
                              </span>
                            </div>
                            <p className={previewClasses.questionText}>{question.questionText}</p>

                            {question.options?.length ? (
                              <div className="space-y-2 ml-0 sm:ml-4">
                                {question.options.map((option) => (
                                  <div key={option} className={previewClasses.option}>
                                    <span className="mt-1 text-[#1E5AA8]">○</span>
                                    <span className="min-w-0 break-words text-gray-700 dark:text-gray-300">{option}</span>
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-600 rounded-lg min-h-[90px] border border-gray-200 dark:border-gray-500 transition-colors">
                                <p className="text-xs text-gray-500 dark:text-gray-400 italic">Espaço para resposta do aluno</p>
                              </div>
                            )}

                            {question.explanation ? (
                              <div className="mt-4 rounded-lg bg-[#F3F7FC] dark:bg-gray-600/70 p-4 border border-[#D4E3F5] dark:border-gray-500">
                                <p className="text-xs uppercase tracking-wide text-[#1E5AA8] dark:text-[#7FC8F8] font-bold mb-2">
                                  Apoio pedagógico
                                </p>
                                <p className="text-sm text-gray-700 dark:text-gray-200">{question.explanation}</p>
                              </div>
                            ) : null}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-20 text-center">
                    <Wand2 className="w-16 h-16 text-gray-300 dark:text-gray-500 mb-4" />
                    <p className="text-gray-500 dark:text-gray-400 text-lg mb-2">
                      Configure os parâmetros e clique em "Gerar Atividade"
                    </p>
                    <p className="text-gray-400 dark:text-gray-500 text-sm max-w-md">
                      Se a IA falhar, o backend tentará reaproveitar questões anteriores do mesmo assunto já salvas no banco.
                    </p>
                  </div>
                )}
              </div>

              {generatedActivity ? (
                <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 pt-4">
                  <button
                    onClick={handleDownload}
                    className="w-full sm:flex-1 bg-[#1E5AA8] hover:bg-[#0A2463] text-white py-3 px-6 rounded-lg font-semibold flex items-center justify-center gap-2 shadow-md hover:shadow-lg transition-all"
                  >
                    <Download className="w-5 h-5" />
                    Baixar PDF
                  </button>
                  <button
                    onClick={handleShare}
                    className="w-full sm:flex-1 border-2 border-gray-300 dark:border-gray-600 hover:border-[#1E5AA8] dark:hover:border-[#4FC3F7] text-gray-700 dark:text-gray-300 hover:text-[#1E5AA8] dark:hover:text-[#4FC3F7] py-3 px-6 rounded-lg font-semibold flex items-center justify-center gap-2 transition-all"
                  >
                    <Send className="w-5 h-5" />
                    {deliveryMode === "students" ? "Confirmar envio aos alunos" : "Compartilhar com a turma"}
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
