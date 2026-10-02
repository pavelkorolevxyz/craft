# Charts on slides

Read only for a numeric visual. Shared scale and roles are in the [visual language](design-language.md).

## Choice and labels

| Data | Construct | Limit |
|---|---|---|
| Categories | `.bar-chart` | Horizontal bars fit long names. Label the value on each row |
| A value by period | `.column-chart` | Periods run in time order |
| Composition of a period | `.column-chart--stacked` | Parts add up to each period's total |
| Two series by period | `.column-chart--grouped` | Two columns per period on one scale |
| Continuous change | `.line-chart` | One main series and at most one background series; labels at line ends |
| Shares of one whole | `.pie-chart` | Two to four parts; not for change over time or comparing independent categories |
| Two measurements by category | `.range-chart` | Both values labeled on one row; the mark at the "after" end shows direction without color |

A map, a network, a distribution or a domain-specific signal shape needs a local visual if a standard chart loses its meaning. Keep Craft's type, palette, scales, labels and accessible text description.

- State the conclusion once, in the title or a side block, not both. Use a side block for a caveat. Otherwise give the chart the full width.
- When the conclusion is revealed, the labeled chart is already visible in the first frame. If the title states the conclusion, show everything at once.
- A chart has an accessible text description of the data and the conclusion, a source, a period and a unit.
- The accent marks the data that proves the claim. The geometry follows the values, not the shape you want.
- A chart starts at the slide's left margin. Columns and lines have both axes labeled. `.chart-y-axis` on the left has five ticks from zero to the top of the plot. An exact number at a chosen point adds to the scale, it does not replace it.
- The plot has two `--line-strong` axes and a quiet `--line` grid at every scale tick. Each tick label sits on its line. The theme draws the axes and grid. Do not add them to the markup or animate them. A standing chart takes the full width of the plot.
- Fill data in focus with `--accent-mark`, its label with `--accent`.

## Parts and color

- Two to four parts use the roles `--chart-series-1` to `--chart-series-4`: blue, amber, green, quiet neutral. Red stays the semantic accent. Merge small parts into an `.is-rest` remainder, which is neutral in any position.
- `.chart-keys` follows the order of parts in HTML. The series sets the color. A key has a swatch, a name and a value. Do not put a label inside a thin slice.
- A donut has its keys on the right with values. Columns have them in a row on top. The gap between keys and chart is smaller than between keys and title.
- In `.range-chart`, draw the arrow between measurements with an empty `<i>` inside `<strong>`, not a font glyph. A glyph shifts against tabular digits.

## Motion and compatibility

`data-reveal` starts motion. `deck.js` sets it on a forward reveal. A rule like `[data-reveal] .block { animation }` stays silent on the first frame, on going back and in print. For numbers use the [counter](motion.md), not a separate script.

Columns grow from zero. Donut slices draw at the same time, each from its own start to its own end, not one after another around the circle. Keys, the range chart and axes do not move. Do not animate text appearing.

Test SVG in a second browser engine. Compute arc length in `viewBox` units and use `calc(var(--value) * 1px ...)` in CSS. Set a slice's start with a rotation. The second engine may ignore a unitless `calc()` in SVG geometry and draw a full ring instead of a slice. Do not replace the rotation with `stroke-dashoffset`.
