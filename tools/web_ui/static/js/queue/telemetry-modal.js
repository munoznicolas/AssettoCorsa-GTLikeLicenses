/**
 * queue/telemetry-modal.js
 * Missing telemetry modal & batch queueing.
 */

import { state } from "../state.js";
import { dom } from "../dom.js";
import { api } from "../api.js";
import { showToast, escapeHtml } from "../ui-utils.js";
import { pollQueueStatus } from "../queue-runner.js";

/**
 * Open the missing telemetry batch runner modal.
 */
export async function openMissingTelemetryModal() {
  if (dom.telemetryBatchModal) {
    dom.telemetryBatchModal.style.display = "flex";
  }
  // Default to current active tier if valid, or "ALL"
  const currentTier = state.curriculum[state.activeTierIndex]?.tier_name;
  if (dom.selectTelemetryTier && currentTier) {
    const opts = Array.from(dom.selectTelemetryTier.options).map((o) => o.value);
    if (opts.includes(currentTier)) {
      dom.selectTelemetryTier.value = currentTier;
    }
  }
  await loadMissingTelemetryData();
}

/**
 * Close the missing telemetry batch runner modal.
 */
export function closeMissingTelemetryModal() {
  if (dom.telemetryBatchModal) {
    dom.telemetryBatchModal.style.display = "none";
  }
}

/**
 * Render HTML for a telemetry combo status badge.
 */
export function getTelemetryStatusBadge(combo) {
  if (combo.is_cached) {
    return `<span class="badge" style="background: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.4);">✓ Recorded</span>`;
  }
  if (combo.is_queued) {
    return `<span class="badge" style="background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4);">⏳ In Queue</span>`;
  }
  return `<span class="badge" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4);">⚠️ Missing</span>`;
}

/**
 * Render a single telemetry combo table row.
 */
export function renderTelemetryComboRow(combo) {
  const statusBadge = getTelemetryStatusBadge(combo);
  const layoutLabel = combo.track_layout
    ? escapeHtml(combo.track_layout)
    : `<span style="color: #64748b; font-style: italic;">Default</span>`;

  const testTags = (combo.test_ids || [])
    .map(
      (id) =>
        `<span class="tag-code" style="font-size: 10px; margin-right: 4px; padding: 1px 5px; background: rgba(255,255,255,0.08); border-radius: 3px;">${escapeHtml(id)}</span>`
    )
    .join("");

  return `
    <tr style="${combo.is_cached ? "opacity: 0.6;" : ""}">
      <td style="font-weight: 500; color: #f8fafc;">${escapeHtml(combo.track_id)}</td>
      <td>${layoutLabel}</td>
      <td style="color: #38bdf8; font-family: monospace;">${escapeHtml(combo.car_id)}</td>
      <td>${testTags}</td>
      <td>${statusBadge}</td>
    </tr>
  `;
}

/**
 * Update UI controls and summary text for missing telemetry data.
 */
export function updateMissingTelemetryUI(tier, data) {
  const missingCount = data.missing_tests_count || 0;
  const uniqueCombosCount = data.unique_combos_count || 0;

  if (dom.telemetrySummaryText) {
    dom.telemetrySummaryText.innerHTML =
      missingCount > 0
        ? `Found <strong style="color: #fbbf24;">${missingCount} rolling start tests</strong> across <strong style="color: #38bdf8;">${uniqueCombosCount} unique track+car combinations</strong> lacking telemetry profiles in <strong>${escapeHtml(tier)}</strong>.`
        : `<span style="color: #4ade80;">🏁 All rolling start tests in <strong>${escapeHtml(tier)}</strong> already have authentic telemetry recorded!</span>`;
  }

  if (dom.btnTelemetryEnqueue) {
    dom.btnTelemetryEnqueue.disabled = uniqueCombosCount === 0;
    dom.btnTelemetryEnqueue.innerHTML =
      uniqueCombosCount > 0
        ? `<span>▶ Run Telemetry for Missing Combos (${uniqueCombosCount} Jobs)</span>`
        : "<span>✓ All Telemetry Recorded</span>";
  }

  if (dom.telemetryQueueInfo) {
    dom.telemetryQueueInfo.textContent = `Total in scope: ${data.total_rolling_tests || 0} rolling tests`;
  }
}

/**
 * Fetch and render missing telemetry combinations table and summary.
 */
export async function loadMissingTelemetryData() {
  if (!dom.telemetryCombosTableBody) return;

  const tier = dom.selectTelemetryTier?.value || "ALL";
  const includeFlying = dom.checkIncludeFlying?.checked ?? true;

  if (dom.telemetrySummaryText) {
    dom.telemetrySummaryText.innerHTML =
      "⏳ Scanning curriculum tests for missing telemetry profiles...";
  }
  if (dom.btnTelemetryEnqueue) {
    dom.btnTelemetryEnqueue.disabled = true;
    dom.btnTelemetryEnqueue.innerHTML = "<span>⏳ Scanning...</span>";
  }

  try {
    const data = await api.getMissingTelemetry(tier, includeFlying);
    if (!data?.success) {
      if (dom.telemetrySummaryText) {
        dom.telemetrySummaryText.innerHTML = `<span style="color: #ef4444;">Error scanning tests: ${escapeHtml(data?.error || "Unknown error")}</span>`;
      }
      return;
    }

    updateMissingTelemetryUI(tier, data);

    const combos = data.all_combos || [];
    if (combos.length === 0) {
      dom.telemetryCombosTableBody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; color: #94a3b8; padding: 20px;">
            No rolling start tests found for the selected filter.
          </td>
        </tr>
      `;
      return;
    }

    dom.telemetryCombosTableBody.innerHTML = combos.map(renderTelemetryComboRow).join("");
  } catch (err) {
    if (dom.telemetrySummaryText) {
      dom.telemetrySummaryText.innerHTML = `<span style="color: #ef4444;">Failed to load telemetry status: ${escapeHtml(err.message)}</span>`;
    }
  }
}

/**
 * Execute batch enqueuing of missing telemetry recordings.
 */
export async function executeQueueMissingTelemetry() {
  const tier = dom.selectTelemetryTier?.value || "ALL";
  const includeFlying = dom.checkIncludeFlying?.checked ?? true;

  if (dom.btnTelemetryEnqueue) {
    dom.btnTelemetryEnqueue.disabled = true;
    dom.btnTelemetryEnqueue.innerHTML = "<span>⏳ Enqueuing recordings...</span>";
  }

  try {
    const res = await api.queueMissingTelemetry(tier, includeFlying);
    if (res?.success) {
      showToast(
        res.message || `Enqueued ${res.enqueued_count} telemetry recording session(s)!`,
        "success"
      );
      void pollQueueStatus();
      await loadMissingTelemetryData();
    } else {
      showToast(res?.error || "Failed to enqueue telemetry recordings", "error");
      if (dom.btnTelemetryEnqueue) dom.btnTelemetryEnqueue.disabled = false;
    }
  } catch (err) {
    showToast(`Error: ${err.message}`, "error");
    if (dom.btnTelemetryEnqueue) dom.btnTelemetryEnqueue.disabled = false;
  }
}
