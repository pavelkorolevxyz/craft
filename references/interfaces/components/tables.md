# Tables

`data-table.html` creates a `.data-table` inside `.table-scroll`. Text and its header align left. The last column aligns right on its own. Mark a numeric column in the middle with `.data-table__num` on the `th` and every `td`, for right alignment and tabular figures. State units and use the same precision. Add a `caption` if the section heading does not explain the table's purpose. `.total` marks the totals row.

A numeric matrix with short cells keeps its columns and scrolls horizontally on a narrow screen. `.table-scroll` fades the edge that hides more columns by itself, so add no shadows of your own. A text table unfolds into records:

```html
<table class="data-table data-table--records">
  <thead><tr><th>Check</th><th>State</th></tr></thead>
  <tbody><tr><td data-label="Check">Login</td><td data-label="State">Pending</td></tr></tbody>
</table>
```

Each `data-label` repeats its `th`. The main field stays a line, the rest become labeled pairs. Do not drop fields silently, and do not repeat them in both the record and a summary next to it. You can move secondary data into details.

Rows are static by default. Selecting a record needs `data-interactive`, `tabindex="0"`, `aria-selected` and working mouse and keyboard handlers. The theme already styles hover and selection.

For sorting, use `<th aria-sort="ascending">` with a `.data-table__sort` button and an inline SVG arrow. Only the current column has `aria-sort`. Reserve room for the arrow in every sortable header. `.data-table--sticky` pins the header, and print returns it to the flow. A details button has `aria-expanded` and `aria-controls`, and the details live in the adjacent `.data-table__detail`.
