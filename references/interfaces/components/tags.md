# Tags and statuses

| Element | Purpose |
|---|---|
| `.tag`, `.tag-list` | Category, team, version. A filled `.tag--accent` highlights one kind of tag |
| `.tag--ok`, `.tag--warn`, `.tag--error` | Status column: border and label in one color, shared height |
| `.status`, `.status--ok`, `.status--warn`, `.status--error` | State in text: a colored dot and a neutral label |
| `.surface-tint`, `.surface-tint--error` | Quiet row highlight with the translucent `--accent-tint` or `--error-tint` |

```html
<span class="status status--error">Error</span>
<span class="tag">Pending</span>
```

Expected and in-between states are neutral. Color is for a state that needs a decision. Set a custom tone with a local `--status`, not a new dot or a data series color. Do not combine check status and review status in one column. The header names exactly what the cells hold.
