import { RouterProvider } from "react-router";
import { router } from "./routes";
import { ThemeProvider } from "./components/ThemeProvider";
import { AuthProvider } from "@/contexts/AuthContext";
import { Toaster } from "sonner";
import { UserThemeSync } from "./components/UserThemeSync";
import { MotionProvider } from "@/motion/MotionProvider";
import { CinematicIntro } from "@/motion/CinematicIntro";

export default function App() {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="light"
      enableSystem={false}
      storageKey="pluseduc:theme:active"
    >
      <MotionProvider>
        <AuthProvider>
          <UserThemeSync />
          <RouterProvider router={router} />
          <Toaster position="top-right" richColors closeButton />
        </AuthProvider>
        {/* A abertura fica por cima enquanto a aplicação já carrega por baixo. */}
        <CinematicIntro />
      </MotionProvider>
    </ThemeProvider>
  );
}
