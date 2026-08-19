import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router";
import { createPortal } from "react-dom";
import { Plus, Search, MoreVertical, Users, Calendar, TrendingUp, Loader2, AlertCircle, BookOpen, ArrowLeft, GraduationCap, UserCheck, User, Mail, Hash, ArrowRightLeft, Trash2, ClipboardList, Download } from "lucide-react";
import { useApiList, useApi } from "@/hooks/useApi";
import { activitiesService, classroomsService, studentsService, CreateClassroomRequest } from "@/services";
import type { Activity, Classroom, Student, LearningGap } from "@/types";
import { formatDate } from "@/utils";
import { toast } from "sonner";

type ViewMode = 'classrooms' | 'classroom-details' | 'student-details';

// Tipo para os dados do formulário de estudante
interface StudentFormData {
  name: string;
  email: string;
  birthDate: string;
  classId: string;
  active: boolean;
  learningGaps: (LearningGap & { _formId: string })[];
}

const createFormId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

const createEmptyLearningGap = (): LearningGap & { _formId: string } => ({
  _formId: createFormId(),
  subject: '',
  topic: '',
  severity: 'LOW',
  description: '',
  identifiedDate: null,
  improvementStatus: 'IDENTIFIED',
});

// Componente de Modal como Portal
const StudentModal = ({
  isOpen,
  onClose,
  editingStudent,
  studentFormData,
  setStudentFormData,
  classrooms,
  isSubmitting,
  onSubmit
}: {
  isOpen: boolean;
  onClose: () => void;
  editingStudent: Student | null;
  studentFormData: StudentFormData;
  setStudentFormData: (data: StudentFormData | ((prev: StudentFormData) => StudentFormData)) => void;
  classrooms: Classroom[] | undefined;
  isSubmitting: boolean;
  onSubmit: (e: React.FormEvent) => void;
}) => {
  useEffect(() => {
    if (isOpen) {
      console.log('=== MODAL PORTAL ABERTO ===');
      document.body.style.overflow = 'hidden';
    } else {
      console.log('=== MODAL PORTAL FECHADO ===');
      document.body.style.overflow = 'unset';
    }

    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const modalContent = (
    <div
      className="fixed inset-0 flex items-center justify-center bg-slate-900/20 p-4 backdrop-blur-[2px]"
      style={{
        zIndex: 999999,
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0
      }}
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-[#0A2463] dark:text-white">
            {editingStudent ? `Editar: ${editingStudent.name}` : 'Novo Aluno'}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 text-xl font-bold w-8 h-8 flex items-center justify-center"
          >
            ✕
          </button>
        </div>

        <form onSubmit={onSubmit} className="space-y-4">
          {/* Informações Básicas */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">
                Nome Completo *
              </label>
              <input
                type="text"
                value={studentFormData.name}
                onChange={(e) => setStudentFormData(prev => ({ ...prev, name: e.target.value }))}
                className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition"
                placeholder="Digite o nome completo"
                required
                disabled={isSubmitting}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">
                Email *
              </label>
              <input
                type="email"
                value={studentFormData.email}
                onChange={(e) => setStudentFormData(prev => ({ ...prev, email: e.target.value }))}
                className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition"
                placeholder="Digite o email"
                required
                disabled={isSubmitting}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">
                Data de Nascimento
              </label>
              <input
                type="date"
                value={studentFormData.birthDate}
                onChange={(e) => setStudentFormData(prev => ({ ...prev, birthDate: e.target.value }))}
                className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition"
                disabled={isSubmitting}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">
                Turma
              </label>
              <select
                value={studentFormData.classId}
                onChange={(e) => setStudentFormData(prev => ({ ...prev, classId: e.target.value }))}
                className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition"
                disabled={isSubmitting}
              >
                <option value="">Selecione uma turma (opcional)</option>
                {classrooms?.map(classroom => (
                  <option key={classroom.id} value={classroom.id}>
                    {classroom.name} - {classroom.gradeLevel} ({classroom.year})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">
              Status
            </label>
            <select
              value={studentFormData.active ? 'true' : 'false'}
              onChange={(e) => setStudentFormData(prev => ({ ...prev, active: e.target.value === 'true' }))}
              className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition"
              disabled={isSubmitting}
            >
              <option value="true">Ativo</option>
              <option value="false">Inativo</option>
            </select>
          </div>

          <div>
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                  Lacunas de Aprendizagem
                </label>
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Preencha as lacunas que quiser registrar para o aluno.
                </p>
              </div>
              <button
                type="button"
                onClick={() =>
                  setStudentFormData((prev) => ({
                    ...prev,
                    learningGaps: [...prev.learningGaps, createEmptyLearningGap()],
                  }))
                }
                disabled={isSubmitting}
                className="inline-flex items-center gap-2 rounded-lg border border-[#1E5AA8] px-3 py-2 text-sm font-semibold text-[#1E5AA8] transition-colors hover:bg-[#1E5AA8] hover:text-white disabled:opacity-50 dark:border-[#4FC3F7] dark:text-[#4FC3F7] dark:hover:bg-[#4FC3F7] dark:hover:text-gray-900"
              >
                <Plus className="h-4 w-4" />
                Adicionar
              </button>
            </div>

            {studentFormData.learningGaps.length === 0 ? (
              <div className="rounded-lg border border-dashed border-gray-300 px-4 py-5 text-sm text-gray-500 dark:border-gray-600 dark:text-gray-400">
                Nenhuma lacuna cadastrada.
              </div>
            ) : (
              <div className="space-y-4">
                {studentFormData.learningGaps.map((gap, index) => (
                  <div key={gap._formId} className="rounded-lg border border-gray-200 p-4 dark:border-gray-600">
                    <div className="mb-4 flex items-center justify-between gap-3">
                      <h3 className="font-semibold text-[#0A2463] dark:text-white">Lacuna {index + 1}</h3>
                      <button
                        type="button"
                        onClick={() =>
                          setStudentFormData((prev) => ({
                            ...prev,
                            learningGaps: prev.learningGaps.filter((_, gapIndex) => gapIndex !== index),
                          }))
                        }
                        disabled={isSubmitting}
                        className="inline-flex items-center gap-2 text-sm font-medium text-red-600 transition-colors hover:text-red-700 disabled:opacity-50"
                      >
                        <Trash2 className="h-4 w-4" />
                        Remover
                      </button>
                    </div>

                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                      <div>
                        <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-200">
                          Disciplina
                        </label>
                        <input
                          type="text"
                          value={gap.subject}
                          onChange={(e) =>
                            setStudentFormData((prev) => ({
                              ...prev,
                              learningGaps: prev.learningGaps.map((item, gapIndex) =>
                                gapIndex === index ? { ...item, subject: e.target.value } : item,
                              ),
                            }))
                          }
                          className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-gray-900 outline-none transition focus:border-transparent focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                          placeholder="Ex: Matemática"
                          disabled={isSubmitting}
                        />
                      </div>

                      <div>
                        <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-200">
                          Tópico
                        </label>
                        <input
                          type="text"
                          value={gap.topic}
                          onChange={(e) =>
                            setStudentFormData((prev) => ({
                              ...prev,
                              learningGaps: prev.learningGaps.map((item, gapIndex) =>
                                gapIndex === index ? { ...item, topic: e.target.value } : item,
                              ),
                            }))
                          }
                          className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-gray-900 outline-none transition focus:border-transparent focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                          placeholder="Ex: Leitura"
                          disabled={isSubmitting}
                        />
                      </div>

                      <div>
                        <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-200">
                          Severidade
                        </label>
                        <select
                          value={gap.severity}
                          onChange={(e) =>
                            setStudentFormData((prev) => ({
                              ...prev,
                              learningGaps: prev.learningGaps.map((item, gapIndex) =>
                                gapIndex === index ? { ...item, severity: e.target.value as LearningGap['severity'] } : item,
                              ),
                            }))
                          }
                          className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-gray-900 outline-none transition focus:border-transparent focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                          disabled={isSubmitting}
                        >
                          <option value="LOW">Baixa</option>
                          <option value="MEDIUM">Média</option>
                          <option value="HIGH">Alta</option>
                        </select>
                      </div>

                      <div>
                        <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-200">
                          Status de melhoria
                        </label>
                        <select
                          value={gap.improvementStatus}
                          onChange={(e) =>
                            setStudentFormData((prev) => ({
                              ...prev,
                              learningGaps: prev.learningGaps.map((item, gapIndex) =>
                                gapIndex === index
                                  ? { ...item, improvementStatus: e.target.value as LearningGap['improvementStatus'] }
                                  : item,
                              ),
                            }))
                          }
                          className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-gray-900 outline-none transition focus:border-transparent focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                          disabled={isSubmitting}
                        >
                          <option value="IDENTIFIED">Identificada</option>
                          <option value="IN_PROGRESS">Em progresso</option>
                          <option value="IMPROVED">Melhorou</option>
                          <option value="RESOLVED">Resolvida</option>
                        </select>
                      </div>

                      <div className="md:col-span-2">
                        <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-200">
                          Data de identificação
                        </label>
                        <input
                          type="date"
                          value={gap.identifiedDate ? gap.identifiedDate.split('T')[0] : ''}
                          onChange={(e) =>
                            setStudentFormData((prev) => ({
                              ...prev,
                              learningGaps: prev.learningGaps.map((item, gapIndex) =>
                                gapIndex === index ? { ...item, identifiedDate: e.target.value || null } : item,
                              ),
                            }))
                          }
                          className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-gray-900 outline-none transition focus:border-transparent focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                          disabled={isSubmitting}
                        />
                      </div>

                      <div className="md:col-span-2">
                        <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-200">
                          Descrição
                        </label>
                        <textarea
                          value={gap.description}
                          onChange={(e) =>
                            setStudentFormData((prev) => ({
                              ...prev,
                              learningGaps: prev.learningGaps.map((item, gapIndex) =>
                                gapIndex === index ? { ...item, description: e.target.value } : item,
                              ),
                            }))
                          }
                          className="min-h-24 w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-gray-900 outline-none transition focus:border-transparent focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                          placeholder="Descreva a lacuna"
                          disabled={isSubmitting}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Botões */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg font-semibold text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 px-4 py-3 bg-[#1E5AA8] hover:bg-[#0A2463] disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-lg font-semibold shadow-md hover:shadow-lg transition flex items-center justify-center gap-2"
            >
              {isSubmitting && (
                <Loader2 className="w-4 h-4 animate-spin" />
              )}
              {isSubmitting
                ? (editingStudent ? 'Salvando...' : 'Criando...')
                : (editingStudent ? 'Salvar Alterações' : 'Criar Aluno')
              }
            </button>
          </div>
        </form>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
};

export function Turmas() {
  const navigate = useNavigate();
  const {
    data: classrooms,
    loading,
    error,
    searchTerm,
    setSearchTerm,
    refetch,
    isEmpty,
    total,
    filteredTotal
  } = useApiList(() => classroomsService.getAllClassrooms());

  const [viewMode, setViewMode] = useState<ViewMode>('classrooms');
  const [selectedClassroom, setSelectedClassroom] = useState<Classroom | null>(null);
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [classroomStudents, setClassroomStudents] = useState<Student[]>([]);
  const [classroomActivities, setClassroomActivities] = useState<Activity[]>([]);
  const [studentActivities, setStudentActivities] = useState<Activity[]>([]);
  const [loadingClassroomActivities, setLoadingClassroomActivities] = useState(false);
  const [loadingStudentActivities, setLoadingStudentActivities] = useState(false);
  const [visibleClassroomActivitiesCount, setVisibleClassroomActivitiesCount] = useState(2);
  const [visibleStudentActivitiesCount, setVisibleStudentActivitiesCount] = useState(2);
  const [downloadingActivityId, setDownloadingActivityId] = useState<string | null>(null);
  const [studentSearch, setStudentSearch] = useState('');
  const [studentSearchResults, setStudentSearchResults] = useState<Student[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [showStudentModal, setShowStudentModal] = useState(false);
  const [showTransferModal, setShowTransferModal] = useState(false);
  const [editingStudent, setEditingStudent] = useState<Student | null>(null);
  const [transferTargetClassroom, setTransferTargetClassroom] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    year: new Date().getFullYear(),
    gradeLevel: '',
    subjects: [] as string[]
  });
  const [studentFormData, setStudentFormData] = useState<StudentFormData>({
    name: '',
    email: '',
    birthDate: '',
    classId: '',
    active: true,
    learningGaps: []
  });

  // Função para limpar IDs que vêm no formato ObjectId
  const cleanStudentId = (id: string): string => {
    if (!id || typeof id !== 'string') {
      console.warn('ID inválido recebido:', id);
      return '';
    }

    let cleanId = id.trim();

    // Se contém ObjectId(), extrair o ID
    if (cleanId.includes('ObjectId')) {
      const match = cleanId.match(/ObjectId\('([^']+)'\)/);
      if (match && match[1]) {
        cleanId = match[1];
      } else {
        console.warn('Formato ObjectId inválido:', id);
        return '';
      }
    }

    // Validar se o ID tem o tamanho correto (MongoDB ObjectID = 24 caracteres)
    if (cleanId.length !== 24) {
      console.warn(`ID com tamanho incorreto: "${cleanId}" (${cleanId.length} chars, esperado: 24)`);
      // Não retornar vazio aqui, deixar o backend decidir se é válido
    }

    // Verificar se contém apenas caracteres hexadecimais válidos
    const hexPattern = /^[0-9a-fA-F]+$/;
    if (!hexPattern.test(cleanId)) {
      console.warn(`ID com caracteres inválidos: "${cleanId}"`);
      // Não retornar vazio aqui, deixar o backend decidir se é válido
    }

    return cleanId;
  };

  // Função para limpar dados de um estudante
  const cleanStudentData = (student: Student): Student => {
    return {
      ...student,
      id: cleanStudentId(student.id)
    };
  };

  // Hook para carregar todos os estudantes (para busca)
  const { data: rawAllStudents, loading: studentsLoading } = useApi(() => studentsService.getAllStudents());

  // Limpar IDs dos estudantes usando useMemo para evitar loop
  const allStudents = useMemo(() => {
    if (!rawAllStudents) return undefined;

    const cleanedStudents = rawAllStudents.map(cleanStudentData);

    // Debug controlado - apenas uma vez quando dados mudarem
    if (cleanedStudents.length > 0) {
      console.log('=== DEBUG TODOS OS ALUNOS (CONTROLADO) ===');
      console.log('Total de alunos:', cleanedStudents.length);

      cleanedStudents.forEach((student, index) => {
        console.log(`Aluno ${index + 1} - ${student.name}:`, {
          id: student.id,
          idLength: student.id?.length,
          name: student.name,
          email: student.email,
          birthDate: student.birthDate,
          classId: student.classId,
          className: student._class,
          active: student.active
        });

        const missingData = [];
        if (!student.name || student.name.trim() === '') missingData.push('name');
        if (!student.email || student.email.trim() === '') missingData.push('email');
        if (!student.birthDate) missingData.push('birthDate');

        // Verificar se ID tem tamanho correto (MongoDB ObjectID tem 24 caracteres)
        if (!student.id || student.id.length !== 24) {
          console.error(`🔴 ID inválido para ${student.name}:`, {
            id: student.id,
            length: student.id?.length,
            expected: 24,
            possibleFix: student.id?.length === 22 ? 'ID truncado - pode ter perdido últimos 2 caracteres' : 'ID corrompido'
          });

          // Se for João Silva com ID truncado, tentar algumas correções comuns
          if (student.name === 'João Silva' && student.id?.length === 22) {
            console.log('🔧 Tentativas de correção para João Silva:');
            console.log('- ID atual:', student.id);
            console.log('- Possíveis IDs completos para testar:');
            // IDs terminam frequentemente em 00, 01, 02, etc
            ['00', '01', '02', '03', '10', '11', '12', '20', '21'].forEach(suffix => {
              console.log(`  - ${student.id}${suffix}`);
            });
          }
        }

        if (missingData.length > 0) {
          console.warn(`⚠️ Aluno ${student.name || student.id} com dados faltando:`, missingData);

          // Para Henrrique sem birthDate, sugerir uma data padrão
          if (student.name === 'Henrrique Lopes' && missingData.includes('birthDate')) {
            console.log('💡 Sugestão: Adicionar birthDate para Henrrique Lopes');
            console.log('   Data sugerida: 2018-01-01 (pode ajustar depois)');
          }
        }
      });

      // Resumo dos problemas encontrados
      const corruptedIds = cleanedStudents.filter(s => !s.id || s.id.length !== 24);
      const missingBirthDates = cleanedStudents.filter(s => !s.birthDate);

      if (corruptedIds.length > 0 || missingBirthDates.length > 0) {
        console.log('📋 RESUMO DE PROBLEMAS:');
        if (corruptedIds.length > 0) {
          console.log(`- ${corruptedIds.length} aluno(s) com ID corrompido:`, corruptedIds.map(s => s.name));
        }
        if (missingBirthDates.length > 0) {
          console.log(`- ${missingBirthDates.length} aluno(s) sem data de nascimento:`, missingBirthDates.map(s => s.name));
        }
        console.log('💡 AÇÕES SUGERIDAS:');
        console.log('1. Verificar dados no MongoDB/Backend');
        console.log('2. Corrigir IDs corrompidos');
        console.log('3. Adicionar datas de nascimento faltantes');
      }
    }

    return cleanedStudents;
  }, [rawAllStudents]);

  useEffect(() => {
    if (studentSearch && allStudents) {
      const results = allStudents.filter(student =>
        student.name.toLowerCase().includes(studentSearch.toLowerCase()) ||
        (student.email || '').toLowerCase().includes(studentSearch.toLowerCase()) ||
        student.id?.toLowerCase().includes(studentSearch.toLowerCase())
      );
      setStudentSearchResults(results);
    } else {
      setStudentSearchResults([]);
    }
  }, [studentSearch, allStudents]);

  const sortedClassroomActivities = useMemo(
    () => [...classroomActivities].sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()),
    [classroomActivities],
  );

  const sortedStudentActivities = useMemo(
    () => [...studentActivities].sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()),
    [studentActivities],
  );

  const visibleClassroomActivities = sortedClassroomActivities.slice(0, visibleClassroomActivitiesCount);
  const visibleStudentActivities = sortedStudentActivities.slice(0, visibleStudentActivitiesCount);


  const getStatusColor = (active: boolean) => {
    return active ? "bg-[#4CAF50] text-white" : "bg-gray-400 text-white";
  };

  const getStatusText = (active: boolean) => {
    return active ? "Ativa" : "Inativa";
  };

  const handleCreateClassroom = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsCreating(true);

    try {
      const createData: CreateClassroomRequest = {
        ...formData,
        teacherId: "current-teacher-id", // TODO: Obter do contexto de autenticação
        subjects: formData.subjects.length > 0 ? formData.subjects : [formData.gradeLevel]
      };

      await classroomsService.createClassroom(createData);
      setShowModal(false);
      setFormData({
        name: '',
        year: new Date().getFullYear(),
        gradeLevel: '',
        subjects: []
      });
      refetch();
    } catch (err) {
      console.error('Erro ao criar turma:', err);
      // TODO: Mostrar notificação de erro
    } finally {
      setIsCreating(false);
    }
  };

  const handleViewClassroomDetails = async (classroom: Classroom) => {
    setSelectedClassroom(classroom);
    setViewMode('classroom-details');
    setStudentActivities([]);
    setVisibleClassroomActivitiesCount(2);
    setVisibleStudentActivitiesCount(2);

    setLoadingClassroomActivities(true);
    activitiesService.getActivitiesByClassroom(classroom.id)
      .then(setClassroomActivities)
      .catch((error) => {
        console.error('Erro ao carregar atividades da turma:', error);
        setClassroomActivities([]);
        toast.error('Não foi possível carregar as atividades da turma.');
      })
      .finally(() => setLoadingClassroomActivities(false));

    // Carregar alunos da turma
    try {
      if (classroom.studentIds && classroom.studentIds.length > 0) {
        console.log('=== CARREGANDO ALUNOS DA TURMA ===');
        console.log('Turma:', classroom.name);
        console.log('Student IDs brutos:', classroom.studentIds);

        // Filtrar e validar IDs antes de tentar carregar
        const validStudentIds = classroom.studentIds
          .map(id => {
            const cleanId = cleanStudentId(id);
            console.log(`ID bruto: "${id}" → ID limpo: "${cleanId}" (${cleanId.length} chars)`);
            return cleanId;
          })
          .filter(id => {
            const isValid = id && typeof id === 'string' && id.length === 24;
            if (!isValid) {
              console.warn(`🔴 ID inválido ignorado: "${id}" (length: ${id?.length})`);
            }
            return isValid;
          });

        console.log('IDs válidos para carregar:', validStudentIds);

        if (validStudentIds.length === 0) {
          console.warn('Nenhum ID válido encontrado para carregar');
          setClassroomStudents([]);
          return;
        }

        // Carregar alunos um por vez para identificar qual está falhando
        const students = [];
        for (const studentId of validStudentIds) {
          try {
            console.log(`Carregando aluno com ID: ${studentId}`);
            const student = await studentsService.getStudentById(studentId);
            students.push(student);
            console.log(`✅ Aluno carregado: ${student.name}`);
          } catch (error) {
            console.error(`❌ Erro ao carregar aluno ${studentId}:`, error);
            // Continuar carregando os outros alunos mesmo se um falhar
          }
        }

        // Limpar dados dos estudantes carregados
        const cleanedStudents = students.map(cleanStudentData);
        console.log(`Carregados ${cleanedStudents.length} de ${validStudentIds.length} alunos da turma`);

        setClassroomStudents(cleanedStudents);
      } else {
        console.log('Turma sem alunos:', classroom.name);
        setClassroomStudents([]);
      }
    } catch (error) {
      console.error('Erro geral ao carregar alunos da turma:', error);
      setClassroomStudents([]);
    }
  };

  const handleViewStudentDetails = async (student: Student) => {
    console.log('Visualizando detalhes do aluno:', student);
    const cleanedStudent = cleanStudentData(student);
    console.log('Aluno com dados limpos:', cleanedStudent);

    setSelectedStudent(cleanedStudent);
    setViewMode('student-details');
    setLoadingStudentActivities(true);
    setVisibleStudentActivitiesCount(2);

    try {
      const activities = await activitiesService.getActivitiesByStudent(cleanedStudent.id);
      setStudentActivities(activities);
    } catch (error) {
      console.error('Erro ao carregar atividades do aluno:', error);
      setStudentActivities([]);
      toast.error('Não foi possível carregar as atividades do aluno.');
    } finally {
      setLoadingStudentActivities(false);
    }
  };

  const handleDownloadActivityPdf = async (activity: Activity) => {
    try {
      setDownloadingActivityId(activity.id);
      await activitiesService.downloadActivityPDF(activity.id, false);
      toast.success('PDF baixado com sucesso.');
    } catch (error) {
      console.error('Erro ao baixar PDF da atividade:', error);
      toast.error('Não foi possível baixar o PDF da atividade.');
    } finally {
      setDownloadingActivityId(null);
    }
  };

  // Handler para abrir modal de criar aluno
  const handleCreateStudent = () => {
    console.log('=== DEBUG CREATE STUDENT ===');
    console.log('Abrindo modal para criar novo aluno');

    setEditingStudent(null);
    setStudentFormData({
      name: '',
      email: '',
      birthDate: '',
      classId: '',
      active: true,
      learningGaps: []
    });

    setShowStudentModal(true);
    console.log('Modal de criação aberto via Portal');
  };

  // Handler para abrir modal de editar aluno
  const handleEditStudent = (student: Student) => {
    console.log('=== DEBUG EDIT STUDENT ===');
    console.log('Aluno completo:', student);
    console.log('ID bruto:', student.id);
    console.log('Tipo do ID:', typeof student.id);

    // Limpar ID se estiver no formato ObjectId('...')
    let cleanId = student.id;
    if (typeof student.id === 'string' && student.id.includes('ObjectId')) {
      const match = student.id.match(/ObjectId\('([^']+)'\)/);
      if (match) {
        cleanId = match[1];
        console.log('ID limpo:', cleanId);
      }
    }

    // Criar um objeto student com ID limpo
    const cleanStudent = {
      ...student,
      id: cleanId
    };

    setEditingStudent(cleanStudent);

    const formattedBirthDate = student.birthDate ? student.birthDate.split('T')[0] : '';

    setStudentFormData({
      name: student.name || '',
      email: student.email || '',
      birthDate: formattedBirthDate,
      classId: student.classId || '',
      active: student.active ?? true,
      learningGaps: (student.learningGaps || []).map((gap) => ({
        _formId: createFormId(),
        ...gap,
        identifiedDate: gap.identifiedDate || null,
      }))
    });

    setShowStudentModal(true);
    console.log('Modal de edição aberto via Portal para:', student.name);
  };

  // Handler para submeter formulário de aluno
  const handleSubmitStudent = async (e: React.FormEvent) => {
    e.preventDefault();

    console.log('=== DEBUG SUBMIT STUDENT ===');
    console.log('editingStudent:', editingStudent);
    console.log('studentFormData:', studentFormData);

    if (!studentFormData.name || !studentFormData.email) {
      toast.error('Por favor, preencha nome e email.');
      return;
    }

    const normalizedLearningGaps = studentFormData.learningGaps
      .filter((gap) => gap.subject || gap.topic || gap.description || gap.identifiedDate)
      .map(({ _formId, ...gap }) => ({
        ...gap,
        identifiedDate: gap.identifiedDate
          ? new Date(`${gap.identifiedDate}T00:00:00.000Z`).toISOString()
          : null,
      }));

    // Validar classId se fornecido
    if (studentFormData.classId) {
      const classExists = classrooms?.find(c => c.id === studentFormData.classId);
      if (!classExists) {
        console.error('Turma não encontrada:', studentFormData.classId);
        console.log('Turmas disponíveis:', classrooms?.map(c => ({ id: c.id, name: c.name })));
        toast.error('A turma selecionada não existe. Selecione uma turma válida ou deixe em branco.');
        return;
      }
    }

    setIsSubmitting(true);

    try {
      if (editingStudent) {
        console.log('Atualizando aluno com ID:', editingStudent.id);

        const updateData = {
          name: studentFormData.name,
          email: studentFormData.email,
          birthDate: studentFormData.birthDate
            ? new Date(studentFormData.birthDate + 'T00:00:00.000Z').toISOString()
            : null,
          classId: studentFormData.classId || undefined,
          active: studentFormData.active,
          learningGaps: normalizedLearningGaps
        };

        console.log('Dados de atualização:', updateData);

        // Atualizar aluno existente
        await studentsService.updateStudent(editingStudent.id, updateData);
        toast.success('Aluno atualizado com sucesso!');
      } else {
        console.log('Criando novo aluno');

        const createData = {
          name: studentFormData.name,
          email: studentFormData.email,
          birthDate: studentFormData.birthDate
            ? new Date(studentFormData.birthDate + 'T00:00:00.000Z').toISOString()
            : null,
          classId: studentFormData.classId || undefined,
          active: studentFormData.active,
          learningGaps: normalizedLearningGaps
        };

        console.log('Dados de criação:', createData);

        // Criar novo aluno
        await studentsService.createStudent(createData);
        toast.success('Aluno criado com sucesso!');
      }

      // Fechar modal e recarregar dados
      setShowStudentModal(false);
      refetch(); // Recarregar turmas

      // Se estiver vendo detalhes de um aluno, atualizar
      if (selectedStudent && editingStudent && selectedStudent.id === editingStudent.id) {
        try {
          const updatedStudent = await studentsService.getStudentById(selectedStudent.id);
          setSelectedStudent(updatedStudent);
        } catch (fetchError) {
          console.error('Erro ao recarregar dados do aluno:', fetchError);
        }
      }

    } catch (error) {
      console.error('Erro ao salvar aluno:', error);

      let errorMessage = `Erro ao ${editingStudent ? 'atualizar' : 'criar'} aluno.`;

      if (error instanceof Error) {
        if (error.message.includes('Turma não encontrado')) {
          errorMessage = 'A turma selecionada não existe. Por favor, selecione uma turma válida.';
        } else if (error.message.includes('404')) {
          errorMessage = editingStudent ? 'Aluno não encontrado. Pode ter sido removido.' : 'Erro ao criar aluno.';
        } else {
          errorMessage += ` ${error.message}`;
        }
      }

      toast.error(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTransferStudent = async (targetClassroomId?: string) => {
    const classroomId = targetClassroomId || transferTargetClassroom;

    if (!selectedStudent || !classroomId) {
      toast.error('Por favor, selecione uma turma de destino.');
      return;
    }

    // Verificar turma atual (pode ser _class ou classId)
    const currentClassroom = selectedStudent._class || selectedStudent.classId;
    const currentClassroomId = selectedStudent.classId;

    console.log('=== TRANSFERINDO ALUNO ===');
    console.log('Aluno:', selectedStudent.name);
    console.log('Turma atual (_class):', selectedStudent._class);
    console.log('Turma atual (classId):', selectedStudent.classId);
    console.log('Nova turma ID:', classroomId);

    try {
      // Se o aluno tem uma turma atual (por ID), remover da turma atual
      if (currentClassroomId) {
        console.log('Removendo da turma atual usando classId...');
        await classroomsService.unenrollStudent(currentClassroomId, selectedStudent.id);
      } else if (currentClassroom) {
        console.log('Aluno tem turma (_class) mas não classId - pode precisar encontrar ID da turma');
        // Encontrar o ID da turma pelo nome
        const currentClassroomObj = classrooms?.find(c => c.name === currentClassroom);
        if (currentClassroomObj) {
          console.log('Encontrou turma atual, removendo...');
          await classroomsService.unenrollStudent(currentClassroomObj.id, selectedStudent.id);
        }
      } else {
        console.log('Aluno não tem turma atual - pulando desenrolamento');
      }

      // Adicionar aluno à nova turma
      console.log('Adicionando à nova turma...');
      await classroomsService.enrollStudent(classroomId, selectedStudent.id);

      // Atualizar dados locais
      setSelectedStudent(prev => prev ? { ...prev, classId: classroomId, _class: classrooms?.find(c => c.id === classroomId)?.name } : null);

      // Recarregar dados
      console.log('Recarregando dados...');
      await refetch();

      // Limpar campos
      setTransferTargetClassroom('');
      setShowTransferModal(false);

      // Feedback de sucesso
      const action = currentClassroom ? 'transferido' : 'matriculado';
      toast.success(`Aluno ${action} com sucesso!`);

    } catch (error) {
      console.error('Erro ao transferir aluno:', error);
      toast.error(`Erro ao ${currentClassroom ? 'transferir' : 'matricular'} aluno. Tente novamente.`);
    }
  };

  const getStudentClassroomName = (student: Student) => {
    // Primeiro tenta usar _class (campo do MongoDB)
    if (student._class) {
      return student._class;
    }

    // Senão, procura pela classId
    const classroom = classrooms?.find(c => c.studentIds?.includes(student.id) || c.id === student.classId);
    return classroom?.name || 'Sem turma';
  };

  const getStudentClassroom = (student: Student) => {
    return classrooms?.find(c => c.studentIds?.includes(student.id) || c.id === student.classId);
  };

  // Calcular estatísticas
  const activeClassrooms = classrooms?.filter(c => c.active) || [];
  const totalStudents = classrooms?.reduce((acc, c) => acc + (c.studentIds?.length || 0), 0) || 0;
  const averageStudentsPerClass = activeClassrooms.length > 0 ?
    Math.round(totalStudents / activeClassrooms.length) : 0;

  const sharedStudentModal = (
    <StudentModal
      isOpen={showStudentModal}
      onClose={() => {
        console.log('Fechando modal via portal');
        setShowStudentModal(false);
      }}
      editingStudent={editingStudent}
      studentFormData={studentFormData}
      setStudentFormData={setStudentFormData}
      classrooms={classrooms}
      isSubmitting={isSubmitting}
      onSubmit={handleSubmitStudent}
    />
  );

  const sharedTransferModal = showTransferModal && selectedStudent ? (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/25 p-4 backdrop-blur-[2px]"
      onClick={() => setShowTransferModal(false)}
    >
      <div
        className="w-full max-w-md rounded-xl bg-white p-6 shadow-2xl dark:bg-gray-800"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-[#0A2463] dark:text-white">Transferir Aluno</h2>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
              Transfira <strong>{selectedStudent.name}</strong> para outra turma.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setShowTransferModal(false)}
            className="text-gray-500 transition-colors hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            ✕
          </button>
        </div>

        <div className="space-y-4">
          <div className="rounded-lg bg-blue-50 p-3 text-sm text-blue-800 dark:bg-blue-950/40 dark:text-blue-200">
            Turma atual: {getStudentClassroomName(selectedStudent)}
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-200">
              Turma de destino
            </label>
            <select
              value={transferTargetClassroom}
              onChange={(e) => setTransferTargetClassroom(e.target.value)}
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-gray-900 outline-none transition focus:border-transparent focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
            >
              <option value="">Selecione uma turma</option>
              {(classrooms || [])
                .filter((classroom) => classroom.id !== selectedStudent.classId && classroom.name !== selectedStudent._class)
                .map((classroom) => (
                  <option key={classroom.id} value={classroom.id}>
                    {classroom.name} - {classroom.gradeLevel} ({classroom.year})
                  </option>
                ))}
            </select>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={() => setShowTransferModal(false)}
              className="flex-1 rounded-lg border border-gray-300 px-4 py-3 font-semibold text-gray-700 transition-colors hover:bg-gray-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={() => handleTransferStudent()}
              className="flex-1 rounded-lg bg-[#1E5AA8] px-4 py-3 font-semibold text-white transition-colors hover:bg-[#0A2463]"
            >
              Transferir
            </button>
          </div>
        </div>
      </div>
    </div>
  ) : null;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex items-center gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-[#1E5AA8]" />
          <span className="text-lg text-gray-600 dark:text-gray-300">Carregando turmas...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">Erro ao carregar turmas</h2>
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

  // Renderização condicional baseada no modo de visualização
  if (viewMode === 'student-details' && selectedStudent) {
    const studentClassroom = getStudentClassroom(selectedStudent);

    return (
      <>
      <div className="space-y-6">
        {/* Header com botão de voltar */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => {
              setViewMode(selectedClassroom ? 'classroom-details' : 'classrooms');
              setSelectedStudent(null);
            }}
            className="flex items-center gap-2 text-[#1E5AA8] hover:text-[#0A2463] transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            {selectedClassroom ? 'Voltar para a Turma' : 'Voltar para Turmas'}
          </button>
        </div>

        {/* Informações do Aluno */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-colors">
          <div className="flex items-start justify-between mb-6">
            <div className="flex items-center gap-4">
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-[#1E5AA8] to-[#4FC3F7] flex items-center justify-center text-white font-bold text-2xl">
                {selectedStudent.name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2)}
              </div>
              <div>
                <h1 className="text-3xl font-bold text-[#0A2463] dark:text-white">{selectedStudent.name}</h1>
                <p className="text-gray-600 dark:text-gray-300 mt-1 flex items-center gap-2">
                  <Mail className="w-4 h-4" />
                  {selectedStudent.email}
                </p>
                <p className="text-gray-600 dark:text-gray-300 mt-1 flex items-center gap-2">
                  <Hash className="w-4 h-4" />
                  ID: {selectedStudent.id}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className={`px-3 py-1 rounded-full text-xs font-semibold ${selectedStudent.active ? 'bg-[#4CAF50] text-white' : 'bg-gray-400 text-white'}`}>
                {selectedStudent.active ? 'Ativo' : 'Inativo'}
              </span>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={(e) => {
                    console.log('=== CLIQUE NO BOTÃO EDITAR ALUNO ===');
                    console.log('selectedStudent:', selectedStudent);
                    console.log('Evento:', e);
                    e.preventDefault();
                    e.stopPropagation();

                    // Garantir que o modal apareça imediatamente
                    setTimeout(() => {
                      handleEditStudent(selectedStudent);
                    }, 10);
                  }}
                  className="flex items-center gap-2 bg-[#4FC3F7] hover:bg-[#1E5AA8] text-white px-4 py-2 rounded-lg transition-colors"
                >
                  <User className="w-4 h-4" />
                  Editar Aluno
                </button>
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setTransferTargetClassroom('');
                    setShowTransferModal(true);
                  }}
                  className="flex items-center gap-2 bg-[#1E5AA8] hover:bg-[#0A2463] text-white px-4 py-2 rounded-lg transition-colors"
                >
                  <ArrowRightLeft className="w-4 h-4" />
                  Transferir Turma
                </button>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
              <div className="flex items-center gap-3 mb-2">
                <Users className="w-6 h-6 text-[#1E5AA8]" />
                <h3 className="font-semibold text-gray-700 dark:text-gray-200">Turma Atual</h3>
              </div>
              <p className="text-xl font-bold text-[#0A2463] dark:text-white">
                {studentClassroom?.name || 'Sem turma'}
              </p>
              {studentClassroom && (
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  {studentClassroom.gradeLevel} • Ano {studentClassroom.year}
                </p>
              )}
            </div>

            <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
              <div className="flex items-center gap-3 mb-2">
                <Calendar className="w-6 h-6 text-[#4CAF50]" />
                <h3 className="font-semibold text-gray-700 dark:text-gray-200">Data de Nascimento</h3>
              </div>
              <p className="text-xl font-bold text-[#0A2463] dark:text-white">
                {formatDate(selectedStudent.birthDate)}
              </p>
            </div>

            <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
              <div className="flex items-center gap-3 mb-2">
                <AlertCircle className="w-6 h-6 text-[#FF9800]" />
                <h3 className="font-semibold text-gray-700 dark:text-gray-200">Lacunas de Aprendizagem</h3>
              </div>
              <p className="text-xl font-bold text-[#0A2463] dark:text-white">
                {selectedStudent.learningGaps?.length || 0}
              </p>
            </div>
          </div>

          {/* Lacunas de Aprendizagem */}
          {selectedStudent.learningGaps && selectedStudent.learningGaps.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-[#0A2463] dark:text-white mb-3">Lacunas de Aprendizagem</h3>
              <div className="space-y-3">
                {selectedStudent.learningGaps.map((gap, index) => (
                  <div key={index} className="border border-gray-200 dark:border-gray-600 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <h4 className="font-semibold text-[#0A2463] dark:text-white">{gap.subject} - {gap.topic}</h4>
                        <p className="text-sm text-gray-600 dark:text-gray-300">{gap.description}</p>
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                          gap.severity === 'HIGH' ? 'bg-red-100 text-red-800' :
                          gap.severity === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-green-100 text-green-800'
                        }`}>
                          {gap.severity === 'HIGH' ? 'Alto' : gap.severity === 'MEDIUM' ? 'Médio' : 'Baixo'}
                        </span>
                        <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                          gap.improvementStatus === 'RESOLVED' ? 'bg-green-100 text-green-800' :
                          gap.improvementStatus === 'IMPROVED' ? 'bg-blue-100 text-blue-800' :
                          gap.improvementStatus === 'IN_PROGRESS' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {gap.improvementStatus === 'RESOLVED' ? 'Resolvido' :
                           gap.improvementStatus === 'IMPROVED' ? 'Melhorado' :
                           gap.improvementStatus === 'IN_PROGRESS' ? 'Em Progresso' :
                           'Identificado'}
                        </span>
                      </div>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Identificado em: {formatDate(gap.identifiedDate)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-colors">
          <div className="mb-4 flex items-center gap-2">
            <ClipboardList className="h-5 w-5 text-[#1E5AA8] dark:text-[#4FC3F7]" />
            <h2 className="text-xl font-bold text-[#0A2463] dark:text-white">Atividades específicas do aluno</h2>
          </div>

          {loadingStudentActivities ? (
            <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
              <Loader2 className="h-4 w-4 animate-spin" />
              Carregando atividades...
            </div>
          ) : sortedStudentActivities.length === 0 ? (
            <div className="rounded-lg border border-dashed border-gray-300 p-6 text-center text-gray-500 dark:border-gray-600 dark:text-gray-400">
              Nenhuma atividade individual foi gerada para este aluno.
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {visibleStudentActivities.map((activity) => (
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
                    className="cursor-pointer rounded-lg border border-gray-200 bg-gray-50 p-4 transition-colors hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:bg-gray-700 dark:hover:bg-gray-600"
                  >
                    <div className="mb-2 flex items-start justify-between gap-3">
                      <h3 className="font-semibold text-[#0A2463] dark:text-white">{activity.title}</h3>
                      <span className="rounded-full bg-[#E3F2FD] px-2 py-1 text-xs font-semibold text-[#0A2463]">
                        {activity.questionsCount} questões
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-300">{activity.subject} • {activity.topic}</p>
                    <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Criada em: {formatDate(activity.createdAt)}
                      </p>
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          handleDownloadActivityPdf(activity);
                        }}
                        disabled={downloadingActivityId === activity.id}
                        className="inline-flex items-center gap-2 rounded-lg border border-[#1E5AA8] px-3 py-2 text-xs font-semibold text-[#1E5AA8] transition-colors hover:bg-[#1E5AA8] hover:text-white disabled:cursor-not-allowed disabled:opacity-60 dark:border-[#4FC3F7] dark:text-[#4FC3F7] dark:hover:bg-[#4FC3F7] dark:hover:text-gray-900"
                      >
                        {downloadingActivityId === activity.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                        Baixar PDF
                      </button>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-4 flex flex-wrap gap-3">
                {visibleStudentActivitiesCount < sortedStudentActivities.length ? (
                  <button
                    type="button"
                    onClick={() => setVisibleStudentActivitiesCount(prev => Math.min(prev + 4, sortedStudentActivities.length))}
                    className="rounded-lg bg-[#1E5AA8] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[#0A2463]"
                  >
                    Ver mais
                  </button>
                ) : null}
                {visibleStudentActivitiesCount > 2 ? (
                  <button
                    type="button"
                    onClick={() => setVisibleStudentActivitiesCount(2)}
                    className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 transition-colors hover:border-[#1E5AA8] hover:text-[#1E5AA8] dark:border-gray-600 dark:text-gray-200"
                  >
                    Mostrar menos
                  </button>
                ) : null}
              </div>
            </>
          )}
        </div>
      </div>
      {sharedStudentModal}
      {sharedTransferModal}
      </>
    );
  }

  if (viewMode === 'classroom-details' && selectedClassroom) {
    return (
      <>
      <div className="space-y-6">
        {/* Header com botão de voltar */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => {
              setViewMode('classrooms');
              setSelectedClassroom(null);
              setClassroomStudents([]);
            }}
            className="flex items-center gap-2 text-[#1E5AA8] hover:text-[#0A2463] transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            Voltar para Turmas
          </button>
        </div>

        {/* Informações da Turma */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-colors">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h1 className="text-3xl font-bold text-[#0A2463] dark:text-white">{selectedClassroom.name}</h1>
              <p className="text-gray-600 dark:text-gray-300 mt-2">
                {selectedClassroom.gradeLevel} • Ano {selectedClassroom.year}
              </p>
            </div>
            <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getStatusColor(selectedClassroom.active)}`}>
              {getStatusText(selectedClassroom.active)}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="flex items-center gap-3">
              <Users className="w-8 h-8 text-[#1E5AA8]" />
              <div>
                <p className="text-2xl font-bold text-[#0A2463] dark:text-white">
                  {selectedClassroom.studentIds?.length || 0}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Alunos</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Calendar className="w-8 h-8 text-[#4CAF50]" />
              <div>
                <p className="text-2xl font-bold text-[#0A2463] dark:text-white">{selectedClassroom.year}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Ano letivo</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <BookOpen className="w-8 h-8 text-[#FF9800]" />
              <div>
                <p className="text-2xl font-bold text-[#0A2463] dark:text-white">
                  {(selectedClassroom.subjects || []).length}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Disciplinas</p>
              </div>
            </div>
          </div>

          {/* Disciplinas */}
          {(selectedClassroom.subjects || []).length > 0 && (
            <div>
              <h3 className="font-semibold text-gray-700 dark:text-gray-200 mb-3">Disciplinas:</h3>
              <div className="flex flex-wrap gap-2">
                {(selectedClassroom.subjects || []).map((subject, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-[#1E5AA8]/10 text-[#1E5AA8] dark:bg-[#4FC3F7]/10 dark:text-[#4FC3F7] text-sm rounded-full"
                  >
                    {subject}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-colors">
          <div className="mb-4 flex items-center gap-2">
            <ClipboardList className="h-5 w-5 text-[#1E5AA8] dark:text-[#4FC3F7]" />
            <h2 className="text-xl font-bold text-[#0A2463] dark:text-white">Atividades da Turma</h2>
          </div>

          {loadingClassroomActivities ? (
            <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
              <Loader2 className="h-4 w-4 animate-spin" />
              Carregando atividades...
            </div>
          ) : sortedClassroomActivities.length === 0 ? (
            <div className="rounded-lg border border-dashed border-gray-300 p-6 text-center text-gray-500 dark:border-gray-600 dark:text-gray-400">
              Nenhuma atividade foi gerada para esta turma.
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {visibleClassroomActivities.map((activity) => (
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
                    className="cursor-pointer rounded-lg border border-gray-200 bg-gray-50 p-4 transition-colors hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-[#1E5AA8] dark:border-gray-600 dark:bg-gray-700 dark:hover:bg-gray-600"
                  >
                    <div className="mb-2 flex items-start justify-between gap-3">
                      <h3 className="font-semibold text-[#0A2463] dark:text-white">{activity.title}</h3>
                      <span className="rounded-full bg-[#E3F2FD] px-2 py-1 text-xs font-semibold text-[#0A2463]">
                        {activity.studentId ? "Individual" : "Turma"}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-300">{activity.subject} • {activity.topic}</p>
                    <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                      <span>{activity.questionsCount} questões</span>
                      <span>•</span>
                      <span>{activity.studentId ? `Para: ${activity.studentName || "aluno selecionado"}` : "Compartilhada com todos"}</span>
                      <span>•</span>
                      <span>{formatDate(activity.createdAt)}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleDownloadActivityPdf(activity)}
                      disabled={downloadingActivityId === activity.id}
                      className="mt-4 inline-flex items-center gap-2 rounded-lg border border-[#1E5AA8] px-3 py-2 text-xs font-semibold text-[#1E5AA8] transition-colors hover:bg-[#1E5AA8] hover:text-white disabled:cursor-not-allowed disabled:opacity-60 dark:border-[#4FC3F7] dark:text-[#4FC3F7] dark:hover:bg-[#4FC3F7] dark:hover:text-gray-900"
                    >
                      {downloadingActivityId === activity.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                      Baixar PDF
                    </button>
                  </div>
                ))}
              </div>
              <div className="mt-4 flex flex-wrap gap-3">
                {visibleClassroomActivitiesCount < sortedClassroomActivities.length ? (
                  <button
                    type="button"
                    onClick={() => setVisibleClassroomActivitiesCount(prev => Math.min(prev + 4, sortedClassroomActivities.length))}
                    className="rounded-lg bg-[#1E5AA8] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[#0A2463]"
                  >
                    Ver mais
                  </button>
                ) : null}
                {visibleClassroomActivitiesCount > 2 ? (
                  <button
                    type="button"
                    onClick={() => setVisibleClassroomActivitiesCount(2)}
                    className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 transition-colors hover:border-[#1E5AA8] hover:text-[#1E5AA8] dark:border-gray-600 dark:text-gray-200"
                  >
                    Mostrar menos
                  </button>
                ) : null}
              </div>
            </>
          )}
        </div>

        {/* Lista de Alunos da Turma */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-colors">
          <h2 className="text-xl font-bold text-[#0A2463] dark:text-white mb-4">Alunos da Turma</h2>

          {classroomStudents.length === 0 ? (
            <div className="text-center py-8">
              <GraduationCap className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Nenhum aluno matriculado</h3>
              <p className="text-gray-500 dark:text-gray-400">Esta turma ainda não possui alunos cadastrados.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {classroomStudents.map((student) => (
                <div
                  key={student.id}
                  className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors cursor-pointer"
                  onClick={() => handleViewStudentDetails(student)}
                >
                  <div className="flex items-start gap-3">
                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-[#1E5AA8] to-[#4FC3F7] flex items-center justify-center text-white font-bold flex-shrink-0">
                      {student.name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-[#0A2463] dark:text-white truncate">
                        {student.name}
                      </h3>
                      {student.email && (
                        <p className="text-sm text-gray-600 dark:text-gray-300 truncate">{student.email}</p>
                      )}
                      <p className="text-xs text-gray-500 dark:text-gray-400">ID: {student.id}</p>
                      <div className="flex items-center justify-between mt-2">
                        <div className="flex items-center gap-1">
                          {student.active ? (
                            <UserCheck className="w-4 h-4 text-[#4CAF50]" />
                          ) : (
                            <User className="w-4 h-4 text-gray-400" />
                          )}
                          <span className={`text-xs font-medium ${student.active ? 'text-[#4CAF50]' : 'text-gray-400'}`}>
                            {student.active ? 'Ativo' : 'Inativo'}
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={(e) => {
                            console.log('=== CLIQUE NO BOTÃO EDITAR (CARD) ===');
                            console.log('student:', student);
                            e.preventDefault();
                            e.stopPropagation();

                            setTimeout(() => {
                              handleEditStudent(student);
                            }, 10);
                          }}
                          className="text-[#1E5AA8] hover:text-[#0A2463] p-1 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                          title="Editar aluno"
                        >
                          <User className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      {sharedStudentModal}
      {sharedTransferModal}
      </>
    );
  }

  // Visualização padrão - Lista de turmas
  return (
    <>
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-[#0A2463] dark:text-white">Turmas e Alunos</h1>
          <p className="text-gray-600 dark:text-gray-300 mt-2">Gerencie suas turmas e alunos</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowModal(true)}
            className="bg-[#1E5AA8] hover:bg-[#0A2463] text-white px-6 py-3 rounded-lg font-semibold flex items-center gap-2 shadow-md hover:shadow-lg transition-all"
          >
            <Plus className="w-5 h-5" />
            Nova Turma
          </button>
          <button
            type="button"
            onClick={(e) => {
              console.log('=== CLIQUE NO BOTÃO ADICIONAR ALUNO ===');
              e.preventDefault();
              e.stopPropagation();

              setTimeout(() => {
                handleCreateStudent();
              }, 10);
            }}
            className="bg-[#4FC3F7] hover:bg-[#1E5AA8] text-white px-6 py-3 rounded-lg font-semibold flex items-center gap-2 shadow-md hover:shadow-lg transition-all"
          >
            <User className="w-5 h-5" />
            Adicionar Aluno
          </button>
        </div>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-gradient-to-br from-[#1E5AA8] to-[#4FC3F7] rounded-lg shadow-md p-6 text-white">
          <div className="flex items-center gap-3 mb-2">
            <Users className="w-6 h-6" />
            <h3 className="font-semibold">Total de Turmas</h3>
          </div>
          <p className="text-4xl font-bold">{total}</p>
          <p className="text-sm opacity-80 mt-1">{activeClassrooms.length} ativas</p>
        </div>

        <div className="bg-gradient-to-br from-[#4CAF50] to-[#81C784] rounded-lg shadow-md p-6 text-white">
          <div className="flex items-center gap-3 mb-2">
            <GraduationCap className="w-6 h-6" />
            <h3 className="font-semibold">Total de Alunos</h3>
          </div>
          <p className="text-4xl font-bold">{totalStudents}</p>
          <p className="text-sm opacity-80 mt-1">Média: {averageStudentsPerClass} por turma</p>
        </div>

        <div className="bg-gradient-to-br from-[#FF9800] to-[#FFB74D] rounded-lg shadow-md p-6 text-white">
          <div className="flex items-center gap-3 mb-2">
            <TrendingUp className="w-6 h-6" />
            <h3 className="font-semibold">Encontradas</h3>
          </div>
          <p className="text-4xl font-bold">{filteredTotal}</p>
          <p className="text-sm opacity-80 mt-1">
            {searchTerm ? `de ${total} turmas` : 'turmas totais'}
          </p>
        </div>
      </div>

      {/* Busca por Aluno */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-colors">
        <h2 className="text-xl font-bold text-[#0A2463] dark:text-white mb-4">Buscar Aluno</h2>
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 dark:text-gray-500" />
          <input
            type="text"
            placeholder="Digite o nome, email ou matrícula do aluno..."
            value={studentSearch}
            onChange={(e) => setStudentSearch(e.target.value)}
            className="w-full pl-11 pr-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition"
          />
        </div>

        {studentsLoading && studentSearch && (
          <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Buscando alunos...</span>
          </div>
        )}

        {studentSearchResults.length > 0 && (
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {studentSearchResults.map((student) => (
              <div
                key={student.id}
                className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors cursor-pointer"
                onClick={() => handleViewStudentDetails(student)}
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#1E5AA8] to-[#4FC3F7] flex items-center justify-center text-white font-bold">
                    {student.name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2)}
                  </div>
                  <div>
                    <h3 className="font-semibold text-[#0A2463] dark:text-white">{student.name}</h3>
                    {student.email && (
                      <p className="text-sm text-gray-600 dark:text-gray-300">{student.email}</p>
                    )}
                  </div>
                </div>
                <div className="text-right flex items-center gap-3">
                  <div>
                    <p className="text-sm font-medium text-gray-700 dark:text-gray-200">
                      {getStudentClassroomName(student)}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">ID: {student.id}</p>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      console.log('=== CLIQUE NO BOTÃO EDITAR (BUSCA) ===');
                      console.log('student:', student);
                      e.preventDefault();
                      e.stopPropagation();

                      setTimeout(() => {
                        handleEditStudent(student);
                      }, 10);
                    }}
                    className="text-[#1E5AA8] hover:text-[#0A2463] p-1 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                    title="Editar aluno"
                  >
                    <User className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {studentSearch && !studentsLoading && studentSearchResults.length === 0 && (
          <div className="text-center py-4 text-gray-500 dark:text-gray-400">
            <GraduationCap className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>Nenhum aluno encontrado</p>
          </div>
        )}
      </div>

      {/* Buscar Turmas */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-colors">
        <h2 className="text-xl font-bold text-[#0A2463] dark:text-white mb-4">Buscar Turma</h2>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 dark:text-gray-500" />
          <input
            type="text"
            placeholder="Buscar por nome da turma, ano ou nível..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-11 pr-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition"
          />
        </div>
      </div>

      {/* Lista de Turmas */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden transition-colors">
        <div className="p-6 border-b border-gray-200 dark:border-gray-600">
          <h2 className="text-xl font-bold text-[#0A2463] dark:text-white">
            {searchTerm ? `Resultados da busca (${filteredTotal})` : 'Todas as Turmas'}
          </h2>
        </div>

        {isEmpty ? (
          <div className="text-center py-12">
            <BookOpen className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              {searchTerm ? 'Nenhuma turma encontrada' : 'Nenhuma turma cadastrada'}
            </h3>
            <p className="text-gray-500 dark:text-gray-400 mb-6">
              {searchTerm
                ? 'Tente ajustar os termos da busca'
                : 'Comece criando sua primeira turma'
              }
            </p>
            {!searchTerm && (
              <button
                onClick={() => setShowModal(true)}
                className="bg-[#1E5AA8] hover:bg-[#0A2463] text-white px-6 py-3 rounded-lg font-semibold flex items-center gap-2 mx-auto transition"
              >
                <Plus className="w-5 h-5" />
                Nova Turma
              </button>
            )}
          </div>
        ) : (
          <div className="divide-y divide-gray-200 dark:divide-gray-600">
            {classrooms.map((classroom) => (
              <div
                key={classroom.id}
                className="p-6 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors cursor-pointer"
                onClick={() => handleViewClassroomDetails(classroom)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-[#1E5AA8] to-[#4FC3F7] flex items-center justify-center text-white font-bold">
                      {classroom.name.charAt(0)}
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-[#0A2463] dark:text-white">
                        {classroom.name}
                      </h3>
                      <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-300">
                        <span>{classroom.gradeLevel}</span>
                        <span>•</span>
                        <span>Ano {classroom.year}</span>
                        <span>•</span>
                        <span>{classroom.studentIds?.length || 0} alunos</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getStatusColor(classroom.active)}`}>
                      {getStatusText(classroom.active)}
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        // TODO: Implementar menu de opções
                      }}
                      className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                    >
                      <MoreVertical className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>


      {/* Modal Nova Turma */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-md p-6 transition-colors">
            <h2 className="text-2xl font-bold text-[#0A2463] dark:text-white mb-6">Nova Turma</h2>
            <form onSubmit={handleCreateClassroom} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Nome da Turma</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition"
                  placeholder="Ex: 9º Ano A"
                  required
                  disabled={isCreating}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Nível/Série</label>
                <input
                  type="text"
                  value={formData.gradeLevel}
                  onChange={(e) => setFormData(prev => ({ ...prev, gradeLevel: e.target.value }))}
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition"
                  placeholder="Ex: 9º Ano"
                  required
                  disabled={isCreating}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Ano</label>
                <input
                  type="number"
                  value={formData.year}
                  onChange={(e) => setFormData(prev => ({ ...prev, year: parseInt(e.target.value) }))}
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-[#1E5AA8] focus:border-transparent outline-none transition"
                  min="2020"
                  max="2030"
                  required
                  disabled={isCreating}
                />
              </div>
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  disabled={isCreating}
                  className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg font-semibold text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isCreating}
                  className="flex-1 px-4 py-3 bg-[#1E5AA8] hover:bg-[#0A2463] disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-lg font-semibold shadow-md hover:shadow-lg transition flex items-center justify-center gap-2"
                >
                  {isCreating && (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  )}
                  {isCreating ? 'Criando...' : 'Criar Turma'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
    {sharedStudentModal}
    {sharedTransferModal}
    </>
  );
}
