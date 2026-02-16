document.addEventListener("DOMContentLoaded", () => {
  const container = document.querySelector(".manual-content");
  if (!container) {
    return;
  }

  const addCopyButtons = () => {
    const blocks = Array.from(container.querySelectorAll("pre"));
    blocks.forEach((pre) => {
      if (pre.querySelector(".manual-copy-button")) {
        return;
      }
      const button = document.createElement("button");
      button.type = "button";
      button.className = "manual-copy-button";
      button.textContent = "⧉";
      button.setAttribute("aria-label", "Copy code");
      button.setAttribute("title", "Copy code");

      button.addEventListener("click", async () => {
        const code = pre.querySelector("code") || pre;
        const text = code.innerText;
        try {
          await navigator.clipboard.writeText(text);
          button.textContent = "✓";
        } catch (err) {
          const textarea = document.createElement("textarea");
          textarea.value = text;
          textarea.setAttribute("readonly", "readonly");
          textarea.style.position = "absolute";
          textarea.style.left = "-9999px";
          document.body.appendChild(textarea);
          textarea.select();
          document.execCommand("copy");
          document.body.removeChild(textarea);
          button.textContent = "✓";
        }
        button.classList.add("is-copied");
        window.setTimeout(() => {
          button.classList.remove("is-copied");
          button.textContent = "⧉";
        }, 1200);
      });

      pre.appendChild(button);
    });
  };

  const closeLightbox = (overlay) => {
    if (overlay && overlay.parentNode) {
      overlay.parentNode.removeChild(overlay);
    }
    document.body.style.overflow = "";
  };

  const openLightbox = (img) => {
    const overlay = document.createElement("div");
    overlay.className = "manual-lightbox";

    const close = document.createElement("div");
    close.className = "manual-lightbox-close";
    close.textContent = "×";
    overlay.appendChild(close);

    const clone = document.createElement("img");
    clone.src = img.currentSrc || img.src;
    clone.alt = img.alt || "Manual image";
    overlay.appendChild(clone);

    const onClose = () => closeLightbox(overlay);
    overlay.addEventListener("click", (event) => {
      if (event.target === overlay || event.target === close) {
        onClose();
      }
    });

    const onKey = (event) => {
      if (event.key === "Escape") {
        onClose();
        document.removeEventListener("keydown", onKey);
      }
    };

    document.addEventListener("keydown", onKey);
    document.body.appendChild(overlay);
    document.body.style.overflow = "hidden";
  };

  container.addEventListener("click", (event) => {
    const target = event.target;
    if (target instanceof HTMLImageElement) {
      openLightbox(target);
    }
  });

  addCopyButtons();
});
