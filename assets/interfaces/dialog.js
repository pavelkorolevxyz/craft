/* Opens and closes a modal dialog.

   The native element handles focus, the Escape key and the top layer. The
   mechanics only open the dialog, close it from a button and return focus
   to the element that opened it. */
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
