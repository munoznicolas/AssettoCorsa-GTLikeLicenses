/**
 * dom.js
 * Centralized DOM element references for Assetto Corsa GT-Like License Test Designer.
 */

export const dom = {};

export function initDom() {
  // Navigation & Workspace
  dom.tabsContainer = document.getElementById("license-tabs");
  dom.tabBtnReference = document.getElementById("tab-btn-reference");
  dom.workspaceView = document.querySelector(".workspace");
  dom.referenceView = document.getElementById("reference-view");

  // Reference View
  dom.gamePillsContainer = document.getElementById("game-selector-pills");
  dom.refSearchInput = document.getElementById("ref-search-input");
  dom.refTierSelect = document.getElementById("ref-tier-select");
  dom.refTableBody = document.getElementById("ref-table-body");

  // Tier & Test List
  dom.testList = document.getElementById("test-list");
  dom.tierTitle = document.getElementById("active-tier-title");
  dom.tierDesc = document.getElementById("active-tier-desc");
  dom.testCountBadge = document.getElementById("test-count-badge");
  dom.btnAddTest = document.getElementById("btn-add-test");
  dom.btnDeleteTest = document.getElementById("btn-delete-test");
  dom.btnSaveTest = document.getElementById("btn-save-test");
  dom.btnRunLive = document.getElementById("btn-run-live");
  dom.btnRunTop = document.getElementById("btn-run-top");
  dom.btnStopAc = document.getElementById("btn-stop-ac");
  dom.runQueueBadge = document.getElementById("run-queue-badge");
  dom.btnRebuild = document.getElementById("btn-rebuild");
  dom.btnSync = document.getElementById("btn-sync");

  // Run Modal Elements
  dom.runModal = document.getElementById("run-modal");
  dom.runModalTitle = document.getElementById("run-modal-title");
  dom.runModalDesc = document.getElementById("run-modal-desc");
  dom.runModalClose = document.getElementById("run-modal-close");
  dom.runModalCancel = document.getElementById("run-modal-cancel");
  dom.runModalActiveBanner = document.getElementById("run-modal-active-banner");
  dom.runModalActiveDesc = document.getElementById("run-modal-active-desc");
  dom.btnModalStopAc = document.getElementById("btn-modal-stop-ac");
  dom.runModalQueueSection = document.getElementById("run-modal-queue-section");
  dom.runModalQueueList = document.getElementById("run-modal-queue-list");
  dom.queueCountNum = document.getElementById("queue-count-num");
  dom.btnRunModePlay = document.getElementById("btn-run-mode-play");
  dom.btnRunModeAi = document.getElementById("btn-run-mode-ai");
  dom.checkRunSync = document.getElementById("check-run-sync");

  // Form Elements
  dom.form = document.getElementById("test-form");
  dom.formTestIdBadge = document.getElementById("form-test-id-badge");
  dom.inputTitle = document.getElementById("input-title");
  dom.inputTestId = document.getElementById("input-test-id");
  dom.inputObjective = document.getElementById("input-objective");
  dom.inputDescription = document.getElementById("input-description");
  dom.selectTrack = document.getElementById("select-track");
  dom.selectLayout = document.getElementById("select-layout");
  dom.selectCar = document.getElementById("select-car");
  dom.inputSearchTrack = document.getElementById("input-search-track");
  dom.btnClearTrackSearch = document.getElementById("btn-clear-track-search");
  dom.trackFilterCount = document.getElementById("track-filter-count");
  dom.inputSearchCar = document.getElementById("input-search-car");
  dom.btnClearCarSearch = document.getElementById("btn-clear-car-search");
  dom.carFilterCount = document.getElementById("car-filter-count");

  // Lap Bounds & Map Elements
  dom.toggleFullLap = document.getElementById("toggle-full-lap");
  dom.sliderStart = document.getElementById("slider-start-s");
  dom.sliderFinish = document.getElementById("slider-finish-s");
  dom.inputStart = document.getElementById("input-start-s");
  dom.inputFinish = document.getElementById("input-finish-s");
  dom.dispStartS = document.getElementById("disp-start-s");
  dom.dispFinishS = document.getElementById("disp-finish-s");
  dom.dispStartM = document.getElementById("disp-start-m");
  dom.dispFinishM = document.getElementById("disp-finish-m");
  dom.dispSectorDist = document.getElementById("disp-sector-dist");
  dom.trackCanvas = document.getElementById("track-canvas");
  dom.canvasLoading = document.getElementById("canvas-loading");
  dom.mapTrackInfo = document.getElementById("map-track-info");

  // Start Mode Elements
  dom.radioStanding = document.getElementById("radio-standing");
  dom.radioRolling = document.getElementById("radio-rolling");
  dom.radioFlying = document.getElementById("radio-flying");
  dom.cardStanding = document.getElementById("mode-card-standing");
  dom.cardRolling = document.getElementById("mode-card-rolling");
  dom.cardFlying = document.getElementById("mode-card-flying");
  dom.btnCalcSpeed = document.getElementById("btn-calc-ai-speed");
  dom.aiSpeedBadge = document.getElementById("ai-speed-status-badge");
  dom.aiSpeedText = document.getElementById("ai-speed-status-text");
  dom.checkStopBox = document.getElementById("check-stop-box");
  dom.stopBoxRow = document.getElementById("stop-box-row");

  // Target Elements
  dom.targetGold = document.getElementById("target-gold");
  dom.targetSilver = document.getElementById("target-silver");
  dom.targetBronze = document.getElementById("target-bronze");
  dom.targetError = document.getElementById("target-error");

  // Modal Elements
  dom.logModal = document.getElementById("log-modal");
  dom.modalTitle = document.getElementById("modal-title");
  dom.modalStatusBadge = document.getElementById("modal-status-badge");
  dom.modalLogText = document.getElementById("modal-log-text");
  dom.modalClose = document.getElementById("modal-close");
  dom.modalBtnOk = document.getElementById("modal-btn-ok");
  dom.toast = document.getElementById("toast");

  return dom;
}

