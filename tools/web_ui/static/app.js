/**
 * app.js
 * Assetto Corsa GT-Like License Test Designer - Root Orchestrator
 */

import { state } from "./js/state.js";
import { dom, initDom } from "./js/dom.js";
import { api } from "./js/api.js";
import { showToast, openModal, closeModal } from "./js/ui-utils.js";
import { initCanvasInteraction } from "./js/track-canvas.js";
import {
  loadInitialData,
  renderTestList,
  setupEditorEventListeners,
} from "./js/test-editor.js";
import {
  pollQueueStatus,
  setupQueueEventListeners,
} from "./js/queue-runner.js";
import { setupReferenceViewListeners } from "./js/reference-view.js";
import { initTelemetrySubmitter } from "./js/telemetry-submitter.js";
import { buildAndExportModZip } from "./js/mod-packager.js";

/**
 * Global operational event listeners (Rebuild, Sync, Modal close).
 */
function setupGlobalEventListeners() {
  // Export Content Manager Mod (.zip) with pure client-side validation & packaging
  if (dom.btnRebuild) {
    dom.btnRebuild.addEventListener("click", async () => {
      openModal(
        "Exporting Content Manager Mod...",
        "Validating tests and packaging drag-and-drop Content Manager archive (.zip)..."
      );
      if (dom.modalStatusBadge) {
        dom.modalStatusBadge.textContent = "BUILDING ZIP";
        dom.modalStatusBadge.className = "badge badge-lg";
        dom.modalStatusBadge.style.color = "#38bdf8";
      }

      try {
        const result = await buildAndExportModZip(state.curriculum, (percent, msg) => {
          if (dom.modalLogText) {
            dom.modalLogText.textContent = `[${percent}%] ${msg}`;
          }
        });

        if (dom.modalStatusBadge) {
          dom.modalStatusBadge.textContent = "READY FOR CM";
          dom.modalStatusBadge.className = "badge badge-lg";
          dom.modalStatusBadge.style.color = "#10b981";
        }

        const rep = result.validation;
        const sizeMb = (result.size / (1024 * 1024)).toFixed(2);
        let log = `✓ Content Manager package created successfully (${sizeMb} MB)!\n`;
        log += `✓ Download started: AssettoCorsa_GT_License_Center.zip\n\n`;
        log += `--- VALIDATION AUDIT ---\n`;
        log += `Audited ${rep.total_files} tests across 5 license tiers: ${rep.passed} passed, 0 failed.\n`;
        log += `All Content Manager series.ini, event.ini, and test JSON definitions generated.\n\n`;
        log += `Installation instructions:\n`;
        log += `1. Locate the downloaded AssettoCorsa_GT_License_Center.zip in your browser downloads.\n`;
        log += `2. Drag and drop the .zip file directly into Content Manager.\n`;
        log += `3. Click 'Install' in the top-right green menu to play!`;

        if (dom.modalLogText) dom.modalLogText.textContent = log;
        showToast("Mod package exported successfully!", "success");
      } catch (err) {
        if (dom.modalStatusBadge) {
          dom.modalStatusBadge.textContent = "EXPORT FAILED";
          dom.modalStatusBadge.style.color = "#ef4444";
        }
        if (dom.modalLogText) {
          dom.modalLogText.textContent = `Error building Content Manager package: ${err.message}`;
        }
        showToast(`Export error: ${err.message}`, "error");
      }
    });
  }

  // Live Sync to Assetto Corsa Root (with friendly static host fallback)
  if (dom.btnSync) {
    const isStatic =
      window.location.hostname.endsWith("github.io") ||
      window.location.protocol === "file:" ||
      Boolean(window.IS_STATIC_HOST);

    dom.btnSync.addEventListener("click", async () => {
      if (isStatic) {
        openModal("Sync to Assetto Corsa", "Local Installation Notice");
        if (dom.modalStatusBadge) {
          dom.modalStatusBadge.textContent = "LOCAL STUDIO ONLY";
          dom.modalStatusBadge.className = "badge badge-lg";
          dom.modalStatusBadge.style.color = "#f59e0b";
        }
        if (dom.modalLogText) {
          dom.modalLogText.textContent =
            "Direct filesystem sync is available when running the developer studio locally via:\n\n" +
            "  python tools/web_ui/server.py\n\n" +
            "To install your changes from the web onto Assetto Corsa:\n" +
            "  1. Click 'Export' in the top navbar to download AssettoCorsa_GT_License_Center.zip.\n" +
            "  2. Drag and drop the downloaded ZIP directly into Content Manager to install!";
        }
        return;
      }

      openModal("Sync to Assetto Corsa", "Synchronizing files to local Assetto Corsa directory...");
      try {
        const data = await api.syncToAC();
        if (data.success) {
          if (dom.modalStatusBadge) {
            dom.modalStatusBadge.textContent = "SYNC COMPLETE";
            dom.modalStatusBadge.className = "badge badge-lg";
            dom.modalStatusBadge.style.color = "#10b981";
          }
          if (dom.modalLogText) dom.modalLogText.textContent = data.message;
        } else {
          if (dom.modalStatusBadge) {
            dom.modalStatusBadge.textContent = "SYNC FAILED";
            dom.modalStatusBadge.className = "badge badge-lg";
            dom.modalStatusBadge.style.color = "#ef4444";
          }
          if (dom.modalLogText) dom.modalLogText.textContent = data.error;
        }
      } catch (err) {
        if (dom.modalStatusBadge) dom.modalStatusBadge.textContent = "NETWORK ERROR";
        if (dom.modalLogText) dom.modalLogText.textContent = err.message;
      }
    });
  }

  // Modal Close Buttons
  if (dom.modalClose) dom.modalClose.addEventListener("click", closeModal);
  if (dom.modalBtnOk) dom.modalBtnOk.addEventListener("click", closeModal);

  // Outside Click Close for Modals
  window.addEventListener("click", (e) => {
    if (e.target === dom.logModal) closeModal();
  });
}

/**
 * Bootstrap the application.
 */
async function init() {
  initDom();
  initCanvasInteraction();
  setupEditorEventListeners();
  setupQueueEventListeners();
  setupReferenceViewListeners();
  setupGlobalEventListeners();
  initTelemetrySubmitter();

  await loadInitialData();
  pollQueueStatus();
}

// Initialize on DOM Ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
