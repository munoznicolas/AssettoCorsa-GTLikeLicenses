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
 * Fetch or calculate initial AI speed from cached profile or background hotlap.
 * @param {boolean} isManualClick
 */
export async function fetchAndApplyAISpeed(isManualClick = true) {
  const trackId = dom.selectTrack ? dom.selectTrack.value : "";
  const trackLayout = dom.selectLayout ? dom.selectLayout.value : "";
  const carId = dom.selectCar ? dom.selectCar.value : "";
  const startS = parseFloat(dom.inputStart ? dom.inputStart.value : 0) || 0;
  const startMode = (dom.radioStanding && dom.radioStanding.checked)
    ? "STANDING"
    : (dom.radioRolling && dom.radioRolling.checked)
    ? "ROLLING"
    : "FLYING_LAP";

  if (startMode === "STANDING") {
    if (dom.inputSpeed) dom.inputSpeed.value = 0;
    if (dom.inputSpawnOffset) dom.inputSpawnOffset.value = 0;
    if (dom.inputGear) dom.inputGear.value = 1;
    if (dom.inputRpm) dom.inputRpm.value = 1000;
    hideAISpeedStatus();
    return;
  }

  if (!trackId || !carId) {
    if (isManualClick) showToast("Please select a track and car first.", "warning");
    return;
  }

  if (dom.btnCalcSpeed) {
    dom.btnCalcSpeed.disabled = true;
    dom.btnCalcSpeed.innerText = "⏳ Checking Cache...";
  }

  try {
    const data = await api.calculateInitialSpeed({
      track_id: trackId,
      track_layout: trackLayout,
      car_id: carId,
      start_s: startS,
      start_mode: startMode,
      countdown_sec: 3.0,
    });

    if (data.success) {
      if (data.status === "cached") {
        if (dom.inputSpeed) dom.inputSpeed.value = data.speed_kmh;
        if (dom.inputSpawnOffset) dom.inputSpawnOffset.value = data.spawn_offset_m;
        if (dom.inputGear) dom.inputGear.value = data.gear !== undefined ? data.gear : "";
        if (dom.inputRpm) dom.inputRpm.value = data.rpm !== undefined ? data.rpm : "";

        const activeTier = state.curriculum[state.activeTierIndex];
        if (activeTier && activeTier.tests && activeTier.tests[state.activeTestIndex]) {
          const test = activeTier.tests[state.activeTestIndex];
          test.spawn = test.spawn || {};
          test.spawn.initial_speed_kmh = data.speed_kmh;
          test.spawn.spawn_offset_m = data.spawn_offset_m;
          test.spawn.initial_gear = data.gear;
          test.spawn.initial_rpm = data.rpm;
        }

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
      } else if (data.status === "queued") {
        pendingTelemetryJobId = data.job_id;
        const activeTier = state.curriculum[state.activeTierIndex];
        pendingTelemetryTestId = (activeTier && activeTier.tests && activeTier.tests[state.activeTestIndex])
          ? activeTier.tests[state.activeTestIndex].test_id
          : null;

        showAISpeedStatus(`⏳ Recording full lap in Assetto Corsa in background... (Queue Job #${data.job_id})`);
        showToast(
          `No cached profile found. Recording full lap in Assetto Corsa in background (Job #${data.job_id}). Form will auto-fill on completion.`,
          "info"
        );
        pollQueueStatus();
      }
    } else {
      if (isManualClick) showToast(data.error || "Failed to calculate AI speed", "error");
    }
  } catch (err) {
    if (isManualClick) showToast(`Calculation error: ${err.message}`, "error");
  } finally {
    if (dom.btnCalcSpeed) {
      dom.btnCalcSpeed.disabled = false;
      dom.btnCalcSpeed.innerText = "⚡ Auto-Calculate from Game Engine";
    }
  }
}

/**
 * Periodically poll runner process queue and monitor background jobs.
 */
export async function pollQueueStatus() {
  try {
    const data = await api.getQueueStatus();
    if (!data || !data.success) return;

    updateQueueUI(data);

    // Check pending telemetry recording job
    if (pendingTelemetryJobId) {
      const jData = await api.getJob(pendingTelemetryJobId);
      if (jData && jData.success && jData.job) {
        const job = jData.job;
        if (job.status === "completed") {
          const activeTier = state.curriculum[state.activeTierIndex];
          const curTest = (activeTier && activeTier.tests && activeTier.tests[state.activeTestIndex])
            ? activeTier.tests[state.activeTestIndex]
            : null;

          if (curTest && curTest.test_id === pendingTelemetryTestId && job.result) {
            if (dom.inputSpeed) dom.inputSpeed.value = job.result.speed_kmh;
            if (dom.inputSpawnOffset) dom.inputSpawnOffset.value = job.result.spawn_offset_m;
            if (dom.inputGear) dom.inputGear.value = job.result.gear !== undefined ? job.result.gear : "";
            if (dom.inputRpm) dom.inputRpm.value = job.result.rpm !== undefined ? job.result.rpm : "";

            curTest.spawn = curTest.spawn || {};
            curTest.spawn.initial_speed_kmh = job.result.speed_kmh;
            curTest.spawn.spawn_offset_m = job.result.spawn_offset_m;
            curTest.spawn.initial_gear = job.result.gear;
            curTest.spawn.initial_rpm = job.result.rpm;

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
        } else if (job.status === "failed" || job.status === "cancelled") {
          showToast(`Telemetry recording ${job.status}: ${job.error || 'Aborted'}`, "warning");
          hideAISpeedStatus();
          pendingTelemetryJobId = null;
          pendingTelemetryTestId = null;
        }
      }
    }
  } catch (err) {
    console.debug("Queue poll error:", err);
  } finally {
    clearTimeout(queuePollTimer);
    queuePollTimer = setTimeout(pollQueueStatus, 2500);
  }
}

/**
 * Update UI elements to reflect AC running state and queued simulations.
 */
export function updateQueueUI(data) {
  // 1. Is AC Process Running?
  if (data.is_ac_running) {
    if (dom.btnStopAc) dom.btnStopAc.style.display = "inline-flex";
    if (dom.runModalActiveBanner) {
      dom.runModalActiveBanner.style.display = "block";
      const title = data.active_job ? data.active_job.title : "Simulation Running";
      const pid = (data.active_job && data.active_job.pid) ? ` (PID: ${data.active_job.pid})` : "";
      if (dom.runModalActiveDesc) dom.runModalActiveDesc.textContent = `${title}${pid}`;
    }
  } else {
    if (dom.btnStopAc) dom.btnStopAc.style.display = "none";
    if (dom.runModalActiveBanner) dom.runModalActiveBanner.style.display = "none";
  }

  // 2. Queued runs count & listing
  const qLen = data.queue_length || 0;
  if (qLen > 0) {
    if (dom.runQueueBadge) {
      dom.runQueueBadge.textContent = `${qLen} queued`;
      dom.runQueueBadge.style.display = "inline-block";
    }
    if (dom.runModalQueueSection) dom.runModalQueueSection.style.display = "block";
    if (dom.queueCountNum) dom.queueCountNum.textContent = qLen;
    if (dom.runModalQueueList) {
      dom.runModalQueueList.innerHTML = (data.queue || []).map((j, idx) => `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background: rgba(255, 255, 255, 0.05); border-radius: 4px; font-size: 11px;">
          <div>
            <strong style="color: #38bdf8;">#${idx + 1}</strong> <span style="color: #cbd5e1;">${escapeHtml(j.title)}</span>
          </div>
          <button type="button" class="btn btn-sm btn-cancel-job" data-id="${j.id}" style="padding: 2px 6px; font-size: 10px; background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 3px; cursor: pointer;">Cancel</button>
        </div>
      `).join("");

      dom.runModalQueueList.querySelectorAll(".btn-cancel-job").forEach(btn => {
        btn.addEventListener("click", async (e) => {
          const jid = e.target.getAttribute("data-id");
          if (jid) {
            await api.cancelQueueJob({ jobId: jid });
            showToast(`Cancelled job #${jid}`, "info");
            pollQueueStatus();
          }
        });
      });
    }
  } else {
    if (dom.runQueueBadge) dom.runQueueBadge.style.display = "none";
    if (dom.runModalQueueSection) dom.runModalQueueSection.style.display = "none";
  }
}

/**
 * Terminate active simulation or clear queue.
 */
export async function cancelActiveACSession() {
  try {
    const data = await api.cancelQueueJob({ cancelAll: true });
    showToast(data.message || "Termination signal sent to Assetto Corsa", "info");
    pollQueueStatus();
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
  const activeTier = state.curriculum[state.activeTierIndex];
  if (!activeTier || !activeTier.tests || !activeTier.tests[state.activeTestIndex]) {
    showToast("No active test selected.", "warning");
    return;
  }
  const test = activeTier.tests[state.activeTestIndex];
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
 * Launch test session into AC with the specified execution mode.
 * @param {"play"|"ai"|"eval"} mode
 */
export async function executeRunLiveTest(mode) {
  const activeTier = state.curriculum[state.activeTierIndex];
  if (!activeTier || !activeTier.tests || !activeTier.tests[state.activeTestIndex]) {
    showToast("No active test selected.", "warning");
    return;
  }
  const test = activeTier.tests[state.activeTestIndex];
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
      if (dom.modalStatusBadge) {
        dom.modalStatusBadge.textContent = "AUDITING (AC RUNNING)...";
        dom.modalStatusBadge.className = "badge badge-lg";
        dom.modalStatusBadge.style.color = "#38bdf8";
      }
      if (dom.modalLogText) {
        dom.modalLogText.textContent = "Launching Assetto Corsa and monitoring in-engine evaluation loop...";
      }

      const evalJobId = data.job_id;
      const startTime = Date.now();
      const pollEval = async () => {
        try {
          const jData = await api.getJob(evalJobId);
          if (jData && jData.success && jData.job) {
            const j = jData.job;
            if (j.status === "completed") {
              if (dom.modalStatusBadge) {
                dom.modalStatusBadge.textContent = "EVAL PASSED";
                dom.modalStatusBadge.style.color = "#10b981";
              }
              if (dom.modalLogText) {
                dom.modalLogText.textContent = (j.result && j.result.log) || j.log || "Evaluation passed with zero errors.";
              }
              pollQueueStatus();
              return;
            } else if (j.status === "failed" || j.status === "cancelled") {
              if (dom.modalStatusBadge) {
                dom.modalStatusBadge.textContent = `EVAL ${j.status.toUpperCase()}`;
                dom.modalStatusBadge.style.color = "#ef4444";
              }
              if (dom.modalLogText) {
                dom.modalLogText.textContent = (j.result && j.result.log) || j.log || j.error || "Evaluation failed.";
              }
              pollQueueStatus();
              return;
            }
          }
        } catch (e) {
          console.debug("Eval poll error:", e);
        }
        if (Date.now() - startTime < 40000) {
          setTimeout(pollEval, 1000);
        } else {
          if (dom.modalStatusBadge) {
            dom.modalStatusBadge.textContent = "TIMED OUT";
            dom.modalStatusBadge.style.color = "#ef4444";
          }
        }
      };
      setTimeout(pollEval, 1200);
    } else {
      if (data.success) {
        showToast(data.message || `Test ${test.test_id} enqueued in Assetto Corsa!`, "success");
      } else {
        showToast(data.error || "Failed to launch Assetto Corsa", "error");
      }
    }
    pollQueueStatus();
  } catch (err) {
    if (mode === "eval") {
      if (dom.modalStatusBadge) dom.modalStatusBadge.textContent = "NETWORK ERROR";
      if (dom.modalLogText) dom.modalLogText.textContent = err.message;
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
    dom.btnRunModePlay.addEventListener("click", () => executeRunLiveTest("play"));
  }
  if (dom.btnRunModeAi) {
    dom.btnRunModeAi.addEventListener("click", () => executeRunLiveTest("ai"));
  }
  if (dom.btnRunModeEval) {
    dom.btnRunModeEval.addEventListener("click", () => executeRunLiveTest("eval"));
  }
}

