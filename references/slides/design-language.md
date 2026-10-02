# Slide visual language

Choose the layout and reveal plan with the [selection rules](selection.md). Take HTML and mechanics from the [mechanics](authoring.md). This file covers only styling. For numeric visuals, also read [charts](charts.md).

## Stage and scale

- A fixed 16:9 stage, built for a projector, a TV and a phone recording. Do not stretch a responsive interface to slide size.
- A page uses the current theme's neutral background or the red accent one. `.surface-panel` is a local surface, not a third page background.
- Content is no smaller than about `1.4cqw`. If a table, code or caption is unreadable on a 390 px wide stage, split the material instead of shrinking the font.
- The only persistent chrome is an optional title at top left and the number at bottom right.
- An image may fill the whole slide. Add a caption only for context or to point at a detail.
- A URL shown on a slide comes with a large working QR code, one resource per slide. `scripts/qr.py` makes the code. Rules are in [QR code](qr.md).

## Theme roles

Shared limits on color, fonts and motion are in [identity](../identity.md). Local roles:

| Role | Purpose |
|---|---|
| `--accent` | Readable red text |
| `--accent-mark` | A saturated dot, line or outline |
| `--accent-fill` | A fill under white text |
| `.surface-accent` | An accent fill with quiet roles already swapped: quiet text takes `--on-accent-muted`, not transparency over white |
| `.surface-panel`, `.surface-code` | A local neutral surface, the background of real code |

## Type and composition

| Class | Job |
|---|---|
| `.type-hero` | The dominant claim |
| `.type-title`, `.type-heading` | Main and local headings |
| `.type-lede`, `.type-note` | A large explanation, a source or a caveat |
| `.type-metric` | A number that proves the claim |
| `.slide-title`, `.content-block` | Slide title, a local heading with an explanation |
| `.stack`, `.cluster`, `.columns` | Vertical group, row, columns |
| `.content-aside` | A `.9fr / 1.1fr` split, more room on the right |
| `.content-aside--separated` | A wider gap when the main material already has labels on the right |
| `.place-center`, `.place-fill`, `.bleed-x` | Centering, filling, bleeding to the edges |
| `.frame`, `.media-contain`, `.media-cover` | Media area, fit inside, fill with cropping |
| `.placeholder` | Only a temporary stand-in inside `.frame`, `.photo` or `.shot` |
| `.qr`, `.qr-link` | A QR code, and a code paired with its URL |

Reuse the roles. Do not invent a new font size and caption style for each layout. A local class changes the geometry of one composition. Its CSS lives next to the deck, not in the shared theme. Inline styles may carry data properties like `style="--value:68%"`, but not layout.

## Content

| Construct | How it looks |
|---|---|
| `.bullets`, `.plain-list` | A number in its own column for spoken order; a circle for equal items. Rows share a baseline grid and a thin top line, density via `--row-pad` |
| `.scoreboard` | Labeled values. An item number is not a metric |
| `.data-table` | Shared headers, the same row structure, exact values. Numbers and their headers align the same way |
| `.steps` | Numbered actions without a time axis |
| `.timeline` | Dated events or periods; `.is-current` means the real current state, not a position in order |
| `.flow` | Equal rectangular nodes with one centered line; a link fills the gap and its arrowhead touches the node edge |
| `.s-visual-compare` | Two comparable images, captions on top, a shared scale |
| `.wipe` | A wipe: `.wipe-before` and `.wipe-after` in one area, `.wipe-label` on top, the edge moves to `--wipe` |
| `.code` | Readable source with the argument's lines highlighted |
| `.code-run` | A typed command: `data-run-commands` lines are typed, output appears line by line |
| `.bento` | `.bento-row` rows of `.bento-tile` tiles with width `--span`, one `.is-accent` per the claim |
| `.iterations` | The current `.iteration.is-current` large, earlier `.iteration` items beside it |
| `.shot--scroll` | A fixed `.shot-head` and a scrolling `.shot-body` |

`.flow-node--accent` gives a permanent fill, not a moving focus. The conditions for accents and reveals are in the [selection rules](selection.md). Do not assign them because an example looks that way.
