# Extending Craft

A new format can be a one-off composition inside an existing format or a full supported format. The two take very different amounts of work.

## One-off composition

Use an existing format if its viewing conditions, interaction model and export method still hold. Create a normal project with `scaffold.py`, put local markup and CSS next to the content, and check it with `check_project.py`.

A one-off composition:

- does not go into `scripts/craft.json`;
- gets no catalog, starter or theme of its own;
- does not extend `scaffold.py`, the release archives or the CI matrix;
- may use local classes that do not become part of Craft's public API.

Examples are a standalone analytics report inside `interface` or an unusual slide type inside `slides`. If the same solution shows up in several unrelated pieces, first extract a fragment of the existing format. Add a new format only when the format contract differs.

## New supported format

Add a format only if the existing ones do not fit the viewing conditions or interaction model, and the new use case will repeat.

### Define the conditions

Write down the viewer, distance and lighting, fixed or responsive sizes, interaction model, duration, requirements for offline use, print and video, the minimum font size and the key information. If the conditions match an existing format, extend that format.

### Format contract

Create:

```text
assets/<surface>/
├── starter/index.html
├── fragments/
├── theme.css
└── mechanics, if needed

references/<surface>/
├── design-language.md
└── authoring.md or components.md, if needed
```

Then:

1. Load `assets/shared/tokens.css` before the format's styles.
2. Map the `--craft-*` tokens to local semantic roles.
3. Keep sizes, components and mechanics inside the format.
4. Add a route to `references/surfaces.md`.
5. Add the format to `scripts/scaffold.py` and cover it in `tests/test_scaffold.py`.
6. Make a starter template without invented data.
7. Add neutral docs in `catalog/<surface>/`: an index, component pages with live examples and a separate full test sheet with no subject-matter page.
8. Register components and categories in `scripts/craft.json`. The index must link to every component. The test sheet must show every registered fragment, state and mechanic.
9. Register the docs and test sheet paths in `scripts/craft.json`. Point browser and visual tests at the test sheet so the number of baselines does not grow with the docs.
10. Check `file://`, keyboard control, overflow and the required export method.

### Fragment contract

Register every file in `assets/<surface>/fragments/` in `scripts/craft.json`. An entry has:

- an `id`, unique within the format;
- a relative `path`;
- a short `purpose` that describes the geometry and role without a subject-matter scenario;
- a `placeholders` map with the type of each placeholder;
- a list of local `dependencies`.

Placeholder types:

- `text`, escaped text;
- `html`, semantic markup passed explicitly;
- `id`, an element id;
- `number`, a number for a counter or a CSS parameter;
- `token`, one safe class or mode name.

The format sets `fragmentTarget`, the selector of the container that receives fragments. A slide fragment's `id` matches its `data-slide-layout`. Placeholder names in the registry must match the file's placeholders exactly. `scripts/check.py` checks this.

Do not add a one-off composition's CSS to the shared core. `shared` holds identity decisions, each format holds its own decisions, and generated projects hold the composition of their content.

## Fixing mechanics

A shared fix gets a negative fixture in `tests/test_probe.py`: the old broken example fails, the fixed one passes. Loosen a check only if it blocked a valid case, never to get a green run. Engine tests do not depend on the text or numbers of a specific talk.
