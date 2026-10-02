# Dialog

```html
<button class="button" type="button" data-dialog-open="#confirm">Revoke access</button>
```

`dialog.js` opens the native dialog and returns focus to the button that opened it after it closes. The element itself handles the focus trap, the Escape key and the backdrop, so you do not need your own.

Use a dialog to confirm an irreversible action or for a short form the work cannot continue without. Help, record details and long forms live on the page or in a side area, because a dialog cuts the user off from context.

The dialog title names the decision, not the subject. The confirm button repeats the action verb: "Revoke", not "Yes". An action that loses data stays reversible or explains the consequence in text.

Fragment: `dialog.html`.
