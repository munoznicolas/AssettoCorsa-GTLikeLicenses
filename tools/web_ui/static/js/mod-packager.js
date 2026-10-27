/**
 * mod-packager.js
 * Pure Client-Side Content Manager Package (.zip) Builder & Curriculum Validator.
 * Generates Kunos-compliant series.ini, event.ini, and calibrated test JSONs
 * directly in the browser and exports a ready-to-install ZIP archive.
 */

const TIER_FOLDER_MAP = {
  "National B": "series_gt_license_b",
  "National A": "series_gt_license_a",
  "International B": "series_gt_license_ib",
  "International A": "series_gt_license_ia",
  "Super License": "series_gt_license_s",
};

const TIER_TESTS_FOLDER_MAP = {
  "National B": "national_b",
  "National A": "national_a",
  "International B": "international_b",
  "International A": "international_a",
  "Super License": "super_license",
};

const TIER_REQUIRES_MAP = {
  "National B": "",
  "National A": "series_gt_license_b",
  "International B": "series_gt_license_a",
  "International A": "series_gt_license_ib",
  "Super License": "series_gt_license_ia",
};

/**
 * Validates in-memory curriculum definitions against schema and game rules.
 * @param {Array} curriculum
 * @returns {Object} validation report
 */
export function validateCurriculumClient(curriculum) {
  let passed = 0;
  let failed = 0;
  const errors = [];
  const warnings = [];

  curriculum.forEach((tier) => {
    const tierName = tier.tier_name || "Unknown Tier";
    (tier.tests || []).forEach((test) => {
      const tId = test.test_id || "UNKNOWN";
      let hasError = false;

      // 1. Mandatory text fields
      if (!test.title || test.title.trim() === "") {
        errors.push({ severity: "ERROR", test_id: tId, message: "Missing test title" });
        hasError = true;
      }
      if (!test.car_id || test.car_id.trim() === "") {
        errors.push({ severity: "ERROR", test_id: tId, message: "Missing car_id" });
        hasError = true;
      }
      if (!test.track_id || test.track_id.trim() === "") {
        errors.push({ severity: "ERROR", test_id: tId, message: "Missing track_id" });
        hasError = true;
      }

      // 2. Targets sanity (gold <= silver <= bronze)
      const targets = test.targets || {};
      const g = Number(targets.gold_seconds);
      const s = Number(targets.silver_seconds);
      const b = Number(targets.bronze_seconds);

      if (!g || !s || !b || g <= 0 || s <= 0 || b <= 0) {
        errors.push({ severity: "ERROR", test_id: tId, message: "Invalid target times (must be > 0)" });
        hasError = true;
      } else if (g > s || s > b) {
        errors.push({
          severity: "ERROR",
          test_id: tId,
          message: `Inverted target times: Gold (${g}s) <= Silver (${s}s) <= Bronze (${b}s) required`,
        });
        hasError = true;
      }

      // 3. Spatial progress bounds
      const s0 = Number(test.start_s ?? 0);
      const s1 = Number(test.finish_s ?? 1);
      if (s0 < 0 || s0 > 1 || s1 < 0 || s1 > 1) {
        errors.push({ severity: "ERROR", test_id: tId, message: "start_s and finish_s must be between 0.0 and 1.0" });
        hasError = true;
      }

      if (hasError) {
        failed++;
      } else {
        passed++;
      }
    });
  });

  return {
    success: errors.length === 0,
    total_files: passed + failed,
    passed,
    failed,
    errors,
    warnings,
  };
}

/**
 * Formats strict Kunos-compliant series.ini text.
 * No spaces around '=', strictly uppercase keys.
 */
export function formatSeriesIni(tier) {
  const folder = tier.folder || TIER_FOLDER_MAP[tier.tier_name] || "series_gt_license_b";
  const requires = TIER_REQUIRES_MAP[tier.tier_name] || "";
  const desc = (tier.description || "Gran Turismo style driving school licenses.")
    .replace(/\r\n/g, "\n")
    .replace(/\n/g, " ");

  const lines = [
    "[CAREER]",
    `NAME=Gran Turismo License - ${tier.tier_name}`,
    `DESCRIPTION=${desc}`,
  ];
  if (requires) {
    lines.push(`REQUIRES=${requires}`);
  }
  lines.push("");
  return lines.join("\r\n");
}

/**
 * Formats strict Kunos-compliant event.ini text for an individual license test event.
 */
export function formatEventIni(test, eventIdx) {
  const tId = test.test_id || `EVENT-${eventIdx}`;
  const title = test.title || "License Test";
  const desc = (test.description || "").replace(/\r\n/g, "\n").replace(/\n/g, "\\n");
  const obj = (test.lesson_objective || "").replace(/\r\n/g, "\n").replace(/\n/g, "\\n");
  const fullDesc = obj ? `${desc}\\n\\nObjective: ${obj}` : desc;

  const targets = test.targets || { gold_seconds: 10, silver_seconds: 12, bronze_seconds: 15 };
  const bronzeMs = Math.round(Number(targets.bronze_seconds) * 1000);
  const silverMs = Math.round(Number(targets.silver_seconds) * 1000);
  const goldMs = Math.round(Number(targets.gold_seconds) * 1000);

  const lines = [
    "[EVENT]",
    `NAME=${tId}: ${title}`,
    `DESCRIPTION=${fullDesc}`,
    "",
    "[RACE]",
    `TRACK=${test.track_id}`,
    `CONFIG_TRACK=${test.track_layout || ""}`,
    `MODEL=${test.car_id}`,
    "MODEL_CONFIG=",
    "CARS=1",
    "AI_LEVEL=98",
    "DRIFT_MODE=0",
    "FIXED_SETUP=1",
    "PENALTIES=1",
    "__CM_CUSTOM_MODE=gt-license",
    "",
    "[CAR_0]",
    `MODEL=${test.car_id}`,
    "MODEL_CONFIG=",
    "SETUP=",
    "SKIN=",
    "BALLAST=0",
    "RESTRICTOR=0",
    "",
    "[LIGHTING]",
    "SUN_ANGLE=48",
    "TIME_MULT=1",
    "CLOUD_SPEED=0.2",
    "",
    "[SESSION_0]",
    "NAME=License Test",
    "TYPE=1",
    "DURATION=0",
    "SPAWN_SET=PIT",
    "",
    "[CONDITION_0]",
    "TYPE=TIME",
    `OBJECTIVE=${bronzeMs}`,
    "",
    "[CONDITION_1]",
    "TYPE=TIME",
    `OBJECTIVE=${silverMs}`,
    "",
    "[CONDITION_2]",
    "TYPE=TIME",
    `OBJECTIVE=${goldMs}`,
    "",
  ];

  return lines.join("\r\n");
}

/**
 * Formats a clean test definition JSON string matching the official schema.
 */
export function formatTestJson(test, tier) {
  const tId = test.test_id || "B-1";
  const tierName = tier.tier_name || "National B";

  const jsonDef = {
    test_id: tId,
    tier: tierName,
    title: test.title || "",
    description: test.description || "",
    lesson_objective: test.lesson_objective || "",
    car_id: test.car_id || "",
    track_id: test.track_id || "",
    track_layout: test.track_layout || "",
    start_mode: test.start_mode || "STANDING",
    spawn: test.spawn || {
      position: [0, 0, 0],
      forward: [0, 0, 1],
      initial_speed_kmh: Number(test.speed || 0),
      gear: 1,
      rpm: 3500,
      heading_deg: 0,
      is_valid: true,
    },
    timing: test.timing || {
      start_gate: {
        center: [0, 0, 0],
        forward: [0, 0, 1],
        left: [-4, 0, 0],
        right: [4, 0, 0],
        width: 8,
        s_norm: Number(test.start_s || 0),
      },
      finish_gate: {
        center: [100, 0, 0],
        forward: [0, 0, 1],
        left: [96, 0, 0],
        right: [104, 0, 0],
        width: 8,
        s_norm: Number(test.finish_s || 1),
      },
      sector_distance_m: 100,
    },
    fail_rules: {
      max_wheels_off: 2,
      wall_collision_threshold_n: 1500,
      max_yaw_angle_deg: 90,
      stop_box_overshoot_fail: Boolean(test.with_stop_box),
    },
    targets: test.targets || {
      gold_seconds: 10.0,
      silver_seconds: 12.0,
      bronze_seconds: 15.0,
    },
  };

  return JSON.stringify(jsonDef, null, 2);
}

/**
 * Assembles and downloads the complete Content Manager Mod (.zip) directly in the browser.
 * @param {Array} curriculum In-memory curriculum catalog
 * @param {Function} onProgress Progress callback(percent, statusMessage)
 */
export async function buildAndExportModZip(curriculum, onProgress = () => {}) {
  if (typeof JSZip === "undefined") {
    throw new Error("JSZip library is not loaded. Please ensure jszip.min.js is included.");
  }

  onProgress(5, "Validating curriculum definitions...");
  const report = validateCurriculumClient(curriculum);
  if (!report.success) {
    throw new Error(
      `Curriculum validation failed with ${report.errors.length} error(s). Please review test definitions.`
    );
  }

  onProgress(15, "Loading base mod package template...");
  const zip = new JSZip();

  // Fetch base mod zip template
  const baseZipUrl = "./assets/base_package.zip";
  let baseArrayBuffer;
  try {
    const res = await fetch(baseZipUrl);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    baseArrayBuffer = await res.arrayBuffer();
    await zip.loadAsync(baseArrayBuffer);
  } catch (err) {
    console.warn("Could not load base_package.zip, assembling new package from scratch:", err);
  }

  onProgress(40, "Generating Content Manager career series and event configs...");

  // Inject fresh configs into zip
  curriculum.forEach((tier) => {
    const sFolder = tier.folder || TIER_FOLDER_MAP[tier.tier_name] || "series_gt_license_b";
    const tFolder = TIER_TESTS_FOLDER_MAP[tier.tier_name] || "national_b";

    // 1. series.ini
    const seriesIni = formatSeriesIni(tier);
    zip.file(`content/career/${sFolder}/series.ini`, seriesIni);

    // 2. Events & Tests
    (tier.tests || []).forEach((test, idx) => {
      const eventNum = idx + 1;
      const eventIni = formatEventIni(test, eventNum);
      zip.file(`content/career/${sFolder}/event${eventNum}/event.ini`, eventIni);

      // Calibrated test definition JSON
      const testJson = formatTestJson(test, tier);
      const parts = (test.test_id || `T-${eventNum}`).split("-");
      const prefix = parts[0].toLowerCase();
      const num = parseInt(parts[1] || eventNum, 10);
      const filename = `test_${prefix}${num.toString().padStart(2, "0")}.json`;

      // Save to content/tests/<tier>/
      zip.file(`content/tests/${tFolder}/${filename}`, testJson);

      // Also mirror to extension/lua/new-modes/gt-license/data/tests/<tier>/
      zip.file(`extension/lua/new-modes/gt-license/data/tests/${tFolder}/${filename}`, testJson);
    });
  });

  onProgress(75, "Compressing Content Manager drag-and-drop ZIP archive...");

  const blob = await zip.generateAsync(
    {
      type: "blob",
      compression: "DEFLATE",
      compressionOptions: { level: 6 },
    },
    (metadata) => {
      const p = 75 + Math.round(metadata.percent * 0.2);
      onProgress(p, `Compressing files (${metadata.percent.toFixed(0)}%)...`);
    }
  );

  onProgress(100, "Triggering download...");

  // Trigger browser file download
  const downloadUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = downloadUrl;
  a.download = "AssettoCorsa_GT_License_Center.zip";
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    document.body.removeChild(a);
    URL.revokeObjectURL(downloadUrl);
  }, 1000);

  return {
    success: true,
    size: blob.size,
    validation: report,
  };
}
