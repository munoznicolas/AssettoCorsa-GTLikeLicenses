/**
 * reference/charts.js
 * Chart.js chart builders and canvas instantiation for the GT reference view.
 */

import { state } from "../state.js";
import { formatTimeDisplay } from "../ui-utils.js";
import {
  buildBaseChartOptions,
  buildPowerPwChartConfig,
  buildGoldDurationChartConfig,
  buildGoldDistributionChartConfig,
  buildDrivetrainChartConfig,
} from "./chart-configs.js";

/**
 * Compute linear interpolation percentile on a pre-sorted ascending array.
 */
function getPercentile(sortedArr, p) {
  if (!sortedArr || sortedArr.length === 0) return null;
  const idx = (sortedArr.length - 1) * p;
  const lower = Math.floor(idx);
  const upper = Math.ceil(idx);
  const weight = idx - lower;
  return sortedArr[lower] * (1 - weight) + sortedArr[upper] * weight;
}

/**
 * Update P80 and P90 percentile badges in the DOM.
 */
function updatePercentileBadges(p80, p90) {
  const badgeP80 = document.getElementById("badge-p80");
  const badgeP90 = document.getElementById("badge-p90");
  if (badgeP80) {
    badgeP80.textContent = p80 !== null ? `80th %ile: ${formatTimeDisplay(p80)}` : "P80: N/A";
  }
  if (badgeP90) {
    badgeP90.textContent = p90 !== null ? `90th %ile: ${formatTimeDisplay(p90)}` : "P90: N/A";
  }
}

/**
 * Compute continuous Gaussian kernel density curve for Gold times.
 */
function computeGoldTimeDistribution(list) {
  const timedTests = list.filter(
    (t) =>
      t.gold_seconds !== null &&
      t.gold_seconds !== undefined &&
      isFinite(t.gold_seconds)
  );
  const times = timedTests.map((t) => t.gold_seconds);
  const sortedTimes = [...times].sort((a, b) => a - b);

  const p80 = getPercentile(sortedTimes, 0.8);
  const p90 = getPercentile(sortedTimes, 0.9);
  updatePercentileBadges(p80, p90);

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

  return { distLabels, distDensity, distNearbyTests, p80, p90, maxSec, step };
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
  const baseChartOptions = buildBaseChartOptions();

  // Chart 1: Power & Power-to-Weight Ratio vs Test Progression (Dual Y-Axis)
  renderSingleChart(
    "chart-power-pw",
    buildPowerPwChartConfig(list, labels, baseChartOptions)
  );

  // Chart 2: Gold Medal Duration vs Test Progression
  renderSingleChart(
    "chart-gold",
    buildGoldDurationChartConfig(list, labels, baseChartOptions)
  );

  // Chart 3: Distribution of Gold Times (Continuous Density Curve with P80 & P90)
  const { distLabels, distDensity, distNearbyTests, p80, p90, maxSec, step } =
    computeGoldTimeDistribution(list);
  renderSingleChart(
    "chart-gold-dist",
    buildGoldDistributionChartConfig(
      distLabels,
      distDensity,
      distNearbyTests,
      p80,
      p90,
      maxSec,
      step,
      baseChartOptions
    )
  );

  // Chart 4: Car Drivetrain Layout vs Test Progression
  renderSingleChart(
    "chart-drivetrain",
    buildDrivetrainChartConfig(list, labels, baseChartOptions)
  );
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
