# Code on a slide

`code-highlight.js` highlights `<pre class="code" data-language="..." data-highlight-lines="2-3">`. Do not hand-write syntax `<span>`s. To move focus, add a next slide with new `data-highlight-lines`. For a typed command, use `.code-run` and list the command lines in `data-run-commands`.

A long line wraps under itself with a hanging indent instead of shrinking the font. A `.code-run` keeps each line whole.

Commands and listings people will copy go in a window: `<figure class="code-window">` with a `<figcaption class="code-window-bar"><i></i><i></i><i></i><span>Terminal</span></figcaption>` over the `pre.code`. Several windows stack in `.code-windows`. Prose in a window goes in `<div class="window-text">` with paragraphs.

Two versions of one thing (a bot reply and a human one, an old and a new config) use the `pair` layout: `.code-windows--pair`, the right window a `.frag`.
