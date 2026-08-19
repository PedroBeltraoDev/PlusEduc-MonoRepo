import { useEffect, useState } from "react";
import { BookOpen, ListTree, Loader2, Pencil, Plus, Save, Trash2, X } from "lucide-react";
import { Link } from "react-router";
import { toast } from "sonner";
import { subjectTopicsService } from "@/services";
import type { SubjectTopic } from "@/types";

export function MateriasTopicos() {
  const [items, setItems] = useState<SubjectTopic[]>([]);
  const [subject, setSubject] = useState("");
  const [initialTopic, setInitialTopic] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingSubject, setEditingSubject] = useState("");
  const [topicDrafts, setTopicDrafts] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [actionId, setActionId] = useState<string | null>(null);

  const loadItems = async () => {
    try {
      setLoading(true);
      setItems(await subjectTopicsService.getAll());
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Não foi possível carregar o catálogo.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadItems();
  }, []);

  const handleCreate = async () => {
    if (!subject.trim()) {
      toast.error("Informe o nome da matéria.");
      return;
    }

    try {
      setSaving(true);
      const created = await subjectTopicsService.create({
        subject: subject.trim(),
        topic: initialTopic.trim() || undefined,
      });
      setItems((current) => {
        const alreadyExists = current.some((item) => item.id === created.id);
        return alreadyExists ? current.map((item) => (item.id === created.id ? created : item)) : [...current, created];
      });
      setSubject("");
      setInitialTopic("");
      toast.success("Matéria salva no catálogo.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Não foi possível salvar a matéria.");
    } finally {
      setSaving(false);
    }
  };

  const handleRename = async (item: SubjectTopic) => {
    if (!editingSubject.trim()) {
      toast.error("Informe o nome da matéria.");
      return;
    }

    try {
      setActionId(item.id);
      const updated = await subjectTopicsService.update(item.id, {
        subject: editingSubject.trim(),
        topics: item.topics,
      });
      setItems((current) => current.map((entry) => (entry.id === updated.id ? updated : entry)));
      setEditingId(null);
      toast.success("Matéria atualizada.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Não foi possível atualizar a matéria.");
    } finally {
      setActionId(null);
    }
  };

  const handleTopicChange = async (item: SubjectTopic, topic: string, remove = false) => {
    const normalized = topic.trim();
    const topics = remove
      ? item.topics.filter((entry) => entry !== topic)
      : [...item.topics, normalized];

    if (!remove && !normalized) {
      toast.error("Informe o nome do tópico.");
      return;
    }

    try {
      setActionId(item.id);
      const updated = await subjectTopicsService.update(item.id, {
        subject: item.subject,
        topics,
      });
      setItems((current) => current.map((entry) => (entry.id === updated.id ? updated : entry)));
      setTopicDrafts((current) => ({ ...current, [item.id]: "" }));
      toast.success(remove ? "Tópico removido." : "Tópico adicionado.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Não foi possível atualizar os tópicos.");
    } finally {
      setActionId(null);
    }
  };

  const handleDelete = async (item: SubjectTopic) => {
    if (!window.confirm(`Excluir a matéria “${item.subject}” e seus tópicos?`)) {
      return;
    }

    try {
      setActionId(item.id);
      await subjectTopicsService.delete(item.id);
      setItems((current) => current.filter((entry) => entry.id !== item.id));
      toast.success("Matéria removida do catálogo.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Não foi possível excluir a matéria.");
    } finally {
      setActionId(null);
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
            <h1 className="text-2xl font-bold text-[#0A2463] dark:text-white">Matérias e tópicos</h1>
            <p className="mt-1 text-gray-600 dark:text-gray-300">
              Cadastre seus conteúdos uma vez e selecione-os ao criar novas atividades.
            </p>
          </div>
        </div>
      </header>

      <section className="rounded-2xl bg-white p-6 shadow-sm transition-colors dark:bg-gray-800">
        <div className="flex items-start gap-4 border-b border-gray-200 pb-5 dark:border-gray-700">
          <div className="rounded-xl bg-[#1E5AA8]/10 p-3 text-[#1E5AA8] dark:bg-blue-400/10 dark:text-[#4FC3F7]">
            <Plus className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-[#0A2463] dark:text-white">Nova matéria</h2>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
              Você pode cadastrar o primeiro tópico agora ou adicioná-lo depois.
            </p>
          </div>
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_1fr_auto] lg:items-end">
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-200">Matéria</span>
            <input
              value={subject}
              onChange={(event) => setSubject(event.target.value)}
              placeholder="Ex.: Matemática"
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-gray-900 outline-none transition focus:border-transparent focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
            />
          </label>
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-200">Primeiro tópico (opcional)</span>
            <input
              value={initialTopic}
              onChange={(event) => setInitialTopic(event.target.value)}
              placeholder="Ex.: Equações do Segundo Grau"
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-gray-900 outline-none transition focus:border-transparent focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
            />
          </label>
          <button
            type="button"
            onClick={handleCreate}
            disabled={saving}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#1E5AA8] px-5 py-3 font-semibold text-white transition hover:bg-[#0A2463] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            Adicionar
          </button>
        </div>
      </section>

      <section className="rounded-2xl bg-white p-6 shadow-sm transition-colors dark:bg-gray-800">
        <div className="flex items-center gap-3 border-b border-gray-200 pb-5 dark:border-gray-700">
          <div className="rounded-xl bg-emerald-100 p-3 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
            <ListTree className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-[#0A2463] dark:text-white">Meu catálogo</h2>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">Edite matérias e mantenha seus tópicos organizados.</p>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center gap-2 py-12 text-gray-500 dark:text-gray-400">
            <Loader2 className="h-5 w-5 animate-spin" />
            Carregando catálogo...
          </div>
        ) : items.length === 0 ? (
          <div className="py-12 text-center">
            <BookOpen className="mx-auto h-10 w-10 text-gray-400" />
            <p className="mt-3 font-semibold text-gray-700 dark:text-gray-200">Nenhuma matéria cadastrada ainda.</p>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Adicione uma matéria acima para começar.</p>
          </div>
        ) : (
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            {items.map((item) => {
              const isEditing = editingId === item.id;
              const isBusy = actionId === item.id;
              return (
                <article key={item.id} className="rounded-xl border border-gray-200 p-5 dark:border-gray-700">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      {isEditing ? (
                        <input
                          value={editingSubject}
                          onChange={(event) => setEditingSubject(event.target.value)}
                          className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 font-semibold text-gray-900 outline-none focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                          autoFocus
                        />
                      ) : (
                        <h3 className="truncate text-lg font-bold text-[#0A2463] dark:text-white">{item.subject}</h3>
                      )}
                    </div>
                    <div className="flex shrink-0 items-center gap-1">
                      {isEditing ? (
                        <>
                          <button type="button" onClick={() => void handleRename(item)} disabled={isBusy} className="rounded-lg p-2 text-emerald-600 transition hover:bg-emerald-50 dark:hover:bg-emerald-900/20" title="Salvar matéria">
                            <Save className="h-4 w-4" />
                          </button>
                          <button type="button" onClick={() => setEditingId(null)} className="rounded-lg p-2 text-gray-500 transition hover:bg-gray-100 dark:hover:bg-gray-700" title="Cancelar">
                            <X className="h-4 w-4" />
                          </button>
                        </>
                      ) : (
                        <>
                          <button type="button" onClick={() => { setEditingId(item.id); setEditingSubject(item.subject); }} className="rounded-lg p-2 text-[#1E5AA8] transition hover:bg-blue-50 dark:hover:bg-blue-900/20" title="Editar matéria">
                            <Pencil className="h-4 w-4" />
                          </button>
                          <button type="button" onClick={() => void handleDelete(item)} disabled={isBusy} className="rounded-lg p-2 text-rose-600 transition hover:bg-rose-50 dark:hover:bg-rose-900/20" title="Excluir matéria">
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    {item.topics.length > 0 ? item.topics.map((topic) => (
                      <span key={topic} className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-3 py-1.5 text-xs font-medium text-[#1E5AA8] dark:bg-blue-950/40 dark:text-blue-200">
                        {topic}
                        <button type="button" onClick={() => void handleTopicChange(item, topic, true)} disabled={isBusy} className="rounded-full p-0.5 hover:bg-blue-100 dark:hover:bg-blue-900/50" title={`Remover ${topic}`}>
                          <X className="h-3 w-3" />
                        </button>
                      </span>
                    )) : (
                      <span className="text-sm text-gray-500 dark:text-gray-400">Nenhum tópico cadastrado.</span>
                    )}
                  </div>

                  <div className="mt-5 flex gap-2">
                    <input
                      value={topicDrafts[item.id] ?? ""}
                      onChange={(event) => setTopicDrafts((current) => ({ ...current, [item.id]: event.target.value }))}
                      onKeyDown={(event) => { if (event.key === "Enter") void handleTopicChange(item, topicDrafts[item.id] ?? ""); }}
                      placeholder="Novo tópico"
                      className="min-w-0 flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                    />
                    <button type="button" onClick={() => void handleTopicChange(item, topicDrafts[item.id] ?? "")} disabled={isBusy} className="inline-flex items-center gap-1 rounded-lg border border-[#1E5AA8] px-3 py-2 text-sm font-semibold text-[#1E5AA8] transition hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-60 dark:text-[#4FC3F7] dark:hover:bg-blue-950/30">
                      <Plus className="h-4 w-4" />
                      Tópico
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      <p className="text-sm text-gray-500 dark:text-gray-400">
        Depois de cadastrar os itens, eles aparecerão como opções em <Link className="font-semibold text-[#1E5AA8] hover:underline" to="/nova-atividade">Nova atividade</Link> e <Link className="font-semibold text-[#1E5AA8] hover:underline" to="/gerar-atividade">Gerar atividade</Link>.
      </p>
    </div>
  );
}
