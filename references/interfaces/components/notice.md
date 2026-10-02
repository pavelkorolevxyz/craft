# In-page notice

```html
<aside class="notice notice--warn" role="status">
  <span class="notice__mark" aria-hidden="true"></span>
  <div>
    <strong class="notice__title">Yesterday's data is incomplete</strong>
    <p>Three of twelve sources have not sent their export yet.</p>
  </div>
</aside>
```

Place a notice next to the content it concerns, not above the whole page. A square mark sets the tone. `.notice--ok` confirms a result, `.notice--warn` names a condition worth knowing, `.notice--error` reports a failed action. Without a modifier the notice is neutral.

Only an error gets a signal background. The theme's `--raise` is the usual notice background. Text stays neutral in every tone, and the title and explanation carry the meaning. The `.notice--action` variant shows one next step and replaces a separate accent callout.

If a notice has an action, put the buttons in `.notice__actions`. They sit under the text and do not compete with the mark.

Announce an error the user learns about from their own action with `role="alert"`, a background change with `role="status"`. Do not re-announce what is already on screen.

Fragment: `notice.html`.
