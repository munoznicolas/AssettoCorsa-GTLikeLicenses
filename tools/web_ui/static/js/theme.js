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
export function setTheme(theme) {
  const resolved = theme === "light" ? "light" : "dark";
  const prev = document.documentElement.getAttribute("data-theme");
  document.documentElement.setAttribute("data-theme", resolved);

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
  // Theme is synchronized with browser preference; manual toggle disabled.
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
