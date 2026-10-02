# Long document navigation

`section-nav.html` loads `section-nav.js`. The link container has `data-section-nav`, and links point to section `id`s. The script updates `aria-current` on scroll and keeps the active link visible in a long strip.

By default the links form a column with a guide line on the edge facing the text. `.section-nav--row` makes a horizontal strip. On mobile the column turns into a strip on its own. The 2 px marker gets its position from `--nav-marker-x`, `--nav-marker-w`, `--nav-marker-y`, `--nav-marker-h`. Without the script, the current link keeps a static mark. Print hides the navigation.

The list has no fill of its own. When the navigation is a sidebar, fill the whole sidebar column, or nothing, and keep the links paintless inside it.
