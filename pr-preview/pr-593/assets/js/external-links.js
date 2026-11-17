/* Mark off-site links so they open in a new tab. The nav is generated from
 * config, so there is no place to set target= on an external entry by hand. */
(function () {
  "use strict";

  function init() {
    var origin = window.location.origin;
    var links = document.querySelectorAll('a[href^="http://"], a[href^="https://"]');
    Array.prototype.forEach.call(links, function (a) {
      if (a.href.indexOf(origin) === 0) return;
      if (a.hasAttribute("target")) return;
      a.setAttribute("target", "_blank");
      // Avoid handing the new tab a reference back to this window.
      a.setAttribute("rel", a.getAttribute("rel") ? a.getAttribute("rel") + " noopener" : "noopener");
    });
  }

  document.addEventListener("DOMContentLoaded", init);
  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(init);
  }
})();
