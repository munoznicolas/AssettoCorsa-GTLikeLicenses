import React, { useState, useEffect } from "react";
import { ThemeProvider, CssBaseline } from "@mui/material";
import { createAppTheme } from "./theme/theme";
import { CurriculumProvider } from "./context/CurriculumContext";
import { Header } from "./components/layout/Header";
import { DrawerMenu } from "./components/layout/DrawerMenu";
import { LicenseNav } from "./components/layout/LicenseNav";
import { Sidebar } from "./components/layout/Sidebar";
import { TestEditor } from "./components/editor/TestEditor";
import { ReferenceView } from "./components/reference/ReferenceView";
import { BatchTelemetryModal } from "./components/modals/BatchTelemetryModal";

export const App: React.FC = () => {
  const [themeMode, setThemeMode] = useState<"light" | "dark">(() => {
    try {
      const stored = localStorage.getItem("theme");
      if (stored === "light" || stored === "dark") return stored;
      return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
    } catch {
      return "dark";
    }
  });

  const [activeView, setActiveView] = useState<"editor" | "reference">("editor");
  const [mobileView, setMobileView] = useState<"catalog" | "editor">("catalog");
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isBatchOpen, setIsBatchOpen] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "info" | "success" | "error" } | null>(null);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", themeMode);
    try {
      localStorage.setItem("theme", themeMode);
    } catch {}
  }, [themeMode]);

  const toggleTheme = () => {
    setThemeMode((prev) => (prev === "dark" ? "light" : "dark"));
  };

  const showToast = (message: string, type: "info" | "success" | "error" = "info") => {
    setToast({ message, type });
    setTimeout(() => {
      setToast(null);
    }, 3500);
  };

  const theme = createAppTheme(themeMode);

  return (
    <ThemeProvider theme={theme}>
      <CurriculumProvider>
        <div id="app">
          {/* Top Header */}
          <Header
            isOpen={isMenuOpen}
            onToggleMenu={() => setIsMenuOpen((prev) => !prev)}
          />

          {/* Navigation Bar: License Tiers & GT Values */}
          <LicenseNav
            activeView={activeView}
            onSelectView={setActiveView}
            onSelectTier={() => setMobileView("catalog")}
          />

          {/* Main Body */}
          {activeView === "editor" ? (
            <div className={`workspace ${mobileView === "editor" ? "view-editor" : ""}`}>
              <Sidebar onSelectTest={() => setMobileView("editor")} />
              <TestEditor onShowToast={showToast} onBack={() => setMobileView("catalog")} />
            </div>
          ) : (
            <div className="workspace view-reference">
              <ReferenceView />
            </div>
          )}

          {/* Slide-out Hamburger Menu Drawer */}
          <DrawerMenu
            isOpen={isMenuOpen}
            theme={themeMode}
            onClose={() => setIsMenuOpen(false)}
            onToggleTheme={toggleTheme}
            onOpenBatchTelemetry={() => setIsBatchOpen(true)}
            onOpenTour={() => {
              showToast("Starting onboarding walkthrough...", "info");
            }}
            onShowToast={showToast}
          />

          {/* Batch Missing Telemetry Modal */}
          <BatchTelemetryModal
            isOpen={isBatchOpen}
            onClose={() => setIsBatchOpen(false)}
            onShowToast={showToast}
          />

          {/* Toast Notification */}
          {toast && (
            <div
              id="toast"
              className="toast"
              style={{
                display: "block",
                backgroundColor:
                  toast.type === "success"
                    ? "var(--accent-green)"
                    : toast.type === "error"
                    ? "var(--accent-danger)"
                    : "var(--bg-card)",
                color: toast.type === "success" || toast.type === "error" ? "#ffffff" : "var(--text-main)",
                border: "1px solid var(--border-color)",
                boxShadow: "0 4px 14px rgba(0, 0, 0, 0.4)",
              }}
            >
              {toast.message}
            </div>
          )}
        </div>
      </CurriculumProvider>
    </ThemeProvider>
  );
};
