import { Mail, LogOut, Moon, Palette, Sun, UserRound } from "lucide-react";
import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { useNavigate } from "react-router";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";
import { studentPortalService } from "@/services";

export function AlunoConfiguracoes() {
  const { theme, setTheme } = useTheme();
  const { logout, userName, userEmail } = useAuth();
  const navigate = useNavigate();
  const [profile, setProfile] = useState<{ name: string; email: string } | null>(null);
  const currentTheme = theme === "dark" ? "dark" : "light";

  useEffect(() => {
    if (userName && userEmail) return;

    let mounted = true;
    void studentPortalService.getProfile()
      .then((studentProfile) => {
        if (mounted) {
          setProfile({ name: studentProfile.name, email: studentProfile.email });
        }
      })
      .catch(() => {
        // Os dados já persistidos no login continuam sendo usados como fallback.
      });

    return () => {
      mounted = false;
    };
  }, [userEmail, userName]);

  const displayName = userName || profile?.name || "Aluno";
  const displayEmail = userEmail || profile?.email || "E-mail não disponível";

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
    navigate("/login");
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-[#0A2463] dark:text-white">Configurações</h1>
        <p className="mt-1 text-gray-600 dark:text-gray-300">
          Ajuste a aparência da sua área e controle sua sessão.
        </p>
      </header>

      <section className="rounded-2xl bg-white p-6 shadow-sm transition-colors dark:bg-gray-800">
        <div className="flex items-start gap-4 border-b border-gray-200 pb-5 dark:border-gray-700">
          <div className="rounded-xl bg-[#1E5AA8]/10 p-3 text-[#1E5AA8] dark:bg-blue-400/10 dark:text-[#4FC3F7]">
            <UserRound className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-[#0A2463] dark:text-white">Informações do aluno</h2>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
              Consulte os dados da sua conta cadastrados no PlusEduc.
            </p>
          </div>
        </div>

        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-700/50">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-300">
              <UserRound className="h-4 w-4" />
              <span>Nome completo</span>
            </div>
            <p className="mt-2 break-words font-semibold text-[#0A2463] dark:text-white">{displayName}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-700/50">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-300">
              <Mail className="h-4 w-4" />
              <span>E-mail</span>
            </div>
            <p className="mt-2 break-words font-semibold text-[#0A2463] dark:text-white">{displayEmail}</p>
          </div>
        </div>
      </section>

      <section className="rounded-2xl bg-white p-6 shadow-sm transition-colors dark:bg-gray-800">
        <div className="flex items-start gap-4 border-b border-gray-200 pb-5 dark:border-gray-700">
          <div className="rounded-xl bg-[#1E5AA8]/10 p-3 text-[#1E5AA8] dark:bg-blue-400/10 dark:text-[#4FC3F7]">
            <Palette className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-[#0A2463] dark:text-white">Tema da interface</h2>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
              Escolha o modo que fica melhor para estudar. A preferência será aplicada em todo o sistema.
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
              <span className="mt-1 block text-xs opacity-75">Menos brilho para estudar à noite</span>
            </span>
          </button>
        </div>
      </section>

      <section className="rounded-2xl border border-rose-200 bg-white p-6 shadow-sm transition-colors dark:border-rose-900/50 dark:bg-gray-800">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-[#0A2463] dark:text-white">Sair da conta</h2>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
              Encerre sua sessão neste dispositivo.
            </p>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-rose-600 px-5 py-3 font-semibold text-white transition hover:bg-rose-700 focus:outline-none focus:ring-2 focus:ring-rose-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
          >
            <LogOut className="h-4 w-4" />
            Sair
          </button>
        </div>
      </section>
    </div>
  );
}
