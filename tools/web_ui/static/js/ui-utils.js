/**
 * ui-utils.js
 * Toast notifications, modal helpers, text escaping, and time formatting.
 */

import { dom } from "./dom.js";

let toastTimer = null;

/**
 * Display toast alert popup in bottom-right corner.
 * @param {string} message
 * @param {"success"|"error"|"warning"|"info"} type
 */
export function showToast(message, type = "success") {
  if (!dom.toast) return;
  dom.toast.textContent = message;
  dom.toast.className = `toast ${type}`;
  dom.toast.style.display = "block";

  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    if (dom.toast) dom.toast.style.display = "none";
  }, 3500);
}

/**
 * Open the primary operation / log modal.
 * @param {string} title
 * @param {string} initialLog
 */
export function openModal(title, initialLog) {
  if (!dom.logModal) return;
  if (dom.modalTitle) dom.modalTitle.textContent = title;
  if (dom.modalStatusBadge) {
    dom.modalStatusBadge.textContent = "IN PROGRESS";
    dom.modalStatusBadge.className = "badge badge-lg";
    dom.modalStatusBadge.style.color = "#38bdf8";
  }
  if (dom.modalLogText) dom.modalLogText.textContent = initialLog;
  dom.logModal.style.display = "flex";
}

/**
 * Close the primary operation / log modal.
 */
export function closeModal() {
  if (dom.logModal) dom.logModal.style.display = "none";
}

/**
 * Safe HTML escaping to prevent XSS in dynamic strings.
 * @param {string} text
 * @returns {string}
 */
export function escapeHtml(text) {
  if (text === null || text === undefined) return "";
  const div = document.createElement("div");
  div.textContent = String(text);
  return div.innerHTML;
}

/**
 * Format raw seconds as mm:ss.fff or ss.fff string.
 * @param {number} totalSeconds
 * @returns {string}
 */
export function formatTimeDisplay(totalSeconds) {
  if (totalSeconds === null || totalSeconds === undefined || isNaN(totalSeconds)) {
    return "--:--.---";
  }
  const mins = Math.floor(totalSeconds / 60);
  const secs = totalSeconds % 60;
  if (mins > 0) {
    return `${mins}:${secs < 10 ? "0" : ""}${secs.toFixed(3)}`;
  }
  return `${secs.toFixed(3)}s`;
}

