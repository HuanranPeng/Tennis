/**
 * Zyro mobile nav opens by toggling .block-header-layout-mobile__dropdown--open (Vue).
 * If hydration misses the handler, the class never toggles. This listens in capture,
 * compares state after a short delay, and toggles only when nothing changed (Vue no-op).
 */
(function () {
  var OPEN = "block-header-layout-mobile__dropdown--open";
  var DELAY_MS = 80;

  function dropdown() {
    return document.querySelector(".block-header-layout-mobile__dropdown");
  }

  function setBodyOpen(on) {
    var v = !!on;
    document.body.classList.toggle("zyro-mobile-nav-open", v);
    document.documentElement.classList.toggle("zyro-mobile-nav-open", v);
    var b = document.querySelector("button.block-header__hamburger-menu");
    if (b) b.setAttribute("aria-expanded", v ? "true" : "false");
  }

  function close() {
    var d = dropdown();
    if (d) d.classList.remove(OPEN);
    setBodyOpen(false);
  }

  document.addEventListener(
    "click",
    function (e) {
      var d = dropdown();
      if (!d) return;

      if (e.target.closest("button.block-header__hamburger-menu")) {
        var before = d.classList.contains(OPEN);
        window.setTimeout(function () {
          var after = d.classList.contains(OPEN);
          if (after === before) d.classList.toggle(OPEN);
          setBodyOpen(d.classList.contains(OPEN));
        }, DELAY_MS);
        return;
      }

      if (!d.classList.contains(OPEN)) return;

      if (e.target.closest(".block-header-layout-mobile__dropdown a")) {
        close();
        return;
      }

      if (!e.target.closest(".block-header-layout-mobile")) close();
    },
    true
  );

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") close();
  });
})();
