# Field and form

The `field.html` fragment builds a whole field, and theme primitives handle its states. Add controls only when the user really changes data or settings. A report does fine without a form.

## Field

```html
<div class="field">
  <label class="field__label" for="limit">Alert threshold</label>
  <input id="limit" name="limit" type="number" value="120"
    aria-describedby="limit-hint">
  <p class="field__hint" id="limit-hint">Value in milliseconds.</p>
  <p class="field__error" id="limit-error"></p>
</div>
```

The label sits above the control and links to it with `for`. The hint explains the rule up front and lives in `aria-describedby`. An empty error paragraph hides itself, so the markup is the same before and after validation.

An error appears next to the control that caused it and says what to do. On error, the field gets `aria-invalid="true"`, and `aria-describedby` gains the message id:

```html
<input id="limit" type="number" value="-5" aria-invalid="true"
  aria-describedby="limit-hint limit-error">
<p class="field__error" id="limit-error">The threshold cannot be below zero.</p>
```

The error message uses the text role for color, and the field border gets the strong mark. Do not rely on color alone. Without text, the error does not read.

## Field groups

`.form-grid` lays fields out in columns to fit the width and stacks them into one on a narrow screen. `.form-actions` keeps the buttons at the end of the form. `.field-set` groups related checkboxes or radios, with the caption in `legend`.

```html
<fieldset class="field-set">
  <legend>What to show</legend>
  <div class="check-group">
    <label class="check"><input type="checkbox" checked><span>Errors</span></label>
    <label class="check"><input type="checkbox"><span>Warnings</span></label>
  </div>
</fieldset>
```

## States

Every control shows hover, focus, pressed and disabled states. On a rectangular field, the state changes its own border. Hover raises it to muted text color. Focus paints it with the mark color and adds an inner line of the same color. The field gets no second border outside. A disabled field is the exception. Its border stays normal, and the quiet `--fill-quiet` fill shows the state, while the value, label and hint fade with it. A darker border does not work here, since the disabled field would look heavier than an active one. Small controls, such as checkbox, radio, switch and slider, use the page's shared focus outline, because there is no room to draw a line inside them. Explain a disabled state with text next to it. A muted color alone does not tell the user why.

Do not disable the submit button before the user has tried to submit. A silently disabled button does not say what is missing.

## Client-side validation

Validate on submit or when focus leaves a field, not on every keystroke. An error message while the user is still typing gets in the way.

After a failed check, move focus to the first field with an error. If there are several errors, add a `.notice` above the form with links to the fields.
