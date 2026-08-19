import { Link, useLocation, useNavigate } from "react-router";
import { LayoutDashboard, Users, ClipboardList, Settings, LogOut } from "lucide-react";
import { LogoIcon } from "./Logo";
import { useAuth } from "@/contexts/AuthContext";
import { cn } from "./ui/utils";

export const menuItems = [
  { icon: LayoutDashboard, label: "Dashboard", path: "/dashboard" },
  { icon: Users, label: "Turmas", path: "/turmas" },
  { icon: ClipboardList, label: "Atividades", path: "/atividades" },
  { icon: Settings, label: "Configurações", path: "/configuracoes" },
];

interface SidebarProps {
  className?: string;
  onNavigate?: () => void;
}

export function Sidebar({ className, onNavigate }: SidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { userName, logout } = useAuth();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Por enquanto, usar dados mock até implementarmos perfil do usuário
  const displayName = userName || "Professor";
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
        <p className="text-xs text-white/70 mt-1">Educador</p>
        <button
          onClick={handleLogout}
          className="mt-3 px-3 py-1 bg-white/10 hover:bg-white/20 text-white text-xs rounded-full transition-colors flex items-center gap-1"
          title="Fazer logout"
        >
          <LogOut className="w-3 h-3" />
          Sair
        </button>
      </div>

      {/* Logo Icon */}
      <div className="px-6 py-4 flex justify-center border-b border-white/10">
        <LogoIcon />
      </div>

      {/* Menu Items */}
      <nav className="flex-1 px-4 py-6 space-y-1">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path || 
            (item.path === "/atividades" && ["/gerar-atividade", "/nova-atividade"].includes(location.pathname));
          
          return (
            <Link
              key={item.path}
              to={item.path}
              onClick={onNavigate}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                isActive
                  ? "bg-white/20 text-white shadow-lg"
                  : "text-white/80 hover:bg-white/10 hover:text-white"
              }`}
            >
              <Icon className="w-5 h-5" />
              <span className="font-medium">{item.label}</span>
              {(item as any).badge && (
                <span className="ml-auto px-2 py-0.5 bg-[#FF9800] text-white text-xs font-semibold rounded-full">
                  {(item as any).badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-white/10">
        <p className="text-xs text-white/60 text-center">PlusEduc © 2026</p>
      </div>
    </div>
  );
}
