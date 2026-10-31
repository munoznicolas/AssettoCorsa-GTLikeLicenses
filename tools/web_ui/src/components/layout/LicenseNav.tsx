import React from "react";
import { BarChart3 } from "lucide-react";
import { useCurriculum } from "../../context/CurriculumContext";

interface Props {
  activeView: "editor" | "reference";
  onSelectView: (view: "editor" | "reference") => void;
  onSelectTier?: () => void;
}

export const LicenseNav: React.FC<Props> = ({ activeView, onSelectView, onSelectTier }) => {
  const { curriculum, activeTierIndex, selectTier } = useCurriculum();

  return (
    <nav className="license-nav">
      <div className="nav-tabs-wrapper">
        <div id="license-tabs" className="tab-container">
          {curriculum.map((tier, idx) => {
            const isActive = activeView === "editor" && idx === activeTierIndex;
            const badgeFile =
              tier.badge_asset ||
              (tier.code === "GT_LIC_B"
                ? "series_b_badge.png"
                : tier.code === "GT_LIC_A"
                ? "series_a_badge.png"
                : tier.code === "GT_LIC_IB"
                ? "series_ib_badge.png"
                : tier.code === "GT_LIC_IA"
                ? "series_ia_badge.png"
                : tier.code === "GT_LIC_S"
                ? "series_s_badge.png"
                : null);

            return (
              <button
                key={tier.code || tier.name || idx}
                className={`license-tab ${isActive ? "active" : ""}`}
                title={`${tier.name} (${tier.tests.length} Tests)`}
                aria-label={tier.name}
                onClick={() => {
                  onSelectView("editor");
                  selectTier(idx);
                  onSelectTier?.();
                }}
              >
                {badgeFile && (
                  <img
                    className="tab-badge-img"
                    src={`/assets/career_ui/${badgeFile}`}
                    alt={tier.tier_name || tier.name}
                    loading="eager"
                  />
                )}
                <span className="tab-label">{tier.tier_name || tier.name}</span>
                <span className="tab-count">{tier.tests.length}</span>
              </button>
            );
          })}
        </div>

        <div className="nav-divider" />

        <div className="extra-tabs-container">
          <button
            id="tab-btn-reference"
            className={`license-tab reference-tab ${activeView === "reference" ? "active" : ""}`}
            title="Gran Turismo Benchmark Data & Visualizations (406 Tests)"
            aria-label="Gran Turismo Benchmark Data & Visualizations"
            onClick={() => onSelectView("reference")}
          >
            <BarChart3 size={14} strokeWidth={2} className="ref-tab-icon" />
            <span className="ref-tab-label">GT Values</span>
            <span className="tab-count" id="ref-total-badge">
              406
            </span>
          </button>
        </div>
      </div>
    </nav>
  );
};
