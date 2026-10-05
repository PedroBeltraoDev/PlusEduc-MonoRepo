import { createBrowserRouter, Navigate } from "react-router";
import { DashboardLayout } from "./components/DashboardLayout";
import { StudentLayout } from "./components/StudentLayout";
import { Login } from "./pages/Login";

// Cada página é carregada sob demanda (code splitting por rota): o bundle inicial traz só o login e os layouts.
export const router = createBrowserRouter([
  {
    path: "/",
    element: <Navigate to="/login" replace />,
  },
  {
    path: "/login",
    element: <Login />,
  },
  {
    path: "/esqueci-senha",
    lazy: async () => ({ Component: (await import("./pages/ForgotPassword")).ForgotPassword }),
  },
  {
    path: "/",
    element: <DashboardLayout />,
    children: [
      {
        path: "dashboard",
        lazy: async () => ({ Component: (await import("./pages/Dashboard")).Dashboard }),
      },
      {
        path: "turmas",
        lazy: async () => ({ Component: (await import("./pages/Turmas")).Turmas }),
      },
      {
        path: "notas",
        lazy: async () => ({ Component: (await import("./pages/Notas")).Notas }),
      },
      {
        path: "atividades",
        lazy: async () => ({ Component: (await import("./pages/Atividades")).Atividades }),
      },
      {
        path: "atividades/:id",
        lazy: async () => ({ Component: (await import("./pages/ProfessorAtividadeDetalhe")).ProfessorAtividadeDetalhe }),
      },
      {
        path: "gerar-atividade",
        lazy: async () => ({ Component: (await import("./pages/GerarAtividade")).GerarAtividade }),
      },
      {
        path: "nova-atividade",
        lazy: async () => ({ Component: (await import("./pages/NovaAtividade")).NovaAtividade }),
      },
      {
        path: "configuracoes",
        lazy: async () => ({ Component: (await import("./pages/Configuracoes")).Configuracoes }),
      },
      {
        path: "materias",
        lazy: async () => ({ Component: (await import("./pages/Materias")).Materias }),
      },
      {
        path: "materias/:subjectId/turmas",
        lazy: async () => ({ Component: (await import("./pages/MateriaTurmas")).MateriaTurmas }),
      },
      {
        path: "materias/:subjectId/turmas/:classroomId/desempenho",
        lazy: async () => ({ Component: (await import("./pages/MateriaTurmaDesempenho")).MateriaTurmaDesempenho }),
      },
      {
        path: "materias-topicos",
        lazy: async () => ({ Component: (await import("./pages/MateriasTopicos")).MateriasTopicos }),
      },
    ],
  },
  {
    path: "/aluno",
    element: <StudentLayout />,
    children: [
      {
        index: true,
        lazy: async () => ({ Component: (await import("./pages/student/AlunoHome")).AlunoHome }),
      },
      {
        path: "atividades",
        lazy: async () => ({ Component: (await import("./pages/student/AlunoAtividades")).AlunoAtividades }),
      },
      {
        path: "atividades/:id",
        lazy: async () => ({ Component: (await import("./pages/student/AlunoAtividadeDetalhe")).AlunoAtividadeDetalhe }),
      },
      {
        path: "turma",
        lazy: async () => ({ Component: (await import("./pages/student/AlunoTurma")).AlunoTurma }),
      },
      {
        path: "professores",
        lazy: async () => ({ Component: (await import("./pages/student/AlunoProfessores")).AlunoProfessores }),
      },
      {
        path: "notas",
        lazy: async () => ({ Component: (await import("./pages/student/AlunoNotas")).AlunoNotas }),
      },
      {
        path: "desempenho",
        lazy: async () => ({ Component: (await import("./pages/student/AlunoDesempenho")).AlunoDesempenho }),
      },
      {
        path: "configuracoes",
        lazy: async () => ({ Component: (await import("./pages/student/AlunoConfiguracoes")).AlunoConfiguracoes }),
      },
    ],
  },
]);
