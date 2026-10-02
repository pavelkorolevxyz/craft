# Craft workflow

## Before HTML

Define the audience, task, real data and expected action or conclusion. Choose a slide layout by [data relation and reveal plan](slides/selection.md), page geometry by [interface layout](interfaces/layout.md).

Use real user data. Do not invent metrics, causes, reviews, sources or system states. If data is missing, mark the gap or ask. Every standalone value gets its own label. Do not glue a category, state and duration into one line.

## Create and compose

All command paths below are relative to the skill root. From another folder, use the root's absolute path.

```bash
python3 scripts/scaffold.py <target-folder> --surface interface --title "Title"
# Styles only, no shell: --template bare. For a deck: --surface slides, a talk with an author: --author "Pavel Korolev"
python3 scripts/compose.py <target-folder> --list-fragments
python3 scripts/compose.py <target-folder> --fragment <id> --list-placeholders
```

Settle delivery before scaffolding. `--delivery local` (the default) keeps everything in the project folder and works over `file://` without a network. `--delivery web` loads fonts from Google Fonts and allows https only from `fonts.googleapis.com`, `fonts.gstatic.com`, and `cdn.jsdelivr.net` or `unpkg.com` with a pinned version. A page without media can become one HTML file: `bundle.py <folder>` writes `index.single.html`. The starter does not overwrite a non-empty folder.

Add a matching registered fragment with `compose.py`. Pass text with `--set` and trusted markup with `--html` or `--html-file`. `--dry-run` validates and prints the fragment without writing it. The script escapes text, checks types and `id` collisions, and adds dependencies.

Use a fragment first, then a theme utility, then local CSS. Do not bend the material to fit a wrong template. Do not copy the whole catalog, and do not edit the shared theme for one page. Keep `data-craft-layout`, `data-slide-layout` and state attributes.

Before handoff, remove filler, promotional claims and conclusions without data. Keep terms and caveats that change the meaning.

## Check

```bash
python3 scripts/check_project.py <target-folder>          # while editing
python3 scripts/check_project.py <target-folder> --full   # before handoff
```

You need Chromium (`CHROMIUM`) and Node.js. `--static-only` checks sources without a browser. The default renders three widths in both themes, and every deck state in its final frame and on a phone: text inside, no shifts, QR scans. `--full` adds the PDF, and for a deck motion, counters, video, the panel, the light theme and deep links. `--shots` saves every page.

Automation does not check meaning. Also check:

| Material | What to check |
|---|---|
| Interface | Search, filters and actions with mouse and keyboard; focus, selection, errors and empty results |
| Slides | Screenshots of every frame against the plan; the basis for comparisons, arrows and accents; motion on a real phone if the deck has video |
| Both formats | Readability and contrast; red without a function |

Keep screenshots, PDFs and exact commands. Name any check you could not run. An agent's own report and a green validator do not replace looking at the content.
