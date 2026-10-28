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

  // Sidebar & Navigation
  dom.sidebar = document.getElementById("sidebar") || document.querySelector(".sidebar");
  dom.btnToggleSidebar = document.getElementById("btn-toggle-sidebar");

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
  dom.btnExportJson = document.getElementById("btn-export-json");
  dom.btnImportJson = document.getElementById("btn-import-json");
  dom.inputImportJsonFile = document.getElementById("input-import-json-file");
  dom.btnResetDefaults = document.getElementById("btn-reset-defaults");

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

  // Missing Telemetry Batch Modal & Buttons
  dom.btnRunMissingTelemetry = document.getElementById("btn-run-missing-telemetry");
  dom.telemetryBatchModal = document.getElementById("telemetry-batch-modal");
  dom.telemetryModalClose = document.getElementById("telemetry-modal-close");
  dom.selectTelemetryTier = document.getElementById("select-telemetry-tier");
  dom.checkIncludeFlying = document.getElementById("check-include-flying");
  dom.telemetrySummaryText = document.getElementById("telemetry-summary-text");
  dom.telemetryCombosTableBody = document.getElementById("telemetry-combos-table-body");
  dom.telemetryQueueInfo = document.getElementById("telemetry-queue-info");
  dom.btnTelemetryCancel = document.getElementById("btn-telemetry-cancel");
  dom.btnTelemetryEnqueue = document.getElementById("btn-telemetry-enqueue");
  dom.btnTelemetryExportScript = document.getElementById("btn-telemetry-export-script");
  dom.btnExportSingleTelemetryScript = document.getElementById("btn-export-single-telemetry-script");
  dom.telemetryMissingCard = document.getElementById("telemetry-missing-card");
  dom.btnDownloadRecordScript = document.getElementById("btn-download-record-script");
  dom.telemetryDropzoneEditor = document.getElementById("telemetry-dropzone-editor");
  dom.inputEditorTelemetryFile = document.getElementById("input-editor-telemetry-file");

  // Tour & Onboarding Elements
  dom.btnTourHelp = document.getElementById("btn-tour-help");
  dom.modalTourWelcome = document.getElementById("modal-tour-welcome");
  dom.modalTourClose = document.getElementById("modal-tour-close");
  dom.btnStartTourEdit = document.getElementById("btn-start-tour-edit");
  dom.btnStartTourTelemetry = document.getElementById("btn-start-tour-telemetry");
  dom.btnSkipTour = document.getElementById("btn-skip-tour");

  return dom;
}
