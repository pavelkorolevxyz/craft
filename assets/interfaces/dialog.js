/* Открытие и закрытие модального окна.

   Фокус, клавишу выхода и верхний слой держит нативный элемент, поэтому
   механика отвечает только за вызов, закрытие по кнопке и возврат фокуса
   тому элементу, который окно открыл. */
(() => {
  "use strict";

  let opener = null;

  document.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target : null;
    if (!target) return;

    const open = target.closest("[data-dialog-open]");
    if (open) {
      const dialog = document.querySelector(open.dataset.dialogOpen || "");
      if (dialog instanceof HTMLDialogElement) {
        opener = open;
        dialog.showModal();
      }
      return;
    }

    const close = target.closest("[data-dialog-close]");
    if (close) {
      close.closest("dialog")?.close();
    }
  });

  document.addEventListener("close", (event) => {
    if (!(event.target instanceof HTMLDialogElement)) return;
    if (opener && opener.isConnected) opener.focus();
    opener = null;
  }, true);
})();
