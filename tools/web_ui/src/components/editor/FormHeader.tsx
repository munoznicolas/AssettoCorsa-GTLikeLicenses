import React from "react";
import { Trash2, Save, Play, ChevronLeft } from "lucide-react";

interface Props {
  testId: string;
  title: string;
  isSaving: boolean;
  onBack?: () => void;
  onTitleChange: (newTitle: string) => void;
  onRunDemo: () => void;
  onDeleteTest: () => void;
  onSaveTest: () => void;
}

export const FormHeader: React.FC<Props> = ({
  testId,
  title,
  isSaving,
  onBack,
  onTitleChange,
  onRunDemo,
  onDeleteTest,
  onSaveTest,
}) => {
  return (
    <div className="form-header">
      <div className="form-title-group">
        {onBack && (
          <button
            type="button"
            id="btn-back-to-list"
            className="btn btn-secondary btn-sm mobile-back-btn"
            title="Back to Test List"
            aria-label="Back to Test List"
            onClick={onBack}
          >
            <ChevronLeft size={14} strokeWidth={2.5} />
            <span>Tests</span>
          </button>
        )}
        <span id="form-test-id-badge" className="badge badge-lg">
          {testId || "--"}
        </span>
        <label htmlFor="input-title" className="visually-hidden">
          Test Title
        </label>
        <input
          type="text"
          id="input-title"
          className="form-control title-input"
          placeholder="Test Title"
          aria-label="Test Title"
          value={title}
          onChange={(e) => onTitleChange(e.target.value)}
          required
        />
      </div>

      <div className="form-actions">
        {/* 1. Watch AI Demo (Desktop only) */}
        <button
          type="button"
          id="btn-run-live"
          className="btn btn-primary desktop-only"
          title="Launch this test in Assetto Corsa with AI autopilot demo (Desktop only)"
          onClick={onRunDemo}
        >
          <span>Watch AI Demo</span>
        </button>

        {/* 2. Trashcan (Delete) */}
        <button
          type="button"
          id="btn-delete-test"
          className="btn btn-danger btn-icon-only"
          title="Delete Test"
          aria-label="Delete Test"
          onClick={onDeleteTest}
        >
          <Trash2 size={16} strokeWidth={2} style={{ width: 16, height: 16, minWidth: 16, minHeight: 16, flexShrink: 0 }} aria-hidden="true" />
        </button>

        {/* 3. Diskette (Save) */}
        <button
          type="button"
          id="btn-save-test"
          className="btn btn-success btn-icon-only"
          title={isSaving ? "Saving..." : "Save Test"}
          aria-label="Save Test"
          disabled={isSaving}
          onClick={onSaveTest}
        >
          <Save size={16} strokeWidth={2} style={{ width: 16, height: 16, minWidth: 16, minHeight: 16, flexShrink: 0 }} aria-hidden="true" />
        </button>
      </div>
    </div>
  );
};
