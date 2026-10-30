import React from "react";
import { Targets } from "../../types";

interface Props {
  targets?: Targets;
  onChange: (targets: Targets) => void;
}

export const TargetTimesCard: React.FC<Props> = ({ targets, onChange }) => {
  const gold = targets?.gold_seconds ?? 0;
  const silver = targets?.silver_seconds ?? 0;
  const bronze = targets?.bronze_seconds ?? 0;

  const hasOrderError = gold > 0 && silver > 0 && bronze > 0 && !(gold < silver && silver < bronze);

  const updateField = (key: "gold_seconds" | "silver_seconds" | "bronze_seconds", val: number) => {
    onChange({
      ...targets,
      [key]: val,
    });
  };

  return (
    <div id="card-target-times" className="card form-card">
      <div className="card-title">Target Times</div>
      <div className="form-grid cols-3 target-times-grid">
        {/* Gold */}
        <div className="form-group">
          <label htmlFor="target-gold" className="medal-label medal-gold">
            <span className="medal-dot gold"></span>Gold
          </label>
          <div className="input-suffix-wrapper">
            <input
              type="number"
              id="target-gold"
              className="form-control mono medal-input gold"
              step="0.001"
              min="0.1"
              value={gold || ""}
              placeholder="0.000"
              onChange={(e) => updateField("gold_seconds", parseFloat(e.target.value) || 0)}
              required
            />
            <span className="input-suffix">s</span>
          </div>
        </div>

        {/* Silver */}
        <div className="form-group">
          <label htmlFor="target-silver" className="medal-label medal-silver">
            <span className="medal-dot silver"></span>Silver
          </label>
          <div className="input-suffix-wrapper">
            <input
              type="number"
              id="target-silver"
              className="form-control mono medal-input silver"
              step="0.001"
              min="0.1"
              value={silver || ""}
              placeholder="0.000"
              onChange={(e) => updateField("silver_seconds", parseFloat(e.target.value) || 0)}
              required
            />
            <span className="input-suffix">s</span>
          </div>
        </div>

        {/* Bronze */}
        <div className="form-group">
          <label htmlFor="target-bronze" className="medal-label medal-bronze">
            <span className="medal-dot bronze"></span>Bronze
          </label>
          <div className="input-suffix-wrapper">
            <input
              type="number"
              id="target-bronze"
              className="form-control mono medal-input bronze"
              step="0.001"
              min="0.1"
              value={bronze || ""}
              placeholder="0.000"
              onChange={(e) => updateField("bronze_seconds", parseFloat(e.target.value) || 0)}
              required
            />
            <span className="input-suffix">s</span>
          </div>
        </div>
      </div>

      {hasOrderError && (
        <div id="target-error" className="target-validation-error" style={{ display: "block", marginTop: "10px" }}>
          Targets must satisfy Gold &lt; Silver &lt; Bronze
        </div>
      )}
    </div>
  );
};
