/**
 * Zyro sticky nav: when .sticky-trigger leaves the viewport, the real app sets a
 * solid header background + .block-header--with-shadow. If Vue hydrates late
 * or fails, this mirrors that behavior via html[data-header-scrolled].
 */
(function () {
  if (!("IntersectionObserver" in window)) return;

  function setScrolled(on) {
    document.documentElement.toggleAttribute("data-header-scrolled", on);
  }

  function run() {
    var trigger = document.querySelector(".sticky-trigger");
    if (!trigger) return;
    var io = new IntersectionObserver(
      function (entries) {
        var e = entries[0];
        if (!e) return;
        setScrolled(!e.isIntersecting);
      },
      { root: null, rootMargin: "0px", threshold: 0 }
    );
    io.observe(trigger);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();
