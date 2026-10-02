# Choosing a layout and reveal plan

Read this before the catalog and before HTML. For each slide, write in the plan:

1. the idea in one sentence;
2. the data relation and `data-slide-layout`, and for a local composition, why no ready layout fit;
3. the `data-key`;
4. the first frame and each following reveal;
5. the reason for the accent, or "no accent";
6. for a screen recording, the video's role and poster.

Do not start HTML without these decisions.

The number of items does not pick the template. Two items are not a comparison, three items are not a diagram. Do not invent links, stages or a winner to make the deck look varied.

## Layout map

Values of `data-slide-layout`. `compose.py <project> --list-fragments` lists the fragments. Do not guess an id from a file name.

| Layout | Use for | Do not use for |
|---|---|---|
| `title` | The title of material without a speaker: a handout deck, a recording | A talk cover with an author, a conclusion or a transition |
| `cover` | The start of a talk with an author, the first slide of the talk | An intro card before each argument |
| `context` | The speaker's experience related to the topic | A project result, use `figure` |
| `section` | A move to a new question or a large part | A claim with content |
| `statement` | One idea with evidence before or after | Several separate ideas |
| `list` | Two or more items of one level | A required order of actions or real links between items |
| `comparison` | Two states or options on a shared criterion | Two unrelated topics |
| `quote` | The exact words of a verified source, with attribution | Your own wording |
| `metrics` | Several values that prove one conclusion without a shared axis | Change over time or a reference table |
| `code` | A point about specific syntax or a condition | Architecture or a visible result |
| `figure` | An image with a short annotation | Decoration or a long explanation |
| `screenshot` | A screen, recording or long page, full-slide | Two states, use `visual-comparison` |
| `table` | Checking uniform records across shared fields | One visual conclusion, use `chart` |
| `steps` | Actions in a required order | The talk plan or a dated history |
| `chart` | A numeric relation on an honest scale | Non-numeric items. Pick the chart type by the [data](charts.md) |
| `timeline` | Dated events or periods that explain the result | Instructions. Numbers 01, 02, 03 are not time |
| `flow` | Handoff, dependency, transformation or branching | A list of features, benefits or topics |
| `visual-comparison` | Two images on a shared question at a comparable scale | Unrelated images |
| `iterations` | Three or more versions of one screen, the current one large | A Before / After pair |
| `bento` | What one thing is made of, on one page: a stack, a set of topics | Topics covered one by one |
| `resource` | One verified resource with a URL and a QR code | Several links or the closing contact |
| `end` | The closing line, author and one contact as a QR code | A new argument |

## Checking the relation and the accent

For a comparison, finish the sentence "I compare ___ and ___ by ___". For Before / After, also name the one object and the change. Both sides use the same criteria and units. If two options have no transition between them, say so. The accented right half of a ready template does not pick a winner: equal options need neutral columns or a table.

For each arrow, name the real relation: "___ passes ___ to ___", "___ depends on ___" or another exact relation. If an arrow only means "next point of the talk", it is a list. Do not add a branch or a loop the data does not have.

| Material | Decision |
|---|---|
| Team training and monitoring | Two lines of work, `list`, not Before / After |
| Speed, accessibility, cost | Criteria, `list`, not `flow` |
| Install, configure, run | Ordered actions, `steps` |
| The client sends a request to the server | A real handoff, `flow` |
| Manual and automated checks | `comparison` by time, coverage and limits, with the same criteria |

All diagram nodes are neutral by default. Use `.flow-node--accent` only if the claim singles out that node, for example "Validation rejects a bad request before the write". Being in the center is not a reason.

A permanent highlight of a subject differs from the focus of the current explanation. `deck.js` does not move `.flow-node--accent` on reveal. To walk through a diagram, build it from neutral nodes and reveal the links. A moving accent needs a local rule for each state and a look at every frame. Check `.is-current`, `.is-after` and code line highlights the same way.

## Reveal plan

You must decide on reveals. You do not have to use them.

| Scenario | First frame | Each next click |
|---|---|---|
| Reading or comparing together | All content | No reveals. This is the usual case for a table or an overview diagram |
| Items covered one by one | The title, sometimes with the first item | One full item. An item, metric, step or event gets `.frag`. The first item goes without `.frag` next to the title if it starts the story |
| Explaining an object's path | The title and the start node | The incoming link and the next node together. A branch after its source, a loop after both ends |
| The first state comes first | The first side | The second side with its label and all its data |
| Evidence, then interpretation | The chart or image with labels | The conclusion or annotation. If the title already states the conclusion, show everything at once |

One `.frag` is one click in HTML order. The markup is in the [mechanics](authoring.md). Compare screenshots of every frame with this plan.

## Text on a slide

- A claim slide carries one idea. The subtitle explains the title and does not hide a second claim. A second idea gets its own slide or a list.
- An image caption adds a fact, a source or a date. It does not retell the frame.
- A one-line subtitle has no final period.
- Replace internal file, flag and class names with a short plain description if the audience does not know them.
- A demo shows the real product or an honestly labeled reconstruction.
- Estimate the length by rehearsal, not by page count.
