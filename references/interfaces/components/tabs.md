# Tabs

```html
<div class="tabs" data-tabs>
  <div class="tablist" role="tablist" aria-label="Queue views">
    <button role="tab" type="button" id="tab-open" aria-controls="panel-open"
      aria-selected="true">Open</button>
    <button role="tab" type="button" id="tab-done" aria-controls="panel-done"
      aria-selected="false">Closed</button>
  </div>
  <div role="tabpanel" id="panel-open" aria-labelledby="tab-open" tabindex="0">...</div>
  <div role="tabpanel" id="panel-done" aria-labelledby="tab-done" tabindex="0" hidden>...</div>
</div>
```

`tabs.js` switches tabs on click, arrow keys, `Home` and `End`, and hides inactive panels.

Tabs fit peer views of one dataset. They do not solve sequential steps, nested sections or side-by-side comparison. Keep 2 to 5 tabs with short labels, and do not hide behind them what the user needs to see at once.

The strip has no fill or rule of its own and takes the color of the surface under it; only the selected tab has a mark. To set tabs apart, place them in a container that is already filled, such as the header or a sidebar, and never paint the strip by itself. Put page-wide section tabs right after `.workspace-head`, with `.tabs--page`: the strip continues the header's fill edge to edge, and the header's bottom rule moves under it. Tabs have no outer margins, and the panel sets the spacing.

Print hides the tab strip and prints all content in sequence.
