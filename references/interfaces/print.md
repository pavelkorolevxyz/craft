# Printing an interface

- Hide search, filters, the theme toggle, copy buttons and other controls that do nothing on paper. Keep the current data, labels and snapshot time.
- Unfold the work grid into one flow. For a wide table, pick an orientation or move secondary fields into labeled details.
- A long `.section` may run onto the next sheet. Use `break-inside: avoid` only for unsplittable rows, quotes, code, charts and short callouts. A heading stays with its first paragraph, `thead` repeats.
- The print theme is light with dark code roles. Set `data-print="true"` on `html` before redrawing graphics for print.
- Join digit groups, and a value with its unit, with a non-breaking space. `@page` has `8mm 14mm` margins. This usually hides Chromium's default headers and footers, but the user can turn them back on.

- Backgrounds print as on screen, via the theme's `print-color-adjust: exact`. Keep it: without backgrounds, white labels on fills, checkbox marks and grid lines vanish.
- Tab panels print in sequence, each with its tab's label. Disclosures print open, scrolling tables in full.
- Do not split a grid drawn with line-colored gaps across sheets, or the rest of the sheet fills with that color. Give it `break-inside: avoid` or unfold it for print.
