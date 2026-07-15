window.VP_BASE = "/vectorpro-cz";
(function () {
  "use strict";
  window.VP_BASE = window.VP_BASE || "";
  window.vpUrl = function (path) {
    if (!path) return window.VP_BASE || "/";
    if (/^https?:\/\//i.test(path)) return path;
    const base = (window.VP_BASE || "").replace(/\/$/, "");
    const p = path.startsWith("/") ? path : "/" + path;
    return base + p;
  };
  window.vpStripBase = function (path) {
    if (!path) return "/";
    const base = (window.VP_BASE || "").replace(/\/$/, "");
    if (base && path.startsWith(base + "/")) return path.slice(base.length);
    if (base && path === base) return "/";
    return path;
  };
})();
