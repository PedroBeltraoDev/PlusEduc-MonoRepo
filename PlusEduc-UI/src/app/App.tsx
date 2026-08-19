import { RouterProvider } from "react-router";
import { router } from "./routes";
import { ThemeProvider } from "./components/ThemeProvider";
import { AuthProvider } from "@/contexts/AuthContext";
import { Toaster } from "sonner";
import { UserThemeSync } from "./components/UserThemeSync";

export default function App() {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="light"
      enableSystem={false}
      storageKey="pluseduc:theme:active"
    >
      <AuthProvider>
        <UserThemeSync />
        <RouterProvider router={router} />
        <Toaster position="top-right" richColors />
      </AuthProvider>
    </ThemeProvider>
  );
}
