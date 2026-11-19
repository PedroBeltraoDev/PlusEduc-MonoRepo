import { Outlet, Navigate, useLocation } from "react-router";
import { PageTransition } from "@/motion/primitives";
import { Loader2, Menu } from "lucide-react";
import { useState } from "react";
import { StudentSidebar } from "./StudentSidebar";
import { useAuth } from "@/contexts/AuthContext";
import { Sheet, SheetContent, SheetTitle } from "./ui/sheet";

export function StudentLayout() {
  const { isAuthenticated, loadingState, isStudent } = useAuth();
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const location = useLocation();

  if (loadingState === "loading") {
    return (
      <div className="min-h-screen bg-[#F5F7FA] dark:bg-gray-900 flex items-center justify-center">
        <div className="flex items-center gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-[#1E5AA8]" />
          <span className="text-lg text-gray-600 dark:text-gray-300">Carregando...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!isStudent) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="min-h-screen bg-[#F5F7FA] dark:bg-gray-900 transition-colors">
      <a
        href="#conteudo"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:text-[#0A2463] focus:shadow-lg"
      >
        Pular para o conteúdo
      </a>
      <aside className="fixed inset-y-0 left-0 hidden w-64 lg:block">
        <StudentSidebar className="w-64" />
      </aside>

      <div className="sticky top-0 z-30 border-b border-gray-200 bg-[#F5F7FA]/95 px-4 py-3 backdrop-blur dark:border-gray-700 dark:bg-gray-900/95 lg:hidden">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setMobileSidebarOpen(true)}
            className="rounded-lg border border-gray-200 bg-white p-2 text-[#0A2463] shadow-sm transition hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
            aria-label="Abrir menu"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div>
            <p className="text-sm font-semibold text-[#0A2463] dark:text-white">PlusEduc</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Área do aluno</p>
          </div>
        </div>
      </div>

      <Sheet open={mobileSidebarOpen} onOpenChange={setMobileSidebarOpen}>
        <SheetContent side="left" className="w-64 p-0">
          <SheetTitle className="sr-only">Menu do aluno</SheetTitle>
          <StudentSidebar className="w-full" onNavigate={() => setMobileSidebarOpen(false)} />
        </SheetContent>
      </Sheet>

      <main id="conteudo" tabIndex={-1} className="p-4 outline-none md:p-6 lg:ml-64 lg:p-8">
        <PageTransition routeKey={location.pathname}>
          <Outlet />
        </PageTransition>
      </main>
    </div>
  );
}
