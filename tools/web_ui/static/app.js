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
  closeRunModal,
  setupQueueEventListeners,
} from "./js/queue-runner.js";
import { setupReferenceViewListeners } from "./js/reference-view.js";

/**
 * Global operational event listeners (Rebuild, Sync, Modal close).
 */
function setupGlobalEventListeners() {
  // Rebuild & Validate Curriculum & Track Miniatures
  if (dom.btnRebuild) {
    dom.btnRebuild.addEventListener("click", async () => {
      openModal(
        "Rebuilding Content & Validating...",
        "Running Content Generator, Track Miniature Builder, and Curriculum Validator..."
      );
      try {
        const report = await api.generateContent();
        if (report.success) {
          if (dom.modalStatusBadge) {
            dom.modalStatusBadge.textContent = "PASSED - ZERO ERRORS";
            dom.modalStatusBadge.className = "badge badge-lg";
            dom.modalStatusBadge.style.color = "#10b981";
          }
          state.cacheBuster = Date.now();
          renderTestList();
        } else {
          if (dom.modalStatusBadge) {
            dom.modalStatusBadge.textContent = `FAILED (${report.failed} files with errors)`;
            dom.modalStatusBadge.className = "badge badge-lg";
            dom.modalStatusBadge.style.color = "#ef4444";
          }
        }

        let log = "";
        if (report.miniatures_updated) {
          log += `✓ Successfully generated & updated ${report.miniatures_updated} track miniature previews (PNG) and maps (SVG).\n\n`;
        }
        log += `Audited ${report.total_files} test files. Passed: ${report.passed}, Failed: ${report.failed}\n\n`;
        if (report.errors && report.errors.length > 0) {
          log += "--- ERRORS ---\n";
          report.errors.forEach((e) => {
            log += `[${e.severity}] [${e.test_id || "ALL"}] ${e.message}\n`;
          });
          log += "\n";
        }
        if (report.warnings && report.warnings.length > 0) {
          log += "--- WARNINGS ---\n";
          report.warnings.forEach((w) => {
            log += `[${w.severity}] [${w.test_id || "ALL"}] ${w.message}\n`;
          });
        }
        if (!report.errors.length && !report.warnings.length) {
          log += "All schema validations, 3D gate vectors, track miniatures, and career links PASSED perfectly!";
        }
        if (dom.modalLogText) dom.modalLogText.textContent = log;
      } catch (err) {
        if (dom.modalStatusBadge) dom.modalStatusBadge.textContent = "SERVER ERROR";
        if (dom.modalLogText) dom.modalLogText.textContent = "Error executing content generator: " + err.message;
      }
    });
  }

  // Live Sync to Assetto Corsa Root
  if (dom.btnSync) {
    dom.btnSync.addEventListener("click", async () => {
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
    if (e.target === dom.runModal) closeRunModal();
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

  await loadInitialData();
  pollQueueStatus();
}

// Initialize on DOM Ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
