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
  };

  // DOM Elements
  const tabsContainer = document.getElementById("license-tabs");
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
    } catch (err) {
      console.error("Initialization failed:", err);
      showToast("Failed to load designer data: " + err.message, "error");
    }
  }

  function populateTrackDropdown() {
    selectTrack.innerHTML = '<option value="">Select Track...</option>';
    state.tracks.forEach(t => {
      const opt = document.createElement("option");
      opt.value = t.track_id;
      opt.textContent = `${t.name} (${t.track_id})`;
      selectTrack.appendChild(opt);
    });
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

  function populateCarDropdown() {
    selectCar.innerHTML = '<option value="">Select Car...</option>';
    state.cars.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.car_id;
      opt.textContent = c.name + (c.brand ? ` (${c.brand})` : "");
      selectCar.appendChild(opt);
    });
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

    // Update active tab styling
    document.querySelectorAll(".license-tab").forEach((tab, idx) => {
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

      item.innerHTML = `
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

    selectTrack.value = test.track_id || "";
    populateLayoutDropdown(test.track_id || "", test.track_layout || "");
    selectCar.value = test.car_id || "";

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
    selectTrack.value = "";
    selectLayout.innerHTML = "";
    selectCar.value = "";
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
      };

      activeTier.tests.push(newTest);
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

      activeTier.tests.splice(state.activeTestIndex, 1);
      const newIdx = Math.max(0, state.activeTestIndex - 1);

      // Save updated tier to server immediately
      try {
        await saveCurrentTier();
        renderLicenseTabs();
        renderTestList();
        loadTestIntoForm(newIdx);
        showToast(`Test ${test.test_id} removed and tier saved.`);
      } catch (err) {
        showToast("Error saving after delete: " + err.message, "error");
      }
    });

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
      openModal("Rebuilding Content & Validating...", "Running Content Generator and Curriculum Validator...");
      try {
        const res = await fetch("/api/generate", { method: "POST" });
        const report = await res.json();
        if (report.success) {
          modalStatusBadge.textContent = "PASSED - ZERO ERRORS";
          modalStatusBadge.className = "badge badge-lg";
          modalStatusBadge.style.color = "#10b981";
        } else {
          modalStatusBadge.textContent = `FAILED (${report.failed} files with errors)`;
          modalStatusBadge.className = "badge badge-lg";
          modalStatusBadge.style.color = "#ef4444";
        }

        let log = `Audited ${report.total_files} test files. Passed: ${report.passed}, Failed: ${report.failed}\n\n`;
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
          log += "All schema validations, 3D gate vectors, target times, and career links PASSED perfectly!";
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
});

