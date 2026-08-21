import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { AlertCircle, Lock, Mail, UserRound } from "lucide-react";
import { Logo } from "../components/Logo";
import { useAuth } from "@/contexts/AuthContext";

type LoginMode = "login" | "register";

export function Login() {
  const navigate = useNavigate();
  const {
    login,
    registerStudent,
    loadingState,
    isAuthenticated,
    getHomePath,
  } = useAuth();
  const [mode, setMode] = useState<LoginMode>("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (isAuthenticated) {
      navigate(getHomePath());
    }
  }, [isAuthenticated, getHomePath, navigate]);

  const changeMode = (nextMode: LoginMode) => {
    setMode(nextMode);
    setError("");
    setName("");
    setEmail("");
    setPassword("");
    setConfirmPassword("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (mode === "register" && password !== confirmPassword) {
      setError("As senhas não coincidem");
      return;
    }

    try {
      const redirectPath = mode === "register"
        ? await registerStudent({ name, email, password })
        : await login({ email, password });
      navigate(redirectPath);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : mode === "register"
            ? "Erro ao cadastrar aluno"
            : "Erro ao fazer login",
      );
    }
  };

  const isLoading = loadingState === "loading";
  const isRegistering = mode === "register";

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0A2463] via-[#1E5AA8] to-[#4FC3F7] dark:from-gray-900 dark:via-gray-800 dark:to-gray-700 flex items-center justify-center p-4 transition-colors">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-md p-8 transition-colors">
        <Logo className="mb-8" />

        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {isRegistering ? "Cadastro de aluno" : "Acesse sua conta"}
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {isRegistering
              ? "Informe seus dados; sua matrícula será gerada automaticamente pela escola."
              : "Entre para continuar no PlusEduc."}
          </p>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 shrink-0" />
            <span className="text-sm text-red-700 dark:text-red-400">{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          {isRegistering && (
            <>
              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">
                  Nome completo
                </label>
                <div className="relative">
                  <UserRound className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 dark:text-gray-500" />
                  <input
                    id="name"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full pl-11 pr-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition"
                    placeholder="Seu nome completo"
                    autoComplete="name"
                    required
                    disabled={isLoading}
                  />
                </div>
              </div>
            </>
          )}

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">
              E-mail
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 dark:text-gray-500" />
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-11 pr-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition"
                placeholder="seu@email.com"
                autoComplete="email"
                required
                disabled={isLoading}
              />
            </div>
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">
              Senha
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 dark:text-gray-500" />
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-11 pr-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition"
                placeholder="••••••••"
                autoComplete={isRegistering ? "new-password" : "current-password"}
                minLength={isRegistering ? 6 : undefined}
                required
                disabled={isLoading}
              />
            </div>
          </div>

          {isRegistering && (
            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">
                Confirmar senha
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 dark:text-gray-500" />
                <input
                  id="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full pl-11 pr-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition"
                  placeholder="Repita sua senha"
                  autoComplete="new-password"
                  minLength={6}
                  required
                  disabled={isLoading}
                />
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-[#1E5AA8] hover:bg-[#0A2463] disabled:bg-gray-400 disabled:cursor-not-allowed text-white py-3 rounded-lg font-semibold transition-all shadow-md hover:shadow-lg flex items-center justify-center gap-2"
          >
            {isLoading && <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />}
            {isLoading ? (isRegistering ? "Cadastrando..." : "Entrando...") : (isRegistering ? "Criar acesso" : "Entrar")}
          </button>

          {!isRegistering && (
            <div className="text-center">
              <a
                href="#"
                onClick={(event) => event.preventDefault()}
                className="text-sm text-[#1E5AA8] hover:text-[#0A2463] dark:text-[#4FC3F7] dark:hover:text-[#1E5AA8] transition"
              >
                Esqueci minha senha
              </a>
            </div>
          )}
        </form>

        <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-600 text-center">
          {isRegistering ? (
            <button
              type="button"
              onClick={() => changeMode("login")}
              className="text-sm font-medium text-[#1E5AA8] hover:text-[#0A2463] dark:text-[#4FC3F7] dark:hover:text-white transition"
            >
              Já tenho uma conta
            </button>
          ) : (
            <>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                Ainda não possui acesso como aluno?
              </p>
              <button
                type="button"
                onClick={() => changeMode("register")}
                className="text-sm font-medium text-[#1E5AA8] hover:text-[#0A2463] dark:text-[#4FC3F7] dark:hover:text-white transition"
              >
                Cadastre-se como aluno
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
