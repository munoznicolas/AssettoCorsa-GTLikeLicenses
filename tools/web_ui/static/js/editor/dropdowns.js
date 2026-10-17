/**
 * editor/dropdowns.js
 * Track, layout, and car dropdown rendering & search filtering.
 */

import { state } from "../state.js";
import { dom } from "../dom.js";

/**
 * Filter tracks by search query across id, name, and layout names.
 */
export function filterTracks(query) {
  if (!query) return state.tracks;
  return state.tracks.filter((t) => {
    const idMatch = (t.track_id || "").toLowerCase().includes(query);
    const nameMatch = (t.name || "").toLowerCase().includes(query);
    const layoutMatch = (t.layouts || []).some(
      (l) =>
        (l.name || "").toLowerCase().includes(query) ||
        (l.layout_id || "").toLowerCase().includes(query)
    );
    return idMatch || nameMatch || layoutMatch;
  });
}

/**
 * Update filter count badge and clear button visibility.
 */
export function updateFilterIndicator(countEl, clearBtn, query, matchCount, totalCount) {
  if (countEl) {
    countEl.style.display = query ? "inline-block" : "none";
    if (query) {
      countEl.textContent = `${matchCount} / ${totalCount}`;
      countEl.classList.toggle("empty", matchCount === 0);
    }
  }
  if (clearBtn) {
    clearBtn.style.display = query ? "block" : "none";
  }
}

/**
 * Filter and populate track selection dropdown.
 */
export function populateTrackDropdown(selectedTrackId = null) {
  if (!dom.selectTrack) return;
  const query = dom.inputSearchTrack?.value.trim().toLowerCase() ?? "";
  const activeTrackId = selectedTrackId ?? dom.selectTrack.value;

  dom.selectTrack.innerHTML = '<option value="">Select Kunos Track...</option>';

  const matches = filterTracks(query);
  updateFilterIndicator(dom.trackFilterCount, dom.btnClearTrackSearch, query, matches.length, state.tracks.length);

  for (const t of matches) {
    const opt = document.createElement("option");
    opt.value = t.track_id;
    opt.textContent = `${t.name} (${t.track_id})`;
    if (t.track_id === activeTrackId) {
      opt.selected = true;
    }
    dom.selectTrack.appendChild(opt);
  }

  if (activeTrackId && (!query || matches.some((t) => t.track_id === activeTrackId))) {
    dom.selectTrack.value = activeTrackId;
  }
}

/**
 * Populate layout dropdown for a given track.
 */
export function populateLayoutDropdown(trackId, selectedLayout = "") {
  if (!dom.selectLayout) return;
  dom.selectLayout.innerHTML = "";
  const track = state.tracks.find((t) => t.track_id === trackId);
  if (!track?.layouts?.length) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "Default Layout";
    dom.selectLayout.appendChild(opt);
    return;
  }

  for (const l of track.layouts) {
    const opt = document.createElement("option");
    opt.value = l.layout_id;
    opt.textContent = l.name || l.layout_id || "Default Layout";
    if (l.layout_id === selectedLayout) {
      opt.selected = true;
    }
    dom.selectLayout.appendChild(opt);
  }
}

/**
 * Check if car matches AWD/4WD tokens.
 */
export function matchesAwd(car, tok) {
  return (
    car.dt === "awd" ||
    car.tags.includes("awd") ||
    car.tags.includes("4wd") ||
    car.tags.includes("mawd") ||
    car.tags.includes("fawd") ||
    car.id.includes(tok) ||
    car.name.includes(tok)
  );
}

/**
 * Check if car matches specific drivetrain token (AWD, FWD, RWD).
 */
export function matchesDrivetrainToken(car, tok) {
  if (tok === "awd" || tok === "4wd") {
    return matchesAwd(car, tok);
  }
  if (tok === "fwd") {
    return car.dt === "fwd" || car.tags.includes("fwd") || car.id.includes(tok) || car.name.includes(tok);
  }
  if (tok === "rwd") {
    return car.dt === "rwd" || car.tags.includes("rwd") || car.id.includes(tok) || car.name.includes(tok);
  }
  return null;
}

/**
 * Check if a car matches a search token.
 */
export function matchesCarToken(car, tok) {
  const dtMatch = matchesDrivetrainToken(car, tok);
  if (dtMatch !== null) return dtMatch;
  return (
    car.id.includes(tok) ||
    car.name.includes(tok) ||
    car.brand.includes(tok) ||
    car.dt.includes(tok) ||
    car.tags.some((t) => t.includes(tok))
  );
}

/**
 * Filter cars by text query and tags.
 */
export function filterCars(query) {
  if (!query) return state.cars;
  const tokens = query.toLowerCase().split(/\s+/).filter(Boolean);
  return state.cars.filter((c) => {
    const carData = {
      id: (c.car_id || "").toLowerCase(),
      name: (c.name || "").toLowerCase(),
      brand: (c.brand || "").toLowerCase(),
      dt: (c.drivetrain || "").toLowerCase(),
      tags: (c.tags || []).map((t) => String(t).toLowerCase()),
    };
    return tokens.every((tok) => matchesCarToken(carData, tok));
  });
}

/**
 * Populate car selection dropdown.
 */
export function populateCarDropdown(selectedCarId = null) {
  if (!dom.selectCar) return;
  const query = dom.inputSearchCar?.value.trim() ?? "";
  const activeCarId = selectedCarId ?? dom.selectCar.value;

  dom.selectCar.innerHTML = '<option value="">Select Kunos Car...</option>';

  const matches = filterCars(query);
  updateFilterIndicator(dom.carFilterCount, dom.btnClearCarSearch, query, matches.length, state.cars.length);

  for (const c of matches) {
    const opt = document.createElement("option");
    opt.value = c.car_id;
    const brandStr = c.brand ? ` (${c.brand})` : "";
    const dtStr = c.drivetrain ? ` [${c.drivetrain}]` : "";
    opt.textContent = `${c.name}${brandStr}${dtStr}`;
    if (c.car_id === activeCarId) {
      opt.selected = true;
    }
    dom.selectCar.appendChild(opt);
  }

  if (activeCarId && (!query || matches.some((c) => c.car_id === activeCarId))) {
    dom.selectCar.value = activeCarId;
  }
}
