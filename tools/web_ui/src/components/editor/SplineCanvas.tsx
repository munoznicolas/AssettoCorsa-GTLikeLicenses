import React, { useRef, useEffect } from "react";
import { SplineData } from "../../types";

interface Props {
  spline: SplineData | null;
  startS: number;
  finishS: number;
  isFullLap: boolean;
  onStartChange: (s: number) => void;
  onFinishChange: (s: number) => void;
  onFullLapToggle: (full: boolean) => void;
}

export const SplineCanvas: React.FC<Props> = ({
  spline,
  startS,
  finishS,
  isFullLap,
  onStartChange,
  onFinishChange,
  onFullLapToggle,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Sector distance calculation
  const totalLengthM = spline?.total_length_m || 0;
  let sectorDistM = 0;
  if (totalLengthM > 0) {
    if (isFullLap) {
      sectorDistM = totalLengthM;
    } else if (finishS >= startS) {
      sectorDistM = (finishS - startS) * totalLengthM;
    } else {
      sectorDistM = (1.0 - startS + finishS) * totalLengthM;
    }
  }

  // Draw on canvas whenever spline or positions change
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    if (!spline || !spline.points || spline.points.length === 0) {
      ctx.fillStyle = "#19191b";
      ctx.fillRect(0, 0, w, h);
      ctx.fillStyle = "#71717a";
      ctx.font = "13px Inter, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Select a track with an AI spline to view 2D map", w / 2, h / 2);
      return;
    }

    const pts = spline.points;
    let minX = Infinity,
      maxX = -Infinity,
      minY = Infinity,
      maxY = -Infinity;
    for (const p of pts) {
      if (p.x < minX) minX = p.x;
      if (p.x > maxX) maxX = p.x;
      if (p.y < minY) minY = p.y;
      if (p.y > maxY) maxY = p.y;
    }

    const bw = maxX - minX || 1;
    const bh = maxY - minY || 1;
    const pad = 28;
    const scale = Math.min((w - pad * 2) / bw, (h - pad * 2) / bh);
    const ox = (w - bw * scale) / 2 - minX * scale;
    const oy = (h - bh * scale) / 2 - minY * scale;

    const toX = (wx: number) => wx * scale + ox;
    const toY = (wy: number) => wy * scale + oy;

    // 1. Draw base circuit track line
    const isDark = document.documentElement.getAttribute("data-theme") !== "light";
    ctx.lineWidth = 5;
    ctx.strokeStyle = isDark ? "rgba(255, 255, 255, 0.18)" : "rgba(0, 0, 0, 0.15)";
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.beginPath();
    ctx.moveTo(toX(pts[0].x), toY(pts[0].y));
    for (let i = 1; i < pts.length; i++) {
      ctx.lineTo(toX(pts[i].x), toY(pts[i].y));
    }
    ctx.closePath();
    ctx.stroke();

    // 2. Draw active sector ribbon
    ctx.lineWidth = 4;
    ctx.strokeStyle = "#f59e0b"; // Gold sector
    ctx.beginPath();
    let started = false;
    for (let i = 0; i < pts.length; i++) {
      const s = pts[i].s;
      let inSector = false;
      if (isFullLap) {
        inSector = true;
      } else if (finishS >= startS) {
        inSector = s >= startS && s <= finishS;
      } else {
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

    // 3. Draw Start Gate point
    const findClosest = (targetS: number) => {
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
    };

    const startPt = findClosest(startS);
    if (startPt) {
      const sx = toX(startPt.x);
      const sy = toY(startPt.y);
      ctx.fillStyle = "#4cc38a";
      ctx.beginPath();
      ctx.arc(sx, sy, 6, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // 4. Draw Finish Gate point
    const finishPt = findClosest(finishS);
    if (finishPt) {
      const fx = toX(finishPt.x);
      const fy = toY(finishPt.y);
      ctx.fillStyle = "#e5484d";
      ctx.beginPath();
      ctx.arc(fx, fy, 6, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  }, [spline, startS, finishS, isFullLap]);

  return (
    <div id="card-gates-spline" className="card form-card">
      <div className="card-title">
        <span>Test Bounds & Track Positions</span>
      </div>

      {/* Canvas */}
      <div className="map-container">
        <div className="canvas-wrapper">
          <canvas ref={canvasRef} width={700} height={300} style={{ width: "100%", height: "300px" }} />
        </div>
      </div>

      {/* Starting and Ending Position Sliders */}
      <div className="form-grid cols-2 mt-3" style={{ marginTop: "12px" }}>
        {/* Start Gate */}
        <div className="form-group gate-control-group gate-start">
          <div className="gate-header">
            <span className="badge badge-success gate-badge">Start Gate</span>
            <label htmlFor="slider-start-s" className="gate-label">
              Position: <span id="disp-start-s" style={{ display: "none" }}>{(startS * 100).toFixed(2)}%</span>
              <span id="disp-start-m">{Math.round(startS * totalLengthM)} m</span>
            </label>
            <input
              type="number"
              id="input-start-s"
              className="form-control num-input mono"
              min="0"
              max="1"
              step="0.0001"
              value={startS}
              disabled={isFullLap}
              onChange={(e) => onStartChange(Math.max(0, Math.min(1, parseFloat(e.target.value) || 0)))}
            />
          </div>
          <input
            type="range"
            id="slider-start-s"
            className="range-slider range-start"
            min="0"
            max="1"
            step="0.0005"
            value={startS}
            disabled={isFullLap}
            onChange={(e) => onStartChange(parseFloat(e.target.value) || 0)}
          />
        </div>

        {/* Finish Gate */}
        <div className="form-group gate-control-group gate-finish">
          <div className="gate-header">
            <span className="badge badge-danger gate-badge">Finish Gate</span>
            <label htmlFor="slider-finish-s" className="gate-label">
              Position: <span id="disp-finish-s" style={{ display: "none" }}>{(finishS * 100).toFixed(2)}%</span>
              <span id="disp-finish-m">{Math.round(finishS * totalLengthM)} m</span>
            </label>
            <input
              type="number"
              id="input-finish-s"
              className="form-control num-input mono"
              min="0"
              max="1"
              step="0.0001"
              value={finishS}
              disabled={isFullLap}
              onChange={(e) => onFinishChange(Math.max(0, Math.min(1, parseFloat(e.target.value) || 0)))}
            />
          </div>
          <input
            type="range"
            id="slider-finish-s"
            className="range-slider range-finish"
            min="0"
            max="1"
            step="0.0005"
            value={finishS}
            disabled={isFullLap}
            onChange={(e) => onFinishChange(parseFloat(e.target.value) || 0)}
          />
        </div>
      </div>

      <div id="sector-stats" className="sector-badge-bar" style={{ marginTop: "10px" }}>
        Sector Distance: <strong>{Math.round(sectorDistM)} m</strong>
      </div>
    </div>
  );
};
