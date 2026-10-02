# Filter bar

```html
<div class="filter-bar" role="group" aria-label="Queue filters">
  <label class="field__label" for="stream">Stream</label>
  <span class="select-control">
    <select id="stream"><option>All</option></select>
    <svg class="select-control__icon" viewBox="0 0 12 8" aria-hidden="true"><path d="m1 1 5 5 5-5"/></svg>
  </span>
  <p class="filter-bar__count" role="status">18 of 84 shown</p>
</div>
```

The bar sits right above the area it changes and ends with the count of matching records. Changing a filter updates the data at once, so there is no Apply button. If the request is slow, the area gets `aria-busy` and a placeholder.

Do not turn the bar into a global toolbar. Page-wide controls live in the workspace header.

Fragment: `filter-bar.html`.
