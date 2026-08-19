import { Loader2, Users } from "lucide-react";
import { useApi, useApiList } from "@/hooks/useApi";
import { studentPortalService } from "@/services";

export function AlunoTurma() {
  const { data: classroom, loading: loadingClass } = useApi(() => studentPortalService.getClassroom());
  const { data: classmates, loading: loadingMates, error } = useApiList(() => studentPortalService.getClassmates());

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[#0A2463] dark:text-white">Minha Turma</h1>
        <p className="text-gray-600 dark:text-gray-300">Informações da sua turma e colegas de classe.</p>
      </div>

      {loadingClass ? (
        <div className="flex items-center gap-2 text-gray-500">
          <Loader2 className="h-5 w-5 animate-spin" />
          Carregando turma...
        </div>
      ) : classroom ? (
        <div className="rounded-2xl bg-white p-6 shadow-sm dark:bg-gray-800">
          <h2 className="text-xl font-semibold text-[#0A2463] dark:text-white">{classroom.name}</h2>
          <p className="mt-2 text-gray-600 dark:text-gray-300">
            {classroom.gradeLevel} • Ano {classroom.year}
          </p>
          {classroom.subjects?.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {classroom.subjects.map((subject) => (
                <span
                  key={subject}
                  className="rounded-full bg-[#E3F2FD] px-3 py-1 text-sm text-[#1E5AA8] dark:bg-blue-900/30 dark:text-blue-200"
                >
                  {subject}
                </span>
              ))}
            </div>
          )}
        </div>
      ) : null}

      <div className="rounded-2xl bg-white p-6 shadow-sm dark:bg-gray-800">
        <div className="mb-4 flex items-center gap-2">
          <Users className="h-5 w-5 text-[#1E5AA8]" />
          <h2 className="text-lg font-semibold text-[#0A2463] dark:text-white">Colegas da turma</h2>
        </div>

        {loadingMates && (
          <div className="flex items-center gap-2 text-gray-500">
            <Loader2 className="h-5 w-5 animate-spin" />
            Carregando colegas...
          </div>
        )}

        {error && <p className="text-red-600">{error}</p>}

        {!loadingMates && classmates?.length === 0 && (
          <p className="text-gray-500 dark:text-gray-400">Nenhum outro aluno na turma.</p>
        )}

        <ul className="divide-y divide-gray-100 dark:divide-gray-700">
          {classmates?.map((mate) => (
            <li key={mate.id} className="flex items-center justify-between py-3">
              <div>
                <p className="font-medium text-[#0A2463] dark:text-white">{mate.name}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">{mate.email}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
