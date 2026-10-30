import { LicenseTier, Track, CarModel, SplineData, ReferenceTest, Targets } from "../types";

export const API_BASE = "";

export async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error || `HTTP ${res.status}: ${res.statusText}`);
  }

  return res.json();
}

export const api = {
  getCurriculum: () =>
    fetchJson<{ success: boolean; curriculum?: LicenseTier[]; tiers?: LicenseTier[]; static_mode?: boolean }>(
      "/api/curriculum"
    ),

  saveTier: (tierName: string, tests: unknown[]) =>
    fetchJson<{ success: boolean; message?: string }>("/api/save_tier", {
      method: "POST",
      body: JSON.stringify({ tier_name: tierName, tests }),
    }),

  getTracks: () => fetchJson<{ tracks: Track[] }>("/api/tracks"),

  getCars: () => fetchJson<{ cars: CarModel[] }>("/api/cars"),

  getSpline: async (trackId: string, layout = ""): Promise<SplineData> => {
    const data = await fetchJson<{ success: boolean; spline?: SplineData } | SplineData>(
      `/api/spline?track_id=${encodeURIComponent(trackId)}&layout=${encodeURIComponent(layout)}`
    );
    if (data && typeof data === "object" && "spline" in data && data.spline) {
      return data.spline;
    }
    return data as SplineData;
  },

  calculateTargets: (trackId: string, layout: string, startS: number, finishS: number, carId: string, mode: string) =>
    fetchJson<Targets>(
      `/api/calculate_targets?track_id=${encodeURIComponent(trackId)}&layout=${encodeURIComponent(layout)}&start_s=${startS}&finish_s=${finishS}&car_id=${encodeURIComponent(carId)}&mode=${encodeURIComponent(mode)}`
    ),

  calculateInitialSpeed: (trackId: string, layout: string, startS: number, carId: string) =>
    fetchJson<{
      speed_kmh?: number;
      initial_gear?: number;
      initial_rpm?: number;
      spawn_offset_meters?: number;
      telemetry_available: boolean;
      source?: string;
    }>("/api/calculate_initial_speed", {
      method: "POST",
      body: JSON.stringify({
        track_id: trackId,
        track_layout: layout,
        start_s: startS,
        car_id: carId,
      }),
    }),

  runLiveTest: (testId: string) =>
    fetchJson<{ success: boolean; pid?: number }>("/api/run_test", {
      method: "POST",
      body: JSON.stringify({ test_id: testId }),
    }),

  getReferenceTests: () =>
    fetchJson<{ success: boolean; tests: ReferenceTest[]; count: number }>("/api/reference_tests"),

  getMissingTelemetry: (tier = "ALL") =>
    fetchJson<{
      missing_tests_count: number;
      unique_combos_count: number;
      missing_combos: Array<{
        track_id: string;
        track_layout: string;
        car_id: string;
        test_ids: string[];
        is_cached: boolean;
        is_queued: boolean;
      }>;
    }>(`/api/telemetry/missing?tier=${encodeURIComponent(tier)}`),

  queueMissingTelemetry: (tier = "ALL", includeFlying = true) =>
    fetchJson<{ success: boolean; queued_count: number }>("/api/telemetry/queue_missing", {
      method: "POST",
      body: JSON.stringify({ tier, include_flying: includeFlying }),
    }),

  generateAndValidate: () =>
    fetchJson<{ success: boolean; log: string }>("/api/generate", {
      method: "POST",
      body: JSON.stringify({}),
    }),

  syncToAc: () =>
    fetchJson<{ success: boolean; log: string }>("/api/sync", {
      method: "POST",
      body: JSON.stringify({}),
    }),
};
