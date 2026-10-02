# Pagination

```html
<nav class="pagination" aria-label="Queue pages">
  <a class="pagination__page" href="#page-1" aria-label="Previous page">
    <svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m15 18-6-6 6-6"/></svg>
  </a>
  <a class="pagination__page" href="#page-1">1</a>
  <a class="pagination__page" href="#page-2" aria-current="page">2</a>
  <a class="pagination__page" href="#page-3">3</a>
  <span class="pagination__gap" aria-hidden="true">…</span>
  <a class="pagination__page" href="#page-9">9</a>
  <a class="pagination__page" href="#page-3" aria-label="Next page">
    <svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 18 6-6-6-6"/></svg>
  </a>
</nav>
```

Equal-width cells sit centered in the bar. Page numbers are muted at rest and take color only on hover, so the row of digits does not compete with the content being paged. The current page gets an `--accent-fill` fill and stops being a link.

A chevron shows direction. The icon sits in the link markup, not in the sprite, so the fragment works on a page without the icon set. The link gets an `aria-label`, and the icon itself is hidden from screen readers.

Shorten a long set with `.pagination__gap` and an ellipsis, not with a small font. Show the first pages, the pages next to the current one and the last page. Mark an unavailable direction with `aria-disabled` and keep it in place, because a vanishing cell shifts its neighbors.

Skip a counter like "2 of 8" under the numbers. It repeats what the row already shows. If the set size matters to the user, put it in the table header next to the filters, not under the page buttons.

A small set fits on one page and needs no pagination.

Fragment: `pagination.html`.
