(() => {
  const root = document.documentElement;
  const systemTheme = matchMedia("(prefers-color-scheme: light)");
  const storageKey = "craft-theme";
  const isTheme = (value) => value === "light" || value === "dark";

  const readSavedTheme = () => {
    try {
      const value = localStorage.getItem(storageKey);
      return isTheme(value) ? value : null;
    } catch (error) {
      return null;
    }
  };

  const requestedTheme = new URLSearchParams(location.search).get("theme");
  const savedTheme = readSavedTheme();
  const initialTheme = isTheme(requestedTheme)
    ? requestedTheme
    : savedTheme || (systemTheme.matches ? "light" : "dark");
  const initialSource = isTheme(requestedTheme) ? "query" : savedTheme ? "saved" : "system";

  const syncButtons = () => {
    const light = root.dataset.theme === "light";
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.setAttribute("aria-pressed", String(light));
      // A page in another language sets data-label-dark and data-label-light on the button.
      const action = light
        ? button.dataset.labelDark || "Switch to dark theme"
        : button.dataset.labelLight || "Switch to light theme";
      button.setAttribute("aria-label", action);
      button.setAttribute("title", action);
    });
  };

  const applyTheme = (theme, source = "saved", persist = false) => {
    if (!isTheme(theme)) return;
    root.dataset.theme = theme;
    root.dataset.themeSource = source;
    if (persist) {
      try {
        localStorage.setItem(storageKey, theme);
      } catch (error) {
        // Storage is optional. Without it the theme still works until a reload.
      }
    }
    syncButtons();
    dispatchEvent(new CustomEvent("craft-themechange", { detail: { theme, source } }));
  };

  applyTheme(initialTheme, initialSource);

  document.addEventListener("DOMContentLoaded", () => {
    syncButtons();
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        applyTheme(root.dataset.theme === "light" ? "dark" : "light", "saved", true);
      });
    });
  });

  systemTheme.addEventListener("change", (event) => {
    if (root.dataset.themeSource !== "system") return;
    applyTheme(event.matches ? "light" : "dark", "system");
  });

  window.CraftTheme = {
    get: () => root.dataset.theme,
    set: (theme) => applyTheme(theme, "saved", true),
  };
})();
