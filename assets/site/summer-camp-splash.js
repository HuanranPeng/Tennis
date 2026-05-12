(function () {
  var KEY = "upaSummerCampSplash2026";
  if (/summerholiday-camp/i.test(window.location.pathname)) return;
  var root = document.getElementById("upa-summer-splash");
  if (!root) return;
  if (sessionStorage.getItem(KEY)) return;

  function lockScroll(on) {
    document.body.style.overflow = on ? "hidden" : "";
  }

  function close() {
    sessionStorage.setItem(KEY, "1");
    root.setAttribute("hidden", "");
    root.classList.remove("upa-summer-splash--visible");
    lockScroll(false);
  }

  function open() {
    root.removeAttribute("hidden");
    root.classList.add("upa-summer-splash--visible");
    lockScroll(true);
    var btn = root.querySelector(".upa-summer-splash__cta") || root.querySelector(".upa-summer-splash__close");
    if (btn) btn.focus({ preventScroll: true });
  }

  root.addEventListener("click", function (e) {
    if (e.target.closest("[data-close-splash]")) close();
  });

  var cta = root.querySelector(".upa-summer-splash__cta");
  if (cta) {
    cta.addEventListener("click", function () {
      sessionStorage.setItem(KEY, "1");
      lockScroll(false);
    });
  }

  document.addEventListener("keydown", function onEsc(e) {
    if (e.key === "Escape" && root.classList.contains("upa-summer-splash--visible")) {
      close();
      document.removeEventListener("keydown", onEsc);
    }
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      requestAnimationFrame(open);
    });
  } else {
    requestAnimationFrame(open);
  }
})();

/** After navigation (e.g. splash “View camp details”), re-apply scroll to #camp-2026
 *  once Astro/Vue layout has settled — native hash scroll often lands too early.
 */
(function () {
  function hashCamp() {
    var h = (location.hash || "").replace(/^#/, "");
    return h === "camp-2026";
  }

  function scrollToCamp2026() {
    if (!hashCamp()) return;
    var el = document.getElementById("camp-2026");
    if (!el) return;
    el.scrollIntoView({ block: "start", behavior: "auto" });
  }

  if (!hashCamp()) return;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", scrollToCamp2026);
  } else {
    scrollToCamp2026();
  }

  window.addEventListener("load", function () {
    scrollToCamp2026();
    setTimeout(scrollToCamp2026, 80);
    setTimeout(scrollToCamp2026, 400);
  });
})();
