import { useEffect, useState } from "react";
import { CircleAlert, Download, ExternalLink, Loader2, X } from "lucide-react";
import { appUpdateService, type AppUpdateStatus } from "@/services/appUpdate";

const SNOOZE_MS = 4 * 60 * 60 * 1000; // "Lembrar depois"
const SNOOZE_KEY = "pluseduc:update-snoozed";
const FAST_POLL_MS = 4000; // aguardando a primeira verificação ou acompanhando o download
const SLOW_POLL_MS = 30 * 60 * 1000;
const MAX_FAST_PENDING_POLLS = 15;

function readSnooze(): { version: string; until: number } | null {
  try {
    const raw = localStorage.getItem(SNOOZE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function writeSnooze(version: string) {
  try {
    localStorage.setItem(SNOOZE_KEY, JSON.stringify({ version, until: Date.now() + SNOOZE_MS }));
  } catch {
    // sem armazenamento local o aviso apenas volta no próximo carregamento
  }
}

function isSnoozed(version: string | null): boolean {
  const snooze = readSnooze();
  return !!version && !!snooze && snooze.version === version && snooze.until > Date.now();
}

function formatSize(bytes: number | null): string {
  return bytes ? ` (${(bytes / 1024 / 1024).toFixed(0)} MB)` : "";
}

/**
 * Aviso de nova versão do aplicativo de desktop. Fica oculto enquanto não há atualização (também sem internet, sem
 * release publicada ou fora do app instalado): qualquer erro de consulta é ignorado.
 */
export function UpdateNotice() {
  const [status, setStatus] = useState<AppUpdateStatus | null>(null);
  const [hiddenKey, setHiddenKey] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);

  useEffect(() => {
    let timer: number | undefined;
    let cancelled = false;
    let pendingPolls = 0;
    const tick = async () => {
      let next: AppUpdateStatus | null = null;
      try {
        next = await appUpdateService.getStatus();
        if (!cancelled) setStatus(next);
      } catch {
        // Backend sem este recurso (ex.: dev) ou já encerrado para instalar: nada a mostrar
      }
      if (cancelled) return;
      const busy = next?.download.state === "downloading" || next?.download.state === "launching";
      const waiting = next?.status === "pending" && pendingPolls++ < MAX_FAST_PENDING_POLLS;
      timer = window.setTimeout(tick, busy || waiting ? FAST_POLL_MS : SLOW_POLL_MS);
    };
    tick();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, []);

  const install = async () => {
    setStarting(true);
    setRequestError(null);
    try {
      setStatus(await appUpdateService.install());
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Não foi possível iniciar a atualização");
    } finally {
      setStarting(false);
    }
  };

  if (!status) return null;
  const { download } = status;
  const inProgress = download.state === "downloading" || download.state === "launching";
  const failed = download.state === "error" || !!requestError;
  const noticeKey = `${status.latestVersion}:${download.state}`;
  const wanted = (status.updateAvailable && !isSnoozed(status.latestVersion)) || inProgress || failed;
  if (!wanted || hiddenKey === noticeKey) return null;

  // "Lembrar depois": adia por algumas horas (guardado no navegador) e esconde o aviso agora
  const dismiss = () => {
    if (status.latestVersion) writeSnooze(status.latestVersion);
    setHiddenKey(noticeKey);
    setRequestError(null);
  };

  const percent = Math.round(download.progress * 100);
  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed bottom-4 right-4 z-[100] w-[min(24rem,calc(100vw-2rem))] rounded-xl border border-[#1E5AA8]/30 bg-white p-4 shadow-xl dark:border-[#1E5AA8]/50 dark:bg-gray-800"
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 rounded-lg bg-[#1E5AA8]/10 p-2 text-[#1E5AA8] dark:text-blue-300">
          {failed ? <CircleAlert className="h-5 w-5 text-red-600" /> : inProgress ? <Loader2 className="h-5 w-5 animate-spin" /> : <Download className="h-5 w-5" />}
        </div>
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-[#0A2463] dark:text-white">
            {download.state === "launching"
              ? `Instalando a versão ${status.latestVersion}…`
              : download.state === "downloading"
                ? `Baixando a versão ${status.latestVersion}… ${percent}%`
                : `Nova versão ${status.latestVersion} disponível`}
          </p>
          <p className="mt-0.5 text-sm text-gray-600 dark:text-gray-300">
            {download.state === "launching"
              ? "O PlusEduc vai fechar e abrir de novo sozinho. Seus dados e configurações são mantidos."
              : failed
                ? requestError ?? download.error
                : `Você está na versão ${status.currentVersion}${formatSize(status.installerSize)}.${status.canInstall ? "" : " Baixe o instalador na página da versão."}`}
          </p>
          {download.state === "downloading" && (
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
              <div className="h-full bg-[#1E5AA8] transition-all" style={{ width: `${percent}%` }} />
            </div>
          )}
          {!inProgress && (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              {status.canInstall ? (
                <button
                  type="button"
                  onClick={install}
                  disabled={starting}
                  className="rounded-lg bg-[#1E5AA8] px-3 py-1.5 text-sm font-medium text-white transition hover:bg-[#0A2463] disabled:opacity-60"
                >
                  {failed ? "Tentar novamente" : "Atualizar"}
                </button>
              ) : (
                status.releaseUrl && (
                  <a
                    href={status.releaseUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 rounded-lg bg-[#1E5AA8] px-3 py-1.5 text-sm font-medium text-white transition hover:bg-[#0A2463]"
                  >
                    Ver a versão <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                )
              )}
              <button
                type="button"
                onClick={dismiss}
                className="rounded-lg px-3 py-1.5 text-sm text-gray-600 transition hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
              >
                Lembrar depois
              </button>
            </div>
          )}
        </div>
        {!inProgress && (
          <button
            type="button"
            aria-label="Fechar aviso"
            onClick={dismiss}
            className="rounded p-1 text-gray-400 transition hover:text-gray-600"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}
