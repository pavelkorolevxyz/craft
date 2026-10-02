# Craft identity

Shared rules for every format. The chosen format sets sizes and interaction.

## Visual language

- Neutral light and dark surfaces, a red brand accent, rectangular panels and 1 px lines.
- Geologica for headings and key numbers, Onest for body text and controls, a monospace font only for code.
- Red marks an action, a selection, a state, a signal, a data link or the main conclusion. Do not alternate red and neutral sections, slides or rows for rhythm.
- Saturated extra colors mark data or statuses. They do not decorate. Never let color carry meaning alone.
- The mark gets the signal color. The text next to it stays neutral. Each format lists its exceptions in its visual language.
- On an accent fill, use `--craft-on-accent-*`, not a stock gray. Transparent quiet roles keep the tone of the surface below.
- A border has four sides. A divider has one. Never draw a shared edge twice.
- Do not add decorative gradients, glow, glass, shadows, rounded panels, repeated cards with icons or terminal styling. The theme already defines the technical layers of background paint. Do not rewrite them to meet this rule.
- Do not set labels in caps with letter spacing.
- Motion explains: a value growing, parts appearing, an object's path, a command being typed. Do not animate decorative loops or page transitions. Motion follows the format's policy: `data-motion` on slides, `prefers-reduced-motion` in interfaces.

## Tokens

Values live in `assets/shared/tokens.css`. Use the roles. Do not copy color values into local CSS.

| Purpose | Shared roles |
|---|---|
| Surfaces | `--craft-bg`, `--craft-surface`, `--craft-surface-muted`, `--craft-sunken` |
| Text and lines | `--craft-text`, `--craft-text-body`, `--craft-muted`, `--craft-line`, `--craft-line-strong` |
| Accent | `--craft-accent` for text, `--craft-accent-mark` for a mark, `--craft-accent-fill` for a fill, `--craft-accent-tint` for a quiet background |
| On accent | `--craft-on-accent`, `--craft-on-accent-muted`, `--craft-on-accent-line`, `--craft-on-accent-disabled` |
| States | `--craft-ok`, `--craft-warn`, `--craft-error` |
| Data series | `--craft-data-red`, `--craft-data-neutral`, `--craft-data-blue`, `--craft-data-amber`, `--craft-data-green` |
| Fonts | `--craft-font-display`, `--craft-font-text`, `--craft-font-mono` |

Each format's theme maps `--craft-*` to local roles. A shared color is no reason to move interface sizes onto a slide or components between formats.
