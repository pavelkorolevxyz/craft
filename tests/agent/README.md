# Testing the skill with separate agents

This tests how a model behaves on real material. It does not replace the source tests. `task.md` gives the same task for a deck and a working page. It deliberately includes independent items, criteria with a reveal, a real flow, equal ways to check a release and a filter with an empty result.

## Running

From the repository root, with model access set up:

```bash
python3 tests/agent/agent_eval.py --agent pi --model openai-codex/gpt-6-astra \
  --output artifacts/agent-eval/my-pi
python3 tests/agent/agent_eval.py --agent claude --model sonnet \
  --output artifacts/agent-eval/my-claude
```

Each run needs a new folder. The default limit is 900 seconds, change it with `--timeout`. The commands make real model calls and are not part of `make test`. Run independent runs in parallel if you need to, but do not compare their times as pure model speed. Service and machine load differ.

The script copies the skill to `craft/` and saves `task.md`, `run.json`, `events.jsonl` and `stderr.log`. The agent gets only this copy and writes to `output/`. `run.json` records the CLI version, model, command, hashes of the task and documents, exit code and time. Code 124 means a timeout, not a successful finish. The `documentsRead` and `documentCharsRead` fields show which references the agent opened and how many characters it read. Compare them with the matching reading route in `scripts/craft.json`. Extra files mean the routing in `SKILL.md` or the index is not precise enough.

For pi, third-party extensions, skills and context files are off. Only the Craft under test is loaded. For Claude, `--safe-mode` turns off user settings, and MCP servers and interactive approval are off too. Read, write, edit and Bash are allowed. This gives separate working folders and context, not an OS sandbox. Run only a trusted task. Models can reach the machine through Bash.

## Independent review

Do not change the agent's result before the review. Wait for the `returncode` field in `run.json`.

```bash
python3 scripts/check_project.py artifacts/agent-eval/my-pi/output/slides --full
python3 scripts/check_project.py artifacts/agent-eval/my-pi/output/interface --full
node tests/agent/browser.mjs artifacts/agent-eval/my-pi
```

You need Node.js with built-in WebSocket and Chromium. `CHROMIUM` sets the browser path. The browser script saves to `review/` a separate screenshot of each screen state of the deck, the page in both themes at 1440, 390 and 320 px, the search, the empty result, the selection, the PDFs and `browser.json`.

Deck navigation, Tab, Enter, arrow keys and mouse selection of a record go through CDP Input. Enter includes the `char` event that native button activation needs. Before the click, the script scrolls the record into view without smooth scrolling. Slide counters reach their final value before the screenshot. The script changes search and filter through the DOM with the matching event and triggers the reset with `.click()`. This does not test the native filter menu. The script recognizes the table and list variants from the task. It is not a general test for any interface. If the structure differs, check the test selector first. Do not report an app bug just because a familiar class is missing.

Look at the screenshots and PDFs yourself. Use `browser.json` to confirm that:

- the independent directions stay a list, not a comparison;
- the criteria appear one at a time and the next one is not visible early. The first frame holds the heading, or the heading with the first criterion, as `selection.md` allows;
- the flow appears as the client, then the link to the server, then the link to the log. No node has a permanent accent;
- the variants are not labeled "Before / After", and 40 and 8 minutes and the same 12 scenarios are kept;
- search returns one record, combining it with "Done" returns zero, and the reset brings back four;
- an empty set leaves no old details, and selection by mouse and keyboard updates them;
- printing outputs the current set, not the original data or hidden selected data;
- every slide has a `data-key`, and `data-local-reason` explains each local composition;
- `release.py` built the archive in `output/release`. It has `manifest.json` and `README.txt`, no notes, and is at most 10 MB.

The agent's `checks.md` is not proof without files and reproducible commands. Record semantics, mechanics, appearance and run completion separately. One successful example does not prove the skill is reliable, and one timeout does not prove the markup is poor.
