import { createBrowserRouter, Navigate } from "react-router";
import { DashboardLayout } from "./components/DashboardLayout";
import { StudentLayout } from "./components/StudentLayout";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { Turmas } from "./pages/Turmas";
import { Atividades } from "./pages/Atividades";
import { GerarAtividade } from "./pages/GerarAtividade";
import { NovaAtividade } from "./pages/NovaAtividade";
import { Configuracoes } from "./pages/Configuracoes";
import { MateriasTopicos } from "./pages/MateriasTopicos";
import { Materias } from "./pages/Materias";
import { MateriaTurmas } from "./pages/MateriaTurmas";
import { MateriaTurmaDesempenho } from "./pages/MateriaTurmaDesempenho";
import { AlunoHome } from "./pages/student/AlunoHome";
import { AlunoAtividades } from "./pages/student/AlunoAtividades";
import { AlunoAtividadeDetalhe } from "./pages/student/AlunoAtividadeDetalhe";
import { ProfessorAtividadeDetalhe } from "./pages/ProfessorAtividadeDetalhe";
import { AlunoTurma } from "./pages/student/AlunoTurma";
import { AlunoProfessores } from "./pages/student/AlunoProfessores";
import { AlunoNotas } from "./pages/student/AlunoNotas";
import { AlunoDesempenho } from "./pages/student/AlunoDesempenho";
import { AlunoConfiguracoes } from "./pages/student/AlunoConfiguracoes";

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
    path: "/",
    element: <DashboardLayout />,
    children: [
      {
        path: "dashboard",
        element: <Dashboard />,
      },
      {
        path: "turmas",
        element: <Turmas />,
      },
      {
        path: "atividades",
        element: <Atividades />,
      },
      {
        path: "atividades/:id",
        element: <ProfessorAtividadeDetalhe />,
      },
      {
        path: "gerar-atividade",
        element: <GerarAtividade />,
      },
      {
        path: "nova-atividade",
        element: <NovaAtividade />,
      },
      {
        path: "configuracoes",
        element: <Configuracoes />,
      },
      {
        path: "materias",
        element: <Materias />,
      },
      {
        path: "materias/:subjectId/turmas",
        element: <MateriaTurmas />,
      },
      {
        path: "materias/:subjectId/turmas/:classroomId/desempenho",
        element: <MateriaTurmaDesempenho />,
      },
      {
        path: "materias-topicos",
        element: <MateriasTopicos />,
      },
    ],
  },
  {
    path: "/aluno",
    element: <StudentLayout />,
    children: [
      {
        index: true,
        element: <AlunoHome />,
      },
      {
        path: "atividades",
        element: <AlunoAtividades />,
      },
      {
        path: "atividades/:id",
        element: <AlunoAtividadeDetalhe />,
      },
      {
        path: "turma",
        element: <AlunoTurma />,
      },
      {
        path: "professores",
        element: <AlunoProfessores />,
      },
      {
        path: "notas",
        element: <AlunoNotas />,
      },
      {
        path: "desempenho",
        element: <AlunoDesempenho />,
      },
      {
        path: "configuracoes",
        element: <AlunoConfiguracoes />,
      },
    ],
  },
]);
