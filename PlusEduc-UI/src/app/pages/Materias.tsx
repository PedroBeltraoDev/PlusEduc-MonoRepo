import { useEffect, useState } from "react";
import { ArrowRight, BookOpen, Loader2, MoreVertical, Plus, Trash2 } from "lucide-react";
import { Link } from "react-router";
import { toast } from "sonner";
import { subjectsService } from "@/services";
import type { Subject } from "@/types";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/app/components/ui/alert-dialog";

export function Materias() {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [openSubjectMenuId, setOpenSubjectMenuId] = useState<string | null>(null);
  const [subjectToDelete, setSubjectToDelete] = useState<Subject | null>(null);
  const [deletingSubjectId, setDeletingSubjectId] = useState<string | null>(null);

  const loadSubjects = async () => {
    try {
      setLoading(true);
      const catalog = await subjectsService.getAll();
      setSubjects(catalog.filter((subject) => subject.active !== false));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Não foi possível carregar as matérias.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadSubjects();
  }, []);

  const handleDelete = async () => {
    if (!subjectToDelete) return;

    const subjectId = subjectToDelete.id;
    try {
      setDeletingSubjectId(subjectId);
      await subjectsService.delete(subjectId);
      setSubjects((current) => current.filter((item) => item.id !== subjectId));
      setSubjectToDelete(null);
      setOpenSubjectMenuId(null);
      toast.success("Matéria apagada com sucesso.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Não foi possível apagar a matéria.");
    } finally {
      setDeletingSubjectId(null);
    }
  };

  const handleCreate = async () => {
    if (!name.trim()) {
      toast.error("Informe o nome da matéria.");
      return;
    }
    try {
      setSaving(true);
      const created = await subjectsService.create({ name: name.trim() });
      setSubjects((current) => current.some((item) => item.id === created.id)
        ? current.map((item) => item.id === created.id ? created : item)
        : [...current, created]);
      setName("");
      toast.success("Matéria cadastrada.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Não foi possível cadastrar a matéria.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <header>
        <div className="flex items-start gap-3">
          <div className="rounded-xl bg-[#1E5AA8] p-3 text-white shadow-sm">
            <BookOpen className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-[#0A2463] dark:text-white">Minhas matérias</h1>
            <p className="mt-1 text-gray-600 dark:text-gray-300">
              Escolha uma matéria para visualizar as turmas em que você leciona.
            </p>
          </div>
        </div>
      </header>

      <section className="rounded-2xl bg-white p-6 shadow-sm dark:bg-gray-800">
        <div className="flex items-center gap-3 border-b border-gray-200 pb-5 dark:border-gray-700">
          <div className="rounded-xl bg-blue-50 p-3 text-[#1E5AA8] dark:bg-blue-950/40 dark:text-[#7FC8F8]">
            <Plus className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-[#0A2463] dark:text-white">Cadastrar matéria</h2>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">Use o mesmo nome que aparece nas turmas.</p>
          </div>
        </div>
        <div className="mt-5 flex flex-col gap-3 sm:flex-row">
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            onKeyDown={(event) => { if (event.key === "Enter") void handleCreate(); }}
            placeholder="Ex.: Matemática"
            className="min-w-0 flex-1 rounded-lg border border-gray-300 bg-white px-4 py-3 text-gray-900 outline-none focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
          />
          <button
            type="button"
            onClick={() => void handleCreate()}
            disabled={saving}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#1E5AA8] px-5 py-3 font-semibold text-white transition hover:bg-[#0A2463] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            Adicionar matéria
          </button>
        </div>
      </section>

      <section className="rounded-2xl bg-white p-6 shadow-sm dark:bg-gray-800">
        <div className="flex items-center justify-between border-b border-gray-200 pb-5 dark:border-gray-700">
          <div>
            <h2 className="text-lg font-semibold text-[#0A2463] dark:text-white">Disciplinas cadastradas</h2>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">Clique em uma matéria para continuar.</p>
          </div>
          <span className="rounded-full bg-blue-50 px-3 py-1 text-sm font-semibold text-[#1E5AA8] dark:bg-blue-950/40 dark:text-[#7FC8F8]">
            {subjects.length} matéria{subjects.length === 1 ? "" : "s"}
          </span>
        </div>

        {loading ? (
          <div className="flex items-center justify-center gap-2 py-12 text-gray-500 dark:text-gray-400">
            <Loader2 className="h-5 w-5 animate-spin" /> Carregando matérias...
          </div>
        ) : subjects.length === 0 ? (
          <div className="py-12 text-center text-gray-500 dark:text-gray-400">
            <BookOpen className="mx-auto h-10 w-10" />
            <p className="mt-3 font-semibold">Nenhuma matéria cadastrada.</p>
            <p className="mt-1 text-sm">Cadastre a primeira matéria acima.</p>
          </div>
        ) : (
          <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {subjects.map((subject) => (
              <div
                key={subject.id}
                className="relative flex items-center rounded-xl border border-gray-200 transition hover:-translate-y-0.5 hover:border-[#1E5AA8] hover:shadow-md dark:border-gray-700 dark:hover:border-[#4FC3F7]"
              >
                <Link
                  to={`/materias/${subject.id}/turmas`}
                  className="group flex min-w-0 flex-1 items-center justify-between p-5 pr-2"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="rounded-lg bg-[#1E5AA8]/10 p-3 text-[#1E5AA8] dark:bg-blue-400/10 dark:text-[#4FC3F7]">
                      <BookOpen className="h-5 w-5" />
                    </div>
                    <span className="truncate font-semibold text-[#0A2463] dark:text-white">{subject.name}</span>
                  </div>
                  <ArrowRight className="h-5 w-5 shrink-0 text-gray-400 transition group-hover:translate-x-1 group-hover:text-[#1E5AA8] dark:group-hover:text-[#4FC3F7]" />
                </Link>
                <div className="relative pr-3">
                  <button
                    type="button"
                    aria-label={`Mais opções da matéria ${subject.name}`}
                    aria-expanded={openSubjectMenuId === subject.id}
                    onClick={() => setOpenSubjectMenuId((current) => current === subject.id ? null : subject.id)}
                    className="rounded-md p-2 text-gray-400 transition-colors hover:text-gray-700 dark:hover:text-gray-200"
                    title="Mais opções"
                  >
                    <MoreVertical className="h-4 w-4" />
                  </button>
                  {openSubjectMenuId === subject.id && (
                    <div className="absolute right-0 top-full z-30 mt-2 min-w-44 overflow-hidden rounded-lg border border-gray-200 bg-white p-1 shadow-xl dark:border-gray-600 dark:bg-gray-800">
                      <button
                        type="button"
                        onClick={() => {
                          setOpenSubjectMenuId(null);
                          setSubjectToDelete(subject);
                        }}
                        className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm font-medium text-red-600 transition-colors hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/40"
                      >
                        <Trash2 className="h-4 w-4" />
                        Apagar matéria
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <AlertDialog
        open={subjectToDelete !== null}
        onOpenChange={(open) => {
          if (!open && !deletingSubjectId) setSubjectToDelete(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Apagar matéria?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta ação apagará a matéria
              {subjectToDelete ? ` “${subjectToDelete.name}”` : ""} da sua lista. Os dados não poderão ser recuperados.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deletingSubjectId !== null}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              disabled={deletingSubjectId !== null}
              onClick={(event) => {
                event.preventDefault();
                void handleDelete();
              }}
              className="bg-red-600 text-white hover:bg-red-700 focus:ring-red-600"
            >
              {deletingSubjectId !== null ? "Apagando..." : "Sim, apagar matéria"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
