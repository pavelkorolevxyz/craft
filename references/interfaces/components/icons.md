# Icons

The line icon set lives as an inline sprite at the start of `body`. Copy only the symbols you use. Use them as `<svg class="icon" aria-hidden="true"><use href="#icon-…"/></svg>`, always next to an accessible name, since an icon does not replace text. Geometry: `viewBox` 24×24, `currentColor` stroke 1.7 px, round caps.

Available symbols: `icon-sun`, `icon-moon`, `icon-chevron`, `icon-down` (only inside `.select-control`), `icon-check`, `icon-copy`, `icon-search`, `icon-x`, `icon-plus`, `icon-filter`, `icon-edit`, `icon-trash`, `icon-download`, `icon-external`, `icon-arrow-right`, `icon-refresh`, `icon-info`, `icon-warn`, `icon-more`. Each symbol's markup is in the sprite in `catalog/interfaces/atoms.html`, with a live example in its "Icon" section. Do not draw a new icon if an existing one covers the meaning. Draw a missing one in the same geometry.

A project with `web` delivery may load Lucide from a CDN on the validator's allowlist. For a couple of icons, the local sprite is shorter and works offline.
