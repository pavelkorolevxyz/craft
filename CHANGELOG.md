# Changelog

## 1.0.0

The first release.

### Skill

- Craft is in English: the skill, references, catalogs, script messages and comments. `scaffold.py` creates projects with `lang="en"` by default. `references/russian.md` covers Russian material: fixed slide words, control labels, numbers and typography.
- References are split by topic, one file per component, and `SKILL.md` routes to them by what the material contains. `check.py` limits each reading route to 32,000 characters and each file to 6,500.
- `references/slides/narrative.md` describes how a talk is built: cover, plan, numbered chapters, episodes, takeaways and the end slide.
- `scaffold.py --author` starts a talk with an author, and the `cover` fragment opens it.

### Slides

- The end slide puts the author bottom left and the contact as a QR code bottom right.
- Motion where a step adds something: diagram arrows draw toward their node, the time axis reaches a new event, step rules and statement underlines draw, big headings and quotes rise line by line, a chapter change passes through an accent curtain, and lanes on the cover and dividers drift.
- The title over full-slide media sits top left and leaves after three seconds; `.s-shot--title-center` hangs it in the middle.
- A screen recording uses the `screenshot` layout like an image.
- `deck.js` and `theme.js` read their labels from data attributes, so a deck or page in another language can override them.

### Interface

- Hover recolors labels only. Frames stay neutral.
- Tab strips and section navigation have no fill of their own and no numbers. They take the color of the container they sit in.
- A compact workspace header without a lede is a single bar, on a phone too.
- The selected segment fills to its edges.
- A `.scroll-region` hands the wheel to the page when it has nothing to scroll.
- The templates catalog page draws each template's geometry on a wide screen and a phone.

### Checks and tooling

- `check_project.py` has three levels: `--static-only`, a default render pass for every edit, and `--full` before handoff.
- `release.py --check static|render|full` (default `full`) picks how far a release is checked.
- One Chromium session per check. The deck probe runs named passes and plays motion ten times faster.
- `make check`, `smoke`, `test` (parallel) and `visual-test` are the stages. A full local cycle takes about a minute.
- The catalogs are published on GitHub Pages with a documentation home page. A `v*` tag makes CI publish the archives as a GitHub release.
