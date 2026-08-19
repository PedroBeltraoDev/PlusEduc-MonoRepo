import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, BookOpen, Loader2, Users } from "lucide-react";
import { Link, useParams } from "react-router";
import { toast } from "sonner";
import { subjectsService } from "@/services";
import type { Subject, SubjectClassroom } from "@/types";

export function MateriaTurmas() {
  const { subjectId = "" } = useParams();
  const [subject, setSubject] = useState<Subject | null>(null);
  const [classrooms, setClassrooms] = useState<SubjectClassroom[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const [subjects, classroomData] = await Promise.all([
          subjectsService.getAll(),
          subjectsService.getClassrooms(subjectId),
        ]);
        setSubject(subjects.find((item) => item.id === subjectId) ?? null);
        setClassrooms(classroomData);
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Não foi possível carregar as turmas.");
      } finally {
        setLoading(false);
      }
    }

    if (subjectId) void load();
  }, [subjectId]);

  return (
    <div className="space-y-6">
      <header>
        <Link to="/materias" className="mb-4 inline-flex items-center gap-2 text-sm font-semibold text-[#1E5AA8] hover:underline dark:text-[#7FC8F8]">
          <ArrowLeft className="h-4 w-4" /> Voltar para matérias
        </Link>
        <div className="flex items-start gap-3">
          <div className="rounded-xl bg-[#1E5AA8] p-3 text-white shadow-sm"><BookOpen className="h-6 w-6" /></div>
          <div>
            <h1 className="text-2xl font-bold text-[#0A2463] dark:text-white">Turmas de {subject?.name ?? "matéria"}</h1>
            <p className="mt-1 text-gray-600 dark:text-gray-300">Escolha uma turma para acompanhar o desempenho dos alunos.</p>
          </div>
        </div>
      </header>

      <section className="rounded-2xl bg-white p-6 shadow-sm dark:bg-gray-800">
        <div className="flex items-center justify-between border-b border-gray-200 pb-5 dark:border-gray-700">
          <div>
            <h2 className="text-lg font-semibold text-[#0A2463] dark:text-white">Turmas encontradas</h2>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">A relação usa as matérias cadastradas em cada turma.</p>
          </div>
          <span className="rounded-full bg-blue-50 px-3 py-1 text-sm font-semibold text-[#1E5AA8] dark:bg-blue-950/40 dark:text-[#7FC8F8]">
            {classrooms.length} turma{classrooms.length === 1 ? "" : "s"}
          </span>
        </div>

        {loading ? (
          <div className="flex items-center justify-center gap-2 py-12 text-gray-500 dark:text-gray-400"><Loader2 className="h-5 w-5 animate-spin" /> Carregando turmas...</div>
        ) : classrooms.length === 0 ? (
          <div className="py-12 text-center text-gray-500 dark:text-gray-400">
            <Users className="mx-auto h-10 w-10" />
            <p className="mt-3 font-semibold">Nenhuma turma vinculada a esta matéria.</p>
            <p className="mt-1 text-sm">Confira se o nome da matéria é igual ao cadastrado na turma.</p>
          </div>
        ) : (
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            {classrooms.map((classroom) => (
              <Link
                key={classroom.id}
                to={`/materias/${subjectId}/turmas/${classroom.id}/desempenho`}
                className="group rounded-xl border border-gray-200 p-5 transition hover:-translate-y-0.5 hover:border-[#1E5AA8] hover:shadow-md dark:border-gray-700 dark:hover:border-[#4FC3F7]"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="font-bold text-[#0A2463] dark:text-white">{classroom.name}</h3>
                    <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                      {classroom.gradeLevel || "Nível não informado"}{classroom.year ? ` · ${classroom.year}` : ""}
                    </p>
                  </div>
                  <ArrowRight className="h-5 w-5 text-gray-400 transition group-hover:translate-x-1 group-hover:text-[#1E5AA8] dark:group-hover:text-[#4FC3F7]" />
                </div>
                <div className="mt-5 grid grid-cols-2 gap-3">
                  <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-700/60"><p className="text-xs text-gray-500 dark:text-gray-400">Alunos</p><p className="mt-1 text-lg font-bold text-[#0A2463] dark:text-white">{classroom.studentCount}</p></div>
                  <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-700/60"><p className="text-xs text-gray-500 dark:text-gray-400">Média da turma</p><p className="mt-1 text-lg font-bold text-[#1E5AA8] dark:text-[#7FC8F8]">{classroom.averageGrade.toFixed(1)}</p></div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
