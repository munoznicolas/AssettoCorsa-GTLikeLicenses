/**
 * queue-runner.js
 * Assetto Corsa simulation execution, queue management, live evaluation, and telemetry handover.
 */

import { state } from "./state.js";
import { dom } from "./dom.js";
import { api } from "./api.js";
import { showToast, openModal, escapeHtml } from "./ui-utils.js";
import { saveFormIntoActiveTest } from "./test-editor.js";

let pendingTelemetryJobId = null;
let pendingTelemetryTestId = null;
let queuePollTimer = null;

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

  const sourceLabel = data.source ? ` (${data.source})` : "";
  const dateStr = data.recorded_at
    ? ` • 📅 ${new Date(data.recorded_at).toISOString().replace("T", " ").substring(0, 16)} UTC`
    : "";
  showAISpeedStatus(
    `AI Telemetry Handover${sourceLabel}${dateStr}: ${data.speed_kmh} km/h | Gear ${data.gear || "Auto"} @ ${data.rpm || "Auto"} RPM | Run-up: ${data.spawn_offset_m}m`
  );
  if (isManualClick) {
    showToast(`Applied authentic ${data.speed_kmh} km/h from cached AI Telemetry!`, "success");
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
    const data = await api.calculateInitialSpeed({
      track_id: trackId,
      track_layout: trackLayout,
      car_id: carId,
      start_s: startS,
      start_mode: startMode,
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

/**
 * Handle completed background telemetry recording job.
 */
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
 * Periodically poll runner process queue and monitor background jobs.
 */
export async function pollQueueStatus() {
  try {
    const data = await api.getQueueStatus();
    if (data?.success) {
      updateQueueUI(data);
      await checkPendingTelemetryJob();
    }
  } catch (err) {
    console.debug("Queue poll error:", err);
  } finally {
    clearTimeout(queuePollTimer);
    queuePollTimer = setTimeout(pollQueueStatus, 2500);
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
  if (dom.runModalActiveBanner) {
    dom.runModalActiveBanner.style.display = isRunning ? "block" : "none";
  }
  if (isRunning && dom.runModalActiveDesc) {
    const title = data.active_job?.title || "Simulation Running";
    const pid = data.active_job?.pid ? ` (PID: ${data.active_job.pid})` : "";
    dom.runModalActiveDesc.textContent = `${title}${pid}`;
  }
}

/**
 * Render items in the queued simulation list.
 */
function renderQueueItems(queue) {
  if (!dom.runModalQueueList) return;
  dom.runModalQueueList.innerHTML = (queue || []).map((j, idx) => `
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background: rgba(255, 255, 255, 0.05); border-radius: 4px; font-size: 11px;">
      <div>
        <strong style="color: #38bdf8;">#${idx + 1}</strong> <span style="color: #cbd5e1;">${escapeHtml(j.title)}</span>
      </div>
      <button type="button" class="btn btn-sm btn-cancel-job" data-id="${j.id}" style="padding: 2px 6px; font-size: 10px; background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 3px; cursor: pointer;">Cancel</button>
    </div>
  `).join("");

  dom.runModalQueueList.querySelectorAll(".btn-cancel-job").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      const jid = (e.currentTarget || e.target)?.dataset?.id;
      if (jid) {
        await api.cancelQueueJob({ jobId: jid });
        showToast(`Cancelled job #${jid}`, "info");
        void pollQueueStatus();
      }
    });
  });
}

/**
 * Update UI for queued simulations count and list.
 */
function updateQueueListUI(data) {
  const qLen = data.queue_length || 0;
  if (dom.runQueueBadge) {
    dom.runQueueBadge.textContent = `${qLen} queued`;
    dom.runQueueBadge.style.display = qLen > 0 ? "inline-block" : "none";
  }
  if (dom.runModalQueueSection) {
    dom.runModalQueueSection.style.display = qLen > 0 ? "block" : "none";
  }
  if (dom.queueCountNum) {
    dom.queueCountNum.textContent = qLen;
  }
  if (qLen > 0) {
    renderQueueItems(data.queue);
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
}

/**
 * Hide AI speed handover status bar.
 */
export function hideAISpeedStatus() {
  if (dom.aiSpeedBadge) {
    dom.aiSpeedBadge.style.display = "none";
  }
}

/**
 * Open the Assetto Corsa live execution modal.
 */
export function openRunModal() {
  const test = getActiveTest();
  if (!test) {
    showToast("No active test selected.", "warning");
    return;
  }
  if (dom.runModalTitle) {
    dom.runModalTitle.textContent = `🏎️ Live Run: [${test.test_id}] ${test.title}`;
  }
  if (dom.runModalDesc) {
    dom.runModalDesc.innerHTML = `Launch <strong>${test.test_id}: ${escapeHtml(test.title)}</strong> (${test.car_id} at ${test.track_id}) directly into Assetto Corsa (<code style="color: #38bdf8;">acs.exe</code>).`;
  }
  if (dom.runModal) dom.runModal.style.display = "flex";
}

/**
 * Close the Assetto Corsa live execution modal.
 */
export function closeRunModal() {
  if (dom.runModal) dom.runModal.style.display = "none";
}

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
 * @param {"play"|"ai"|"eval"} mode
 */
export async function executeRunLiveTest(mode) {
  const test = getActiveTest();
  if (!test) {
    showToast("No active test selected.", "warning");
    return;
  }
  const syncFirst = dom.checkRunSync ? dom.checkRunSync.checked : true;

  // Save current form inputs into the in-memory test object
  saveFormIntoActiveTest();
  closeRunModal();

  if (mode === "eval") {
    openModal(
      `Automated In-Engine Evaluation: ${test.test_id}`,
      `Executing in-engine launch test for ${test.test_id} with 8s evaluation loop...\nMonitoring acs.exe process and checking physics/telemetry logs.`
    );
  } else {
    const modeLabel = mode === "ai" ? "AI Autopilot Demo" : "Driver Control";
    showToast(`Launching ${test.test_id} in Assetto Corsa (${modeLabel})...`, "info");
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
 * Attach listeners for run modal and queue controls.
 */
export function setupQueueEventListeners() {
  if (dom.btnRunLive) dom.btnRunLive.addEventListener("click", openRunModal);
  if (dom.btnRunTop) dom.btnRunTop.addEventListener("click", openRunModal);
  if (dom.runModalClose) dom.runModalClose.addEventListener("click", closeRunModal);
  if (dom.runModalCancel) dom.runModalCancel.addEventListener("click", closeRunModal);

  if (dom.btnRunModePlay) {
    dom.btnRunModePlay.addEventListener("click", () => {
      void executeRunLiveTest("play");
    });
  }
  if (dom.btnRunModeAi) {
    dom.btnRunModeAi.addEventListener("click", () => {
      void executeRunLiveTest("ai");
    });
  }
}
