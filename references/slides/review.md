# Deck edits and release

## Edits from feedback

Resolve the page number from the feedback to a key with `deck_map.py`, and name its key, step and title in the reply. Change only the agreed set: neighboring titles and order stay. Build a large rework as a separate version for approval first. After approval, keep one source. Give each comment a status: done, postponed with a reason, or needs a decision. The author's latest decision outranks earlier summaries and rules drawn from old edits.

## Release

```bash
python3 scripts/release.py <target-folder> --out <folder> --limit-mb <venue limit> [--pdf]
```

Give the organizer the archive from this command, not the project folder. It takes only the files in use, stops on drafts and placeholders, versions links against caching, writes `manifest.json` and `README.txt`, runs the `--full` check (`--check render` for a quick rebuild), checks the unpacked copy offline and prints the heaviest files. After publishing, check the site: `release.py <folder>/manifest.json --published <url>`.
