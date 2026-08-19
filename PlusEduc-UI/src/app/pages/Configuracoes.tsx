import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Sun, Moon, User, Mail, Briefcase, Edit, Key, LogOut, Shield, Loader2 } from "lucide-react";
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
    <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-[#0A2463] dark:text-white">Configurações</h1>
          <p className="text-gray-600 dark:text-gray-300 mt-2">Gerencie suas preferências e dados de acesso</p>
        </div>

        {/* Grid de Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Seção 1: Aparência (Tema) */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 space-y-5 transition-colors">
            <div className="flex items-center gap-3 pb-4 border-b border-gray-200 dark:border-gray-600">
              <div className="p-2 bg-[#1E5AA8]/10 rounded-lg">
                <Sun className="w-5 h-5 text-[#1E5AA8]" />
              </div>
              <h2 className="text-lg font-bold text-[#0A2463] dark:text-white">Aparência</h2>
            </div>

            <div className="space-y-4">
              <p className="text-sm text-gray-600 dark:text-gray-300">
                Escolha entre o modo claro ou escuro para sua interface
              </p>

              {/* Toggle Switch */}
              <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg transition-colors">
                <div className="flex items-center gap-3">
                  {theme === "light" ? (
                    <Sun className="w-5 h-5 text-[#FF9800]" />
                  ) : (
                    <Moon className="w-5 h-5 text-[#1E5AA8] dark:text-[#4FC3F7]" />
                  )}
                  <span className="font-medium text-gray-700 dark:text-gray-200">
                    {theme === "light" ? "Modo Claro" : "Modo Escuro"}
                  </span>
                </div>
                <button
                  onClick={() => setTheme(theme === "light" ? "dark" : "light")}
                  className={`relative w-14 h-7 rounded-full transition-colors ${
                    theme === "light" ? "bg-gray-300" : "bg-[#1E5AA8]"
                  }`}
                >
                  <span
                    className={`absolute top-1 left-1 w-5 h-5 bg-white rounded-full shadow-md transition-transform ${
                      theme === "dark" ? "translate-x-7" : ""
                    }`}
                  />
                </button>
              </div>

              {/* Preview Visual */}
              <div className="space-y-3">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  Preview
                </p>
                <div className="grid grid-cols-2 gap-3">
                  {/* Preview Modo Claro */}
                  <button
                    onClick={() => setTheme("light")}
                    className={`relative p-3 border-2 rounded-lg transition-all ${
                      theme === "light"
                        ? "border-[#1E5AA8] ring-2 ring-[#1E5AA8]/20"
                        : "border-gray-200 hover:border-gray-300"
                    }`}
                  >
                    <div className="space-y-2">
                      <div className="h-16 bg-gradient-to-b from-[#0A2463] to-[#1E5AA8] rounded" />
                      <div className="h-2 bg-gray-100 rounded w-3/4" />
                      <div className="h-2 bg-gray-100 rounded w-1/2" />
                    </div>
                    <p className="text-xs font-medium text-gray-600 mt-2 text-center">
                      Claro
                    </p>
                    {theme === "light" && (
                      <div className="absolute top-2 right-2 w-5 h-5 bg-[#4CAF50] rounded-full flex items-center justify-center">
                        <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                    )}
                  </button>

                  {/* Preview Modo Escuro */}
                  <button
                    onClick={() => setTheme("dark")}
                    className={`relative p-3 border-2 rounded-lg transition-all ${
                      theme === "dark"
                        ? "border-[#1E5AA8] ring-2 ring-[#1E5AA8]/20"
                        : "border-gray-200 hover:border-gray-300"
                    }`}
                  >
                    <div className="space-y-2">
                      <div className="h-16 bg-gradient-to-b from-[#0A2463] to-[#1E5AA8] rounded" />
                      <div className="h-2 bg-gray-700 rounded w-3/4" />
                      <div className="h-2 bg-gray-700 rounded w-1/2" />
                    </div>
                    <p className="text-xs font-medium text-gray-600 mt-2 text-center">
                      Escuro
                    </p>
                    {theme === "dark" && (
                      <div className="absolute top-2 right-2 w-5 h-5 bg-[#4CAF50] rounded-full flex items-center justify-center">
                        <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                    )}
                  </button>
                </div>
              </div>

              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-xs text-blue-700">
                  <strong>Nota:</strong> A preferência de tema será aplicada em todo o sistema.
                </p>
              </div>
            </div>
          </div>

          {/* Seção 2: Dados Pessoais */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 space-y-5 transition-colors">
            <div className="flex items-center gap-3 pb-4 border-b border-gray-200 dark:border-gray-600">
              <div className="p-2 bg-[#1E5AA8]/10 dark:bg-[#1E5AA8]/20 rounded-lg">
                <User className="w-5 h-5 text-[#1E5AA8] dark:text-[#4FC3F7]" />
              </div>
              <h2 className="text-lg font-bold text-[#0A2463] dark:text-white">Dados Pessoais</h2>
            </div>

            <div className="space-y-4">
              {/* Nome */}
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">
                  <User className="w-4 h-4" />
                  Nome
                </label>
                <input
                  type="text"
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  readOnly={!isEditing}
                  placeholder="Nome não informado"
                  className={`w-full px-4 py-3 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition ${isEditing ? "bg-white dark:bg-gray-700" : "bg-gray-50 dark:bg-gray-700/70"}`}
                />
              </div>

              {/* Email */}
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">
                  <Mail className="w-4 h-4" />
                  Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  readOnly={!isEditing}
                  placeholder="E-mail não informado"
                  className={`w-full px-4 py-3 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition ${isEditing ? "bg-white dark:bg-gray-700" : "bg-gray-50 dark:bg-gray-700/70"}`}
                />
              </div>

              {/* Função (Read-only) */}
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">
                  <Briefcase className="w-4 h-4" />
                  Função (Role)
                </label>
                <input
                  type="text"
                  value={funcao}
                  disabled
                  className="w-full px-4 py-3 border border-gray-200 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-500 dark:text-gray-400 cursor-not-allowed outline-none"
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 flex items-center gap-1">
                  <Shield className="w-3 h-3" />
                  Este campo é definido pelo administrador do sistema
                </p>
              </div>

              {/* Botões de Ação */}
              <div className="flex flex-wrap gap-3 pt-4">
                {isEditing && (
                  <button
                    type="button"
                    onClick={handleCancelEdit}
                    disabled={isSaving}
                    className="flex-1 border-2 border-gray-300 text-gray-700 hover:bg-gray-100 py-3 px-6 rounded-lg font-semibold transition-all disabled:cursor-not-allowed disabled:opacity-60 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
                  >
                    Cancelar
                  </button>
                )}
                <button
                  type="button"
                  onClick={handleEditProfile}
                  disabled={isSaving}
                  className="flex-1 border-2 border-[#1E5AA8] text-[#1E5AA8] hover:bg-[#1E5AA8] hover:text-white py-3 px-6 rounded-lg font-semibold flex items-center justify-center gap-2 transition-all disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Edit className="w-4 h-4" />}
                  {isSaving ? "Salvando..." : isEditing ? "Salvar Perfil" : "Editar Perfil"}
                </button>
                <button
                  onClick={handleChangePassword}
                  className="text-[#1E5AA8] hover:text-[#0A2463] font-medium flex items-center gap-2 px-4 transition-colors"
                >
                  <Key className="w-4 h-4" />
                  Alterar Senha
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Seção 3: Sessão e Segurança (Full Width) */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 space-y-5 transition-colors">
          <div className="flex items-center gap-3 pb-4 border-b border-gray-200 dark:border-gray-600">
            <div className="p-2 bg-red-50 dark:bg-red-900/20 rounded-lg">
              <Shield className="w-5 h-5 text-red-600 dark:text-red-400" />
            </div>
            <h2 className="text-lg font-bold text-[#0A2463] dark:text-white">Sessão e Segurança</h2>
          </div>

          <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6 p-6 bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded-lg">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <LogOut className="w-5 h-5 text-red-600 dark:text-red-400" />
                <h3 className="font-bold text-red-900 dark:text-red-200">Encerrar Sessão</h3>
              </div>
              <p className="text-sm text-red-700 dark:text-red-300">
                Você precisará fazer login novamente para acessar suas turmas e atividades
              </p>
              <p className="text-xs text-red-600 dark:text-red-400 mt-2">
                Certifique-se de salvar todas as alterações antes de sair
              </p>
            </div>
            <button
              onClick={handleLogout}
              className="bg-red-600 hover:bg-red-700 text-white py-3 px-8 rounded-lg font-semibold flex items-center gap-2 shadow-md hover:shadow-lg transition-all whitespace-nowrap"
            >
              <LogOut className="w-5 h-5" />
              Sair da Conta
            </button>
          </div>

          {/* Informações Adicionais de Segurança */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4">
            <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg transition-colors">
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                Último Acesso
              </p>
              <p className="text-sm font-medium text-gray-700 dark:text-gray-200">15/04/2026 às 09:32</p>
            </div>
            <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg transition-colors">
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                Dispositivo
              </p>
              <p className="text-sm font-medium text-gray-700 dark:text-gray-200">Chrome - Windows 11</p>
            </div>
          </div>
        </div>
    </div>
  );
}
