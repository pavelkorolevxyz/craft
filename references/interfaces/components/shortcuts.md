# Keyboard shortcuts

Use them only for repeated work, not a one-off report. The action keeps its regular control. Show the shortcut with `<kbd>` and `aria-keyshortcuts`, and add a handler.

- Do not intercept typing in `input`, `textarea`, `select`, `contenteditable`, or browser and system shortcuts.
- A single letter is fine for a frequent, reversible action. Ignore `event.repeat` if a repeat creates extra work.
- Use `event.code` for a physical key and `event.key` for a typed character.
- Keep focus in place and report the result with a visible state or `aria-live`. A cheat sheet fits in a line or a `<details>`, not a dialog.
