/* Вкладки: выбор панели мышью и клавиатурой.

   Разметка уже описывает связи через role, aria-controls и aria-selected,
   поэтому механика только переносит выбор. Стрелки двигают фокус вместе с
   выбором, как этого ждут от списка вкладок, а Home и End доводят до края. */
(() => {
  "use strict";

  function tabsOf(list) {
    return [...list.querySelectorAll('[role="tab"]:not(:disabled)')];
  }

  function select(list, tab) {
    for (const item of tabsOf(list)) {
      const current = item === tab;
      item.setAttribute("aria-selected", String(current));
      item.tabIndex = current ? 0 : -1;
      const panel = document.getElementById(item.getAttribute("aria-controls") || "");
      if (panel) panel.hidden = !current;
    }
  }

  function setup(list) {
    const tabs = tabsOf(list);
    if (!tabs.length) return;
    const active = tabs.find((tab) => tab.getAttribute("aria-selected") === "true") || tabs[0];
    select(list, active);

    list.addEventListener("click", (event) => {
      const tab = event.target instanceof Element ? event.target.closest('[role="tab"]') : null;
      if (tab && !tab.disabled) select(list, tab);
    });

    list.addEventListener("keydown", (event) => {
      const items = tabsOf(list);
      const index = items.indexOf(document.activeElement);
      if (index < 0) return;
      const step = { ArrowRight: 1, ArrowLeft: -1, Home: -index, End: items.length - 1 - index }[event.key];
      if (step === undefined) return;
      event.preventDefault();
      const next = items[(index + step + items.length) % items.length];
      select(list, next);
      next.focus();
    });
  }

  function init() {
    for (const list of document.querySelectorAll('[data-tabs] [role="tablist"]')) setup(list);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
