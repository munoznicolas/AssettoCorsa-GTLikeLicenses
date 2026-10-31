import React, { useEffect, useState } from "react";
import { useCurriculum } from "../../context/CurriculumContext";
import { FormHeader } from "./FormHeader";
import { LessonCard } from "./LessonCard";
import { TrackVehicleSection } from "./TrackVehicleSection";
import { SplineCanvas } from "./SplineCanvas";
import { StartModeCard } from "./StartModeCard";
import { TargetTimesCard } from "./TargetTimesCard";
import { api } from "../../api/client";

interface Props {
  onShowToast: (msg: string, type?: "info" | "success" | "error") => void;
  onBack?: () => void;
}

export const TestEditor: React.FC<Props> = ({ onShowToast, onBack }) => {
  const {
    activeTest,
    tracks,
    cars,
    currentSpline,
    updateActiveTest,
    saveActiveTier,
    deleteActiveTest,
    isSaving,
  } = useCurriculum();

  const [isFullLap, setIsFullLap] = useState(false);

  useEffect(() => {
    if (activeTest) {
      const full = (activeTest.start_s ?? 0) === 0 && (activeTest.finish_s ?? 1) === 1;
      setIsFullLap(full);
    }
  }, [activeTest?.test_id]);

  if (!activeTest) {
    return (
      <main className="editor-pane">
        <div className="empty-state">
          <h3>No Test Selected</h3>
          <p>Select a test from the left panel to inspect or edit.</p>
        </div>
      </main>
    );
  }

  const handleTrackChange = async (newTrackId: string) => {
    updateActiveTest({ track_id: newTrackId, track_layout: "" });
  };

  const handleLayoutChange = (newLayout: string) => {
    updateActiveTest({ track_layout: newLayout });
  };

  const handleCarChange = (newCarId: string) => {
    updateActiveTest({ car_id: newCarId });
  };

  const handleSave = async () => {
    try {
      await saveActiveTier();
      onShowToast(`Saved ${activeTest.test_id} successfully!`, "success");
    } catch (err: any) {
      onShowToast(`Failed to save: ${err.message}`, "error");
    }
  };

  const handleDelete = async () => {
    if (window.confirm(`Delete test ${activeTest.test_id}: "${activeTest.title}"?`)) {
      await deleteActiveTest();
      onShowToast(`Deleted test ${activeTest.test_id}`, "info");
    }
  };

  const handleRunDemo = async () => {
    try {
      onShowToast(`Launching ${activeTest.test_id} in Assetto Corsa with AI demo...`, "info");
      await api.runLiveTest(activeTest.test_id);
    } catch (err: any) {
      onShowToast(`Launch failed: ${err.message}`, "error");
    }
  };

  return (
    <main className="editor-pane">
      <form
        id="test-form"
        className="editor-form"
        onSubmit={(e) => {
          e.preventDefault();
          handleSave();
        }}
      >
        {/* Header: Title + Watch AI Demo + Trashcan + Diskette */}
        <FormHeader
          testId={activeTest.test_id}
          title={activeTest.title}
          isSaving={isSaving}
          onBack={onBack}
          onTitleChange={(title) => updateActiveTest({ title })}
          onRunDemo={handleRunDemo}
          onDeleteTest={handleDelete}
          onSaveTest={handleSave}
        />

        {/* Section 1: Curriculum Lesson & Description */}
        <LessonCard
          testId={activeTest.test_id}
          objective={activeTest.objective || ""}
          description={activeTest.description || ""}
          onObjectiveChange={(objective) => updateActiveTest({ objective })}
          onDescriptionChange={(description) => updateActiveTest({ description })}
        />

        {/* Section 2: Track & Vehicle Selection (MUI Autocomplete) */}
        <TrackVehicleSection
          tracks={tracks}
          cars={cars}
          selectedTrackId={activeTest.track_id}
          selectedLayout={activeTest.track_layout || ""}
          selectedCarId={activeTest.car_id}
          onTrackChange={handleTrackChange}
          onLayoutChange={handleLayoutChange}
          onCarChange={handleCarChange}
        />

        {/* Section 3: Spline Canvas & Spatial Bounds */}
        <SplineCanvas
          spline={currentSpline}
          startS={activeTest.start_s ?? 0}
          finishS={activeTest.finish_s ?? 1}
          isFullLap={isFullLap}
          onStartChange={(start_s) => updateActiveTest({ start_s })}
          onFinishChange={(finish_s) => updateActiveTest({ finish_s })}
          onFullLapToggle={(full) => {
            setIsFullLap(full);
            if (full) {
              updateActiveTest({ start_s: 0.0, finish_s: 1.0 });
            }
          }}
        />

        {/* Section 4: Start Mode & Physics */}
        <StartModeCard
          startMode={activeTest.start_mode}
          withStopBox={Boolean(activeTest.with_stop_box)}
          rollingSpeedKmh={activeTest.rolling_speed_kmh}
          initialGear={activeTest.initial_gear}
          initialRpm={activeTest.initial_rpm}
          onStartModeChange={(start_mode) => updateActiveTest({ start_mode })}
          onStopBoxToggle={(with_stop_box) => updateActiveTest({ with_stop_box })}
        />

        {/* Section 5: Target Times */}
        <TargetTimesCard
          targets={activeTest.targets}
          onChange={(targets) => updateActiveTest({ targets })}
        />
      </form>
    </main>
  );
};
