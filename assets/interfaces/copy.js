/* Копирование текста в буфер обмена для блока кода и любого значения,
   которое пользователь переносит в другой инструмент.

   Кнопка ссылается на источник через data-copy, а результат показывает
   второй подписью в той же ячейке, поэтому её размер не меняется.
   На file:// защищённого контекста нет и современный интерфейс буфера
   недоступен, поэтому остаётся запасной путь через выделение. */
(() => {
  "use strict";

  const RESET = 2000;
  const timers = new WeakMap();

  function fallback(text) {
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("aria-hidden", "true");
    area.style.position = "fixed";
    area.style.top = "-1000px";
    document.body.append(area);
    area.select();
    try {
      return document.execCommand("copy");
    } finally {
      area.remove();
    }
  }

  async function copy(text) {
    if (window.isSecureContext && navigator.clipboard) {
      try {
        await navigator.clipboard.writeText(text);
        return true;
      } catch {
        return fallback(text);
      }
    }
    return fallback(text);
  }

  document.addEventListener("click", async (event) => {
    const target = event.target instanceof Element ? event.target.closest("[data-copy]") : null;
    if (!target) return;
    const source = document.querySelector(target.dataset.copy || "");
    if (!source) return;
    const done = await copy(source.textContent || "");
    if (!done) return;
    target.setAttribute("aria-pressed", "true");
    clearTimeout(timers.get(target));
    timers.set(target, setTimeout(() => target.setAttribute("aria-pressed", "false"), RESET));
  });
})();
