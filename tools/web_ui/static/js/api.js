/**
 * api.js
 * Central REST API client for Assetto Corsa GT-Like License Test Designer.
 */

export const api = {
  /**
   * Fetch curriculum test catalogs.
   */
  async getCurriculum() {
    const res = await fetch("/api/curriculum");
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
    const res = await fetch(`/api/tracks${allTracks ? "?all=1" : ""}`);
    return await res.json();
  },

  /**
   * Fetch available cars.
   * @param {boolean} allCars If true, includes third-party cars.
   */
  async getCars(allCars = false) {
    const res = await fetch(`/api/cars${allCars ? "?all=1" : ""}`);
    return await res.json();
  },

  /**
   * Fetch 2D AI spline coordinates for a track and layout.
   */
  async getSpline(trackId, layout = "") {
    const query = new URLSearchParams({ track_id: trackId, layout: layout || "" });
    const res = await fetch(`/api/spline?${query.toString()}`);
    return await res.json();
  },

  /**
   * Fetch Gran Turismo reference curriculum test data.
   */
  async getReferenceTests() {
    const res = await fetch("/api/reference_tests");
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
    const res = await fetch(`/api/telemetry/missing?${query.toString()}`);
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
   * Trigger live sync directly to Assetto Corsa root.
   */
  async syncToAC() {
    const res = await fetch("/api/sync", { method: "POST" });
    return await res.json();
  },
};

