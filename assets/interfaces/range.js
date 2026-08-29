/* Заливка пройденной части шкалы значения.

   Дорожка ползунка рисуется одним фоном, а браузер не даёт разделить её на
   пройденную и оставшуюся часть: у Chromium для этого нет псевдоэлемента.
   Скрипт держит долю в --value, а красит её CSS, поэтому разметка остаётся
   нативной, а без скрипта шкала работает и выглядит как рельса без заливки.

   Свойство то же, что у .progress__fill: у шкалы и прогресса одна механика
   и одна краска. */
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
