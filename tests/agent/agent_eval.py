#!/usr/bin/env python3
"""Run a separate agent on a copy of Craft and save the run conditions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from lib import ROOT


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=("pi", "claude"), required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--task", type=Path, default=ROOT / "tests/agent/task.md")
    args = parser.parse_args()
    target = args.output.expanduser().resolve()
    target.mkdir(parents=True, exist_ok=False)
    skill = target / "craft"
    skill.mkdir()
    for name in ("SKILL.md", "references", "assets", "catalog", "scripts"):
        source = ROOT / name
        if source.is_dir():
            shutil.copytree(source, skill / name, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(source, skill / name)
    task = args.task.read_text(encoding="utf-8")
    (target / "task.md").write_text(task, encoding="utf-8")
    if args.agent == "pi":
        command = ["pi", "-p", "--mode", "json", "--no-session", "--no-extensions",
                   "--no-skills", "--skill", str(skill / "SKILL.md"), "--no-context-files",
                   "--no-prompt-templates", "--offline", "--model", args.model, task]
    else:
        command = ["claude", "-p", "--safe-mode", "--strict-mcp-config",
                   "--no-session-persistence", "--output-format", "stream-json", "--verbose",
                   "--permission-mode", "dontAsk", "--tools", "Read,Write,Edit,Bash",
                   "--allowedTools", "Read,Write,Edit,Bash", "--model", args.model, task]
    documents = [skill / "SKILL.md", *sorted((skill / "references").rglob("*.md"))]
    hashes = {str(p.relative_to(skill)): hashlib.sha256(p.read_bytes()).hexdigest() for p in documents}
    metadata = {"agent": args.agent, "model": args.model, "command": command[:-1] + ["<task.md>"],
                "taskSha256": hashlib.sha256(task.encode()).hexdigest(), "documentSha256": hashes,
                "documentChars": sum(len(p.read_text()) for p in documents), "timeout": args.timeout,
                "version": subprocess.check_output([args.agent, "--version"], text=True).strip()}
    (target / "run.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    start = time.monotonic()
    with (target / "events.jsonl").open("w") as stdout, (target / "stderr.log").open("w") as stderr:
        process = subprocess.Popen(command, cwd=target, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            code = process.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            code = 124
    metadata.update(returncode=code, seconds=round(time.monotonic() - start, 1))
    metadata["changedDocuments"] = [str(p.relative_to(skill)) for p in documents
                                    if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != hashes[str(p.relative_to(skill))]]
    read = documents_read(target / "events.jsonl", skill)
    metadata["documentsRead"] = read
    metadata["documentCharsRead"] = sum(len((skill / name).read_text()) for name in read if (skill / name).exists())
    (target / "run.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: metadata[key] for key in ("agent", "model", "returncode", "seconds", "changedDocuments", "documentCharsRead")}, ensure_ascii=False))


def documents_read(events: Path, skill: Path) -> list[str]:
    """Return the references the agent opened with a tool call, in order of first read.

    A path can be absolute, relative to the run folder, or relative to the last
    `cd` in a shell command, so each path is resolved where it appears."""
    run_dir = skill.parent
    seen: list[str] = []

    def calls(node):
        if isinstance(node, dict):
            if node.get("type") in ("tool_use", "toolCall"):
                yield node.get("input") or node.get("arguments") or {}
            for value in node.values():
                yield from calls(value)
        elif isinstance(node, list):
            for value in node:
                yield from calls(value)

    for line in events.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        for arguments in calls(event):
            for text in (str(value) for value in arguments.values() if isinstance(value, str)):
                base = run_dir
                for match in re.finditer(r"(?:\bcd\s+([^\s;&|]+))|([\w./-]+\.md)\b", text):
                    if match.group(1):
                        base = (run_dir / match.group(1)).resolve()
                        continue
                    candidate = Path(match.group(2))
                    for root in (Path("/"), base, run_dir):
                        path = (root / candidate).resolve()
                        if path.is_file() and skill in path.parents:
                            name = path.relative_to(skill).as_posix()
                            if name.endswith(".md") and (name == "SKILL.md" or name.startswith("references/")) and name not in seen:
                                seen.append(name)
                            break
    return seen

if __name__ == "__main__":
    main()
