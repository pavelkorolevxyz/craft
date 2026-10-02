# Motion and numbers

## Motion

The deck sets motion with one policy, `<html data-motion>`:

| Mode | Behavior |
|---|---|
| `show` (set by `scaffold.py`) | Authored animations always play, for the talk |
| `auto` | Follows the viewer's reduced-motion setting |
| `static` | Final frames without motion, for reading and export |

`?motion=`, the `M` key and the panel button switch the mode. The choice is not saved. `deck.js` sets `:root[data-motion-state="on|off"]`. When `off` and in print, `base.css` finishes animations instantly. Do not write your own `prefers-reduced-motion` in deck CSS.

Motion belongs to the forward step: `[data-reveal] .block { animation }` sets only the start frame with `from`. The base state is the final frame, so static mode, print and going back show the content, not an empty start. An animation does not change pages. Mark an element that must leave after entering with `data-exit="intended"`.

## Numbers

Keep the final value in text. `data-count` counts up from zero only on a forward reveal:

```html
<div class="frag"><p class="type-metric" data-count data-count-duration="1200">12,400</p></div>
```

Separate thousands with a comma from five digits on. A plain space fails. The mechanics keep the number on one line and reserve the width of the final value. Count values only, not step numbers or scale ticks. In a table, mark the number inside the cell: `<td class="num"><span data-count>1,240</span></td>`.
