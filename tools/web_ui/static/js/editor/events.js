/**
 * editor/events.js
 * Action handlers and DOM event listener setup for the test editor.
 */

import { state } from "../state.js";
import { dom } from "../dom.js";
import { api } from "../api.js";
import { showToast } from "../ui-utils.js";
import {
  fetchAndRenderSpline,
  setTrackCanvasPositionCallback,
} from "../track-canvas.js";
import {
  fetchAndApplyAISpeed,
  cancelActiveACSession,
  hideAISpeedStatus,
} from "../queue-runner.js";
import {
  filterTracks,
  populateTrackDropdown,
  populateLayoutDropdown,
  filterCars,
  populateCarDropdown,
} from "./dropdowns.js";
import {
  renderLicenseTabs,
  renderTestList,
  renumberTierTests,
  setupTestListDragListeners,
} from "./sidebar.js";
import {
  loadTestIntoForm,
  setSpatialPositions,
  triggerAutoCalculateTargets,
  updateFullLapState,
  setStartMode,
  validateTargets,
  autoCalculateSpawnOffset,
  applyStandingMode,
  saveFormIntoActiveTest,
  saveCurrentTier,
} from "../test-editor.js";

/**
 * Action handler for adding a new test.
 */
export function handleAddTest() {
  const activeTier = state.curriculum[state.activeTierIndex];
  if (!activeTier) return;
  const count = activeTier.tests.length + 1;
  const prefix = activeTier.test_prefix || "T-";

  const newTest = {
    test_id: `${prefix}${count}`,
    previous_test_id: null,
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
    preview_image: `/content/career/${activeTier.folder}/event${count}/preview.png`,
  };

  activeTier.tests.push(newTest);
  renumberTierTests(activeTier);
  renderLicenseTabs();
  renderTestList();
  void loadTestIntoForm(activeTier.tests.length - 1);
  showToast(`Added new test ${newTest.test_id}`);
}

/**
 * Action handler for deleting the active test.
 */
export async function handleDeleteTest() {
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
    state.cacheBuster = Date.now();
    renderLicenseTabs();
    renderTestList();
    await loadTestIntoForm(newIdx);
    showToast(`Removed test ${deletedId}. Subsequent tests renumbered successfully.`);
  } catch (err) {
    showToast("Error saving after delete: " + err.message, "error");
  }
}

/**
 * Keydown handler for track search input.
 */
export async function handleTrackSearchKeydown(e) {
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
export function handleCarSearchKeydown(e) {
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
export function handleCardStandingClick() {
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
export function handleCardRollingClick() {
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
export function handleCardFlyingClick() {
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
export async function handleFormSubmit(e) {
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
    submitBtn.innerHTML = `<span>⏳ Saving & Building Miniature...</span>`;
  }

  try {
    await saveCurrentTier();

    // Fire off Track Miniature Builder for this particular test so it updates its image
    if (testId) {
      try {
        const minResult = await api.generateMiniature(testId, activeTest);
        if (minResult && !minResult.success) {
          console.warn("Track Miniature Builder reported warning:", minResult.error);
        }
      } catch (minErr) {
        console.warn("Track Miniature Builder network/execution warning:", minErr);
      }
    }

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
export function setupSearchFilterListeners() {
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
export function setupDropdownChangeListeners() {
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
export function setupPositionControlListeners() {
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
export function setupStartModeListeners() {
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
export function setupEditorEventListeners() {
  setTrackCanvasPositionCallback((startS, finishS) => {
    setSpatialPositions(startS, finishS);
  });

  setupTestListDragListeners();

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
}
