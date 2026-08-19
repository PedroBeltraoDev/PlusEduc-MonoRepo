import { Link, useLocation, useNavigate } from "react-router";
import { BookOpen, ClipboardList, GraduationCap, Home, LogOut, Users } from "lucide-react";
import { LogoIcon } from "./Logo";
import { useAuth } from "@/contexts/AuthContext";
import { cn } from "./ui/utils";

export const studentMenuItems = [
  { icon: Home, label: "Início", path: "/aluno" },
  { icon: ClipboardList, label: "Atividades", path: "/aluno/atividades" },
  { icon: Users, label: "Minha Turma", path: "/aluno/turma" },
  { icon: GraduationCap, label: "Professores", path: "/aluno/professores" },
  { icon: BookOpen, label: "Minhas Notas", path: "/aluno/notas" },
];

interface StudentSidebarProps {
  className?: string;
  onNavigate?: () => void;
}

export function StudentSidebar({ className, onNavigate }: StudentSidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { userName, logout } = useAuth();

  const displayName = userName || "Aluno";
  const displayInitials = userName
    ? userName.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
    : "AL";

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div
      className={cn(
        "bg-gradient-to-b from-[#0A2463] to-[#1E5AA8] dark:from-gray-900 dark:to-gray-800 text-white flex h-full flex-col shadow-xl transition-colors",
        className
      )}
    >
      <div className="p-6 flex flex-col items-center border-b border-white/10">
        <div className="w-16 h-16 rounded-full bg-white/20 flex items-center justify-center mb-3 ring-4 ring-white/10">
          <span className="text-2xl font-bold text-white">{displayInitials}</span>
        </div>
        <h3 className="font-semibold text-white">{displayName}</h3>
        <p className="text-xs text-white/70 mt-1">Área do Aluno</p>
        <button
          onClick={handleLogout}
          className="mt-3 px-3 py-1 bg-white/10 hover:bg-white/20 text-white text-xs rounded-full transition-colors flex items-center gap-1"
          title="Sair"
        >
          <LogOut className="w-3 h-3" />
          Sair
        </button>
      </div>

      <div className="px-6 py-4 flex justify-center border-b border-white/10">
        <LogoIcon />
      </div>

      <nav className="flex-1 px-4 py-6 space-y-1">
        {studentMenuItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            location.pathname === item.path ||
            (item.path !== "/aluno" && location.pathname.startsWith(item.path));

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
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-white/10">
        <p className="text-xs text-white/60 text-center">PlusEduc © 2026</p>
      </div>
    </div>
  );
}
