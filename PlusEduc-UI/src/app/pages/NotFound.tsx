import { Link } from "react-router";
import { Compass } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

// Endereço que não existe: em vez da tela técnica do React Router, mostra uma página clara com o caminho de volta.
export function NotFound() {
  const { isAuthenticated, getHomePath } = useAuth();
  const home = isAuthenticated ? getHomePath() : "/login";

  return (
    <div className="min-h-screen bg-[#F5F7FA] dark:bg-gray-900 flex items-center justify-center px-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 text-center shadow-lg dark:bg-gray-800">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-[#E8F0FB] text-[#1E5AA8]">
          <Compass className="h-7 w-7" />
        </div>
        <h1 className="text-2xl font-bold text-[#0A2463] dark:text-white">Página não encontrada</h1>
        <p className="mt-2 text-gray-600 dark:text-gray-300">O endereço digitado não existe ou foi movido.</p>
        <Link
          to={home}
          className="mt-6 inline-block rounded-lg bg-[#1E5AA8] px-5 py-2.5 font-medium text-white transition hover:bg-[#0A2463]"
        >
          {isAuthenticated ? "Voltar ao início" : "Ir para o login"}
        </Link>
      </div>
    </div>
  );
}
