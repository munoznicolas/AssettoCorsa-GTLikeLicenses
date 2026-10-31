import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";
import { LicenseTier, LicenseTest, Track, CarModel, SplineData } from "../types";
import { api } from "../api/client";

interface CurriculumContextType {
  curriculum: LicenseTier[];
  activeTierIndex: number;
  activeTestIndex: number;
  activeTier: LicenseTier | null;
  activeTest: LicenseTest | null;
  tracks: Track[];
  cars: CarModel[];
  currentSpline: SplineData | null;
  isLoading: boolean;
  isSaving: boolean;
  dirty: boolean;
  selectTier: (index: number) => void;
  selectTest: (index: number) => void;
  updateActiveTest: (fields: Partial<LicenseTest>) => void;
  saveActiveTier: () => Promise<void>;
  addTestToActiveTier: () => void;
  deleteActiveTest: () => Promise<void>;
  reorderTestsInActiveTier: (fromIndex: number, toIndex: number) => void;
  loadSplineForActiveTest: (trackId: string, layout: string) => Promise<void>;
  setCurrentSpline: (spline: SplineData | null) => void;
  reloadCurriculum: () => Promise<void>;
}

const CurriculumContext = createContext<CurriculumContextType | undefined>(undefined);

export const CurriculumProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [curriculum, setCurriculum] = useState<LicenseTier[]>([]);
  const [activeTierIndex, setActiveTierIndex] = useState(0);
  const [activeTestIndex, setActiveTestIndex] = useState(0);
  const [tracks, setTracks] = useState<Track[]>([]);
  const [cars, setCars] = useState<CarModel[]>([]);
  const [currentSpline, setCurrentSpline] = useState<SplineData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  const activeTier = curriculum[activeTierIndex] || null;
  const activeTest = activeTier?.tests[activeTestIndex] || null;

  const reloadCurriculum = useCallback(async () => {
    setIsLoading(true);
    try {
      const [currRes, tracksRes, carsRes] = await Promise.all([
        api.getCurriculum(),
        api.getTracks(),
        api.getCars(),
      ]);
      const tiersList = currRes.curriculum || currRes.tiers || [];
      setCurriculum(tiersList);
      setTracks(tracksRes.tracks || []);
      setCars(carsRes.cars || []);
    } catch (err) {
      console.error("Failed to load curriculum or catalog data:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    reloadCurriculum();
  }, [reloadCurriculum]);

  const loadSplineForActiveTest = useCallback(async (trackId: string, layout: string) => {
    if (!trackId) {
      setCurrentSpline(null);
      return;
    }
    try {
      const res: any = await api.getSpline(trackId, layout);
      const splineData = res?.spline || res;
      setCurrentSpline(splineData);
    } catch (err) {
      console.warn("Spline load failed:", err);
      setCurrentSpline(null);
    }
  }, []);

  // When test changes, load its spline
  useEffect(() => {
    if (activeTest?.track_id) {
      loadSplineForActiveTest(activeTest.track_id, activeTest.track_layout || "");
    } else {
      setCurrentSpline(null);
    }
  }, [activeTest?.track_id, activeTest?.track_layout, loadSplineForActiveTest]);

  const selectTier = (index: number) => {
    setActiveTierIndex(index);
    setActiveTestIndex(0);
  };

  const selectTest = (index: number) => {
    setActiveTestIndex(index);
  };

  const updateActiveTest = (fields: Partial<LicenseTest>) => {
    if (!activeTier || !activeTest) return;
    const normalizedFields: Partial<LicenseTest> = { ...fields };
    if (fields.objective !== undefined) {
      normalizedFields.lesson_objective = fields.objective;
    } else if (fields.lesson_objective !== undefined) {
      normalizedFields.objective = fields.lesson_objective;
    }
    if (fields.rolling_speed_kmh !== undefined) {
      normalizedFields.speed = fields.rolling_speed_kmh;
    } else if (fields.speed !== undefined) {
      normalizedFields.rolling_speed_kmh = fields.speed;
    }
    if (fields.spawn_offset_meters !== undefined) {
      normalizedFields.spawn_offset = fields.spawn_offset_meters;
    } else if (fields.spawn_offset !== undefined) {
      normalizedFields.spawn_offset_meters = fields.spawn_offset;
    }

    setCurriculum((prev) => {
      const newCurr = [...prev];
      const tier = { ...newCurr[activeTierIndex] };
      const tests = [...tier.tests];
      tests[activeTestIndex] = { ...tests[activeTestIndex], ...normalizedFields };
      tier.tests = tests;
      newCurr[activeTierIndex] = tier;
      return newCurr;
    });
    setDirty(true);
  };

  const saveActiveTier = async () => {
    if (!activeTier) return;
    setIsSaving(true);
    try {
      const tierName = activeTier.tier_name || activeTier.name;
      await api.saveTier(tierName, activeTier.tests);
      setDirty(false);
    } catch (err) {
      console.error("Save tier failed:", err);
      throw err;
    } finally {
      setIsSaving(false);
    }
  };

  const addTestToActiveTier = () => {
    if (!activeTier) return;
    const tierPrefix = activeTier.name.includes("Super")
      ? "S"
      : activeTier.name.includes("National B")
      ? "B"
      : activeTier.name.includes("National A")
      ? "A"
      : activeTier.name.includes("International B")
      ? "IB"
      : "IA";
    const nextNum = activeTier.tests.length + 1;
    const newTest: LicenseTest = {
      test_id: `${tierPrefix}-${nextNum}`,
      title: "New Curriculum Test",
      objective: "Technique to practice",
      description: "Instructions during countdown",
      track_id: tracks[0]?.track_id || "ks_vallelunga",
      track_layout: "",
      car_id: cars[0]?.car_id || "abarth500",
      start_mode: "STANDING",
      start_s: 0.0,
      finish_s: 1.0,
      targets: {
        gold_seconds: 30.0,
        silver_seconds: 32.5,
        bronze_seconds: 35.0,
      },
    };

    setCurriculum((prev) => {
      const newCurr = [...prev];
      const tier = { ...newCurr[activeTierIndex] };
      tier.tests = [...tier.tests, newTest];
      newCurr[activeTierIndex] = tier;
      return newCurr;
    });
    setActiveTestIndex(activeTier.tests.length);
    setDirty(true);
  };

  const deleteActiveTest = async () => {
    if (!activeTier || !activeTest) return;
    const newTests = activeTier.tests.filter((_, idx) => idx !== activeTestIndex);
    setCurriculum((prev) => {
      const newCurr = [...prev];
      const tier = { ...newCurr[activeTierIndex], tests: newTests };
      newCurr[activeTierIndex] = tier;
      return newCurr;
    });
    setActiveTestIndex(Math.max(0, activeTestIndex - 1));
    setDirty(true);
  };

  const reorderTestsInActiveTier = (fromIndex: number, toIndex: number) => {
    if (!activeTier || fromIndex === toIndex) return;
    if (fromIndex < 0 || fromIndex >= activeTier.tests.length) return;
    if (toIndex < 0 || toIndex >= activeTier.tests.length) return;

    setCurriculum((prev) => {
      const newCurr = [...prev];
      const tier = { ...newCurr[activeTierIndex] };
      const tests = [...tier.tests];
      const [moved] = tests.splice(fromIndex, 1);
      tests.splice(toIndex, 0, moved);

      const tierPrefix = activeTier.name.includes("Super")
        ? "S"
        : activeTier.name.includes("National B")
        ? "B"
        : activeTier.name.includes("National A")
        ? "A"
        : activeTier.name.includes("International B")
        ? "IB"
        : "IA";

      tier.tests = tests.map((t, idx) => ({
        ...t,
        test_id: `${tierPrefix}-${idx + 1}`,
      }));

      newCurr[activeTierIndex] = tier;
      return newCurr;
    });

    if (activeTestIndex === fromIndex) {
      setActiveTestIndex(toIndex);
    } else if (fromIndex < activeTestIndex && toIndex >= activeTestIndex) {
      setActiveTestIndex(activeTestIndex - 1);
    } else if (fromIndex > activeTestIndex && toIndex <= activeTestIndex) {
      setActiveTestIndex(activeTestIndex + 1);
    }

    setDirty(true);
  };

  return (
    <CurriculumContext.Provider
      value={{
        curriculum,
        activeTierIndex,
        activeTestIndex,
        activeTier,
        activeTest,
        tracks,
        cars,
        currentSpline,
        isLoading,
        isSaving,
        dirty,
        selectTier,
        selectTest,
        updateActiveTest,
        saveActiveTier,
        addTestToActiveTier,
        deleteActiveTest,
        reorderTestsInActiveTier,
        loadSplineForActiveTest,
        setCurrentSpline,
        reloadCurriculum,
      }}
    >
      {children}
    </CurriculumContext.Provider>
  );
};

export const useCurriculum = () => {
  const context = useContext(CurriculumContext);
  if (!context) {
    throw new Error("useCurriculum must be used within a CurriculumProvider");
  }
  return context;
};
