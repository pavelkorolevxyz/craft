# Page geometry

The starter is empty. Pick a mode for the task, then add only the fragments you need. One page can mix modes.

| Mode | When to use | Geometry and base |
|---|---|---|
| Document | Reading a report or study top to bottom | `page-head`, sections with `.document-band`, text in `.prose`. A standalone bounded block uses `.document-block`, framed with `.document-block--framed` |
| Data view | Comparing values, finding outliers | `workspace-head`, a full-width table or chart. Filters sit above the area they change. Metrics back up the finding and do not become a splash screen |
| Workspace | Picking a record, editing, working with details | `workspace-head` and `split-workspace`. The main work area starts on the first screen. On a narrow screen the columns stack and share one scroll |

Do not center a tool like a text document. Do not split the page in half just because there are two blocks. `split-workspace` is for a main area and its related details. On mobile, after an explicit selection, take the user to the details, but do not scroll the page on every arrow key. The selection mechanics are in [master-detail](components/master-detail.md).

A catalog of titles and dates stays a list of rows. Do not add cards, descriptions or tags from a reference design unless asked.

Align compared values on a shared row or column. A growing feed gets the full row, not a short panel beside something else. Headings and a rule separate work areas. Backgrounds come from the ready theme, with no separate shade for each panel.

## Shell and header

```html
<main class="shell" data-craft-layout="interface">
  <header class="page-head">
    <div class="page-head__main">
      <h1>Page title</h1>
      <p class="page-head__lede">A short explanation.</p>
    </div>
  </header>
  <section class="section">
    <div class="section-head"><h2>Data</h2><p>Source and period.</p></div>
  </section>
</main>
```

`.shell` is full width. Use `page-head.html` for a document and `workspace-head.html` for a compact header with controls. The compact header is one bar, the title and a couple of tools on a centered row, on a phone too. A lede is optional: add `<p class="workspace-head__lede">` under the title only when the current state needs a line, and the tools then align to its last line. An eyebrow line and a separate metadata column are not part of the base header.

`section.html` creates a standalone part with an `h2`. `.section--tight` trims padding for tables and logs. Use `.section--accent` only for an accent that carries meaning. A right-hand controls column needs its own local composition.

## Hierarchy and borders

- The main work or text starts on the first screen. The header holds the title and the controls you need, not a promo block. Add metrics only when they support the task.
- A title's explanation sits right under it. Standalone controls and actions can go on the right, but not a detached subtitle.
- Do not add a decorative line above the title, counters repeated in a paragraph, an icon over every section or a footer with the design system's name.
- Put areas of similar height side by side. A growing feed takes a row, a short summary goes above or below. Keep a bounded text and its note in one bounded grid, or a wide `.split` leaves an empty strip between them.
- A border has one owner. Use `border-collapse: collapse` for tables and a single line at each join for grids. Do not fake empty-cell borders with pseudo-elements.
- Leave a group gap between a framed block and the next section's divider. Align the block's content, not its outer border, to the text column. `.document-block--framed` does this.
- Matching neighbor panels align their header, body and total zones with `.equal-panels` and `.equal-panel`, not with fixed heights.
- The page scrolls by default. Use nested scroll only for an independent area, such as an editor or a long queue. Give it an accessible name, keyboard access and enough height. Add `overscroll-behavior: contain` only to a region with a bounded height. On a region with nothing to scroll, Chromium keeps the wheel and the page under it stops scrolling. On mobile, return to the page flow. Table rules are in [tables](components/tables.md).

## Local data

Embed a small dataset in the HTML or a local script. Under `file://`, load large data with a plain `<script>`, not `fetch()` of a local JSON file. Use JavaScript for real interaction, not for static composition. Keep state in the URL or `localStorage` only when it helps repeat work.
