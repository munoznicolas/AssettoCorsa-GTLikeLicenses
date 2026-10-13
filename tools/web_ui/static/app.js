/**
 * app.js
 * Assetto Corsa GT-Like License Test Designer - Client Application
 */

document.addEventListener("DOMContentLoaded", () => {
  // Application State
  const state = {
    curriculum: [],
    activeTierIndex: 0,
    activeTestIndex: 0,
    tracks: [],
    cars: [],
    currentSpline: null,
    isDirty: false,
    referenceTests: [],
    activeRefGame: "ALL",
    refCharts: {},
    isReferenceViewActive: false,
    cacheBuster: Date.now(),
  };

  // DOM Elements
  const tabsContainer = document.getElementById("license-tabs");
  const tabBtnReference = document.getElementById("tab-btn-reference");
  const workspaceView = document.querySelector(".workspace");
  const referenceView = document.getElementById("reference-view");
  const gamePillsContainer = document.getElementById("game-selector-pills");
  const refSearchInput = document.getElementById("ref-search-input");
  const refTierSelect = document.getElementById("ref-tier-select");
  const refTableBody = document.getElementById("ref-table-body");
  const testList = document.getElementById("test-list");
  const tierTitle = document.getElementById("active-tier-title");
  const tierDesc = document.getElementById("active-tier-desc");
  const testCountBadge = document.getElementById("test-count-badge");
  const btnAddTest = document.getElementById("btn-add-test");
  const btnDeleteTest = document.getElementById("btn-delete-test");
  const btnSaveTest = document.getElementById("btn-save-test");
  const btnRebuild = document.getElementById("btn-rebuild");
  const btnSync = document.getElementById("btn-sync");

  // Form Elements
  const form = document.getElementById("test-form");
  const formTestIdBadge = document.getElementById("form-test-id-badge");
  const inputTitle = document.getElementById("input-title");
  const inputTestId = document.getElementById("input-test-id");
  const inputObjective = document.getElementById("input-objective");
  const inputDescription = document.getElementById("input-description");
  const selectTrack = document.getElementById("select-track");
  const selectLayout = document.getElementById("select-layout");
  const selectCar = document.getElementById("select-car");
  const inputSearchTrack = document.getElementById("input-search-track");
  const btnClearTrackSearch = document.getElementById("btn-clear-track-search");
  const trackFilterCount = document.getElementById("track-filter-count");
  const inputSearchCar = document.getElementById("input-search-car");
  const btnClearCarSearch = document.getElementById("btn-clear-car-search");
  const carFilterCount = document.getElementById("car-filter-count");

  // Lap Bounds & Map Elements
  const toggleFullLap = document.getElementById("toggle-full-lap");
  const sliderStart = document.getElementById("slider-start-s");
  const sliderFinish = document.getElementById("slider-finish-s");
  const inputStart = document.getElementById("input-start-s");
  const inputFinish = document.getElementById("input-finish-s");
  const dispStartS = document.getElementById("disp-start-s");
  const dispFinishS = document.getElementById("disp-finish-s");
  const dispStartM = document.getElementById("disp-start-m");
  const dispFinishM = document.getElementById("disp-finish-m");
  const dispSectorDist = document.getElementById("disp-sector-dist");
  const trackCanvas = document.getElementById("track-canvas");
  const canvasLoading = document.getElementById("canvas-loading");
  const mapTrackInfo = document.getElementById("map-track-info");

  // Start Mode Elements
  const radioStanding = document.getElementById("radio-standing");
  const radioRolling = document.getElementById("radio-rolling");
  const radioFlying = document.getElementById("radio-flying");
  const cardStanding = document.getElementById("mode-card-standing");
  const cardRolling = document.getElementById("mode-card-rolling");
  const cardFlying = document.getElementById("mode-card-flying");
  const inputSpeed = document.getElementById("input-speed");
  const inputSpawnOffset = document.getElementById("input-spawn-offset");
  const inputGear = document.getElementById("input-gear");
  const inputRpm = document.getElementById("input-rpm");
  const checkStopBox = document.getElementById("check-stop-box");
  const stopBoxRow = document.getElementById("stop-box-row");

  // Target Elements
  const targetGold = document.getElementById("target-gold");
  const targetSilver = document.getElementById("target-silver");
  const targetBronze = document.getElementById("target-bronze");
  const targetError = document.getElementById("target-error");

  // Modal Elements
  const logModal = document.getElementById("log-modal");
  const modalTitle = document.getElementById("modal-title");
  const modalStatusBadge = document.getElementById("modal-status-badge");
  const modalLogText = document.getElementById("modal-log-text");
  const modalClose = document.getElementById("modal-close");
  const modalBtnOk = document.getElementById("modal-btn-ok");
  const toast = document.getElementById("toast");

  // Initialize
  init();

  async function init() {
    setupEventListeners();
    await loadInitialData();
  }

  function showToast(message, type = "success") {
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.style.display = "block";
    setTimeout(() => {
      toast.style.display = "none";
    }, 3500);
  }

  async function loadInitialData() {
    try {
      // 1. Fetch Tracks
      const trackRes = await fetch("/api/tracks");
      const trackData = await trackRes.json();
      if (trackData.success) {
        state.tracks = trackData.tracks;
        populateTrackDropdown();
      }

      // 2. Fetch Cars
      const carRes = await fetch("/api/cars");
      const carData = await carRes.json();
      if (carData.success) {
        state.cars = carData.cars;
        populateCarDropdown();
      }

      // 3. Fetch Curriculum
      const curRes = await fetch("/api/curriculum");
      const curData = await curRes.json();
      if (curData.success) {
        state.curriculum = curData.curriculum;
        renderLicenseTabs();
        selectTier(0);
      }

      // 4. Fetch GT Reference Benchmark Tests
      try {
        const refRes = await fetch("/api/reference_tests");
        const refData = await refRes.json();
        if (refData.success) {
          state.referenceTests = refData.tests;
          const refBadge = document.getElementById("ref-total-badge");
          if (refBadge) refBadge.textContent = refData.count || refData.tests.length;
          setupReferenceViewListeners();
        }
      } catch (err) {
        console.warn("Could not load reference benchmark tests:", err);
      }
    } catch (err) {
      console.error("Initialization failed:", err);
      showToast("Failed to load designer data: " + err.message, "error");
    }
  }

  function populateTrackDropdown(selectedTrackId = null) {
    const query = inputSearchTrack ? inputSearchTrack.value.trim().toLowerCase() : "";
    const activeTrackId = selectedTrackId !== null ? selectedTrackId : selectTrack.value;

    selectTrack.innerHTML = '<option value="">Select Kunos Track...</option>';

    let matches = state.tracks;
    if (query) {
      matches = state.tracks.filter(t => {
        const idMatch = (t.track_id || "").toLowerCase().includes(query);
        const nameMatch = (t.name || "").toLowerCase().includes(query);
        const layoutMatch = (t.layouts || []).some(l =>
          (l.name || "").toLowerCase().includes(query) || (l.layout_id || "").toLowerCase().includes(query)
        );
        return idMatch || nameMatch || layoutMatch;
      });

      if (trackFilterCount) {
        trackFilterCount.style.display = "inline-block";
        trackFilterCount.textContent = `${matches.length} / ${state.tracks.length}`;
        trackFilterCount.classList.toggle("empty", matches.length === 0);
      }
      if (btnClearTrackSearch) {
        btnClearTrackSearch.style.display = "block";
      }
    } else {
      if (trackFilterCount) trackFilterCount.style.display = "none";
      if (btnClearTrackSearch) btnClearTrackSearch.style.display = "none";
    }

    matches.forEach(t => {
      const opt = document.createElement("option");
      opt.value = t.track_id;
      opt.textContent = `${t.name} (${t.track_id})`;
      if (t.track_id === activeTrackId) {
        opt.selected = true;
      }
      selectTrack.appendChild(opt);
    });

    if (activeTrackId && matches.some(t => t.track_id === activeTrackId)) {
      selectTrack.value = activeTrackId;
    } else if (!query && activeTrackId) {
      selectTrack.value = activeTrackId;
    }
  }

  function populateLayoutDropdown(trackId, selectedLayout = "") {
    selectLayout.innerHTML = "";
    const track = state.tracks.find(t => t.track_id === trackId);
    if (!track || !track.layouts || track.layouts.length === 0) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "Default Layout";
      selectLayout.appendChild(opt);
      return;
    }

    track.layouts.forEach(l => {
      const opt = document.createElement("option");
      opt.value = l.layout_id;
      opt.textContent = l.name || (l.layout_id ? l.layout_id : "Default Layout");
      if (l.layout_id === selectedLayout) {
        opt.selected = true;
      }
      selectLayout.appendChild(opt);
    });
  }

  function filterCars(query) {
    if (!query) return state.cars;
    const tokens = query.toLowerCase().split(/\s+/).filter(Boolean);
    return state.cars.filter(c => {
      const id = (c.car_id || "").toLowerCase();
      const name = (c.name || "").toLowerCase();
      const brand = (c.brand || "").toLowerCase();
      const dt = (c.drivetrain || "").toLowerCase();
      const tags = (c.tags || []).map(t => String(t).toLowerCase());

      return tokens.every(tok => {
        if (tok === "awd" || tok === "4wd") {
          return dt === "awd" || tags.includes("awd") || tags.includes("4wd") || tags.includes("mawd") || tags.includes("fawd") || id.includes(tok) || name.includes(tok);
        }
        if (tok === "fwd") {
          return dt === "fwd" || tags.includes("fwd") || id.includes(tok) || name.includes(tok);
        }
        if (tok === "rwd") {
          return dt === "rwd" || tags.includes("rwd") || id.includes(tok) || name.includes(tok);
        }
        return id.includes(tok) || name.includes(tok) || brand.includes(tok) || dt.includes(tok) || tags.some(t => t.includes(tok));
      });
    });
  }

  function populateCarDropdown(selectedCarId = null) {
    const query = inputSearchCar ? inputSearchCar.value.trim() : "";
    const activeCarId = selectedCarId !== null ? selectedCarId : selectCar.value;

    selectCar.innerHTML = '<option value="">Select Kunos Car...</option>';

    let matches = filterCars(query);
    if (query) {
      if (carFilterCount) {
        carFilterCount.style.display = "inline-block";
        carFilterCount.textContent = `${matches.length} / ${state.cars.length}`;
        carFilterCount.classList.toggle("empty", matches.length === 0);
      }
      if (btnClearCarSearch) {
        btnClearCarSearch.style.display = "block";
      }
    } else {
      if (carFilterCount) carFilterCount.style.display = "none";
      if (btnClearCarSearch) btnClearCarSearch.style.display = "none";
    }

    matches.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.car_id;
      const brandStr = c.brand ? ` (${c.brand})` : "";
      const dtStr = c.drivetrain ? ` [${c.drivetrain}]` : "";
      opt.textContent = `${c.name}${brandStr}${dtStr}`;
      if (c.car_id === activeCarId) {
        opt.selected = true;
      }
      selectCar.appendChild(opt);
    });

    if (activeCarId && matches.some(c => c.car_id === activeCarId)) {
      selectCar.value = activeCarId;
    } else if (!query && activeCarId) {
      selectCar.value = activeCarId;
    }
  }

  // License Tabs
  function renderLicenseTabs() {
    tabsContainer.innerHTML = "";
    state.curriculum.forEach((tier, idx) => {
      const btn = document.createElement("button");
      btn.className = `license-tab ${idx === state.activeTierIndex ? "active" : ""}`;
      btn.innerHTML = `
        <img class="tab-badge-img" src="/assets/career_ui/${tier.badge_asset}" alt="${tier.name}">
        <span>${tier.tier_name}</span>
        <span class="tab-count">${tier.tests.length}</span>
      `;
      btn.addEventListener("click", () => selectTier(idx));
      tabsContainer.appendChild(btn);
    });
  }

  function selectTier(tierIdx) {
    state.activeTierIndex = tierIdx;
    state.activeTestIndex = 0;
    state.isReferenceViewActive = false;

    // Show workspace, hide reference view
    if (workspaceView) workspaceView.style.display = "flex";
    if (referenceView) referenceView.style.display = "none";
    if (tabBtnReference) tabBtnReference.classList.remove("active");

    // Update active tab styling
    document.querySelectorAll(".tab-container .license-tab").forEach((tab, idx) => {
      tab.classList.toggle("active", idx === tierIdx);
    });

    const activeTier = state.curriculum[tierIdx];
    tierTitle.textContent = activeTier.tier_name;
    tierDesc.textContent = activeTier.description;
    testCountBadge.textContent = `${activeTier.tests.length} Tests`;

    renderTestList();
    if (activeTier.tests.length > 0) {
      loadTestIntoForm(0);
    } else {
      clearForm();
    }
  }

  // Test List
  function renderTestList() {
    testList.innerHTML = "";
    const activeTier = state.curriculum[state.activeTierIndex];

    activeTier.tests.forEach((test, idx) => {
      const item = document.createElement("div");
      item.className = `test-item ${idx === state.activeTestIndex ? "active" : ""}`;

      const modeClass = test.start_mode.toLowerCase();
      const isFullLap = isFullLapTest(test);
      const lapTypeLabel = isFullLap ? "Full Lap" : "Sector";

      const previewUrl = test.preview_image || (activeTier.folder ? `/content/career/${activeTier.folder}/event${idx + 1}/preview.png` : `/api/test_preview?test_id=${encodeURIComponent(test.test_id)}`);

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
      testList.appendChild(item);
    });
  }

  function isFullLapTest(test) {
    const s0 = parseFloat(test.start_s || 0);
    const s1 = parseFloat(test.finish_s || 1);
    return (s0 <= 0.005 && s1 >= 0.99) || test.start_mode === "FLYING_LAP";
  }


  // Load Test Into Form
  async function loadTestIntoForm(testIdx) {
    state.activeTestIndex = testIdx;
    const activeTier = state.curriculum[state.activeTierIndex];
    const test = activeTier.tests[testIdx];
    if (!test) return;

    // Update list selection highlight
    document.querySelectorAll(".test-item").forEach((el, idx) => {
      el.classList.toggle("active", idx === testIdx);
    });

    // Populate Fields
    formTestIdBadge.textContent = test.test_id;
    inputTestId.value = test.test_id;
    inputTitle.value = test.title || "";
    inputObjective.value = test.lesson_objective || "";
    inputDescription.value = test.description || "";

    // Reset search filters when loading a test
    if (inputSearchTrack) inputSearchTrack.value = "";
    if (inputSearchCar) inputSearchCar.value = "";
    populateTrackDropdown(test.track_id || "");
    populateLayoutDropdown(test.track_id || "", test.track_layout || "");
    populateCarDropdown(test.car_id || "");

    // Lap Mode & Positions
    const fullLap = isFullLapTest(test);
    toggleFullLap.checked = fullLap;
    updateFullLapState(fullLap);

    const startS = parseFloat(test.start_s || 0.0);
    const finishS = parseFloat(test.finish_s || 1.0);
    setSpatialPositions(startS, finishS);

    // Start Mode
    setStartMode(test.start_mode || "STANDING");
    inputSpeed.value = test.speed !== undefined ? test.speed : 0;
    inputSpawnOffset.value = test.spawn_offset !== undefined ? test.spawn_offset : 0;
    inputGear.value = test.gear !== undefined ? test.gear : "";
    inputRpm.value = test.rpm !== undefined ? test.rpm : "";
    checkStopBox.checked = Boolean(test.with_stop_box);

    // Targets
    const targets = test.targets || { gold_seconds: 10, silver_seconds: 12, bronze_seconds: 15 };
    targetGold.value = targets.gold_seconds;
    targetSilver.value = targets.silver_seconds;
    targetBronze.value = targets.bronze_seconds;
    validateTargets();

    // Fetch spline & render map
    await fetchAndRenderSpline(test.track_id, test.track_layout || "");
  }

  function clearForm() {
    formTestIdBadge.textContent = "--";
    inputTestId.value = "";
    inputTitle.value = "";
    inputObjective.value = "";
    inputDescription.value = "";
    if (inputSearchTrack) inputSearchTrack.value = "";
    if (inputSearchCar) inputSearchCar.value = "";
    populateTrackDropdown("");
    selectLayout.innerHTML = "";
    populateCarDropdown("");
    setSpatialPositions(0, 1);
    setStartMode("STANDING");
    targetGold.value = "";
    targetSilver.value = "";
    targetBronze.value = "";
    state.currentSpline = null;
    drawEmptyCanvas();
  }

  function setSpatialPositions(startS, finishS) {
    startS = Math.max(0, Math.min(1, startS));
    finishS = Math.max(0, Math.min(1, finishS));

    sliderStart.value = startS;
    sliderFinish.value = finishS;
    inputStart.value = startS.toFixed(4);
    inputFinish.value = finishS.toFixed(4);

    dispStartS.textContent = (startS * 100).toFixed(2) + "%";
    dispFinishS.textContent = (finishS * 100).toFixed(2) + "%";

    const totalLen = state.currentSpline ? state.currentSpline.total_length_m : 0;
    const startM = Math.round(startS * totalLen);
    const finishM = Math.round(finishS * totalLen);
    let sectorDist = 0;
    if (finishS >= startS) {
      sectorDist = Math.round((finishS - startS) * totalLen);
    } else {
      sectorDist = Math.round((1.0 - startS + finishS) * totalLen);
    }

    dispStartM.textContent = startM + " m";
    dispFinishM.textContent = finishM + " m";
    dispSectorDist.textContent = sectorDist + " m";

    renderCanvasTrack();
  }

  function updateFullLapState(isFull) {
    sliderStart.disabled = isFull;
    sliderFinish.disabled = isFull;
    inputStart.disabled = isFull;
    inputFinish.disabled = isFull;

    if (isFull) {
      setSpatialPositions(0.000, 0.999);
    }
  }

  function setStartMode(mode) {
    radioStanding.checked = (mode === "STANDING");
    radioRolling.checked = (mode === "ROLLING");
    radioFlying.checked = (mode === "FLYING_LAP");

    cardStanding.classList.toggle("active", mode === "STANDING");
    cardRolling.classList.toggle("active", mode === "ROLLING");
    cardFlying.classList.toggle("active", mode === "FLYING_LAP");

    if (mode === "STANDING") {
      stopBoxRow.style.display = "block";
    } else {
      stopBoxRow.style.display = "none";
      checkStopBox.checked = false;
    }
  }

  function validateTargets() {
    const gold = parseFloat(targetGold.value);
    const silver = parseFloat(targetSilver.value);
    const bronze = parseFloat(targetBronze.value);

    if (!isNaN(gold) && !isNaN(silver) && !isNaN(bronze)) {
      if (gold >= silver || silver >= bronze) {
        targetError.style.display = "block";
        return false;
      }
    }
    targetError.style.display = "none";
    return true;
  }

  // Spline & Map Canvas
  async function fetchAndRenderSpline(trackId, layout) {
    if (!trackId) {
      state.currentSpline = null;
      mapTrackInfo.textContent = "No track selected";
      drawEmptyCanvas();
      return;
    }

    canvasLoading.style.display = "flex";
    try {
      const res = await fetch(`/api/spline?track_id=${encodeURIComponent(trackId)}&layout=${encodeURIComponent(layout)}`);
      const data = await res.json();
      if (data.success && data.spline) {
        state.currentSpline = data.spline;
        mapTrackInfo.textContent = `Length: ${data.spline.total_length_m.toLocaleString()} m | Points: ${data.spline.point_count}`;
        setSpatialPositions(parseFloat(inputStart.value || 0), parseFloat(inputFinish.value || 1));
      } else {
        state.currentSpline = null;
        mapTrackInfo.textContent = "AI spline not found for this track layout";
        drawEmptyCanvas();
      }
    } catch (e) {
      state.currentSpline = null;
      mapTrackInfo.textContent = "Error loading spline";
      drawEmptyCanvas();
    } finally {
      canvasLoading.style.display = "none";
    }
  }

  function drawEmptyCanvas() {
    const ctx = trackCanvas.getContext("2d");
    ctx.clearRect(0, 0, trackCanvas.width, trackCanvas.height);
    ctx.fillStyle = "#161b22";
    ctx.fillRect(0, 0, trackCanvas.width, trackCanvas.height);

    ctx.fillStyle = "#48566a";
    ctx.font = "14px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("Select a track with an AI spline to view 2D map", trackCanvas.width / 2, trackCanvas.height / 2);
  }

  function renderCanvasTrack() {
    if (!state.currentSpline || !state.currentSpline.points || state.currentSpline.points.length === 0) {
      drawEmptyCanvas();
      return;
    }

    const pts = state.currentSpline.points;
    const bounds = state.currentSpline.bounds;
    const ctx = trackCanvas.getContext("2d");
    const w = trackCanvas.width;
    const h = trackCanvas.height;

    ctx.clearRect(0, 0, w, h);

    // Coordinate transforms to fit canvas with padding
    const pad = 30;
    const bw = bounds.width || 1;
    const bh = bounds.height || 1;
    const scale = Math.min((w - pad * 2) / bw, (h - pad * 2) / bh);
    const ox = (w - bw * scale) / 2 - bounds.min_x * scale;
    const oy = (h - bh * scale) / 2 - bounds.min_y * scale;

    const toX = (wx) => wx * scale + ox;
    const toY = (wy) => wy * scale + oy;

    const startS = parseFloat(inputStart.value || 0);
    const finishS = parseFloat(inputFinish.value || 1);

    // 1. Draw base track line (dark road)
    ctx.lineWidth = 6;
    ctx.strokeStyle = "#27313f";
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.beginPath();
    ctx.moveTo(toX(pts[0].x), toY(pts[0].y));
    for (let i = 1; i < pts.length; i++) {
      ctx.lineTo(toX(pts[i].x), toY(pts[i].y));
    }
    ctx.stroke();

    // 2. Draw active sector (glowing gold)
    ctx.lineWidth = 4;
    ctx.strokeStyle = "#f59e0b";
    ctx.shadowColor = "rgba(245, 158, 11, 0.6)";
    ctx.shadowBlur = 8;
    ctx.beginPath();

    let started = false;
    for (let i = 0; i < pts.length; i++) {
      const s = pts[i].s;
      let inSector = false;
      if (finishS >= startS) {
        inSector = (s >= startS && s <= finishS);
      } else {
        // Sector wraps around 1.0 -> 0.0
        inSector = (s >= startS || s <= finishS);
      }

      if (inSector) {
        if (!started) {
          ctx.moveTo(toX(pts[i].x), toY(pts[i].y));
          started = true;
        } else {
          ctx.lineTo(toX(pts[i].x), toY(pts[i].y));
        }
      } else {
        started = false;
      }
    }
    ctx.stroke();
    ctx.shadowBlur = 0; // Reset shadow

    // 3. Find and Draw Start Gate Marker
    const startPt = findPointAtProgress(pts, startS);
    if (startPt) {
      drawMarker(ctx, toX(startPt.x), toY(startPt.y), "#10b981", "START");
    }

    // 4. Find and Draw Finish Gate Marker
    const finishPt = findPointAtProgress(pts, finishS);
    if (finishPt) {
      drawMarker(ctx, toX(finishPt.x), toY(finishPt.y), "#e11d48", "FINISH");
    }
  }

  function findPointAtProgress(pts, targetS) {
    if (!pts || pts.length === 0) return null;
    let closest = pts[0];
    let minDiff = Math.abs(pts[0].s - targetS);
    for (let i = 1; i < pts.length; i++) {
      const diff = Math.abs(pts[i].s - targetS);
      if (diff < minDiff) {
        minDiff = diff;
        closest = pts[i];
      }
    }
    return closest;
  }

  function drawMarker(ctx, x, y, color, label) {
    ctx.save();
    ctx.fillStyle = color;
    ctx.shadowColor = color;
    ctx.shadowBlur = 8;
    ctx.beginPath();
    ctx.arc(x, y, 7, 0, Math.PI * 2);
    ctx.fill();

    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 9px 'JetBrains Mono', monospace";
    ctx.textAlign = "center";
    ctx.fillText(label, x, y - 11);
    ctx.restore();
  }

  // Interactive Click on Canvas Track Map
  trackCanvas.addEventListener("click", (e) => {
    if (!state.currentSpline || toggleFullLap.checked) return;

    const rect = trackCanvas.getBoundingClientRect();
    const clickX = (e.clientX - rect.left) * (trackCanvas.width / rect.width);
    const clickY = (e.clientY - rect.top) * (trackCanvas.height / rect.height);

    const pts = state.currentSpline.points;
    const bounds = state.currentSpline.bounds;
    const pad = 30;
    const bw = bounds.width || 1;
    const bh = bounds.height || 1;
    const scale = Math.min((trackCanvas.width - pad * 2) / bw, (trackCanvas.height - pad * 2) / bh);
    const ox = (trackCanvas.width - bw * scale) / 2 - bounds.min_x * scale;
    const oy = (trackCanvas.height - bh * scale) / 2 - bounds.min_y * scale;

    // Find closest waypoint to mouse click
    let closestPt = null;
    let minDist = Infinity;
    for (let i = 0; i < pts.length; i++) {
      const px = pts[i].x * scale + ox;
      const py = pts[i].y * scale + oy;
      const d = Math.hypot(clickX - px, clickY - py);
      if (d < minDist) {
        minDist = d;
        closestPt = pts[i];
      }
    }

    if (closestPt && minDist < 40) {
      const s = closestPt.s;
      const curStart = parseFloat(inputStart.value || 0);
      const curFinish = parseFloat(inputFinish.value || 1);

      // If Shift key is held, set Finish. Otherwise set whichever gate is closer.
      if (e.shiftKey) {
        setSpatialPositions(curStart, s);
      } else {
        const distToStart = Math.abs(s - curStart);
        const distToFinish = Math.abs(s - curFinish);
        if (distToStart < distToFinish) {
          setSpatialPositions(s, curFinish);
        } else {
          setSpatialPositions(curStart, s);
        }
      }
    }
  });

  function renumberTierTests(tier) {
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

  // Event Listeners
  function setupEventListeners() {
    // Add Test
    btnAddTest.addEventListener("click", () => {
      const activeTier = state.curriculum[state.activeTierIndex];
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
        start_s: 0.1000,
        finish_s: 0.3000,
        spawn_offset: 58.3,
        speed: 70.0,
        gear: 2,
        rpm: 4500,
        with_stop_box: false,
        targets: { gold_seconds: 15.000, silver_seconds: 16.500, bronze_seconds: 18.500 },
        preview_image: `/content/career/${activeTier.folder}/event${count}/preview.png`,
      };

      activeTier.tests.push(newTest);
      renumberTierTests(activeTier);
      renderLicenseTabs();
      renderTestList();
      loadTestIntoForm(activeTier.tests.length - 1);
      showToast(`Added new test ${newTest.test_id}`);
    });

    // Delete Test
    btnDeleteTest.addEventListener("click", async () => {
      const activeTier = state.curriculum[state.activeTierIndex];
      if (activeTier.tests.length <= 1) {
        showToast("Cannot delete the only test in this license.", "error");
        return;
      }

      const test = activeTier.tests[state.activeTestIndex];
      if (!confirm(`Are you sure you want to remove test "${test.test_id}: ${test.title}"?`)) {
        return;
      }

      const deletedId = test.test_id;
      activeTier.tests.splice(state.activeTestIndex, 1);

      // Automatically renumber subsequent tests
      renumberTierTests(activeTier);

      const newIdx = Math.max(0, Math.min(state.activeTestIndex, activeTier.tests.length - 1));
      state.activeTestIndex = newIdx;

      // Save updated tier to server immediately
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

    // Track Search & Filter
    if (inputSearchTrack) {
      inputSearchTrack.addEventListener("input", () => {
        populateTrackDropdown();
      });

      inputSearchTrack.addEventListener("keydown", async (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          const query = inputSearchTrack.value.trim().toLowerCase();
          const matches = state.tracks.filter(t =>
            (t.track_id || "").toLowerCase().includes(query) ||
            (t.name || "").toLowerCase().includes(query)
          );
          if (matches.length > 0) {
            selectTrack.value = matches[0].track_id;
            populateLayoutDropdown(selectTrack.value, "");
            await fetchAndRenderSpline(selectTrack.value, selectLayout.value);
            selectTrack.focus();
          }
        } else if (e.key === "ArrowDown") {
          e.preventDefault();
          selectTrack.focus();
        } else if (e.key === "Escape") {
          const currentVal = selectTrack.value;
          inputSearchTrack.value = "";
          populateTrackDropdown(currentVal);
        }
      });
    }

    if (btnClearTrackSearch) {
      btnClearTrackSearch.addEventListener("click", () => {
        const currentVal = selectTrack.value;
        inputSearchTrack.value = "";
        populateTrackDropdown(currentVal);
        inputSearchTrack.focus();
      });
    }

    // Car Search & Filter
    if (inputSearchCar) {
      inputSearchCar.addEventListener("input", () => {
        populateCarDropdown();
      });

      inputSearchCar.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          const matches = filterCars(inputSearchCar.value.trim());
          if (matches.length > 0) {
            selectCar.value = matches[0].car_id;
            selectCar.focus();
          }
        } else if (e.key === "ArrowDown") {
          e.preventDefault();
          selectCar.focus();
        } else if (e.key === "Escape") {
          const currentVal = selectCar.value;
          inputSearchCar.value = "";
          populateCarDropdown(currentVal);
        }
      });
    }

    if (btnClearCarSearch) {
      btnClearCarSearch.addEventListener("click", () => {
        const currentVal = selectCar.value;
        inputSearchCar.value = "";
        populateCarDropdown(currentVal);
        inputSearchCar.focus();
      });
    }

    // Track & Layout change
    selectTrack.addEventListener("change", async (e) => {
      const trackId = e.target.value;
      populateLayoutDropdown(trackId, "");
      await fetchAndRenderSpline(trackId, selectLayout.value);
    });

    selectLayout.addEventListener("change", async (e) => {
      await fetchAndRenderSpline(selectTrack.value, e.target.value);
    });

    // Full Lap Toggle
    toggleFullLap.addEventListener("change", (e) => {
      updateFullLapState(e.target.checked);
    });

    // Sliders & Inputs sync
    sliderStart.addEventListener("input", (e) => {
      setSpatialPositions(parseFloat(e.target.value), parseFloat(sliderFinish.value));
    });

    sliderFinish.addEventListener("input", (e) => {
      setSpatialPositions(parseFloat(sliderStart.value), parseFloat(e.target.value));
    });

    inputStart.addEventListener("change", (e) => {
      setSpatialPositions(parseFloat(e.target.value || 0), parseFloat(inputFinish.value || 1));
    });

    inputFinish.addEventListener("change", (e) => {
      setSpatialPositions(parseFloat(inputStart.value || 0), parseFloat(e.target.value || 1));
    });

    // Start Mode Switchers
    cardStanding.addEventListener("click", () => {
      setStartMode("STANDING");
      inputSpeed.value = 0;
      inputSpawnOffset.value = 0;
    });

    cardRolling.addEventListener("click", () => {
      setStartMode("ROLLING");
      if (parseFloat(inputSpeed.value) <= 0) {
        inputSpeed.value = 75;
      }
      autoCalculateSpawnOffset();
    });

    cardFlying.addEventListener("click", () => {
      setStartMode("FLYING_LAP");
      if (parseFloat(inputSpeed.value) <= 0) {
        inputSpeed.value = 140;
      }
      if (parseFloat(inputSpawnOffset.value) <= 0) {
        inputSpawnOffset.value = 60;
      }
    });

    inputSpeed.addEventListener("input", () => {
      if (radioRolling.checked) {
        autoCalculateSpawnOffset();
      }
    });

    function autoCalculateSpawnOffset() {
      const spdKmh = parseFloat(inputSpeed.value) || 0;
      // Formula from GEMINI.md: spawn_offset = v_mps * 3.0 seconds
      const offset = (spdKmh / 3.6) * 3.0;
      inputSpawnOffset.value = offset.toFixed(1);
    }

    // Targets Validation
    [targetGold, targetSilver, targetBronze].forEach(el => {
      el.addEventListener("input", validateTargets);
    });

    // Form Save
    form.addEventListener("submit", async (e) => {
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
        showToast(`Saved test ${inputTestId.value}!`);
      } catch (err) {
        showToast("Save failed: " + err.message, "error");
      }
    });

    // Rebuild & Validate
    btnRebuild.addEventListener("click", async () => {
      openModal("Rebuilding Content & Validating...", "Running Content Generator, Track Miniature Builder, and Curriculum Validator...");
      try {
        const res = await fetch("/api/generate", { method: "POST" });
        const report = await res.json();
        if (report.success) {
          modalStatusBadge.textContent = "PASSED - ZERO ERRORS";
          modalStatusBadge.className = "badge badge-lg";
          modalStatusBadge.style.color = "#10b981";

          state.cacheBuster = Date.now();
          renderTestList();
        } else {
          modalStatusBadge.textContent = `FAILED (${report.failed} files with errors)`;
          modalStatusBadge.className = "badge badge-lg";
          modalStatusBadge.style.color = "#ef4444";
        }

        let log = "";
        if (report.miniatures_updated) {
          log += `✓ Successfully generated & updated ${report.miniatures_updated} track miniature previews (PNG) and maps (SVG).\n\n`;
        }
        log += `Audited ${report.total_files} test files. Passed: ${report.passed}, Failed: ${report.failed}\n\n`;
        if (report.errors && report.errors.length > 0) {
          log += "--- ERRORS ---\n";
          report.errors.forEach(e => {
            log += `[${e.severity}] [${e.test_id || "ALL"}] ${e.message}\n`;
          });
          log += "\n";
        }
        if (report.warnings && report.warnings.length > 0) {
          log += "--- WARNINGS ---\n";
          report.warnings.forEach(w => {
            log += `[${w.severity}] [${w.test_id || "ALL"}] ${w.message}\n`;
          });
        }
        if (!report.errors.length && !report.warnings.length) {
          log += "All schema validations, 3D gate vectors, track miniatures, and career links PASSED perfectly!";
        }
        modalLogText.textContent = log;
      } catch (err) {
        modalStatusBadge.textContent = "SERVER ERROR";
        modalLogText.textContent = "Error executing content generator: " + err.message;
      }
    });

    // Sync to AC
    btnSync.addEventListener("click", async () => {
      openModal("Sync to Assetto Corsa", "Synchronizing files to local Assetto Corsa directory...");
      try {
        const res = await fetch("/api/sync", { method: "POST" });
        const data = await res.json();
        if (data.success) {
          modalStatusBadge.textContent = "SYNC COMPLETE";
          modalStatusBadge.className = "badge badge-lg";
          modalStatusBadge.style.color = "#10b981";
          modalLogText.textContent = data.message;
        } else {
          modalStatusBadge.textContent = "SYNC FAILED";
          modalStatusBadge.className = "badge badge-lg";
          modalStatusBadge.style.color = "#ef4444";
          modalLogText.textContent = data.error;
        }
      } catch (err) {
        modalStatusBadge.textContent = "NETWORK ERROR";
        modalLogText.textContent = err.message;
      }
    });

    modalClose.addEventListener("click", () => logModal.style.display = "none");
    modalBtnOk.addEventListener("click", () => logModal.style.display = "none");
  }

  function saveFormIntoActiveTest() {
    const activeTier = state.curriculum[state.activeTierIndex];
    const test = activeTier.tests[state.activeTestIndex];
    if (!test) return;

    test.test_id = inputTestId.value.trim();
    test.title = inputTitle.value.trim();
    test.lesson_objective = inputObjective.value.trim();
    test.description = inputDescription.value.trim();
    test.car_id = selectCar.value;
    test.track_id = selectTrack.value;
    test.track_layout = selectLayout.value;

    test.start_s = parseFloat(inputStart.value || 0);
    test.finish_s = parseFloat(inputFinish.value || 1);

    if (radioStanding.checked) {
      test.start_mode = "STANDING";
      test.speed = 0.0;
      test.spawn_offset = 0.0;
      test.with_stop_box = checkStopBox.checked;
    } else if (radioRolling.checked) {
      test.start_mode = "ROLLING";
      test.speed = parseFloat(inputSpeed.value) || 75.0;
      test.spawn_offset = parseFloat(inputSpawnOffset.value) || 62.5;
      test.with_stop_box = false;
    } else {
      test.start_mode = "FLYING_LAP";
      test.speed = parseFloat(inputSpeed.value) || 140.0;
      test.spawn_offset = parseFloat(inputSpawnOffset.value) || 60.0;
      test.with_stop_box = false;
    }

    if (inputGear.value) test.gear = parseInt(inputGear.value);
    else delete test.gear;

    if (inputRpm.value) test.rpm = parseInt(inputRpm.value);
    else delete test.rpm;

    test.targets = {
      gold_seconds: parseFloat(targetGold.value),
      silver_seconds: parseFloat(targetSilver.value),
      bronze_seconds: parseFloat(targetBronze.value),
    };
  }

  async function saveCurrentTier() {
    const activeTier = state.curriculum[state.activeTierIndex];
    const res = await fetch("/api/save_tier", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tier_name: activeTier.tier_name,
        tests: activeTier.tests,
      }),
    });
    const data = await res.json();
    if (!data.success) {
      throw new Error(data.error || "Save failed");
    }
    return data;
  }

  function openModal(title, initialLog) {
    modalTitle.textContent = title;
    modalStatusBadge.textContent = "Processing...";
    modalStatusBadge.className = "badge badge-lg";
    modalStatusBadge.style.color = "#f59e0b";
    modalLogText.textContent = initialLog;
    logModal.style.display = "flex";
  }

  function escapeHtml(text) {
    if (!text) return "";
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  // =========================================================================
  // GT Reference & Constant Values View Implementation
  // =========================================================================

  function setupReferenceViewListeners() {
    if (tabBtnReference) {
      tabBtnReference.addEventListener("click", () => {
        openReferenceView();
      });
    }

    if (gamePillsContainer) {
      gamePillsContainer.querySelectorAll(".pill-btn").forEach(btn => {
        btn.addEventListener("click", () => {
          gamePillsContainer.querySelectorAll(".pill-btn").forEach(b => b.classList.remove("active"));
          btn.classList.add("active");
          state.activeRefGame = btn.getAttribute("data-game") || "ALL";
          populateRefTierDropdown();
          renderReferenceView();
        });
      });
    }

    if (refSearchInput) {
      refSearchInput.addEventListener("input", () => {
        renderRefTableOnly();
      });
    }

    if (refTierSelect) {
      refTierSelect.addEventListener("change", () => {
        renderRefTableOnly();
      });
    }
  }

  function openReferenceView() {
    state.isReferenceViewActive = true;
    if (workspaceView) workspaceView.style.display = "none";
    if (referenceView) referenceView.style.display = "flex";
    if (tabBtnReference) tabBtnReference.classList.add("active");

    // Remove active highlight from license tier tabs
    document.querySelectorAll(".tab-container .license-tab").forEach(tab => {
      tab.classList.remove("active");
    });

    populateRefTierDropdown();
    renderReferenceView();
  }

  function populateRefTierDropdown() {
    if (!refTierSelect) return;
    const currentVal = refTierSelect.value;
    refTierSelect.innerHTML = '<option value="ALL">All License Tiers</option>';

    let tests = state.referenceTests;
    if (state.activeRefGame !== "ALL") {
      tests = tests.filter(t => t.game === state.activeRefGame);
    }

    const uniqueTiers = Array.from(new Set(tests.map(t => t.license))).filter(Boolean);
    uniqueTiers.forEach(tier => {
      const opt = document.createElement("option");
      opt.value = tier;
      opt.textContent = tier;
      if (tier === currentVal) opt.selected = true;
      refTierSelect.appendChild(opt);
    });
  }

  function formatTimeDisplay(totalSeconds) {
    if (totalSeconds === null || totalSeconds === undefined || !isFinite(totalSeconds)) return "N/A";
    const mins = Math.floor(totalSeconds / 60);
    const secs = (totalSeconds % 60).toFixed(3);
    return `${mins}:${secs.padStart(6, "0")}`;
  }

  function getFilteredRefTests() {
    let list = state.referenceTests || [];
    if (state.activeRefGame !== "ALL") {
      list = list.filter(t => t.game === state.activeRefGame);
    }
    return list;
  }

  function renderReferenceView() {
    const list = getFilteredRefTests();

    // 1. Calculate & Render Summary Metrics
    renderReferenceMetrics(list);

    // 2. Render Charts
    renderReferenceCharts(list);

    // 3. Render Table
    renderRefTableOnly();
  }

  function renderReferenceMetrics(list) {
    const totalCount = list.length;
    let timedCount = 0;
    let totalSec = 0;
    let totalHp = 0;
    let hpCount = 0;
    let totalPw = 0;
    let pwCount = 0;
    const layoutCounts = {};

    list.forEach(t => {
      if (t.gold_seconds !== null && t.gold_seconds !== undefined && isFinite(t.gold_seconds)) {
        timedCount++;
        totalSec += t.gold_seconds;
      }
      if (t.hp) {
        totalHp += t.hp;
        hpCount++;
      }
      if (t.pw_kg_hp) {
        totalPw += t.pw_kg_hp;
        pwCount++;
      }
      const layout = t.drivetrain_layout || "FR";
      layoutCounts[layout] = (layoutCounts[layout] || 0) + 1;
    });

    const avgSec = timedCount > 0 ? totalSec / timedCount : 0;
    const avgHp = hpCount > 0 ? Math.round(totalHp / hpCount) : 0;
    const avgPw = pwCount > 0 ? (totalPw / pwCount).toFixed(2) : "N/A";

    // Format top layout breakdown string
    const sortedLayouts = Object.entries(layoutCounts)
      .sort((a, b) => b[1] - a[1])
      .map(([k, v]) => `${k}: ${v}`)
      .slice(0, 4)
      .join(" | ");

    const elTotalTests = document.getElementById("metric-total-tests");
    const elTotalGold = document.getElementById("metric-total-gold");
    const elAvgGold = document.getElementById("metric-avg-gold");
    const elAvgHp = document.getElementById("metric-avg-hp");
    const elAvgPw = document.getElementById("metric-avg-pw");
    const elLayouts = document.getElementById("metric-drivetrain-breakdown");

    if (elTotalTests) elTotalTests.textContent = totalCount;
    if (elTotalGold) elTotalGold.textContent = formatTimeDisplay(totalSec);
    if (elAvgGold) elAvgGold.textContent = formatTimeDisplay(avgSec);
    if (elAvgHp) elAvgHp.textContent = `${avgHp} HP`;
    if (elAvgPw) elAvgPw.textContent = `${avgPw} kg/hp`;
    if (elLayouts) elLayouts.textContent = sortedLayouts || "N/A";
  }

  function renderReferenceCharts(list) {
    if (typeof Chart === "undefined") {
      console.warn("Chart.js not loaded, retrying in 200ms...");
      setTimeout(() => renderReferenceCharts(list), 200);
      return;
    }

    const labels = list.map(t => state.activeRefGame === "ALL" ? `${t.game} ${t.code}` : t.code);
    const progressionNumbers = list.map((t, idx) => idx + 1);

    const baseChartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 400 },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#1e293b",
          titleColor: "#fff",
          bodyColor: "#cbd5e1",
          borderColor: "#334155",
          borderWidth: 1,
          padding: 10,
          titleFont: { family: "Chakra Petch", size: 12, weight: "bold" },
          bodyFont: { family: "Inter", size: 11 },
        }
      },
      scales: {
        x: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: {
            color: "#94a3b8",
            font: { family: "JetBrains Mono", size: 10 },
            maxRotation: 45,
            autoSkip: true,
            maxTicksLimit: 25,
          },
          title: {
            display: true,
            text: state.activeRefGame === "ALL" ? "Curriculum Progression (All GT Games)" : `${state.activeRefGame} Test Progression`,
            color: "#64748b",
            font: { family: "Chakra Petch", size: 11, weight: "bold" },
          }
        },
        y: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: {
            color: "#94a3b8",
            font: { family: "JetBrains Mono", size: 10 },
          }
        }
      }
    };

    // -------------------------------------------------------------------------
    // Chart 1: Power & Power-to-Weight Ratio vs Test Progression (Dual Y-Axis)
    // -------------------------------------------------------------------------
    const hpData = list.map(t => t.hp || 0);
    const pwData = list.map(t => t.pw_kg_hp || null);

    renderSingleChart("chart-power-pw", {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "HorsePower (HP)",
            data: hpData,
            yAxisID: "yHP",
            borderColor: "#ef4444",
            backgroundColor: "rgba(239, 68, 68, 0.08)",
            borderWidth: 2,
            fill: false,
            tension: 0.25,
            pointBackgroundColor: "#ef4444",
            pointRadius: list.length > 50 ? 2 : 3,
            pointHoverRadius: 6,
          },
          {
            label: "Power to Weight (kg/hp)",
            data: pwData,
            yAxisID: "yPW",
            borderColor: "#f59e0b",
            backgroundColor: "rgba(245, 158, 11, 0.08)",
            borderWidth: 2,
            borderDash: [4, 4],
            fill: false,
            tension: 0.25,
            pointBackgroundColor: "#f59e0b",
            pointRadius: list.length > 50 ? 2 : 3,
            pointHoverRadius: 6,
          }
        ]
      },
      options: {
        ...baseChartOptions,
        plugins: {
          ...baseChartOptions.plugins,
          legend: {
            display: true,
            position: "top",
            align: "end",
            labels: {
              color: "#cbd5e1",
              font: { family: "Chakra Petch", size: 10, weight: "bold" },
              boxWidth: 12,
              padding: 10
            }
          },
          tooltip: {
            ...baseChartOptions.plugins.tooltip,
            callbacks: {
              title: (items) => {
                const idx = items[0].dataIndex;
                const t = list[idx];
                return `${t.game} [${t.code}] - ${t.title || t.test}`;
              },
              afterTitle: (items) => {
                const t = list[items[0].dataIndex];
                return `🚗 ${t.car}`;
              },
              label: (item) => {
                if (item.datasetIndex === 0) {
                  return `⚡ Horsepower: ${item.parsed.y} HP`;
                } else {
                  return `⚖️ Power/Weight: ${item.parsed.y} kg/hp`;
                }
              }
            }
          }
        },
        scales: {
          ...baseChartOptions.scales,
          yHP: {
            type: "linear",
            display: true,
            position: "left",
            title: {
              display: true,
              text: "Horsepower (HP)",
              color: "#ef4444",
              font: { family: "Chakra Petch", size: 11, weight: "bold" }
            },
            ticks: {
              color: "#f87171",
              font: { family: "JetBrains Mono", size: 10 }
            },
            grid: { color: "rgba(255, 255, 255, 0.05)" }
          },
          yPW: {
            type: "linear",
            display: true,
            position: "right",
            title: {
              display: true,
              text: "P/W (kg/hp)",
              color: "#f59e0b",
              font: { family: "Chakra Petch", size: 11, weight: "bold" }
            },
            ticks: {
              color: "#fbbf24",
              font: { family: "JetBrains Mono", size: 10 }
            },
            grid: { drawOnChartArea: false }
          }
        }
      }
    });

    // -------------------------------------------------------------------------
    // Chart 2: Gold Medal Duration vs Test Progression
    // -------------------------------------------------------------------------
    const goldData = list.map(t => t.gold_seconds !== null && t.gold_seconds !== undefined ? t.gold_seconds : null);
    renderSingleChart("chart-gold", {
      type: "line",
      data: {
        labels: labels,
        datasets: [{
          label: "Gold Duration (sec)",
          data: goldData,
          borderColor: "#10b981",
          backgroundColor: "rgba(16, 185, 129, 0.12)",
          borderWidth: 2,
          fill: true,
          tension: 0.25,
          pointBackgroundColor: "#10b981",
          pointRadius: list.length > 50 ? 2 : 3,
          pointHoverRadius: 6,
        }]
      },
      options: {
        ...baseChartOptions,
        plugins: {
          ...baseChartOptions.plugins,
          tooltip: {
            ...baseChartOptions.plugins.tooltip,
            callbacks: {
              title: (items) => {
                const idx = items[0].dataIndex;
                const t = list[idx];
                return `${t.game} [${t.code}] - ${t.title || t.test}`;
              },
              label: (item) => {
                const t = list[item.dataIndex];
                return `🥇 Gold Target: ${t.gold} (${item.parsed.y}s) | Track: ${t.track}`;
              }
            }
          }
        },
        scales: {
          ...baseChartOptions.scales,
          y: {
            ...baseChartOptions.scales.y,
            title: { display: true, text: "Gold Target Duration (Seconds)", color: "#10b981", font: { family: "Chakra Petch", size: 11 } },
            ticks: {
              ...baseChartOptions.scales.y.ticks,
              callback: (val) => `${val}s`
            }
          }
        }
      }
    });

    // -------------------------------------------------------------------------
    // Chart 3: Distribution of Gold Times (Continuous Density Curve with P80 & P90)
    // -------------------------------------------------------------------------
    const timedTests = list.filter(t => t.gold_seconds !== null && t.gold_seconds !== undefined && isFinite(t.gold_seconds));
    const times = timedTests.map(t => t.gold_seconds);

    // Calculate 80th and 90th percentiles
    const sortedTimes = [...times].sort((a, b) => a - b);
    const getPercentile = (arr, p) => {
      if (!arr || arr.length === 0) return null;
      const idx = (arr.length - 1) * p;
      const lower = Math.floor(idx);
      const upper = Math.ceil(idx);
      const weight = idx - lower;
      return arr[lower] * (1 - weight) + arr[upper] * weight;
    };

    const p80 = getPercentile(sortedTimes, 0.80);
    const p90 = getPercentile(sortedTimes, 0.90);

    // Update header badges
    const badgeP80 = document.getElementById("badge-p80");
    const badgeP90 = document.getElementById("badge-p90");
    if (badgeP80) {
      badgeP80.textContent = p80 !== null ? `80th %ile: ${formatTimeDisplay(p80)}` : "P80: N/A";
    }
    if (badgeP90) {
      badgeP90.textContent = p90 !== null ? `90th %ile: ${formatTimeDisplay(p90)}` : "P90: N/A";
    }

    // Calculate time domain bounds for continuous curve
    const maxSecRaw = times.length > 0 ? Math.max(...times) : 60;
    const maxSec = Math.min(210, Math.ceil(maxSecRaw / 10) * 10);
    const step = 5; // 5-second sampling resolution
    const sigma = 4.0; // Gaussian kernel bandwidth

    const distLabels = [];
    const distDensity = [];
    const distNearbyTests = [];

    for (let s = 5; s <= maxSec; s += step) {
      distLabels.push(s < 60 ? `${s}s` : formatTimeDisplay(s));

      let density = 0;
      const nearby = [];

      times.forEach((t, i) => {
        const diff = (t - s) / sigma;
        density += Math.exp(-0.5 * diff * diff);
        if (Math.abs(t - s) <= (step / 2)) {
          nearby.push(timedTests[i]);
        }
      });

      distDensity.push(Number(density.toFixed(2)));
      distNearbyTests.push(nearby);
    }

    renderSingleChart("chart-gold-dist", {
      type: "line",
      data: {
        labels: distLabels,
        datasets: [{
          label: "Test Concentration Density",
          data: distDensity,
          borderColor: "#06b6d4",
          backgroundColor: "rgba(6, 182, 212, 0.16)",
          borderWidth: 2.5,
          fill: true,
          tension: 0.4, // Smooth cubic spline for continuous curve
          pointRadius: 0, // Clean continuous line
          pointHoverRadius: 6,
          pointBackgroundColor: "#22d3ee",
          pointBorderColor: "#fff",
          pointBorderWidth: 1.5,
        }]
      },
      plugins: [{
        id: "percentilesAnnotations",
        afterDraw(chart) {
          if (p80 === null && p90 === null) return;
          const { ctx, chartArea, scales } = chart;
          if (!chartArea || !scales || !scales.x) return;
          const { top, bottom, left, right } = chartArea;
          const xScale = scales.x;

          const getPixelForSec = (sec) => {
            const rawIdx = (sec - 5) / step;
            if (rawIdx < 0 || rawIdx > distLabels.length - 1) return null;
            return xScale.getPixelForValue(rawIdx);
          };

          const drawPercentileLine = (sec, label, color) => {
            if (sec === null || sec > maxSec) return;
            const px = getPixelForSec(sec);
            if (px === null || px < left || px > right) return;

            ctx.save();
            ctx.setLineDash([5, 4]);
            ctx.lineWidth = 1.5;
            ctx.strokeStyle = color;

            ctx.beginPath();
            ctx.moveTo(px, top + 22);
            ctx.lineTo(px, bottom);
            ctx.stroke();

            // Label badge at the top
            ctx.setLineDash([]);
            const text = `${label} (${formatTimeDisplay(sec)})`;
            ctx.font = "bold 10px 'JetBrains Mono', monospace";
            const textWidth = ctx.measureText(text).width;

            ctx.fillStyle = "rgba(15, 23, 42, 0.9)";
            ctx.fillRect(px - textWidth / 2 - 5, top + 4, textWidth + 10, 16);
            ctx.strokeStyle = color;
            ctx.strokeRect(px - textWidth / 2 - 5, top + 4, textWidth + 10, 16);

            ctx.fillStyle = color;
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(text, px, top + 12);
            ctx.restore();
          };

          drawPercentileLine(p80, "P80", "#fbbf24");
          drawPercentileLine(p90, "P90", "#f43f5e");
        }
      }],
      options: {
        ...baseChartOptions,
        plugins: {
          ...baseChartOptions.plugins,
          tooltip: {
            ...baseChartOptions.plugins.tooltip,
            callbacks: {
              title: (items) => `Target Duration: ~${distLabels[items[0].dataIndex]}`,
              label: (item) => {
                const nearby = distNearbyTests[item.dataIndex];
                const count = nearby ? nearby.length : 0;
                return `📊 Tests in ±2.5s window: ${count} (Density Score: ${item.parsed.y})`;
              },
              afterLabel: (item) => {
                const nearby = distNearbyTests[item.dataIndex];
                if (!nearby || nearby.length === 0) return "";
                const sample = nearby.slice(0, 5).map(t => `${t.code} (${t.gold})`).join(", ");
                const more = nearby.length > 5 ? ` +${nearby.length - 5} more` : "";
                return `Examples: ${sample}${more}`;
              }
            }
          }
        },
        scales: {
          ...baseChartOptions.scales,
          x: {
            ...baseChartOptions.scales.x,
            title: {
              display: true,
              text: "Gold Target Duration",
              color: "#06b6d4",
              font: { family: "Chakra Petch", size: 11, weight: "bold" }
            }
          },
          y: {
            ...baseChartOptions.scales.y,
            title: {
              display: true,
              text: "Relative Test Frequency / Density",
              color: "#64748b",
              font: { family: "Chakra Petch", size: 11, weight: "bold" }
            }
          }
        }
      }
    });

    // -------------------------------------------------------------------------
    // Chart 4: Car Drivetrain Layout vs Test Progression
    // -------------------------------------------------------------------------
    const LAYOUT_CATEGORIES = ["FF", "FR", "MR", "RR", "FAWD", "MAWD", "RAWD"];
    const layoutData = list.map(t => {
      const idx = LAYOUT_CATEGORIES.indexOf(t.drivetrain_layout);
      return idx >= 0 ? idx : 1; // Default to FR if missing
    });

    renderSingleChart("chart-drivetrain", {
      type: "line",
      data: {
        labels: labels,
        datasets: [{
          label: "Drivetrain Layout",
          data: layoutData,
          borderColor: "#8b5cf6",
          backgroundColor: "rgba(139, 92, 246, 0.12)",
          borderWidth: 2,
          stepped: "middle",
          fill: false,
          pointBackgroundColor: "#8b5cf6",
          pointRadius: list.length > 50 ? 3 : 4,
          pointHoverRadius: 7,
        }]
      },
      options: {
        ...baseChartOptions,
        plugins: {
          ...baseChartOptions.plugins,
          tooltip: {
            ...baseChartOptions.plugins.tooltip,
            callbacks: {
              title: (items) => {
                const idx = items[0].dataIndex;
                const t = list[idx];
                return `${t.game} [${t.code}] - ${t.title || t.test}`;
              },
              label: (item) => {
                const t = list[item.dataIndex];
                const cat = LAYOUT_CATEGORIES[item.parsed.y] || "Unknown";
                return `⚙️ Layout: ${cat} (Engine: ${t.engine}, Drivetrain: ${t.drivetrain}) | Car: ${t.car}`;
              }
            }
          }
        },
        scales: {
          ...baseChartOptions.scales,
          y: {
            ...baseChartOptions.scales.y,
            min: 0,
            max: LAYOUT_CATEGORIES.length - 1,
            title: { display: true, text: "Powertrain Layout Category", color: "#8b5cf6", font: { family: "Chakra Petch", size: 11 } },
            ticks: {
              ...baseChartOptions.scales.y.ticks,
              stepSize: 1,
              callback: (val) => LAYOUT_CATEGORIES[val] || ""
            }
          }
        }
      }
    });
  }

  function renderSingleChart(canvasId, config) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    if (state.refCharts[canvasId]) {
      state.refCharts[canvasId].destroy();
    }

    state.refCharts[canvasId] = new Chart(canvas, config);
  }

  function renderRefTableOnly() {
    if (!refTableBody) return;
    refTableBody.innerHTML = "";

    let list = getFilteredRefTests();

    // Apply Tier filter
    const selectedTier = refTierSelect ? refTierSelect.value : "ALL";
    if (selectedTier && selectedTier !== "ALL") {
      list = list.filter(t => t.license === selectedTier);
    }

    // Apply Search filter
    const searchVal = refSearchInput ? refSearchInput.value.trim().toLowerCase() : "";
    if (searchVal) {
      list = list.filter(t => {
        return (
          (t.code && t.code.toLowerCase().includes(searchVal)) ||
          (t.title && t.title.toLowerCase().includes(searchVal)) ||
          (t.car && t.car.toLowerCase().includes(searchVal)) ||
          (t.track && t.track.toLowerCase().includes(searchVal)) ||
          (t.drivetrain_layout && t.drivetrain_layout.toLowerCase().includes(searchVal)) ||
          (t.game && t.game.toLowerCase().includes(searchVal)) ||
          (t.license && t.license.toLowerCase().includes(searchVal))
        );
      });
    }

    const countLabel = document.getElementById("table-count-label");
    if (countLabel) countLabel.textContent = `${list.length} Tests`;

    if (list.length === 0) {
      refTableBody.innerHTML = `<tr><td colspan="12" style="text-align: center; color: var(--text-dim); padding: 30px;">No tests matching your filter criteria.</td></tr>`;
      return;
    }

    list.forEach(t => {
      const row = document.createElement("tr");
      const layoutClass = `layout-${t.drivetrain_layout || "FR"}`;
      const gameClass = t.game === "AC Mod" ? "tag-game tag-game-ac" : "tag-game";
      row.innerHTML = `
        <td><span class="tag-code">${escapeHtml(t.code)}</span></td>
        <td><span class="${gameClass}">${escapeHtml(t.game)}</span></td>
        <td>${escapeHtml(t.license)}</td>
        <td><strong>${escapeHtml(t.title || t.test)}</strong></td>
        <td>${escapeHtml(t.car)}</td>
        <td><span class="tag-hp">${t.hp ? t.hp + ' HP' : 'N/A'}</span></td>
        <td><span class="tag-pw">${t.pw_kg_hp ? t.pw_kg_hp : 'N/A'}</span></td>
        <td><span class="tag-layout ${layoutClass}">${escapeHtml(t.drivetrain_layout || 'FR')}</span></td>
        <td>${escapeHtml(t.track)}</td>
        <td style="color: #fbbf24; font-family: var(--font-mono); font-weight: 600;">${escapeHtml(t.gold)}</td>
        <td style="color: #cbd5e1; font-family: var(--font-mono);">${escapeHtml(t.silver)}</td>
        <td style="color: #d97706; font-family: var(--font-mono);">${escapeHtml(t.bronze)}</td>
      `;
      refTableBody.appendChild(row);
    });
  }
});

