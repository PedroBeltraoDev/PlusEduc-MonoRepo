import { Link } from "react-router";
import { ClipboardList, GraduationCap, Users, BookOpen } from "lucide-react";
import { useApi } from "@/hooks/useApi";
import { studentPortalService } from "@/services";

const quickLinks = [
  { to: "/aluno/atividades", icon: ClipboardList, label: "Atividades", color: "bg-[#1E5AA8]" },
  { to: "/aluno/turma", icon: Users, label: "Minha Turma", color: "bg-[#4FC3F7]" },
  { to: "/aluno/professores", icon: GraduationCap, label: "Professores", color: "bg-[#FF9800]" },
  { to: "/aluno/notas", icon: BookOpen, label: "Minhas Notas", color: "bg-[#4CAF50]" },
];

export function AlunoHome() {
  const { data: profile, loading } = useApi(() => studentPortalService.getProfile());

  return (
    <div className="space-y-6">
      <div className="rounded-2xl bg-white p-6 shadow-sm dark:bg-gray-800">
        <h1 className="text-2xl font-bold text-[#0A2463] dark:text-white">
          Olá, {profile?.name || "Aluno"}!
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-300">
          Bem-vindo à sua área. Aqui você pode ver atividades, turma, professores e notas.
        </p>
        {profile?.className && (
          <p className="mt-3 inline-flex rounded-full bg-[#E3F2FD] px-4 py-1 text-sm font-medium text-[#1E5AA8] dark:bg-blue-900/30 dark:text-blue-200">
            Turma: {profile.className}
          </p>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {quickLinks.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.to}
              to={item.to}
              className="rounded-2xl bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md dark:bg-gray-800"
            >
              <div className={`mb-4 inline-flex rounded-xl p-3 text-white ${item.color}`}>
                <Icon className="h-6 w-6" />
              </div>
              <h2 className="font-semibold text-[#0A2463] dark:text-white">{item.label}</h2>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Acessar seção</p>
            </Link>
          );
        })}
      </div>

      {loading && (
        <p className="text-sm text-gray-500 dark:text-gray-400">Carregando perfil...</p>
      )}
    </div>
  );
}
