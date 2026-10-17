/**
 * queue-runner.js
 * Assetto Corsa simulation execution, queue management, live evaluation, and telemetry handover.
 */

import { state } from "./state.js";
import { dom } from "./dom.js";
import { api } from "./api.js";
import { showToast, openModal } from "./ui-utils.js";
import { saveFormIntoActiveTest } from "./test-editor.js";
import {
  openMissingTelemetryModal,
  closeMissingTelemetryModal,
  loadMissingTelemetryData,
  executeQueueMissingTelemetry,
} from "./queue/telemetry-modal.js";

export {
  openMissingTelemetryModal,
  closeMissingTelemetryModal,
  getTelemetryStatusBadge,
  renderTelemetryComboRow,
  updateMissingTelemetryUI,
  loadMissingTelemetryData,
  executeQueueMissingTelemetry,
} from "./queue/telemetry-modal.js";

let pendingTelemetryJobId = null;
let pendingTelemetryTestId = null;
let queuePollTimer = null;

function getActiveTest() {
  return state.curriculum[state.activeTierIndex]?.tests?.[state.activeTestIndex] ?? null;
}

function getSelectedStartMode() {
  if (dom.radioStanding?.checked) return "STANDING";
  if (dom.radioRolling?.checked) return "ROLLING";
  return "FLYING_LAP";
}

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

function setSpeedButtonLoading(isLoading) {
  if (!dom.btnCalcSpeed) return;
  dom.btnCalcSpeed.disabled = isLoading;
  dom.btnCalcSpeed.innerText = isLoading ? "⏳ Checking Cache..." : "⚡ Auto-Calculate from Game Engine";
}

function handleCachedSpeedResult(data, isManualClick) {
  const test = getActiveTest();
  applySpeedDataToTest(test, data);

  if (data.targets) {
    if (dom.targetGold) dom.targetGold.value = Number(data.targets.gold_seconds).toFixed(1);
    if (dom.targetSilver) dom.targetSilver.value = Number(data.targets.silver_seconds).toFixed(1);
    if (dom.targetBronze) dom.targetBronze.value = Number(data.targets.bronze_seconds).toFixed(1);
    if (test) {
      test.targets = {
        gold_seconds: Number(data.targets.gold_seconds),
        silver_seconds: Number(data.targets.silver_seconds),
        bronze_seconds: Number(data.targets.bronze_seconds),
      };
    }
  }

  const sourceLabel = data.source ? ` (${data.source})` : "";
  const dateStr = data.recorded_at
    ? ` • 📅 ${new Date(data.recorded_at).toISOString().replace("T", " ").substring(0, 16)} UTC`
    : "";
  const targetsStr = data.targets ? ` | Gold: ${data.targets.gold_seconds}s` : "";
  showAISpeedStatus(
    `AI Telemetry Handover${sourceLabel}${dateStr}: ${data.speed_kmh} km/h | Gear ${data.gear || "Auto"} @ ${data.rpm || "Auto"} RPM | Run-up: ${data.spawn_offset_m}m${targetsStr}`
  );
  if (isManualClick) {
    showToast(`Applied authentic ${data.speed_kmh} km/h and medal targets from cached AI Telemetry!`, "success");
  }
}

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
    const data = await api.calculateInitialSpeed({
      track_id: trackId,
      track_layout: trackLayout,
      car_id: carId,
      start_s: startS,
      finish_s: Number.parseFloat(dom.inputFinish?.value || "1") || 1,
      start_mode: startMode,
      with_stop_box: dom.checkStopBox?.checked || false,
      countdown_sec: 3.0,
    });

    if (!data.success) {
      if (isManualClick) showToast(data.error || "Failed to calculate AI speed", "error");
    } else if (data.status === "cached") {
      handleCachedSpeedResult(data, isManualClick);
    } else if (data.status === "queued") {
      handleQueuedSpeedJob(data);
    }
  } catch (err) {
    if (isManualClick) showToast(`Calculation error: ${err.message}`, "error");
  } finally {
    setSpeedButtonLoading(false);
  }
}

function handleCompletedTelemetryJob(job) {
  const curTest = getActiveTest();
  if (curTest && curTest.test_id === pendingTelemetryTestId && job.result) {
    applySpeedDataToTest(curTest, job.result);

    const dateStr = job.result.recorded_at
      ? ` • 📅 ${new Date(job.result.recorded_at).toISOString().replace("T", " ").substring(0, 16)} UTC`
      : "";
    showAISpeedStatus(
      `AI Telemetry Handover (live in-engine)${dateStr}: ${job.result.speed_kmh} km/h | Gear ${job.result.gear || "Auto"} @ ${job.result.rpm || "Auto"} RPM | Run-up: ${job.result.spawn_offset_m}m`
    );
    showToast(
      `✨ 100% AI Telemetry recorded & applied to ${curTest.test_id}: ${job.result.speed_kmh} km/h (Gear ${job.result.gear})!`,
      "success"
    );
  }
  pendingTelemetryJobId = null;
  pendingTelemetryTestId = null;
}

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
 */
export async function pollQueueStatus() {
  clearTimeout(queuePollTimer);
  queuePollTimer = null;

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
    queuePollTimer = setTimeout(pollQueueStatus, isBusy ? 2500 : 60000);
  }
}

function updateAcProcessUI(data) {
  const isRunning = Boolean(data.is_ac_running);
  if (dom.btnStopAc) {
    dom.btnStopAc.style.display = isRunning ? "inline-flex" : "none";
  }
}

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

export function updateQueueUI(data) {
  updateAcProcessUI(data);
  updateQueueListUI(data);
}

export async function cancelActiveACSession() {
  try {
    const data = await api.cancelQueueJob({ cancelAll: true });
    showToast(data.message || "Termination signal sent to Assetto Corsa", "info");
    void pollQueueStatus();
  } catch (err) {
    showToast("Error stopping AC: " + err.message, "error");
  }
}

export function showAISpeedStatus(text) {
  if (dom.aiSpeedBadge && dom.aiSpeedText) {
    dom.aiSpeedText.innerText = text;
    dom.aiSpeedBadge.style.display = "block";
  }
}

export function hideAISpeedStatus() {
  if (dom.aiSpeedBadge) {
    dom.aiSpeedBadge.style.display = "none";
  }
}

export function openRunModal() {
  void executeRunLiveTest("ai");
}

export function closeRunModal() {}

function setModalEvalStatus(badgeText, color, logText) {
  if (dom.modalStatusBadge) {
    dom.modalStatusBadge.textContent = badgeText;
    dom.modalStatusBadge.style.color = color;
  }
  if (dom.modalLogText && logText !== undefined) {
    dom.modalLogText.textContent = logText;
  }
}

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

function monitorEvalJob(evalJobId) {
  setModalEvalStatus("AUDITING (AC RUNNING)...", "#38bdf8", "Launching Assetto Corsa and monitoring in-engine evaluation loop...");
  if (dom.modalStatusBadge) dom.modalStatusBadge.className = "badge badge-lg";

  const startTime = Date.now();
  const pollEval = async () => {
    try {
      const jData = await api.getJob(evalJobId);
      const job = jData?.success ? jData.job : null;
      if (job && handleEvalJobStatus(job)) return;
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
      sync_first: true,
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

export function setupQueueEventListeners() {
  dom.btnRunLive?.addEventListener("click", () => void executeRunLiveTest("ai"));
  dom.btnRunTop?.addEventListener("click", () => void executeRunLiveTest("ai"));

  dom.btnRunMissingTelemetry?.addEventListener("click", openMissingTelemetryModal);
  dom.telemetryModalClose?.addEventListener("click", closeMissingTelemetryModal);
  dom.btnTelemetryCancel?.addEventListener("click", closeMissingTelemetryModal);
  dom.selectTelemetryTier?.addEventListener("change", () => void loadMissingTelemetryData());
  dom.checkIncludeFlying?.addEventListener("change", () => void loadMissingTelemetryData());
  dom.btnTelemetryEnqueue?.addEventListener("click", () => void executeQueueMissingTelemetry());

  window.addEventListener("focus", () => void pollQueueStatus());
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") void pollQueueStatus();
  });
}
