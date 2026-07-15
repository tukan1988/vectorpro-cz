(function () {
  "use strict";

  const AUTH_KEY = "vp_edit_auth";
  const STORE_KEY = "vp_edit_store";
  const WEB_PASSWORD = "titanic";
  const GH_TOKEN_KEY = "vp_gh_token";

  let storeMode = sessionStorage.getItem(STORE_KEY) || "auto";
  let gh = null;
  let saveQueue = Promise.resolve();

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
    else {
      sessionStorage.removeItem(AUTH_KEY);
      sessionStorage.removeItem(GH_TOKEN_KEY);
      sessionStorage.removeItem(STORE_KEY);
      gh = null;
      storeMode = "auto";
    }
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

  function b64encodeUtf8(str) {
    const bytes = new TextEncoder().encode(str);
    let bin = "";
    bytes.forEach((b) => {
      bin += String.fromCharCode(b);
    });
    return btoa(bin);
  }

  function b64decode(str) {
    const bin = atob(str);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return bytes;
  }

  async function decryptGithubToken(password, cfg) {
    const salt = b64decode(cfg.salt);
    const nonce = b64decode(cfg.nonce);
    const data = b64decode(cfg.data);
    const enc = new TextEncoder();
    const material = await crypto.subtle.importKey("raw", enc.encode(password), "PBKDF2", false, [
      "deriveKey",
    ]);
    const key = await crypto.subtle.deriveKey(
      { name: "PBKDF2", salt, iterations: 120000, hash: "SHA-256" },
      material,
      { name: "AES-GCM", length: 256 },
      false,
      ["decrypt"]
    );
    const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv: nonce }, key, data);
    return new TextDecoder().decode(plain);
  }

  async function initGithub(password) {
    const res = await fetch(urlFn("/assets/gh-edit.json"), { cache: "no-store" });
    if (!res.ok) throw new Error("Chybí konfigurace GitHub editace");
    const cfg = await res.json();
    const token = await decryptGithubToken(password, cfg);
    gh = { owner: cfg.owner, repo: cfg.repo, token };
    sessionStorage.setItem(GH_TOKEN_KEY, token);
    sessionStorage.setItem(STORE_KEY, "github");
    storeMode = "github";
  }

  async function ensureGithub() {
    if (gh && gh.token) return gh;
    const token = sessionStorage.getItem(GH_TOKEN_KEY);
    if (!token) throw new Error("Nejste přihlášeni k GitHub ukládání");
    const res = await fetch(urlFn("/assets/gh-edit.json"), { cache: "no-store" });
    const cfg = await res.json();
    gh = { owner: cfg.owner, repo: cfg.repo, token };
    return gh;
  }

  async function githubGetJson(path, branch) {
    const { owner, repo, token } = await ensureGithub();
    const url = `https://api.github.com/repos/${owner}/${repo}/contents/${path}?ref=${encodeURIComponent(branch)}`;
    const res = await fetch(url, {
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${token}`,
      },
    });
    if (res.status === 404) return { data: {}, sha: null };
    if (!res.ok) throw new Error(await res.text());
    const meta = await res.json();
    const raw = atob(meta.content.replace(/\n/g, ""));
    const bytes = Uint8Array.from(raw, (c) => c.charCodeAt(0));
    const json = JSON.parse(new TextDecoder().decode(bytes));
    return { data: json, sha: meta.sha };
  }

  async function githubPutJson(path, branch, obj, message) {
    const { owner, repo, token } = await ensureGithub();
    const url = `https://api.github.com/repos/${owner}/${repo}/contents/${path}`;
    let sha = null;
    const get = await fetch(`${url}?ref=${encodeURIComponent(branch)}`, {
      headers: { Accept: "application/vnd.github+json", Authorization: `Bearer ${token}` },
    });
    if (get.ok) sha = (await get.json()).sha;
    const body = {
      message: message || `Update ${path}`,
      content: b64encodeUtf8(JSON.stringify(obj, null, 2) + "\n"),
      branch,
    };
    if (sha) body.sha = sha;
    const res = await fetch(url, {
      method: "PUT",
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async function saveJsonToGithub(kind, mutator) {
    const pagesPath = kind === "annotations" ? "data/annotations.json" : "data/video-overrides.json";
    const mainPath =
      kind === "annotations"
        ? "vectorpro-cz/data/annotations.json"
        : "vectorpro-cz/data/video-overrides.json";

    saveQueue = saveQueue.then(async () => {
      const pageFile = await githubGetJson(pagesPath, "gh-pages");
      const next = { ...(pageFile.data || {}) };
      mutator(next);
      await githubPutJson(pagesPath, "gh-pages", next, `Edit ${kind} (web)`);
      try {
        await githubPutJson(mainPath, "main", next, `Edit ${kind} (web)`);
      } catch (err) {
        console.warn("Sync na main selhal", err);
      }
    });
    await saveQueue;
  }

  async function loadStaticJson(path, fallbackKey) {
    try {
      const res = await fetch(urlFn(path), { cache: "no-store" });
      if (res.ok) return await res.json();
    } catch (_) {}
    try {
      return JSON.parse(localStorage.getItem(fallbackKey) || "{}");
    } catch {
      return {};
    }
  }

  async function loadAll() {
    try {
      const [ann, vid] = await Promise.all([api("/api/annotations"), api("/api/videos")]);
      storeMode = "local";
      return { annotations: ann, videos: vid };
    } catch {
      const [annotations, videos] = await Promise.all([
        loadStaticJson("/data/annotations.json", "vp_annotations"),
        loadStaticJson("/data/video-overrides.json", "vp_videos"),
      ]);
      return { annotations, videos };
    }
  }

  async function saveAnnotation(id, text) {
    if (storeMode === "github" || sessionStorage.getItem(STORE_KEY) === "github") {
      try {
        setStatus("Ukládám na GitHub…", true);
        await saveJsonToGithub("annotations", (all) => {
          if (text) all[id] = text;
          else delete all[id];
        });
        setStatus("Uloženo na GitHub.", true);
        return;
      } catch (err) {
        console.warn(err);
        setStatus("Uložení na GitHub selhalo.", false);
      }
    }
    try {
      await api("/api/annotations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, text }),
      });
      setStatus("Uloženo.", true);
    } catch {
      const all = JSON.parse(localStorage.getItem("vp_annotations") || "{}");
      if (text) all[id] = text;
      else delete all[id];
      localStorage.setItem("vp_annotations", JSON.stringify(all));
      setStatus("Uloženo lokálně.", true);
    }
  }

  async function saveVideo(key, data) {
    if (storeMode === "github" || sessionStorage.getItem(STORE_KEY) === "github") {
      try {
        setStatus("Ukládám video nastavení…", true);
        await saveJsonToGithub("videos", (all) => {
          if (data && Object.keys(data).length) all[key] = data;
          else delete all[key];
        });
        setStatus("Uloženo na GitHub.", true);
        return;
      } catch (err) {
        console.warn(err);
        setStatus("Uložení na GitHub selhalo.", false);
      }
    }
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
          alert("Pro úpravu popisku se nejdříve přihlaste dole na stránce.");
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

    $all(".editable-title-cs").forEach((el) => {
      if (el.dataset.titleBound) return;
      el.dataset.titleBound = "1";
      el.addEventListener("blur", () => {
        if (!isAuthed()) return;
        const field = el.dataset.field || "title";
        const slug = document.body.dataset.pageSlug || "home";
        const vidKey = el.closest(".video-wrap")?.dataset?.videoKey;
        const id = vidKey ? `${vidKey}::${field}` : `${slug}::${field}`;
        saveAnnotation(id, el.textContent.trim());
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
        if (storeMode === "github" || sessionStorage.getItem(STORE_KEY) === "github") {
          alert("Na webu GitHub použijte „Nastavit odkaz“ (upload velkých videí není podporován).");
          e.target.value = "";
          return;
        }
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
    if (sessionStorage.getItem(STORE_KEY) === "github" && sessionStorage.getItem(GH_TOKEN_KEY)) {
      storeMode = "github";
      try {
        await ensureGithub();
      } catch (_) {}
    }
    await reloadAll();
    updateEditUI();
    $("#edit-login")?.addEventListener("click", async () => {
      const pass = ($("#edit-password")?.value || "").trim();
      if (!pass) {
        setStatus("Zadejte heslo.", false);
        return;
      }
      try {
        await api("/api/auth", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ password: pass }),
        });
        storeMode = "local";
        sessionStorage.setItem(STORE_KEY, "local");
        setAuthed(true);
        return;
      } catch (_) {
        /* static GitHub Pages – continue */
      }
      if (pass !== WEB_PASSWORD) {
        setStatus("Špatné heslo.", false);
        return;
      }
      try {
        setStatus("Přihlašuji…", true);
        await initGithub(pass);
        setAuthed(true);
        setStatus("Režim úprav aktivní (ukládá na GitHub)", true);
      } catch (err) {
        console.warn(err);
        setStatus("Přihlášení selhalo (GitHub konfigurace).", false);
      }
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
