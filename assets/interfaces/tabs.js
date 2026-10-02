/* Tabs. Picks a panel with the mouse or the keyboard.

   The markup already describes the links through role, aria-controls and
   aria-selected, so the mechanics only move the selection. Arrow keys move
   focus together with the selection, as users expect from a tab list. Home
   and End jump to the first and last tab. */
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
      if (panel) {
        panel.hidden = !current;
        // On paper the panels print one after another without the tab bar, and CSS prints the label.
        panel.dataset.tabLabel = item.textContent.trim();
      }
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
