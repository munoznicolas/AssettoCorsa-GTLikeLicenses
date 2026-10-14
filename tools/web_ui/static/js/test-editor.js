/**
 * test-editor.js
 * Test definition editor, form validation, license tabs, and curriculum catalog manager.
 */

import { state } from "./state.js";
import { dom } from "./dom.js";
import { api } from "./api.js";
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
  hideAISpeedStatus,
} from "./queue-runner.js";

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

    // 3. Fetch Curriculum
    const curData = await api.getCurriculum();
    if (curData.success) {
      state.curriculum = curData.curriculum;
      renderLicenseTabs();
      selectTier(0);
    }

    // 4. Fetch GT Reference Benchmark Tests
    try {
      const refData = await api.getReferenceTests();
      if (refData.success) {
        state.referenceTests = refData.tests;
        const refBadge = document.getElementById("ref-total-badge");
        if (refBadge) refBadge.textContent = refData.count || refData.tests.length;
      }
    } catch (err) {
      console.warn("Could not load reference benchmark tests:", err);
    }
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
  const query = dom.inputSearchTrack ? dom.inputSearchTrack.value.trim().toLowerCase() : "";
  const activeTrackId = selectedTrackId !== null ? selectedTrackId : dom.selectTrack.value;

  dom.selectTrack.innerHTML = '<option value="">Select Kunos Track...</option>';

  let matches = state.tracks;
  if (query) {
    matches = state.tracks.filter((t) => {
      const idMatch = (t.track_id || "").toLowerCase().includes(query);
      const nameMatch = (t.name || "").toLowerCase().includes(query);
      const layoutMatch = (t.layouts || []).some(
        (l) =>
          (l.name || "").toLowerCase().includes(query) ||
          (l.layout_id || "").toLowerCase().includes(query)
      );
      return idMatch || nameMatch || layoutMatch;
    });

    if (dom.trackFilterCount) {
      dom.trackFilterCount.style.display = "inline-block";
      dom.trackFilterCount.textContent = `${matches.length} / ${state.tracks.length}`;
      dom.trackFilterCount.classList.toggle("empty", matches.length === 0);
    }
    if (dom.btnClearTrackSearch) {
      dom.btnClearTrackSearch.style.display = "block";
    }
  } else {
    if (dom.trackFilterCount) dom.trackFilterCount.style.display = "none";
    if (dom.btnClearTrackSearch) dom.btnClearTrackSearch.style.display = "none";
  }

  matches.forEach((t) => {
    const opt = document.createElement("option");
    opt.value = t.track_id;
    opt.textContent = `${t.name} (${t.track_id})`;
    if (t.track_id === activeTrackId) {
      opt.selected = true;
    }
    dom.selectTrack.appendChild(opt);
  });

  if (activeTrackId && matches.some((t) => t.track_id === activeTrackId)) {
    dom.selectTrack.value = activeTrackId;
  } else if (!query && activeTrackId) {
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
  if (!track || !track.layouts || track.layouts.length === 0) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "Default Layout";
    dom.selectLayout.appendChild(opt);
    return;
  }

  track.layouts.forEach((l) => {
    const opt = document.createElement("option");
    opt.value = l.layout_id;
    opt.textContent = l.name || (l.layout_id ? l.layout_id : "Default Layout");
    if (l.layout_id === selectedLayout) {
      opt.selected = true;
    }
    dom.selectLayout.appendChild(opt);
  });
}

/**
 * Filter cars by text query and tags.
 */
export function filterCars(query) {
  if (!query) return state.cars;
  const tokens = query.toLowerCase().split(/\s+/).filter(Boolean);
  return state.cars.filter((c) => {
    const id = (c.car_id || "").toLowerCase();
    const name = (c.name || "").toLowerCase();
    const brand = (c.brand || "").toLowerCase();
    const dt = (c.drivetrain || "").toLowerCase();
    const tags = (c.tags || []).map((t) => String(t).toLowerCase());

    return tokens.every((tok) => {
      if (tok === "awd" || tok === "4wd") {
        return (
          dt === "awd" ||
          tags.includes("awd") ||
          tags.includes("4wd") ||
          tags.includes("mawd") ||
          tags.includes("fawd") ||
          id.includes(tok) ||
          name.includes(tok)
        );
      }
      if (tok === "fwd") {
        return (
          dt === "fwd" ||
          tags.includes("fwd") ||
          id.includes(tok) ||
          name.includes(tok)
        );
      }
      if (tok === "rwd") {
        return (
          dt === "rwd" ||
          tags.includes("rwd") ||
          id.includes(tok) ||
          name.includes(tok)
        );
      }
      return (
        id.includes(tok) ||
        name.includes(tok) ||
        brand.includes(tok) ||
        dt.includes(tok) ||
        tags.some((t) => t.includes(tok))
      );
    });
  });
}

/**
 * Populate car selection dropdown.
 */
export function populateCarDropdown(selectedCarId = null) {
  if (!dom.selectCar) return;
  const query = dom.inputSearchCar ? dom.inputSearchCar.value.trim() : "";
  const activeCarId = selectedCarId !== null ? selectedCarId : dom.selectCar.value;

  dom.selectCar.innerHTML = '<option value="">Select Kunos Car...</option>';

  let matches = filterCars(query);
  if (query) {
    if (dom.carFilterCount) {
      dom.carFilterCount.style.display = "inline-block";
      dom.carFilterCount.textContent = `${matches.length} / ${state.cars.length}`;
      dom.carFilterCount.classList.toggle("empty", matches.length === 0);
    }
    if (dom.btnClearCarSearch) {
      dom.btnClearCarSearch.style.display = "block";
    }
  } else {
    if (dom.carFilterCount) dom.carFilterCount.style.display = "none";
    if (dom.btnClearCarSearch) dom.btnClearCarSearch.style.display = "none";
  }

  matches.forEach((c) => {
    const opt = document.createElement("option");
    opt.value = c.car_id;
    const brandStr = c.brand ? ` (${c.brand})` : "";
    const dtStr = c.drivetrain ? ` [${c.drivetrain}]` : "";
    opt.textContent = `${c.name}${brandStr}${dtStr}`;
    if (c.car_id === activeCarId) {
      opt.selected = true;
    }
    dom.selectCar.appendChild(opt);
  });

  if (activeCarId && matches.some((c) => c.car_id === activeCarId)) {
    dom.selectCar.value = activeCarId;
  } else if (!query && activeCarId) {
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
      <img class="tab-badge-img" src="/assets/career_ui/${tier.badge_asset}" alt="${tier.name}">
      <span>${tier.tier_name}</span>
      <span class="tab-count">${tier.tests.length}</span>
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
    loadTestIntoForm(0);
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

    const modeClass = (test.start_mode || "standing").toLowerCase();
    const isFullLap = isFullLapTest(test);
    const lapTypeLabel = isFullLap ? "Full Lap" : "Sector";

    const previewUrl =
      test.preview_image ||
      (activeTier.folder
        ? `/content/career/${activeTier.folder}/event${idx + 1}/preview.png`
        : `/api/test_preview?test_id=${encodeURIComponent(test.test_id)}`);

    item.innerHTML = `
      <div class="test-item-thumb">
        <img src="${previewUrl}?t=${state.cacheBuster}" 
             alt="${test.test_id}" 
             loading="lazy" 
             onerror="this.parentElement.style.opacity='0.25'; this.style.display='none'">
      </div>
      <div class="test-item-body">
        <div class="test-item-top">
          <span class="test-item-id">${test.test_id}</span>
          <span class="test-item-mode ${modeClass}">${test.start_mode}</span>
        </div>
        <div class="test-item-title">${escapeHtml(test.title)}</div>
        <div class="test-item-meta">
          <span>🏁 ${lapTypeLabel}</span>
          <span>📍 ${escapeHtml(test.track_id)}</span>
          <span>🥇 ${test.targets ? test.targets.gold_seconds.toFixed(2) + "s" : ""}</span>
        </div>
      </div>
    `;

    item.addEventListener("click", () => {
      loadTestIntoForm(idx);
    });
    dom.testList.appendChild(item);
  });
}

/**
 * Determine if test is a full lap session.
 */
export function isFullLapTest(test) {
  const s0 = parseFloat(test.start_s || 0);
  const s1 = parseFloat(test.finish_s || 1);
  return (s0 <= 0.005 && s1 >= 0.99) || test.start_mode === "FLYING_LAP";
}

/**
 * Load test definition into editing form controls.
 */
export async function loadTestIntoForm(testIdx) {
  state.activeTestIndex = testIdx;
  const activeTier = state.curriculum[state.activeTierIndex];
  if (!activeTier || !activeTier.tests) return;
  const test = activeTier.tests[testIdx];
  if (!test) return;

  // Update list selection highlight
  document.querySelectorAll(".test-item").forEach((el, idx) => {
    el.classList.toggle("active", idx === testIdx);
  });

  // Populate Fields
  if (dom.formTestIdBadge) dom.formTestIdBadge.textContent = test.test_id;
  if (dom.inputTestId) dom.inputTestId.value = test.test_id;
  if (dom.inputTitle) dom.inputTitle.value = test.title || "";
  if (dom.inputObjective) dom.inputObjective.value = test.lesson_objective || "";
  if (dom.inputDescription) dom.inputDescription.value = test.description || "";

  // Reset search filters when loading a test
  if (dom.inputSearchTrack) dom.inputSearchTrack.value = "";
  if (dom.inputSearchCar) dom.inputSearchCar.value = "";
  populateTrackDropdown(test.track_id || "");
  populateLayoutDropdown(test.track_id || "", test.track_layout || "");
  populateCarDropdown(test.car_id || "");

  // Lap Mode & Positions
  const fullLap = isFullLapTest(test);
  if (dom.toggleFullLap) dom.toggleFullLap.checked = fullLap;
  updateFullLapState(fullLap);

  const startS = parseFloat(test.start_s || 0.0);
  const finishS = parseFloat(test.finish_s || 1.0);
  setSpatialPositions(startS, finishS);

  // Start Mode
  setStartMode(test.start_mode || "STANDING");
  if (dom.inputSpeed) dom.inputSpeed.value = test.speed !== undefined ? test.speed : (test.spawn ? test.spawn.initial_speed_kmh : 0);
  if (dom.inputSpawnOffset) dom.inputSpawnOffset.value = test.spawn_offset !== undefined ? test.spawn_offset : (test.spawn ? test.spawn.spawn_offset_m : 0);
  if (dom.inputGear) dom.inputGear.value = test.gear !== undefined ? test.gear : (test.spawn && test.spawn.initial_gear !== undefined ? test.spawn.initial_gear : "");
  if (dom.inputRpm) dom.inputRpm.value = test.rpm !== undefined ? test.rpm : (test.spawn && test.spawn.initial_rpm !== undefined ? test.spawn.initial_rpm : "");
  if (dom.checkStopBox) dom.checkStopBox.checked = Boolean(test.with_stop_box);

  // Targets
  const targets = test.targets || {
    gold_seconds: 10,
    silver_seconds: 12,
    bronze_seconds: 15,
  };
  if (dom.targetGold) dom.targetGold.value = targets.gold_seconds;
  if (dom.targetSilver) dom.targetSilver.value = targets.silver_seconds;
  if (dom.targetBronze) dom.targetBronze.value = targets.bronze_seconds;
  validateTargets();

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

  const totalLen = state.currentSpline ? state.currentSpline.total_length_m : 0;
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
}

/**
 * Validate that gold < silver < bronze.
 */
export function validateTargets() {
  if (!dom.targetGold || !dom.targetSilver || !dom.targetBronze) return true;
  const gold = parseFloat(dom.targetGold.value);
  const silver = parseFloat(dom.targetSilver.value);
  const bronze = parseFloat(dom.targetBronze.value);

  if (!isNaN(gold) && !isNaN(silver) && !isNaN(bronze)) {
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
  if (!tier || !tier.tests) return;
  const prefix = tier.test_prefix || "T-";
  tier.tests.forEach((t, i) => {
    const num = i + 1;
    t.test_id = `${prefix}${num}`;
    if (tier.folder) {
      t.preview_image = `/content/career/${tier.folder}/event${num}/preview.png`;
    }
  });
}

/**
 * Auto-calculate spawn run-up distance based on speed and 3-second countdown.
 */
export function autoCalculateSpawnOffset() {
  if (!dom.inputSpeed || !dom.inputSpawnOffset) return;
  const spdKmh = parseFloat(dom.inputSpeed.value) || 0;
  // Formula: spawn_offset = v_mps * 3.0 seconds
  const offset = (spdKmh / 3.6) * 3.0;
  dom.inputSpawnOffset.value = offset.toFixed(1);
}

/**
 * Persist current form inputs into the active in-memory test object.
 */
export function saveFormIntoActiveTest() {
  const activeTier = state.curriculum[state.activeTierIndex];
  if (!activeTier || !activeTier.tests) return;
  const test = activeTier.tests[state.activeTestIndex];
  if (!test) return;

  test.test_id = dom.inputTestId ? dom.inputTestId.value.trim() : test.test_id;
  test.title = dom.inputTitle ? dom.inputTitle.value.trim() : test.title;
  test.lesson_objective = dom.inputObjective ? dom.inputObjective.value.trim() : "";
  test.description = dom.inputDescription ? dom.inputDescription.value.trim() : "";
  test.car_id = dom.selectCar ? dom.selectCar.value : test.car_id;
  test.track_id = dom.selectTrack ? dom.selectTrack.value : test.track_id;
  test.track_layout = dom.selectLayout ? dom.selectLayout.value : "";

  test.start_s = parseFloat(dom.inputStart ? dom.inputStart.value : 0) || 0;
  test.finish_s = parseFloat(dom.inputFinish ? dom.inputFinish.value : 1) || 1;

  if (dom.radioStanding && dom.radioStanding.checked) {
    test.start_mode = "STANDING";
    test.speed = 0.0;
    test.spawn_offset = 0.0;
    test.with_stop_box = dom.checkStopBox ? dom.checkStopBox.checked : false;
  } else if (dom.radioRolling && dom.radioRolling.checked) {
    test.start_mode = "ROLLING";
    test.speed = parseFloat(dom.inputSpeed ? dom.inputSpeed.value : 75) || 75.0;
    test.spawn_offset = parseFloat(dom.inputSpawnOffset ? dom.inputSpawnOffset.value : 62.5) || 62.5;
    test.with_stop_box = false;
  } else {
    test.start_mode = "FLYING_LAP";
    test.speed = parseFloat(dom.inputSpeed ? dom.inputSpeed.value : 140) || 140.0;
    test.spawn_offset = parseFloat(dom.inputSpawnOffset ? dom.inputSpawnOffset.value : 60) || 60.0;
    test.with_stop_box = false;
  }

  test.spawn = test.spawn || {};
  test.spawn.initial_speed_kmh = test.speed;
  test.spawn.spawn_offset_m = test.spawn_offset;

  if (dom.inputGear && dom.inputGear.value) {
    test.gear = parseInt(dom.inputGear.value);
    test.spawn.initial_gear = parseInt(dom.inputGear.value);
  } else {
    delete test.gear;
    if (test.spawn) delete test.spawn.initial_gear;
  }

  if (dom.inputRpm && dom.inputRpm.value) {
    test.rpm = parseInt(dom.inputRpm.value);
    test.spawn.initial_rpm = parseInt(dom.inputRpm.value);
  } else {
    delete test.rpm;
    if (test.spawn) delete test.spawn.initial_rpm;
  }

  test.targets = {
    gold_seconds: parseFloat(dom.targetGold ? dom.targetGold.value : 10) || 10,
    silver_seconds: parseFloat(dom.targetSilver ? dom.targetSilver.value : 12) || 12,
    bronze_seconds: parseFloat(dom.targetBronze ? dom.targetBronze.value : 15) || 15,
  };
}

/**
 * Save active tier's test collection to server.
 */
export async function saveCurrentTier() {
  const activeTier = state.curriculum[state.activeTierIndex];
  if (!activeTier) return;
  const data = await api.saveTier(activeTier.tier_name, activeTier.tests);
  if (!data.success) {
    throw new Error(data.error || "Save failed");
  }
  return data;
}

/**
 * Attach DOM listeners for all test editor controls.
 */
export function setupEditorEventListeners() {
  // Wire canvas click position updates directly into setSpatialPositions
  setTrackCanvasPositionCallback((startS, finishS) => {
    setSpatialPositions(startS, finishS);
  });

  // Add Test
  if (dom.btnAddTest) {
    dom.btnAddTest.addEventListener("click", () => {
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
        car_id: state.cars[0] ? state.cars[0].car_id : "ks_mazda_miata",
        track_id: state.tracks[0] ? state.tracks[0].track_id : "ks_vallelunga",
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
        preview_image: `/content/career/${activeTier.folder}/event${count}/preview.png`,
      };

      activeTier.tests.push(newTest);
      renumberTierTests(activeTier);
      renderLicenseTabs();
      renderTestList();
      loadTestIntoForm(activeTier.tests.length - 1);
      showToast(`Added new test ${newTest.test_id}`);
    });
  }

  // Delete Test
  if (dom.btnDeleteTest) {
    dom.btnDeleteTest.addEventListener("click", async () => {
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

      try {
        await saveCurrentTier();
        renderLicenseTabs();
        renderTestList();
        loadTestIntoForm(newIdx);
        showToast(`Removed test ${deletedId}. Subsequent tests renumbered successfully.`);
      } catch (err) {
        showToast("Error saving after delete: " + err.message, "error");
      }
    });
  }

  // Track Search & Filter
  if (dom.inputSearchTrack) {
    dom.inputSearchTrack.addEventListener("input", () => {
      populateTrackDropdown();
    });

    dom.inputSearchTrack.addEventListener("keydown", async (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        const query = dom.inputSearchTrack.value.trim().toLowerCase();
        const matches = state.tracks.filter(
          (t) =>
            (t.track_id || "").toLowerCase().includes(query) ||
            (t.name || "").toLowerCase().includes(query)
        );
        if (matches.length > 0 && dom.selectTrack) {
          dom.selectTrack.value = matches[0].track_id;
          populateLayoutDropdown(dom.selectTrack.value, "");
          await fetchAndRenderSpline(dom.selectTrack.value, dom.selectLayout ? dom.selectLayout.value : "");
          dom.selectTrack.focus();
        }
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        if (dom.selectTrack) dom.selectTrack.focus();
      } else if (e.key === "Escape") {
        const currentVal = dom.selectTrack ? dom.selectTrack.value : "";
        dom.inputSearchTrack.value = "";
        populateTrackDropdown(currentVal);
      }
    });
  }

  if (dom.btnClearTrackSearch) {
    dom.btnClearTrackSearch.addEventListener("click", () => {
      const currentVal = dom.selectTrack ? dom.selectTrack.value : "";
      if (dom.inputSearchTrack) {
        dom.inputSearchTrack.value = "";
        populateTrackDropdown(currentVal);
        dom.inputSearchTrack.focus();
      }
    });
  }

  // Car Search & Filter
  if (dom.inputSearchCar) {
    dom.inputSearchCar.addEventListener("input", () => {
      populateCarDropdown();
    });

    dom.inputSearchCar.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        const matches = filterCars(dom.inputSearchCar.value.trim());
        if (matches.length > 0 && dom.selectCar) {
          dom.selectCar.value = matches[0].car_id;
          dom.selectCar.focus();
        }
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        if (dom.selectCar) dom.selectCar.focus();
      } else if (e.key === "Escape") {
        const currentVal = dom.selectCar ? dom.selectCar.value : "";
        dom.inputSearchCar.value = "";
        populateCarDropdown(currentVal);
      }
    });
  }

  if (dom.btnClearCarSearch) {
    dom.btnClearCarSearch.addEventListener("click", () => {
      const currentVal = dom.selectCar ? dom.selectCar.value : "";
      if (dom.inputSearchCar) {
        dom.inputSearchCar.value = "";
        populateCarDropdown(currentVal);
        dom.inputSearchCar.focus();
      }
    });
  }

  // Track & Layout change
  if (dom.selectTrack) {
    dom.selectTrack.addEventListener("change", async (e) => {
      const trackId = e.target.value;
      populateLayoutDropdown(trackId, "");
      await fetchAndRenderSpline(trackId, dom.selectLayout ? dom.selectLayout.value : "");
    });
  }

  if (dom.selectLayout) {
    dom.selectLayout.addEventListener("change", async (e) => {
      await fetchAndRenderSpline(dom.selectTrack ? dom.selectTrack.value : "", e.target.value);
    });
  }

  // Full Lap Toggle
  if (dom.toggleFullLap) {
    dom.toggleFullLap.addEventListener("change", (e) => {
      updateFullLapState(e.target.checked);
    });
  }

  // Sliders & Inputs sync
  if (dom.sliderStart) {
    dom.sliderStart.addEventListener("input", (e) => {
      setSpatialPositions(parseFloat(e.target.value), parseFloat(dom.sliderFinish ? dom.sliderFinish.value : 1));
    });
  }

  if (dom.sliderFinish) {
    dom.sliderFinish.addEventListener("input", (e) => {
      setSpatialPositions(parseFloat(dom.sliderStart ? dom.sliderStart.value : 0), parseFloat(e.target.value));
    });
  }

  if (dom.inputStart) {
    dom.inputStart.addEventListener("change", (e) => {
      setSpatialPositions(parseFloat(e.target.value || 0), parseFloat(dom.inputFinish ? dom.inputFinish.value : 1));
    });
  }

  if (dom.inputFinish) {
    dom.inputFinish.addEventListener("change", (e) => {
      setSpatialPositions(parseFloat(dom.inputStart ? dom.inputStart.value : 0), parseFloat(e.target.value || 1));
    });
  }

  // Start Mode Switchers
  if (dom.cardStanding) {
    dom.cardStanding.addEventListener("click", () => {
      setStartMode("STANDING");
      if (dom.inputSpeed) dom.inputSpeed.value = 0;
      if (dom.inputSpawnOffset) dom.inputSpawnOffset.value = 0;
      if (dom.inputGear) dom.inputGear.value = 1;
      if (dom.inputRpm) dom.inputRpm.value = 1000;
      hideAISpeedStatus();
    });
  }

  if (dom.cardRolling) {
    dom.cardRolling.addEventListener("click", () => {
      setStartMode("ROLLING");
      if (parseFloat(dom.inputSpeed ? dom.inputSpeed.value : 0) <= 0) {
        fetchAndApplyAISpeed(false);
      } else {
        autoCalculateSpawnOffset();
      }
    });
  }

  if (dom.cardFlying) {
    dom.cardFlying.addEventListener("click", () => {
      setStartMode("FLYING_LAP");
      if (parseFloat(dom.inputSpeed ? dom.inputSpeed.value : 0) <= 0) {
        fetchAndApplyAISpeed(false);
      } else {
        autoCalculateSpawnOffset();
      }
    });
  }

  if (dom.btnCalcSpeed) {
    dom.btnCalcSpeed.addEventListener("click", () => {
      fetchAndApplyAISpeed(true);
    });
  }

  if (dom.btnStopAc) dom.btnStopAc.addEventListener("click", cancelActiveACSession);
  if (dom.btnModalStopAc) dom.btnModalStopAc.addEventListener("click", cancelActiveACSession);

  if (dom.inputSpeed) {
    dom.inputSpeed.addEventListener("input", () => {
      if ((dom.radioRolling && dom.radioRolling.checked) || (dom.radioFlying && dom.radioFlying.checked)) {
        autoCalculateSpawnOffset();
      }
    });
  }

  // Targets Validation
  [dom.targetGold, dom.targetSilver, dom.targetBronze].forEach((el) => {
    if (el) el.addEventListener("input", validateTargets);
  });

  // Form Save
  if (dom.form) {
    dom.form.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!validateTargets()) {
        showToast("Please ensure Gold < Silver < Bronze targets.", "error");
        return;
      }

      saveFormIntoActiveTest();
      try {
        await saveCurrentTier();
        renderLicenseTabs();
        renderTestList();
        showToast(`Saved test ${dom.inputTestId ? dom.inputTestId.value : ""}!`);
      } catch (err) {
        showToast("Save failed: " + err.message, "error");
      }
    });
  }
}

