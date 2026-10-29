/**
 * theme.js
 * Theme controller supporting automatic browser preference detection and manual user toggle.
 * Dispatches 'themechange' custom events for reactive UI and canvas updates.
 */

import { dom } from "./dom.js";

const STORAGE_KEY = "theme";

/**
 * Detect user's browser/system color scheme preference.
 * @returns {"light" | "dark"}
 */
export function getBrowserTheme() {
  if (typeof window !== "undefined" && window.matchMedia) {
    return window.matchMedia("(prefers-color-scheme: light)").matches
      ? "light"
      : "dark";
  }
  return "dark";
}

/**
 * Get current active theme from DOM attribute or fallback to browser preference.
 * @returns {"light" | "dark"}
 */
export function getActiveTheme() {
  const currentAttr =
    typeof document !== "undefined"
      ? document.documentElement.getAttribute("data-theme")
      : null;
  return currentAttr === "light" || currentAttr === "dark"
    ? currentAttr
    : getBrowserTheme();
}

/**
 * Update theme toggle button icon, title, and label.
 * @param {"light" | "dark"} theme
 */
export function updateThemeToggleUI(theme) {
  if (!dom.btnThemeToggle || !dom.themeToggleIcon) return;
  const isLight = theme === "light";
  dom.themeToggleIcon.textContent = isLight ? "🌙" : "☀️";
  const label = isLight ? "Switch to dark theme" : "Switch to light theme";
  dom.btnThemeToggle.setAttribute("title", label);
  dom.btnThemeToggle.setAttribute("aria-label", label);
  if (dom.themeToggleText) {
    dom.themeToggleText.textContent = isLight ? "Dark Theme" : "Light Theme";
  }
}

/**
 * Apply theme to document, update UI toggle, and notify subscribers.
 * @param {"light" | "dark"} theme
 */
export function setTheme(theme) {
  const resolved = theme === "light" ? "light" : "dark";
  const prev = document.documentElement.getAttribute("data-theme");
  document.documentElement.setAttribute("data-theme", resolved);
  updateThemeToggleUI(resolved);

  if (prev !== resolved) {
    window.dispatchEvent(
      new CustomEvent("themechange", { detail: { theme: resolved } })
    );
  }
}

/**
 * Synchronize the document theme with the user's browser preference.
 * @returns {"light" | "dark"}
 */
export function syncThemeWithBrowser() {
  const preferred = getBrowserTheme();
  setTheme(preferred);
  return preferred;
}

/**
 * Toggle between light and dark modes manually.
 */
export function toggleTheme() {
  const current = getActiveTheme();
  const next = current === "light" ? "dark" : "light";
  setTheme(next);
}

/**
 * Initialize theme synchronizer and register media query listener for browser changes.
 */
export function initTheme() {
  // Synchronize immediately on startup
  const active = getActiveTheme();
  setTheme(active);

  // Hook up button toggle if present in the DOM
  if (dom.btnThemeToggle) {
    dom.btnThemeToggle.addEventListener("click", () => {
      toggleTheme();
    });
  }

  // Listen for real-time changes in browser / OS preference
  try {
    if (typeof window !== "undefined" && window.matchMedia) {
      const mediaQuery = window.matchMedia("(prefers-color-scheme: light)");
      const onPreferenceChange = (e) => {
        setTheme(e.matches ? "light" : "dark");
      };

      if (mediaQuery.addEventListener) {
        mediaQuery.addEventListener("change", onPreferenceChange);
      } else if (mediaQuery.addListener) {
        mediaQuery.addListener(onPreferenceChange);
      }
    }
  } catch (e) {
    console.warn("prefers-color-scheme listener not available:", e);
  }
}
