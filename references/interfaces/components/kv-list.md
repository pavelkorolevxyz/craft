# Key-value pairs

Use `kv-list.html` when the fields of one object are read in order, not compared across records.

```html
<div class="kv-block">
  <h3 class="kv-block__title">Settings</h3>
  <dl class="kv-list kv-list--lined"><dt>Version</dt><dd>2.4.1</dd><dt>Environment</dt><dd>Staging</dd></dl>
</div>
```

`.kv-list--lined` adds dividers. On a narrow screen a pair wraps onto two lines and stays together.
