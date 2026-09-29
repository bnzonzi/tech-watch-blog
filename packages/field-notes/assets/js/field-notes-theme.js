(function () {
  "use strict";

  var STORAGE_KEY = "fn-theme";
  var PERSONA_KEY = "fn-persona";

  function getStoredTheme() {
    try {
      var t = localStorage.getItem(STORAGE_KEY);
      if (t === "light" || t === "dark" || t === "system") return t;
    } catch (e) {
      /* ignore */
    }
    return "light";
  }

  function resolveTheme(preference) {
    if (preference === "dark" || preference === "light") return preference;
    if (typeof matchMedia !== "undefined" && matchMedia("(prefers-color-scheme: dark)").matches) {
      return "dark";
    }
    return "light";
  }

  function applyTheme(resolved) {
    document.documentElement.setAttribute("data-theme", resolved);
    document.documentElement.style.colorScheme = resolved;
  }

  function setTheme(preference) {
    try {
      localStorage.setItem(STORAGE_KEY, preference);
    } catch (e) {
      /* ignore */
    }
    applyTheme(resolveTheme(preference));
    syncThemeControls(preference, resolveTheme(preference));
  }

  function syncThemeControls(preference, resolved) {
    var switches = document.querySelectorAll("[data-fn-theme-switch]");
    switches.forEach(function (el) {
      var isDark = resolved === "dark";
      el.setAttribute("aria-checked", isDark ? "true" : "false");
    });
    var selects = document.querySelectorAll("[data-fn-theme-select]");
    selects.forEach(function (sel) {
      sel.value = preference;
    });
    var status = document.getElementById("fn-theme-status");
    if (status) {
      var labels = { light: "clair", dark: "sombre", system: "système" };
      status.textContent =
        "Thème : " +
        (labels[preference] || preference) +
        (preference === "system" ? " (" + (resolved === "dark" ? "sombre" : "clair") + ")" : "");
    }
  }

  function initTheme() {
    var pref = getStoredTheme();
    applyTheme(resolveTheme(pref));
    syncThemeControls(pref, resolveTheme(pref));

    document.querySelectorAll("[data-fn-theme-switch]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var resolved = resolveTheme(getStoredTheme());
        setTheme(resolved === "dark" ? "light" : "dark");
      });
    });

    document.querySelectorAll("[data-fn-theme-select]").forEach(function (sel) {
      sel.addEventListener("change", function () {
        setTheme(sel.value);
      });
    });

    if (typeof matchMedia !== "undefined") {
      matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () {
        if (getStoredTheme() === "system") {
          applyTheme(resolveTheme("system"));
          syncThemeControls("system", resolveTheme("system"));
        }
      });
    }
  }

  function getStoredPersona() {
    try {
      var p = localStorage.getItem(PERSONA_KEY);
      if (p === "lea" || p === "malik") return p;
    } catch (e) {
      /* ignore */
    }
    return "lea";
  }

  function setPersona(persona) {
    try {
      localStorage.setItem(PERSONA_KEY, persona);
    } catch (e) {
      /* ignore */
    }
    document.body.setAttribute("data-persona", persona);
    document.querySelectorAll("[data-fn-persona]").forEach(function (el) {
      var active = el.getAttribute("data-fn-persona") === persona;
      el.setAttribute("aria-pressed", active ? "true" : "false");
      el.classList.toggle("is-active", active);
    });
    var preview = document.getElementById("fn-persona-preview");
    if (preview) {
      preview.textContent =
        persona === "lea"
          ? "Aperçu Léa : lecture bureau, badges « découverte », callouts pas à pas."
          : "Aperçu Malik : scan rapide, accents menthe, liens outils GAFAM en évidence.";
    }
  }

  function initPersona() {
    if (!document.body.hasAttribute("data-persona")) {
      document.body.setAttribute("data-persona", getStoredPersona());
    }
    setPersona(getStoredPersona());
    document.querySelectorAll("[data-fn-persona]").forEach(function (el) {
      el.addEventListener("click", function () {
        setPersona(el.getAttribute("data-fn-persona"));
      });
    });
  }

  function initCalloutPlayground() {
    var root = document.getElementById("fn-callout-playground");
    if (!root) return;
    var typeSelect = document.getElementById("fn-callout-type");
    var titleInput = document.getElementById("fn-callout-title");
    var bodyInput = document.getElementById("fn-callout-body");
    var preview = document.getElementById("fn-callout-preview");

    function render() {
      if (!preview || !typeSelect) return;
      var type = typeSelect.value;
      var mod =
        type === "tested"
          ? "fn-callout--tested"
          : type === "internal"
            ? "fn-callout--internal"
            : type === "fail"
              ? "fn-callout--fail"
              : "";
      preview.className = "fn-callout " + mod;
      var titleEl = preview.querySelector(".fn-callout__title");
      var bodyEl = preview.querySelector(".fn-callout__body");
      if (titleEl) titleEl.textContent = titleInput ? titleInput.value : "";
      if (bodyEl) bodyEl.textContent = bodyInput ? bodyInput.value : "";
    }

    [typeSelect, titleInput, bodyInput].forEach(function (el) {
      if (el) el.addEventListener("input", render);
      if (el) el.addEventListener("change", render);
    });
    render();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      initTheme();
      initPersona();
      initCalloutPlayground();
    });
  } else {
    initTheme();
    initPersona();
    initCalloutPlayground();
  }
})();
