document.addEventListener("DOMContentLoaded", () => {
  const toggleContainer = document.querySelector("[data-sidebar-toggle]");

  if (!toggleContainer) {
    return;
  }

  const buttons = Array.from(
    toggleContainer.querySelectorAll("[data-sidebar-filter]")
  );
  const allOnlyItems = Array.from(
    document.querySelectorAll(".sidebar-all")
  );

  const setActiveFilter = (filter) => {
    const showAll = filter === "all";

    allOnlyItems.forEach((item) => {
      item.hidden = !showAll;
    });

    buttons.forEach((button) => {
      const isActive = button.dataset.sidebarFilter === filter;
      button.classList.toggle("is-active", isActive);
      button.classList.toggle("outline", !isActive);
    });
  };

  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      setActiveFilter(button.dataset.sidebarFilter);
    });
  });

  setActiveFilter("observers");
});
