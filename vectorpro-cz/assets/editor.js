(function () {
  "use strict";

  const PASSWORD = "titanic";
  const AUTH_KEY = "vp_edit_auth";

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function $all(sel, root) {
    return Array.from((root || document).querySelectorAll(sel));
  }

  function isAuthed() {
    return sessionStorage.getItem(AUTH_KEY) === "1";
  }

  function setAuthed(val) {
    if (val) sessionStorage.setItem(AUTH_KEY, "1");
    else sessionStorage.removeItem(AUTH_KEY);
    updateEditUI();
  }

  function setStatus(msg, ok) {
    const el = $("#edit-status");
    if (!el) return;
    el.textContent = msg;
    el.style.color = ok ? "#8fd694" : "#ff8a80";
  }

  function urlFn(path) {
    return typeof window.vpUrl === "function" ? window.vpUrl(path) : path;
  }

  async function api(path, opts) {
    const res = await fetch(urlFn(path), opts);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async function loadAll() {
    try {
      const [ann, vid] = await Promise.all([api("/api/annotations"), api("/api/videos")]);
      return { annotations: ann, videos: vid };
    } catch {
      return {
        annotations: JSON.parse(localStorage.getItem("vp_annotations") || "{}"),
        videos: JSON.parse(localStorage.getItem("vp_videos") || "{}"),
      };
    }
  }

  async function saveAnnotation(id, text) {
    try {
      await api("/api/annotations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, text }),
      });
      setStatus("Uloženo.", true);
    } catch {
      const all = JSON.parse(localStorage.getItem("vp_annotations") || "{}");
      all[id] = text;
      localStorage.setItem("vp_annotations", JSON.stringify(all));
      setStatus("Uloženo lokálně.", true);
    }
  }

  async function saveVideo(key, data) {
    try {
      await api("/api/videos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key, ...data }),
      });
    } catch {
      const all = JSON.parse(localStorage.getItem("vp_videos") || "{}");
      all[key] = data;
      localStorage.setItem("vp_videos", JSON.stringify(all));
    }
  }

  function posterFromEmbed(embed) {
    const m = (embed || "").match(/embed\/([^/]+)\/([^/?]+)/);
    if (!m) return "";
    return `https://cdn-thumbnails.sproutvideo.com/${m[1]}/${m[2]}/0/btn_true,btnbg_2f3437/poster.jpg`;
  }

  function playHrefFromKey(key) {
    if (!key || !key.includes("::")) return "#";
    const [slug, idx] = key.split("::");
    return urlFn(`/play/${slug}/${idx}`);
  }

  function openVideoWindow(key) {
    const url = playHrefFromKey(key);
    if (!url || url === "#") return;
    window.open(url, "_blank", "noopener,noreferrer");
  }

  function playInline(wrap) {
    const embed = wrap.dataset.defaultEmbed || "";
    const key = wrap.dataset.videoKey || "";
    const vids = wrap.dataset.vidsUrl || "";
    const toolbar = wrap.querySelector(".video-toolbar");
    wrap.querySelector(".video-display")?.remove();

    if (!embed) {
      openVideoWindow(key);
      return;
    }

    const area = document.createElement("div");
    area.className = "video-display video-inline-embed";

    const iframe = document.createElement("iframe");
    const sep = embed.includes("?") ? "&" : "?";
    iframe.src = `${embed}${sep}autoPlay=true`;
    iframe.setAttribute("allow", "autoplay; fullscreen; encrypted-media; picture-in-picture");
    iframe.allowFullscreen = true;
    iframe.title = "Video přehrávač";
    area.appendChild(iframe);

    const hints = document.createElement("p");
    hints.className = "video-open-hint";
    const playUrl = playHrefFromKey(key);
    hints.innerHTML =
      `Nepřehrává se? <a href="${playUrl}" target="_blank" rel="noopener">Otevřít přehrávač</a>` +
      (vids ? ` · <a href="${vids}" target="_blank" rel="noopener">Původní web</a>` : "");
    area.appendChild(hints);

    wrap.insertBefore(area, toolbar || null);
  }

  function bindPlayClicks(root) {
    $all(".video-wrap[data-video-key]", root).forEach((wrap) => {
      const link = wrap.querySelector(".video-play-link");
      if (!link || link.dataset.playBound) return;
      link.dataset.playBound = "1";
      link.addEventListener("click", (e) => {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
        e.preventDefault();
        playInline(wrap);
      });
    });
  }

  function buildLauncher(wrap, cfg) {
    const key = wrap.dataset.videoKey || "";
    const embed = wrap.dataset.defaultEmbed || "";
    const href = cfg?.mode === "link" && cfg.url ? cfg.url : playHrefFromKey(key);
    const poster = posterFromEmbed(embed);

    const area = document.createElement("div");
    area.className = "video-display video-launcher";

    const link = document.createElement("a");
    link.className = "video-play-link";
    link.href = href;
    link.target = "_blank";
    link.rel = "noopener";
    link.title = "Přehrát video v novém okně";
    // Native navigation – no preventDefault (avoids popup blocker)

    if (poster) {
      const img = document.createElement("img");
      img.className = "video-poster";
      img.src = poster;
      img.alt = "Náhled videa";
      link.appendChild(img);
    } else {
      const fb = document.createElement("div");
      fb.className = "video-poster-fallback";
      link.appendChild(fb);
    }

    const btn = document.createElement("span");
    btn.className = "video-play-btn";
    btn.textContent = "▶";
    link.appendChild(btn);

    const label = document.createElement("span");
    label.className = "video-play-label";
    label.textContent = "Přehrát video";
    link.appendChild(label);

    area.appendChild(link);
    const hint = document.createElement("p");
    hint.className = "video-open-hint";
    hint.textContent = "Klikněte pro přehrání videa (Ctrl+klik otevře nové okno).";
    area.appendChild(hint);
    return area;
  }

  function renderVideoWrap(wrap, cfg) {
    const toolbar = wrap.querySelector(".video-toolbar");
    wrap.querySelector(".video-display")?.remove();

    const mode = cfg?.mode || "launcher";
    if (mode === "deleted") {
      const area = document.createElement("div");
      area.className = "video-display";
      area.innerHTML = '<p class="video-deleted-msg">Video skryto.</p>';
      wrap.insertBefore(area, toolbar || null);
      return;
    }
    if (mode === "link") {
      const area = document.createElement("div");
      area.className = "video-display";
      area.innerHTML = `<a class="video-link-btn" href="${cfg.url}" target="_blank" rel="noopener">${cfg.label || "Otevřít odkaz"}</a>`;
      wrap.insertBefore(area, toolbar || null);
      return;
    }
    if (mode === "upload" && cfg.url) {
      const area = document.createElement("div");
      area.className = "video-display video-inline";
      const v = document.createElement("video");
      v.src = cfg.url;
      v.controls = true;
      v.playsInline = true;
      area.appendChild(v);
      wrap.insertBefore(area, toolbar || null);
      return;
    }
    wrap.insertBefore(buildLauncher(wrap, cfg), toolbar || null);
    bindPlayClicks(wrap);
  }

  function applyVideoOverrides(videos) {
    $all(".video-wrap[data-video-key]").forEach((wrap) => {
      const key = wrap.dataset.videoKey;
      if (videos[key]) renderVideoWrap(wrap, videos[key]);
    });
  }

  function setupLaunchers(root) {
    $all(".video-wrap[data-video-key]", root).forEach((wrap) => {
      const key = wrap.dataset.videoKey;
      const href = playHrefFromKey(key);
      const link = wrap.querySelector(".video-play-link");
      if (link && href !== "#") link.href = href;
    });
    bindPlayClicks(root);
  }

  function bindNoteBlocks() {
    $all(".note-block").forEach((block) => {
      const note = block.querySelector(".editable-note");
      if (!note) return;

      const placeholder = note.dataset.placeholder || "Klikněte pro přidání popisku…";
      if (!note.textContent.trim()) {
        note.classList.add("desc-empty");
        note.dataset.placeholder = placeholder;
      }

      block.querySelector(".note-add-desc-btn, .note-add-btn")?.addEventListener("click", () => {
        note.classList.remove("desc-empty");
        if (isAuthed()) {
          note.contentEditable = "true";
          note.focus();
        } else {
          alert("Pro úpravu popisku zadejte heslo titanic dole na stránce.");
        }
      });

      note.addEventListener("focus", () => {
        if (isAuthed()) note.classList.remove("desc-empty");
      });

      note.addEventListener("blur", () => {
        const id = block.dataset.noteId;
        const text = note.textContent.trim();
        if (!text) note.classList.add("desc-empty");
        if (id && isAuthed()) saveAnnotation(id, text);
      });
    });
  }

  function applyAnnotations(data) {
    $all(".note-block").forEach((block) => {
      const id = block.dataset.noteId;
      if (!id) return;
      const note = block.querySelector(".editable-note");
      if (note && data[id] !== undefined) {
        note.textContent = data[id];
        note.classList.toggle("desc-empty", !data[id].trim());
      }
      const custom = data[`${id}::custom`];
      if (custom) {
        let el = block.querySelector(".custom-note .custom-text");
        if (!el) {
          const wrap = document.createElement("div");
          wrap.className = "custom-note";
          wrap.innerHTML = '<div class="custom-note-label">Vlastní poznámka</div><div class="custom-text"></div>';
          block.appendChild(wrap);
          el = wrap.querySelector(".custom-text");
        }
        el.textContent = custom;
      }
    });

    $all(".editable-title-cs").forEach((el) => {
      const field = el.dataset.field || "title";
      const slug = document.body.dataset.pageSlug || "home";
      const vidKey = el.closest(".video-wrap")?.dataset?.videoKey;
      const id = vidKey ? `${vidKey}::${field}` : `${slug}::${field}`;
      if (data[id] !== undefined) el.textContent = data[id];
    });
  }

  function bindVideoToolbar() {
    $all(".video-toolbar").forEach((bar) => {
      if (bar.dataset.bound) return;
      bar.dataset.bound = "1";
      const key = bar.dataset.videoKey;
      const wrap = bar.closest(".video-wrap");

      bar.querySelector('[data-action="delete-video"]')?.addEventListener("click", () => {
        saveVideo(key, { mode: "deleted" });
        renderVideoWrap(wrap, { mode: "deleted" });
      });

      bar.querySelector('[data-action="restore-video"]')?.addEventListener("click", () => {
        saveVideo(key, { mode: "launcher" });
        renderVideoWrap(wrap, { mode: "launcher" });
        setupLaunchers(wrap);
      });

      bar.querySelector('[data-action="set-link"]')?.addEventListener("click", () => {
        const url = prompt("URL (nové okno):", wrap.dataset.vidsUrl || "https://");
        if (!url) return;
        const label = prompt("Text tlačítka:", "Otevřít video");
        const cfg = { mode: "link", url, label: label || "Otevřít video" };
        saveVideo(key, cfg);
        renderVideoWrap(wrap, cfg);
      });

      bar.querySelector('[data-action="upload-video"]')?.addEventListener("change", async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const fd = new FormData();
        fd.append("file", file);
        fd.append("key", key);
        try {
          const res = await fetch(urlFn("/api/upload-video"), { method: "POST", body: fd });
          const data = await res.json();
          if (!res.ok) throw new Error();
          const cfg = { mode: "upload", url: data.url };
          saveVideo(key, cfg);
          renderVideoWrap(wrap, cfg);
        } catch {
          saveVideo(key, { mode: "upload", url: URL.createObjectURL(file) });
          renderVideoWrap(wrap, { mode: "upload", url: URL.createObjectURL(file) });
        }
        e.target.value = "";
      });
    });
  }

  function enableEditing() {
    document.body.classList.add("edit-mode");
    $all(".editable-note, .editable-title-cs").forEach((el) => {
      el.contentEditable = "true";
    });
    bindVideoToolbar();
  }

  function disableEditing() {
    document.body.classList.remove("edit-mode");
    $all(".editable-note, .editable-title-cs, .custom-text").forEach((el) => {
      el.contentEditable = "false";
    });
  }

  function updateEditUI() {
    const loginBtn = $("#edit-login");
    const logoutBtn = $("#edit-logout");
    const passInput = $("#edit-password");
    if (!loginBtn) return;
    if (isAuthed()) {
      loginBtn.hidden = true;
      logoutBtn.hidden = false;
      if (passInput) passInput.hidden = true;
      setStatus("Režim úprav aktivní", true);
      enableEditing();
    } else {
      loginBtn.hidden = false;
      logoutBtn.hidden = true;
      if (passInput) passInput.hidden = false;
      disableEditing();
    }
  }

  async function reloadAll() {
    const { annotations, videos } = await loadAll();
    applyAnnotations(annotations);
    applyVideoOverrides(videos);
    setupLaunchers();
    bindNoteBlocks();
    bindVideoToolbar();
    if (isAuthed()) enableEditing();
  }

  window.vpReloadAnnotations = reloadAll;
  window.vpApplyVideoOverrides = reloadAll;
  window.vpActivateIframes = setupLaunchers;

  async function init() {
    await reloadAll();
    updateEditUI();
    $("#edit-login")?.addEventListener("click", async () => {
      if (($("#edit-password")?.value || "") !== PASSWORD) {
        setStatus("Špatné heslo.", false);
        return;
      }
      try {
        await api("/api/auth", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ password: PASSWORD }),
        });
      } catch (_) {}
      setAuthed(true);
    });
    $("#edit-password")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") $("#edit-login")?.click();
    });
    $("#edit-logout")?.addEventListener("click", () => {
      setAuthed(false);
      fetch(urlFn("/api/logout"), { method: "POST" }).catch(() => {});
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
