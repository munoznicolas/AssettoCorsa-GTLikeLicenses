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
  dom.themeToggleIcon.innerHTML = isLight
    ? `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>`
    : `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>`;
  const label = isLight ? "Switch to dark theme" : "Switch to light theme";
  dom.btnThemeToggle.setAttribute("title", label);
  dom.btnThemeToggle.setAttribute("aria-label", label);
  const textEl = document.getElementById("theme-toggle-text");
  if (textEl) {
    textEl.textContent = isLight ? "Dark Theme" : "Light Theme";
  }
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
