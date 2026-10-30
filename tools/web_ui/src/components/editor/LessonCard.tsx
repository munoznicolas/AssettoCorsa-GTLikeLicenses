import React from "react";

interface Props {
  testId: string;
  objective: string;
  description: string;
  onObjectiveChange: (val: string) => void;
  onDescriptionChange: (val: string) => void;
}

export const LessonCard: React.FC<Props> = ({
  testId,
  objective,
  description,
  onObjectiveChange,
  onDescriptionChange,
}) => {
  return (
    <div id="card-lesson-info" className="card form-card">
      <div className="card-title">Curriculum Lesson & Description</div>
      <div className="form-grid cols-2">
        <div className="form-group">
          <label htmlFor="input-objective">Lesson Objective</label>
          <input
            type="text"
            id="input-objective"
            className="form-control"
            placeholder="Driving technique to practice"
            value={objective}
            onChange={(e) => onObjectiveChange(e.target.value)}
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="input-test-id">Test Identifier</label>
          <input
            type="text"
            id="input-test-id"
            className="form-control mono"
            value={testId}
            readOnly
            title="Automatically assigned sequentially based on position in this license tier"
          />
        </div>
      </div>
      <div className="form-group" style={{ marginTop: "12px" }}>
        <label htmlFor="input-description">Test Description / Instruction</label>
        <textarea
          id="input-description"
          className="form-control"
          rows={2}
          placeholder="Instruction displayed during countdown"
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value)}
          required
        />
      </div>
    </div>
  );
};
