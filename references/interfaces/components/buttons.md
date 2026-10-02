# Buttons

`.button--primary` marks the main action on the screen, a plain `.button` the rest, `.button--quiet` a tertiary action next to the content. One screen gets one main action.

While a request runs, the button gets `aria-busy="true"`. If the label changes, both texts share one cell:

```html
<button class="button button--stable" type="button" aria-pressed="false">
  <span class="button__label button__label--rest">Pause</span>
  <span class="button__label button__label--pressed">Resume</span>
</button>
```

The theme hides the inactive text with `visibility`, so both count toward the size. Reserve space for a changing status next to it the same way.
