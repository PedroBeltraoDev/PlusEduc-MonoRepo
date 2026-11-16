import { useState } from "react";
import { m as motion } from "motion/react";
import { Gauge, Sparkles, Wind, Zap } from "lucide-react";
import { useMotion } from "@/motion/MotionProvider";
import { PROFILE_LABELS, type MotionProfile } from "@/motion/profiles";
import { INTRO_ALWAYS_KEY } from "@/motion/CinematicIntro";

const ICONS: Record<MotionProfile, typeof Sparkles> = { ultra: Sparkles, balanced: Wind, performance: Zap };
const ORDER: MotionProfile[] = ["ultra", "balanced", "performance"];

function readIntroAlways(): boolean {
  try {
    return localStorage.getItem(INTRO_ALWAYS_KEY) === "true";
  } catch {
    return false;
  }
}

function Toggle({ checked, onChange, label, description, disabled }: { checked: boolean; onChange: (value: boolean) => void; label: string; description: string; disabled?: boolean }) {
  const m = useMotion();
  return (
    <label className={`flex items-start justify-between gap-4 rounded-xl p-3 ${disabled ? "opacity-60" : "cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50"}`}>
      <span>
        <span className="block text-sm font-medium text-gray-800 dark:text-gray-100">{label}</span>
        <span className="mt-0.5 block text-xs text-gray-500 dark:text-gray-400">{description}</span>
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={`relative mt-0.5 inline-flex h-6 w-11 shrink-0 items-center rounded-full px-0.5 transition-colors ${checked ? "bg-[#1E5AA8] dark:bg-[#4FC3F7]" : "bg-gray-300 dark:bg-gray-600"}`}
      >
        <motion.span
          className="h-5 w-5 rounded-full bg-white shadow"
          animate={{ x: checked ? 20 : 0 }}
          transition={m.snappy}
        />
      </button>
    </label>
  );
}

/** Perfis do Ultra Motion (vale para o painel do professor e para o portal do aluno). */
export function MotionSettingsCard() {
  const m = useMotion();
  const [introAlways, setIntroAlways] = useState(readIntroAlways);

  const changeIntro = (value: boolean) => {
    setIntroAlways(value);
    try {
      localStorage.setItem(INTRO_ALWAYS_KEY, String(value));
    } catch {
      // armazenamento bloqueado: vale só nesta página
    }
  };

  return (
    <section className="rounded-2xl bg-white p-6 shadow-sm transition-colors dark:bg-gray-800" aria-labelledby="motion-title">
      <div className="flex items-start gap-4 border-b border-gray-200 pb-5 dark:border-gray-700">
        <div className="rounded-xl bg-[#1E5AA8]/10 p-3 text-[#1E5AA8] dark:bg-blue-400/10 dark:text-[#4FC3F7]">
          <Gauge className="h-6 w-6" />
        </div>
        <div>
          <h2 id="motion-title" className="text-lg font-semibold text-[#0A2463] dark:text-white">Animações (Ultra Motion)</h2>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
            Escolha quanto movimento a interface usa. A preferência fica salva neste navegador.
          </p>
        </div>
      </div>

      <div role="radiogroup" aria-label="Perfil de movimento" className="mt-5 grid gap-3 sm:grid-cols-3">
        {ORDER.map((profile) => {
          const Icon = ICONS[profile];
          const selected = m.chosen === profile;
          return (
            <button
              key={profile}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => m.setProfile(profile)}
              className={`relative overflow-hidden rounded-xl border-2 p-4 text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#4FC3F7] ${
                selected ? "border-[#1E5AA8] dark:border-[#4FC3F7]" : "border-gray-200 hover:border-gray-300 dark:border-gray-700 dark:hover:border-gray-600"
              }`}
            >
              {selected && (
                <motion.span
                  layoutId={m.reduced ? undefined : "motion-profile-selected"}
                  className="absolute inset-0 bg-blue-50 dark:bg-blue-950/40"
                  transition={m.snappy}
                  aria-hidden="true"
                />
              )}
              <span className="relative block">
                <Icon className="h-5 w-5 text-[#1E5AA8] dark:text-[#4FC3F7]" />
                <span className="mt-2 block font-semibold text-[#0A2463] dark:text-white">{PROFILE_LABELS[profile].title}</span>
                <span className="mt-1 block text-xs text-gray-600 dark:text-gray-300">{PROFILE_LABELS[profile].description}</span>
              </span>
            </button>
          );
        })}
      </div>

      {m.profile !== m.chosen && !m.reduced && (
        <p className="mt-3 text-xs text-amber-700 dark:text-amber-300" role="status">
          Ajuste automático ativo: usando o perfil {PROFILE_LABELS[m.profile].title} neste aparelho.
        </p>
      )}
      {m.systemReduced && (
        <p className="mt-3 text-xs text-amber-700 dark:text-amber-300" role="status">
          O sistema operacional pede movimento reduzido: os deslocamentos ficam desligados.
        </p>
      )}

      <div className="mt-4 space-y-1">
        <Toggle
          checked={m.autoAdjust}
          onChange={m.setAutoAdjust}
          label="Ajustar automaticamente"
          description="Reduz os efeitos em aparelhos mais simples ou quando a tela travar."
        />
        <Toggle
          checked={m.userReduced || m.systemReduced}
          onChange={m.setUserReduced}
          disabled={m.systemReduced}
          label="Reduzir movimentos não essenciais"
          description="Remove deslocamentos e efeitos decorativos, mantendo apenas mudanças de opacidade."
        />
        <Toggle
          checked={introAlways}
          onChange={changeIntro}
          label="Mostrar a abertura sempre"
          description="Por padrão, a abertura aparece uma vez por sessão do navegador."
        />
      </div>
    </section>
  );
}
