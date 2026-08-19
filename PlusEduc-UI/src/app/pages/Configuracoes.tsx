import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import {
  Briefcase,
  Edit,
  Key,
  Loader2,
  LogOut,
  Mail,
  Moon,
  Palette,
  Shield,
  Sun,
  User,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";

export function Configuracoes() {
  const { theme, setTheme } = useTheme();
  const { logout, role, userName, userEmail, updateProfile } = useAuth();
  const [nome, setNome] = useState(userName ?? "");
  const [email, setEmail] = useState(userEmail ?? "");
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const funcao = role === "ADMIN" ? "Administrador" : role === "STUDENT" ? "Aluno" : "Professora";
  const currentTheme = theme === "dark" ? "dark" : "light";

  useEffect(() => {
    if (!isEditing) {
      setNome(userName ?? "");
      setEmail(userEmail ?? "");
    }
  }, [isEditing, userEmail, userName]);

  const handleLogout = () => {
    toast.success("Sessão encerrada com sucesso!", {
      duration: 2000,
      style: {
        background: "#4CAF50",
        color: "white",
        border: "none",
      },
    });
    logout();
  };

  const handleEditProfile = async () => {
    if (!isEditing) {
      setIsEditing(true);
      return;
    }

    const trimmedName = nome.trim();
    const trimmedEmail = email.trim().toLowerCase();
    if (!trimmedName || !trimmedEmail) {
      toast.error("Nome e e-mail são obrigatórios.");
      return;
    }

    try {
      setIsSaving(true);
      await updateProfile({ name: trimmedName, email: trimmedEmail });
      setNome(trimmedName);
      setEmail(trimmedEmail);
      setIsEditing(false);
      toast.success("Perfil atualizado com sucesso.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Não foi possível atualizar o perfil.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setNome(userName ?? "");
    setEmail(userEmail ?? "");
    setIsEditing(false);
  };

  const handleChangePassword = () => {
    toast.info("Um link foi enviado para seu e-mail", {
      duration: 3000,
    });
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-[#0A2463] dark:text-white">Configurações</h1>
        <p className="mt-1 text-gray-600 dark:text-gray-300">
          Gerencie suas preferências e dados de acesso.
        </p>
      </header>

      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <section className="rounded-2xl bg-white p-6 shadow-sm transition-colors dark:bg-gray-800">
          <div className="flex items-start gap-4 border-b border-gray-200 pb-5 dark:border-gray-700">
            <div className="rounded-xl bg-[#1E5AA8]/10 p-3 text-[#1E5AA8] dark:bg-blue-400/10 dark:text-[#4FC3F7]">
              <Palette className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-[#0A2463] dark:text-white">Tema da interface</h2>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
                Escolha o modo que fica melhor para trabalhar. A preferência será aplicada em todo o sistema.
              </p>
            </div>
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            <button
              type="button"
              onClick={() => setTheme("light")}
              aria-pressed={currentTheme === "light"}
              className={`flex items-center gap-3 rounded-xl border-2 p-4 text-left transition focus:outline-none focus:ring-2 focus:ring-[#1E5AA8] ${
                currentTheme === "light"
                  ? "border-[#1E5AA8] bg-blue-50 text-[#0A2463] dark:border-[#4FC3F7] dark:bg-blue-950/30 dark:text-blue-100"
                  : "border-gray-200 text-gray-600 hover:border-gray-300 dark:border-gray-700 dark:text-gray-300 dark:hover:border-gray-600"
              }`}
            >
              <Sun className="h-5 w-5 shrink-0 text-amber-500" />
              <span>
                <span className="block font-semibold">Modo claro</span>
                <span className="mt-1 block text-xs opacity-75">Fundo claro e leitura confortável</span>
              </span>
            </button>

            <button
              type="button"
              onClick={() => setTheme("dark")}
              aria-pressed={currentTheme === "dark"}
              className={`flex items-center gap-3 rounded-xl border-2 p-4 text-left transition focus:outline-none focus:ring-2 focus:ring-[#1E5AA8] ${
                currentTheme === "dark"
                  ? "border-[#1E5AA8] bg-blue-50 text-[#0A2463] dark:border-[#4FC3F7] dark:bg-blue-950/30 dark:text-blue-100"
                  : "border-gray-200 text-gray-600 hover:border-gray-300 dark:border-gray-700 dark:text-gray-300 dark:hover:border-gray-600"
              }`}
            >
              <Moon className="h-5 w-5 shrink-0 text-[#1E5AA8] dark:text-[#4FC3F7]" />
              <span>
                <span className="block font-semibold">Modo escuro</span>
                <span className="mt-1 block text-xs opacity-75">Menos brilho para trabalhar à noite</span>
              </span>
            </button>
          </div>
        </section>

        <section className="rounded-2xl bg-white p-6 shadow-sm transition-colors dark:bg-gray-800">
          <div className="flex items-start gap-4 border-b border-gray-200 pb-5 dark:border-gray-700">
            <div className="rounded-xl bg-[#1E5AA8]/10 p-3 text-[#1E5AA8] dark:bg-blue-400/10 dark:text-[#4FC3F7]">
              <User className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-[#0A2463] dark:text-white">Dados pessoais</h2>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
                Mantenha suas informações de acesso atualizadas.
              </p>
            </div>
          </div>

          <div className="mt-6 space-y-4">
            <label className="block">
              <span className="mb-2 flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-200">
                <User className="h-4 w-4" />
                Nome
              </span>
              <input
                type="text"
                value={nome}
                onChange={(event) => setNome(event.target.value)}
                readOnly={!isEditing}
                placeholder="Nome não informado"
                className={`w-full rounded-lg border border-gray-300 px-4 py-3 text-gray-900 outline-none transition focus:border-transparent focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:text-gray-100 ${isEditing ? "bg-white dark:bg-gray-700" : "bg-gray-50 dark:bg-gray-700/70"}`}
              />
            </label>

            <label className="block">
              <span className="mb-2 flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-200">
                <Mail className="h-4 w-4" />
                E-mail
              </span>
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                readOnly={!isEditing}
                placeholder="E-mail não informado"
                className={`w-full rounded-lg border border-gray-300 px-4 py-3 text-gray-900 outline-none transition focus:border-transparent focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:text-gray-100 ${isEditing ? "bg-white dark:bg-gray-700" : "bg-gray-50 dark:bg-gray-700/70"}`}
              />
            </label>

            <div>
              <span className="mb-2 flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-200">
                <Briefcase className="h-4 w-4" />
                Função
              </span>
              <div className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-gray-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-400">
                <span>{funcao}</span>
                <Shield className="ml-auto h-4 w-4" />
              </div>
            </div>

            <div className="flex flex-wrap gap-3 pt-2">
              {isEditing && (
                <button
                  type="button"
                  onClick={handleCancelEdit}
                  disabled={isSaving}
                  className="flex-1 rounded-lg border-2 border-gray-300 px-4 py-3 font-semibold text-gray-700 transition hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
                >
                  Cancelar
                </button>
              )}
              <button
                type="button"
                onClick={handleEditProfile}
                disabled={isSaving}
                className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg border-2 border-[#1E5AA8] px-4 py-3 font-semibold text-[#1E5AA8] transition hover:bg-[#1E5AA8] hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Edit className="h-4 w-4" />}
                {isSaving ? "Salvando..." : isEditing ? "Salvar perfil" : "Editar perfil"}
              </button>
              <button
                type="button"
                onClick={handleChangePassword}
                className="inline-flex items-center gap-2 px-2 py-3 font-medium text-[#1E5AA8] transition hover:text-[#0A2463] dark:text-[#4FC3F7] dark:hover:text-white"
              >
                <Key className="h-4 w-4" />
                Alterar senha
              </button>
            </div>
          </div>
        </section>
      </div>

      <section className="rounded-2xl border border-rose-200 bg-white p-6 shadow-sm transition-colors dark:border-rose-900/50 dark:bg-gray-800">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <LogOut className="h-5 w-5 text-rose-600 dark:text-rose-400" />
              <h2 className="text-lg font-semibold text-[#0A2463] dark:text-white">Encerrar sessão</h2>
            </div>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
              Você precisará fazer login novamente para acessar suas turmas e atividades.
            </p>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Salve suas alterações antes de sair.
            </p>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-rose-600 px-5 py-3 font-semibold text-white transition hover:bg-rose-700 focus:outline-none focus:ring-2 focus:ring-rose-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
          >
            <LogOut className="h-4 w-4" />
            Sair da conta
          </button>
        </div>

        <div className="mt-5 grid gap-3 border-t border-gray-200 pt-5 sm:grid-cols-2 dark:border-gray-700">
          <div className="rounded-xl bg-gray-50 p-4 dark:bg-gray-700">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Último acesso</p>
            <p className="mt-2 text-sm font-medium text-gray-700 dark:text-gray-200">15/04/2026 às 09:32</p>
          </div>
          <div className="rounded-xl bg-gray-50 p-4 dark:bg-gray-700">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Dispositivo</p>
            <p className="mt-2 text-sm font-medium text-gray-700 dark:text-gray-200">Chrome - Windows 11</p>
          </div>
        </div>
      </section>
    </div>
  );
}
