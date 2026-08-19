import { useEffect, useRef } from "react";
import { useTheme } from "next-themes";
import { useAuth } from "@/contexts/AuthContext";

const DEFAULT_THEME = "light" as const;
type UserTheme = "light" | "dark";

function getThemeStorageKey(userId: string | null, userEmail: string | null) {
  const identity = userId || userEmail?.trim().toLowerCase();
  return identity ? `pluseduc:theme:${identity}` : null;
}

export function UserThemeSync() {
  const { theme, setTheme } = useTheme();
  const { isAuthenticated, userId, userEmail } = useAuth();
  const storageKey = getThemeStorageKey(userId, userEmail);
  const loadedSessionKeyRef = useRef<string | null>(null);
  const pendingThemeRef = useRef<UserTheme | null>(null);
  const sessionKey = isAuthenticated && storageKey ? storageKey : "anonymous";

  useEffect(() => {
    if (loadedSessionKeyRef.current === sessionKey) {
      return;
    }

    loadedSessionKeyRef.current = sessionKey;
    pendingThemeRef.current = null;

    if (!isAuthenticated || !storageKey) {
      if (theme !== DEFAULT_THEME) {
        setTheme(DEFAULT_THEME);
      }
      return;
    }

    const storedTheme = localStorage.getItem(storageKey);
    const nextTheme: UserTheme = storedTheme === "dark" ? "dark" : DEFAULT_THEME;
    pendingThemeRef.current = nextTheme;

    if (theme !== nextTheme) {
      setTheme(nextTheme);
    }
  }, [isAuthenticated, sessionKey, storageKey, theme, setTheme]);

  useEffect(() => {
    if (!isAuthenticated || !storageKey || (theme !== "light" && theme !== "dark")) {
      return;
    }

    if (pendingThemeRef.current !== null) {
      if (theme !== pendingThemeRef.current) {
        return;
      }
      pendingThemeRef.current = null;
    }

    localStorage.setItem(storageKey, theme);
  }, [isAuthenticated, storageKey, theme]);

  return null;
}
