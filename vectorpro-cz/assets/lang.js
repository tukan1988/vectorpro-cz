(function () {
  "use strict";

  const KEY = "vp_english";

  function isOn() {
    return localStorage.getItem(KEY) === "1";
  }

  function apply(on) {
    document.body.classList.toggle("show-english", on);
    const btn = document.getElementById("english-toggle");
    if (btn) {
      btn.textContent = on ? "English OFF" : "English ON";
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    }
  }

  function init() {
    const header = document.querySelector(".site-header");
    if (header && !document.getElementById("english-toggle")) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.id = "english-toggle";
      btn.className = "english-toggle";
      btn.title = "Zobrazit nebo skrýt anglické texty";
      btn.addEventListener("click", () => {
        const next = !isOn();
        localStorage.setItem(KEY, next ? "1" : "0");
        apply(next);
      });
      const orig = header.querySelector(".orig-link");
      if (orig) header.insertBefore(btn, orig);
      else header.appendChild(btn);
    }
    apply(isOn());
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.vpApplyEnglish = apply;
})();
