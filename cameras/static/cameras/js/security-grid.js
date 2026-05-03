(() => {
  let STREAM_TIMEOUT_MS = 3 * 60 * 1000;
  const state = new Map();
  let proxyBase = "";
  let countdownTimer = null;

  function normalizePath(streamPath) {
    return streamPath
      .split("/")
      .filter(Boolean)
      .map((segment) => encodeURIComponent(segment))
      .join("/");
  }

  function buildStreamUrl(streamPath) {
    return `${proxyBase}${normalizePath(streamPath)}/index.m3u8`;
  }

  function icon(kind) {
    const icons = {
      play: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7z" fill="currentColor"/></svg>',
      mute: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 9h4l5-4v14l-5-4H5zM17 9l4 6m0-6l-4 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
      volume: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 9h4l5-4v14l-5-4H5z" fill="currentColor"/><path d="M17 9a4 4 0 010 6m2-9a8 8 0 010 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
      fullscreen: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 4H4v4M16 4h4v4M8 20H4v-4M16 20h4v-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
      stop: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 7h10v10H7z" fill="currentColor"/></svg>',
    };
    return icons[kind];
  }

  function formatCountdown(ms) {
    const total = Math.max(0, Math.round(ms / 1000));
    const m = Math.floor(total / 60);
    const s = total % 60;
    return `${m}:${String(s).padStart(2, "0")}`;
  }

  function setLed(card, status) {
    const led = card.querySelector(".cam-led");
    if (led) led.dataset.state = status;
    const tag = card.querySelector(".cam-live-tag");
    if (tag) tag.hidden = status !== "streaming";
  }

  function setCountdown(card, ms) {
    const el = card.querySelector(".cam-countdown");
    if (!el) return;
    el.textContent = formatCountdown(ms);
  }

  function controlButton(iconKind, title, onClick) {
    const button = document.createElement("button");
    button.className = "cam-button";
    button.type = "button";
    button.innerHTML = icon(iconKind);
    button.title = title;
    button.setAttribute("aria-label", title);
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      onClick();
    });
    return button;
  }

  function buildCardShell(entry, badgeText) {
    const card = document.createElement("article");
    card.className = "cam-card";
    card.setAttribute("tabindex", "-1");
    card.dataset.kind = entry.kind;

    const viewport = document.createElement("div");
    viewport.className = "cam-viewport";

    const badge = document.createElement("span");
    badge.className = "cam-badge";
    badge.textContent = badgeText;
    viewport.appendChild(badge);

    const liveTag = document.createElement("span");
    liveTag.className = "cam-live-tag";
    liveTag.textContent = "LIVE";
    liveTag.hidden = true;
    viewport.appendChild(liveTag);

    const led = document.createElement("span");
    led.className = "cam-led";
    led.dataset.state = "idle";
    viewport.appendChild(led);

    const placeholder = document.createElement("button");
    placeholder.type = "button";
    placeholder.className = "cam-placeholder";
    placeholder.innerHTML = icon("play");
    placeholder.setAttribute("aria-label", `Start ${entry.label}`);
    viewport.appendChild(placeholder);

    const countdown = document.createElement("span");
    countdown.className = "cam-countdown";
    countdown.hidden = true;
    countdown.textContent = "0:00";
    viewport.appendChild(countdown);

    const controls = document.createElement("div");
    controls.className = "cam-controls";
    viewport.appendChild(controls);

    card.appendChild(viewport);

    const footer = document.createElement("div");
    footer.className = "cam-footer";
    const label = document.createElement("span");
    label.className = "cam-footer-label";
    label.textContent = entry.label;
    label.title = entry.label;
    footer.appendChild(label);
    card.appendChild(footer);

    return { card, viewport, placeholder, controls, countdown };
  }

  function createSecurityCard(entry) {
    const { card, placeholder, controls, countdown } = buildCardShell(entry, entry.path);
    placeholder.dataset.path = entry.path;
    placeholder.dataset.label = entry.label;

    placeholder.addEventListener("click", (event) => {
      event.stopPropagation();
      if (state.has(card)) return;
      startSecurity(card, placeholder, controls, countdown);
    });

    return card;
  }

  function createWebcamCard(entry) {
    const badgeText = `${entry.host}:${entry.port}/${entry.suffix}`;
    const { card, placeholder, controls, countdown } = buildCardShell(entry, badgeText);
    placeholder.dataset.src = entry.src;
    placeholder.dataset.label = entry.label;

    placeholder.addEventListener("click", (event) => {
      event.stopPropagation();
      if (state.has(card)) return;
      startWebcam(card, placeholder, controls, countdown);
    });

    return card;
  }

  function createCard(entry) {
    if (entry.kind === "webcam") return createWebcamCard(entry);
    return createSecurityCard(entry);
  }

  async function tryPlay(video) {
    try {
      await video.play();
    } catch (err) {
      const message = err && typeof err.message === "string" ? err.message : "";
      if (err && err.name === "AbortError") return;
      if (message.includes("fetching process for the media resource was aborted")) return;
      if (message.includes("play() request was interrupted")) return;
      console.warn("Autoplay was blocked:", err);
    }
  }

  function getPlaybackSupportMessage(video) {
    if (video.canPlayType("application/vnd.apple.mpegurl")) return "";
    if (window.Hls && window.Hls.isSupported()) return "";
    if (!window.Hls) return "hls.js not loaded";
    return "HLS unsupported in this browser";
  }

  function syncMuteUi(card) {
    const s = state.get(card);
    if (!s || !s.muteButton) return;
    s.muteButton.innerHTML = icon(s.video.muted ? "mute" : "volume");
    s.muteButton.title = s.video.muted ? "Unmute stream" : "Mute stream";
    s.muteButton.setAttribute("aria-label", s.muteButton.title);
  }

  function startSecurity(card, placeholder, controlsHost, countdownEl) {
    if (state.has(card)) return;

    const streamPath = placeholder.dataset.path;
    const streamUrl = buildStreamUrl(streamPath);

    const video = document.createElement("video");
    video.className = "cam-video";
    video.autoplay = true;
    video.muted = true;
    video.playsInline = true;
    video.controls = false;

    const muteButton = controlButton("mute", "Unmute stream", () => {
      const current = state.get(card);
      if (!current) return;
      current.video.muted = !current.video.muted;
      syncMuteUi(card);
    });

    const fullscreenButton = controlButton("fullscreen", "Toggle fullscreen", async () => {
      if (document.fullscreenElement === card) {
        await document.exitFullscreen();
        return;
      }
      if (card.requestFullscreen) await card.requestFullscreen();
    });

    const stopButton = controlButton("stop", "Stop stream", () => {
      stopSecurity(card, placeholder);
    });

    controlsHost.append(muteButton, stopButton, fullscreenButton);

    placeholder.style.display = "none";
    card.classList.add("is-streaming");
    card.querySelector(".cam-viewport").insertBefore(video, placeholder);

    const fullscreenHandler = () => syncMuteUi(card);
    document.addEventListener("fullscreenchange", fullscreenHandler);

    state.set(card, {
      kind: "security",
      video,
      muteButton,
      fullscreenButton,
      stopButton,
      fullscreenHandler,
      hls: null,
      placeholder,
      countdownEl,
      startedAt: Date.now(),
    });
    countdownEl.hidden = false;
    setCountdown(card, STREAM_TIMEOUT_MS);
    refreshLiveUi();

    const handleError = () => {
      setLed(card, "error");
      setTimeout(() => stopSecurity(card, placeholder), 1500);
    };

    const supportMessage = getPlaybackSupportMessage(video);
    if (supportMessage) {
      setLed(card, supportMessage);
      // Tear down without keeping state.
      video.remove();
      controlsHost.replaceChildren();
      countdownEl.hidden = true;
      placeholder.style.display = "";
      card.classList.remove("is-streaming");
      document.removeEventListener("fullscreenchange", fullscreenHandler);
      state.delete(card);
      refreshLiveUi();
      return;
    }

    setLed(card, "starting");
    video.addEventListener("error", handleError);
    video.addEventListener("playing", () => {
      setLed(card, "streaming");
      syncMuteUi(card);
    });
    video.addEventListener("volumechange", () => syncMuteUi(card));
    syncMuteUi(card);

    if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = streamUrl;
      video.addEventListener(
        "loadedmetadata",
        () => {
          setLed(card, "streaming");
          tryPlay(video);
        },
        { once: true },
      );
      return;
    }

    if (window.Hls && window.Hls.isSupported()) {
      const hls = new window.Hls();
      state.get(card).hls = hls;
      hls.on(window.Hls.Events.MANIFEST_PARSED, () => {
        setLed(card, "streaming");
        tryPlay(video);
      });
      hls.on(window.Hls.Events.ERROR, (_event, data) => {
        if (data && data.fatal) handleError();
      });
      hls.loadSource(streamUrl);
      hls.attachMedia(video);
      return;
    }

    handleError();
  }

  function stopSecurity(card, placeholder) {
    const s = state.get(card);
    if (!s) {
      placeholder.style.display = "";
      setLed(card, "idle");
      return;
    }
    if (s.fullscreenHandler) {
      document.removeEventListener("fullscreenchange", s.fullscreenHandler);
    }
    if (s.hls) s.hls.destroy();
    if (s.video) {
      s.video.pause();
      s.video.removeAttribute("src");
      s.video.load();
      s.video.remove();
    }

    const controls = card.querySelector(".cam-controls");
    if (controls) controls.replaceChildren();
    if (s.countdownEl) s.countdownEl.hidden = true;

    card.classList.remove("is-streaming");
    placeholder.style.display = "";
    setLed(card, "idle");
    state.delete(card);
    refreshLiveUi();
  }

  function startWebcam(card, placeholder, controlsHost, countdownEl) {
    if (state.has(card)) return;

    const src = placeholder.dataset.src;
    const label = placeholder.dataset.label || "webcam";

    const img = document.createElement("img");
    img.className = "cam-img";
    img.alt = `Live stream from ${label}`;
    img.draggable = false;

    const fullscreenButton = controlButton("fullscreen", "Toggle fullscreen", async () => {
      if (document.fullscreenElement === card) {
        await document.exitFullscreen();
        return;
      }
      if (card.requestFullscreen) await card.requestFullscreen();
    });
    const stopButton = controlButton("stop", "Stop stream", () => {
      stopWebcam(card, placeholder);
    });
    controlsHost.append(stopButton, fullscreenButton);

    placeholder.style.display = "none";
    card.classList.add("is-streaming");
    card.querySelector(".cam-viewport").insertBefore(img, placeholder);

    state.set(card, {
      kind: "webcam",
      img,
      placeholder,
      countdownEl,
      startedAt: Date.now(),
    });
    countdownEl.hidden = false;
    setCountdown(card, STREAM_TIMEOUT_MS);
    refreshLiveUi();

    setLed(card, "starting");
    img.addEventListener("load", () => setLed(card, "streaming"));
    img.addEventListener("error", () => {
      setLed(card, "error");
      setTimeout(() => stopWebcam(card, placeholder), 1500);
    });
    img.src = src;
  }

  function stopWebcam(card, placeholder) {
    const s = state.get(card);
    if (!s) {
      placeholder.style.display = "";
      setLed(card, "idle");
      return;
    }
    if (s.img) {
      try {
        s.img.src = "about:blank";
      } catch (err) {
        /* ignore */
      }
      s.img.remove();
    }
    const controls = card.querySelector(".cam-controls");
    if (controls) controls.replaceChildren();
    if (s.countdownEl) s.countdownEl.hidden = true;

    card.classList.remove("is-streaming");
    placeholder.style.display = "";
    setLed(card, "idle");
    state.delete(card);
    refreshLiveUi();
  }

  function stopAny(card) {
    const s = state.get(card);
    if (!s) return;
    if (s.kind === "webcam") stopWebcam(card, s.placeholder);
    else stopSecurity(card, s.placeholder);
  }

  function refreshLiveUi() {
    const liveCount = state.size;
    const counter = document.querySelector("[data-cam-live-count]");
    if (counter) counter.textContent = String(liveCount);
    const stopAllBtn = document.querySelector("[data-cam-stop-all]");
    if (stopAllBtn) stopAllBtn.disabled = liveCount === 0;

    if (liveCount > 0 && !countdownTimer) {
      countdownTimer = setInterval(tickCountdowns, 500);
    } else if (liveCount === 0 && countdownTimer) {
      clearInterval(countdownTimer);
      countdownTimer = null;
    }
  }

  function tickCountdowns() {
    const now = Date.now();
    for (const [card, s] of state.entries()) {
      const remaining = STREAM_TIMEOUT_MS - (now - s.startedAt);
      if (remaining <= 0) {
        if (s.kind === "webcam") stopWebcam(card, s.placeholder, true);
        else stopSecurity(card, s.placeholder, true);
        continue;
      }
      setCountdown(card, remaining);
    }
  }

  function buildErrorRow(text) {
    const div = document.createElement("div");
    div.className = "stream-card-empty";
    div.textContent = text;
    return div;
  }

  function renderGroup(group, container) {
    if (group.name) {
      const heading = document.createElement("h2");
      heading.className = "camera-group-title";
      heading.textContent = group.name;
      container.appendChild(heading);
    }
    const grid = document.createElement("div");
    grid.className = "security-grid";
    group.cameras.forEach((entry) => grid.appendChild(createCard(entry)));
    container.appendChild(grid);
  }

  function init() {
    const root = document.getElementById("securityGrid");
    const configNode = document.getElementById("camera-config");
    if (!root || !configNode) return;

    let payload;
    try {
      payload = JSON.parse(configNode.textContent || "null");
    } catch (err) {
      console.error("Cameras: malformed config payload", err);
      root.appendChild(buildErrorRow("Unable to load camera configuration"));
      return;
    }

    if (!payload || !Array.isArray(payload.groups) || !payload.groups.length) {
      root.appendChild(buildErrorRow("No cameras configured"));
      return;
    }
    if (!payload.proxy_base) {
      root.appendChild(buildErrorRow("Cameras proxy is not configured"));
      return;
    }

    proxyBase = payload.proxy_base;
    if (typeof payload.stream_timeout_ms === "number" && payload.stream_timeout_ms > 0) {
      STREAM_TIMEOUT_MS = payload.stream_timeout_ms;
    }

    const host = document.createElement("div");
    host.className = "camera-sections";
    root.replaceWith(host);

    payload.groups.forEach((group) => renderGroup(group, host));

    const stopAllBtn = document.querySelector("[data-cam-stop-all]");
    if (stopAllBtn) {
      stopAllBtn.addEventListener("click", () => {
        for (const card of Array.from(state.keys())) stopAny(card);
      });
    }

    if (!window.Hls) {
      console.warn("hls.js did not load. Non-Safari browsers will not start security streams.");
    }

    window.addEventListener("beforeunload", () => {
      for (const card of Array.from(state.keys())) stopAny(card);
    });

    refreshLiveUi();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
