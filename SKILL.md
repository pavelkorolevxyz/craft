---
name: craft
description: "Use Craft for standalone HTML pages and slide decks."
---

# Craft

1. Pick the format. A talk or presentation uses `slides`. A page to read or operate uses `interface`. If the format is unclear, read the [format map](references/surfaces.md).
2. Read the shared [identity rules](references/identity.md) and the [build and check workflow](references/workflow.md). If the material is in Russian, also read [material in Russian](references/russian.md).
3. Follow only the chosen branch below. Open a reference from the "by content" list only if the material has that content. Do not read the catalog or references ahead of time.

## Slides

Before HTML, read the [talk outline](references/slides/narrative.md) and [choosing a layout](references/slides/selection.md), then the [visual language](references/slides/design-language.md) and the [mechanics](references/slides/authoring.md). Get the chosen fragment's contract from `compose.py --list-placeholders`.

By content:
- numeric chart: [charts](references/slides/charts.md);
- animation, number counter: [motion and numbers](references/slides/motion.md);
- video, screen recording, photo: [video and images](references/slides/media.md);
- source code: [code on a slide](references/slides/code.md);
- a URL shown on screen: [QR code](references/slides/qr.md);
- feedback on the deck or handing it to the organizer: [edits and release](references/slides/review.md).

## Interface

Pick the template without asking. A new standalone page: `blank` with the [shell](references/interfaces/shell.md). Embedding in another site, a fragment, or no header: `bare`, styles only.

Read the [page layout](references/interfaces/layout.md), the [visual language](references/interfaces/design-language.md) and the [component index](references/interfaces/components.md). The index maps the material's content to separate component references. Open only the ones you need.

If the material will be printed or saved as PDF, read [print](references/interfaces/print.md).

## Another format or extending the system

Read the [extension rules](references/extending.md). Level theory, catalog internals and releases are not needed for a normal build.
