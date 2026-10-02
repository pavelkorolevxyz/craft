# Components

Classes live in `assets/interfaces/theme.css`, ready markup in `assets/interfaces/fragments/`. `compose.py` adds a fragment, and its id matches the file name. `--fragment <id> --list-placeholders` prints its contract. Use the catalog `catalog/interfaces/index.html` for a live example and the API of one component, not as a page to copy.

Open only the rows your page has. Add navigation when the page does not fit on screen or splits into parts. Feedback interrupts work only when the user cannot go on without answering.

| The page has | Fragment | Reference |
|---|---|---|
| Key figures above the content | `metric-strip` | [Metrics](components/metrics.md) |
| A table of records or values | `data-table` | [Tables](components/tables.md) |
| Category, version, record status | | [Tags and statuses](components/tags.md) |
| Fields of one object | `kv-list` | [Key-value pairs](components/kv-list.md) |
| Chart, bars, shares | | [Charts](components/charts.md) |
| Progress, event log | `timeline` | [Progress and events](components/progress.md) |
| Source code | `code-block` | [Code](components/code.md) |
| Input, form, validation | `field` | [Field and form](components/field.md) |
| Checkbox, switch, slider, pick from options | | [Choosing a value](components/choice.md) |
| Buttons and actions | | [Buttons](components/buttons.md) |
| Filters above data | `filter-bar` | [Filter bar](components/filter-bar.md) |
| Peer views, page sections | `tabs` | [Tabs](components/tabs.md) |
| A list and details of the selected record | `split-workspace` | [Master-detail](components/master-detail.md) |
| A long set split into pages | `pagination` | [Pagination](components/pagination.md) |
| Position in a nested hierarchy | `breadcrumbs` | [Breadcrumbs](components/breadcrumbs.md) |
| A finite sequence of stages | `steps` | [Steps](components/steps.md) |
| A long document with sections | `section-nav` | [Document navigation](components/section-nav.md) |
| Repeated keyboard actions | | [Keyboard shortcuts](components/shortcuts.md) |
| A message inside the page | `notice` | [Notice](components/notice.md) |
| Waiting for data | | [Loading](components/loading.md) |
| Hidden details | | [Disclosure](components/disclosure.md) |
| Confirmation or input over the page | `dialog` | [Dialog](components/dialog.md) |
| No results or a load error | `empty-state` | [Empty state](components/empty-state.md) |
| Bounded document blocks and bands | | [Document building blocks](components/document.md) |
| Pictograms | | [Icons](components/icons.md) |

The [classification rules](atomic-design.md) describe the atomic levels. You need them when you extend the catalog, not when you build a page.
