/**
 * telemetry-engine.js
 * Client-Side Telemetry & Target Physics Calculator.
 *
 * Implements mathematical parity with Assetto Corsa AI Telemetry Profile calculations
 * without requiring any Python backend:
 *   - Continuous trajectory query and linear interpolation
 *   - Backward distance integration for vehicle countdown run-up (spawn_offset)
 *   - Forward traversal integration under launch acceleration & stop-box braking
 *   - Gran Turismo medal ceiling derivation (Gold/Silver/Bronze)
 */

export class TelemetryEngine {
  /**
   * @param {Object} profile Telemetry profile data matching TelemetryProfile JSON schema
   */
  constructor(profile) {
    if (!profile || !Array.isArray(profile.samples) || profile.samples.length === 0) {
      throw new Error("Invalid telemetry profile: missing or empty samples array");
    }

    this.trackId = profile.track_id || "";
    this.trackLayout = profile.track_layout || "";
    this.carId = profile.car_id || "";
    this.aiLevel = Number(profile.ai_level ?? 100);
    this.source = profile.source || "custom_upload";
    this.recordedAt = profile.recorded_at || new Date().toISOString();
    this.totalTrackLengthM = Number(profile.total_track_length_m || 0);
    this.lapTimeS = Number(profile.lap_time_s || 0);

    // Sort samples strictly by distance_m
    this.samples = profile.samples.slice().sort((a, b) => a.distance_m - b.distance_m);

    if (this.totalTrackLengthM <= 0) {
      const maxSampleDist = this.samples[this.samples.length - 1].distance_m;
      this.totalTrackLengthM = maxSampleDist > 0 ? maxSampleDist : 1000.0;
    }
  }

  /**
   * Queries speed (km/h), gear, and RPM at exact distance along the track spline.
   * @param {number} distanceM Distance from start line in meters
   * @returns {{ speedKmh: number, gear: number, rpm: number }}
   */
  querySample(distanceM) {
    const tot = this.totalTrackLengthM;
    const d = ((distanceM % tot) + tot) % tot;
    const n = this.samples.length;

    if (d <= this.samples[0].distance_m) {
      const s0 = this.samples[n - 1];
      const s1 = this.samples[0];
      const span = s1.distance_m + (tot - s0.distance_m);
      const frac = span > 0 ? (d + (tot - s0.distance_m)) / span : 0;
      return {
        speedKmh: s0.speed_kmh + frac * (s1.speed_kmh - s0.speed_kmh),
        gear: frac < 0.5 ? s0.gear : s1.gear,
        rpm: Math.round(s0.rpm + frac * (s1.rpm - s0.rpm)),
      };
    }

    if (d >= this.samples[n - 1].distance_m) {
      const s0 = this.samples[n - 1];
      const s1 = this.samples[0];
      const span = s1.distance_m + (tot - s0.distance_m);
      const frac = span > 0 ? (d - s0.distance_m) / span : 0;
      return {
        speedKmh: s0.speed_kmh + frac * (s1.speed_kmh - s0.speed_kmh),
        gear: frac < 0.5 ? s0.gear : s1.gear,
        rpm: Math.round(s0.rpm + frac * (s1.rpm - s0.rpm)),
      };
    }

    // Binary search for interval
    let low = 0;
    let high = n - 1;
    while (low <= high) {
      const mid = (low + high) >> 1;
      if (this.samples[mid].distance_m <= d) {
        low = mid + 1;
      } else {
        high = mid - 1;
      }
    }

    const idx0 = Math.max(0, high);
    const idx1 = Math.min(n - 1, idx0 + 1);
    const s0 = this.samples[idx0];
    const s1 = this.samples[idx1];
    const span = s1.distance_m - s0.distance_m;
    const frac = span > 0 ? (d - s0.distance_m) / span : 0;

    return {
      speedKmh: s0.speed_kmh + frac * (s1.speed_kmh - s0.speed_kmh),
      gear: frac < 0.5 ? s0.gear : s1.gear,
      rpm: Math.round(s0.rpm + frac * (s1.rpm - s0.rpm)),
    };
  }

  /**
   * Numerically integrates backward along the velocity curve to find spawn position.
   * @param {number} gateDistM Distance at the start gate
   * @param {number} countdownSec Seconds to integrate backward
   * @param {number} stepDt Time step in seconds (default 0.05s)
   * @returns {number} Spawn distance along the track in meters
   */
  integrateDistanceBackward(gateDistM, countdownSec = 3.0, stepDt = 0.05) {
    const tot = this.totalTrackLengthM;
    let currDist = gateDistM;
    let tAccum = 0.0;

    while (tAccum < countdownSec) {
      const { speedKmh } = this.querySample(currDist);
      const vMs = Math.max(5.0, speedKmh / 3.6);
      const dt = Math.min(stepDt, countdownSec - tAccum);
      const ds = vMs * dt;
      currDist = ((currDist - ds) % tot + tot) % tot;
      tAccum += dt;
    }

    return currDist;
  }

  /**
   * Calculates countdown run-up distance (spawn_offset) and handover physics.
   * @param {number} gateProgress Normalized progress [0..1] of the start gate
   * @param {number} countdownSec Countdown duration in seconds (default 3.0)
   * @returns {Object} Gate and spawn physics object
   */
  calculateGatePhysics(gateProgress, countdownSec = 3.0) {
    const tot = this.totalTrackLengthM;
    const gateProgNorm = ((gateProgress % 1.0) + 1.0) % 1.0;
    const gateDist = (gateProgNorm * tot) % tot;
    const gateSample = this.querySample(gateDist);

    const spawnDist = this.integrateDistanceBackward(gateDist, countdownSec);
    const spawnOffset = ((gateDist - spawnDist + tot) % tot);
    const spawnSample = this.querySample(spawnDist);
    const spawnProg = tot > 0 ? spawnDist / tot : 0.0;

    return {
      gate_progress: Number(gateProgNorm.toFixed(4)),
      gate_distance_m: Number(gateDist.toFixed(2)),
      speed_kmh: Number(gateSample.speedKmh.toFixed(1)),
      gear: gateSample.gear,
      rpm: gateSample.rpm,
      spawn_offset_m: Number(spawnOffset.toFixed(1)),
      spawn_progress: Number(spawnProg.toFixed(4)),
      spawn_distance_m: Number(spawnDist.toFixed(2)),
      spawn_speed_kmh: Number(spawnSample.speedKmh.toFixed(1)),
      spawn_gear: spawnSample.gear,
      spawn_rpm: spawnSample.rpm,
      countdown_sec: countdownSec,
      total_track_length_m: Number(tot.toFixed(2)),
      source: this.source,
      recorded_at: this.recordedAt,
    };
  }

  /**
   * Computes start distance and sector length handling wrap-around and full lap conditions.
   * @private
   */
  _computeSectorLength(startS, finishS, startMode) {
    const tot = this.totalTrackLengthM;
    const s0 = ((startS % 1.0) + 1.0) % 1.0;
    const s1 = Math.abs(finishS - 1.0) < 1e-4 ? 1.0 : ((finishS % 1.0) + 1.0) % 1.0;
    const startDist = s0 * tot;
    const finishDist = s1 * tot;

    const isFullLap =
      startMode === "FLYING_LAP" ||
      (s0 <= 0.005 && s1 >= 0.99) ||
      (Math.abs(s0 - s1) < 0.002 && (startMode === "FLYING_LAP" || startMode === "STANDING"));

    let secLen = isFullLap ? tot : s1 >= s0 ? finishDist - startDist : tot - startDist + finishDist;

    if (secLen <= 1.0) {
      secLen = isFullLap ? tot : 100.0;
    }

    return { startDist, secLen };
  }

  /**
   * Computes effective speed accounting for standing start launch and stop box deceleration.
   * @private
   */
  _effectiveSpeed(vFlyingMs, distTraveled, secLen, startMode, withStopBox, aLaunch = 6.0, aBrake = 9.0) {
    if (startMode !== "STANDING") {
      return vFlyingMs;
    }

    const vLaunch = Math.sqrt(2.0 * aLaunch * Math.max(0.2, distTraveled));
    let vEff = Math.min(vFlyingMs, vLaunch);

    if (withStopBox) {
      const distRem = Math.max(0.0, secLen - distTraveled);
      const vStop = Math.sqrt(2.0 * aBrake * Math.max(0.2, distRem));
      vEff = Math.min(vEff, vStop);
    }

    return Math.max(2.5, vEff);
  }

  /**
   * Numerically integrates elapsed time across sector length.
   * @private
   */
  _integrateTraversalTime(startDist, secLen, startMode, withStopBox, stepM = 1.0) {
    const tot = this.totalTrackLengthM;
    const step = Math.max(0.5, Math.min(stepM, secLen / 500.0));
    let tAccum = 0.0;
    let distTraveled = 0.0;

    while (distTraveled < secLen) {
      const currD = (startDist + distTraveled) % tot;
      const { speedKmh } = this.querySample(currD);
      const vMs = this._effectiveSpeed(
        Math.max(5.0, speedKmh / 3.6),
        distTraveled,
        secLen,
        startMode,
        withStopBox
      );
      tAccum += step / vMs;
      distTraveled += step;
    }

    if (startMode === "STANDING" && withStopBox) {
      tAccum += 0.5; // 0.5s pause to verify complete standstill
    }

    return tAccum;
  }

  /**
   * Derives Gran Turismo Gold, Silver, and Bronze target times.
   * @private
   */
  _calculateMedalTargets(tAccum, startMode) {
    if (startMode === "ROLLING" || startMode === "FLYING_LAP") {
      const gold = Math.ceil(Number((tAccum * 0.98).toFixed(4)) * 10.0) / 10.0;
      const silver = Math.ceil(Number((tAccum * 1.05).toFixed(4)) * 10.0) / 10.0;
      const bronze = Math.ceil(Number((tAccum * 1.15).toFixed(4)) * 10.0) / 10.0;
      return { gold, silver, bronze };
    }

    const gold = Math.ceil(Number(tAccum.toFixed(4)) * 10.0) / 10.0;
    const silver = Math.ceil(Number((gold * (1.05 / 0.98)).toFixed(4)) * 10.0) / 10.0;
    const bronze = Math.ceil(Number((gold * (1.15 / 0.98)).toFixed(4)) * 10.0) / 10.0;
    return { gold, silver, bronze };
  }

  /**
   * Numerically integrates traversal time and calculates Gold/Silver/Bronze medal times.
   * @param {number} startS Normalized sector start [0..1]
   * @param {number} finishS Normalized sector finish [0..1]
   * @param {string} startMode "ROLLING" | "STANDING" | "FLYING_LAP"
   * @param {boolean} withStopBox Whether vehicle must come to complete halt inside stop box
   * @param {number} stepM Integration step size in meters (default 1.0m)
   * @returns {Object} Target calculation result
   */
  calculateSectorTargets(startS, finishS, startMode = "ROLLING", withStopBox = false, stepM = 1.0) {
    const { startDist, secLen } = this._computeSectorLength(startS, finishS, startMode);
    const tAccum = this._integrateTraversalTime(startDist, secLen, startMode, withStopBox, stepM);
    const { gold, silver, bronze } = this._calculateMedalTargets(tAccum, startMode);

    return {
      gold_seconds: gold,
      silver_seconds: silver,
      bronze_seconds: bronze,
      sector_time_s: Number(tAccum.toFixed(3)),
      sector_length_m: Number(secLen.toFixed(1)),
      start_dist_m: Number(startDist.toFixed(1)),
    };
  }
}
