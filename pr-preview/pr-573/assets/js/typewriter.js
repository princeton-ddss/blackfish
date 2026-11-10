/* Cycling typewriter for the home hero, mirroring the dashboard's
 * react-simple-typewriter settings (web/src/routes/dashboard/dashboard.jsx):
 * 60ms type, 50ms delete, blinking "|" cursor. */
(function () {
  "use strict";

  var TYPE_MS = 60;
  var DELETE_MS = 50;
  var HOLD_MS = 1800;
  var NEXT_MS = 400;

  function start(el) {
    if (el.dataset.twRunning === "1") return;
    el.dataset.twRunning = "1";

    var words;
    try {
      words = JSON.parse(el.getAttribute("data-words") || "[]");
    } catch (e) {
      words = [];
    }
    if (!words.length) return;

    var out = el.querySelector(".tw-text");
    if (!out) return;

    // Respect users who ask for less motion: show the first line, no animation.
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      out.textContent = words[0];
      return;
    }

    var w = 0;
    var i = 0;
    var deleting = false;

    function tick() {
      var word = words[w];
      out.textContent = word.slice(0, i);

      if (!deleting && i === word.length) {
        deleting = true;
        return setTimeout(tick, HOLD_MS);
      }
      if (deleting && i === 0) {
        deleting = false;
        w = (w + 1) % words.length;
        return setTimeout(tick, NEXT_MS);
      }
      i += deleting ? -1 : 1;
      setTimeout(tick, deleting ? DELETE_MS : TYPE_MS);
    }

    tick();
  }

  function init() {
    var el = document.querySelector("[data-typewriter]");
    if (el) start(el);
  }

  document.addEventListener("DOMContentLoaded", init);
  // navigation.instant swaps content without a reload.
  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(init);
  }
})();
