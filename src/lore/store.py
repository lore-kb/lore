"""JSONL-based knowledge store.

Each project gets its own .jsonl file in ~/.lore/entries/. Files are
append-only and git-friendly. Global entries (feedback, preferences)
go in _global.jsonl.
"""

import os
import json
from pathlib import Path
from typing import Optional

from .types import Entry

DEFAULT_LORE_DIR = os.path.expanduser("~/.lore")


def lore_dir() -> Path:
    """Return the lore directory, respecting LORE_DIR env var."""
    return Path(os.environ.get("LORE_DIR", DEFAULT_LORE_DIR))


def ensure_dirs():
    """Create the lore directory structure if it doesn't exist."""
    base = lore_dir()
    (base / "entries").mkdir(parents=True, exist_ok=True)
    (base / "compiled").mkdir(parents=True, exist_ok=True)


def _entries_path(project: str) -> Path:
    """Path to a project's JSONL file."""
    safe_name = project.replace("/", "_").replace("\\", "_") or "_global"
    return lore_dir() / "entries" / f"{safe_name}.jsonl"


def append(entry: Entry) -> Entry:
    """Append an entry to the store. Returns the entry with generated ID."""
    ensure_dirs()
    path = _entries_path(entry.project)
    with open(path, "a", encoding="utf-8") as f:
        f.write(entry.to_json() + "\n")
    return entry


def load_project(project: str) -> list[Entry]:
    """Load all entries for a project."""
    path = _entries_path(project)
    if not path.exists():
        return []
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(Entry.from_json(line))
                except (json.JSONDecodeError, TypeError):
                    continue
    return entries


def load_all() -> list[Entry]:
    """Load all entries across all projects."""
    ensure_dirs()
    entries_dir = lore_dir() / "entries"
    all_entries = []
    for path in sorted(entries_dir.glob("*.jsonl")):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        all_entries.append(Entry.from_json(line))
                    except (json.JSONDecodeError, TypeError):
                        continue
    return all_entries


def projects() -> list[str]:
    """List all projects that have entries."""
    ensure_dirs()
    entries_dir = lore_dir() / "entries"
    return sorted(p.stem for p in entries_dir.glob("*.jsonl") if p.stat().st_size > 0)


def project_stats() -> dict[str, dict]:
    """Return stats for each project: entry count, types, last entry date."""
    stats = {}
    for project in projects():
        entries = load_project(project)
        if not entries:
            continue
        type_counts = {}
        for e in entries:
            type_counts[e.type] = type_counts.get(e.type, 0) + 1
        stale = sum(1 for e in entries if e.is_stale)
        stats[project] = {
            "total": len(entries),
            "types": type_counts,
            "stale": stale,
            "last_entry": entries[-1].ts if entries else None,
        }
    return stats


def search(
    query: str, project: Optional[str] = None, entry_type: Optional[str] = None
) -> list[Entry]:
    """Search entries by query text, optionally filtered by project and type."""
    if project:
        entries = load_project(project)
    else:
        entries = load_all()

    if entry_type:
        entries = [e for e in entries if e.type == entry_type]

    # Filter by superseded: if entry A supersedes entry B, exclude B
    superseded_ids = {e.supersedes for e in entries if e.supersedes}
    entries = [e for e in entries if e.id not in superseded_ids]

    if not query:
        return entries

    return [e for e in entries if e.matches(query)]


def supersede(old_id: str, new_entry: Entry) -> Entry:
    """Create a new entry that supersedes an old one."""
    new_entry.supersedes = old_id
    return append(new_entry)
