import React, { useState, useEffect, useMemo } from "react";
import { Flag, Timer, Zap, Scale, Search } from "lucide-react";
import { ReferenceTest } from "../../types";
import { api } from "../../api/client";

export const ReferenceView: React.FC = () => {
  const [tests, setTests] = useState<ReferenceTest[]>([]);
  const [selectedGame, setSelectedGame] = useState("ALL");
  const [selectedTier, setSelectedTier] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    api
      .getReferenceTests()
      .then((res) => {
        if (mounted) {
          setTests(res.tests || (res as any).reference_tests || []);
        }
      })
      .catch((err) => console.warn("Failed to load reference tests:", err))
      .finally(() => {
        if (mounted) setIsLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const games = ["ALL", "GT1", "GT2", "GT3", "GT4", "GT5", "GT6", "GT7", "AC Mod"];

  const filteredTests = useMemo(() => {
    return tests.filter((t) => {
      if (selectedGame !== "ALL" && t.game !== selectedGame) return false;
      if (selectedTier !== "ALL" && t.tier !== selectedTier) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const matches =
          t.code.toLowerCase().includes(q) ||
          (t.title || t.test || "").toLowerCase().includes(q) ||
          t.car.toLowerCase().includes(q) ||
          t.track.toLowerCase().includes(q) ||
          (t.layout || "").toLowerCase().includes(q);
        if (!matches) return false;
      }
      return true;
    });
  }, [tests, selectedGame, selectedTier, searchQuery]);

  // Aggregate metrics
  const totalCount = filteredTests.length;
  const validHp = filteredTests.filter((t) => t.hp && t.hp > 0);
  const avgHp =
    validHp.length > 0
      ? Math.round(validHp.reduce((acc, t) => acc + (t.hp || 0), 0) / validHp.length)
      : 0;

  const validPw = filteredTests.filter((t) => t.pw && t.pw > 0);
  const avgPw =
    validPw.length > 0
      ? (validPw.reduce((acc, t) => acc + (t.pw || 0), 0) / validPw.length).toFixed(2)
      : "5.09";

  const timed = filteredTests.filter(
    (t) =>
      (t.gold_s !== undefined && isFinite(t.gold_s)) ||
      (t.gold_seconds !== undefined && isFinite(t.gold_seconds))
  );
  const totalGoldSec = timed.reduce(
    (acc, t) => acc + (t.gold_s ?? t.gold_seconds ?? 0),
    0
  );
  const avgGoldSec = timed.length > 0 ? totalGoldSec / timed.length : 0;
  const formatTime = (sec: number) => {
    if (!sec || !isFinite(sec)) return "0:00.000";
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s < 10 ? "0" : ""}${s.toFixed(3)}`;
  };

  return (
    <div id="reference-view" className="reference-view">
      <div className="ref-header">
        <div className="ref-title-group">
          <h2>Gran Turismo Driving School Benchmarks</h2>
        </div>

        {/* Game filter pills */}
        <div className="ref-controls">
          <span className="ref-control-label">Select Game:</span>
          <div id="game-selector-pills" className="game-pills">
            {games.map((g, idx) => (
              <React.Fragment key={g}>
                {idx === 5 && <div className="game-pills-break" />}
                <button
                  className={`pill-btn ${selectedGame === g ? "active" : ""}`}
                  onClick={() => setSelectedGame(g)}
                >
                  {g}
                </button>
              </React.Fragment>
            ))}
          </div>
        </div>
      </div>

      {/* Condensed Metrics Summary Card */}
      <div className="ref-card ref-metrics-summary-card">
        <div className="metric-stat-item">
          <div className="metric-icon">
            <Flag size={18} strokeWidth={2} />
          </div>
          <div className="metric-info">
            <span className="metric-label">Total Tests</span>
            <span className="metric-value">{totalCount}</span>
          </div>
        </div>

        <div className="metric-stat-divider" />

        <div className="metric-stat-item">
          <div className="metric-icon">
            <Timer size={18} strokeWidth={2} />
          </div>
          <div className="metric-info">
            <span className="metric-label">Avg Gold Duration</span>
            <span className="metric-value">{timed.length > 0 ? formatTime(avgGoldSec) : "0:00.000"}</span>
          </div>
        </div>

        <div className="metric-stat-divider" />

        <div className="metric-stat-item">
          <div className="metric-icon">
            <Zap size={18} strokeWidth={2} />
          </div>
          <div className="metric-info">
            <span className="metric-label">Average Horsepower</span>
            <span className="metric-value">{avgHp} HP</span>
          </div>
        </div>

        <div className="metric-stat-divider" />

        <div className="metric-stat-item">
          <div className="metric-icon">
            <Scale size={18} strokeWidth={2} />
          </div>
          <div className="metric-info">
            <span className="metric-label">Avg Power / Weight</span>
            <span className="metric-value">{avgPw} kg/hp</span>
          </div>
        </div>
      </div>

      {/* Documentation Table */}
      <div className="ref-card table-card" style={{ marginTop: "16px", marginBottom: "24px" }}>
        <div className="table-card-header">
          <div className="table-title">
            <h3 style={{ fontSize: "14px", fontWeight: 600 }}>Constant Values Documentation Table</h3>
          </div>
          <div className="table-filters" style={{ display: "flex", gap: "10px" }}>
            <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
              <Search size={14} style={{ position: "absolute", left: 10, color: "var(--text-dim)" }} />
              <input
                type="text"
                className="form-control table-search"
                style={{ paddingLeft: "30px", height: "32px", fontSize: "12px" }}
                placeholder="Search test, car, track, layout..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>
        </div>

        <div className="table-responsive" style={{ maxHeight: "500px", overflowY: "auto" }}>
          <table className="ref-data-table">
            <thead>
              <tr>
                <th>Test ID</th>
                <th>Game</th>
                <th>Tier</th>
                <th>Title</th>
                <th>Car Model</th>
                <th>HP</th>
                <th>P/W (kg/hp)</th>
                <th>Track / Sector</th>
                <th>Gold Target</th>
              </tr>
            </thead>
            <tbody>
              {filteredTests.slice(0, 100).map((t, idx) => (
                <tr key={`${t.game}-${t.code}-${idx}`}>
                  <td className="mono" style={{ color: "var(--accent-gold)", fontWeight: 600 }}>
                    {t.code}
                  </td>
                  <td>{t.game}</td>
                  <td>{t.tier}</td>
                  <td style={{ fontWeight: 500 }}>{t.title || t.test}</td>
                  <td>{t.car}</td>
                  <td className="mono">{t.hp || "--"}</td>
                  <td className="mono">{t.pw ? Number(t.pw).toFixed(2) : "--"}</td>
                  <td>{t.track}</td>
                  <td className="mono" style={{ color: "var(--accent-gold)" }}>
                    {t.gold}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
