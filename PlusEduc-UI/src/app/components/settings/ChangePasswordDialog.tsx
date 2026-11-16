import { useState } from "react";
import { Key, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";
import { FeedbackMessage } from "@/motion/primitives";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "../ui/dialog";

/**
 * Troca de senha real (POST /api/auth/change-password). Antes o botão só exibia
 * "Um link foi enviado para seu e-mail" sem fazer nada.
 */
export function ChangePasswordDialog() {
  const { changePassword } = useAuth();
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const reset = () => {
    setCurrent("");
    setNext("");
    setConfirm("");
    setError("");
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (next.length < 6) {
      setError("A nova senha precisa ter pelo menos 6 caracteres.");
      return;
    }
    if (next !== confirm) {
      setError("A confirmação não confere com a nova senha.");
      return;
    }
    try {
      setSaving(true);
      await changePassword(current, next);
      toast.success("Senha alterada. As outras sessões abertas foram encerradas.");
      setOpen(false);
      reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível alterar a senha.");
    } finally {
      setSaving(false);
    }
  };

  const field = "w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-gray-900 outline-none focus:border-transparent focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100";

  return (
    <Dialog
      open={open}
      onOpenChange={(value) => {
        setOpen(value);
        if (!value) reset();
      }}
    >
      <DialogTrigger asChild>
        <button
          type="button"
          className="inline-flex items-center gap-2 px-2 py-3 font-medium text-[#1E5AA8] transition hover:text-[#0A2463] dark:text-[#4FC3F7] dark:hover:text-white"
        >
          <Key className="h-4 w-4" />
          Alterar senha
        </button>
      </DialogTrigger>
      <DialogContent className="dark:bg-gray-800">
        <DialogHeader>
          <DialogTitle className="text-[#0A2463] dark:text-white">Alterar senha</DialogTitle>
          <DialogDescription>Depois da troca, as sessões abertas em outros aparelhos são encerradas.</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4">
          <FeedbackMessage show={Boolean(error)} tone="error" messageKey={error}>
            <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">{error}</p>
          </FeedbackMessage>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-200">Senha atual</span>
            <input type="password" autoComplete="current-password" required value={current} onChange={(e) => setCurrent(e.target.value)} className={field} disabled={saving} />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-200">Nova senha</span>
            <input type="password" autoComplete="new-password" required minLength={6} value={next} onChange={(e) => setNext(e.target.value)} className={field} disabled={saving} />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-200">Confirmar nova senha</span>
            <input type="password" autoComplete="new-password" required minLength={6} value={confirm} onChange={(e) => setConfirm(e.target.value)} className={field} disabled={saving} />
          </label>
          <button
            type="submit"
            disabled={saving}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-[#1E5AA8] px-4 py-3 font-semibold text-white hover:bg-[#0A2463] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            {saving ? "Salvando..." : "Salvar nova senha"}
          </button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
