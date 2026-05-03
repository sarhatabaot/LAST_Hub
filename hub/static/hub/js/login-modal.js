(() => {
  const dialog = document.getElementById("loginDialog");
  if (!(dialog instanceof HTMLDialogElement)) return;

  const opener = document.querySelector("[data-login-open]");
  const closer = dialog.querySelector("[data-login-close]");
  const form = dialog.querySelector("#loginForm");
  const errorBox = dialog.querySelector("#loginError");

  if (opener) {
    opener.addEventListener("click", (event) => {
      event.preventDefault();
      if (errorBox) errorBox.hidden = true;
      dialog.showModal();
    });
  }

  if (closer) {
    closer.addEventListener("click", () => dialog.close());
  }

  dialog.addEventListener("click", (event) => {
    // Click on backdrop (the dialog element itself) closes it.
    if (event.target === dialog) dialog.close();
  });

  if (!form) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (errorBox) errorBox.hidden = true;

    const fd = new FormData(form);
    let res;
    try {
      res = await fetch(form.action, {
        method: "POST",
        body: fd,
        credentials: "same-origin",
        redirect: "manual",
      });
    } catch (err) {
      if (errorBox) {
        errorBox.textContent = "Network error. Please try again.";
        errorBox.hidden = false;
      }
      return;
    }

    // Django's LoginView returns 302 on success. With redirect:'manual'
    // the browser surfaces this as type 'opaqueredirect' (status 0).
    const isRedirect = res.type === "opaqueredirect" ||
      (res.status >= 300 && res.status < 400);

    if (isRedirect) {
      // Session cookie is set; reload to pick up the authenticated state.
      window.location.reload();
      return;
    }

    if (errorBox) {
      errorBox.textContent = "Invalid username or password.";
      errorBox.hidden = false;
    }
  });
})();
