/**
 * Sticky nav bar: after scrolling past .sticky-trigger, match Zyro (opaque bar + light shadow).
 * Uses scroll/resize + optional IntersectionObserver; retries until the sentinel exists (SSR inside astro-island).
 */
(function () {
  var rafId = 0;
  var waitTries = 0;
  var maxWait = 240;

  function sync() {
    var t = document.querySelector(".sticky-trigger");
    var past = false;
    if (t) {
      var r = t.getBoundingClientRect();
      past = r.bottom <= 0.5;
    } else {
      var y = window.scrollY || document.documentElement.scrollTop || 0;
      past = y > 48;
    }
    document.documentElement.toggleAttribute("data-header-scrolled", past);
  }

  function onScroll() {
    if (rafId) return;
    rafId = requestAnimationFrame(function () {
      rafId = 0;
      sync();
    });
  }

  function bind() {
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", sync, { passive: true });
    window.addEventListener("pageshow", sync);
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden) sync();
    });
    sync();
  }

  function waitForTrigger() {
    sync();
    if (document.querySelector(".sticky-trigger")) {
      bind();
      if ("IntersectionObserver" in window) {
        var t = document.querySelector(".sticky-trigger");
        var io = new IntersectionObserver(
          function () {
            sync();
          },
          { root: null, rootMargin: "0px", threshold: [0, 0.01, 1] }
        );
        io.observe(t);
      }
      return;
    }
    if (waitTries++ < maxWait) {
      requestAnimationFrame(waitForTrigger);
    } else {
      bind();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", waitForTrigger);
  } else {
    waitForTrigger();
  }
})();
