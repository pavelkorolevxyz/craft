# Document building blocks

Pick the geometry in [page geometry](../layout.md). Available blocks:

| Class | Purpose |
|---|---|
| `.split` | Unequal columns. Other geometry needs a local class |
| `.stack` | Vertical group with `--stack-gap` |
| `.document-band` | Full-width band with padding around a readable text column |
| `.document-block` | Standalone bounded block, centered as a whole |
| `.document-block--framed` | Border extends past the text column by the inner padding |
| `.prose` | Line length for text, not a width cap for a workspace |
| `.equal-panels`, `.equal-panel` | Matching dividers across neighbor panels via `subgrid` |

```html
<div class="equal-panels chart-grid">
  <article class="equal-panel">
    <header class="equal-panel__head">Title</header>
    <div class="equal-panel__body">Content</div>
    <footer class="equal-panel__foot">Total</footer>
  </article>
</div>
```

The three zones align only neighbors in one row. A single panel and a vertical stack keep their natural height. Do not use document classes on a dashboard or a work tool.
