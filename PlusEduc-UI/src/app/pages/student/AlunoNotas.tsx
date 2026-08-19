import { BookOpen, Loader2 } from "lucide-react";
import { useApiList } from "@/hooks/useApi";
import { studentPortalService } from "@/services";
import { formatDate } from "@/utils";

export function AlunoNotas() {
  const { data: grades, loading, error } = useApiList(() => studentPortalService.getGrades());

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[#0A2463] dark:text-white">Minhas Notas</h1>
        <p className="text-gray-600 dark:text-gray-300">Acompanhe seu desempenho por disciplina.</p>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-gray-500">
          <Loader2 className="h-5 w-5 animate-spin" />
          Carregando notas...
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>
      )}

      {!loading && grades?.length === 0 && (
        <div className="rounded-2xl bg-white p-8 text-center shadow-sm dark:bg-gray-800">
          <BookOpen className="mx-auto h-12 w-12 text-gray-400" />
          <p className="mt-4 text-gray-600 dark:text-gray-300">Nenhuma nota registrada ainda.</p>
        </div>
      )}

      <div className="overflow-hidden rounded-2xl bg-white shadow-sm dark:bg-gray-800">
        <table className="w-full text-left">
          <thead className="bg-gray-50 dark:bg-gray-900/50">
            <tr>
              <th className="px-4 py-3 text-sm font-semibold text-gray-600 dark:text-gray-300">Disciplina</th>
              <th className="px-4 py-3 text-sm font-semibold text-gray-600 dark:text-gray-300">Nota</th>
              <th className="px-4 py-3 text-sm font-semibold text-gray-600 dark:text-gray-300">Tipo</th>
              <th className="px-4 py-3 text-sm font-semibold text-gray-600 dark:text-gray-300">Data</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {grades?.map((grade) => (
              <tr key={grade.id}>
                <td className="px-4 py-3 font-medium text-[#0A2463] dark:text-white">{grade.subject}</td>
                <td className="px-4 py-3">
                  <span className="rounded-full bg-[#E8F5E9] px-3 py-1 font-semibold text-green-700 dark:bg-green-900/30 dark:text-green-300">
                    {grade.grade.toFixed(1)}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{grade.activityType}</td>
                <td className="px-4 py-3 text-gray-500 dark:text-gray-400">{formatDate(grade.date)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
