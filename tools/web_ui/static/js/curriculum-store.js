/**
 * curriculum-store.js
 * Browser LocalStorage Source of Truth & JSON Backup Manager for License Test Curriculum.
 *
 * Replaces Python backend file writes with browser-local persistence:
 *   - Automatic hydration from static api/curriculum.json on first visit
 *   - Auto-saving all test additions, edits, deletions, and reorders to LocalStorage
 *   - One-click "Export curriculum.json" for Git commits or backup
 *   - One-click "Import curriculum.json" to restore or share test configurations
 *   - "Reset to Defaults" to re-seed from official baseline
 */

import { api, resolveApiPath } from "./api.js";

export const STORAGE_KEY = "gt_curriculum_v1";

/**
 * Validates that an object has the expected curriculum schema.
 * @param {any} data
 * @returns {boolean}
 */
export function isValidCurriculum(data) {
  if (!Array.isArray(data) || data.length === 0) return false;
  return data.every(
    (tier) =>
      tier &&
      typeof tier.tier_name === "string" &&
      Array.isArray(tier.tests)
  );
}

/**
 * Loads curriculum tests from LocalStorage, falling back to static api/curriculum.json.
 * @returns {Promise<Array>} Curriculum tiers array
 */
export async function loadCurriculum() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      if (isValidCurriculum(parsed)) {
        return parsed;
      }
    }
  } catch (err) {
    console.warn("Failed to load curriculum from LocalStorage, falling back to bundled defaults:", err);
  }

  // Fetch baseline curriculum from static distribution
  try {
    const baseline = await api.getCurriculum();
    const curriculumData = baseline?.curriculum || baseline;
    if (isValidCurriculum(curriculumData)) {
      saveCurriculum(curriculumData);
      return curriculumData;
    }
  } catch (err) {
    console.error("Failed to fetch baseline curriculum.json:", err);
  }

  return [];
}

/**
 * Persists active curriculum configuration into LocalStorage.
 * @param {Array} curriculum
 * @returns {boolean} Success status
 */
export function saveCurriculum(curriculum) {
  if (!isValidCurriculum(curriculum)) {
    console.error("Refusing to save invalid curriculum to LocalStorage");
    return false;
  }
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(curriculum));
    return true;
  } catch (err) {
    console.error("LocalStorage quota exceeded or write failed:", err);
    return false;
  }
}

/**
 * Discards local changes and re-seeds state from baseline api/curriculum.json.
 * @returns {Promise<Array>}
 */
export async function resetCurriculumToDefaults() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Ignore error
  }

  const baseline = await api.getCurriculum();
  const curriculumData = baseline?.curriculum || baseline;
  if (isValidCurriculum(curriculumData)) {
    saveCurriculum(curriculumData);
    return curriculumData;
  }
  throw new Error("Failed to re-fetch baseline curriculum defaults.");
}

/**
 * Triggers a client-side download of the active curriculum as a formatted curriculum.json file.
 * @param {Array} curriculum
 * @param {string} [filename="curriculum.json"]
 */
export function exportCurriculumJson(curriculum, filename = "curriculum.json") {
  const jsonStr = JSON.stringify(curriculum, null, 2);
  const blob = new Blob([jsonStr], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Parses and validates an uploaded curriculum.json File, saving it to LocalStorage.
 * @param {File} file
 * @returns {Promise<Array>} Parsed curriculum array
 */
export async function importCurriculumJsonFile(file) {
  if (!file) {
    throw new Error("No file selected");
  }

  const text = await file.text();
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch (e) {
    throw new Error(`Invalid JSON file: ${e.message}`);
  }

  const curriculumData = parsed?.curriculum || parsed;
  if (!isValidCurriculum(curriculumData)) {
    throw new Error("Imported file does not match curriculum structure (expected array of tiers with tests).");
  }

  saveCurriculum(curriculumData);
  return curriculumData;
}
