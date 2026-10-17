/**
 * test-editor.js
 * Test definition editor, form validation, license tabs, and curriculum catalog manager.
 */

import { state } from "./state.js";
import { dom } from "./dom.js";
import { api } from "./api.js";
import { showToast } from "./ui-utils.js";
import { fetchAndRenderSpline, renderCanvasTrack, drawEmptyCanvas } from "./track-canvas.js";
import { showAISpeedStatus, hideAISpeedStatus } from "./queue-runner.js";
import {
  populateTrackDropdown,
  populateLayoutDropdown,
  populateCarDropdown,
} from "./editor/dropdowns.js";
import { renderLicenseTabs, selectTier } from "./editor/sidebar.js";

export {
  filterTracks,
  updateFilterIndicator,
  populateTrackDropdown,
  populateLayoutDropdown,
  matchesAwd,
  matchesDrivetrainToken,
  matchesCarToken,
  filterCars,
  populateCarDropdown,
} from "./editor/dropdowns.js";
export {
  renderLicenseTabs,
  selectTier,
  renderTestList,
  saveDraggedTestOrder,
  renumberTierTests,
  setupTestListDragListeners,
} from "./editor/sidebar.js";
export {
  handleAddTest,
  handleDeleteTest,
  handleTrackSearchKeydown,
  handleCarSearchKeydown,
  handleCardStandingClick,
  handleCardRollingClick,
  handleCardFlyingClick,
  handleFormSubmit,
  setupSearchFilterListeners,
  setupDropdownChangeListeners,
  setupPositionControlListeners,
  setupStartModeListeners,
  setupEditorEventListeners,
} from "./editor/events.js";

let autoCalculateTargetsTimer = null;

function updateTestAISpeedDisplay(test) {
  const isRollingOrFlying = test.start_mode && test.start_mode !== "STANDING";
  const hasSpeed = test.speed || test.spawn?.initial_speed_kmh;
  if (!isRollingOrFlying || !hasSpeed) {
    hideAISpeedStatus();
    return;
  }
  const spd = test.speed ?? test.spawn?.initial_speed_kmh ?? 0;
  const gear = test.gear ?? test.spawn?.initial_gear ?? "Auto";
  const rpm = test.rpm ?? test.spawn?.initial_rpm ?? "Auto";
  const defaultOffset = ((Number.parseFloat(spd) / 3.6) * 3).toFixed(1);
  const offset = test.spawn_offset ?? test.spawn?.spawn_offset_m ?? defaultOffset;
  showAISpeedStatus(`AI Telemetry: ${spd} km/h | Gear ${gear} @ ${rpm} RPM | Run-up: ${offset}m`);
}

async function loadReferenceTests() {
  try {
    const refData = await api.getReferenceTests();
    if (refData?.success) {
      state.referenceTests = refData.tests;
      const refBadge = document.getElementById("ref-total-badge");
      if (refBadge) refBadge.textContent = refData.count ?? refData.tests?.length ?? "";
    }
  } catch (err) {
    console.warn("Could not load reference benchmark tests:", err);
  }
}

export async function loadInitialData() {
  try {
    const trackData = await api.getTracks();
    if (trackData.success) {
      state.tracks = trackData.tracks;
      populateTrackDropdown();
    }
    const carData = await api.getCars();
    if (carData.success) {
      state.cars = carData.cars;
      populateCarDropdown();
    }
    const curData = await api.getCurriculum();
    if (curData.success) {
      state.curriculum = curData.curriculum;
      renderLicenseTabs();
      selectTier(0);
    }
    await loadReferenceTests();
  } catch (err) {
    console.error("Initialization failed:", err);
    showToast("Failed to load designer data: " + err.message, "error");
  }
}

export function isFullLapTest(test) {
  const s0 = Number.parseFloat(test.start_s || 0);
  const s1 = Number.parseFloat(test.finish_s || 1);
  return (s0 <= 0.005 && s1 >= 0.99) || test.start_mode === "FLYING_LAP";
}

function populateTestFormFields(test) {
  if (dom.formTestIdBadge) dom.formTestIdBadge.textContent = test.test_id;
  if (dom.inputTestId) dom.inputTestId.value = test.test_id;
  if (dom.inputTitle) dom.inputTitle.value = test.title || "";
  if (dom.inputObjective) dom.inputObjective.value = test.lesson_objective || "";
  if (dom.inputDescription) dom.inputDescription.value = test.description || "";
  if (dom.inputSearchTrack) dom.inputSearchTrack.value = "";
  if (dom.inputSearchCar) dom.inputSearchCar.value = "";
  populateTrackDropdown(test.track_id || "");
  populateLayoutDropdown(test.track_id || "", test.track_layout || "");
  populateCarDropdown(test.car_id || "");
}

function populateTestTargets(test) {
  const targets = test.targets || { gold_seconds: 10, silver_seconds: 12, bronze_seconds: 15 };
  if (dom.targetGold) dom.targetGold.value = targets.gold_seconds;
  if (dom.targetSilver) dom.targetSilver.value = targets.silver_seconds;
  if (dom.targetBronze) dom.targetBronze.value = targets.bronze_seconds;
  validateTargets();
}

export async function loadTestIntoForm(testIdx) {
  state.activeTestIndex = testIdx;
  const activeTier = state.curriculum[state.activeTierIndex];
  const test = activeTier?.tests?.[testIdx];
  if (!test) return;

  document.querySelectorAll(".test-item").forEach((el, idx) => {
    el.classList.toggle("active", idx === testIdx);
  });

  populateTestFormFields(test);

  const fullLap = isFullLapTest(test);
  if (dom.toggleFullLap) dom.toggleFullLap.checked = fullLap;
  updateFullLapState(fullLap);

  const startS = Number.parseFloat(test.start_s || 0.0);
  const finishS = Number.parseFloat(test.finish_s || 1.0);
  setSpatialPositions(startS, finishS);

  setStartMode(test.start_mode || "STANDING");
  updateTestAISpeedDisplay(test);
  if (dom.checkStopBox) dom.checkStopBox.checked = Boolean(test.with_stop_box);

  populateTestTargets(test);
  await fetchAndRenderSpline(test.track_id, test.track_layout || "");
}

export function clearForm() {
  if (dom.formTestIdBadge) dom.formTestIdBadge.textContent = "--";
  if (dom.inputTestId) dom.inputTestId.value = "";
  if (dom.inputTitle) dom.inputTitle.value = "";
  if (dom.inputObjective) dom.inputObjective.value = "";
  if (dom.inputDescription) dom.inputDescription.value = "";
  if (dom.inputSearchTrack) dom.inputSearchTrack.value = "";
  if (dom.inputSearchCar) dom.inputSearchCar.value = "";
  populateTrackDropdown("");
  if (dom.selectLayout) dom.selectLayout.innerHTML = "";
  populateCarDropdown("");
  setSpatialPositions(0, 1);
  setStartMode("STANDING");
  if (dom.targetGold) dom.targetGold.value = "";
  if (dom.targetSilver) dom.targetSilver.value = "";
  if (dom.targetBronze) dom.targetBronze.value = "";
  state.currentSpline = null;
  drawEmptyCanvas();
}

export function setSpatialPositions(startS, finishS) {
  startS = Math.max(0, Math.min(1, startS));
  finishS = Math.max(0, Math.min(1, finishS));

  if (dom.sliderStart) dom.sliderStart.value = startS;
  if (dom.sliderFinish) dom.sliderFinish.value = finishS;
  if (dom.inputStart) dom.inputStart.value = startS.toFixed(4);
  if (dom.inputFinish) dom.inputFinish.value = finishS.toFixed(4);

  if (dom.dispStartS) dom.dispStartS.textContent = (startS * 100).toFixed(2) + "%";
  if (dom.dispFinishS) dom.dispFinishS.textContent = (finishS * 100).toFixed(2) + "%";

  const totalLen = state.currentSpline?.total_length_m ?? 0;
  const startM = Math.round(startS * totalLen);
  const finishM = Math.round(finishS * totalLen);
  const sectorDist =
    finishS >= startS
      ? Math.round((finishS - startS) * totalLen)
      : Math.round((1.0 - startS + finishS) * totalLen);

  if (dom.dispStartM) dom.dispStartM.textContent = startM + " m";
  if (dom.dispFinishM) dom.dispFinishM.textContent = finishM + " m";
  if (dom.dispSectorDist) dom.dispSectorDist.textContent = sectorDist + " m";

  renderCanvasTrack();
  triggerAutoCalculateTargets(100, startS, finishS);
}

export function triggerAutoCalculateTargets(delay = 100, overrideStartS = null, overrideFinishS = null) {
  if (autoCalculateTargetsTimer) clearTimeout(autoCalculateTargetsTimer);
  autoCalculateTargetsTimer = setTimeout(() => {
    void autoCalculateTargetsFromTelemetry(overrideStartS, overrideFinishS);
  }, delay);
}

function applyCalculatedPhysics(test, physics, startMode) {
  if (startMode === "STANDING" || !physics) return;
  test.speed = physics.speed_kmh;
  test.spawn_offset = physics.spawn_offset_m;
  test.gear = physics.gear;
  test.rpm = physics.rpm;
  if (test.spawn) {
    test.spawn.initial_speed_kmh = physics.speed_kmh;
    test.spawn.spawn_offset_m = physics.spawn_offset_m;
    test.spawn.initial_gear = physics.gear;
    test.spawn.initial_rpm = physics.rpm;
  }
}

function applyCalculatedTargets(test, res, startMode) {
  const tg = res.targets;
  if (dom.targetGold) dom.targetGold.value = tg.gold_seconds.toFixed(1);
  if (dom.targetSilver) dom.targetSilver.value = tg.silver_seconds.toFixed(1);
  if (dom.targetBronze) dom.targetBronze.value = tg.bronze_seconds.toFixed(1);

  test.targets = {
    gold_seconds: tg.gold_seconds,
    silver_seconds: tg.silver_seconds,
    bronze_seconds: tg.bronze_seconds,
  };

  applyCalculatedPhysics(test, res.physics, startMode);
  validateTargets();

  const speedVal = res.physics?.speed_kmh ?? test.speed;
  const modeLabel = startMode === "STANDING" ? "Standing Launch" : `${speedVal} km/h Handover`;
  const sourceLabel = res.source ? ` (${res.source.replaceAll("_", " ")})` : "";
  showAISpeedStatus(
    `⚡ Telemetry Targets${sourceLabel}: Gold ${tg.gold_seconds}s | Silver ${tg.silver_seconds}s | Bronze ${tg.bronze_seconds}s • ${modeLabel} • Sector: ${res.sector_time_s}s (${res.sector_length_m}m)`
  );
}

function getSelectedStartMode() {
  if (dom.radioStanding?.checked) return "STANDING";
  if (dom.radioRolling?.checked) return "ROLLING";
  return "FLYING_LAP";
}

export async function autoCalculateTargetsFromTelemetry(overrideStartS = null, overrideFinishS = null) {
  const activeTier = state.curriculum[state.activeTierIndex];
  const test = activeTier?.tests?.[state.activeTestIndex] ?? null;
  if (!test) return;

  const trackId = dom.selectTrack?.value || test.track_id;
  const layout = dom.selectLayout?.value ?? test.track_layout ?? "";
  const carId = dom.selectCar?.value || test.car_id;
  const rawStart = dom.inputStart?.value ?? test.start_s ?? 0;
  const rawFinish = dom.inputFinish?.value ?? test.finish_s ?? 1;
  const startS = overrideStartS !== null ? overrideStartS : Number.parseFloat(rawStart);
  const finishS = overrideFinishS !== null ? overrideFinishS : Number.parseFloat(rawFinish);

  const startMode = getSelectedStartMode();
  const withStopBox = dom.checkStopBox ? dom.checkStopBox.checked : Boolean(test.with_stop_box);

  test.start_s = startS;
  test.finish_s = finishS;
  if (!trackId || !carId) return;

  try {
    const res = await api.calculateTargets({
      track_id: trackId,
      track_layout: layout,
      car_id: carId,
      start_s: startS,
      finish_s: finishS,
      start_mode: startMode,
      with_stop_box: withStopBox,
    });
    if (res?.success && res.targets) {
      applyCalculatedTargets(test, res, startMode);
    }
  } catch (err) {
    console.warn("Auto-calculate targets error:", err);
  }
}

export function updateFullLapState(isFull) {
  if (dom.sliderStart) dom.sliderStart.disabled = isFull;
  if (dom.sliderFinish) dom.sliderFinish.disabled = isFull;
  if (dom.inputStart) dom.inputStart.disabled = isFull;
  if (dom.inputFinish) dom.inputFinish.disabled = isFull;
  if (isFull) setSpatialPositions(0.0, 0.999);
}

export function setStartMode(mode) {
  if (dom.radioStanding) dom.radioStanding.checked = mode === "STANDING";
  if (dom.radioRolling) dom.radioRolling.checked = mode === "ROLLING";
  if (dom.radioFlying) dom.radioFlying.checked = mode === "FLYING_LAP";

  if (dom.cardStanding) dom.cardStanding.classList.toggle("active", mode === "STANDING");
  if (dom.cardRolling) dom.cardRolling.classList.toggle("active", mode === "ROLLING");
  if (dom.cardFlying) dom.cardFlying.classList.toggle("active", mode === "FLYING_LAP");

  if (mode === "STANDING") {
    if (dom.stopBoxRow) dom.stopBoxRow.style.display = "block";
  } else {
    if (dom.stopBoxRow) dom.stopBoxRow.style.display = "none";
    if (dom.checkStopBox) dom.checkStopBox.checked = false;
  }
  triggerAutoCalculateTargets(50);
}

export function validateTargets() {
  if (!dom.targetGold || !dom.targetSilver || !dom.targetBronze) return true;
  const gold = Number.parseFloat(dom.targetGold.value);
  const silver = Number.parseFloat(dom.targetSilver.value);
  const bronze = Number.parseFloat(dom.targetBronze.value);

  if (!Number.isNaN(gold) && !Number.isNaN(silver) && !Number.isNaN(bronze)) {
    if (gold >= silver || silver >= bronze) {
      if (dom.targetError) dom.targetError.style.display = "block";
      return false;
    }
  }
  if (dom.targetError) dom.targetError.style.display = "none";
  return true;
}

export function autoCalculateSpawnOffset(test = null) {
  const targetTest = test ?? state.curriculum[state.activeTierIndex]?.tests?.[state.activeTestIndex] ?? null;
  if (!targetTest) return;
  const spdKmh = Number.parseFloat(targetTest.speed) || 0;
  const offset = (spdKmh / 3.6) * 3.0;
  targetTest.spawn_offset = Number.parseFloat(offset.toFixed(1));
  if (targetTest.spawn) {
    targetTest.spawn.spawn_offset_m = targetTest.spawn_offset;
  }
}

export function applyStandingMode(test) {
  test.start_mode = "STANDING";
  test.speed = 0.0;
  test.spawn_offset = 0.0;
  test.with_stop_box = Boolean(dom.checkStopBox?.checked);
  delete test.gear;
  delete test.rpm;
  if (test.spawn) {
    test.spawn.initial_speed_kmh = 0.0;
    test.spawn.spawn_offset_m = 0.0;
    delete test.spawn.initial_gear;
    delete test.spawn.initial_rpm;
  }
}

function applyDynamicMode(test, mode, defaultSpeed) {
  test.start_mode = mode;
  const currentSpeed = test.speed ?? 0;
  test.speed = currentSpeed > 0 ? currentSpeed : defaultSpeed;
  const currentOffset = test.spawn_offset ?? 0;
  const calculatedOffset = Number.parseFloat(((test.speed / 3.6) * 3.0).toFixed(1));
  test.spawn_offset = currentOffset > 0 ? currentOffset : calculatedOffset;
  test.with_stop_box = false;
}

function syncNumericField(test, fieldName) {
  const spawnProp = fieldName === "gear" ? "initial_gear" : "initial_rpm";
  const val = test[fieldName];
  if (val !== undefined && val !== null && String(val).trim() !== "") {
    const num = Number.parseInt(val, 10);
    test[fieldName] = num;
    test.spawn[spawnProp] = num;
  } else {
    delete test[fieldName];
    if (test.spawn) delete test.spawn[spawnProp];
  }
}

function applyStartModeSettings(test) {
  if (dom.radioStanding?.checked) {
    applyStandingMode(test);
  } else if (dom.radioRolling?.checked) {
    applyDynamicMode(test, "ROLLING", 75.0);
  } else {
    applyDynamicMode(test, "FLYING_LAP", 140.0);
  }

  test.spawn = test.spawn || {};
  test.spawn.initial_speed_kmh = test.speed;
  test.spawn.spawn_offset_m = test.spawn_offset;

  syncNumericField(test, "gear");
  syncNumericField(test, "rpm");
}

export function saveFormIntoActiveTest() {
  const activeTier = state.curriculum[state.activeTierIndex];
  const test = activeTier?.tests?.[state.activeTestIndex];
  if (!test) return;

  test.test_id = dom.inputTestId?.value.trim() || test.test_id;
  test.title = dom.inputTitle?.value.trim() || test.title;
  test.lesson_objective = dom.inputObjective?.value.trim() ?? "";
  test.description = dom.inputDescription?.value.trim() ?? "";
  test.car_id = dom.selectCar?.value || test.car_id;
  test.track_id = dom.selectTrack?.value || test.track_id;
  test.track_layout = dom.selectLayout?.value ?? "";

  test.start_s = Number.parseFloat(dom.inputStart?.value ?? 0) || 0;
  test.finish_s = Number.parseFloat(dom.inputFinish?.value ?? 1) || 1;

  applyStartModeSettings(test);

  test.targets = {
    gold_seconds: Number.parseFloat(dom.targetGold?.value ?? 10) || 10,
    silver_seconds: Number.parseFloat(dom.targetSilver?.value ?? 12) || 12,
    bronze_seconds: Number.parseFloat(dom.targetBronze?.value ?? 15) || 15,
  };
}

export async function saveCurrentTier() {
  const activeTier = state.curriculum[state.activeTierIndex];
  if (!activeTier) return;
  const data = await api.saveTier(activeTier.tier_name, activeTier.tests);
  if (!data.success) throw new Error(data.error || "Save failed");
  for (const test of activeTier.tests) {
    delete test.previous_test_id;
  }
  return data;
}
