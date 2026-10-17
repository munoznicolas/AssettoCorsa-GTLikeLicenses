/**
 * reference/chart-configs.js
 * Chart.js configuration builders for Gran Turismo curriculum reference analytics.
 */

import { state } from "../state.js";
import { formatTimeDisplay } from "../ui-utils.js";

export const LAYOUT_CATEGORIES = ["FF", "FR", "MR", "RR", "FAWD", "MAWD", "RAWD"];

/**
 * Create base Chart.js options shared across reference charts.
 */
export function buildBaseChartOptions() {
  return {
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
}

/**
 * Chart 1: Power & Power-to-Weight Ratio vs Test Progression (Dual Y-Axis).
 */
export function buildPowerPwChartConfig(list, labels, baseChartOptions) {
  const hpData = list.map((t) => t.hp || 0);
  const pwData = list.map((t) => t.pw_kg_hp || null);

  return {
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
              }
              return `⚖️ Power/Weight: ${item.parsed.y} kg/hp`;
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
  };
}

/**
 * Chart 2: Gold Medal Duration vs Test Progression.
 */
export function buildGoldDurationChartConfig(list, labels, baseChartOptions) {
  const goldData = list.map((t) =>
    t.gold_seconds !== null && t.gold_seconds !== undefined ? t.gold_seconds : null
  );

  return {
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
  };
}

/**
 * Chart 3: Distribution of Gold Times (Continuous Density Curve with P80 & P90).
 */
export function buildGoldDistributionChartConfig(
  distLabels,
  distDensity,
  distNearbyTests,
  p80,
  p90,
  maxSec,
  step,
  baseChartOptions
) {
  return {
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
          tension: 0.4,
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
  };
}

/**
 * Chart 4: Car Drivetrain Layout vs Test Progression.
 */
export function buildDrivetrainChartConfig(list, labels, baseChartOptions) {
  const layoutData = list.map((t) => {
    const idx = LAYOUT_CATEGORIES.indexOf(t.drivetrain_layout);
    return idx >= 0 ? idx : 1; // Default to FR if missing
  });

  return {
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
  };
}
