import { useState, useEffect } from "react";
import { useNavigate } from "react-router";
import { Users, GraduationCap, ClipboardList, TrendingUp, CheckCircle, Clock, AlertCircle, Loader2 } from "lucide-react";
import { studentsService, classroomsService, activitiesService } from "@/services";
import type { ClassroomPerformance } from "@/services/classrooms";
import type { Classroom, Activity } from "@/types";
import { formatDate } from "@/utils";

interface DashboardStats {
  totalStudents: number;
  totalClassrooms: number;
  totalActivities: number;
  recentActivities: number;
}

export function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats>({
    totalStudents: 0,
    totalClassrooms: 0,
    totalActivities: 0,
    recentActivities: 0
  });
  const [recentActivities, setRecentActivities] = useState<Activity[]>([]);
  const [classroomsSummary, setClassroomsSummary] = useState<{
    classroom: Classroom;
    studentsCount: number;
    activitiesCount: number;
    performance: ClassroomPerformance | null;
  }[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Carregar dados em paralelo
      const [students, classrooms, activities] = await Promise.all([
        studentsService.getAllStudents(),
        classroomsService.getAllClassrooms(),
        activitiesService.getAllActivities()
      ]);

      // Calcular estatísticas
      const activeStudents = students?.filter(s => s.active) || [];
      const activeClassrooms = classrooms?.filter(c => c.active) || [];
      const recentActivitiesData = activities
        ?.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
        ?.slice(0, 5) || [];

      setStats({
        totalStudents: activeStudents.length,
        totalClassrooms: activeClassrooms.length,
        totalActivities: activities?.length || 0,
        recentActivities: recentActivitiesData.length
      });

      setRecentActivities(recentActivitiesData);

      // Preparar resumo das turmas
      const classroomsSummaryData = await Promise.all(
        activeClassrooms.slice(0, 4).map(async (classroom) => {
          const classroomActivities = activities?.filter(a => a.classroomId === classroom.id) || [];
          const performance = await classroomsService
            .getClassroomPerformance(classroom.id)
            .catch(() => null);
          return {
            classroom,
            studentsCount: classroom.studentIds?.length || 0,
            activitiesCount: classroomActivities.length,
            performance,
          };
        })
      );

      setClassroomsSummary(classroomsSummaryData);
    } catch (err) {
      console.error('Erro ao carregar dashboard:', err);
      setError('Erro ao carregar dados do dashboard');
    } finally {
      setIsLoading(false);
    }
  };

  const getActivityStatus = (activity: Activity) => {
    // Para demonstração, vamos simular diferentes status
    const daysSinceCreated = Math.floor(
      (Date.now() - new Date(activity.createdAt).getTime()) / (1000 * 60 * 60 * 24)
    );

    if (daysSinceCreated <= 1) {
      return {
        status: 'Novo',
        color: 'text-[#4FC3F7]',
        icon: Clock
      };
    } else if (daysSinceCreated <= 7) {
      return {
        status: 'Em andamento',
        color: 'text-[#FF9800]',
        icon: Clock
      };
    } else {
      return {
        status: 'Finalizada',
        color: 'text-[#4CAF50]',
        icon: CheckCircle
      };
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex items-center gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-[#1E5AA8]" />
          <span className="text-lg text-gray-600 dark:text-gray-300">Carregando dashboard...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">Erro ao carregar dashboard</h2>
          <p className="text-gray-600 dark:text-gray-300 mb-4">{error}</p>
          <button
            onClick={loadDashboardData}
            className="bg-[#1E5AA8] hover:bg-[#0A2463] text-white px-6 py-2 rounded-lg transition"
          >
            Tentar novamente
          </button>
        </div>
      </div>
    );
  }

  const evaluatedClassrooms = classroomsSummary.filter(
    (item) => item.performance && item.performance.subjectPerformance.length > 0,
  );
  const overallPerformance = evaluatedClassrooms.length > 0
    ? evaluatedClassrooms.reduce((total, item) => total + (item.performance?.averageGrade || 0), 0) / evaluatedClassrooms.length
    : null;
  const formatPerformance = (value: number) => value.toLocaleString("pt-BR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 2,
  });

  const statsCards = [
    {
      icon: Users,
      label: "Total de Turmas",
      value: stats.totalClassrooms.toString(),
      change: `${stats.totalClassrooms} ativas`,
      color: "bg-[#1E5AA8]"
    },
    {
      icon: GraduationCap,
      label: "Total de Alunos",
      value: stats.totalStudents.toString(),
      change: `${stats.totalStudents} ativos`,
      color: "bg-[#4FC3F7]"
    },
    {
      icon: ClipboardList,
      label: "Total de Atividades",
      value: stats.totalActivities.toString(),
      change: `${stats.recentActivities} recentes`,
      color: "bg-[#FF9800]"
    },
    {
      icon: TrendingUp,
      label: "Performance",
      value: overallPerformance !== null ? `${formatPerformance(overallPerformance)}/10` : "Sem notas",
      change: evaluatedClassrooms.length > 0
        ? `${evaluatedClassrooms.length} turma${evaluatedClassrooms.length === 1 ? "" : "s"} avaliada${evaluatedClassrooms.length === 1 ? "" : "s"}`
        : "Adicione notas para calcular",
      color: "bg-[#4CAF50]"
    },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-[#0A2463] dark:text-white">Dashboard</h1>
        <p className="text-gray-600 dark:text-gray-300 mt-2">
          Bem-vindo de volta! Aqui está um resumo da sua plataforma educacional.
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
        {statsCards.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <div key={index} className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 hover:shadow-lg transition-all">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0 pr-4">
                  <p className="text-gray-600 dark:text-gray-300 text-sm mb-2">{stat.label}</p>
                  <p className="text-2xl lg:text-3xl font-bold text-[#0A2463] dark:text-white mb-1 break-words">
                    {stat.value}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{stat.change}</p>
                </div>
                <div className={`${stat.color} p-3 rounded-lg flex-shrink-0`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Activities */}
        <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-colors">
          <h2 className="text-xl font-bold text-[#0A2463] dark:text-white mb-4">Atividades Recentes</h2>

          {recentActivities.length === 0 ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <ClipboardList className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>Nenhuma atividade encontrada</p>
            </div>
          ) : (
            <div className="space-y-3">
              {recentActivities.map((activity) => {
                const statusInfo = getActivityStatus(activity);
                const StatusIcon = statusInfo.icon;

                return (
                  <div
                    key={activity.id}
                    role="button"
                    tabIndex={0}
                    title="Abrir atividade no modo professor"
                    aria-label={`Abrir atividade ${activity.title}`}
                    onClick={() => navigate(`/atividades/${activity.id}`)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        navigate(`/atividades/${activity.id}`);
                      }
                    }}
                    className="flex cursor-pointer items-center gap-4 rounded-lg bg-gray-50 p-4 transition-colors hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-[#1E5AA8] dark:bg-gray-700 dark:hover:bg-gray-600"
                  >
                    <StatusIcon className={`w-5 h-5 ${statusInfo.color} flex-shrink-0`} />
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-[#0A2463] dark:text-white truncate">
                        {activity.title}
                      </h3>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {formatDate(activity.createdAt)}
                        </span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">•</span>
                        <span className="text-xs text-gray-600 dark:text-gray-300">
                          {activity.subject} • {activity.difficultyLevel}
                        </span>
                      </div>
                    </div>
                    <span className={`text-sm font-medium ${statusInfo.color} flex-shrink-0`}>
                      {statusInfo.status}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Classrooms Summary */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-colors">
          <h2 className="text-xl font-bold text-[#0A2463] dark:text-white mb-4">Resumo de Turmas</h2>

          {classroomsSummary.length === 0 ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <Users className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>Nenhuma turma encontrada</p>
            </div>
          ) : (
            <div className="space-y-4">
              {classroomsSummary.map((item) => (
                <div key={item.classroom.id} className="border-l-4 border-[#1E5AA8] dark:border-[#4FC3F7] pl-4 py-2">
                  <h3 className="font-semibold text-[#0A2463] dark:text-white">
                    {item.classroom.name}
                  </h3>
                  <div className="mt-2 space-y-1">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600 dark:text-gray-300">Alunos:</span>
                      <span className="font-medium text-[#0A2463] dark:text-white">
                        {item.studentsCount}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600 dark:text-gray-300">Atividades:</span>
                      <span className="font-medium text-[#0A2463] dark:text-white">
                        {item.activitiesCount}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600 dark:text-gray-300">Ano:</span>
                      <span className="font-medium text-[#4CAF50]">
                        {item.classroom.year}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600 dark:text-gray-300">Performance:</span>
                      <span className="font-semibold text-[#4CAF50]">
                        {item.performance === null
                          ? "Indisponível"
                          : item.performance.subjectPerformance.length > 0
                            ? `${formatPerformance(item.performance.averageGrade)}/10`
                            : "Sem notas"}
                      </span>
                    </div>
                    {item.performance && item.performance.subjectPerformance.length > 0 && (
                      <div className="mt-2 space-y-1 border-t border-gray-200 pt-2 dark:border-gray-600">
                        {item.performance.subjectPerformance.slice(0, 3).map((subject) => (
                          <div key={subject.subject} className="flex justify-between gap-2 text-xs">
                            <span className="truncate text-gray-500 dark:text-gray-400">{subject.subject}</span>
                            <span className="font-medium text-gray-700 dark:text-gray-200">
                              {formatPerformance(subject.average)}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
