(function () {
  "use strict";

  function urlFn(path) {
    return typeof window.vpUrl === "function" ? window.vpUrl(path) : path;
  }

  function stripBase(path) {
    return typeof window.vpStripBase === "function" ? window.vpStripBase(path) : path;
  }

  function contentEl() {
    return document.querySelector(".content-panel .content") || document.querySelector("main.content");
  }

  function getSlug(pathname) {
    const m = pathname.match(/\/software\/([^/]+)/);
    return m ? m[1] : "";
  }

  function setActive(slug) {
    document.querySelectorAll(".sidebar li.active").forEach((li) => li.classList.remove("active"));
    if (!slug) return;
    document.querySelectorAll(".sidebar a").forEach((a) => {
      const href = stripBase(a.getAttribute("href") || "");
      const norm = normalizeHref(href);
      if (norm === `/software/${slug}/`) {
        a.closest("li")?.classList.add("active");
      }
    });
  }

  function showLoading() {
    const main = contentEl();
    if (main) main.style.opacity = "0.45";
  }

  function hideLoading() {
    const main = contentEl();
    if (main) main.style.opacity = "1";
  }

  async function loadPage(url, push) {
    showLoading();
    try {
      const res = await fetch(url, { credentials: "same-origin" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const html = await res.text();
      const doc = new DOMParser().parseFromString(html, "text/html");
      const newMain = doc.querySelector(".content-panel .content") || doc.querySelector("main.content");
      const oldMain = contentEl();
      if (!newMain || !oldMain) {
        window.location.href = url;
        return;
      }

      oldMain.innerHTML = newMain.innerHTML;
      document.title = doc.title;
      const slug = doc.body?.dataset?.pageSlug || getSlug(stripBase(url));
      document.body.dataset.pageSlug = slug;
      setActive(slug);

      if (push) history.pushState({ url }, "", url);

      const panel = document.querySelector(".content-panel");
      if (panel) panel.scrollIntoView({ behavior: "smooth", block: "start" });

      if (typeof window.vpReloadAnnotations === "function") window.vpReloadAnnotations();
      else if (typeof window.vpActivateIframes === "function") window.vpActivateIframes(oldMain);
      if (typeof window.vpApplyVideoOverrides === "function") window.vpApplyVideoOverrides();
      else if (typeof window.vpActivateIframes === "function") window.vpActivateIframes(oldMain);
    } catch (err) {
      console.warn("SPA load failed", err);
      window.location.href = url;
    } finally {
      hideLoading();
    }
  }

  function normalizeHref(href) {
    href = stripBase(href || "");
    if (!href) return "";
    if (href.startsWith("http")) {
      try {
        return stripBase(new URL(href).pathname.replace(/\/index\.html$/, "/").replace(/\/?$/, "/"));
      } catch {
        return href;
      }
    }
    if (href.includes("software/")) {
      const m = href.match(/software\/([^/]+)/);
      if (m) return `/software/${m[1]}/`;
    }
    if (href.startsWith("/software/")) {
      return href.replace(/\/index\.html$/, "/").replace(/\/?$/, "/");
    }
    return href;
  }

  function init() {
    const sidebar = document.querySelector(".sidebar");
    if (!sidebar) return;

    sidebar.addEventListener("click", (e) => {
      const a = e.target.closest("a");
      if (!a) return;
      const href = a.getAttribute("href") || "";
      if (!href.includes("/software/") && !href.includes("software/")) return;

      const path = normalizeHref(href);
      if (!path.startsWith("/software/")) return;

      e.preventDefault();
      loadPage(urlFn(path), true);
    });

    window.addEventListener("popstate", (e) => {
      const url = (e.state && e.state.url) || location.pathname;
      if (url.includes("/software/")) loadPage(url, false);
    });

    setActive(document.body.dataset.pageSlug || getSlug(stripBase(location.pathname)));
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
