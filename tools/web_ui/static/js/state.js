/**
 * state.js
 * Central reactive application state for Assetto Corsa GT-Like License Test Designer.
 */

export const state = {
  curriculum: [],
  activeTierIndex: 0,
  activeTestIndex: 0,
  tracks: [],
  cars: [],
  currentSpline: null,
  isDirty: false,
  referenceTests: [],
  activeRefGame: "ALL",
  refCharts: {},
  isReferenceViewActive: false,
  isTourActive: false,
  cacheBuster: Date.now(),
};

/**
 * Returns the currently active license tier object, or null.
 */
export function getActiveTier() {
  return state.curriculum && state.curriculum[state.activeTierIndex]
    ? state.curriculum[state.activeTierIndex]
    : null;
}

/**
 * Returns the currently active test definition object, or null.
 */
export function getActiveTest() {
  const tier = getActiveTier();
  return tier && tier.tests && tier.tests[state.activeTestIndex]
    ? tier.tests[state.activeTestIndex]
    : null;
}
