# Deck build and mechanics

Layout and reveal choices live in the [selection rules](selection.md), styling in the [visual language](design-language.md). Setup, `compose.py` and the check order are in the [workflow](../workflow.md).

## Source slide

Live examples: `catalog/slides/index.html` and `case-study.html`. Do not copy the catalog's order.

One slide is one `<section class="slide" data-slide-layout="..." data-key="...">`. Leave `<p class="slide-number"></p>` empty, the mechanics fill in the number. The deck's first heading is an `h1`. Other slides may use `.slide-title`.

Start a standard slide with `compose.py --key`, not markup from memory. The check matches each layout against its traits in `layoutGuidance.signature`: an end slide without `.s-end`, a resource without `.qr-link` or a list without `.bullets` fails. If no layout solves the task, mark the slide `data-composition="local"` and give the reason in `data-local-reason`. Set `data-slide-layout` to the closest layout. Do not add kickers or navigation labels to the number, the top left title, dividers, the cover or the end: the check compares chrome positions across all pages of one layout.

## Key, not number

`data-key` is the permanent address of a source slide, made of lowercase Latin letters, digits and hyphens. Page numbers change when slides move. Keys do not. `#key` opens the slide's first state, `#key/2` the second reveal, `#12` the twelfth page.

Before editing by number, resolve it to a key:

```bash
python3 scripts/deck_map.py <deck> 19 20
```

The order of edits from feedback is in the [workflow](../workflow.md).

## Status

`data-status="draft"` prints a "Draft" badge (`data-status-label` changes the text). `data-status="skip"` removes the slide from the show and the PDF without deleting the source. `?skipped=show` shows it temporarily. Set the status on each source slide, not on a page range.

## Reveal

`deck.js` creates a page with a number, an address and a PDF sheet for each `.frag` in HTML order. Do not copy slide HTML by hand.

A link appears together with its node:

```html
<div class="flow place-fill">
  <div class="flow-node"><strong>Client</strong></div>
  <div class="flow-step frag">
    <b class="flow-arrow" aria-hidden="true"></b>
    <div class="flow-node"><strong>Server</strong></div>
  </div>
</div>
```

One `.frag` wrapper holds the parts of one frame: an arrow with its node, a caption with its image. A part in another container joins the same click with `data-frag="with-previous"`. An intended step inside a revealed block uses `data-frag="nested"`. Any other `.frag` nesting is an error.

Shown content stays in place. Mark an intended layout change between steps with `data-shift="intended"`.

## Controls and accessibility

Arrow keys and space change pages. `G` toggles the grid, `L` the strip, `F` full screen, `T` the theme, `M` motion, `H` the control panel. The browser remembers the theme.

A slide's accessible name comes from its first `h1`, `h2`, `h3` or `.slide-title`. A table needs a slide title and a `caption`. The mechanics link them with `aria-labelledby`.

Local mechanics listen for the `craft-slidechange` event instead of watching attributes. `window.craftDeck` exposes the page map and the motion policy.

## Show and review

`?reveal=steps` (the default) shows every reveal for the talk. `?reveal=final` shows each slide's final frame for review. The PDF prints the open mode. There is one source: do not collapse reveals for review, and do not add `.frag` to every item for a test.
