/* Settings-page control for the dark-mode switch.
   The blocking head script (blog_template.render_theme_boot) applies the
   stored value before paint. This file only wires the switch. */
(function () {
  var STORAGE_KEY = "abz-theme";

  function storedTheme() {
    try {
      var value = localStorage.getItem(STORAGE_KEY);
      if (value === "light" || value === "dark") return value;
    } catch (err) {
      return null;
    }
    return null;
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    document.documentElement.style.colorScheme = theme;
  }

  function persistTheme(theme) {
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (err) {
      /* private mode or blocked storage: the theme still applies this visit */
    }
  }

  function setStatus(theme) {
    var status = document.getElementById("theme-status");
    if (!status) return;
    status.textContent = theme === "dark"
      ? "Mode sombre activé. Ce choix est enregistré dans ce navigateur."
      : "Mode clair activé. Ce choix est enregistré dans ce navigateur.";
  }

  function syncToggle(theme) {
    var toggle = document.getElementById("dark-mode-toggle");
    if (!toggle) return;
    var dark = theme === "dark";
    toggle.setAttribute("aria-checked", dark ? "true" : "false");
    setStatus(theme);
  }

  document.addEventListener("DOMContentLoaded", function () {
    var theme = storedTheme() || "dark";
    applyTheme(theme);
    syncToggle(theme);

    var toggle = document.getElementById("dark-mode-toggle");
    if (!toggle) return;

    toggle.addEventListener("click", function () {
      var next = (storedTheme() || "dark") === "dark" ? "light" : "dark";
      persistTheme(next);
      applyTheme(next);
      syncToggle(next);
    });
  });
})();
