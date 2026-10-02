# Interface system levels

Craft maps composition with Foundation and the five levels of atomic design. A level says what an element owns.

## Foundation

Foundation holds the base tokens: color roles, the type scale and spacing. Components read these values, but Foundation never goes on a page as an interface of its own. Layout patterns and CSS utilities belong in the composition guide, not in separate Foundation entries.

The type scale is Foundation. The icon component stays an atom. It has public markup, a size and accessibility rules.

## Atom

An atom has one role and does not lay out its neighbors. It has its own sizes, variants and states.

Examples: button, text input, checkbox, status, icon. If an element needs a label, a hint and an error message as a fixed group, it is the `field` molecule.

## Molecule

A molecule joins a few atoms for one local task. You can move it between sections without changing its internal contract.

Examples: labeled field, tabs, pagination, notice, section navigation, empty state. A molecule does not own a large page area and does not run several neighboring groups.

## Organism

An organism takes up its own interface area and lays out what it contains. It groups atoms and molecules around one part of the task.

Examples: filter bar, data table, workspace header, chart, key-value list, dialog. An organism can have its own fragment in `assets/interfaces/fragments/`.

## Template

A template sets page geometry without subject content. Craft has no required layout per product type. It uses three modes instead:

- document, for reading top to bottom;
- data view, for tables, charts and comparisons;
- workspace, for a main area with related details.

One page can mix modes when the task calls for it. The rules for choosing are in [page geometry](layout.md).

## Page

A page fills a template with real data and tests the levels together. Catalog recipes show what goes in and in what order. They do not become new general-purpose components.

## How to pick a level

1. If the thing stores a base value that components use, it is Foundation.
2. Remove the content and look at what the element still owns.
3. One role with its own states is an atom.
4. A short fixed group for one operation is a molecule.
5. An element that runs its own area and lays out several groups is an organism.
6. If it defines only page geometry, it is a template.

Do not raise the level because of how many tags are nested. A native `select` is complex inside the browser, but in the system it stays an atom. An empty state stays a molecule while it is a heading, a note and an action. The organism that contains it owns the whole area.

## Catalog registry

A component section gets `data-atomic-level="atom|molecule|organism"`, and a shared Foundation rule gets `data-foundation-doc`. Foundation, Atoms, Molecules, Organisms, Templates and Pages each have their own catalog page. The home page stays the map of the whole system.
