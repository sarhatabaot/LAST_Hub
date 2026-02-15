document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.querySelector("[data-hub-sidebar]");
  const modeButtons = Array.from(
    document.querySelectorAll("[data-hub-mode]")
  );
  const modeSwitch = document.querySelector("[data-hub-mode-switch]");
  const searchInput = document.querySelector("[data-sidebar-search]");
  const searchItems = Array.from(document.querySelectorAll("[data-search-item]"));
  const observerSection = document.querySelector(
    '[data-hub-section="observer"]'
  );
  const developerSection = document.querySelector(
    '[data-hub-section="developer"]'
  );

  if (!sidebar && !modeSwitch && modeButtons.length === 0) {
    return;
  }

  const STORAGE_KEY = "hub-mode";
  const VALID_MODES = new Set(["observer", "developer"]);
  const pageModeMap = {
    home: "observer",
    hub: "developer",
    manual_index: "developer",
    manual_detail: "developer",
    operations: "observer",
    forecast: "observer",
    allsky: "observer",
    zorg: "observer",
    safety_status: "observer",
  };

  let currentMode = "observer";

  const normalize = (value) =>
    (value || "").toString().trim().toLowerCase();

  const setButtonState = (mode) => {
    modeButtons.forEach((button) => {
      const isActive = button.dataset.hubMode === mode;
      button.classList.toggle("is-active", isActive);
      button.classList.toggle("outline", !isActive);
    });
  };

  const openSectionForMode = (mode) => {
    if (mode === "observer" && observerSection) {
      observerSection.open = true;
    }
    if (mode === "developer" && developerSection) {
      developerSection.open = true;
    }
  };

  const detectModeFromPage = () => {
    const page = normalize(document.body.dataset.hubPage);
    if (page && pageModeMap[page]) {
      return pageModeMap[page];
    }
    const activeLink = document.querySelector(".sidebar a.contrast");
    if (!activeLink) {
      return null;
    }
    const section = activeLink.closest("[data-hub-section]");
    if (!section) {
      return null;
    }
    const sectionName = section.dataset.hubSection;
    return VALID_MODES.has(sectionName) ? sectionName : null;
  };

  const applySearch = () => {
    if (!searchInput || searchItems.length === 0) {
      return;
    }

    const query = normalize(searchInput.value);
    const scope = ["shared", "observer", "developer"];

    searchItems.forEach((item) => {
      const section = item.closest("[data-hub-section]");
      const sectionName = section ? section.dataset.hubSection : "shared";
      if (query.length === 0) {
        item.hidden = false;
        return;
      }
      if (!scope.includes(sectionName)) {
        item.hidden = true;
        return;
      }
      const matches = normalize(item.textContent).includes(query);
      item.hidden = !matches;
    });

    if (query.length > 0) {
      if (observerSection) observerSection.open = true;
      if (developerSection) developerSection.open = true;
    }

  };

  const setMode = (mode, options = {}) => {
    if (!VALID_MODES.has(mode)) {
      return;
    }
    const { persist } = options;
    currentMode = mode;
    setButtonState(mode);
    if (modeSwitch) {
      modeSwitch.checked = mode === "developer";
      modeSwitch.setAttribute(
        "aria-checked",
        mode === "developer" ? "true" : "false"
      );
    }
    if (persist && window.localStorage) {
      window.localStorage.setItem(STORAGE_KEY, mode);
    }
    applySearch();
  };

  const storedMode =
    window.localStorage && window.localStorage.getItem(STORAGE_KEY);
  const pageMode = detectModeFromPage();
  const initialMode = pageMode || storedMode || "observer";
  if (pageMode) {
    openSectionForMode(pageMode);
  }
  setMode(initialMode, { persist: Boolean(pageMode || !storedMode) });

  if (modeButtons.length > 0) {
    modeButtons.forEach((button) => {
      button.addEventListener("click", () => {
        const nextMode = button.dataset.hubMode;
        setMode(nextMode, { persist: true });
      });
    });
  }

  if (modeSwitch) {
    modeSwitch.addEventListener("change", () => {
      const nextMode = modeSwitch.checked ? "developer" : "observer";
      setMode(nextMode, { persist: true });
    });
  }

  if (searchInput) {
    searchInput.addEventListener("input", applySearch);
  }

});
