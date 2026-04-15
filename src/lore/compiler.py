"""Compiles raw entries into a CLAUDE.md-compatible article.

The compile step is what makes lore a compiler, not a notebook. It takes
N raw entries (facts, decisions, learnings) and produces one coherent
article that fits within a 200-line budget — the same constraint power
users maintain for their CLAUDE.md files.
"""

import os
from typing import Optional

from . import store
from .types import Entry

COMPILE_PROMPT = """You are compiling a project knowledge base from raw entries into a clean, concise CLAUDE.md file.

PROJECT: {project}
ENTRIES ({count} total):

{entries_text}

---

Compile these entries into a CLAUDE.md file that:

1. Starts with "# {project}" and a 1-2 sentence summary
2. Has a "## Key Decisions" section listing the most important decisions with their WHY (not just what)
3. Has a "## Known Pitfalls" section with things that were tried and failed (from decision traces)
4. Has a "## Current State" section with the latest facts about the project
5. Has a "## Rules" section with any feedback/preferences that apply
6. Stays UNDER 200 lines total
7. Uses bullet points, not paragraphs
8. Omits stale facts (marked as stale in the entries)
9. When multiple facts conflict, use the most recent one
10. Does NOT include entry IDs, timestamps, or metadata — just the knowledge

Output ONLY the markdown content. No explanation, no preamble."""


def compile_project(project: str, output_path: Optional[str] = None) -> str:
    """Compile a project's entries into a CLAUDE.md article.

    Returns the compiled markdown text. If output_path is provided,
    also writes to that file.
    """
    entries = store.load_project(project)
    if not entries:
        return f"# {project}\n\nNo entries yet.\n"

    # Also load global feedback entries
    global_entries = [e for e in store.load_project("_global") if e.type == "feedback"]

    # Filter out superseded entries
    superseded_ids = {e.supersedes for e in entries if e.supersedes}
    entries = [e for e in entries if e.id not in superseded_ids]

    all_entries = entries + global_entries
    entries_text = _format_entries_for_prompt(all_entries)

    compiled = _call_llm(project, entries_text, len(all_entries))

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(compiled)

    return compiled


def compile_to_default_path(project: str) -> str:
    """Compile and write to the default compiled/ directory."""
    output_path = str(store.lore_dir() / "compiled" / f"{project}.md")
    return compile_project(project, output_path)


def _format_entries_for_prompt(entries: list[Entry]) -> str:
    """Format entries as structured text for the LLM prompt."""
    lines = []
    for e in entries:
        header = f"[{e.type.upper()}] ({e.ts[:10]})"
        if e.is_stale:
            header += " [STALE]"
        lines.append(header)
        lines.append(f"  {e.content}")
        if e.why:
            lines.append(f"  WHY: {e.why}")
        if e.tried_first:
            lines.append(f"  TRIED FIRST: {e.tried_first}")
        if e.failed_because:
            lines.append(f"  FAILED BECAUSE: {e.failed_because}")
        if e.outcome:
            lines.append(f"  OUTCOME: {e.outcome}")
        if e.tags:
            lines.append(f"  TAGS: {', '.join(e.tags)}")
        lines.append("")
    return "\n".join(lines)


def _call_llm(project: str, entries_text: str, count: int) -> str:
    """Call the LLM to compile entries into an article."""
    prompt = COMPILE_PROMPT.format(
        project=project,
        count=count,
        entries_text=entries_text,
    )

    # Try Anthropic API first
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        return _call_anthropic(prompt, api_key)

    # Fallback: generate a simple structured output without LLM
    return _compile_without_llm(project, entries_text)


def _call_anthropic(prompt: str, api_key: str) -> str:
    """Call Claude API for compilation."""
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception as e:
        return f"# Compilation error\n\nFailed to call LLM: {e}\n"


def _compile_without_llm(project: str, entries_text: str) -> str:
    """Simple structured compilation without an LLM.

    Produces a usable CLAUDE.md by organizing entries by type.
    Not as good as LLM compilation but works offline and with no API key.
    """
    from . import store as s

    entries = s.load_project(project)
    superseded = {e.supersedes for e in entries if e.supersedes}
    entries = [e for e in entries if e.id not in superseded and not e.is_stale]

    lines = [f"# {project}", ""]

    decisions = [e for e in entries if e.type == "decision"]
    if decisions:
        lines.append("## Key Decisions")
        for d in decisions:
            lines.append(f"- **{d.content}**")
            if d.why:
                lines.append(f"  - Why: {d.why}")
            if d.outcome:
                lines.append(f"  - Outcome: {d.outcome}")
        lines.append("")

    learnings = [e for e in entries if e.type == "learning"]
    if learnings:
        lines.append("## Learnings")
        for entry in learnings:
            lines.append(f"- {entry.content}")
        lines.append("")

    facts = [e for e in entries if e.type == "fact"]
    if facts:
        lines.append("## Current State")
        for f_ in facts[-20:]:  # only most recent 20
            lines.append(f"- {f_.content}")
        lines.append("")

    feedback = [e for e in entries if e.type == "feedback"]
    global_fb = [e for e in s.load_project("_global") if e.type == "feedback"]
    all_fb = feedback + global_fb
    if all_fb:
        lines.append("## Rules")
        for fb in all_fb:
            lines.append(f"- {fb.content}")
        lines.append("")

    return "\n".join(lines)
