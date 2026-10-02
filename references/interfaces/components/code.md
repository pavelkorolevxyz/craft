# Code

`code-block.html` creates a `.code-block` with `.code-block__head`, a `pre` and a `.code-block__copy` button. A button with `data-copy="#id"` points at the source. `copy.js` copies the text and toggles `.button--stable` through `aria-pressed` for two seconds. Without clipboard access under `file://`, it copies through a selection.

Set the source caption in the regular font. Monospace is for code only. Print hides the button.

`code-highlight.js` highlights code. `compose.py` copies it with the fragment, and it runs offline under `file://`. It colors HTML with inner `<style>` and `<script>`, CSS, JavaScript, JSON and shell commands. Set the language with a `language-css` class (`-html`, `-js`, `-json`, `-shell`) or `data-language` on `code`. Otherwise the script guesses from the text. Roles: element name and keyword `--accent`, attribute and string `--craft-code-gold`, number `--craft-code-blue`, punctuation `--craft-code-text`, comment `--muted`. Do not write your own highlight classes or color code by hand. For code a script inserts later, call `window.CraftCode.apply(root)`.

Inline code differs by font and `--fill-quiet`, not by color, and wraps only as a whole.
