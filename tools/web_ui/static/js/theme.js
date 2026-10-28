/**
 * theme.js
 * Theme controller supporting Light and Dark modes with localStorage persistence,
 * system preference awareness, and FOUC-safe synchronization.
 */

import { dom } from "./dom.js";

const STORAGE_KEY = "theme";

/**
 * Get current active theme from DOM attribute or fallback to dark.
 * @returns {"light" | "dark"}
 */
export function getActiveTheme() {
  return document.documentElement.getAttribute("data-theme") === "light"
    ? "light"
    : "dark";
}

/**
 * Synchronize theme toggle button icon and accessibility labels.
 * @param {"light" | "dark"} theme
 */
export function updateThemeToggleUI(theme) {
  if (!dom.btnThemeToggle || !dom.themeToggleIcon) return;
  const isLight = theme === "light";
  // When light, show moon icon to switch to dark. When dark, show sun icon to switch to light.
  dom.themeToggleIcon.textContent = isLight ? "🌙" : "☀️";
  const label = isLight ? "Switch to dark theme" : "Switch to light theme";
  dom.btnThemeToggle.setAttribute("title", label);
  dom.btnThemeToggle.setAttribute("aria-label", label);
}

/**
 * Apply theme to document, optionally persist to localStorage, and notify subscribers.
 * @param {"light" | "dark"} theme
 * @param {boolean} persist
 */
export function setTheme(theme, persist = true) {
  document.documentElement.setAttribute("data-theme", theme);
  if (persist) {
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {
      console.warn("Unable to save theme preference to localStorage:", e);
    }
  }
  updateThemeToggleUI(theme);
  window.dispatchEvent(new CustomEvent("themechange", { detail: { theme } }));
}

/**
 * Toggle between light and dark themes.
 */
export function toggleTheme() {
  const current = getActiveTheme();
  const next = current === "light" ? "dark" : "light";
  setTheme(next, true);
}

/**
 * Initialize theme listener and bind toggle button event handler.
 */
export function initTheme() {
  const active = getActiveTheme();
  updateThemeToggleUI(active);

  if (dom.btnThemeToggle) {
    dom.btnThemeToggle.addEventListener("click", () => {
      toggleTheme();
    });
  }

  // Follow OS preference if the user has not explicitly stored a preference
  try {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    mediaQuery.addEventListener("change", (e) => {
      try {
        if (!localStorage.getItem(STORAGE_KEY)) {
          const osTheme = e.matches ? "dark" : "light";
          setTheme(osTheme, false);
        }
      } catch (err) {
        // Ignore localStorage access errors
      }
    });
  } catch (e) {
    console.warn("prefers-color-scheme listener not available:", e);
  }
}
