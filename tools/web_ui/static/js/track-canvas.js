/**
 * track-canvas.js
 * 2D Interactive Track Map and AI Spline visualizer.
 */

import { state } from "./state.js";
import { dom } from "./dom.js";
import { api } from "./api.js";
import { isLightTheme, onThemeChange } from "./theme.js";

let onPositionChangeCallback = null;

/**
 * Configure the position update callback when canvas is clicked.
 * @param {Function} callback (startS, finishS) => void
 */
export function setTrackCanvasPositionCallback(callback) {
  onPositionChangeCallback = callback;
}

/**
 * Fetch and render 2D AI spline for a track layout.
 * @param {string} trackId
 * @param {string} layout
 */
export async function fetchAndRenderSpline(trackId, layout) {
  if (!trackId) {
    state.currentSpline = null;
    if (dom.mapTrackInfo) dom.mapTrackInfo.textContent = "No track selected";
    drawEmptyCanvas();
    return;
  }

  if (dom.canvasLoading) dom.canvasLoading.style.display = "flex";

  try {
    const data = await api.getSpline(trackId, layout);
    if (data.success && data.points && data.points.length > 0) {
      state.currentSpline = data;
      if (dom.mapTrackInfo) {
        const count = data.points.length;
        const lenKm = ((data.total_length || 0) / 1000).toFixed(2);
        dom.mapTrackInfo.textContent = `${count} pts • ${lenKm} km`;
      }
      renderCanvasTrack();
    } else {
      state.currentSpline = null;
      if (dom.mapTrackInfo) {
        dom.mapTrackInfo.textContent = data.error || "No AI spline available for layout";
      }
      drawEmptyCanvas();
    }
  } catch (err) {
    console.error("Failed to load track spline:", err);
    state.currentSpline = null;
    if (dom.mapTrackInfo) dom.mapTrackInfo.textContent = "Error loading spline";
    drawEmptyCanvas();
  } finally {
    if (dom.canvasLoading) dom.canvasLoading.style.display = "none";
  }
}

/**
 * Draw placeholder message when no spline is loaded.
 */
export function drawEmptyCanvas() {
  if (!dom.trackCanvas) return;
  const isLight = isLightTheme();
  const ctx = dom.trackCanvas.getContext("2d");
  ctx.clearRect(0, 0, dom.trackCanvas.width, dom.trackCanvas.height);
  ctx.fillStyle = isLight ? "#f8fafc" : "#080b12";
  ctx.fillRect(0, 0, dom.trackCanvas.width, dom.trackCanvas.height);

  ctx.fillStyle = isLight ? "#64748b" : "#596b86";
  ctx.font = "14px Inter, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(
    "Select a track with an AI spline to view 2D map",
    dom.trackCanvas.width / 2,
    dom.trackCanvas.height / 2
  );
}

/**
 * Render complete 2D circuit outline, active sector ribbon, and start/finish gate markers.
 */
export function renderCanvasTrack() {
  if (
    !dom.trackCanvas ||
    !state.currentSpline ||
    !state.currentSpline.points ||
    state.currentSpline.points.length === 0
  ) {
    drawEmptyCanvas();
    return;
  }

  const isLight = isLightTheme();
  const pts = state.currentSpline.points;
  const bounds = state.currentSpline.bounds;
  const ctx = dom.trackCanvas.getContext("2d");
  const w = dom.trackCanvas.width;
  const h = dom.trackCanvas.height;

  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = isLight ? "#f8fafc" : "#080b12";
  ctx.fillRect(0, 0, w, h);

  // Coordinate transforms to fit canvas with padding
  const pad = 30;
  const bw = bounds.width || 1;
  const bh = bounds.height || 1;
  const scale = Math.min((w - pad * 2) / bw, (h - pad * 2) / bh);
  const ox = (w - bw * scale) / 2 - bounds.min_x * scale;
  const oy = (h - bh * scale) / 2 - bounds.min_y * scale;

  const toX = (wx) => wx * scale + ox;
  const toY = (wy) => wy * scale + oy;

  const startS = parseFloat(dom.inputStart ? dom.inputStart.value : 0) || 0;
  const finishS = parseFloat(dom.inputFinish ? dom.inputFinish.value : 1) || 1;

  // 1. Draw base track line (subdued circuit outline)
  ctx.lineWidth = 6;
  ctx.strokeStyle = isLight ? "#cbd5e1" : "#1e2942";
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.beginPath();
  ctx.moveTo(toX(pts[0].x), toY(pts[0].y));
  for (let i = 1; i < pts.length; i++) {
    ctx.lineTo(toX(pts[i].x), toY(pts[i].y));
  }
  ctx.stroke();

  // 2. Draw active sector (glowing gold ribbon)
  ctx.lineWidth = 4;
  ctx.strokeStyle = isLight ? "#d97706" : "#facc15";
  ctx.shadowColor = isLight ? "rgba(217, 119, 6, 0.4)" : "rgba(250, 204, 21, 0.6)";
  ctx.shadowBlur = 8;
  ctx.beginPath();

  let started = false;
  for (let i = 0; i < pts.length; i++) {
    const s = pts[i].s;
    let inSector = false;
    if (finishS >= startS) {
      inSector = s >= startS && s <= finishS;
    } else {
      // Sector wraps around 1.0 -> 0.0
      inSector = s >= startS || s <= finishS;
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
    drawMarker(ctx, toX(startPt.x), toY(startPt.y), isLight ? "#059669" : "#10b981", "START");
  }

  // 4. Find and Draw Finish Gate Marker
  const finishPt = findPointAtProgress(pts, finishS);
  if (finishPt) {
    drawMarker(ctx, toX(finishPt.x), toY(finishPt.y), isLight ? "#dc2626" : "#e11d48", "FINISH");
  }
}

/**
 * Locate waypoint closest to normalized progress s (0.0 .. 1.0).
 */
export function findPointAtProgress(pts, targetS) {
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

/**
 * Draw 2D circular badge marker on canvas.
 */
export function drawMarker(ctx, x, y, color, label) {
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

  ctx.fillStyle = isLightTheme() ? "#0f172a" : "#ffffff";
  ctx.font = "bold 9px 'JetBrains Mono', monospace";
  ctx.textAlign = "center";
  ctx.fillText(label, x, y - 11);
  ctx.restore();
}

/**
 * Attach click interaction to canvas map.
 */
export function initCanvasInteraction() {
  if (!dom.trackCanvas) return;

  // Re-render track when theme changes
  onThemeChange(() => {
    renderCanvasTrack();
  });

  dom.trackCanvas.addEventListener("click", (e) => {
    if (!state.currentSpline || (dom.toggleFullLap && dom.toggleFullLap.checked)) return;

    const rect = dom.trackCanvas.getBoundingClientRect();
    const clickX = (e.clientX - rect.left) * (dom.trackCanvas.width / rect.width);
    const clickY = (e.clientY - rect.top) * (dom.trackCanvas.height / rect.height);

    const pts = state.currentSpline.points;
    const bounds = state.currentSpline.bounds;
    const pad = 30;
    const bw = bounds.width || 1;
    const bh = bounds.height || 1;
    const scale = Math.min(
      (dom.trackCanvas.width - pad * 2) / bw,
      (dom.trackCanvas.height - pad * 2) / bh
    );
    const ox = (dom.trackCanvas.width - bw * scale) / 2 - bounds.min_x * scale;
    const oy = (dom.trackCanvas.height - bh * scale) / 2 - bounds.min_y * scale;

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

    if (closestPt && minDist < 40 && onPositionChangeCallback) {
      const s = closestPt.s;
      const curStart = parseFloat(dom.inputStart ? dom.inputStart.value : 0) || 0;
      const curFinish = parseFloat(dom.inputFinish ? dom.inputFinish.value : 1) || 1;

      // If Shift key is held, set Finish. Otherwise set whichever gate is closer.
      if (e.shiftKey) {
        onPositionChangeCallback(curStart, s);
      } else {
        const distToStart = Math.abs(s - curStart);
        const distToFinish = Math.abs(s - curFinish);
        if (distToStart < distToFinish) {
          onPositionChangeCallback(s, curFinish);
        } else {
          onPositionChangeCallback(curStart, s);
        }
      }
    }
  });
}
