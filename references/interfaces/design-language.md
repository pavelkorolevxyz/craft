# Interface visual language

Pick page geometry in [geometry](layout.md), building blocks in the [component index](components.md), print rules in [print](print.md). Shared tokens and bans are in [identity](../identity.md), the review order in the [workflow](../workflow.md). This file covers only the interface format.

## Sizes and type

- A workspace takes the full width and at least the window height. Do not cap a dashboard or tool with an outer `max-width`. A text column stays within 65 to 75 characters.
- The type scale is fixed: meta text 12 px, body 14 px, lede 16 px, local heading 18 px, section 24 px, page title and metric 32 px. On mobile a section is 22 px and the page title 28 px. Do not use `clamp()` or viewport units for font size.
- Headings use weight 600 to 700. A page has one `h1`, standalone sections get `h2`, nested blocks `h3`. The class sets the look, not the heading level.
- The spacing scale `--space-1` to `--space-7` is 4, 8, 12, 16, 20, 24, 32 px. Font, line and icon sizes are not on it. Inside a group use 8 to 16 px, between groups 24 to 32 px. Do not repeat one `.stack` at every level.
- A text control is at least 44 px tall, an icon button at least 40×40 px. An icon button gets an `aria-label`, a tooltip and a visible focus. Keep the text on a rare or irreversible action.

## Color and themes

Values come from `assets/shared/tokens.css`. `assets/interfaces/theme.css` already defines the interface roles and states. Do not copy numeric colors from the catalog into local styles.

| Role | Use |
|---|---|
| `--accent`, `--accent-mark`, `--accent-fill`, `--accent-tint` | Text, strong mark, fill under white text, quiet signal background |
| `--ok`, `--warn`, `--error` | States that need a decision. Expected and in-between states stay neutral |
| `--data-red`, `--data-neutral`, `--data-blue`, `--data-amber`, `--data-green` | Chart series, not states |
| `--fill-quiet` | Inline code chip and disabled field |
| `--raise`, `--raise-solid` | Ready background for a nested component, translucent and opaque |

The current theme uses `--raise` behind nested fields, buttons and panels. Use `--raise-solid` where the line underneath must not show through. This is a theme-wide experiment with nesting depth. Do not cancel it with a local `background: transparent`, and do not pick a separate gray for each panel. Changes to the experiment go into the theme itself, not into a new page.

The mark gets the signal color, the text next to it stays neutral. The exception is `.tag`, where the border and label form one colored sign.

On `--accent-fill`, swap text and quiet roles for `--craft-on-accent-*`. On the translucent `--accent-tint` the usual roles stay. A new local accent composition uses the same roles, not new shades.

Load `theme.js` in `head` before the CSS. It picks the theme from `?theme=`, the saved value or `prefers-color-scheme`. It saves an explicit choice; without one the page follows the system. Redraw graphics that read `getComputedStyle` on `craft-themechange`. Both themes and print have their own data roles, so do not hard-code a screen color in a script.

## Control states

| State | How |
|---|---|
| Hover | `--accent` text, no fill, no frame color, no size change. An accent link strengthens to `--accent-mark` |
| Selected tab, section, row with details | 2 px mark on the side facing the content, accent label |
| Selected table row or current step | `--accent-tint` when the element has no single edge facing the content |
| Selected segment or pagination page | `--accent-fill` under a white label |
| Focus | Visible outline, not a stand-in for selection |
| Disabled | Muted control without hover and a text reason next to it |

Static rows, panels and statuses get no hover. Express state with native `checked`, `aria-pressed`, `aria-selected`, `aria-current` or `aria-sort`, not with a separate model in classes.

Hover exceptions: the filled primary button, the switch and the slider thumb change their fill, and a rectangular field strengthens its border. Border width never changes. Checkbox, radio, switch and slider keep their familiar shapes. The no-rounding rule applies to panels.

Reserve space for the longest changing text. A button that redraws data lives outside the area it replaces. Use `.button--stable` for two labels. Each component's rules say whether keyboard focus stays or moves. A row selection handler must not create a second, independent cursor.

Arrows and sort icons are inline SVG, not text characters. The markup is in the matching component reference.
