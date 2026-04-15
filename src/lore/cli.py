"""CLI for lore — the rare manual interface.

Most knowledge capture happens automatically via the MCP server.
The CLI is for manual capture, search, compilation, and status checks.
"""

import click

from . import __version__, store, compiler
from .types import Entry, fact, decision, learning, feedback, reference
from .mcp_server import serve as _mcp_serve


@click.group()
@click.version_option(__version__)
def main():
    """lore — your knowledge base has a compiler."""
    pass


@main.command()
def init():
    """Initialize lore in ~/.lore/."""
    store.ensure_dirs()
    click.echo(f"Initialized lore at {store.lore_dir()}")
    click.echo("")
    click.echo("Next steps:")
    click.echo("  lore learn 'something useful' -p myproject   # capture a learning")
    click.echo("  lore status                                   # see what's captured")
    click.echo("  lore compile myproject                        # compile into an article")


@main.command()
@click.argument("content")
@click.option("-p", "--project", default="", help="Project name")
@click.option("--why", default=None, help="Why this was learned (context)")
def learn(content, project, why):
    """Capture a learning (reusable insight)."""
    entry = learning(content, project=project)
    if why:
        entry.why = why
    entry = store.append(entry)
    _echo_captured(entry)


@main.command("fact")
@click.argument("content")
@click.option("-p", "--project", default="", help="Project name")
@click.option("--replaces", default=None, help="ID of fact this supersedes")
def add_fact(content, project, replaces):
    """Capture a fact."""
    entry = fact(content, project=project)
    if replaces:
        entry = store.supersede(replaces, entry)
    else:
        entry = store.append(entry)
    _echo_captured(entry)


@main.command("decision")
@click.argument("content")
@click.option("-p", "--project", default="", help="Project name")
@click.option("--why", required=True, help="Why this decision was made")
@click.option("--tried-first", default=None, help="What was tried before")
@click.option("--failed-because", default=None, help="Why the first approach failed")
@click.option("--outcome", default=None, help="What happened after the decision")
def add_decision(content, project, why, tried_first, failed_because, outcome):
    """Capture a decision with full reasoning trace."""
    entry = decision(content, project=project, why=why,
                     tried_first=tried_first, failed_because=failed_because,
                     outcome=outcome)
    entry = store.append(entry)
    _echo_captured(entry)


@main.command("feedback")
@click.argument("content")
def add_feedback(content):
    """Capture a preference or rule (applies globally)."""
    entry = feedback(content)
    entry = store.append(entry)
    _echo_captured(entry)


@main.command("ref")
@click.argument("content")
@click.option("-p", "--project", default="", help="Project name")
def add_reference(content, project):
    """Capture a reference (pointer to external info)."""
    entry = reference(content, project=project)
    entry = store.append(entry)
    _echo_captured(entry)


@main.command()
@click.argument("query", default="")
@click.option("-p", "--project", default=None, help="Filter by project")
@click.option("-t", "--type", "entry_type", default=None,
              type=click.Choice(["fact", "decision", "learning", "feedback", "reference"]),
              help="Filter by entry type")
@click.option("-n", "--limit", default=20, help="Max results")
def search(query, project, entry_type, limit):
    """Search across all captured knowledge."""
    results = store.search(query, project=project, entry_type=entry_type)
    if not results:
        click.echo("No results found.")
        return

    # Most recent first
    results = list(reversed(results))[:limit]
    for entry in results:
        _echo_entry(entry)
        click.echo("")


@main.command()
@click.argument("project")
@click.option("-o", "--output", default=None, help="Output file path")
def compile(project, output):
    """Compile a project's entries into a CLAUDE.md article."""
    entries = store.load_project(project)
    if not entries:
        click.echo(f"No entries for project '{project}'.")
        return

    click.echo(f"Compiling {project} ({len(entries)} entries)...")
    if output:
        text = compiler.compile_project(project, output)
        click.echo(f"Written: {output} ({len(text.splitlines())} lines)")
    else:
        text = compiler.compile_to_default_path(project)
        path = store.lore_dir() / "compiled" / f"{project}.md"
        click.echo(f"Written: {path} ({len(text.splitlines())} lines)")


@main.command()
def status():
    """Show what's captured across all projects."""
    stats = store.project_stats()
    if not stats:
        click.echo("No entries yet. Run 'lore init' and start capturing.")
        return

    total_entries = 0
    total_stale = 0
    for project, s in stats.items():
        total_entries += s["total"]
        total_stale += s["stale"]
        types_str = ", ".join(f'{v} {k}' for k, v in sorted(s["types"].items()))
        stale_str = f" ({s['stale']} stale)" if s["stale"] else ""
        last = s["last_entry"][:10] if s["last_entry"] else "?"
        click.echo(f"  {project:20s}  {s['total']:4d} entries  ({types_str}){stale_str}  last: {last}")

    click.echo(f"\n  Total: {total_entries} entries across {len(stats)} projects")
    if total_stale:
        click.echo(f"  ⚠ {total_stale} entries are stale (older than their stale_after date)")


@main.command()
def demo():
    """Generate sample entries to see how lore works."""
    store.ensure_dirs()

    samples = [
        fact("Claude Code supports --allowedTools for tool-level scoping", project="demo"),
        fact("Multica hardcodes --permission-mode bypassPermissions", project="demo"),
        decision("Wrap agent CLIs instead of building custom adapters", project="demo",
                 why="Multica review showed wrapping is simpler. Custom adapters = 500 lines, wrappers = 200 lines.",
                 tried_first="Custom internal/adapters/github/ Go package calling GitHub API directly",
                 failed_because="Contradicted our own thesis: README says 'wraps not replaces'",
                 outcome="Shipped in 200 lines. Generalizes to Codex/OpenClaw/OpenCode."),
        learning("iframe in widget automation requires inspecting shadow DOM first. Direct querySelector fails silently.", project="demo"),
        feedback("Never add Co-Authored-By Claude to commits"),
        reference("Shopify CLI: shopify store execute --store jumkey.myshopify.com", project="demo"),
    ]

    for s in samples:
        store.append(s)

    click.echo(f"Created {len(samples)} sample entries in project 'demo'.")
    click.echo("")
    click.echo("Try these:")
    click.echo("  lore search 'adapter'              # find entries about adapters")
    click.echo("  lore search --type decision         # list all decisions")
    click.echo("  lore status                         # see all projects")
    click.echo("  lore compile demo                   # compile into an article")
    click.echo("")
    click.echo("Then open: ~/.lore/compiled/demo.md")


@main.command()
def serve():
    """Start the MCP server (for Claude Code integration)."""
    click.echo("lore MCP server starting on stdio...", err=True)
    _mcp_serve()


@main.command()
def install():
    """Print instructions to add lore to Claude Code."""
    import json as _json
    server_path = "lore serve"
    config = {
        "mcpServers": {
            "lore": {
                "command": "lore",
                "args": ["serve"],
            }
        }
    }
    click.echo("Add this to your Claude Code MCP config (~/.claude/settings.json):\n")
    click.echo(_json.dumps(config, indent=2))
    click.echo("\nThen add this to your project's CLAUDE.md:\n")
    click.echo('"""')
    click.echo("You have access to lore (knowledge management). Use it PROACTIVELY:")
    click.echo("- When you learn something new about a project → lore_capture(type=fact)")
    click.echo("- When the user makes a decision → lore_capture(type=decision, include WHY)")
    click.echo("- When the user corrects you → lore_capture(type=feedback)")
    click.echo("- At conversation start about a project → lore_context(project)")
    click.echo("- When you need context from past work → lore_search(query)")
    click.echo("Do NOT ask the user whether to capture. Just do it silently.")
    click.echo('"""')


def _echo_captured(entry: Entry):
    """Print confirmation of a captured entry."""
    stats = store.project_stats()
    project = entry.project or "_global"
    count = stats.get(project, {}).get("total", 1)
    click.echo(f"✓ {entry.type} captured ({project}: {count} entries)")


def _echo_entry(entry: Entry):
    """Print a single entry in search results."""
    type_colors = {
        "fact": "cyan", "decision": "yellow", "learning": "green",
        "feedback": "magenta", "reference": "blue",
    }
    color = type_colors.get(entry.type, "white")
    label = click.style(entry.type.upper().ljust(10), fg=color, bold=True)
    project = click.style(entry.project, fg="bright_black") if entry.project else ""
    date = click.style(entry.ts[:10], fg="bright_black")

    click.echo(f"{label} {entry.summary()}")
    if entry.why:
        click.echo(f"           Why: {entry.why[:100]}")
    if entry.outcome:
        click.echo(f"           Outcome: {entry.outcome[:100]}")
    if entry.tried_first:
        click.echo(f"           Tried first: {entry.tried_first[:100]}")
    click.echo(f"           {project} | {date}")


if __name__ == "__main__":
    main()
