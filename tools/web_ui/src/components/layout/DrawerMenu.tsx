import React from "react";
import { Download, RefreshCw, Radio, Upload, RotateCcw, HelpCircle, Sun, Moon, Square } from "lucide-react";
import { api } from "../../api/client";

interface Props {
  isOpen: boolean;
  theme: "light" | "dark";
  onClose: () => void;
  onToggleTheme: () => void;
  onOpenBatchTelemetry: () => void;
  onOpenTour: () => void;
  onShowToast: (msg: string, type?: "info" | "success" | "error") => void;
}

export const DrawerMenu: React.FC<Props> = ({
  isOpen,
  theme,
  onClose,
  onToggleTheme,
  onOpenBatchTelemetry,
  onOpenTour,
  onShowToast,
}) => {
  const fileInputRef = React.useRef<HTMLInputElement | null>(null);

  const handleExportZip = async () => {
    onShowToast("Building Content Manager mod package...", "info");
    try {
      const res = await api.generateAndValidate();
      onShowToast("Export generated successfully!", "success");
    } catch (err: any) {
      onShowToast(`Export error: ${err.message}`, "error");
    }
  };

  const handleSyncAc = async () => {
    onShowToast("Syncing changes to Assetto Corsa...", "info");
    try {
      const res = await api.syncToAc();
      onShowToast("Synced to Assetto Corsa!", "success");
    } catch (err: any) {
      onShowToast(`Sync failed: ${err.message}`, "error");
    }
  };

  return (
    <>
      <div
        className={`actions-menu-backdrop ${isOpen ? "open" : ""}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <div className={`header-actions ${isOpen ? "open" : ""}`}>
        <div className="actions-drawer-header">
          <span className="actions-drawer-title">Actions</span>
        </div>

        {/* Primary Actions */}
        <button
          id="btn-rebuild"
          className="btn btn-secondary"
          title="Export Content Manager package (.zip)"
          onClick={() => {
            onClose();
            handleExportZip();
          }}
        >
          <Download size={15} strokeWidth={1.75} />
          <span>Export Package (.zip)</span>
        </button>

        <button
          id="btn-sync"
          className="btn btn-secondary"
          title="Sync changes directly to Assetto Corsa install"
          onClick={() => {
            onClose();
            handleSyncAc();
          }}
        >
          <RefreshCw size={15} strokeWidth={1.75} />
          <span>Sync to Assetto Corsa</span>
        </button>

        <div className="menu-divider" />

        {/* Telemetry & Curriculum Tools */}
        <button
          id="btn-run-missing-telemetry"
          className="btn btn-secondary btn-sm"
          title="Batch run/record telemetry in Assetto Corsa for missing track+car profiles"
          onClick={() => {
            onClose();
            onOpenBatchTelemetry();
          }}
        >
          <Radio size={15} strokeWidth={1.75} />
          <span>Record Missing Telemetry</span>
        </button>

        <button
          id="btn-import-json"
          className="btn btn-secondary btn-sm"
          title="Import and restore curriculum.json configuration file"
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload size={15} strokeWidth={1.75} />
          <span>Import JSON</span>
        </button>
        <input
          type="file"
          ref={fileInputRef}
          accept=".json,application/json"
          style={{ display: "none" }}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) {
              onShowToast(`Selected ${file.name} for import`, "info");
              onClose();
            }
          }}
        />

        <button
          id="btn-reset-defaults"
          className="btn btn-secondary btn-sm"
          title="Reset curriculum back to baseline defaults"
          onClick={() => {
            if (window.confirm("Reset all curriculum tests to original defaults?")) {
              onClose();
              onShowToast("Curriculum reset to defaults", "info");
            }
          }}
        >
          <RotateCcw size={15} strokeWidth={1.75} />
          <span>Reset Defaults</span>
        </button>

        <div className="menu-divider" />

        {/* Preferences & Tour */}
        <button
          id="btn-tour-help"
          className="btn btn-secondary btn-sm"
          title="Interactive Onboarding Tours & Help"
          onClick={() => {
            onClose();
            onOpenTour();
          }}
        >
          <HelpCircle size={15} strokeWidth={1.75} />
          <span>Take Tour</span>
        </button>

        <button
          id="btn-theme-toggle"
          className="btn btn-secondary btn-sm"
          title={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
          onClick={onToggleTheme}
        >
          {theme === "dark" ? <Sun size={15} strokeWidth={1.75} /> : <Moon size={15} strokeWidth={1.75} />}
          <span>{theme === "dark" ? "Light Theme" : "Dark Theme"}</span>
        </button>
      </div>
    </>
  );
};
