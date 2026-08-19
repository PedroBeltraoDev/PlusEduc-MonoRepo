import { GraduationCap, Loader2, Mail } from "lucide-react";
import { useApiList } from "@/hooks/useApi";
import { studentPortalService } from "@/services";

export function AlunoProfessores() {
  const { data: teachers, loading, error } = useApiList(() => studentPortalService.getTeachers());

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[#0A2463] dark:text-white">Meus Professores</h1>
        <p className="text-gray-600 dark:text-gray-300">Professores vinculados à sua turma.</p>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-gray-500">
          <Loader2 className="h-5 w-5 animate-spin" />
          Carregando professores...
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>
      )}

      {!loading && teachers?.length === 0 && (
        <div className="rounded-2xl bg-white p-8 text-center shadow-sm dark:bg-gray-800">
          <GraduationCap className="mx-auto h-12 w-12 text-gray-400" />
          <p className="mt-4 text-gray-600 dark:text-gray-300">Nenhum professor encontrado.</p>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {teachers?.map((teacher) => (
          <div key={teacher.id} className="rounded-2xl bg-white p-5 shadow-sm dark:bg-gray-800">
            <h2 className="text-lg font-semibold text-[#0A2463] dark:text-white">{teacher.name}</h2>
            <p className="mt-1 inline-flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400">
              <Mail className="h-4 w-4" />
              {teacher.email}
            </p>
            {teacher.subjects?.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {teacher.subjects.map((subject) => (
                  <span
                    key={subject}
                    className="rounded-full bg-[#FFF3E0] px-2 py-1 text-xs text-[#E65100] dark:bg-orange-900/30 dark:text-orange-200"
                  >
                    {subject}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
