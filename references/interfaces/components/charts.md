# Charts and bars

Pick the form by the data: a line for change and events, bars for categories, a heatmap for distribution, a donut for parts of a whole. HTML, CSS or SVG is enough for a small dataset. A chart has a title, labels, units and an accessible text summary.

- Bars start at zero. If the range starts elsewhere, say so. Repeat the value as text, and let a block element set the bar length.
- Series follow the roles `--data-red`, `--data-neutral`, `--data-blue`, `--data-amber`, `--data-green`. If red already means a breached threshold, start with neutral. Use at most five series.
- A donut has at most five slices, with percentages labeled next to it. A heatmap explains which way brightness goes and does not replace exact numbers needed for a decision.
- A line is 1.5 px thick and solid. In SVG use `vector-effect="non-scaling-stroke"`. With `preserveAspectRatio="none"`, move labels into HTML so the text does not stretch.
- `.series-key` with `style="--swatch: var(--data-blue)"` ties a name to its series.
- An interactive chart gets focus, arrow-key control and a live region with the value. A static chart does not pretend to be interactive.
- Color a change only when its direction has one clear meaning. Traffic growth alone is neither good nor bad.

```html
<div class="bar-list" aria-label="Load">
  <div class="bar"><div class="bar__head"><span>Main stream</span><strong>82%</strong></div>
    <div class="bar__track"><div class="bar__fill" style="--value:82%"></div></div>
  </div>
</div>
```
