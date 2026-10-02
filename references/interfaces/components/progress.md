# Progress and events

Progress shows how far one operation has gone. `.bar` compares values.

```html
<div class="progress">
  <div class="progress__head"><span>Processed</span><strong>420 of 900</strong></div>
  <div class="progress__track"><span class="progress__fill" style="--value:47%"></span></div>
</div>
```

If the share is unknown, `.progress--indeterminate` only says that work is happening. Keep text next to it, because the bar stops under reduced motion.

`timeline.html` shows events in time order with one time format. `.timeline__mark` takes its own column. `.timeline__time`, `.timeline__title` and the note align on a shared left edge in the second column. The line joins the dots and does not break on a long entry. For a finite sequence of actions, use [steps](steps.md).
