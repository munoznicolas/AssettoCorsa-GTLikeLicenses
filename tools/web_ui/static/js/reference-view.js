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

/**
 * Render all 4 analytical Chart.js graphs.
 */
export function renderReferenceCharts(list) {
  if (typeof Chart === "undefined") {
    console.warn("Chart.js not loaded, retrying in 200ms...");
    setTimeout(() => renderReferenceCharts(list), 200);
    return;
  }

  const labels = list.map((t) =>
    state.activeRefGame === "ALL" ? `${t.game} ${t.code}` : t.code
  );

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
      },
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
          text:
            state.activeRefGame === "ALL"
              ? "Curriculum Progression (All GT Games)"
              : `${state.activeRefGame} Test Progression`,
          color: "#64748b",
          font: { family: "Chakra Petch", size: 11, weight: "bold" },
        },
      },
      y: {
        grid: { color: "rgba(255, 255, 255, 0.05)" },
        ticks: {
          color: "#94a3b8",
          font: { family: "JetBrains Mono", size: 10 },
        },
      },
    },
  };

  // -------------------------------------------------------------------------
  // Chart 1: Power & Power-to-Weight Ratio vs Test Progression (Dual Y-Axis)
  // -------------------------------------------------------------------------
  const hpData = list.map((t) => t.hp || 0);
  const pwData = list.map((t) => t.pw_kg_hp || null);

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
        },
      ],
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
            padding: 10,
          },
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
            },
          },
        },
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
            font: { family: "Chakra Petch", size: 11, weight: "bold" },
          },
          ticks: {
            color: "#f87171",
            font: { family: "JetBrains Mono", size: 10 },
          },
          grid: { color: "rgba(255, 255, 255, 0.05)" },
        },
        yPW: {
          type: "linear",
          display: true,
          position: "right",
          title: {
            display: true,
            text: "P/W (kg/hp)",
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

  // -------------------------------------------------------------------------
  // Chart 2: Gold Medal Duration vs Test Progression
  // -------------------------------------------------------------------------
  const goldData = list.map((t) =>
    t.gold_seconds !== null && t.gold_seconds !== undefined ? t.gold_seconds : null
  );
  renderSingleChart("chart-gold", {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
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
              const t = list[idx];
              return `${t.game} [${t.code}] - ${t.title || t.test}`;
            },
            label: (item) => {
              const t = list[item.dataIndex];
              return `🥇 Gold Target: ${t.gold} (${item.parsed.y}s) | Track: ${t.track}`;
            },
          },
        },
      },
      scales: {
        ...baseChartOptions.scales,
        y: {
          ...baseChartOptions.scales.y,
          title: {
            display: true,
            text: "Gold Target Duration (Seconds)",
            color: "#10b981",
            font: { family: "Chakra Petch", size: 11 },
          },
          ticks: {
            ...baseChartOptions.scales.y.ticks,
            callback: (val) => `${val}s`,
          },
        },
      },
    },
  });

  // -------------------------------------------------------------------------
  // Chart 3: Distribution of Gold Times (Continuous Density Curve with P80 & P90)
  // -------------------------------------------------------------------------
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
      if (Math.abs(t - s) <= step / 2) {
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
      datasets: [
        {
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
            title: (items) => `Target Duration: ~${distLabels[items[0].dataIndex]}`,
            label: (item) => {
              const nearby = distNearbyTests[item.dataIndex];
              const count = nearby ? nearby.length : 0;
              return `📊 Tests in ±2.5s window: ${count} (Density Score: ${item.parsed.y})`;
            },
            afterLabel: (item) => {
              const nearby = distNearbyTests[item.dataIndex];
              if (!nearby || nearby.length === 0) return "";
              const sample = nearby
                .slice(0, 5)
                .map((t) => `${t.code} (${t.gold})`)
                .join(", ");
              const more = nearby.length > 5 ? ` +${nearby.length - 5} more` : "";
              return `Examples: ${sample}${more}`;
            },
          },
        },
      },
      scales: {
        ...baseChartOptions.scales,
        x: {
          ...baseChartOptions.scales.x,
          title: {
            display: true,
            text: "Gold Target Duration",
            color: "#06b6d4",
            font: { family: "Chakra Petch", size: 11, weight: "bold" },
          },
        },
        y: {
          ...baseChartOptions.scales.y,
          title: {
            display: true,
            text: "Relative Test Frequency / Density",
            color: "#64748b",
            font: { family: "Chakra Petch", size: 11, weight: "bold" },
          },
        },
      },
    },
  });

  // -------------------------------------------------------------------------
  // Chart 4: Car Drivetrain Layout vs Test Progression
  // -------------------------------------------------------------------------
  const LAYOUT_CATEGORIES = ["FF", "FR", "MR", "RR", "FAWD", "MAWD", "RAWD"];
  const layoutData = list.map((t) => {
    const idx = LAYOUT_CATEGORIES.indexOf(t.drivetrain_layout);
    return idx >= 0 ? idx : 1; // Default to FR if missing
  });

  renderSingleChart("chart-drivetrain", {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
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
              const t = list[idx];
              return `${t.game} [${t.code}] - ${t.title || t.test}`;
            },
            label: (item) => {
              const t = list[item.dataIndex];
              const cat = LAYOUT_CATEGORIES[item.parsed.y] || "Unknown";
              return `⚙️ Layout: ${cat} (Engine: ${t.engine}, Drivetrain: ${t.drivetrain}) | Car: ${t.car}`;
            },
          },
        },
      },
      scales: {
        ...baseChartOptions.scales,
        y: {
          ...baseChartOptions.scales.y,
          min: 0,
          max: LAYOUT_CATEGORIES.length - 1,
          title: {
            display: true,
            text: "Powertrain Layout Category",
            color: "#8b5cf6",
            font: { family: "Chakra Petch", size: 11 },
          },
          ticks: {
            ...baseChartOptions.scales.y.ticks,
            stepSize: 1,
            callback: (val) => LAYOUT_CATEGORIES[val] || "",
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
    const layoutClass = `layout-${t.drivetrain_layout || "FR"}`;
    const gameClass = t.game === "AC Mod" ? "tag-game tag-game-ac" : "tag-game";
    row.innerHTML = `
      <td><span class="tag-code">${escapeHtml(t.code)}</span></td>
      <td><span class="${gameClass}">${escapeHtml(t.game)}</span></td>
      <td>${escapeHtml(t.license)}</td>
      <td><strong>${escapeHtml(t.title || t.test)}</strong></td>
      <td>${escapeHtml(t.car)}</td>
      <td><span class="tag-hp">${t.hp ? t.hp + " HP" : "N/A"}</span></td>
      <td><span class="tag-pw">${t.pw_kg_hp ? t.pw_kg_hp : "N/A"}</span></td>
      <td><span class="tag-layout ${layoutClass}">${escapeHtml(t.drivetrain_layout || "FR")}</span></td>
      <td>${escapeHtml(t.track)}</td>
      <td style="color: #fbbf24; font-family: var(--font-mono); font-weight: 600;">${escapeHtml(t.gold)}</td>
      <td style="color: #cbd5e1; font-family: var(--font-mono);">${escapeHtml(t.silver)}</td>
      <td style="color: #d97706; font-family: var(--font-mono);">${escapeHtml(t.bronze)}</td>
    `;
    dom.refTableBody.appendChild(row);
  });
}

