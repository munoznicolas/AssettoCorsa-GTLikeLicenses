/**
 * telemetry-store.js
 * Dual-Source Telemetry Resolution & IndexedDB Cache.
 *
 * Resolves AI telemetry profiles on-demand:
 *   1. Local IndexedDB cache for user-uploaded custom telemetry recordings.
 *   2. Precalculated static telemetry JSON files from repository / GitHub CDN.
 */

import { TelemetryEngine } from "./telemetry-engine.js";
import { resolveApiPath } from "./api.js";

const DB_NAME = "gt_telemetry_db";
const DB_VERSION = 1;
const STORE_NAME = "custom_profiles";

let dbInstance = null;
const memoryProfileCache = new Map();

/**
 * Initializes and returns the IndexedDB instance for custom telemetry recordings.
 * @returns {Promise<IDBDatabase>}
 */
function openTelemetryDb() {
  if (dbInstance) return Promise.resolve(dbInstance);

  return new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") {
      reject(new Error("IndexedDB is not supported in this environment"));
      return;
    }

    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "key" });
      }
    };

    request.onsuccess = (e) => {
      dbInstance = e.target.result;
      resolve(dbInstance);
    };

    request.onerror = (e) => {
      reject(e.target.error || new Error("Failed to open IndexedDB"));
    };
  });
}

/**
 * Derives canonical filename/key for telemetry combination.
 * Matches tools/telemetry/recorder.py profile_filename() exactly.
 * @param {string} trackId
 * @param {string} layout
 * @param {string} carId
 * @param {number} [aiLevel=100]
 * @returns {string} Filename, e.g. "magione__ks_toyota_gt86__ai100.json"
 */
export function getTelemetryFilename(trackId, layout, carId, aiLevel = 100) {
  const cleanTrack = String(trackId || "").trim().toLowerCase();
  const cleanLayout = String(layout || "").trim().toLowerCase();
  const cleanCar = String(carId || "").trim().toLowerCase();
  const level = Number(aiLevel || 100);

  if (cleanLayout) {
    return `${cleanTrack}__${cleanLayout}__${cleanCar}__ai${level}.json`;
  }
  return `${cleanTrack}__${cleanCar}__ai${level}.json`;
}

/**
 * Stores a user-uploaded custom telemetry profile into IndexedDB.
 * @param {Object} profileData Parsed TelemetryProfile JSON object
 * @returns {Promise<{ key: string, filename: string, profile: Object }>}
 */
export async function saveCustomTelemetryProfile(profileData) {
  if (!profileData || !profileData.track_id || !profileData.car_id) {
    throw new Error("Invalid telemetry profile: missing track_id or car_id");
  }

  const key = getTelemetryFilename(
    profileData.track_id,
    profileData.track_layout || "",
    profileData.car_id,
    profileData.ai_level || 100
  );

  const entry = {
    key,
    filename: key,
    track_id: profileData.track_id,
    track_layout: profileData.track_layout || "",
    car_id: profileData.car_id,
    ai_level: profileData.ai_level || 100,
    data: profileData,
    uploaded_at: Date.now(),
  };

  try {
    const db = await openTelemetryDb();
    await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readwrite");
      const store = tx.objectStore(STORE_NAME);
      const req = store.put(entry);
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  } catch (err) {
    console.warn("IndexedDB save failed, falling back to session memory:", err);
  }

  memoryProfileCache.set(key, profileData);
  return { key, filename: key, profile: profileData };
}

/**
 * Fetches a custom profile from IndexedDB or memory cache.
 * @param {string} key
 * @returns {Promise<Object|null>}
 */
export async function getCustomTelemetryProfile(key) {
  if (memoryProfileCache.has(key)) {
    return memoryProfileCache.get(key);
  }

  try {
    const db = await openTelemetryDb();
    const entry = await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readonly");
      const store = tx.objectStore(STORE_NAME);
      const req = store.get(key);
      req.onsuccess = () => resolve(req.result || null);
      req.onerror = () => reject(req.error);
    });

    if (entry && entry.data) {
      memoryProfileCache.set(key, entry.data);
      return entry.data;
    }
  } catch (err) {
    console.warn("IndexedDB read error:", err);
  }

  return null;
}

/**
 * Fetches precalculated telemetry profile from static paths or GitHub raw CDN.
 * @param {string} filename
 * @returns {Promise<Object|null>}
 */
async function fetchPrecalculatedProfile(filename) {
  if (memoryProfileCache.has(filename)) {
    return memoryProfileCache.get(filename);
  }

  const candidateUrls = [
    resolveApiPath(`api/telemetry_profiles/${encodeURIComponent(filename)}`),
    `./data/telemetry_profiles/${encodeURIComponent(filename)}`,
    `data/telemetry_profiles/${encodeURIComponent(filename)}`,
    `https://raw.githubusercontent.com/munoznicolas/ac-license-center/main/data/telemetry_profiles/${encodeURIComponent(filename)}`,
  ];

  for (const url of candidateUrls) {
    try {
      const res = await fetch(url);
      if (res.ok) {
        const text = await res.text();
        if (!text.trim().startsWith("<")) {
          const data = JSON.parse(text);
          if (data && Array.isArray(data.samples)) {
            memoryProfileCache.set(filename, data);
            return data;
          }
        }
      }
    } catch {
      // Continue to next candidate URL
    }
  }

  return null;
}

/**
 * Resolves a TelemetryEngine instance for a track, layout, and car combination.
 * Checks IndexedDB custom store first, then repository precalculated profiles.
 * @param {string} trackId
 * @param {string} layout
 * @param {string} carId
 * @param {number} [aiLevel=100]
 * @returns {Promise<{ engine: TelemetryEngine, source: string, filename: string } | null>}
 */
export async function resolveTelemetryEngine(trackId, layout, carId, aiLevel = 100) {
  if (!trackId || !carId) return null;

  const filename = getTelemetryFilename(trackId, layout, carId, aiLevel);

  // 1. Check custom uploaded profile (IndexedDB / Memory)
  const customData = await getCustomTelemetryProfile(filename);
  if (customData) {
    return {
      engine: new TelemetryEngine(customData),
      source: "custom_uploaded",
      filename,
    };
  }

  // 2. Check precalculated profile from repository / CDN
  const precalcData = await fetchPrecalculatedProfile(filename);
  if (precalcData) {
    return {
      engine: new TelemetryEngine(precalcData),
      source: "precalculated",
      filename,
    };
  }

  // 3. Fallback: Check if there's an ai95 profile available for this combination
  if (aiLevel !== 95) {
    const fn95 = getTelemetryFilename(trackId, layout, carId, 95);
    const precalc95 = await fetchPrecalculatedProfile(fn95);
    if (precalc95) {
      return {
        engine: new TelemetryEngine(precalc95),
        source: "precalculated_ai95",
        filename: fn95,
      };
    }
  }

  return null;
}
