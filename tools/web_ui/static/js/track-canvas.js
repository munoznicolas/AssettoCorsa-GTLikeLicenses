function getThemeColor(varName, fallback) {
  try {
    const val = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
    return val || fallback;
  } catch (e) {
    return fallback;
  }
}

/**
 * track-canvas.js
 * 2D Interactive Track Map and AI Spline visualizer.
 */

import { state } from "./state.js";
import { dom } from "./dom.js";
import { api } from "./api.js";

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
    drawEmptyCanvas();
    return;
  }

  if (dom.canvasLoading) dom.canvasLoading.style.display = "flex";
  try {
    const data = await api.getSpline(trackId, layout);
    if (data.success && data.spline) {
      state.currentSpline = data.spline;
      if (onPositionChangeCallback && dom.inputStart && dom.inputFinish) {
        onPositionChangeCallback(
          parseFloat(dom.inputStart.value || 0),
          parseFloat(dom.inputFinish.value || 1)
        );
      }
    } else {
      state.currentSpline = null;
      drawEmptyCanvas();
    }
  } catch (e) {
    state.currentSpline = null;
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
  const ctx = dom.trackCanvas.getContext("2d");
  ctx.clearRect(0, 0, dom.trackCanvas.width, dom.trackCanvas.height);
  ctx.fillStyle = getThemeColor("--bg-card", "#0c0f14");
  ctx.fillRect(0, 0, dom.trackCanvas.width, dom.trackCanvas.height);

  ctx.fillStyle = getThemeColor("--text-dim", "#5c687a");
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

  const pts = state.currentSpline.points;
  const bounds = state.currentSpline.bounds;
  const ctx = dom.trackCanvas.getContext("2d");
  const w = dom.trackCanvas.width;
  const h = dom.trackCanvas.height;

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

  const startS = parseFloat(dom.inputStart ? dom.inputStart.value : 0) || 0;
  const finishS = parseFloat(dom.inputFinish ? dom.inputFinish.value : 1) || 1;

  // 1. Draw base track line
  ctx.lineWidth = 6;
  ctx.strokeStyle = getThemeColor("--border-color", "#262e3b");
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.beginPath();
  ctx.moveTo(toX(pts[0].x), toY(pts[0].y));
  for (let i = 1; i < pts.length; i++) {
    ctx.lineTo(toX(pts[i].x), toY(pts[i].y));
  }
  ctx.stroke();

  // 2. Draw active sector
  ctx.lineWidth = 4;
  ctx.strokeStyle = getThemeColor("--accent-gold", "#f59e0b");
  ctx.shadowColor = getThemeColor("--accent-gold-border", "rgba(245, 158, 11, 0.35)");
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
    drawMarker(ctx, toX(startPt.x), toY(startPt.y), getThemeColor("--accent-green", "#10b981"), "START");
  }

  // 4. Find and Draw Finish Gate Marker
  const finishPt = findPointAtProgress(pts, finishS);
  if (finishPt) {
    drawMarker(ctx, toX(finishPt.x), toY(finishPt.y), getThemeColor("--accent-danger", "#e11d48"), "FINISH");
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

  // 1. Draw glowing circular gate anchor
  ctx.fillStyle = color;
  ctx.shadowColor = color;
  ctx.shadowBlur = 8;
  ctx.beginPath();
  ctx.arc(x, y, 6.5, 0, Math.PI * 2);
  ctx.fill();

  // 2. White outer ring around dot
  ctx.shadowBlur = 0;
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 2;
  ctx.stroke();

  // 3. Draw pill badge container for label
  ctx.font = "bold 10px 'JetBrains Mono', monospace";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";

  const metrics = ctx.measureText(label);
  const textWidth = metrics.width;
  const pillW = textWidth + 12;
  const pillH = 16;
  const pillX = x - pillW / 2;
  // If near top edge of canvas, position pill below anchor to prevent clipping
  const pillY = y < 30 ? y + 14 : y - 24;
  const radius = 3;

  const isLight = document.documentElement.getAttribute("data-theme") === "light";

  if (isLight) {
    // Light mode: solid colored pill badge with crisp white text (contrast > 4.7:1)
    ctx.fillStyle = color;
    ctx.beginPath();
    if (ctx.roundRect) {
      ctx.roundRect(pillX, pillY, pillW, pillH, radius);
    } else {
      ctx.rect(pillX, pillY, pillW, pillH);
    }
    ctx.fill();

    ctx.strokeStyle = "rgba(0, 0, 0, 0.15)";
    ctx.lineWidth = 1;
    ctx.stroke();

    ctx.fillStyle = "#ffffff";
    ctx.fillText(label, x, pillY + pillH / 2);
  } else {
    // Dark mode: dark pill badge with colored text matching gate
    ctx.fillStyle = "rgba(12, 15, 20, 0.9)";
    ctx.beginPath();
    if (ctx.roundRect) {
      ctx.roundRect(pillX, pillY, pillW, pillH, radius);
    } else {
      ctx.rect(pillX, pillY, pillW, pillH);
    }
    ctx.fill();

    ctx.strokeStyle = color;
    ctx.lineWidth = 1;
    ctx.stroke();

    ctx.fillStyle = color;
    ctx.fillText(label, x, pillY + pillH / 2);
  }

  ctx.restore();
}


/**
 * Attach click & touch interactions to canvas map.
 */
export function initCanvasInteraction() {
  if (!dom.trackCanvas) return;

  window.addEventListener("themechange", () => renderCanvasTrack());

  const handlePointerAt = (clientX, clientY, shiftKey) => {
    if (!state.currentSpline || (dom.toggleFullLap && dom.toggleFullLap.checked)) return;

    const rect = dom.trackCanvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;

    const clickX = (clientX - rect.left) * (dom.trackCanvas.width / rect.width);
    const clickY = (clientY - rect.top) * (dom.trackCanvas.height / rect.height);

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

    // Find closest waypoint to mouse/touch position
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

    if (closestPt && minDist < 50 && onPositionChangeCallback) {
      const s = closestPt.s;
      const curStart = parseFloat(dom.inputStart ? dom.inputStart.value : 0) || 0;
      const curFinish = parseFloat(dom.inputFinish ? dom.inputFinish.value : 1) || 1;

      // If Shift key is held (desktop), place Finish; otherwise move closest gate
      if (shiftKey) {
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
  };

  dom.trackCanvas.addEventListener("click", (e) => {
    handlePointerAt(e.clientX, e.clientY, e.shiftKey);
  });

  dom.trackCanvas.addEventListener("touchstart", (e) => {
    if (e.touches && e.touches.length === 1) {
      const touch = e.touches[0];
      handlePointerAt(touch.clientX, touch.clientY, false);
    }
  }, { passive: true });
}

