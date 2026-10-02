# Choosing a value

## Checkbox, radio, switch

A checkbox marks independent values, a radio picks one of several, a switch turns on a mode and applies it at once. If the choice takes effect only after confirmation, use a checkbox, not a switch.

```html
<label class="switch">
  <input type="checkbox" role="switch" checked>
  <span>Auto-refresh</span>
</label>
```

For a partly selected group, set `indeterminate` on the parent checkbox from a local script. Markup cannot express this state.

The theme draws the geometry and states. Keep native elements and their keyboard behavior. Do not replace them with a `div` imitation.

## Slider

```html
<label class="field__label" for="window">Averaging window</label>
<input class="range" id="window" type="range" min="1" max="60" value="15"
  aria-describedby="window-value">
<output class="muted" id="window-value">15 minutes</output>
```

A slider suits an approximate value with a visible range. Exact numbers go into a field. Keep the current value visible next to it and update it with the slider.

The track is one line without ticks. The round thumb is set off by a gap in the background color. Hover changes only the thumb's fill and outline, not the track or sizes. The theme defines these states.

## Picking from a list

For up to five short options use the native radio group `.segmented`. For more, use `select` in `.select-control`.

```html
<div class="segmented" role="radiogroup" aria-label="State">
  <label><input type="radio" name="state" value="all" checked><span>All</span></label>
  <label><input type="radio" name="state" value="error"><span>Errors</span></label>
</div>
<label for="period">Period</label>
<span class="select-control">
  <select id="period"><option>7 days</option></select>
  <svg class="select-control__icon" viewBox="0 0 12 8" aria-hidden="true"><path d="m1 1 5 5 5-5"/></svg>
</span>
```

Native fields keep focus and arrow keys. In a `select`, the SVG replaces the system arrow, and the theme sets its color.
