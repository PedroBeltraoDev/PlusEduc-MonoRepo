// Item de menu lateral com indicador ativo deslizante (layoutId): ao trocar de página, o destaque
// "viaja" até o novo item com mola, em vez de piscar. Funciona igual nos dois portais.
import type { ComponentType, ReactNode } from 'react';
import { Link } from 'react-router';
import { m as motion } from 'motion/react';
import { useMotion } from './MotionProvider';

export function SidebarNavLink({
  to,
  icon: Icon,
  label,
  active,
  onNavigate,
  indicatorId,
  trailing,
}: {
  to: string;
  icon: ComponentType<{ className?: string }>;
  label: string;
  active: boolean;
  onNavigate?: () => void;
  /** Id do grupo do indicador (o menu do celular e o do computador são instâncias separadas). */
  indicatorId: string;
  trailing?: ReactNode;
}) {
  const m = useMotion();
  return (
    <Link
      to={to}
      onClick={onNavigate}
      aria-current={active ? 'page' : undefined}
      className={`group relative flex items-center gap-3 rounded-lg px-4 py-3 outline-none transition-colors focus-visible:ring-2 focus-visible:ring-[#4FC3F7] ${
        active ? 'text-white' : 'text-white/80 hover:bg-white/10 hover:text-white'
      }`}
    >
      {active && (
        <motion.span
          layoutId={m.profile === 'performance' || m.reduced ? undefined : indicatorId}
          className="absolute inset-0 rounded-lg bg-white/20 shadow-lg"
          transition={m.snappy}
          aria-hidden="true"
        />
      )}
      {active && (
        <motion.span
          layoutId={m.profile === 'performance' || m.reduced ? undefined : `${indicatorId}-bar`}
          className="absolute left-0 top-2 bottom-2 w-1 rounded-r-full bg-[#4FC3F7]"
          transition={m.snappy}
          aria-hidden="true"
        />
      )}
      <span className="relative flex items-center gap-3">
        <Icon className={`h-5 w-5 transition-transform duration-200 ${m.hover ? 'group-hover:translate-x-0.5' : ''}`} />
        <span className="font-medium">{label}</span>
      </span>
      {trailing && <span className="relative ml-auto">{trailing}</span>}
    </Link>
  );
}
