document.addEventListener("DOMContentLoaded", () => {
  const container = document.querySelector(".manual-content");
  if (!container) {
    return;
  }

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
});
