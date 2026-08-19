import { useEffect, useState } from "react";
import { ArrowLeft, BarChart3, Loader2, Medal, Users } from "lucide-react";
import { Link, useParams } from "react-router";
import { toast } from "sonner";
import { subjectsService } from "@/services";
import type { Subject, SubjectStudentPerformance } from "@/types";

type SortOption = "name-asc" | "name-desc" | "grade-desc" | "grade-asc";

export function MateriaTurmaDesempenho() {
  const { subjectId = "", classroomId = "" } = useParams();
  const [subject, setSubject] = useState<Subject | null>(null);
  const [rows, setRows] = useState<SubjectStudentPerformance[]>([]);
  const [classroomName, setClassroomName] = useState("turma");
  const [sortOption, setSortOption] = useState<SortOption>("name-asc");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadHeader() {
      try {
        const [subjects, classrooms] = await Promise.all([
          subjectsService.getAll(),
          subjectsService.getClassrooms(subjectId),
        ]);
        setSubject(subjects.find((item) => item.id === subjectId) ?? null);
        setClassroomName(classrooms.find((item) => item.id === classroomId)?.name ?? "turma");
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Não foi possível carregar os dados da turma.");
      }
    }
    if (subjectId && classroomId) void loadHeader();
  }, [subjectId, classroomId]);

  useEffect(() => {
    async function loadPerformance() {
      try {
        setLoading(true);
        const sortBy = sortOption.startsWith("grade") ? "grade" : "name";
        const order = sortOption.endsWith("desc") ? "desc" : "asc";
        setRows(await subjectsService.getPerformance(subjectId, classroomId, { sortBy, order }));
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Não foi possível carregar o desempenho.");
      } finally {
        setLoading(false);
      }
    }
    if (subjectId && classroomId) void loadPerformance();
  }, [subjectId, classroomId, sortOption]);

  const gradedRows = rows.filter((row) => row.gradeCount > 0);
  const classAverage = gradedRows.length ? gradedRows.reduce((total, row) => total + row.averageGrade, 0) / gradedRows.length : 0;

  return (
    <div className="space-y-6">
      <header>
        <Link to={`/materias/${subjectId}/turmas`} className="mb-4 inline-flex items-center gap-2 text-sm font-semibold text-[#1E5AA8] hover:underline dark:text-[#7FC8F8]"><ArrowLeft className="h-4 w-4" /> Voltar para turmas</Link>
        <div className="flex items-start gap-3"><div className="rounded-xl bg-[#1E5AA8] p-3 text-white shadow-sm"><BarChart3 className="h-6 w-6" /></div><div><h1 className="text-2xl font-bold text-[#0A2463] dark:text-white">Desempenho da turma</h1><p className="mt-1 text-gray-600 dark:text-gray-300">{subject?.name ?? "Matéria"} · {classroomName}</p></div></div>
      </header>

      <section className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl bg-white p-5 shadow-sm dark:bg-gray-800"><div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400"><Users className="h-4 w-4" /> Alunos</div><p className="mt-2 text-2xl font-bold text-[#0A2463] dark:text-white">{rows.length}</p></div>
        <div className="rounded-2xl bg-white p-5 shadow-sm dark:bg-gray-800"><div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400"><Medal className="h-4 w-4" /> Com notas</div><p className="mt-2 text-2xl font-bold text-[#0A2463] dark:text-white">{gradedRows.length}</p></div>
        <div className="rounded-2xl bg-white p-5 shadow-sm dark:bg-gray-800"><div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400"><BarChart3 className="h-4 w-4" /> Média da turma</div><p className="mt-2 text-2xl font-bold text-[#1E5AA8] dark:text-[#7FC8F8]">{classAverage.toFixed(1)}</p></div>
      </section>

      <section className="rounded-2xl bg-white p-6 shadow-sm dark:bg-gray-800">
        <div className="flex flex-col gap-4 border-b border-gray-200 pb-5 sm:flex-row sm:items-center sm:justify-between dark:border-gray-700"><div><h2 className="text-lg font-semibold text-[#0A2463] dark:text-white">Alunos e notas</h2><p className="mt-1 text-sm text-gray-600 dark:text-gray-300">Filtre para encontrar rapidamente quem precisa de atenção.</p></div><label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-200">Ordenar por<select value={sortOption} onChange={(event) => setSortOption(event.target.value as SortOption)} className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 outline-none focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"><option value="name-asc">Nome (A–Z)</option><option value="name-desc">Nome (Z–A)</option><option value="grade-desc">Maior nota</option><option value="grade-asc">Menor nota</option></select></label></div>
        {loading ? <div className="flex items-center justify-center gap-2 py-12 text-gray-500 dark:text-gray-400"><Loader2 className="h-5 w-5 animate-spin" /> Carregando desempenho...</div> : rows.length === 0 ? <div className="py-12 text-center text-gray-500 dark:text-gray-400"><Users className="mx-auto h-10 w-10" /><p className="mt-3 font-semibold">Nenhum aluno encontrado nesta turma.</p></div> : <div className="mt-6 overflow-x-auto"><table className="w-full min-w-[640px] text-left"><thead><tr className="border-b border-gray-200 text-xs uppercase tracking-wide text-gray-500 dark:border-gray-700 dark:text-gray-400"><th className="px-3 py-3">Aluno</th><th className="px-3 py-3">Média</th><th className="px-3 py-3">Avaliações</th><th className="px-3 py-3">Última nota</th></tr></thead><tbody>{rows.map((row) => <tr key={row.studentId} className="border-b border-gray-100 last:border-0 dark:border-gray-700/70"><td className="px-3 py-4"><p className="font-semibold text-[#0A2463] dark:text-white">{row.studentName}</p><p className="text-xs text-gray-500 dark:text-gray-400">{row.studentEmail || "E-mail não informado"}</p></td><td className="px-3 py-4"><span className={`font-bold ${row.gradeCount > 0 ? "text-[#1E5AA8] dark:text-[#7FC8F8]" : "text-gray-400"}`}>{row.gradeCount > 0 ? row.averageGrade.toFixed(1) : "Sem nota"}</span></td><td className="px-3 py-4 text-gray-600 dark:text-gray-300">{row.gradeCount}</td><td className="px-3 py-4 text-gray-600 dark:text-gray-300">{row.lastGrade == null ? "—" : row.lastGrade.toFixed(1)}</td></tr>)}</tbody></table></div>}
      </section>
    </div>
  );
}
