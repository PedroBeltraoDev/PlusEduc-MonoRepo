import { useLocation, useNavigate } from "react-router";
import { SidebarNavLink } from "@/motion/SidebarNavLink";
import { BarChart3, BookOpen, ClipboardCheck, History, LayoutDashboard, Users, ClipboardList, Settings, LogOut } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { cn } from "./ui/utils";

// Rotas que pertencem a um item de menu além do próprio caminho (telas de criação, detalhe, etc.).
const relatedPaths: Record<string, string[]> = {
  "/atividades": ["/gerar-atividade", "/nova-atividade"],
  "/materias": ["/materias-topicos"],
};

export const isMenuItemActive = (itemPath: string, pathname: string) =>
  pathname === itemPath ||
  pathname.startsWith(`${itemPath}/`) ||
  (relatedPaths[itemPath] ?? []).some((related) => pathname === related || pathname.startsWith(`${related}/`));

export const menuItems = [
  { icon: LayoutDashboard, label: "Dashboard", path: "/dashboard" },
  { icon: Users, label: "Turmas", path: "/turmas" },
  { icon: ClipboardList, label: "Atividades", path: "/atividades" },
  { icon: ClipboardCheck, label: "Notas e Frequência", path: "/notas" },
  { icon: BarChart3, label: "Relatórios", path: "/relatorios" },
  { icon: History, label: "Histórico", path: "/historico" },
  { icon: BookOpen, label: "Minhas matérias", path: "/materias" },
  { icon: Settings, label: "Configurações", path: "/configuracoes" },
];

interface SidebarProps {
  className?: string;
  onNavigate?: () => void;
}

export function Sidebar({ className, onNavigate }: SidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { userName, logout, role } = useAuth();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const displayName = userName || (role === "ADMIN" ? "Administrador" : "Professor");
  const displayInitials = userName
    ? userName.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)
    : "PR";

  return (
    <div
      className={cn(
        "bg-gradient-to-b from-[#0A2463] to-[#1E5AA8] dark:from-gray-900 dark:to-gray-800 text-white flex h-full flex-col shadow-xl transition-colors",
        className,
      )}
    >
      {/* Avatar e Info do Usuário */}
      <div className="p-6 flex flex-col items-center border-b border-white/10">
        <div className="w-16 h-16 rounded-full bg-white/20 flex items-center justify-center mb-3 ring-4 ring-white/10">
          <span className="text-2xl font-bold text-white">{displayInitials}</span>
        </div>
        <h3 className="font-semibold text-white">{displayName}</h3>
        <p className="text-xs text-white/70 mt-1">{role === "ADMIN" ? "Administrador" : "Educador"}</p>
        <button
          onClick={handleLogout}
          className="mt-3 px-3 py-1 bg-white/10 hover:bg-white/20 text-white text-xs rounded-full transition-colors flex items-center gap-1"
          title="Fazer logout"
        >
          <LogOut className="w-3 h-3" />
          Sair
        </button>
      </div>

      {/* Menu Items */}
      <nav className="flex-1 px-4 py-6 space-y-1">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = isMenuItemActive(item.path, location.pathname);

          return (
            <SidebarNavLink
              key={item.path}
              to={item.path}
              icon={Icon}
              label={item.label}
              active={isActive}
              onNavigate={onNavigate}
              indicatorId={onNavigate ? "staff-nav-mobile" : "staff-nav"}
            />
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-white/10">
        <p className="text-xs text-white/60 text-center">PlusEduc © {new Date().getFullYear()}</p>
      </div>
    </div>
  );
}
