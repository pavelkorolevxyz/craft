/* Fills the passed part of a range slider.

   The browser draws the slider track as one background and gives no way to
   split it into passed and remaining parts. Chromium has no pseudo-element
   for that. The script keeps the fraction in --value and CSS paints it, so
   the markup stays native. Without the script the slider still works and
   looks like a rail with no fill.

   It uses the same property as .progress__fill. The range and the progress
   bar share the mechanics and the paint. */
(() => {
  "use strict";

  function paint(input) {
    const min = Number(input.min === "" ? 0 : input.min);
    const max = Number(input.max === "" ? 100 : input.max);
    const span = max - min;
    const share = span > 0 ? (Number(input.value) - min) / span : 0;
    input.style.setProperty("--value", `${Math.min(Math.max(share, 0), 1) * 100}%`);
  }

  document.addEventListener("input", (event) => {
    const target = event.target;
    if (target instanceof HTMLInputElement && target.classList.contains("range")) paint(target);
  });

  function start() {
    document.querySelectorAll("input.range").forEach(paint);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
