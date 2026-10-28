/**
 * miniature-builder.js
 * Pure Client-Side Track Miniature / Sector Preview Generator.
 *
 * Replaces Python matplotlib / PIL miniature rendering with HTML5 Canvas:
 *   - Projects track spline coordinates onto a 512x288 canvas
 *   - Draws full circuit layout with highlighted active sector
 *   - Renders start/finish visual gate markers
 *   - Returns PNG Data URL and Blob for direct insertion into Content Manager ZIP packages
 */

/**
 * Projects 2D world coordinates (x, z) to canvas pixel coordinates.
 * @param {number} x
 * @param {number} z
 * @param {Object} bounds { minX, maxX, minZ, maxZ }
 * @param {number} width Canvas width
 * @param {number} height Canvas height
 * @param {number} padding Margin padding in pixels
 * @returns {[number, number]}
 */
function projectPoint(x, z, bounds, width, height, padding = 24) {
  const spanX = Math.max(1, bounds.maxX - bounds.minX);
  const spanZ = Math.max(1, bounds.maxZ - bounds.minZ);
  const scale = Math.min((width - padding * 2) / spanX, (height - padding * 2) / spanZ);

  const cx = (bounds.minX + bounds.maxX) / 2;
  const cz = (bounds.minZ + bounds.maxZ) / 2;

  const px = width / 2 + (x - cx) * scale;
  const py = height / 2 - (z - cz) * scale; // Invert Z for screen Y

  return [px, py];
}

/**
 * Computes bounding box for spline points.
 * @param {Array<{ x: number, z: number }>} points
 * @returns {Object}
 */
function computeBounds(points) {
  let minX = Infinity;
  let maxX = -Infinity;
  let minZ = Infinity;
  let maxZ = -Infinity;

  for (const p of points) {
    if (p.x < minX) minX = p.x;
    if (p.x > maxX) maxX = p.x;
    if (p.z < minZ) minZ = p.z;
    if (p.z > maxZ) maxZ = p.z;
  }

  if (!isFinite(minX)) {
    return { minX: -100, maxX: 100, minZ: -100, maxZ: 100 };
  }
  return { minX, maxX, minZ, maxZ };
}

/**
 * Interpolates coordinates along waypoints at a normalized progress s in [0..1].
 * @param {Array<{ x: number, z: number }>} points
 * @param {number} s
 * @returns {{ x: number, z: number, angle: number }}
 */
function getPointAtProgress(points, s) {
  const normS = ((s % 1.0) + 1.0) % 1.0;
  const n = points.length;
  if (n === 0) return { x: 0, z: 0, angle: 0 };
  if (n === 1) return { x: points[0].x, z: points[0].z, angle: 0 };

  const exactIdx = normS * (n - 1);
  const idx0 = Math.floor(exactIdx);
  const idx1 = Math.min(n - 1, idx0 + 1);
  const frac = exactIdx - idx0;

  const p0 = points[idx0];
  const p1 = points[idx1];

  const x = p0.x + frac * (p1.x - p0.x);
  const z = p0.z + frac * (p1.z - p0.z);

  const dx = p1.x - p0.x;
  const dz = p1.z - p0.z;
  const angle = Math.atan2(dz, dx);

  return { x, z, angle };
}

/**
 * Generates an overhead track sector preview miniature as a PNG Data URL.
 * @param {Object} spline Spline object containing points array: [{ x, z }, ...]
 * @param {number} startS Sector start normalized [0..1]
 * @param {number} finishS Sector finish normalized [0..1]
 * @param {Object} [options]
 * @param {number} [options.width=512]
 * @param {number} [options.height=288]
 * @param {string} [options.testId=""]
 * @returns {string} PNG Data URL
 */
export function generateMiniatureDataUrl(spline, startS = 0.0, finishS = 1.0, options = {}) {
  const width = options.width || 512;
  const height = options.height || 288;
  const testId = options.testId || "";

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");

  // 1. Dark high-contrast background gradient
  const bgGrad = ctx.createLinearGradient(0, 0, width, height);
  bgGrad.addColorStop(0, "#0c0f14");
  bgGrad.addColorStop(1, "#13171e");
  ctx.fillStyle = bgGrad;
  ctx.fillRect(0, 0, width, height);

  // Subtle grid lines
  ctx.strokeStyle = "rgba(255, 255, 255, 0.03)";
  ctx.lineWidth = 1;
  for (let x = 32; x < width; x += 32) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }
  for (let y = 32; y < height; y += 32) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }

  const points = spline?.points || spline?.waypoints || [];
  if (points.length < 2) {
    // Fallback placeholder
    ctx.fillStyle = "#5c687a";
    ctx.font = "bold 16px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("No Track Spline Available", width / 2, height / 2);
    return canvas.toDataURL("image/png");
  }

  const bounds = computeBounds(points);

  // 2. Full Circuit Silhouette (slate gray)
  ctx.strokeStyle = "#262e3b";
  ctx.lineWidth = 4;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.beginPath();
  const [firstX, firstY] = projectPoint(points[0].x, points[0].z, bounds, width, height);
  ctx.moveTo(firstX, firstY);
  for (let i = 1; i < points.length; i++) {
    const [px, py] = projectPoint(points[i].x, points[i].z, bounds, width, height);
    ctx.lineTo(px, py);
  }
  ctx.closePath();
  ctx.stroke();

  // 3. Highlighted Sector Trajectory (Vibrant Cyan Glow + Stroke)
  const n = points.length;
  let idxStart = Math.round(startS * (n - 1));
  let idxFinish = Math.round(finishS * (n - 1));

  ctx.save();
  ctx.shadowColor = "#38bdf8";
  ctx.shadowBlur = 10;
  ctx.strokeStyle = "#38bdf8";
  ctx.lineWidth = 7;
  ctx.beginPath();

  if (idxStart <= idxFinish) {
    const [sx, sy] = projectPoint(points[idxStart].x, points[idxStart].z, bounds, width, height);
    ctx.moveTo(sx, sy);
    for (let i = idxStart + 1; i <= idxFinish; i++) {
      const [px, py] = projectPoint(points[i].x, points[i].z, bounds, width, height);
      ctx.lineTo(px, py);
    }
  } else {
    // Wraps past finish line
    const [sx, sy] = projectPoint(points[idxStart].x, points[idxStart].z, bounds, width, height);
    ctx.moveTo(sx, sy);
    for (let i = idxStart + 1; i < n; i++) {
      const [px, py] = projectPoint(points[i].x, points[i].z, bounds, width, height);
      ctx.lineTo(px, py);
    }
    for (let i = 0; i <= idxFinish; i++) {
      const [px, py] = projectPoint(points[i].x, points[i].z, bounds, width, height);
      ctx.lineTo(px, py);
    }
  }
  ctx.stroke();
  ctx.restore();

  // 4. Start Gate Line & Marker (Emerald Green)
  const pStart = getPointAtProgress(points, startS);
  const [sPx, sPy] = projectPoint(pStart.x, pStart.z, bounds, width, height);
  const sNormal = pStart.angle + Math.PI / 2;
  const gateArm = 14;

  ctx.strokeStyle = "#10b981";
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(sPx - Math.cos(sNormal) * gateArm, sPy + Math.sin(sNormal) * gateArm);
  ctx.lineTo(sPx + Math.cos(sNormal) * gateArm, sPy - Math.sin(sNormal) * gateArm);
  ctx.stroke();

  ctx.fillStyle = "#10b981";
  ctx.beginPath();
  ctx.arc(sPx, sPy, 4.5, 0, Math.PI * 2);
  ctx.fill();

  // 5. Finish Gate Line & Marker (Crimson Red / Checkered)
  const pFinish = getPointAtProgress(points, finishS);
  const [fPx, fPy] = projectPoint(pFinish.x, pFinish.z, bounds, width, height);
  const fNormal = pFinish.angle + Math.PI / 2;

  ctx.strokeStyle = "#ef4444";
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(fPx - Math.cos(fNormal) * gateArm, fPy + Math.sin(fNormal) * gateArm);
  ctx.lineTo(fPx + Math.cos(fNormal) * gateArm, fPy - Math.sin(fNormal) * gateArm);
  ctx.stroke();

  ctx.fillStyle = "#ef4444";
  ctx.beginPath();
  ctx.arc(fPx, fPy, 4.5, 0, Math.PI * 2);
  ctx.fill();

  // 6. Test ID Badge watermark in top-left
  if (testId) {
    ctx.fillStyle = "rgba(15, 23, 42, 0.75)";
    ctx.fillRect(16, 16, 70, 26);
    ctx.strokeStyle = "rgba(56, 189, 248, 0.4)";
    ctx.lineWidth = 1;
    ctx.strokeRect(16, 16, 70, 26);

    ctx.fillStyle = "#38bdf8";
    ctx.font = "bold 13px monospace";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(testId, 51, 29);
  }

  return canvas.toDataURL("image/png");
}

/**
 * Asynchronously converts miniature canvas to a binary Blob for ZIP inclusion.
 * @param {Object} spline
 * @param {number} startS
 * @param {number} finishS
 * @param {Object} [options]
 * @returns {Promise<Blob>}
 */
export function generateMiniatureBlob(spline, startS = 0.0, finishS = 1.0, options = {}) {
  const dataUrl = generateMiniatureDataUrl(spline, startS, finishS, options);
  return fetch(dataUrl).then((res) => res.blob());
}
