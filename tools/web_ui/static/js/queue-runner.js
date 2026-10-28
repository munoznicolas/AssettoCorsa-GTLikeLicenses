/**
 * queue-runner.js
 * Assetto Corsa simulation execution, queue management, live evaluation, and telemetry handover.
 */

import { state } from "./state.js";
import { dom } from "./dom.js";
import { api, isStaticHost } from "./api.js";
import { showToast, openModal, escapeHtml } from "./ui-utils.js";
import { saveFormIntoActiveTest } from "./test-editor.js";
import { resolveTelemetryEngine } from "./telemetry-store.js";

let pendingTelemetryJobId = null;
let pendingTelemetryTestId = null;
let queuePollTimer = null;
let currentTelemetryData = null;

/**
 * Retrieve the active test object from state if present.
 */
function getActiveTest() {
  return state.curriculum[state.activeTierIndex]?.tests?.[state.activeTestIndex] ?? null;
}

/**
 * Determine start mode based on UI radio buttons.
 */
function getSelectedStartMode() {
  if (dom.radioStanding?.checked) return "STANDING";
  if (dom.radioRolling?.checked) return "ROLLING";
  return "FLYING_LAP";
}

/**
 * Reset test spawn parameters for standing start mode.
 */
function resetStandingMode(test) {
  if (!test) return;
  test.speed = 0.0;
  test.spawn_offset = 0.0;
  delete test.gear;
  delete test.rpm;
  if (test.spawn) {
    test.spawn.initial_speed_kmh = 0.0;
    test.spawn.spawn_offset_m = 0.0;
    delete test.spawn.initial_gear;
    delete test.spawn.initial_rpm;
  }
}

/**
 * Apply AI telemetry speed, gear, rpm, and offset data to a test object.
 */
function applySpeedDataToTest(test, data) {
  if (!test) return;
  test.speed = data.speed_kmh;
  test.spawn_offset = data.spawn_offset_m;
  if (data.gear !== undefined) test.gear = data.gear;
  if (data.rpm !== undefined) test.rpm = data.rpm;

  test.spawn = test.spawn || {};
  test.spawn.initial_speed_kmh = data.speed_kmh;
  test.spawn.spawn_offset_m = data.spawn_offset_m;
  if (data.gear !== undefined) test.spawn.initial_gear = data.gear;
  if (data.rpm !== undefined) test.spawn.initial_rpm = data.rpm;
}

/**
 * Set the auto-calculate speed button state.
 */
function setSpeedButtonLoading(isLoading) {
  if (!dom.btnCalcSpeed) return;
  dom.btnCalcSpeed.disabled = isLoading;
  dom.btnCalcSpeed.innerText = isLoading ? "⏳ Checking Cache..." : "⚡ Auto-Calculate from Game Engine";
}

/**
 * Handle cached AI speed calculation response.
 */
function handleCachedSpeedResult(data, isManualClick) {
  const test = getActiveTest();
  applySpeedDataToTest(test, data);

  if (data.targets) {
    if (dom.targetGold) dom.targetGold.value = Number(data.targets.gold_seconds).toFixed(3);
    if (dom.targetSilver) dom.targetSilver.value = Number(data.targets.silver_seconds).toFixed(3);
    if (dom.targetBronze) dom.targetBronze.value = Number(data.targets.bronze_seconds).toFixed(3);
    if (test) {
      test.targets = {
        gold_seconds: Number(data.targets.gold_seconds),
        silver_seconds: Number(data.targets.silver_seconds),
        bronze_seconds: Number(data.targets.bronze_seconds),
      };
    }
  }

  showAISpeedStatus(
    `AI Telemetry: ${data.speed_kmh} km/h | Gear ${data.gear || "Auto"} @ ${data.rpm || "Auto"} RPM | Run-up: ${data.spawn_offset_m}m`
  );
  if (isManualClick) {
    showToast(`Applied authentic ${data.speed_kmh} km/h and medal targets from cached AI Telemetry!`, "success");
  }
}

/**
 * Handle background queued AI speed recording job response.
 */
function handleQueuedSpeedJob(data) {
  pendingTelemetryJobId = data.job_id;
  pendingTelemetryTestId = getActiveTest()?.test_id ?? null;

  showAISpeedStatus(`⏳ Recording full lap in Assetto Corsa in background... (Queue Job #${data.job_id})`);
  showToast(
    `No cached profile found. Recording full lap in Assetto Corsa in background (Job #${data.job_id}). Form will auto-fill on completion.`,
    "info"
  );
  void pollQueueStatus();
}

/**
 * Fetch or calculate initial AI speed from cached profile or background hotlap.
 * @param {boolean} isManualClick
 */
export async function fetchAndApplyAISpeed(isManualClick = true) {
  const trackId = dom.selectTrack?.value || "";
  const trackLayout = dom.selectLayout?.value || "";
  const carId = dom.selectCar?.value || "";
  const startS = Number.parseFloat(dom.inputStart?.value || "0") || 0;
  const startMode = getSelectedStartMode();

  if (startMode === "STANDING") {
    resetStandingMode(getActiveTest());
    hideAISpeedStatus();
    return;
  }

  if (!trackId || !carId) {
    if (isManualClick) showToast("Please select a track and car first.", "warning");
    return;
  }

  setSpeedButtonLoading(true);

  try {
    const telRes = await resolveTelemetryEngine(trackId, trackLayout, carId);
    if (telRes) {
      const { engine, source } = telRes;
      const physics = engine.calculateGatePhysics(startS, 3.0);
      handleCachedSpeedResult({
        success: true,
        status: "cached",
        source,
        speed_kmh: physics.speed_kmh,
        spawn_offset_m: physics.spawn_offset_m,
        gear: physics.gear,
        rpm: physics.rpm,
        recorded_at: engine.recordedAt,
      }, isManualClick);
    } else {
      if (isManualClick) {
        showToast(`No telemetry profile found for ${carId} @ ${trackId}. Upload or record in AC.`, "warning");
      }
    }
  } catch (err) {
    if (isManualClick) showToast(`Calculation error: ${err.message}`, "error");
  } finally {
    setSpeedButtonLoading(false);
  }
}

/**
 * Handle completed background telemetry recording job.
 */
function handleCompletedTelemetryJob(job) {
  const curTest = getActiveTest();
  if (curTest && curTest.test_id === pendingTelemetryTestId && job.result) {
    applySpeedDataToTest(curTest, job.result);

    showAISpeedStatus(
      `AI Telemetry: ${job.result.speed_kmh} km/h | Gear ${job.result.gear || "Auto"} @ ${job.result.rpm || "Auto"} RPM | Run-up: ${job.result.spawn_offset_m}m`
    );
    showToast(
      `✨ 100% AI Telemetry recorded & applied to ${curTest.test_id}: ${job.result.speed_kmh} km/h (Gear ${job.result.gear})!`,
      "success"
    );
  }
  pendingTelemetryJobId = null;
  pendingTelemetryTestId = null;
}

/**
 * Check pending telemetry recording job if active.
 */
async function checkPendingTelemetryJob() {
  if (!pendingTelemetryJobId) return;

  const jData = await api.getJob(pendingTelemetryJobId);
  const job = jData?.success ? jData.job : null;
  if (!job) return;

  if (job.status === "completed") {
    handleCompletedTelemetryJob(job);
  } else if (job.status === "failed" || job.status === "cancelled") {
    showToast(`Telemetry recording ${job.status}: ${job.error || "Aborted"}`, "warning");
    hideAISpeedStatus();
    pendingTelemetryJobId = null;
    pendingTelemetryTestId = null;
  }
}

/**
 * Poll runner process queue and monitor background jobs.
 * Automatically backs off when queue and AC process are idle to eliminate polling spam.
 */
export async function pollQueueStatus() {
  clearTimeout(queuePollTimer);
  queuePollTimer = null;

  if (isStaticHost()) {
    return;
  }

  let isBusy = false;
  try {
    const data = await api.getQueueStatus();
    if (data?.success) {
      updateQueueUI(data);
      await checkPendingTelemetryJob();
      isBusy = Boolean(data.is_ac_running || (data.queue_length || 0) > 0 || pendingTelemetryJobId);
    }
  } catch (err) {
    console.debug("Queue poll error:", err);
  } finally {
    clearTimeout(queuePollTimer);
    if (isBusy) {
      // Actively poll while AC simulation is running or jobs are queued in background
      queuePollTimer = setTimeout(pollQueueStatus, 2500);
    } else {
      // Idle: do not poll continuously. Relaxed fallback heartbeat (60s)
      queuePollTimer = setTimeout(pollQueueStatus, 60000);
    }
  }
}

/**
 * Update UI for active Assetto Corsa simulation process.
 */
function updateAcProcessUI(data) {
  const isRunning = Boolean(data.is_ac_running);
  if (dom.btnStopAc) {
    dom.btnStopAc.style.display = isRunning ? "inline-flex" : "none";
  }
}

/**
 * Update UI for queued simulations count.
 */
function updateQueueListUI(data) {
  const qLen = data.queue_length || 0;
  if (dom.runQueueBadge) {
    dom.runQueueBadge.textContent = `${qLen} queued`;
    dom.runQueueBadge.style.display = qLen > 0 ? "inline-block" : "none";
  }
  if (dom.queueCountNum) {
    dom.queueCountNum.textContent = qLen;
  }
}

/**
 * Update UI elements to reflect AC running state and queued simulations.
 */
export function updateQueueUI(data) {
  updateAcProcessUI(data);
  updateQueueListUI(data);
}

/**
 * Terminate active simulation or clear queue.
 */
export async function cancelActiveACSession() {
  try {
    const data = await api.cancelQueueJob({ cancelAll: true });
    showToast(data.message || "Termination signal sent to Assetto Corsa", "info");
    void pollQueueStatus();
  } catch (err) {
    showToast("Error stopping AC: " + err.message, "error");
  }
}

/**
 * Display AI speed handover status bar.
 */
export function showAISpeedStatus(text) {
  if (dom.aiSpeedBadge && dom.aiSpeedText) {
    dom.aiSpeedText.innerText = text;
    dom.aiSpeedBadge.style.display = "block";
  }
  if (dom.btnExportSingleTelemetryScript) {
    dom.btnExportSingleTelemetryScript.style.display = "inline-flex";
  }
}

/**
 * Hide AI speed handover status bar.
 */
export function hideAISpeedStatus() {
  if (dom.aiSpeedBadge) {
    dom.aiSpeedBadge.style.display = "none";
  }
  if (dom.btnExportSingleTelemetryScript) {
    dom.btnExportSingleTelemetryScript.style.display = "none";
  }
}

/**
 * Direct launch of Assetto Corsa live session (AI Autopilot Demo).
 */
export function openRunModal() {
  void executeRunLiveTest("ai");
}

/**
 * Close modal shim for backwards compatibility.
 */
export function closeRunModal() {}

/**
 * Set modal status badge text, color, and log text during evaluation.
 */
function setModalEvalStatus(badgeText, color, logText) {
  if (dom.modalStatusBadge) {
    dom.modalStatusBadge.textContent = badgeText;
    dom.modalStatusBadge.style.color = color;
  }
  if (dom.modalLogText && logText !== undefined) {
    dom.modalLogText.textContent = logText;
  }
}

/**
 * Process job completion status for in-engine evaluation.
 * @returns {boolean} True if job is finished (completed, failed, cancelled)
 */
function handleEvalJobStatus(job) {
  if (job.status === "completed") {
    setModalEvalStatus("EVAL PASSED", "#10b981", job.result?.log || job.log || "Evaluation passed with zero errors.");
    void pollQueueStatus();
    return true;
  }
  if (job.status === "failed" || job.status === "cancelled") {
    setModalEvalStatus(`EVAL ${job.status.toUpperCase()}`, "#ef4444", job.result?.log || job.log || job.error || "Evaluation failed.");
    void pollQueueStatus();
    return true;
  }
  return false;
}

/**
 * Monitor background evaluation job until finished or timed out.
 */
function monitorEvalJob(evalJobId) {
  setModalEvalStatus("AUDITING (AC RUNNING)...", "#38bdf8", "Launching Assetto Corsa and monitoring in-engine evaluation loop...");
  if (dom.modalStatusBadge) dom.modalStatusBadge.className = "badge badge-lg";

  const startTime = Date.now();

  const pollEval = async () => {
    try {
      const jData = await api.getJob(evalJobId);
      const job = jData?.success ? jData.job : null;
      if (job && handleEvalJobStatus(job)) {
        return;
      }
    } catch (e) {
      console.debug("Eval poll error:", e);
    }

    if (Date.now() - startTime < 40000) {
      setTimeout(pollEval, 1000);
    } else if (dom.modalStatusBadge) {
      dom.modalStatusBadge.textContent = "TIMED OUT";
      dom.modalStatusBadge.style.color = "#ef4444";
    }
  };

  setTimeout(pollEval, 1200);
}

/**
 * Launch test session into AC with the specified execution mode.
 * @param {"ai"|"eval"} mode
 */
export async function executeRunLiveTest(mode = "ai") {
  const test = getActiveTest();
  if (!test) {
    showToast("No active test selected.", "warning");
    return;
  }
  const syncFirst = true;

  // Save current form inputs into the in-memory test object
  saveFormIntoActiveTest();

  if (mode === "eval") {
    openModal(
      `Automated In-Engine Evaluation: ${test.test_id}`,
      `Executing in-engine launch test for ${test.test_id} with 8s evaluation loop...\nMonitoring acs.exe process and checking physics/telemetry logs.`
    );
  } else {
    showToast(`Launching ${test.test_id} in Assetto Corsa (AI Autopilot Demo)...`, "info");
  }

  try {
    const data = await api.runLiveTest({
      test_id: test.test_id,
      mode: mode,
      sync_first: syncFirst,
      test_data: test,
      timeout: 8,
    });

    if (mode === "eval" && data.job_id) {
      monitorEvalJob(data.job_id);
    } else if (data.success) {
      showToast(data.message || `Test ${test.test_id} enqueued in Assetto Corsa!`, "success");
    } else {
      showToast(data.error || "Failed to launch Assetto Corsa", "error");
    }
    void pollQueueStatus();
  } catch (err) {
    if (mode === "eval") {
      setModalEvalStatus("NETWORK ERROR", "#ef4444", err.message);
    } else {
      showToast(`Launch error: ${err.message}`, "error");
    }
  }
}

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
    const opts = Array.from(dom.selectTelemetryTier.options).map(o => o.value);
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
function getTelemetryStatusBadge(combo) {
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
function renderTelemetryComboRow(combo, idx) {
  const statusBadge = getTelemetryStatusBadge(combo);
  const layoutLabel = combo.track_layout
    ? escapeHtml(combo.track_layout)
    : `<span style="color: #64748b; font-style: italic;">Default</span>`;

  const testTags = (combo.test_ids || []).map(id =>
    `<span class="tag-code" style="font-size: 10px; margin-right: 4px; padding: 1px 5px; background: rgba(255,255,255,0.08); border-radius: 3px;">${escapeHtml(id)}</span>`
  ).join("");

  return `
    <tr style="${combo.is_cached ? 'opacity: 0.6;' : ''}">
      <td style="font-weight: 500; color: #f8fafc;">${escapeHtml(combo.track_id)}</td>
      <td>${layoutLabel}</td>
      <td style="color: #38bdf8; font-family: monospace;">${escapeHtml(combo.car_id)}</td>
      <td>${testTags}</td>
      <td>${statusBadge}</td>
      <td style="text-align: right;">
        <button type="button" class="btn btn-xs btn-download-row-script" data-combo-idx="${idx}" title="Download PowerShell runner script for this specific combination" style="font-size: 11px; padding: 2px 6px; border: 1px solid rgba(56, 189, 248, 0.4); color: #38bdf8; background: transparent; border-radius: 4px; cursor: pointer;">
          Script
        </button>
      </td>
    </tr>
  `;
}

/**
 * Update UI controls and summary text for missing telemetry data.
 */
function updateMissingTelemetryUI(tier, data) {
  const missingCount = data.missing_tests_count || 0;
  const uniqueCombosCount = data.unique_combos_count || 0;

  if (dom.telemetrySummaryText) {
    dom.telemetrySummaryText.innerHTML = missingCount > 0
      ? `Found <strong style="color: #fbbf24;">${missingCount} rolling start tests</strong> across <strong style="color: #38bdf8;">${uniqueCombosCount} unique track+car combinations</strong> lacking telemetry profiles in <strong>${escapeHtml(tier)}</strong>.`
      : `<span style="color: #4ade80;">🏁 All rolling start tests in <strong>${escapeHtml(tier)}</strong> already have authentic telemetry recorded!</span>`;
  }

  if (dom.btnTelemetryEnqueue) {
    if (isStaticHost()) {
      dom.btnTelemetryEnqueue.style.display = "none";
    } else {
      dom.btnTelemetryEnqueue.disabled = uniqueCombosCount === 0;
      dom.btnTelemetryEnqueue.innerHTML = uniqueCombosCount > 0
        ? `<span>▶ Run Telemetry for Missing Combos (${uniqueCombosCount} Jobs)</span>`
        : "<span>✓ All Telemetry Recorded</span>";
    }
  }

  if (dom.telemetryQueueInfo) {
    dom.telemetryQueueInfo.textContent = `Total in scope: ${data.total_rolling_tests || 0} rolling tests`;
  }

  if (dom.btnTelemetryExportScript) {
    const totalCombos = (data.all_combos || []).length;
    dom.btnTelemetryExportScript.disabled = totalCombos === 0;
    dom.btnTelemetryExportScript.innerHTML = uniqueCombosCount > 0
      ? `<span>Download Script for Missing (${uniqueCombosCount} Jobs)</span>`
      : `<span>Download Recording Script (${totalCombos} Jobs)</span>`;
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
    dom.telemetrySummaryText.innerHTML = "⏳ Scanning curriculum tests for missing telemetry profiles...";
  }
  if (dom.btnTelemetryEnqueue) {
    if (isStaticHost()) {
      dom.btnTelemetryEnqueue.style.display = "none";
    } else {
      dom.btnTelemetryEnqueue.disabled = true;
      dom.btnTelemetryEnqueue.innerHTML = "<span>⏳ Scanning...</span>";
    }
  }

  try {
    const data = await api.getMissingTelemetry(tier, includeFlying);
    if (!data?.success) {
      if (dom.telemetrySummaryText) {
        dom.telemetrySummaryText.innerHTML = `<span style="color: #ef4444;">Error scanning tests: ${escapeHtml(data?.error || "Unknown error")}</span>`;
      }
      return;
    }

    currentTelemetryData = data;
    updateMissingTelemetryUI(tier, data);

    const combos = data.all_combos || [];
    if (combos.length === 0) {
      dom.telemetryCombosTableBody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align: center; color: #94a3b8; padding: 20px;">
            No rolling start tests found for the selected filter.
          </td>
        </tr>
      `;
      return;
    }

    dom.telemetryCombosTableBody.innerHTML = combos.map((c, i) => renderTelemetryComboRow(c, i)).join("");

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
      showToast(res.message || `Enqueued ${res.enqueued_count} telemetry recording session(s)!`, "success");
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

/**
 * Attach listeners for run modal and queue controls.
 */
/**
 * Generates an automated PowerShell script to record telemetry locally in Assetto Corsa.
 * @param {Array<{track_id: string, track_layout?: string, car_id: string}>} combos
 * @param {Object} [options]
 * @returns {string}
 */
export function generatePowerShellRecordingScript(combos, options = {}) {
  const aiLevel = options.aiLevel || 100;
  const defaultAcRoot = "D:\\SteamLibrary\\steamapps\\common\\assettocorsa";

  const jobsPsArray = combos.map(c => {
    const track = c.track_id || "";
    const layout = c.track_layout || "";
    const car = c.car_id || "";
    return `    @{ Track = "${track}"; Layout = "${layout}"; Car = "${car}" }`;
  }).join(",\n");

  return `<#
================================================================================
 Assetto Corsa GT Licenses - Local AI Telemetry Recorder
 Generated by Assetto Corsa GT License Test Designer
 Target Combinations: ${combos.length}
================================================================================
#>

[CmdletBinding()]
param(
    [string]$AcRoot = "${defaultAcRoot}",
    [int]$AiLevel = ${aiLevel},
    [switch]$SplineFallback
)

$ErrorActionPreference = "Stop"

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host " Assetto Corsa GT Licenses - Automated AI Telemetry Recorder" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

# 1. Verify Python availability
try {
    $pythonVer = python --version 2>&1
    Write-Host "[✓] Python detected: $pythonVer" -ForegroundColor Green
} catch {
    Write-Error "Python was not found in PATH. Please install Python 3.8+ to record telemetry."
}

# 2. Locate Assetto Corsa root
if (-not (Test-Path "$AcRoot\\acs.exe")) {
    $candidates = @(
        "C:\\Program Files (x86)\\Steam\\steamapps\\common\\assettocorsa",
        "D:\\SteamLibrary\\steamapps\\common\\assettocorsa",
        "E:\\SteamLibrary\\steamapps\\common\\assettocorsa"
    )
    foreach ($cand in $candidates) {
        if (Test-Path "$cand\\acs.exe") {
            $AcRoot = $cand
            break
        }
    }
}

if (-not (Test-Path "$AcRoot\\acs.exe")) {
    Write-Host "[!] Assetto Corsa not found at: $AcRoot" -ForegroundColor Yellow
    $AcRoot = Read-Host "Please enter the absolute path to your Assetto Corsa directory"
    if (-not (Test-Path "$AcRoot\\acs.exe")) {
        Write-Error "Assetto Corsa executable (acs.exe) not found at '$AcRoot'."
    }
}
Write-Host "[✓] Assetto Corsa Directory: $AcRoot" -ForegroundColor Green

# 3. Target Combinations
$Jobs = @(
${jobsPsArray}
)

Write-Host "\`nReady to record $($Jobs.Count) combination(s) with AI Level $AiLevel%." -ForegroundColor Yellow
Write-Host "Each session will launch AC, allow the AI to complete a clean flying lap, and record 60Hz physics.\`n" -ForegroundColor Gray

$completed = 0
$failed = 0

foreach ($job in $Jobs) {
    $idx = $completed + $failed + 1
    Write-Host "[$idx/$($Jobs.Count)] Recording: $($job.Car) @ $($job.Track) $($job.Layout)" -ForegroundColor Magenta

    $cmdArgs = @(
        "tools/record_ai_telemetry.py",
        "--track", $job.Track,
        "--car", $job.Car,
        "--ai-level", $AiLevel,
        "--ac-root", $AcRoot
    )

    if ($job.Layout -and $job.Layout.Trim() -ne "") {
        $cmdArgs += @("--layout", $job.Layout)
    }

    if (-not $SplineFallback) {
        $cmdArgs += @("--live")
    }

    try {
        & python @cmdArgs
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[✓] Successfully recorded telemetry for $($job.Car) @ $($job.Track)!" -ForegroundColor Green
            $completed++
        } else {
            Write-Host "[!] Warning: telemetry recording returned exit code $LASTEXITCODE" -ForegroundColor Red
            $failed++
        }
    } catch {
        Write-Host "[!] Error recording job: $_" -ForegroundColor Red
        $failed++
    }
}

Write-Host "\`n==================================================================" -ForegroundColor Cyan
Write-Host " Completed: $completed / $($Jobs.Count) (Failed/Skipped: $failed)" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Yellow" })
Write-Host " Recorded profiles saved to: data/telemetry_profiles/" -ForegroundColor Cyan
Write-Host " You can now commit and push the new profiles back to your repository!" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Cyan
`;
}

/**
 * Triggers a browser file download for a text blob.
 * @param {string} filename
 * @param {string} content
 */
export function triggerScriptDownload(filename, content) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Export a PowerShell script for all missing or filtered telemetry combinations.
 */
export function executeExportMissingTelemetryScript() {
  const tier = dom.selectTelemetryTier?.value || "ALL";
  const missing = currentTelemetryData?.unique_missing_combos || [];
  const combosToExport = missing.length > 0 ? missing : (currentTelemetryData?.all_combos || []);

  if (combosToExport.length === 0) {
    showToast("No combinations available to export", "warning");
    return;
  }

  const safeTier = tier.toLowerCase().replace(/\s+/g, "_");
  const filename = `record_telemetry_${safeTier}.ps1`;
  const scriptContent = generatePowerShellRecordingScript(combosToExport, {
    aiLevel: 100
  });

  triggerScriptDownload(filename, scriptContent);
  showToast(`Downloaded ${filename} (${combosToExport.length} jobs)!`, "success");
}

/**
 * Export a PowerShell script for the single active test currently in the editor.
 */
export function executeExportSingleTelemetryScript() {
  const test = getActiveTest();
  if (!test) {
    showToast("No active test selected", "warning");
    return;
  }

  const combo = [{
    track_id: test.track_id,
    track_layout: test.track_layout || "",
    car_id: test.car_id
  }];

  const testId = (test.test_id || "test").toLowerCase().replace(/[^a-z0-9_-]/g, "_");
  const filename = `record_telemetry_${testId}.ps1`;
  const scriptContent = generatePowerShellRecordingScript(combo, { aiLevel: 100 });

  triggerScriptDownload(filename, scriptContent);
  showToast(`Downloaded telemetry script for ${test.car_id} @ ${test.track_id}!`, "success");
}

export function setupQueueEventListeners() {
  if (dom.btnRunLive) {
    if (isStaticHost()) {
      dom.btnRunLive.style.display = "none";
    } else {
      dom.btnRunLive.addEventListener("click", () => {
        void executeRunLiveTest("ai");
      });
    }
  }
  if (dom.btnRunTop) {
    dom.btnRunTop.addEventListener("click", () => {
      void executeRunLiveTest("ai");
    });
  }

  // Missing Telemetry Batch Controls
  if (dom.btnRunMissingTelemetry) {
    if (isStaticHost()) {
      dom.btnRunMissingTelemetry.style.display = "none";
    } else {
      dom.btnRunMissingTelemetry.addEventListener("click", openMissingTelemetryModal);
    }
  }
  if (dom.telemetryModalClose) dom.telemetryModalClose.addEventListener("click", closeMissingTelemetryModal);
  if (dom.btnTelemetryCancel) dom.btnTelemetryCancel.addEventListener("click", closeMissingTelemetryModal);
  if (dom.selectTelemetryTier) dom.selectTelemetryTier.addEventListener("change", () => {
    void loadMissingTelemetryData();
  });
  if (dom.checkIncludeFlying) dom.checkIncludeFlying.addEventListener("change", () => {
    void loadMissingTelemetryData();
  });
  if (dom.btnTelemetryEnqueue) dom.btnTelemetryEnqueue.addEventListener("click", () => {
    void executeQueueMissingTelemetry();
  });
  if (dom.btnTelemetryExportScript) {
    dom.btnTelemetryExportScript.addEventListener("click", executeExportMissingTelemetryScript);
  }
  if (dom.btnExportSingleTelemetryScript) {
    dom.btnExportSingleTelemetryScript.addEventListener("click", executeExportSingleTelemetryScript);
  }

  // Delegated click listener for per-row script download
  if (dom.telemetryCombosTableBody) {
    dom.telemetryCombosTableBody.addEventListener("click", (e) => {
      const btn = e.target.closest(".btn-download-row-script");
      if (!btn) return;
      const idx = parseInt(btn.getAttribute("data-combo-idx"), 10);
      const combo = currentTelemetryData?.all_combos?.[idx];
      if (!combo) return;

      const filename = `record_${combo.track_id}_${combo.car_id}.ps1`;
      const scriptContent = generatePowerShellRecordingScript([combo], { aiLevel: 100 });
      triggerScriptDownload(filename, scriptContent);
      showToast(`Downloaded ${filename}!`, "success");
    });
  }

  // Refresh queue status immediately when user switches back to this browser tab
  if (!isStaticHost()) {
    window.addEventListener("focus", () => void pollQueueStatus());
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") {
        void pollQueueStatus();
      }
    });
  }
}
