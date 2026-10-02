# Talk outline

This order fits a public talk.

## Skeleton

1. `cover`: title and author on a red fill with lines. `scaffold.py --author "Pavel Korolev"` adds the cover. The authorless `title` layout is for material nobody presents: a handout deck, a recording, an internal review.
2. `context` "About me", if the audience does not know the speaker and their background affects trust. Name, role, one reason to trust them, a photo.
3. Framing: a neutral `statement` on what the talk is about, if the audience may expect something else. For example: "This talk is about a hobby side project".
4. Plan: a `list` titled "Plan" with chapter names, items revealed one at a time. Plan items have no subtitle.
5. Before each chapter from the plan, a `section` numbered `01`, `02` with the same name as in the plan. Subsections get no divider. A one-slide chapter does not need one.
6. A chapter holds episodes, described below. Each conclusion follows its episodes.
7. Before the end you may collect conclusions in a "What I took away" list, revealed one at a time. The summary repeats conclusions already shown and adds no new ones.
8. `end`: a closing line like "Thank you", the author with an optional event, one contact as a QR code. `QR_LINK` comes from `qr.py <address> --link`, see [QR](qr.md).

Without an author, plan and chapters you get a short deck: `title`, content slides, `end`. A ten-slide deck rarely needs dividers.

## Episode

Introduce a technical detail as a chain: the pain, the decision, the observed effect, the new cost. One event taken apart with a number or a frame convinces more than a list of general advice. Put the evidence, such as a chart, screenshot, code or table, next to the claim it supports.

A bridge between episodes is a neutral one-sentence `statement` on what exists and what comes next. For example: "The content is done. Now the package has to become a release".

## Claim color

A red fill (`surface-accent` on `.s-statement`) marks a conclusion the audience takes home. Framing, bridges, facts and numbers stay neutral. The `statement` fragment is neutral. Add the conclusion class by hand.

## Wording

- A claim title is one sentence. A second idea goes into a list, steps or a comparison. Avoid two claims in a row.
- A subtitle refines the title in one sentence with no final period. An idea of its own gets its own slide.
- Write conclusions in the first person about your experience: "it worked in my project", "the cost was". Do not generalize one case to the whole industry.
- Keep internal file names and jargon only if the audience knows them.

## Structural slides

Do not add kickers ("Take 01", "Chapter 2 of 6"), navigation lines or series labels to the cover, plan, dividers and end. Add structure with new slides in standard layouts: a claim, a list, steps.

Many short slides at a fast pace are normal. Do not squeeze two ideas onto one slide to save pages. Check timing in a rehearsal.
