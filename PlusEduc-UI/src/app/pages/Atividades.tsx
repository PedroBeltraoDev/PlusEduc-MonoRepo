import { Link, useNavigate } from "react-router";
import { useState } from "react";
import { Plus, Wand2, ClipboardList, Calendar, Filter, Loader2, AlertCircle, Download, BookOpen, Search, MoreVertical } from "lucide-react";
import { useApiList } from "@/hooks/useApi";
import { activitiesService } from "@/services";
import type { Activity } from "@/types";
import { formatDate } from "@/utils";

export function Atividades() {
  const navigate = useNavigate();
  const {
    data: activities,
    loading,
    error,
    searchTerm,
    setSearchTerm,
    refetch,
    isEmpty,
    total
  } = useApiList(() => activitiesService.getAllActivities());

  const [isExporting, setIsExporting] = useState<string | null>(null);

  // Calcular estatísticas
  const aiGeneratedActivities = activities?.filter(a => a.generatedByAi) || [];
  const thisWeekActivities = activities?.filter(a => {
    const activityDate = new Date(a.createdAt);
    const oneWeekAgo = new Date();
    oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
    return activityDate >= oneWeekAgo;
  }) || [];

  const getStatusInfo = (activity: Activity) => {
    const daysSinceCreated = Math.floor(
      (Date.now() - new Date(activity.createdAt).getTime()) / (1000 * 60 * 60 * 24)
    );

    if (daysSinceCreated <= 1) {
      return { status: 'Nova', color: 'bg-[#4FC3F7] text-white' };
    } else if (daysSinceCreated <= 7) {
      return { status: 'Recente', color: 'bg-[#FF9800] text-white' };
    } else {
      return { status: 'Antiga', color: 'bg-gray-400 text-white' };
    }
  };

  const getDifficultyColor = (level: string) => {
    switch (level) {
      case 'EASY':
      case 'FACIL':
        return 'bg-[#4CAF50] text-white';
      case 'MEDIUM':
      case 'MEDIO':
        return 'bg-[#FF9800] text-white';
      case 'HARD':
      case 'DIFICIL':
        return 'bg-[#F44336] text-white';
      default: return 'bg-gray-400 text-white';
    }
  };

  const getDifficultyText = (level: string) => {
    switch (level) {
      case 'EASY':
      case 'FACIL':
        return 'Fácil';
      case 'MEDIUM':
      case 'MEDIO':
        return 'Médio';
      case 'HARD':
      case 'DIFICIL':
        return 'Difícil';
      default: return level;
    }
  };

  const handleDownloadPDF = async (activity: Activity) => {
    try {
      setIsExporting(activity.id);
      await activitiesService.downloadActivityPDF(activity.id, false);
    } catch (err) {
      console.error('Erro ao baixar PDF:', err);
      // TODO: Mostrar notificação de erro
    } finally {
      setIsExporting(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex items-center gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-[#1E5AA8]" />
          <span className="text-lg text-gray-600 dark:text-gray-300">Carregando atividades...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">Erro ao carregar atividades</h2>
          <p className="text-gray-600 dark:text-gray-300 mb-4">{error}</p>
          <button
            onClick={refetch}
            className="bg-[#1E5AA8] hover:bg-[#0A2463] text-white px-6 py-2 rounded-lg transition"
          >
            Tentar novamente
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-[#0A2463] dark:text-white">Atividades</h1>
          <p className="text-gray-600 dark:text-gray-300 mt-2">Gerencie e crie atividades para suas turmas</p>
        </div>
        <div className="flex gap-3">
          <Link
            to="/gerar-atividade"
            className="bg-gradient-to-r from-[#1E5AA8] to-[#4FC3F7] hover:from-[#0A2463] hover:to-[#1E5AA8] text-white px-6 py-3 rounded-lg font-semibold flex items-center gap-2 shadow-md hover:shadow-lg transition-all"
          >
            <Wand2 className="w-5 h-5" />
            Gerar com IA
            <span className="ml-1 px-2 py-0.5 bg-white/20 text-xs rounded-full">Novo</span>
          </Link>
          <Link
            to="/nova-atividade"
            className="border-2 border-[#1E5AA8] dark:border-[#4FC3F7] text-[#1E5AA8] dark:text-[#4FC3F7] hover:bg-[#1E5AA8] dark:hover:bg-[#4FC3F7] hover:text-white dark:hover:text-gray-900 px-6 py-3 rounded-lg font-semibold flex items-center gap-2 transition-all"
          >
            <Plus className="w-5 h-5" />
            Nova Atividade
          </Link>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-colors">
          <div className="flex items-center gap-3 mb-2">
            <ClipboardList className="w-6 h-6 text-[#1E5AA8] dark:text-[#4FC3F7]" />
            <h3 className="font-semibold text-gray-700 dark:text-gray-200">Total de Atividades</h3>
          </div>
          <p className="text-3xl font-bold text-[#0A2463] dark:text-white">{total}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{activities.length} disponíveis</p>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-colors">
          <div className="flex items-center gap-3 mb-2">
            <Calendar className="w-6 h-6 text-[#4CAF50]" />
            <h3 className="font-semibold text-gray-700 dark:text-gray-200">Esta Semana</h3>
          </div>
          <p className="text-3xl font-bold text-[#0A2463] dark:text-white">{thisWeekActivities.length}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">criadas recentemente</p>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-colors">
          <div className="flex items-center gap-3 mb-2">
            <Filter className="w-6 h-6 text-[#FF9800]" />
            <h3 className="font-semibold text-gray-700 dark:text-gray-200">Geradas com IA</h3>
          </div>
          <p className="text-3xl font-bold text-[#0A2463] dark:text-white">{aiGeneratedActivities.length}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {total > 0 ? Math.round((aiGeneratedActivities.length / total) * 100) : 0}% do total
          </p>
        </div>
      </div>

      {/* Search Bar */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 transition-colors">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 dark:text-gray-500" />
          <input
            type="text"
            placeholder="Buscar por título, disciplina ou tópico..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-11 pr-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition"
          />
        </div>
      </div>

      {/* Lista de Atividades */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-colors">
        <h2 className="text-xl font-bold text-[#0A2463] dark:text-white mb-4">
          {searchTerm ? `Resultados da busca (${activities.length})` : 'Todas as Atividades'}
        </h2>

        {isEmpty ? (
          <div className="text-center py-12">
            <BookOpen className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              {searchTerm ? 'Nenhuma atividade encontrada' : 'Nenhuma atividade cadastrada'}
            </h3>
            <p className="text-gray-500 dark:text-gray-400 mb-6">
              {searchTerm
                ? 'Tente ajustar os termos da busca'
                : 'Comece criando ou gerando sua primeira atividade'
              }
            </p>
            {!searchTerm && (
              <div className="flex gap-3 justify-center">
                <Link
                  to="/gerar-atividade"
                  className="bg-[#1E5AA8] hover:bg-[#0A2463] text-white px-6 py-3 rounded-lg font-semibold flex items-center gap-2 transition"
                >
                  <Wand2 className="w-5 h-5" />
                  Gerar com IA
                </Link>
                <Link
                  to="/nova-atividade"
                  className="border-2 border-[#1E5AA8] text-[#1E5AA8] hover:bg-[#1E5AA8] hover:text-white px-6 py-3 rounded-lg font-semibold flex items-center gap-2 transition"
                >
                  <Plus className="w-5 h-5" />
                  Nova Atividade
                </Link>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {activities.map((activity) => {
              const statusInfo = getStatusInfo(activity);
              return (
                <div
                  key={activity.id}
                  role="button"
                  tabIndex={0}
                  aria-label={`Abrir atividade ${activity.title}`}
                  onClick={() => navigate(`/atividades/${activity.id}`)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      navigate(`/atividades/${activity.id}`);
                    }
                  }}
                  className="flex cursor-pointer items-center justify-between rounded-lg bg-gray-50 p-4 transition-colors hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-[#1E5AA8] dark:bg-gray-700 dark:hover:bg-gray-600"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-semibold text-[#0A2463] dark:text-white truncate">
                        {activity.title}
                      </h3>
                      {activity.generatedByAi && (
                        <span className="px-2 py-1 bg-gradient-to-r from-[#1E5AA8] to-[#4FC3F7] text-white text-xs rounded-full font-medium">
                          IA
                        </span>
                      )}
                      <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getDifficultyColor(activity.difficultyLevel)}`}>
                        {getDifficultyText(activity.difficultyLevel)}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-300">
                      <span>{activity.subject}</span>
                      <span>•</span>
                      <span>{activity.topic}</span>
                      <span>•</span>
                      <span>{formatDate(activity.createdAt)}</span>
                      <span>•</span>
                      <span>{activity.questionsCount} questões</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold ${statusInfo.color}`}>
                      {statusInfo.status}
                    </span>
                    <button
                      onClick={(event) => {
                        event.stopPropagation();
                        handleDownloadPDF(activity);
                      }}
                      disabled={isExporting === activity.id}
                      className="p-2 text-gray-400 hover:text-[#1E5AA8] dark:hover:text-[#4FC3F7] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      title="Baixar PDF"
                    >
                      {isExporting === activity.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Download className="w-4 h-4" />
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={(event) => event.stopPropagation()}
                      className="p-2 text-gray-400 transition-colors hover:text-gray-600 dark:hover:text-gray-300"
                    >
                      <MoreVertical className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
