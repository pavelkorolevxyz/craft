# Process steps

```html
<ol class="steps" aria-label="Release progress">
  <li data-state="done"><span class="steps__index">01</span><span class="steps__title">Build</span></li>
  <li data-state="current"><span class="steps__index">02</span><span class="steps__title">Review</span></li>
  <li><span class="steps__index">03</span><span class="steps__title">Publish</span></li>
</ol>
```

Steps show a finite sequence with a known end. The current step gets a fill and an accent number. A done step differs from an upcoming one by label brightness. On a narrow screen the row turns into a column.

For an open-ended stream of events, use a [timeline](progress.md).

Fragment: `steps.html`.
