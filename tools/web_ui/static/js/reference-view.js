/**
 * reference-view.js
 * Gran Turismo curriculum reference comparison, analytics, and Chart.js visualizations.
 */

import { state } from "./state.js";
import { dom } from "./dom.js";
import { formatTimeDisplay, escapeHtml } from "./ui-utils.js";
import { renderReferenceCharts, renderSingleChart } from "./reference/charts.js";

export { renderReferenceCharts, renderSingleChart };

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
    const safeLayout = escapeHtml(t.drivetrain_layout || "FR");
    const layoutClass = `layout-${safeLayout}`;
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
      <td style="color: #fbbf24; font-family: var(--font-mono); font-weight: 600;">${escapeHtml(t.gold)}</td>
      <td style="color: #cbd5e1; font-family: var(--font-mono);">${escapeHtml(t.silver)}</td>
      <td style="color: #d97706; font-family: var(--font-mono);">${escapeHtml(t.bronze)}</td>
    `;
    dom.refTableBody.appendChild(row);
  });
}
