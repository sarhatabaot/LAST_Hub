document.addEventListener("click", (event) => {
  const userMenu = document.querySelector(".hub-user-menu");
  if (!userMenu || !userMenu.hasAttribute("open")) {
    return;
  }

  if (!userMenu.contains(event.target)) {
    userMenu.removeAttribute("open");
  }
});
