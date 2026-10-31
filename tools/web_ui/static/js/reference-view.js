/**
 * reference-view.js
 * Gran Turismo curriculum reference comparison, analytics, and Chart.js visualizations.
 */

import { state } from "./state.js";
import { dom } from "./dom.js";
import { formatTimeDisplay, escapeHtml } from "./ui-utils.js";

/**
 * Register event listeners for reference view tabs, filter pills, search input, and tier dropdown.
 */
export function setupReferenceViewListeners() {
  if (dom.tabBtnReference) {
    dom.tabBtnReference.addEventListener("click", () => {
      openReferenceView();
    });
  }

  if (dom.gamePillsContainer) {
    dom.gamePillsContainer.querySelectorAll(".pill-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        dom.gamePillsContainer
          .querySelectorAll(".pill-btn")
          .forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.activeRefGame = btn.getAttribute("data-game") || "ALL";
        populateRefTierDropdown();
        renderReferenceView();
      });
    });
  }

  // Toggle gold medal scale focus mode (for individual tests)
  const btnToggleScale = document.getElementById("btn-toggle-gold-scale");
  if (btnToggleScale) {
    btnToggleScale.addEventListener("click", () => {
      state.goldScaleFocus = !state.goldScaleFocus;
      btnToggleScale.classList.toggle("active", state.goldScaleFocus);
      btnToggleScale.textContent = state.goldScaleFocus ? "Focus ≤3m" : "Full Scale";
      const list = getFilteredRefTests();
      renderGoldChart(list);
    });
  }

  // Toggle license tier aggregation vs individual test data points
  const handleToggleAggregation = () => {
    state.refChartsAggregateByLicense = !state.refChartsAggregateByLicense;
    updateAggregationUiControls();
    const list = getFilteredRefTests();
    renderPowerChart(list);
    renderGoldChart(list);
  };

  const btnTogglePowerAgg = document.getElementById("btn-toggle-power-agg");
  if (btnTogglePowerAgg) {
    btnTogglePowerAgg.addEventListener("click", handleToggleAggregation);
  }

  const btnToggleGoldAgg = document.getElementById("btn-toggle-gold-agg");
  if (btnToggleGoldAgg) {
    btnToggleGoldAgg.addEventListener("click", handleToggleAggregation);
  }

  // Interactive dataset toggle for Chart 1 (HP vs kg/hp)
  const badgeHp = document.getElementById("badge-toggle-hp");
  if (badgeHp) {
    badgeHp.addEventListener("click", () => {
      const chart = state.refCharts["chart-power-pw"];
      if (chart) {
        const isVisible = chart.isDatasetVisible(0);
        chart.setDatasetVisibility(0, !isVisible);
        chart.update();
        badgeHp.classList.toggle("dimmed", isVisible);
      }
    });
  }

  const badgePw = document.getElementById("badge-toggle-pw");
  if (badgePw) {
    badgePw.addEventListener("click", () => {
      const chart = state.refCharts["chart-power-pw"];
      if (chart) {
        const isVisible = chart.isDatasetVisible(1);
        chart.setDatasetVisibility(1, !isVisible);
        chart.update();
        badgePw.classList.toggle("dimmed", isVisible);
      }
    });
  }

  if (dom.refSearchInput) {
    dom.refSearchInput.addEventListener("input", () => {
      renderRefTableOnly();
    });
  }

  if (dom.refTierSelect) {
    dom.refTierSelect.addEventListener("change", () => {
      renderRefTableOnly();
    });
  }

  window.addEventListener("themechange", () => {
    if (state.isReferenceViewActive) {
      renderReferenceView();
    }
  });

  let refResizeTimer = null;
  window.addEventListener("resize", () => {
    if (state.isReferenceViewActive) {
      clearTimeout(refResizeTimer);
      refResizeTimer = setTimeout(() => {
        const list = getFilteredRefTests();
        updateAggregationUiControls();
        renderPowerChart(list);
        renderGoldChart(list);
      }, 150);
    }
  });
}

/**
 * Open the Gran Turismo reference comparison view and hide the test editor workspace.
 */
export function openReferenceView() {
  state.isReferenceViewActive = true;
  if (dom.workspaceView) dom.workspaceView.style.display = "none";
  if (dom.referenceView) dom.referenceView.style.display = "flex";
  if (dom.tabBtnReference) dom.tabBtnReference.classList.add("active");

  // Remove active highlight from license tier tabs
  document.querySelectorAll(".tab-container .license-tab").forEach((tab) => {
    tab.classList.remove("active");
  });

  populateRefTierDropdown();
  renderReferenceView();
}

/**
 * Populate license tier filter dropdown for reference view.
 */
export function populateRefTierDropdown() {
  if (!dom.refTierSelect) return;
  const currentVal = dom.refTierSelect.value;
  dom.refTierSelect.innerHTML = '<option value="ALL">All License Tiers</option>';

  let tests = state.referenceTests;
  if (state.activeRefGame !== "ALL") {
    tests = tests.filter((t) => t.game === state.activeRefGame);
  }

  const uniqueTiers = Array.from(new Set(tests.map((t) => t.license))).filter(Boolean);
  uniqueTiers.forEach((tier) => {
    const opt = document.createElement("option");
    opt.value = tier;
    opt.textContent = tier;
    if (tier === currentVal) opt.selected = true;
    dom.refTierSelect.appendChild(opt);
  });
}

/**
 * Filter reference tests by selected Gran Turismo release.
 */
export function getFilteredRefTests() {
  let list = state.referenceTests || [];
  if (state.activeRefGame !== "ALL") {
    list = list.filter((t) => t.game === state.activeRefGame);
  }
  return list;
}

/**
 * Helper to normalize drivetrain layout codes.
 */
function normalizeLayout(raw) {
  if (!raw) return "FR";
  const up = raw.toUpperCase().trim();
  if (up === "FAWD" || up === "MAWD" || up === "RAWD" || up === "AWD") return "4WD";
  return up;
}

/**
 * Render all metrics cards, Chart.js plots, and data table.
 */
export function renderReferenceView() {
  const list = getFilteredRefTests();
  renderReferenceMetrics(list);
  renderReferenceCharts(list);
  renderRefTableOnly();
}

/**
 * Calculate and update summary KPI metric cards.
 */
export function renderReferenceMetrics(list) {
  const totalCount = list.length;
  let timedCount = 0;
  let totalSec = 0;
  let totalHp = 0;
  let hpCount = 0;
  let totalPw = 0;
  let pwCount = 0;
  const layoutCounts = {};

  list.forEach((t) => {
    if (
      t.gold_seconds !== null &&
      t.gold_seconds !== undefined &&
      isFinite(t.gold_seconds)
    ) {
      timedCount++;
      totalSec += t.gold_seconds;
    }
    if (t.hp && t.hp > 0) {
      totalHp += t.hp;
      hpCount++;
    }
    if (t.pw_kg_hp && t.pw_kg_hp > 0) {
      totalPw += t.pw_kg_hp;
      pwCount++;
    }
    const layout = normalizeLayout(t.drivetrain_layout);
    layoutCounts[layout] = (layoutCounts[layout] || 0) + 1;
  });

  const avgSec = timedCount > 0 ? totalSec / timedCount : 0;
  const avgHp = hpCount > 0 ? Math.round(totalHp / hpCount) : 0;
  const avgPw = pwCount > 0 ? (totalPw / pwCount).toFixed(2) : "N/A";

  // Top layout breakdown formatted into responsive tags
  const sortedLayouts = Object.entries(layoutCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4);

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

  if (elLayouts) {
    if (sortedLayouts.length === 0) {
      elLayouts.innerHTML = '<span class="dt-chip"><span class="dt-chip-name">N/A</span></span>';
    } else {
      elLayouts.innerHTML = sortedLayouts
        .map(([k, v]) => {
          const chipClass = `dt-${k.toLowerCase()}`;
          return `<span class="dt-chip ${chipClass}" title="${escapeHtml(k)}: ${v} tests"><span class="dt-chip-name">${escapeHtml(k)}</span> <span class="dt-chip-val">${v}</span></span>`;
        })
        .join("");
    }
  }
}

/**
 * Shared palette and options generator for Chart.js.
 */
function getSharedChartContext() {
  const cs = getComputedStyle(document.documentElement);
  const textColor = cs.getPropertyValue("--text-muted").trim() || "#8b9bb4";
  const titleColor = cs.getPropertyValue("--text-dim").trim() || "#5c687a";
  const gridColor = cs.getPropertyValue("--border-subtle").trim() || "rgba(255, 255, 255, 0.05)";
  const tooltipBg = cs.getPropertyValue("--bg-panel").trim() || "#1e293b";
  const tooltipText = cs.getPropertyValue("--text-main").trim() || "#ffffff";
  const tooltipBorder = cs.getPropertyValue("--border-color").trim() || "#334155";

  const baseChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 300 },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: tooltipBg,
        titleColor: tooltipText,
        bodyColor: textColor,
        borderColor: tooltipBorder,
        borderWidth: 1,
        padding: 10,
        titleFont: { family: "Chakra Petch", size: 12, weight: "bold" },
        bodyFont: { family: "Inter", size: 11 },
      },
    },
    scales: {
      x: {
        grid: { color: gridColor },
        ticks: {
          color: textColor,
          font: { family: "JetBrains Mono", size: 10 },
          maxRotation: 45,
          autoSkip: true,
          maxTicksLimit: 14,
        },
        title: {
          display: true,
          text:
            state.activeRefGame === "ALL"
              ? "Curriculum Progression (All GT Games)"
              : `${state.activeRefGame} Test Progression`,
          color: titleColor,
          font: { family: "Chakra Petch", size: 11, weight: "bold" },
        },
      },
    },
  };

  return { textColor, titleColor, gridColor, tooltipBg, tooltipText, tooltipBorder, baseChartOptions };
}

/**
 * Helper to produce clean abbreviated license names for X-axis labels.
 */
function formatShortLicense(lic) {
  if (!lic) return "";
  return lic
    .replace("-License", "")
    .replace(" License", "")
    .replace("National ", "Nat ")
    .replace("International ", "Int ")
    .replace("Master National ", "M-Nat ")
    .replace("Master International ", "M-Int ")
    .replace("Master Super", "M-Super");
}

/**
 * Determine if current viewport matches mobile screen breakpoint (<= 768px).
 */
export function isMobileChartViewport() {
  return typeof window !== "undefined" && window.innerWidth <= 768;
}

/**
 * Determine if reference charts should group by game release (mobile view with ALL games selected).
 */
export function shouldShowPerGameChart(activeGame = state.activeRefGame) {
  const isAgg = state.refChartsAggregateByLicense !== false;
  return isAgg && (activeGame === "ALL" || !activeGame);
}

/**
 * Aggregate reference tests grouped per game release for compact mobile visualization.
 */
export function aggregateTestsByGame(list) {
  const groupsMap = new Map();
  const GAME_ORDER = ["GT1", "GT2", "GT3", "GT4", "GT5", "GT6", "GT7", "AC Mod"];

  for (const game of GAME_ORDER) {
    groupsMap.set(game, {
      game,
      tests: [],
    });
  }

  for (const t of list) {
    const game = t.game || "GT";
    if (!groupsMap.has(game)) {
      groupsMap.set(game, {
        game,
        tests: [],
      });
    }
    groupsMap.get(game).tests.push(t);
  }

  const aggregates = [];
  for (const [game, grp] of groupsMap.entries()) {
    const tests = grp.tests;
    if (!tests || tests.length === 0) continue;

    const validHp = tests.filter((t) => t.hp && t.hp > 0);
    const avgHp =
      validHp.length > 0
        ? Math.round(validHp.reduce((sum, t) => sum + t.hp, 0) / validHp.length)
        : null;

    const validPw = tests.filter((t) => t.pw_kg_hp && t.pw_kg_hp > 0);
    const avgPw =
      validPw.length > 0
        ? parseFloat((validPw.reduce((sum, t) => sum + t.pw_kg_hp, 0) / validPw.length).toFixed(2))
        : null;

    const validGold = tests.filter(
      (t) => t.gold_seconds !== null && t.gold_seconds !== undefined && isFinite(t.gold_seconds)
    );
    const avgDuration =
      validGold.length > 0
        ? parseFloat((validGold.reduce((sum, t) => sum + t.gold_seconds, 0) / validGold.length).toFixed(2))
        : null;

    const minHp = validHp.length > 0 ? Math.min(...validHp.map((t) => t.hp)) : null;
    const maxHp = validHp.length > 0 ? Math.max(...validHp.map((t) => t.hp)) : null;

    const minPw = validPw.length > 0 ? Math.min(...validPw.map((t) => t.pw_kg_hp)).toFixed(2) : null;
    const maxPw = validPw.length > 0 ? Math.max(...validPw.map((t) => t.pw_kg_hp)).toFixed(2) : null;

    const minGold = validGold.length > 0 ? Math.min(...validGold.map((t) => t.gold_seconds)) : null;
    const maxGold = validGold.length > 0 ? Math.max(...validGold.map((t) => t.gold_seconds)) : null;

    const carList = Array.from(new Set(tests.map((t) => t.car).filter(Boolean)));
    const licenseList = Array.from(new Set(tests.map((t) => t.license).filter(Boolean)));

    aggregates.push({
      key: game,
      game,
      license: "All Tiers",
      shortLabel: game,
      fullLabel: game,
      testCount: tests.length,
      licenseCount: licenseList.length,
      validHpCount: validHp.length,
      avgHp,
      minHp,
      maxHp,
      validPwCount: validPw.length,
      avgPw,
      minPw,
      maxPw,
      validGoldCount: validGold.length,
      avgDuration,
      minGold,
      maxGold,
      sampleCars: carList.slice(0, 3),
      tests,
    });
  }

  return aggregates;
}

/**
 * Aggregate test list by license tier per game calculating average HP, kg/hp and gold duration.
 */
export function aggregateTestsByLicense(list, activeGame = "ALL") {
  const groupsMap = new Map();

  for (const t of list) {
    const game = t.game || "GT";
    const license = t.license || "Standard";
    const key = `${game}||${license}`;
    if (!groupsMap.has(key)) {
      groupsMap.set(key, {
        game,
        license,
        tests: [],
      });
    }
    groupsMap.get(key).tests.push(t);
  }

  const aggregates = [];
  for (const [, grp] of groupsMap.entries()) {
    const tests = grp.tests;
    const validHp = tests.filter((t) => t.hp && t.hp > 0);
    const avgHp =
      validHp.length > 0
        ? Math.round(validHp.reduce((sum, t) => sum + t.hp, 0) / validHp.length)
        : null;

    const validPw = tests.filter((t) => t.pw_kg_hp && t.pw_kg_hp > 0);
    const avgPw =
      validPw.length > 0
        ? parseFloat((validPw.reduce((sum, t) => sum + t.pw_kg_hp, 0) / validPw.length).toFixed(2))
        : null;

    const validGold = tests.filter(
      (t) => t.gold_seconds !== null && t.gold_seconds !== undefined && isFinite(t.gold_seconds)
    );
    const avgDuration =
      validGold.length > 0
        ? parseFloat((validGold.reduce((sum, t) => sum + t.gold_seconds, 0) / validGold.length).toFixed(2))
        : null;

    const minHp = validHp.length > 0 ? Math.min(...validHp.map((t) => t.hp)) : null;
    const maxHp = validHp.length > 0 ? Math.max(...validHp.map((t) => t.hp)) : null;

    const minPw = validPw.length > 0 ? Math.min(...validPw.map((t) => t.pw_kg_hp)).toFixed(2) : null;
    const maxPw = validPw.length > 0 ? Math.max(...validPw.map((t) => t.pw_kg_hp)).toFixed(2) : null;

    const minGold = validGold.length > 0 ? Math.min(...validGold.map((t) => t.gold_seconds)) : null;
    const maxGold = validGold.length > 0 ? Math.max(...validGold.map((t) => t.gold_seconds)) : null;

    const shortLic = formatShortLicense(grp.license);
    const shortLabel = activeGame === "ALL" ? `${grp.game} ${shortLic}` : shortLic;
    const carList = Array.from(new Set(tests.map((t) => t.car).filter(Boolean)));

    aggregates.push({
      key: `${grp.game}||${grp.license}`,
      game: grp.game,
      license: grp.license,
      shortLabel,
      fullLabel: `${grp.game} ${grp.license}`,
      testCount: tests.length,
      validHpCount: validHp.length,
      avgHp,
      minHp,
      maxHp,
      validPwCount: validPw.length,
      avgPw,
      minPw,
      maxPw,
      validGoldCount: validGold.length,
      avgDuration,
      minGold,
      maxGold,
      sampleCars: carList.slice(0, 3),
      tests,
    });
  }

  return aggregates;
}

/**
 * Synchronize aggregation button labels, active classes, and card header titles.
 */
export function updateAggregationUiControls() {
  const isAgg = state.refChartsAggregateByLicense !== false;
  const showPerGame = shouldShowPerGameChart(state.activeRefGame);
  const btnPower = document.getElementById("btn-toggle-power-agg");
  const btnGold = document.getElementById("btn-toggle-gold-agg");
  const btnScale = document.getElementById("btn-toggle-gold-scale");
  const titlePower = document.getElementById("title-chart-power");
  const titleGold = document.getElementById("title-chart-gold");

  const aggLabel = showPerGame ? "Avg by Game" : "Avg by License";

  if (btnPower) {
    btnPower.classList.toggle("active", isAgg);
    btnPower.textContent = isAgg ? aggLabel : "All Tests";
  }
  if (btnGold) {
    btnGold.classList.toggle("active", isAgg);
    btnGold.textContent = isAgg ? aggLabel : "All Tests";
  }
  if (btnScale) {
    btnScale.style.display = isAgg ? "none" : "inline-block";
  }
  if (titlePower) {
    if (isAgg) {
      titlePower.textContent = showPerGame
        ? "Average Power & Power-to-Weight Ratio by Game"
        : "Average Power & Power-to-Weight Ratio by License";
    } else {
      titlePower.textContent = "Power & Power-to-Weight Ratio vs Test Progression";
    }
  }
  if (titleGold) {
    if (isAgg) {
      titleGold.textContent = showPerGame
        ? "Average Gold Medal Duration by Game"
        : "Average Gold Medal Duration by License";
    } else {
      titleGold.textContent = "Gold Medal Duration vs Test Progression";
    }
  }

  const badgeHp = document.getElementById("badge-toggle-hp");
  const badgePw = document.getElementById("badge-toggle-pw");
  if (badgeHp) badgeHp.classList.remove("dimmed");
  if (badgePw) badgePw.classList.remove("dimmed");
}

/**
 * Render all 4 analytical Chart.js graphs.
 */
export function renderReferenceCharts(list) {
  if (typeof Chart === "undefined") {
    console.warn("Chart.js not loaded, retrying in 200ms...");
    setTimeout(() => renderReferenceCharts(list), 200);
    return;
  }

  updateAggregationUiControls();
  renderPowerChart(list);
  renderGoldChart(list);
  renderGoldDistChart(list);
  renderDrivetrainChart(list);
}

/**
 * Chart 1: Power & Power-to-Weight Ratio vs Progression (Dual Y-Axis)
 */
function renderPowerChart(list) {
  const { gridColor, baseChartOptions } = getSharedChartContext();
  const isAgg = state.refChartsAggregateByLicense !== false;
  const showPerGame = shouldShowPerGameChart(state.activeRefGame);

  let labels;
  let hpData;
  let pwData;
  let aggregates = null;

  if (isAgg) {
    if (showPerGame) {
      aggregates = aggregateTestsByGame(list);
    } else {
      aggregates = aggregateTestsByLicense(list, state.activeRefGame);
    }
    labels = aggregates.map((a) => a.shortLabel);
    hpData = aggregates.map((a) => a.avgHp);
    pwData = aggregates.map((a) => a.avgPw);
  } else {
    labels = list.map((t) =>
      state.activeRefGame === "ALL" ? `${t.game} ${t.code}` : t.code
    );
    hpData = list.map((t) => (t.hp && t.hp > 0 ? t.hp : null));
    pwData = list.map((t) => (t.pw_kg_hp && t.pw_kg_hp > 0 ? t.pw_kg_hp : null));
  }

  const dense = labels.length > 50;

  // Responsive scroll configuration for mobile
  const canvasPower = document.getElementById("chart-power-pw");
  const wrapperPower = canvasPower?.closest(".chart-canvas-wrapper");
  const cardPower = canvasPower?.closest(".chart-card");
  const swipeHintPower = cardPower?.querySelector(".chart-swipe-hint");
  const isCompactPower = labels.length <= 10;
  if (wrapperPower) {
    wrapperPower.classList.toggle("no-scroll", isCompactPower);
  }
  if (swipeHintPower) {
    swipeHintPower.style.display = isCompactPower ? "none" : "";
  }

  renderSingleChart("chart-power-pw", {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: isAgg ? "Avg Horsepower (HP)" : "Horsepower (HP)",
          data: hpData,
          yAxisID: "yHP",
          borderColor: "#ef4444",
          backgroundColor: "rgba(239, 68, 68, 0.08)",
          borderWidth: isAgg ? 2.5 : 2,
          fill: false,
          tension: isAgg ? 0.3 : 0.2,
          spanGaps: true,
          pointBackgroundColor: "#ef4444",
          pointRadius: isAgg ? 4 : (dense ? 0 : 2),
          pointHoverRadius: 7,
        },
        {
          label: isAgg ? "Avg Power to Weight (kg/hp)" : "Power to Weight (kg/hp)",
          data: pwData,
          yAxisID: "yPW",
          borderColor: "#f59e0b",
          backgroundColor: "rgba(245, 158, 11, 0.08)",
          borderWidth: isAgg ? 2.5 : 2,
          borderDash: [4, 4],
          fill: false,
          tension: isAgg ? 0.3 : 0.2,
          spanGaps: true,
          pointBackgroundColor: "#f59e0b",
          pointRadius: isAgg ? 4 : (dense ? 0 : 2),
          pointHoverRadius: 7,
        },
      ],
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
              if (isAgg) {
                const a = aggregates[idx];
                if (showPerGame) {
                  return `${a.game} — All Licenses (${a.testCount} tests, ${a.licenseCount} tiers)`;
                }
                return `${a.game} — ${a.license} (${a.testCount} tests)`;
              }
              const t = list[idx];
              return `${t.game} [${t.code}] - ${t.title || t.test}`;
            },
            afterTitle: (items) => {
              const idx = items[0].dataIndex;
              if (isAgg) {
                const a = aggregates[idx];
                return a.sampleCars.length > 0 ? `Sample Cars: ${a.sampleCars.join(", ")}` : "";
              }
              const t = list[idx];
              return `Car: ${t.car}`;
            },
            label: (item) => {
              if (isAgg) {
                const a = aggregates[item.dataIndex];
                if (item.datasetIndex === 0) {
                  const range = a.minHp !== null ? ` (Range: ${a.minHp} – ${a.maxHp} HP)` : "";
                  return `Average HP: ${item.parsed.y !== null ? item.parsed.y + " HP" : "N/A"}${range}`;
                } else {
                  const range = a.minPw !== null ? ` (Range: ${a.minPw} – ${a.maxPw} kg/hp)` : "";
                  return `Average P/W: ${item.parsed.y !== null ? item.parsed.y + " kg/hp" : "N/A"}${range}`;
                }
              }
              if (item.datasetIndex === 0) {
                return `Horsepower: ${item.parsed.y} HP`;
              } else {
                return `Power/Weight: ${item.parsed.y} kg/hp`;
              }
            },
          },
        },
      },
      scales: {
        x: {
          ...baseChartOptions.scales.x,
          title: {
            display: true,
            text: isAgg
              ? (showPerGame
                  ? "Game Releases (Average Values)"
                  : (state.activeRefGame === "ALL"
                      ? "License Tier Progression by Game (Average Values)"
                      : `${state.activeRefGame} License Progression (Average Values)`))
              : baseChartOptions.scales.x.title.text,
            color: baseChartOptions.scales.x.title.color,
            font: baseChartOptions.scales.x.title.font,
          },
          ticks: {
            ...baseChartOptions.scales.x.ticks,
            maxRotation: showPerGame ? 0 : 45,
            maxTicksLimit: showPerGame ? 10 : (isAgg ? 25 : 14),
          },
        },
        yHP: {
          type: "linear",
          display: true,
          position: "left",
          title: {
            display: true,
            text: isAgg ? "Avg Horsepower (HP)" : "Horsepower (HP)",
            color: "#ef4444",
            font: { family: "Chakra Petch", size: 11, weight: "bold" },
          },
          ticks: {
            color: "#f87171",
            font: { family: "JetBrains Mono", size: 10 },
          },
          grid: { color: gridColor },
        },
        yPW: {
          type: "linear",
          display: true,
          position: "right",
          title: {
            display: true,
            text: isAgg ? "Avg P/W (kg/hp)" : "P/W (kg/hp)",
            color: "#f59e0b",
            font: { family: "Chakra Petch", size: 11, weight: "bold" },
          },
          ticks: {
            color: "#fbbf24",
            font: { family: "JetBrains Mono", size: 10 },
          },
          grid: { drawOnChartArea: false },
        },
      },
    },
  });
}

/**
 * Chart 2: Gold Medal Duration vs Progression (Focus mode protects scale for tests)
 */
function renderGoldChart(list) {
  const { textColor, gridColor, baseChartOptions } = getSharedChartContext();
  const isAgg = state.refChartsAggregateByLicense !== false;
  const showPerGame = shouldShowPerGameChart(state.activeRefGame);
  const isFocused = !isAgg && state.goldScaleFocus !== false;
  const maxZoomSec = 180; // 3-minute threshold for individual tests

  let labels;
  let goldData;
  let aggregates = null;

  if (isAgg) {
    if (showPerGame) {
      aggregates = aggregateTestsByGame(list);
    } else {
      aggregates = aggregateTestsByLicense(list, state.activeRefGame);
    }
    labels = aggregates.map((a) => a.shortLabel);
    goldData = aggregates.map((a) => a.avgDuration);
  } else {
    labels = list.map((t) =>
      state.activeRefGame === "ALL" ? `${t.game} ${t.code}` : t.code
    );
    goldData = list.map((t) => {
      if (t.gold_seconds === null || t.gold_seconds === undefined) return null;
      if (isFocused && t.gold_seconds > maxZoomSec) return maxZoomSec;
      return t.gold_seconds;
    });
  }

  const dense = labels.length > 50;

  // Responsive scroll configuration for mobile
  const canvasGold = document.getElementById("chart-gold");
  const wrapperGold = canvasGold?.closest(".chart-canvas-wrapper");
  const cardGold = canvasGold?.closest(".chart-card");
  const swipeHintGold = cardGold?.querySelector(".chart-swipe-hint");
  const isCompactGold = labels.length <= 10;
  if (wrapperGold) {
    wrapperGold.classList.toggle("no-scroll", isCompactGold);
  }
  if (swipeHintGold) {
    swipeHintGold.style.display = isCompactGold ? "none" : "";
  }

  renderSingleChart("chart-gold", {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: isAgg ? "Avg Gold Duration" : "Gold Duration",
          data: goldData,
          borderColor: "#10b981",
          backgroundColor: "rgba(16, 185, 129, 0.12)",
          borderWidth: isAgg ? 2.5 : 2,
          fill: true,
          tension: isAgg ? 0.3 : 0.25,
          spanGaps: true,
          pointBackgroundColor: "#10b981",
          pointRadius: isAgg ? 4 : (dense ? 0 : 2),
          pointHoverRadius: 7,
        },
      ],
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
              if (isAgg) {
                const a = aggregates[idx];
                if (showPerGame) {
                  return `${a.game} — All Licenses (${a.testCount} tests, ${a.licenseCount} tiers)`;
                }
                return `${a.game} — ${a.license} (${a.testCount} tests)`;
              }
              const t = list[idx];
              return `${t.game} [${t.code}] - ${t.title || t.test}`;
            },
            label: (item) => {
              if (isAgg) {
                const a = aggregates[item.dataIndex];
                if (a.avgDuration === null) {
                  return "Average Gold Target: N/A (no recorded times)";
                }
                const formatted = formatTimeDisplay(a.avgDuration);
                const range = a.minGold !== null
                  ? ` (Range: ${formatTimeDisplay(a.minGold)} – ${formatTimeDisplay(a.maxGold)})`
                  : "";
                return `Average Gold: ${formatted} (${a.avgDuration.toFixed(1)}s)${range}`;
              }
              const t = list[item.dataIndex];
              const rawSec = t.gold_seconds;
              const isOutlier = isFocused && rawSec > maxZoomSec;
              const note = isOutlier ? ` [Outlier: ${t.gold}]` : "";
              return `Gold Target: ${t.gold} (${rawSec ? rawSec.toFixed(3) : 0}s)${note}`;
            },
            afterLabel: (item) => {
              if (isAgg) {
                const a = aggregates[item.dataIndex];
                return `Timed tests: ${a.validGoldCount} of ${a.testCount}`;
              }
              const t = list[item.dataIndex];
              return `Track: ${t.track}`;
            },
          },
        },
      },
      scales: {
        x: {
          ...baseChartOptions.scales.x,
          title: {
            display: true,
            text: isAgg
              ? (showPerGame
                  ? "Game Releases (Average Values)"
                  : (state.activeRefGame === "ALL"
                      ? "License Tier Progression by Game (Average Values)"
                      : `${state.activeRefGame} License Progression (Average Values)`))
              : baseChartOptions.scales.x.title.text,
            color: baseChartOptions.scales.x.title.color,
            font: baseChartOptions.scales.x.title.font,
          },
          ticks: {
            ...baseChartOptions.scales.x.ticks,
            maxRotation: showPerGame ? 0 : 45,
            maxTicksLimit: showPerGame ? 10 : (isAgg ? 25 : 14),
          },
        },
        y: {
          grid: { color: gridColor },
          max: isFocused ? maxZoomSec : undefined,
          ticks: {
            color: textColor,
            font: { family: "JetBrains Mono", size: 10 },
            stepSize: isAgg ? 15 : (isFocused ? 30 : 60),
            callback: (val) => {
              if (val === 0) return "0s";
              if (val < 60) return `${val}s`;
              const m = Math.floor(val / 60);
              const s = val % 60;
              return s > 0 ? `${m}:${s < 10 ? "0" : ""}${s}` : `${m}m`;
            },
          },
          title: {
            display: true,
            text: isAgg
              ? "Avg Target Duration (mm:ss)"
              : (isFocused ? "Target Duration (mm:ss, Focus ≤3m)" : "Target Duration (mm:ss)"),
            color: "#10b981",
            font: { family: "Chakra Petch", size: 11, weight: "bold" },
          },
        },
      },
    },
  });
}

/**
 * Chart 3: Distribution of Gold Times (Continuous Density Curve with Exact P80 & P90)
 */
function renderGoldDistChart(list) {
  const { textColor, titleColor, gridColor, baseChartOptions } = getSharedChartContext();

  const timedTests = list.filter(
    (t) =>
      t.gold_seconds !== null &&
      t.gold_seconds !== undefined &&
      isFinite(t.gold_seconds)
  );
  const times = timedTests.map((t) => t.gold_seconds);

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

  const p80 = getPercentile(sortedTimes, 0.8);
  const p90 = getPercentile(sortedTimes, 0.9);

  // Update header badges
  const badgeP80 = document.getElementById("badge-p80");
  const badgeP90 = document.getElementById("badge-p90");
  if (badgeP80) {
    badgeP80.textContent = p80 !== null ? `80th %ile: ${formatTimeDisplay(p80).replace(/\.000$/, "")}` : "P80: N/A";
  }
  if (badgeP90) {
    badgeP90.textContent = p90 !== null ? `90th %ile: ${formatTimeDisplay(p90).replace(/\.000$/, "")}` : "P90: N/A";
  }

  // Linear sampling domain up to 180 seconds (covers 99% of curriculum tests)
  const maxSec = 180;
  const distPoints = [];
  const distNearbyMap = {};
  const sigma = 3.5;

  for (let s = 2; s <= maxSec; s += 2) {
    let density = 0;
    const nearby = [];

    times.forEach((t, i) => {
      const diff = (t - s) / sigma;
      density += Math.exp(-0.5 * diff * diff);
      if (Math.abs(t - s) <= 2.5) {
        nearby.push(timedTests[i]);
      }
    });

    distPoints.push({ x: s, y: Number(density.toFixed(2)) });
    distNearbyMap[s] = nearby;
  }

  renderSingleChart("chart-gold-dist", {
    type: "line",
    data: {
      datasets: [
        {
          label: "Test Concentration Density",
          data: distPoints,
          borderColor: "#06b6d4",
          backgroundColor: "rgba(6, 182, 212, 0.16)",
          borderWidth: 2.5,
          fill: true,
          tension: 0.35,
          pointRadius: 0,
          pointHoverRadius: 6,
          pointBackgroundColor: "#22d3ee",
          pointBorderColor: "#fff",
          pointBorderWidth: 1.5,
        },
      ],
    },
    plugins: [
      {
        id: "percentilesAnnotations",
        afterDraw(chart) {
          if (p80 === null && p90 === null) return;
          const { ctx, chartArea, scales } = chart;
          if (!chartArea || !scales || !scales.x) return;
          const { top, bottom, left, right } = chartArea;
          const xScale = scales.x;

          const p80Px = p80 !== null && p80 <= maxSec ? xScale.getPixelForValue(p80) : null;
          const p90Px = p90 !== null && p90 <= maxSec ? xScale.getPixelForValue(p90) : null;
          const isCrowded = p80Px !== null && p90Px !== null && Math.abs(p80Px - p90Px) < 70;

          const drawPercentileLine = (sec, px, label, color, labelOffsetY) => {
            if (sec === null || px === null || px < left || px > right) return;

            ctx.save();
            ctx.setLineDash([5, 4]);
            ctx.lineWidth = 1.5;
            ctx.strokeStyle = color;

            ctx.beginPath();
            ctx.moveTo(px, top + 26);
            ctx.lineTo(px, bottom);
            ctx.stroke();

            // Label badge at the top
            ctx.setLineDash([]);
            const timeStr = formatTimeDisplay(sec).replace(/\.000$/, "");
            const text = `${label} (${timeStr})`;
            ctx.font = "bold 10px 'JetBrains Mono', monospace";
            const textWidth = ctx.measureText(text).width;
            const boxW = textWidth + 12;
            const boxH = 18;
            const boxX = Math.max(left + 2, Math.min(right - boxW - 2, px - boxW / 2));
            const boxY = top + labelOffsetY;

            ctx.fillStyle = "rgba(15, 23, 42, 0.94)";
            ctx.beginPath();
            if (ctx.roundRect) {
              ctx.roundRect(boxX, boxY, boxW, boxH, 4);
            } else {
              ctx.rect(boxX, boxY, boxW, boxH);
            }
            ctx.fill();
            ctx.strokeStyle = color;
            ctx.lineWidth = 1;
            ctx.stroke();

            ctx.fillStyle = color;
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(text, boxX + boxW / 2, boxY + boxH / 2);
            ctx.restore();
          };

          drawPercentileLine(p80, p80Px, "P80", "#fbbf24", 4);
          drawPercentileLine(p90, p90Px, "P90", "#f43f5e", isCrowded ? 26 : 4);
        },
      },
    ],
    options: {
      ...baseChartOptions,
      plugins: {
        ...baseChartOptions.plugins,
        tooltip: {
          ...baseChartOptions.plugins.tooltip,
          callbacks: {
            title: (items) => {
              const sec = items[0].parsed.x;
              return `Target Duration: ~${formatTimeDisplay(sec).replace(/\.000$/, "")}`;
            },
            label: (item) => {
              const sec = Math.round(item.parsed.x / 2) * 2;
              const nearby = distNearbyMap[sec] || [];
              return `Tests in ±2.5s window: ${nearby.length} (Density: ${item.parsed.y})`;
            },
            afterLabel: (item) => {
              const sec = Math.round(item.parsed.x / 2) * 2;
              const nearby = distNearbyMap[sec];
              if (!nearby || nearby.length === 0) return "";
              const sample = nearby
                .slice(0, 4)
                .map((t) => `${t.code} (${t.gold})`)
                .join(", ");
              const more = nearby.length > 4 ? ` +${nearby.length - 4} more` : "";
              return `Examples: ${sample}${more}`;
            },
          },
        },
      },
      scales: {
        x: {
          type: "linear",
          min: 0,
          max: maxSec,
          grid: { color: gridColor },
          ticks: {
            color: textColor,
            font: { family: "JetBrains Mono", size: 10 },
            stepSize: 30,
            callback: (val) => {
              if (val === 0) return "0s";
              if (val < 60) return `${val}s`;
              const m = Math.floor(val / 60);
              const s = val % 60;
              return s > 0 ? `${m}:${s < 10 ? "0" : ""}${s}` : `${m}m`;
            },
          },
          title: {
            display: true,
            text: "Gold Target Duration",
            color: "#06b6d4",
            font: { family: "Chakra Petch", size: 11, weight: "bold" },
          },
        },
        y: {
          grid: { color: gridColor },
          ticks: {
            color: textColor,
            font: { family: "JetBrains Mono", size: 10 },
          },
          title: {
            display: true,
            text: "Relative Test Frequency / Density",
            color: titleColor,
            font: { family: "Chakra Petch", size: 11, weight: "bold" },
          },
        },
      },
    },
  });
}

/**
 * Chart 4: Car Drivetrain Architecture Distribution (Clean Horizontal Bar Chart)
 */
function renderDrivetrainChart(list) {
  const { textColor, gridColor, baseChartOptions } = getSharedChartContext();

  const LAYOUT_SPECS = [
    { key: "FR", name: "Front-Engine, Rear-Wheel Drive (FR)", color: "#8b5cf6", border: "#a78bfa" },
    { key: "MR", name: "Mid-Engine, Rear-Wheel Drive (MR)", color: "#06b6d4", border: "#22d3ee" },
    { key: "FF", name: "Front-Engine, Front-Wheel Drive (FF)", color: "#f59e0b", border: "#fbbf24" },
    { key: "4WD", name: "All-Wheel Drive (4WD/AWD)", color: "#10b981", border: "#34d399" },
    { key: "RR", name: "Rear-Engine, Rear-Wheel Drive (RR)", color: "#f43f5e", border: "#fb7185" },
  ];

  const counts = { FR: 0, MR: 0, FF: 0, "4WD": 0, RR: 0 };
  const hpTotals = { FR: 0, MR: 0, FF: 0, "4WD": 0, RR: 0 };
  const hpCounts = { FR: 0, MR: 0, FF: 0, "4WD": 0, RR: 0 };
  const sampleCars = { FR: [], MR: [], FF: [], "4WD": [], RR: [] };

  list.forEach((t) => {
    const layout = normalizeLayout(t.drivetrain_layout);
    if (counts[layout] !== undefined) {
      counts[layout]++;
      if (t.hp && t.hp > 0) {
        hpTotals[layout] += t.hp;
        hpCounts[layout]++;
      }
      if (t.car && sampleCars[layout].length < 3 && !sampleCars[layout].includes(t.car)) {
        sampleCars[layout].push(t.car);
      }
    }
  });

  const total = list.length || 1;
  const barData = LAYOUT_SPECS.map((s) => counts[s.key]);

  renderSingleChart("chart-drivetrain", {
    type: "bar",
    data: {
      labels: LAYOUT_SPECS.map((s) => s.key),
      datasets: [
        {
          label: "Tests Count",
          data: barData,
          backgroundColor: LAYOUT_SPECS.map((s) => s.color + "40"),
          borderColor: LAYOUT_SPECS.map((s) => s.border),
          borderWidth: 1.5,
          borderRadius: 4,
          barThickness: 24,
        },
      ],
    },
    options: {
      ...baseChartOptions,
      indexAxis: "y",
      plugins: {
        ...baseChartOptions.plugins,
        tooltip: {
          ...baseChartOptions.plugins.tooltip,
          callbacks: {
            title: (items) => {
              const spec = LAYOUT_SPECS[items[0].dataIndex];
              return spec ? spec.name : items[0].label;
            },
            label: (item) => {
              const spec = LAYOUT_SPECS[item.dataIndex];
              const count = item.parsed.x;
              const pct = ((count / total) * 100).toFixed(1);
              const avgHp =
                hpCounts[spec.key] > 0
                  ? `${Math.round(hpTotals[spec.key] / hpCounts[spec.key])} HP`
                  : "N/A";
              return `Tests: ${count} (${pct}%) | Avg Power: ${avgHp}`;
            },
            afterLabel: (item) => {
              const spec = LAYOUT_SPECS[item.dataIndex];
              const cars = sampleCars[spec.key];
              return cars.length > 0 ? `Sample: ${cars.join(", ")}` : "";
            },
          },
        },
      },
      scales: {
        x: {
          type: "linear",
          grid: { color: gridColor },
          ticks: {
            color: textColor,
            font: { family: "JetBrains Mono", size: 10 },
            precision: 0,
          },
          title: {
            display: true,
            text: "Total Tests in Curriculum",
            color: "#8b5cf6",
            font: { family: "Chakra Petch", size: 11, weight: "bold" },
          },
        },
        y: {
          grid: { display: false },
          ticks: {
            color: textColor,
            font: { family: "JetBrains Mono", size: 11, weight: "bold" },
          },
        },
      },
    },
  });
}

/**
 * Render or re-instantiate a single Chart.js canvas instance.
 */
export function renderSingleChart(canvasId, config) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  if (state.refCharts[canvasId]) {
    state.refCharts[canvasId].destroy();
  }

  state.refCharts[canvasId] = new Chart(canvas, config);
}

/**
 * Render the filtered table of Gran Turismo reference curriculum benchmarks.
 */
export function renderRefTableOnly() {
  if (!dom.refTableBody) return;
  dom.refTableBody.innerHTML = "";

  let list = getFilteredRefTests();

  // Apply Tier filter
  const selectedTier = dom.refTierSelect ? dom.refTierSelect.value : "ALL";
  if (selectedTier && selectedTier !== "ALL") {
    list = list.filter((t) => t.license === selectedTier);
  }

  // Apply Search filter
  const searchVal = dom.refSearchInput ? dom.refSearchInput.value.trim().toLowerCase() : "";
  if (searchVal) {
    list = list.filter((t) => {
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
    dom.refTableBody.innerHTML = `<tr><td colspan="12" style="text-align: center; color: var(--text-dim); padding: 30px;">No tests matching your filter criteria.</td></tr>`;
    return;
  }

  list.forEach((t) => {
    const row = document.createElement("tr");
    const safeLayout = escapeHtml(normalizeLayout(t.drivetrain_layout));
    const layoutClass = `layout-${safeLayout.toLowerCase()}`;
    const gameClass = t.game === "AC Mod" ? "tag-game tag-game-ac" : "tag-game";
    row.innerHTML = `
      <td><span class="tag-code">${escapeHtml(t.code)}</span></td>
      <td><span class="${gameClass}">${escapeHtml(t.game)}</span></td>
      <td>${escapeHtml(t.license)}</td>
      <td><strong>${escapeHtml(t.title || t.test)}</strong></td>
      <td>${escapeHtml(t.car)}</td>
      <td><span class="tag-hp">${t.hp ? escapeHtml(t.hp) + " HP" : "N/A"}</span></td>
      <td><span class="tag-pw">${t.pw_kg_hp ? escapeHtml(t.pw_kg_hp) : "N/A"}</span></td>
      <td><span class="tag-layout ${layoutClass}">${safeLayout}</span></td>
      <td>${escapeHtml(t.track)}</td>
      <td style="color: var(--accent-gold); font-family: var(--font-mono); font-weight: 600;">${escapeHtml(t.gold)}</td>
      <td style="color: var(--accent-silver); font-family: var(--font-mono);">${escapeHtml(t.silver)}</td>
      <td style="color: var(--accent-bronze); font-family: var(--font-mono);">${escapeHtml(t.bronze)}</td>
    `;
    dom.refTableBody.appendChild(row);
  });
}
