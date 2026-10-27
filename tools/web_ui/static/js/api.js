/**
 * Resolves API URL, automatically mapping to static pre-rendered JSON files
 * when running on GitHub Pages or file protocol.
 * @param {string} endpoint
 * @returns {string}
 */
export function resolveApiPath(endpoint) {
  const isStatic =
    window.location.hostname.endsWith("github.io") ||
    window.location.protocol === "file:" ||
    Boolean(window.IS_STATIC_HOST);

  if (isStatic) {
    const clean = endpoint.startsWith("/") ? endpoint.slice(1) : endpoint;

    // Spline query endpoints: api/spline?track_id=...&layout=...
    if (clean.startsWith("api/spline?") || clean === "api/spline") {
      const url = new URL(clean, "http://dummy");
      const trackId = url.searchParams.get("track_id") || "";
      const layout = url.searchParams.get("layout") || "";
      const key = layout ? `${trackId}__${layout}` : trackId;
      return `./api/splines/${encodeURIComponent(key)}.json`;
    }

    const staticMap = {
      "curriculum": "api/curriculum.json",
      "tracks": "api/tracks.json",
      "cars": "api/cars.json",
      "reference_tests": "api/reference_tests.json",
      "telemetry/missing": "api/missing_telemetry.json",
    };

    const base = clean.replace(/^api\//, "").split("?")[0];
    if (staticMap[base]) {
      return `./${staticMap[base]}`;
    }
  }

  const rel = endpoint.startsWith("/") ? endpoint.slice(1) : endpoint;
  return `./${rel}`;
}

/**
 * api.js
 * Central REST API client for Assetto Corsa GT-Like License Test Designer.
 */

export const api = {
  /**
   * Fetch curriculum test catalogs.
   */
  async getCurriculum() {
    const res = await fetch(resolveApiPath("api/curriculum"));
    return await res.json();
  },

  /**
   * Save curriculum tier data.
   */
  async saveTier(tierName, tests) {
    const res = await fetch("/api/save_tier", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tier_name: tierName, tests }),
    });
    return await res.json();
  },

  /**
   * Fetch available tracks.
   * @param {boolean} allTracks If true, includes third-party tracks.
   */
  async getTracks(allTracks = false) {
    const res = await fetch(resolveApiPath(`api/tracks${allTracks ? "?all=1" : ""}`));
    return await res.json();
  },

  /**
   * Fetch available cars.
   * @param {boolean} allCars If true, includes third-party cars.
   */
  async getCars(allCars = false) {
    const res = await fetch(resolveApiPath(`api/cars${allCars ? "?all=1" : ""}`));
    return await res.json();
  },

  /**
   * Fetch 2D AI spline coordinates for a track and layout.
   */
  async getSpline(trackId, layout = "") {
    const query = new URLSearchParams({ track_id: trackId, layout: layout || "" });
    try {
      const res = await fetch(resolveApiPath(`api/spline?${query.toString()}`));
      if (res.ok) {
        return await res.json();
      }
      // If layout-specific file not found (e.g. 404), fallback to base track spline
      if (layout) {
        const fallbackQuery = new URLSearchParams({ track_id: trackId, layout: "" });
        const fallbackRes = await fetch(resolveApiPath(`api/spline?${fallbackQuery.toString()}`));
        if (fallbackRes.ok) {
          return await fallbackRes.json();
        }
      }
      return { success: false, error: "AI spline not found for this track layout" };
    } catch (e) {
      return { success: false, error: e.message };
    }
  },

  /**
   * Fetch Gran Turismo reference curriculum test data.
   */
  async getReferenceTests() {
    const res = await fetch(resolveApiPath("api/reference_tests"));
    return await res.json();
  },

  /**
   * Calculate or retrieve initial AI rolling speed from cached profiles / game engine.
   */
  async calculateInitialSpeed(payload) {
    const res = await fetch("/api/calculate_initial_speed", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return await res.json();
  },

  /**
   * Numerically integrates telemetry points to calculate Gold, Silver, Bronze targets and launch physics.
   */
  async calculateTargets(payload) {
    const res = await fetch("/api/calculate_targets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return await res.json();
  },

  /**
   * Get runner process queue and AC process status.
   */
  async getQueueStatus() {
    const res = await fetch("/api/queue/status");
    return await res.json();
  },

  /**
   * Cancel specific job or active AC simulation.
   */
  async cancelQueueJob({ jobId = null, cancelAll = false } = {}) {
    const res = await fetch("/api/queue/cancel", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: jobId, cancel_all: cancelAll }),
    });
    return await res.json();
  },

  /**
   * Fetch summary of rolling start tests missing track+car telemetry.
   */
  async getMissingTelemetry(tier = "ALL", includeFlying = true) {
    const query = new URLSearchParams({
      tier: tier || "ALL",
      include_flying: includeFlying ? "1" : "0",
    });
    const res = await fetch(resolveApiPath(`api/telemetry/missing?${query.toString()}`));
    return await res.json();
  },

  /**
   * Enqueue in-engine recording for all rolling start tests missing telemetry.
   */
  async queueMissingTelemetry(tier = "ALL", includeFlying = true) {
    const res = await fetch("/api/telemetry/queue_missing", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tier, include_flying: includeFlying }),
    });
    return await res.json();
  },

  /**
   * Enqueue or launch live AC session.
   */
  async runLiveTest(payload) {
    const res = await fetch("/api/run_test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return await res.json();
  },

  /**
   * Check status of an individual queue job.
   */
  async getJob(jobId) {
    const res = await fetch(`/api/job/${jobId}`);
    return await res.json();
  },

  /**
   * Trigger content rebuild and curriculum validation.
   */
  async generateContent() {
    const res = await fetch("/api/generate", { method: "POST" });
    return await res.json();
  },

  /**
   * Trigger Track Miniature Builder for a specific test.
   */
  async generateMiniature(testId, testData = null) {
    const res = await fetch("/api/generate_miniature", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ test_id: testId, test_data: testData }),
    });
    return await res.json();
  },

  /**
   * Trigger live sync directly to Assetto Corsa root.
   */
  async syncToAC() {
    const res = await fetch("/api/sync", { method: "POST" });
    return await res.json();
  },

  /**
   * Submits a recorded telemetry JSON file and Google ID token to the serverless gateway to create a PR.
   * @param {Object} params
   * @param {string} params.googleToken - Google OAuth JWT
   * @param {string} params.filename - e.g. "ks_brands_hatch__gp__lotus_elise_sc__ai100.json"
   * @param {Object} params.telemetryData - Parsed telemetry JSON payload
   * @param {string} [params.gatewayUrl] - Optional custom gateway URL
   */
  async submitTelemetryProfile({ googleToken, filename, telemetryData, gatewayUrl }) {
    const defaultGateway = "https://ac-telemetry-pr-gateway.workers.dev/submit";
    const url = gatewayUrl || localStorage.getItem("gt_pr_gateway_url") || defaultGateway;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        google_token: googleToken,
        filename,
        telemetry_data: telemetryData,
      }),
    });
    return await res.json();
  },
};