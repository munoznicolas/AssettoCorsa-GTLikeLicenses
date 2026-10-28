/**
 * test-editor.js
 * Test definition editor, form validation, license tabs, and curriculum catalog manager.
 */

import { state } from "./state.js";
import { dom } from "./dom.js";
import { api, isStaticHost } from "./api.js";
import { showToast, escapeHtml } from "./ui-utils.js";
import {
  fetchAndRenderSpline,
  renderCanvasTrack,
  drawEmptyCanvas,
  setTrackCanvasPositionCallback,
} from "./track-canvas.js";
import {
  fetchAndApplyAISpeed,
  cancelActiveACSession,
  showAISpeedStatus,
  hideAISpeedStatus,
  executeExportSingleTelemetryScript,
} from "./queue-runner.js";
import { loadCurriculum, saveCurriculum } from "./curriculum-store.js";
import { resolveTelemetryEngine, saveCustomTelemetryProfile } from "./telemetry-store.js";
import { generateMiniatureDataUrl } from "./miniature-builder.js";

/**
 * Filter tracks by search query across id, name, and layout names.
 */
function filterTracks(query) {
  if (!query) return state.tracks;
  return state.tracks.filter((t) => {
    const idMatch = (t.track_id || "").toLowerCase().includes(query);
    const nameMatch = (t.name || "").toLowerCase().includes(query);
    const layoutMatch = (t.layouts || []).some(
      (l) =>
        (l.name || "").toLowerCase().includes(query) ||
        (l.layout_id || "").toLowerCase().includes(query)
    );
    return idMatch || nameMatch || layoutMatch;
  });
}

/**
 * Update filter count badge and clear button visibility.
 */
function updateFilterIndicator(countEl, clearBtn, query, matchCount, totalCount) {
  if (countEl) {
    countEl.style.display = query ? "inline-block" : "none";
    if (query) {
      countEl.textContent = `${matchCount} / ${totalCount}`;
      countEl.classList.toggle("empty", matchCount === 0);
    }
  }
  if (clearBtn) {
    clearBtn.style.display = query ? "block" : "none";
  }
}

/**
 * Format and update AI Speed Telemetry display banner.
 */
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

/**
 * Load GT reference benchmark tests.
 */
async function loadReferenceTests() {
  try {
    const refData = await api.getReferenceTests();
    if (refData?.success) {
      state.referenceTests = refData.tests;
      const refBadge = document.getElementById("ref-total-badge");
      if (refBadge) {
        refBadge.textContent = refData.count ?? refData.tests?.length ?? "";
      }
    }
  } catch (err) {
    console.warn("Could not load reference benchmark tests:", err);
  }
}

/**
 * Initial load of curriculum, tracks, cars, and benchmark reference tests.
 */
export async function loadInitialData() {
  try {
    // 1. Fetch Tracks
    const trackData = await api.getTracks();
    if (trackData.success) {
      state.tracks = trackData.tracks;
      populateTrackDropdown();
    }

    // 2. Fetch Cars
    const carData = await api.getCars();
    if (carData.success) {
      state.cars = carData.cars;
      populateCarDropdown();
    }

    // 3. Load Curriculum (LocalStorage source of truth with bundled fallback)
    const loadedCurriculum = await loadCurriculum();
    if (loadedCurriculum && loadedCurriculum.length > 0) {
      state.curriculum = loadedCurriculum;
      renderLicenseTabs();
      selectTier(0);
    }

    // 4. Fetch GT Reference Benchmark Tests
    await loadReferenceTests();
  } catch (err) {
    console.error("Initialization failed:", err);
    showToast("Failed to load designer data: " + err.message, "error");
  }
}

/**
 * Filter and populate track selection dropdown.
 */
export function populateTrackDropdown(selectedTrackId = null) {
  if (!dom.selectTrack) return;
  const query = dom.inputSearchTrack?.value.trim().toLowerCase() ?? "";
  const activeTrackId = selectedTrackId ?? dom.selectTrack.value;

  dom.selectTrack.innerHTML = '<option value="">Select Kunos Track...</option>';

  const matches = filterTracks(query);
  updateFilterIndicator(dom.trackFilterCount, dom.btnClearTrackSearch, query, matches.length, state.tracks.length);

  for (const t of matches) {
    const opt = document.createElement("option");
    opt.value = t.track_id;
    opt.textContent = `${t.name} (${t.track_id})`;
    if (t.track_id === activeTrackId) {
      opt.selected = true;
    }
    dom.selectTrack.appendChild(opt);
  }

  if (activeTrackId && (!query || matches.some((t) => t.track_id === activeTrackId))) {
    dom.selectTrack.value = activeTrackId;
  }
}

/**
 * Populate layout dropdown for a given track.
 */
export function populateLayoutDropdown(trackId, selectedLayout = "") {
  if (!dom.selectLayout) return;
  dom.selectLayout.innerHTML = "";
  const track = state.tracks.find((t) => t.track_id === trackId);
  if (!track?.layouts?.length) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "Default Layout";
    dom.selectLayout.appendChild(opt);
    return;
  }

  for (const l of track.layouts) {
    const opt = document.createElement("option");
    opt.value = l.layout_id;
    opt.textContent = l.name || l.layout_id || "Default Layout";
    if (l.layout_id === selectedLayout) {
      opt.selected = true;
    }
    dom.selectLayout.appendChild(opt);
  }
}

/**
 * Check if car matches AWD/4WD tokens.
 */
function matchesAwd(car, tok) {
  return (
    car.dt === "awd" ||
    car.tags.includes("awd") ||
    car.tags.includes("4wd") ||
    car.tags.includes("mawd") ||
    car.tags.includes("fawd") ||
    car.id.includes(tok) ||
    car.name.includes(tok)
  );
}

/**
 * Check if car matches specific drivetrain token (AWD, FWD, RWD).
 */
function matchesDrivetrainToken(car, tok) {
  if (tok === "awd" || tok === "4wd") {
    return matchesAwd(car, tok);
  }
  if (tok === "fwd") {
    return car.dt === "fwd" || car.tags.includes("fwd") || car.id.includes(tok) || car.name.includes(tok);
  }
  if (tok === "rwd") {
    return car.dt === "rwd" || car.tags.includes("rwd") || car.id.includes(tok) || car.name.includes(tok);
  }
  return null;
}

/**
 * Check if a car matches a search token.
 */
function matchesCarToken(car, tok) {
  const dtMatch = matchesDrivetrainToken(car, tok);
  if (dtMatch !== null) return dtMatch;
  return (
    car.id.includes(tok) ||
    car.name.includes(tok) ||
    car.brand.includes(tok) ||
    car.dt.includes(tok) ||
    car.tags.some((t) => t.includes(tok))
  );
}

/**
 * Filter cars by text query and tags.
 */
export function filterCars(query) {
  if (!query) return state.cars;
  const tokens = query.toLowerCase().split(/\s+/).filter(Boolean);
  return state.cars.filter((c) => {
    const carData = {
      id: (c.car_id || "").toLowerCase(),
      name: (c.name || "").toLowerCase(),
      brand: (c.brand || "").toLowerCase(),
      dt: (c.drivetrain || "").toLowerCase(),
      tags: (c.tags || []).map((t) => String(t).toLowerCase()),
    };
    return tokens.every((tok) => matchesCarToken(carData, tok));
  });
}

/**
 * Populate car selection dropdown.
 */
export function populateCarDropdown(selectedCarId = null) {
  if (!dom.selectCar) return;
  const query = dom.inputSearchCar?.value.trim() ?? "";
  const activeCarId = selectedCarId ?? dom.selectCar.value;

  dom.selectCar.innerHTML = '<option value="">Select Kunos Car...</option>';

  const matches = filterCars(query);
  updateFilterIndicator(dom.carFilterCount, dom.btnClearCarSearch, query, matches.length, state.cars.length);

  for (const c of matches) {
    const opt = document.createElement("option");
    opt.value = c.car_id;
    const brandStr = c.brand ? ` (${c.brand})` : "";
    const dtStr = c.drivetrain ? ` [${c.drivetrain}]` : "";
    opt.textContent = `${c.name}${brandStr}${dtStr}`;
    if (c.car_id === activeCarId) {
      opt.selected = true;
    }
    dom.selectCar.appendChild(opt);
  }

  if (activeCarId && (!query || matches.some((c) => c.car_id === activeCarId))) {
    dom.selectCar.value = activeCarId;
  }
}

/**
 * Render license tier navigation tabs.
 */
export function renderLicenseTabs() {
  if (!dom.tabsContainer) return;
  dom.tabsContainer.innerHTML = "";
  state.curriculum.forEach((tier, idx) => {
    const btn = document.createElement("button");
    btn.className = `license-tab ${idx === state.activeTierIndex ? "active" : ""}`;
    btn.innerHTML = `
      <img class="tab-badge-img" src="./assets/career_ui/${escapeHtml(tier.badge_asset)}" alt="${escapeHtml(tier.tier_name)}">
      <span>${escapeHtml(tier.tier_name)}</span>
      <span class="tab-count">${Number(tier.tests.length) || 0}</span>
    `;
    btn.addEventListener("click", () => selectTier(idx));
    dom.tabsContainer.appendChild(btn);
  });
}

/**
 * Switch active license tier.
 */
export function selectTier(tierIdx) {
  state.activeTierIndex = tierIdx;
  state.activeTestIndex = 0;
  state.isReferenceViewActive = false;

  // Show workspace, hide reference view
  if (dom.workspaceView) dom.workspaceView.style.display = "flex";
  if (dom.referenceView) dom.referenceView.style.display = "none";
  if (dom.tabBtnReference) dom.tabBtnReference.classList.remove("active");

  // Update active tab styling
  document.querySelectorAll(".tab-container .license-tab").forEach((tab, idx) => {
    tab.classList.toggle("active", idx === tierIdx);
  });

  const activeTier = state.curriculum[tierIdx];
  if (!activeTier) return;

  if (dom.tierTitle) dom.tierTitle.textContent = activeTier.tier_name;
  if (dom.tierDesc) dom.tierDesc.textContent = activeTier.description;
  if (dom.testCountBadge) dom.testCountBadge.textContent = `${activeTier.tests.length} Tests`;

  renderTestList();
  if (activeTier.tests.length > 0) {
    void loadTestIntoForm(0);
  } else {
    clearForm();
  }
}

/**
 * Render tests sidebar list for the active tier.
 */
export function renderTestList() {
  if (!dom.testList) return;
  dom.testList.innerHTML = "";
  const activeTier = state.curriculum[state.activeTierIndex];
  if (!activeTier) return;

  activeTier.tests.forEach((test, idx) => {
    const item = document.createElement("div");
    item.className = `test-item ${idx === state.activeTestIndex ? "active" : ""}`;

    const modeClass = escapeHtml((test.start_mode || "standing").toLowerCase());
    const isFullLap = isFullLapTest(test);
    const lapTypeLabel = isFullLap ? "Full Lap" : "Sector";

    const rawPreview =
      test.preview_image ||
      (activeTier.folder
        ? `./content/career/${encodeURIComponent(activeTier.folder)}/event${idx + 1}/preview.png`
        : `/api/test_preview?test_id=${encodeURIComponent(test.test_id)}`);
    const previewUrl = rawPreview && rawPreview.startsWith("/") ? `.${rawPreview}` : rawPreview;

    item.innerHTML = `
      <div class="test-item-thumb">
        <img src="${escapeHtml(previewUrl)}?t=${encodeURIComponent(state.cacheBuster)}" 
             alt="${escapeHtml(test.test_id)}" 
             loading="lazy" 
             onerror="this.style.display='none'">
        <span class="test-item-stage-overlay">${escapeHtml(test.test_id)}</span>
      </div>
      <div class="test-item-body">
        <div class="test-item-top">
          <span class="test-item-id">${escapeHtml(test.test_id)}</span>
          <span class="test-item-mode ${modeClass}">${escapeHtml(test.start_mode)}</span>
        </div>
        <div class="test-item-title">${escapeHtml(test.title)}</div>
        <div class="test-item-meta">
          <span>🏁 ${lapTypeLabel}</span>
          <span>📍 ${escapeHtml(test.track_id)}</span>
          <span>🥇 ${test.targets?.gold_seconds !== undefined ? `${Number(test.targets.gold_seconds).toFixed(2)}s` : ""}</span>
        </div>
      </div>
    `;

    item.addEventListener("click", () => {
      void loadTestIntoForm(idx);
    });
    dom.testList.appendChild(item);
  });
}

/**
 * Determine if test is a full lap session.
 */
export function isFullLapTest(test) {
  const s0 = Number.parseFloat(test.start_s || 0);
  const s1 = Number.parseFloat(test.finish_s || 1);
  return (s0 <= 0.005 && s1 >= 0.99) || test.start_mode === "FLYING_LAP";
}

/**
 * Populate standard test text and dropdown fields in the form.
 */
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

/**
 * Populate medal targets in the form.
 */
function populateTestTargets(test) {
  const targets = test.targets || {
    gold_seconds: 10,
    silver_seconds: 12,
    bronze_seconds: 15,
  };
  if (dom.targetGold) dom.targetGold.value = targets.gold_seconds;
  if (dom.targetSilver) dom.targetSilver.value = targets.silver_seconds;
  if (dom.targetBronze) dom.targetBronze.value = targets.bronze_seconds;
  validateTargets();
}

/**
 * Load test definition into editing form controls.
 */
export async function loadTestIntoForm(testIdx) {
  state.activeTestIndex = testIdx;
  const activeTier = state.curriculum[state.activeTierIndex];
  if (!activeTier?.tests) return;
  const test = activeTier.tests[testIdx];
  if (!test) return;

  // Update list selection highlight
  document.querySelectorAll(".test-item").forEach((el, idx) => {
    el.classList.toggle("active", idx === testIdx);
  });

  populateTestFormFields(test);

  // Lap Mode & Positions
  const fullLap = isFullLapTest(test);
  if (dom.toggleFullLap) dom.toggleFullLap.checked = fullLap;
  updateFullLapState(fullLap);

  const startS = Number.parseFloat(test.start_s || 0.0);
  const finishS = Number.parseFloat(test.finish_s || 1.0);
  setSpatialPositions(startS, finishS);

  // Start Mode & Telemetry Status
  setStartMode(test.start_mode || "STANDING");
  updateTestAISpeedDisplay(test);
  if (dom.checkStopBox) dom.checkStopBox.checked = Boolean(test.with_stop_box);

  populateTestTargets(test);

  // Fetch spline & render map
  await fetchAndRenderSpline(test.track_id, test.track_layout || "");
}

/**
 * Clear the test form fields.
 */
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

/**
 * Synchronize start/finish slider values, text displays, and 2D canvas marker projections.
 */
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
  let sectorDist = 0;
  if (finishS >= startS) {
    sectorDist = Math.round((finishS - startS) * totalLen);
  } else {
    sectorDist = Math.round((1.0 - startS + finishS) * totalLen);
  }

  if (dom.dispStartM) dom.dispStartM.textContent = startM + " m";
  if (dom.dispFinishM) dom.dispFinishM.textContent = finishM + " m";
  if (dom.dispSectorDist) dom.dispSectorDist.textContent = sectorDist + " m";

  renderCanvasTrack();
  triggerAutoCalculateTargets(100, startS, finishS);
}

let autoCalculateTargetsTimer = null;

/**
 * Debounced trigger to recalculate Gold, Silver, Bronze targets and launch physics from telemetry points.
 */
export function triggerAutoCalculateTargets(delay = 100, overrideStartS = null, overrideFinishS = null) {
  if (autoCalculateTargetsTimer) {
    clearTimeout(autoCalculateTargetsTimer);
  }
  autoCalculateTargetsTimer = setTimeout(() => {
    void autoCalculateTargetsFromTelemetry(overrideStartS, overrideFinishS);
  }, delay);
}

/**
 * Update test physics parameters from calculation result.
 */
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

/**
 * Apply targets and physics from telemetry response to UI and test object.
 */
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

/**
 * Get active start mode string from UI radio buttons.
 */
function getSelectedStartMode() {
  if (dom.radioStanding?.checked) return "STANDING";
  if (dom.radioRolling?.checked) return "ROLLING";
  return "FLYING_LAP";
}

/**
 * Performs step-by-step telemetry integration for the current test definition.
 */
export async function autoCalculateTargetsFromTelemetry(overrideStartS = null, overrideFinishS = null) {
  const activeTier = state.curriculum[state.activeTierIndex];
  const test = activeTier?.tests ? activeTier.tests[state.activeTestIndex] : null;
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
    const telRes = await resolveTelemetryEngine(trackId, layout, carId);
    if (telRes) {
      const { engine, source } = telRes;
      const countdownSec = Number(test.countdown_sec || 3.0);
      const targets = engine.calculateSectorTargets(startS, finishS, startMode, withStopBox);
      const physics = engine.calculateGatePhysics(startS, countdownSec);

      applyCalculatedTargets(test, {
        success: true,
        source,
        targets,
        physics,
        sector_time_s: targets.sector_time_s,
        sector_length_m: targets.sector_length_m,
      }, startMode);

      if (dom.telemetryMissingCard) dom.telemetryMissingCard.style.display = "none";
      if (dom.btnExportSingleTelemetryScript) dom.btnExportSingleTelemetryScript.style.display = "none";
    } else {
      // Telemetry not available for this track + car combination
      if (dom.telemetryMissingCard) dom.telemetryMissingCard.style.display = "block";
      if (dom.btnExportSingleTelemetryScript) dom.btnExportSingleTelemetryScript.style.display = "inline-flex";
      showAISpeedStatus(`?? No telemetry profile for ${carId} @ ${trackId}. Upload profile below or record in AC.`);
    }
  } catch (err) {
    console.warn("Client-side telemetry targets error:", err);
  }
}

/**
 * Lock or unlock sliders depending on full lap state.
 */
export function updateFullLapState(isFull) {
  if (dom.sliderStart) dom.sliderStart.disabled = isFull;
  if (dom.sliderFinish) dom.sliderFinish.disabled = isFull;
  if (dom.inputStart) dom.inputStart.disabled = isFull;
  if (dom.inputFinish) dom.inputFinish.disabled = isFull;

  if (isFull) {
    setSpatialPositions(0.0, 0.999);
  }
}

/**
 * Switch starting condition mode (Standing, Rolling, Flying Lap).
 */
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

/**
 * Validate that gold < silver < bronze.
 */
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

/**
 * Renumber test IDs and preview image paths sequentially within a tier.
 */
export function renumberTierTests(tier) {
  if (!tier?.tests) return;
  const prefix = tier.test_prefix || "T-";
  tier.tests.forEach((t, i) => {
    const num = i + 1;
    t.test_id = `${prefix}${num}`;
    if (tier.folder) {
      t.preview_image = `./content/career/${tier.folder}/event${num}/preview.png`;
    }
  });
}

/**
 * Auto-calculate spawn run-up distance based on speed and 3-second countdown.
 */
export function autoCalculateSpawnOffset(test = null) {
  const targetTest = test ?? state.curriculum[state.activeTierIndex]?.tests?.[state.activeTestIndex] ?? null;
  if (!targetTest) return;
  const spdKmh = Number.parseFloat(targetTest.speed) || 0;
  // Formula: spawn_offset = v_mps * 3.0 seconds
  const offset = (spdKmh / 3.6) * 3.0;
  targetTest.spawn_offset = Number.parseFloat(offset.toFixed(1));
  if (targetTest.spawn) {
    targetTest.spawn.spawn_offset_m = targetTest.spawn_offset;
  }
}

/**
 * Configure standing start parameters for test.
 */
function applyStandingMode(test) {
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

/**
 * Configure rolling / flying lap parameters for test.
 */
function applyDynamicMode(test, mode, defaultSpeed) {
  test.start_mode = mode;
  const currentSpeed = test.speed ?? 0;
  test.speed = currentSpeed > 0 ? currentSpeed : defaultSpeed;
  const currentOffset = test.spawn_offset ?? 0;
  const calculatedOffset = Number.parseFloat(((test.speed / 3.6) * 3.0).toFixed(1));
  test.spawn_offset = currentOffset > 0 ? currentOffset : calculatedOffset;
  test.with_stop_box = false;
}

/**
 * Synchronize gear or rpm integer value between test object and spawn dictionary.
 */
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

/**
 * Update test physics and start conditions from form selections.
 */
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

/**
 * Persist current form inputs into the active in-memory test object.
 */
export function saveFormIntoActiveTest() {
  const activeTier = state.curriculum[state.activeTierIndex];
  if (!activeTier?.tests) return;
  const test = activeTier.tests[state.activeTestIndex];
  if (!test) return;

  test.test_id = dom.inputTestId?.value.trim() || test.test_id;
  test.title = dom.inputTitle?.value.trim() || test.title;
  test.lesson_objective = dom.inputObjective?.value.trim() ?? "";
  test.description = dom.inputDescription?.value.trim() ?? "";
  test.car_id = dom.selectCar?.value || test.car_id;
  test.track_id = dom.selectTrack?.value || test.track_id;
  test.track_layout = dom.selectLayout?.value ?? "";

  const rawStart = dom.inputStart?.value ?? 0;
  const rawFinish = dom.inputFinish?.value ?? 1;
  test.start_s = Number.parseFloat(rawStart) || 0;
  test.finish_s = Number.parseFloat(rawFinish) || 1;

  applyStartModeSettings(test);

  const goldVal = dom.targetGold?.value ?? 10;
  const silverVal = dom.targetSilver?.value ?? 12;
  const bronzeVal = dom.targetBronze?.value ?? 15;
  test.targets = {
    gold_seconds: Number.parseFloat(goldVal) || 10,
    silver_seconds: Number.parseFloat(silverVal) || 12,
    bronze_seconds: Number.parseFloat(bronzeVal) || 15,
  };
}

/**
 * Save active tier's test collection to server.
 */
export async function saveCurrentTier() {
  saveCurriculum(state.curriculum);
  return { success: true, local: true };
}

/**
 * Action handler for adding a new test.
 */
function handleAddTest() {
  const activeTier = state.curriculum[state.activeTierIndex];
  if (!activeTier) return;
  const count = activeTier.tests.length + 1;
  const prefix = activeTier.test_prefix || "T-";

  const newTest = {
    test_id: `${prefix}${count}`,
    tier: activeTier.tier_name,
    title: `Test ${count}: New Sector Challenge`,
    description: "Execute the prescribed driving line cleanly with zero track limit infractions.",
    lesson_objective: "Mastering vehicle balance through the sector.",
    car_id: state.cars[0]?.car_id ?? "ks_mazda_miata",
    track_id: state.tracks[0]?.track_id ?? "ks_vallelunga",
    track_layout: "",
    start_mode: "ROLLING",
    start_s: 0.1,
    finish_s: 0.3,
    spawn_offset: 58.3,
    speed: 70.0,
    gear: 2,
    rpm: 4500,
    with_stop_box: false,
    targets: {
      gold_seconds: 15.0,
      silver_seconds: 16.5,
      bronze_seconds: 18.5,
    },
    preview_image: `./content/career/${activeTier.folder}/event${count}/preview.png`,
  };

  activeTier.tests.push(newTest);
  renumberTierTests(activeTier);
  saveCurriculum(state.curriculum);
  renderLicenseTabs();
  renderTestList();
  void loadTestIntoForm(activeTier.tests.length - 1);
  showToast(`Added new test ${newTest.test_id}`);
}

/**
 * Action handler for deleting the active test.
 */
async function handleDeleteTest() {
  const activeTier = state.curriculum[state.activeTierIndex];
  if (!activeTier || activeTier.tests.length <= 1) {
    showToast("Cannot delete the only test in this license.", "error");
    return;
  }

  const test = activeTier.tests[state.activeTestIndex];
  if (!confirm(`Are you sure you want to remove test "${test.test_id}: ${test.title}"?`)) {
    return;
  }

  const deletedId = test.test_id;
  activeTier.tests.splice(state.activeTestIndex, 1);
  renumberTierTests(activeTier);

  const newIdx = Math.max(0, Math.min(state.activeTestIndex, activeTier.tests.length - 1));
  state.activeTestIndex = newIdx;

  saveCurriculum(state.curriculum);

  // Immediately update UI state so test is removed on screen
  renderLicenseTabs();
  renderTestList();
  await loadTestIntoForm(newIdx);
  showToast(`Removed test ${deletedId}. Subsequent tests renumbered successfully.`);
}

/**
 * Keydown handler for track search input.
 */
async function handleTrackSearchKeydown(e) {
  if (e.key === "Enter") {
    e.preventDefault();
    const query = dom.inputSearchTrack?.value.trim().toLowerCase() ?? "";
    const matches = filterTracks(query);
    if (matches.length > 0 && dom.selectTrack) {
      dom.selectTrack.value = matches[0].track_id;
      populateLayoutDropdown(dom.selectTrack.value, "");
      await fetchAndRenderSpline(dom.selectTrack.value, dom.selectLayout?.value ?? "");
      dom.selectTrack.focus();
    }
  } else if (e.key === "ArrowDown") {
    e.preventDefault();
    dom.selectTrack?.focus();
  } else if (e.key === "Escape") {
    const currentVal = dom.selectTrack?.value ?? "";
    if (dom.inputSearchTrack) dom.inputSearchTrack.value = "";
    populateTrackDropdown(currentVal);
  }
}

/**
 * Keydown handler for car search input.
 */
function handleCarSearchKeydown(e) {
  if (e.key === "Enter") {
    e.preventDefault();
    const query = dom.inputSearchCar?.value.trim() ?? "";
    const matches = filterCars(query);
    if (matches.length > 0 && dom.selectCar) {
      dom.selectCar.value = matches[0].car_id;
      dom.selectCar.focus();
    }
  } else if (e.key === "ArrowDown") {
    e.preventDefault();
    dom.selectCar?.focus();
  } else if (e.key === "Escape") {
    const currentVal = dom.selectCar?.value ?? "";
    if (dom.inputSearchCar) dom.inputSearchCar.value = "";
    populateCarDropdown(currentVal);
  }
}

/**
 * Click handler for standing start card.
 */
function handleCardStandingClick() {
  setStartMode("STANDING");
  const activeTier = state.curriculum[state.activeTierIndex];
  const test = activeTier?.tests ? activeTier.tests[state.activeTestIndex] : null;
  if (test) {
    applyStandingMode(test);
  }
  hideAISpeedStatus();
}

/**
 * Click handler for rolling start card.
 */
function handleCardRollingClick() {
  setStartMode("ROLLING");
  const activeTier = state.curriculum[state.activeTierIndex];
  const test = activeTier?.tests ? activeTier.tests[state.activeTestIndex] : null;
  if (test) {
    test.start_mode = "ROLLING";
    if (!test.speed || test.speed <= 0) {
      void fetchAndApplyAISpeed(false);
    } else {
      autoCalculateSpawnOffset(test);
    }
  }
}

/**
 * Click handler for flying lap card.
 */
function handleCardFlyingClick() {
  setStartMode("FLYING_LAP");
  const activeTier = state.curriculum[state.activeTierIndex];
  const test = activeTier?.tests ? activeTier.tests[state.activeTestIndex] : null;
  if (test) {
    test.start_mode = "FLYING_LAP";
    if (!test.speed || test.speed <= 0) {
      void fetchAndApplyAISpeed(false);
    } else {
      autoCalculateSpawnOffset(test);
    }
  }
}

/**
 * Form submission handler.
 */
async function handleFormSubmit(e) {
  e.preventDefault();
  if (!validateTargets()) {
    showToast("Please ensure Gold < Silver < Bronze targets.", "error");
    return;
  }

  saveFormIntoActiveTest();

  const activeTier = state.curriculum[state.activeTierIndex];
  const activeTest = activeTier?.tests?.[state.activeTestIndex];
  const testId = dom.inputTestId?.value.trim() || activeTest?.test_id;

  const submitBtn = dom.btnSaveTest || dom.form?.querySelector('button[type="submit"]');
  const originalHtml = submitBtn ? submitBtn.innerHTML : "";
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span>Saving & Building Miniature...</span>`;
  }

  try {
    // Generate Miniature client-side using HTML5 Canvas
    if (testId && state.currentSpline && activeTest) {
      try {
        const miniatureDataUrl = generateMiniatureDataUrl(
          state.currentSpline,
          activeTest.start_s ?? 0.0,
          activeTest.finish_s ?? 1.0,
          { testId }
        );
        activeTest.preview_image = miniatureDataUrl;
      } catch (minErr) {
        console.warn("Client-side miniature generation warning:", minErr);
      }
    }

    saveCurriculum(state.curriculum);
    state.cacheBuster = Date.now();
    renderLicenseTabs();
    renderTestList();
    showToast(`Saved test ${testId}! Track miniature updated.`);
  } catch (err) {
    showToast("Save failed: " + err.message, "error");
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalHtml;
    }
  }
}

/**
 * Attach track & car search/filter DOM listeners.
 */
function setupSearchFilterListeners() {
  if (dom.inputSearchTrack) {
    dom.inputSearchTrack.addEventListener("input", () => {
      populateTrackDropdown();
    });
    dom.inputSearchTrack.addEventListener("keydown", (e) => {
      void handleTrackSearchKeydown(e);
    });
  }

  if (dom.btnClearTrackSearch) {
    dom.btnClearTrackSearch.addEventListener("click", () => {
      const currentVal = dom.selectTrack?.value ?? "";
      if (dom.inputSearchTrack) {
        dom.inputSearchTrack.value = "";
        populateTrackDropdown(currentVal);
        dom.inputSearchTrack.focus();
      }
    });
  }

  if (dom.inputSearchCar) {
    dom.inputSearchCar.addEventListener("input", () => {
      populateCarDropdown();
    });
    dom.inputSearchCar.addEventListener("keydown", handleCarSearchKeydown);
  }

  if (dom.btnClearCarSearch) {
    dom.btnClearCarSearch.addEventListener("click", () => {
      const currentVal = dom.selectCar?.value ?? "";
      if (dom.inputSearchCar) {
        dom.inputSearchCar.value = "";
        populateCarDropdown(currentVal);
        dom.inputSearchCar.focus();
      }
    });
  }
}

/**
 * Attach track, layout, car, and stop-box dropdown change listeners.
 */
function setupDropdownChangeListeners() {
  if (dom.selectTrack) {
    dom.selectTrack.addEventListener("change", (e) => {
      const trackId = e.target.value;
      populateLayoutDropdown(trackId, "");
      void fetchAndRenderSpline(trackId, dom.selectLayout?.value ?? "");
      triggerAutoCalculateTargets(100);
    });
  }

  if (dom.selectLayout) {
    dom.selectLayout.addEventListener("change", (e) => {
      void fetchAndRenderSpline(dom.selectTrack?.value ?? "", e.target.value);
      triggerAutoCalculateTargets(100);
    });
  }

  if (dom.selectCar) {
    dom.selectCar.addEventListener("change", () => {
      triggerAutoCalculateTargets(100);
    });
  }

  if (dom.checkStopBox) {
    dom.checkStopBox.addEventListener("change", () => {
      triggerAutoCalculateTargets(50);
    });
  }

  if (dom.toggleFullLap) {
    dom.toggleFullLap.addEventListener("change", (e) => {
      updateFullLapState(e.target.checked);
    });
  }
}

/**
 * Attach spatial sliders and manual numeric inputs listeners.
 */
function setupPositionControlListeners() {
  if (dom.sliderStart) {
    dom.sliderStart.addEventListener("input", (e) => {
      const finishVal = dom.sliderFinish?.value ?? 1;
      setSpatialPositions(Number.parseFloat(e.target.value), Number.parseFloat(finishVal));
    });
  }

  if (dom.sliderFinish) {
    dom.sliderFinish.addEventListener("input", (e) => {
      const startVal = dom.sliderStart?.value ?? 0;
      setSpatialPositions(Number.parseFloat(startVal), Number.parseFloat(e.target.value));
    });
  }

  if (dom.inputStart) {
    const onStartChange = (e) => {
      const finishVal = dom.inputFinish?.value ?? 1;
      setSpatialPositions(Number.parseFloat(e.target.value || 0), Number.parseFloat(finishVal));
    };
    dom.inputStart.addEventListener("input", onStartChange);
    dom.inputStart.addEventListener("change", onStartChange);
  }

  if (dom.inputFinish) {
    const onFinishChange = (e) => {
      const startVal = dom.inputStart?.value ?? 0;
      setSpatialPositions(Number.parseFloat(startVal), Number.parseFloat(e.target.value || 1));
    };
    dom.inputFinish.addEventListener("input", onFinishChange);
    dom.inputFinish.addEventListener("change", onFinishChange);
  }
}

/**
 * Attach start mode card selectors and AC execution buttons listeners.
 */
function setupStartModeListeners() {
  dom.cardStanding?.addEventListener("click", handleCardStandingClick);
  dom.cardRolling?.addEventListener("click", handleCardRollingClick);
  dom.cardFlying?.addEventListener("click", handleCardFlyingClick);

  dom.btnStopAc?.addEventListener("click", () => {
    void cancelActiveACSession();
  });
}

/**
 * Attach DOM listeners for all test editor controls.
 */
/**
 * Setup sidebar collapse/expand toggle and restore state from localStorage.
 */
export function initSidebarCollapse() {
  if (!dom.sidebar || !dom.btnToggleSidebar) return;

  const updateSidebarState = (isCollapsed) => {
    if (isCollapsed) {
      dom.sidebar.classList.add("collapsed");
      dom.btnToggleSidebar.title = "Expand sidebar";
      dom.btnToggleSidebar.setAttribute("aria-label", "Expand sidebar");
      dom.btnAddTest?.setAttribute("title", "Add new test (+)");
    } else {
      dom.sidebar.classList.remove("collapsed");
      dom.btnToggleSidebar.title = "Collapse sidebar";
      dom.btnToggleSidebar.setAttribute("aria-label", "Collapse sidebar");
      dom.btnAddTest?.setAttribute("title", "Add new test to this license");
    }
  };

  const savedState = localStorage.getItem("gt_sidebar_collapsed") === "true";
  updateSidebarState(savedState);

  const toggleSidebar = () => {
    const willCollapse = !dom.sidebar.classList.contains("collapsed");
    updateSidebarState(willCollapse);
    try {
      localStorage.setItem("gt_sidebar_collapsed", willCollapse ? "true" : "false");
    } catch {
      // Ignore localStorage exceptions in restricted contexts
    }
  };

  window.toggleSidebar = toggleSidebar;
  dom.btnToggleSidebar.onclick = toggleSidebar;
}

export function setupEditorEventListeners() {
  initSidebarCollapse();

  setTrackCanvasPositionCallback((startS, finishS) => {
    setSpatialPositions(startS, finishS);
  });

  dom.btnAddTest?.addEventListener("click", handleAddTest);
  dom.btnDeleteTest?.addEventListener("click", () => {
    void handleDeleteTest();
  });

  setupSearchFilterListeners();
  setupDropdownChangeListeners();
  setupPositionControlListeners();
  setupStartModeListeners();

  [dom.targetGold, dom.targetSilver, dom.targetBronze].forEach((el) => {
    el?.addEventListener("input", validateTargets);
  });

  dom.form?.addEventListener("submit", (e) => {
    void handleFormSubmit(e);
  });

  if (dom.btnDownloadRecordScript) {
    dom.btnDownloadRecordScript.addEventListener("click", () => {
      executeExportSingleTelemetryScript();
    });
  }

  if (dom.telemetryDropzoneEditor && dom.inputEditorTelemetryFile) {
    dom.telemetryDropzoneEditor.addEventListener("click", () => {
      dom.inputEditorTelemetryFile.click();
    });

    const handleTelemetryFile = async (file) => {
      if (!file) return;
      try {
        const text = await file.text();
        const parsed = JSON.parse(text);
        await saveCustomTelemetryProfile(parsed);
        showToast(`Loaded telemetry for ${parsed.car_id || "car"} @ ${parsed.track_id || "track"}! Calculating targets...`, "success");
        await autoCalculateTargetsFromTelemetry();
      } catch (err) {
        showToast("Telemetry file error: " + err.message, "error");
      }
    };

    dom.inputEditorTelemetryFile.addEventListener("change", (e) => {
      const file = e.target.files?.[0];
      if (file) void handleTelemetryFile(file);
      dom.inputEditorTelemetryFile.value = "";
    });

    dom.telemetryDropzoneEditor.addEventListener("dragover", (e) => {
      e.preventDefault();
      dom.telemetryDropzoneEditor.style.borderColor = "#38bdf8";
      dom.telemetryDropzoneEditor.style.background = "rgba(56, 189, 248, 0.15)";
    });

    dom.telemetryDropzoneEditor.addEventListener("dragleave", () => {
      dom.telemetryDropzoneEditor.style.borderColor = "rgba(255, 255, 255, 0.25)";
      dom.telemetryDropzoneEditor.style.background = "rgba(0, 0, 0, 0.25)";
    });

    dom.telemetryDropzoneEditor.addEventListener("drop", (e) => {
      e.preventDefault();
      dom.telemetryDropzoneEditor.style.borderColor = "rgba(255, 255, 255, 0.25)";
      dom.telemetryDropzoneEditor.style.background = "rgba(0, 0, 0, 0.25)";
      const file = e.dataTransfer?.files?.[0];
      if (file) void handleTelemetryFile(file);
    });
  }
}
