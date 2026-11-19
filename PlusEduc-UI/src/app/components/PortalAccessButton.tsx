import { useState } from "react";
import { KeyRound, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { studentsService } from "@/services";
import type { Student } from "@/types";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";

interface PortalAccessButtonProps {
  student: Student;
  onEnabled: () => void;
}

const inputClass =
  "w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-gray-900 outline-none focus:border-transparent focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100";

// Aluno cadastrado pela escola ainda sem login: a equipe define a senha inicial e libera o Portal do Aluno.
export function PortalAccessButton({ student, onEnabled }: PortalAccessButtonProps) {
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  if (student.hasPortalAccess !== false) {
    return null;
  }

  const close = (value: boolean) => {
    setOpen(value);
    if (!value) {
      setPassword("");
      setConfirm("");
      setError("");
    }
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (password.length < 6) {
      setError("A senha inicial deve ter pelo menos 6 caracteres.");
      return;
    }
    if (password !== confirm) {
      setError("A confirmação não confere com a senha.");
      return;
    }
    try {
      setSaving(true);
      await studentsService.enableStudentAccess(student.id, password);
      toast.success(`Acesso ao portal liberado para ${student.name}. Informe a senha inicial ao aluno.`);
      close(false);
      onEnabled();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível liberar o acesso.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          setOpen(true);
        }}
        className="flex items-center gap-2 rounded-lg bg-[#4CAF50] px-4 py-2 text-white transition-colors hover:bg-green-700"
      >
        <KeyRound className="h-4 w-4" />
        Liberar acesso ao portal
      </button>
      <Dialog open={open} onOpenChange={close}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Liberar acesso ao portal</DialogTitle>
            <DialogDescription>
              {student.name} entrará no Portal do Aluno com o e-mail {student.email} e a senha inicial definida aqui.
              Depois, o aluno pode trocá-la em Configurações.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={submit} className="space-y-3">
            <div>
              <label htmlFor="portal-password" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-200">Senha inicial</label>
              <input id="portal-password" type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} className={inputClass} />
            </div>
            <div>
              <label htmlFor="portal-password-confirm" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-200">Confirmar senha</label>
              <input id="portal-password-confirm" type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} className={inputClass} />
            </div>
            {error && <p className="text-sm text-red-600 dark:text-red-400" role="alert">{error}</p>}
            <DialogFooter>
              <button type="button" onClick={() => close(false)} className="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700">
                Cancelar
              </button>
              <button type="submit" disabled={saving} className="inline-flex items-center gap-2 rounded-lg bg-[#1E5AA8] px-4 py-2 font-semibold text-white hover:bg-[#0A2463] disabled:opacity-60">
                {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                Liberar acesso
              </button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
