import { useState } from "react";
import { Key, Loader2, Lock } from "lucide-react";
import { toast } from "sonner";
import { authService } from "@/services";

const inputClass =
  "w-full rounded-lg border border-gray-300 bg-white py-3 pl-10 pr-4 text-gray-900 outline-none transition focus:border-transparent focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100";

// Troca de senha pelo próprio usuário logado (RF03): usada nas configurações do professor/admin e do aluno.
export function ChangePasswordCard() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (newPassword.length < 6) {
      setError("A nova senha deve ter pelo menos 6 caracteres.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("A confirmação não confere com a nova senha.");
      return;
    }
    if (newPassword === currentPassword) {
      setError("A nova senha deve ser diferente da senha atual.");
      return;
    }
    try {
      setIsSaving(true);
      await authService.changePassword({ currentPassword, newPassword });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      toast.success("Senha alterada com sucesso. Use a nova senha no próximo acesso.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível alterar a senha.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <section className="rounded-2xl bg-white p-6 shadow-sm transition-colors dark:bg-gray-800">
      <div className="flex items-start gap-4 border-b border-gray-200 pb-5 dark:border-gray-700">
        <div className="rounded-xl bg-[#1E5AA8]/10 p-3 text-[#1E5AA8] dark:bg-blue-400/10 dark:text-[#4FC3F7]">
          <Key className="h-6 w-6" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-[#0A2463] dark:text-white">Alterar senha</h2>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
            Informe a senha atual e escolha uma nova, com pelo menos 6 caracteres.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="mt-6 grid gap-4 md:grid-cols-3">
        {[
          { id: "current-password", label: "Senha atual", value: currentPassword, set: setCurrentPassword, auto: "current-password" },
          { id: "new-password", label: "Nova senha", value: newPassword, set: setNewPassword, auto: "new-password" },
          { id: "confirm-password", label: "Confirmar nova senha", value: confirmPassword, set: setConfirmPassword, auto: "new-password" },
        ].map((field) => (
          <label key={field.id} htmlFor={field.id} className="block">
            <span className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-200">{field.label}</span>
            <span className="relative block">
              <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                id={field.id}
                type="password"
                value={field.value}
                onChange={(event) => field.set(event.target.value)}
                autoComplete={field.auto}
                required
                disabled={isSaving}
                className={inputClass}
              />
            </span>
          </label>
        ))}

        {error && (
          <p role="alert" className="text-sm text-red-600 dark:text-red-400 md:col-span-3">
            {error}
          </p>
        )}

        <div className="md:col-span-3">
          <button
            type="submit"
            disabled={isSaving}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#1E5AA8] px-5 py-3 font-semibold text-white transition hover:bg-[#0A2463] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Key className="h-4 w-4" />}
            {isSaving ? "Salvando..." : "Salvar nova senha"}
          </button>
        </div>
      </form>
    </section>
  );
}
