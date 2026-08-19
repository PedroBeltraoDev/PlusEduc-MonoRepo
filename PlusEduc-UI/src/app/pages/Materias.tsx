import { useEffect, useState } from "react";
import { ArrowRight, BookOpen, Loader2, Plus } from "lucide-react";
import { Link } from "react-router";
import { toast } from "sonner";
import { subjectsService } from "@/services";
import type { Subject } from "@/types";

export function Materias() {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const loadSubjects = async () => {
    try {
      setLoading(true);
      setSubjects(await subjectsService.getAll());
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Não foi possível carregar as matérias.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadSubjects();
  }, []);

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
              <Link
                key={subject.id}
                to={`/materias/${subject.id}/turmas`}
                className="group flex items-center justify-between rounded-xl border border-gray-200 p-5 transition hover:-translate-y-0.5 hover:border-[#1E5AA8] hover:shadow-md dark:border-gray-700 dark:hover:border-[#4FC3F7]"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <div className="rounded-lg bg-[#1E5AA8]/10 p-3 text-[#1E5AA8] dark:bg-blue-400/10 dark:text-[#4FC3F7]">
                    <BookOpen className="h-5 w-5" />
                  </div>
                  <span className="truncate font-semibold text-[#0A2463] dark:text-white">{subject.name}</span>
                </div>
                <ArrowRight className="h-5 w-5 shrink-0 text-gray-400 transition group-hover:translate-x-1 group-hover:text-[#1E5AA8] dark:group-hover:text-[#4FC3F7]" />
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
