/**
 * theme.js
 * Gran Turismo License Center Theme Management Subsystem.
 * Provides GT2-inspired Dark Theme, GT5-inspired Light Theme, and auto System Theme switching.
 */

import { dom } from "./dom.js";

export const THEME_KEYS = {
  SYSTEM: "system",
  DARK: "dark",
  LIGHT: "light",
};

const STORAGE_KEY = "gt_license_theme";

// Icons for the 3 theme states
const ICONS = {
  [THEME_KEYS.SYSTEM]: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" pointer-events="none"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>`,
  [THEME_KEYS.DARK]: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" pointer-events="none"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`,
  [THEME_KEYS.LIGHT]: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" pointer-events="none"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>`,
};

const TOOLTIPS = {
  [THEME_KEYS.SYSTEM]: "Theme: System (Auto) — Follows OS theme. Click to switch to GT2 Dark",
  [THEME_KEYS.DARK]: "Theme: GT2 Dark — Click to switch to GT5 Light",
  [THEME_KEYS.LIGHT]: "Theme: GT5 Light — Click to switch to System (Auto)",
};

// Event listeners for theme changes (e.g. canvas re-render, charts update)
const themeChangeListeners = new Set();

export function onThemeChange(callback) {
  themeChangeListeners.add(callback);
}

export function offThemeChange(callback) {
  themeChangeListeners.delete(callback);
}

/**
 * Returns the user's stored preference ("system", "dark", or "light"). Defaults to "system".
 */
export function getStoredTheme() {
  try {
    const val = localStorage.getItem(STORAGE_KEY);
    if (val === THEME_KEYS.DARK || val === THEME_KEYS.LIGHT || val === THEME_KEYS.SYSTEM) {
      return val;
    }
  } catch (e) {
    console.warn("localStorage unavailable for theme preference:", e);
  }
  return THEME_KEYS.SYSTEM;
}

/**
 * Resolves the concrete theme ("dark" or "light") given a theme setting.
 */
export function resolveTheme(setting) {
  if (setting === THEME_KEYS.DARK) return THEME_KEYS.DARK;
  if (setting === THEME_KEYS.LIGHT) return THEME_KEYS.LIGHT;
  // System mode: inspect OS color scheme
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
    ? THEME_KEYS.DARK
    : THEME_KEYS.LIGHT;
}

/**
 * Returns true if the active computed theme is light.
 */
export function isLightTheme() {
  return document.documentElement.getAttribute("data-theme") === THEME_KEYS.LIGHT;
}

/**
 * Apply the theme setting to the DOM and optionally persist to localStorage.
 */
export function applyTheme(setting, persist = true, animate = false) {
  const resolved = resolveTheme(setting);

  if (animate) {
    document.documentElement.classList.add("theme-transitioning");
    setTimeout(() => {
      document.documentElement.classList.remove("theme-transitioning");
    }, 260);
  }

  document.documentElement.setAttribute("data-theme-setting", setting);
  document.documentElement.setAttribute("data-theme", resolved);

  // Update theme-color meta tag
  const metaTheme = document.querySelector('meta[name="theme-color"]');
  if (metaTheme) {
    metaTheme.setAttribute("content", resolved === THEME_KEYS.DARK ? "#080b12" : "#ffffff");
  }

  // Update toggle button icon and tooltip
  if (dom.btnThemeToggle) {
    dom.btnThemeToggle.innerHTML = ICONS[setting] || ICONS[THEME_KEYS.SYSTEM];
    dom.btnThemeToggle.setAttribute("title", TOOLTIPS[setting] || TOOLTIPS[THEME_KEYS.SYSTEM]);
    dom.btnThemeToggle.setAttribute("aria-label", `Current theme: ${setting}. Click to cycle.`);
  }

  if (persist) {
    try {
      localStorage.setItem(STORAGE_KEY, setting);
    } catch (e) {
      console.warn("Failed to persist theme to localStorage:", e);
    }
  }

  // Notify registered subscribers (canvas, charts, etc.)
  themeChangeListeners.forEach((fn) => {
    try {
      fn(resolved, setting);
    } catch (err) {
      console.error("Error in theme change listener:", err);
    }
  });
}

/**
 * Cycle to the next theme in order: System -> Dark -> Light -> System
 */
export function cycleTheme() {
  const current = getStoredTheme();
  let next = THEME_KEYS.SYSTEM;
  if (current === THEME_KEYS.SYSTEM) {
    next = THEME_KEYS.DARK;
  } else if (current === THEME_KEYS.DARK) {
    next = THEME_KEYS.LIGHT;
  } else {
    next = THEME_KEYS.SYSTEM;
  }
  applyTheme(next, true, true);
}

/**
 * Initialize theme subsystem and bind events.
 */
export function initTheme() {
  const initialSetting = getStoredTheme();
  applyTheme(initialSetting, false, false);

  if (dom.btnThemeToggle) {
    dom.btnThemeToggle.addEventListener("click", () => {
      cycleTheme();
    });
  }

  // Listen to OS prefers-color-scheme changes
  if (window.matchMedia) {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = () => {
      if (getStoredTheme() === THEME_KEYS.SYSTEM) {
        applyTheme(THEME_KEYS.SYSTEM, false, true);
      }
    };
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener("change", handleChange);
    } else if (mediaQuery.addListener) {
      mediaQuery.addListener(handleChange);
    }
  }
}
