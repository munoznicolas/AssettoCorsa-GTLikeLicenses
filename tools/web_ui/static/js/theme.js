/**
 * theme.js
 * Theme controller automatically synchronized with the user's browser/system preference.
 * Dispatches 'themechange' custom events for reactive UI and canvas updates.
 */

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
 * Apply theme to document and notify subscribers via 'themechange' event.
 * @param {"light" | "dark"} theme
 */
export function updateThemeToggleUI(theme) {
  if (!dom.btnThemeToggle) return;
  const isLight = theme === "light";
  const iconSlot = document.getElementById("theme-toggle-icon");
  const textSlot = document.getElementById("theme-toggle-text");

  const moonSvg = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>`;
  const sunSvg = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>`;

  if (iconSlot) {
    iconSlot.innerHTML = isLight ? moonSvg : sunSvg;
  }
  if (textSlot) {
    textSlot.textContent = isLight ? "Dark Theme" : "Light Theme";
  }
  const label = isLight ? "Switch to dark theme" : "Switch to light theme";
  dom.btnThemeToggle.setAttribute("title", label);
  dom.btnThemeToggle.setAttribute("aria-label", label);
}

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
 * Legacy UI updater retained as a no-op for backward compatibility.
 * @param {"light" | "dark"} _theme
 */
export function updateThemeToggleUI(_theme) {
  // Theme toggle button has been removed in favor of automatic browser sync.
}

/**
 * Legacy toggle retained as a no-op for backward compatibility.
 */
export function toggleTheme() {
  const current = getEffectiveTheme();
  const next = current === "light" ? "dark" : "light";
  try {
    localStorage.setItem(STORAGE_KEY, next);
  } catch (_) {}
  setTheme(next);
}

/**
 * Initialize theme synchronizer and register media query listener for browser changes.
 */
export function initTheme() {
  // Clean up any legacy manual theme override stored in localStorage
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (e) {
    // Ignore storage errors in sandboxed environments
  }

  // Synchronize immediately on startup
  syncThemeWithBrowser();

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
        // Fallback for older WebKit / Safari
        mediaQuery.addListener(onPreferenceChange);
      }
    }
  } catch (e) {
    console.warn("prefers-color-scheme listener not available:", e);
  }
}
