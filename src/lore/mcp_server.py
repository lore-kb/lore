"""MCP server for lore — the auto-capture mechanism.

This is what makes lore unique: Claude Code calls these tools
proactively during conversation. The user never types 'lore' anything.
Knowledge flows into the store as a side effect of working.

To use: add this server to Claude Code's MCP config, and add the
CLAUDE.md instruction that tells Claude to use lore tools proactively.

Usage:
    python -m lore.mcp_server

Or via the CLI:
    lore serve
"""

import json
import sys

from .types import fact, decision, learning, feedback, reference
from . import store, compiler

# Notification symbols for each entry type
_ICONS = {
    "fact": "📌",
    "decision": "⚖️",
    "learning": "💡",
    "feedback": "📝",
    "reference": "🔗",
}


def _notify(entry_type: str, content: str, project: str):
    """Print a notification to stderr so the user sees it.

    MCP tool results go to Claude (stdout JSON-RPC). The user never sees
    them. This stderr print is how the user knows lore captured something.
    """
    icon = _ICONS.get(entry_type, "📦")
    proj = f" ({project})" if project and project != "_global" else ""
    short = content[:80] + "..." if len(content) > 80 else content
    print(f"  {icon} lore: {entry_type}{proj} — {short}", file=sys.stderr, flush=True)


def handle_request(request: dict) -> dict:
    """Handle a JSON-RPC request from Claude Code."""
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "initialize":
        return _response(
            req_id,
            {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "lore", "version": "0.1.0"},
                "capabilities": {"tools": {"listChanged": False}},
            },
        )

    if method == "tools/list":
        return _response(req_id, {"tools": TOOLS})

    if method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments", {})
        try:
            result = _call_tool(name, args)
            return _response(
                req_id,
                {
                    "content": [{"type": "text", "text": result}],
                },
            )
        except Exception as e:
            return _response(
                req_id,
                {
                    "content": [{"type": "text", "text": f"Error: {e}"}],
                    "isError": True,
                },
            )

    if method == "notifications/initialized":
        return None  # notification, no response needed

    return _error(req_id, -32601, f"Unknown method: {method}")


TOOLS = [
    {
        "name": "lore_capture",
        "description": (
            "Capture a piece of knowledge (fact, decision, learning, feedback, or reference). "
            "Call this PROACTIVELY when you detect new knowledge during conversation. "
            "For decisions, always include 'why'. For learnings, include context that makes "
            "it reusable. Do NOT ask the user whether to capture — just do it silently."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["fact", "decision", "learning", "feedback", "reference"],
                    "description": "Type of knowledge entry",
                },
                "content": {
                    "type": "string",
                    "description": "The knowledge to capture",
                },
                "project": {
                    "type": "string",
                    "description": "Project name (auto-detected from cwd if omitted)",
                    "default": "",
                },
                "why": {
                    "type": "string",
                    "description": "Why this decision was made (required for type=decision)",
                    "default": "",
                },
                "tried_first": {
                    "type": "string",
                    "description": "What was tried before this approach",
                    "default": "",
                },
                "failed_because": {
                    "type": "string",
                    "description": "Why the previous approach failed",
                    "default": "",
                },
                "outcome": {
                    "type": "string",
                    "description": "What happened after this decision/learning",
                    "default": "",
                },
                "supersedes": {
                    "type": "string",
                    "description": "ID of an entry this replaces (for updated facts)",
                    "default": "",
                },
            },
            "required": ["type", "content"],
        },
    },
    {
        "name": "lore_search",
        "description": (
            "Search across all captured knowledge. Use this when you need context from "
            "past sessions — decisions that were made, learnings that apply, facts about "
            "the project. Returns structured results with decision traces."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (matched against content, why, outcome, tags)",
                },
                "project": {
                    "type": "string",
                    "description": "Filter by project name",
                    "default": "",
                },
                "type": {
                    "type": "string",
                    "enum": [
                        "fact",
                        "decision",
                        "learning",
                        "feedback",
                        "reference",
                        "",
                    ],
                    "description": "Filter by entry type",
                    "default": "",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "lore_context",
        "description": (
            "Load the compiled knowledge summary for a project. Call this at the START "
            "of a conversation when the user mentions a project, to load relevant context "
            "from past sessions. Returns a concise summary of decisions, learnings, and "
            "current state."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": "Project name to load context for",
                },
            },
            "required": ["project"],
        },
    },
]


def _call_tool(name: str, args: dict) -> str:
    """Execute a tool and return the result as text."""
    store.ensure_dirs()

    if name == "lore_capture":
        entry_type = args["type"]
        content = args["content"]
        project = args.get("project", "")
        supersedes_id = args.get("supersedes", "")

        constructors = {
            "fact": fact,
            "decision": decision,
            "learning": learning,
            "feedback": feedback,
            "reference": reference,
        }
        constructor = constructors.get(entry_type)
        if not constructor:
            return f"Unknown type: {entry_type}"

        kwargs = {}
        if entry_type != "feedback":
            kwargs["project"] = project
        for field in ("why", "tried_first", "failed_because", "outcome"):
            if args.get(field):
                kwargs[field] = args[field]

        entry = constructor(content, **kwargs)

        if supersedes_id:
            entry = store.supersede(supersedes_id, entry)
        else:
            entry = store.append(entry)

        stats = store.project_stats()
        proj = entry.project or "_global"
        count = stats.get(proj, {}).get("total", 1)
        _notify(entry_type, content, proj)
        return f"Captured {entry_type} ({proj}: {count} entries)"

    elif name == "lore_search":
        query = args.get("query", "")
        project = args.get("project") or None
        entry_type = args.get("type") or None

        results = store.search(query, project=project, entry_type=entry_type)
        if not results:
            return "No results found."

        results = list(reversed(results))[:15]
        lines = []
        for e in results:
            lines.append(f"[{e.type.upper()}] {e.content}")
            if e.why:
                lines.append(f"  Why: {e.why}")
            if e.tried_first:
                lines.append(f"  Tried first: {e.tried_first}")
            if e.failed_because:
                lines.append(f"  Failed because: {e.failed_because}")
            if e.outcome:
                lines.append(f"  Outcome: {e.outcome}")
            lines.append(f"  Project: {e.project} | Date: {e.ts[:10]}")
            lines.append("")
        return "\n".join(lines)

    elif name == "lore_context":
        project = args["project"]
        entries = store.load_project(project)
        if not entries:
            return f"No knowledge captured for project '{project}' yet."

        # Try compiled version first
        compiled_path = store.lore_dir() / "compiled" / f"{project}.md"
        if compiled_path.exists():
            return compiled_path.read_text()

        # Otherwise compile on the fly (offline mode)
        return compiler.compile_project(project)

    return f"Unknown tool: {name}"


def _response(req_id, result):
    """Build a JSON-RPC response."""
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _error(req_id, code, message):
    """Build a JSON-RPC error response."""
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def serve():
    """Run the MCP server on stdio (JSON-RPC over stdin/stdout)."""
    store.ensure_dirs()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue

        response = handle_request(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    serve()
