# Page shell

Only for the `blank` template. The `bare` starter skips this reference.

## Frame and theme

`<main class="shell" data-craft-shell="app">` opens with `.workspace-head--compact`: `h1` on the left, page tools on the right, the theme toggle last. Page-wide controls live in the header, sections in `.tabs--page` below it. With `data-craft-shell`, the validator requires a working toggle.

A custom theme button: `data-theme-toggle`, `aria-pressed="false"`, classes `.button--stable .button--icon .theme-switch` and SVG labels `.button__label--rest`, `.button__label--pressed`. `theme.js` sets its name and tooltip.

## Action feedback

Show the result of a click, selection or key press at once, in view. Do not silently redraw a panel off screen. If list and details stacked into one column, open the details at the row or move the user there. A hidden `aria-live` does not replace a visible status. Test every action at 320 px.
