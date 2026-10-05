import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";
import {
  AlertTriangle,
  CalendarCheck,
  ClipboardCheck,
  Loader2,
  Pencil,
  Plus,
  Trash2,
  TrendingUp,
  Users,
} from "lucide-react";
import { toast } from "sonner";
import { classroomsService, gradesService } from "@/services";
import type { GradeClassroomSummary, GradeFormData, GradeStudentSummary } from "@/services";
import type { Classroom, GradeRecord } from "@/types";
import { ACTIVITY_TYPES, activityTypeLabel, formatDate } from "@/utils";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/app/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/app/components/ui/dialog";

const MIN_PASSING_GRADE = 6;
const MIN_ATTENDANCE = 75;
const SELECTABLE_TYPES = ["EXAM", "ASSIGNMENT", "EXERCISE", "PROJECT", "QUIZ", "PARTICIPATION"] as const;

type PresenceChoice = "present" | "absent" | "none";

interface GradeFormState {
  studentId: string;
  subject: string;
  activityType: string;
  grade: string;
  presence: PresenceChoice;
  date: string;
  observations: string;
}

const todayIso = () => new Date().toISOString().slice(0, 10);

const emptyForm = (studentId = "", subject = ""): GradeFormState => ({
  studentId,
  subject,
  activityType: "EXAM",
  grade: "",
  presence: "present",
  date: todayIso(),
  observations: "",
});

const presenceFromRecord = (attendance: boolean | null | undefined): PresenceChoice =>
  attendance === true ? "present" : attendance === false ? "absent" : "none";

const inputClass =
  "w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-gray-900 outline-none focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100";

function gradeTone(value: number, hasData: boolean) {
  if (!hasData) return "bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-300";
  return value >= MIN_PASSING_GRADE
    ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-200"
    : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-200";
}

export function Notas() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [classrooms, setClassrooms] = useState<Classroom[]>([]);
  const [loadingClassrooms, setLoadingClassrooms] = useState(true);
  const [classroomId, setClassroomId] = useState(searchParams.get("turma") ?? "");
  const [subject, setSubject] = useState("");
  const [summary, setSummary] = useState<GradeClassroomSummary | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(null);
  const [records, setRecords] = useState<GradeRecord[]>([]);
  const [loadingRecords, setLoadingRecords] = useState(false);

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<GradeRecord | null>(null);
  const [form, setForm] = useState<GradeFormState>(emptyForm());
  const [saving, setSaving] = useState(false);
  const [recordToDelete, setRecordToDelete] = useState<GradeRecord | null>(null);
  const [deleting, setDeleting] = useState(false);

  const selectedStudent: GradeStudentSummary | null =
    summary?.students.find((item) => item.studentId === selectedStudentId) ?? null;
  const classroom = useMemo(() => classrooms.find((item) => item.id === classroomId) ?? null, [classrooms, classroomId]);
  const subjectOptions = classroom?.subjects ?? [];

  useEffect(() => {
    classroomsService
      .getAllClassrooms()
      .then((items) => {
        const active = items.filter((item) => item.active !== false);
        setClassrooms(active);
        setClassroomId((current) => current || active[0]?.id || "");
      })
      .catch((error) => toast.error(error instanceof Error ? error.message : "Não foi possível carregar as turmas."))
      .finally(() => setLoadingClassrooms(false));
  }, []);

  const loadSummary = useCallback(async () => {
    if (!classroomId) return;
    try {
      setLoadingSummary(true);
      setSummaryError(null);
      setSummary(await gradesService.getClassroomSummary(classroomId, subject || undefined));
    } catch (error) {
      setSummary(null);
      setSummaryError(error instanceof Error ? error.message : "Não foi possível carregar as notas da turma.");
    } finally {
      setLoadingSummary(false);
    }
  }, [classroomId, subject]);

  const loadRecords = useCallback(
    async (studentId: string) => {
      try {
        setLoadingRecords(true);
        const items = await gradesService.getByStudent(studentId);
        setRecords(
          items.filter(
            (item) =>
              item.classroomId === classroomId &&
              (!subject || item.subject.trim().toLowerCase() === subject.trim().toLowerCase()),
          ),
        );
      } catch (error) {
        setRecords([]);
        toast.error(error instanceof Error ? error.message : "Não foi possível carregar os lançamentos do aluno.");
      } finally {
        setLoadingRecords(false);
      }
    },
    [classroomId, subject],
  );

  useEffect(() => {
    setSelectedStudentId(null);
    setRecords([]);
    void loadSummary();
  }, [loadSummary]);

  // Recarrega os lançamentos do aluno aberto sempre que o resumo muda (criar, editar ou excluir).
  useEffect(() => {
    if (selectedStudentId) void loadRecords(selectedStudentId);
  }, [selectedStudentId, summary, loadRecords]);

  const handleClassroomChange = (value: string) => {
    setClassroomId(value);
    setSubject("");
    setSearchParams(value ? { turma: value } : {}, { replace: true });
  };

  const openCreate = (studentId = "") => {
    setEditing(null);
    setForm(emptyForm(studentId, subject || subjectOptions[0] || ""));
    setFormOpen(true);
  };

  const openEdit = (record: GradeRecord) => {
    setEditing(record);
    setForm({
      studentId: record.studentId,
      subject: record.subject ?? "",
      activityType: record.activityType || "EXAM",
      grade: String(record.grade),
      presence: presenceFromRecord(record.attendance),
      date: (record.date || todayIso()).slice(0, 10),
      observations: record.observations ?? "",
    });
    setFormOpen(true);
  };

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault();
    const value = Number(form.grade.replace(",", "."));
    if (!form.studentId) return void toast.error("Selecione o aluno.");
    if (!form.subject.trim()) return void toast.error("Informe a disciplina.");
    if (form.grade.trim() === "" || Number.isNaN(value) || value < 0 || value > 10) {
      return void toast.error("A nota deve ser um número entre 0 e 10.");
    }
    if (!form.date) return void toast.error("Informe a data do lançamento.");

    const payload: GradeFormData = {
      studentId: form.studentId,
      classroomId,
      subject: form.subject.trim(),
      activityType: form.activityType,
      grade: Math.round(value * 10) / 10,
      attendance: form.presence === "none" ? null : form.presence === "present",
      observations: form.observations,
      date: `${form.date}T12:00:00Z`,
    };

    try {
      setSaving(true);
      if (editing) {
        await gradesService.update(editing.id, payload);
        toast.success("Lançamento atualizado.");
      } else {
        await gradesService.create(payload);
        toast.success("Nota e frequência lançadas.");
      }
      setFormOpen(false);
      setSelectedStudentId(form.studentId);
      await loadSummary();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Não foi possível salvar o lançamento.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!recordToDelete) return;
    try {
      setDeleting(true);
      await gradesService.delete(recordToDelete.id);
      toast.success("Lançamento excluído.");
      setRecordToDelete(null);
      await loadSummary();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Não foi possível excluir o lançamento.");
    } finally {
      setDeleting(false);
    }
  };

  const hasLaunches = (summary?.totalLaunches ?? 0) > 0;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="rounded-xl bg-[#1E5AA8] p-3 text-white shadow-sm">
            <ClipboardCheck className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-[#0A2463] dark:text-white">Notas e Frequência</h1>
            <p className="mt-1 text-gray-600 dark:text-gray-300">
              Lance notas e presenças por turma. O aluno enxerga tudo em “Minhas Notas” e “Desempenho”.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => openCreate(selectedStudentId ?? "")}
          disabled={!classroomId || !summary || summary.students.length === 0}
          className="inline-flex items-center gap-2 rounded-lg bg-[#1E5AA8] px-5 py-3 font-semibold text-white transition hover:bg-[#0A2463] disabled:cursor-not-allowed disabled:opacity-60"
        >
          <Plus className="h-4 w-4" />
          Lançar nota
        </button>
      </header>

      <section className="grid gap-3 rounded-2xl bg-white p-5 shadow-sm dark:bg-gray-800 md:grid-cols-2">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
          Turma
          <select
            value={classroomId}
            onChange={(event) => handleClassroomChange(event.target.value)}
            disabled={loadingClassrooms}
            className={`${inputClass} mt-1`}
          >
            {classrooms.length === 0 && <option value="">{loadingClassrooms ? "Carregando turmas..." : "Nenhuma turma"}</option>}
            {classrooms.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name} • {item.gradeLevel}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
          Disciplina
          <select value={subject} onChange={(event) => setSubject(event.target.value)} className={`${inputClass} mt-1`}>
            <option value="">Todas as disciplinas</option>
            {subjectOptions.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
      </section>

      {loadingSummary && !summary && (
        <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
          <Loader2 className="h-5 w-5 animate-spin" />
          Carregando notas da turma...
        </div>
      )}

      {summaryError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">
          {summaryError}
        </div>
      )}

      {summary && (
        <>
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Resumo da turma">
            {[
              { icon: Users, label: "Alunos", value: String(summary.studentsCount), tone: "text-[#1E5AA8]" },
              {
                icon: TrendingUp,
                label: "Média da turma",
                value: hasLaunches ? summary.averageGrade.toFixed(1) : "-",
                tone: hasLaunches && summary.averageGrade < MIN_PASSING_GRADE ? "text-red-600" : "text-emerald-600",
              },
              {
                icon: CalendarCheck,
                label: "Frequência da turma",
                value: hasLaunches ? `${summary.attendanceRate}%` : "-",
                tone: hasLaunches && summary.attendanceRate < MIN_ATTENDANCE ? "text-red-600" : "text-emerald-600",
              },
              { icon: ClipboardCheck, label: "Lançamentos", value: String(summary.totalLaunches), tone: "text-[#1E5AA8]" },
            ].map(({ icon: Icon, label, value, tone }) => (
              <div key={label} className="rounded-2xl bg-white p-5 shadow-sm dark:bg-gray-800">
                <div className="flex items-center gap-2 text-sm font-medium text-gray-500 dark:text-gray-400">
                  <Icon className="h-4 w-4" />
                  {label}
                </div>
                <p className={`mt-2 text-3xl font-bold ${tone}`}>{value}</p>
              </div>
            ))}
          </section>

          <section className="overflow-hidden rounded-2xl bg-white shadow-sm dark:bg-gray-800">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-200 px-5 py-4 dark:border-gray-700">
              <div>
                <h2 className="text-lg font-semibold text-[#0A2463] dark:text-white">{summary.classroomName}</h2>
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  Média mínima {MIN_PASSING_GRADE.toFixed(1)} • frequência mínima {MIN_ATTENDANCE}%.
                  {subject ? ` Filtrando por ${subject}.` : ""}
                </p>
              </div>
              <Link to="/turmas" className="text-sm font-semibold text-[#1E5AA8] hover:underline dark:text-[#4FC3F7]">
                Gerenciar alunos da turma
              </Link>
            </div>

            {summary.students.length === 0 ? (
              <div className="py-12 text-center text-gray-500 dark:text-gray-400">
                <Users className="mx-auto h-10 w-10" />
                <p className="mt-3 font-semibold">Esta turma ainda não tem alunos.</p>
                <p className="mt-1 text-sm">Matricule alunos em Turmas para lançar notas.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-left">
                  <thead className="bg-gray-50 dark:bg-gray-900/50">
                    <tr>
                      {["Aluno", "Média", "Frequência", "Lançamentos", ""].map((heading) => (
                        <th key={heading} className="px-4 py-3 text-sm font-semibold text-gray-600 dark:text-gray-300">
                          {heading}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                    {summary.students.map((row) => {
                      const hasData = row.launches > 0;
                      const lowAttendance = row.totalClasses > 0 && row.attendanceRate < MIN_ATTENDANCE;
                      const isSelected = selectedStudent?.studentId === row.studentId;
                      return (
                        <tr key={row.studentId} className={isSelected ? "bg-blue-50/60 dark:bg-blue-950/20" : undefined}>
                          <td className="px-4 py-3 font-medium text-[#0A2463] dark:text-white">{row.studentName}</td>
                          <td className="px-4 py-3">
                            <span className={`rounded-full px-3 py-1 text-sm font-semibold ${gradeTone(row.average, hasData)}`}>
                              {hasData ? row.average.toFixed(1) : "-"}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            {row.totalClasses > 0 ? (
                              <div className="min-w-[140px]">
                                <div className="flex items-center justify-between text-sm">
                                  <span className={lowAttendance ? "font-semibold text-red-600" : "font-semibold text-gray-700 dark:text-gray-200"}>
                                    {row.attendanceRate}%
                                  </span>
                                  <span className="text-xs text-gray-500 dark:text-gray-400">
                                    {row.attendedClasses}P • {row.absences}F
                                  </span>
                                </div>
                                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
                                  <div
                                    className={`h-full ${lowAttendance ? "bg-red-500" : "bg-emerald-500"}`}
                                    style={{ width: `${row.attendanceRate}%` }}
                                  />
                                </div>
                              </div>
                            ) : (
                              <span className="text-sm text-gray-400">Sem registro</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-gray-600 dark:text-gray-300">
                            {row.launches}
                            {hasData && row.average < MIN_PASSING_GRADE ? (
                              <AlertTriangle className="ml-2 inline h-4 w-4 text-amber-500" aria-label="Média abaixo do mínimo" />
                            ) : null}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <div className="flex justify-end gap-2">
                              <button
                                type="button"
                                onClick={() => setSelectedStudentId(isSelected ? null : row.studentId)}
                                className="rounded-lg border border-[#1E5AA8] px-3 py-1.5 text-sm font-semibold text-[#1E5AA8] transition hover:bg-[#1E5AA8] hover:text-white dark:border-[#4FC3F7] dark:text-[#4FC3F7]"
                              >
                                {isSelected ? "Ocultar" : "Ver lançamentos"}
                              </button>
                              <button
                                type="button"
                                onClick={() => openCreate(row.studentId)}
                                className="rounded-lg bg-[#1E5AA8] px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-[#0A2463]"
                              >
                                Lançar
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {selectedStudent && (
            <section className="rounded-2xl bg-white p-5 shadow-sm dark:bg-gray-800" aria-label="Lançamentos do aluno">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h2 className="text-lg font-semibold text-[#0A2463] dark:text-white">Lançamentos de {selectedStudent.studentName}</h2>
                  <p className="text-sm text-gray-600 dark:text-gray-300">
                    Edite ou exclua; a média e a frequência são recalculadas na hora.
                  </p>
                </div>
              </div>
              {loadingRecords ? (
                <div className="mt-4 flex items-center gap-2 text-gray-500 dark:text-gray-400">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Carregando lançamentos...
                </div>
              ) : records.length === 0 ? (
                <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">Nenhum lançamento para este filtro.</p>
              ) : (
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full min-w-[640px] text-left">
                    <thead className="bg-gray-50 dark:bg-gray-900/50">
                      <tr>
                        {["Data", "Disciplina", "Tipo", "Nota", "Presença", "Observações", ""].map((heading) => (
                          <th key={heading} className="px-3 py-2 text-sm font-semibold text-gray-600 dark:text-gray-300">
                            {heading}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                      {records.map((record) => (
                        <tr key={record.id}>
                          <td className="px-3 py-2 text-gray-600 dark:text-gray-300">{formatDate(record.date)}</td>
                          <td className="px-3 py-2 font-medium text-[#0A2463] dark:text-white">{record.subject || "-"}</td>
                          <td className="px-3 py-2 text-gray-600 dark:text-gray-300">
                            {activityTypeLabel(record.activityType)}
                            {record.activityId ? (
                              <span className="ml-2 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-800 dark:bg-blue-900/30 dark:text-blue-200">
                                Atividade online
                              </span>
                            ) : null}
                          </td>
                          <td className="px-3 py-2">
                            <span className={`rounded-full px-3 py-1 text-sm font-semibold ${gradeTone(record.grade, true)}`}>
                              {record.grade.toFixed(1)}
                            </span>
                          </td>
                          <td className="px-3 py-2 text-sm">
                            {record.attendance === true ? (
                              <span className="font-semibold text-emerald-700 dark:text-emerald-300">Presente</span>
                            ) : record.attendance === false ? (
                              <span className="font-semibold text-red-600">Faltou</span>
                            ) : (
                              <span className="text-gray-400">Não registrada</span>
                            )}
                          </td>
                          <td className="max-w-[220px] truncate px-3 py-2 text-sm text-gray-500 dark:text-gray-400" title={record.observations}>
                            {record.observations || "-"}
                          </td>
                          <td className="px-3 py-2 text-right">
                            <div className="flex justify-end gap-1">
                              <button
                                type="button"
                                onClick={() => openEdit(record)}
                                aria-label="Editar lançamento"
                                title="Editar"
                                className="rounded-md p-2 text-gray-500 transition hover:bg-gray-100 hover:text-[#1E5AA8] dark:hover:bg-gray-700"
                              >
                                <Pencil className="h-4 w-4" />
                              </button>
                              <button
                                type="button"
                                onClick={() => setRecordToDelete(record)}
                                aria-label="Excluir lançamento"
                                title="Excluir"
                                className="rounded-md p-2 text-gray-500 transition hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/40"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          )}
        </>
      )}

      <Dialog open={formOpen} onOpenChange={(open) => !saving && setFormOpen(open)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>{editing ? "Editar lançamento" : "Lançar nota e frequência"}</DialogTitle>
            <DialogDescription>
              {summary?.classroomName ? `Turma ${summary.classroomName}. ` : ""}A nota vai de 0 a 10; a presença é opcional.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSave} noValidate className="space-y-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
              Aluno
              <select
                value={form.studentId}
                onChange={(event) => setForm((current) => ({ ...current, studentId: event.target.value }))}
                disabled={editing !== null}
                className={`${inputClass} mt-1`}
              >
                <option value="">Selecione o aluno</option>
                {summary?.students.map((row) => (
                  <option key={row.studentId} value={row.studentId}>
                    {row.studentName}
                  </option>
                ))}
              </select>
            </label>

            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                Disciplina
                {subjectOptions.length > 0 ? (
                  <select
                    value={form.subject}
                    onChange={(event) => setForm((current) => ({ ...current, subject: event.target.value }))}
                    className={`${inputClass} mt-1`}
                  >
                    <option value="">Selecione</option>
                    {Array.from(new Set([...subjectOptions, ...(form.subject ? [form.subject] : [])])).map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    value={form.subject}
                    onChange={(event) => setForm((current) => ({ ...current, subject: event.target.value }))}
                    className={`${inputClass} mt-1`}
                    placeholder="Ex.: Matemática"
                  />
                )}
              </label>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                Tipo
                <select
                  value={form.activityType}
                  onChange={(event) => setForm((current) => ({ ...current, activityType: event.target.value }))}
                  className={`${inputClass} mt-1`}
                >
                  {Array.from(new Set([...SELECTABLE_TYPES, form.activityType])).map((type) => (
                    <option key={type} value={type}>
                      {(ACTIVITY_TYPES as Record<string, string>)[type] ?? type}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                Nota (0 a 10)
                <input
                  type="number"
                  inputMode="decimal"
                  min={0}
                  max={10}
                  step={0.1}
                  value={form.grade}
                  onChange={(event) => setForm((current) => ({ ...current, grade: event.target.value }))}
                  className={`${inputClass} mt-1`}
                  placeholder="7.5"
                />
              </label>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                Data
                <input
                  type="date"
                  value={form.date}
                  onChange={(event) => setForm((current) => ({ ...current, date: event.target.value }))}
                  className={`${inputClass} mt-1`}
                />
              </label>
            </div>

            <fieldset>
              <legend className="text-sm font-medium text-gray-700 dark:text-gray-200">Presença</legend>
              <div className="mt-2 flex flex-wrap gap-2">
                {([
                  ["present", "Presente"],
                  ["absent", "Faltou"],
                  ["none", "Não registrar"],
                ] as const).map(([value, label]) => (
                  <label
                    key={value}
                    className={`cursor-pointer rounded-lg border px-4 py-2 text-sm font-semibold transition ${
                      form.presence === value
                        ? "border-[#1E5AA8] bg-blue-50 text-[#1E5AA8] dark:bg-blue-950/40 dark:text-[#4FC3F7]"
                        : "border-gray-300 text-gray-600 hover:border-gray-400 dark:border-gray-600 dark:text-gray-300"
                    }`}
                  >
                    <input
                      type="radio"
                      name="presence"
                      value={value}
                      checked={form.presence === value}
                      onChange={() => setForm((current) => ({ ...current, presence: value }))}
                      className="sr-only"
                    />
                    {label}
                  </label>
                ))}
              </div>
            </fieldset>

            <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
              Observações
              <textarea
                value={form.observations}
                onChange={(event) => setForm((current) => ({ ...current, observations: event.target.value }))}
                rows={3}
                maxLength={500}
                className={`${inputClass} mt-1 resize-y`}
                placeholder="Opcional"
              />
            </label>

            <DialogFooter>
              <button
                type="button"
                onClick={() => setFormOpen(false)}
                disabled={saving}
                className="rounded-lg border border-gray-300 px-4 py-2 font-semibold text-gray-700 transition hover:bg-gray-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={saving}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#1E5AA8] px-5 py-2 font-semibold text-white transition hover:bg-[#0A2463] disabled:opacity-60"
              >
                {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                {editing ? "Salvar alterações" : "Lançar"}
              </button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog
        open={recordToDelete !== null}
        onOpenChange={(open) => {
          if (!open && !deleting) setRecordToDelete(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir lançamento?</AlertDialogTitle>
            <AlertDialogDescription>
              {recordToDelete
                ? `A nota ${recordToDelete.grade.toFixed(1)} de ${recordToDelete.subject || "disciplina não informada"} (${formatDate(recordToDelete.date)}) será removida e a média e a frequência do aluno serão recalculadas.`
                : ""}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              disabled={deleting}
              onClick={(event) => {
                event.preventDefault();
                void handleDelete();
              }}
              className="bg-red-600 text-white hover:bg-red-700 focus:ring-red-600"
            >
              {deleting ? "Excluindo..." : "Sim, excluir lançamento"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
