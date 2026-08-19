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
import { AlunoHome } from "./pages/student/AlunoHome";
import { AlunoAtividades } from "./pages/student/AlunoAtividades";
import { AlunoAtividadeDetalhe } from "./pages/student/AlunoAtividadeDetalhe";
import { ProfessorAtividadeDetalhe } from "./pages/ProfessorAtividadeDetalhe";
import { AlunoTurma } from "./pages/student/AlunoTurma";
import { AlunoProfessores } from "./pages/student/AlunoProfessores";
import { AlunoNotas } from "./pages/student/AlunoNotas";

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
    ],
  },
]);
