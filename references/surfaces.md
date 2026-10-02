# Craft formats

Pick the request's format before loading detailed references.

| Request | `--surface` value | What to read | Project setup |
|---|---|---|---|
| dashboard, report, local tool, data page | `interface` | `interfaces/design-language.md`, then the patterns or components you need | `--surface interface` |
| talk, deck, conference slides, presentation | `slides` | `slides/selection.md`, then `slides/design-language.md` and `slides/authoring.md` | `--surface slides` |
| poster, long read, social image, resume or unknown format | new or one-off format | `extending.md` | add a generator once the conditions are known |

## Routing rules

1. Use the format the user asked for.
2. If people operate the result, filter it or read it closely, choose `interface`.
3. If the material is projected or a speaker shows it in sequence, choose `slides`.
4. Do not fake slides with a responsive page, and do not turn a dashboard into a deck.
5. For an unknown format, define the audience, viewing distance, aspect ratio, interaction, duration and export format before writing code.

Load the shared identity reference once. Load format references only after routing.
