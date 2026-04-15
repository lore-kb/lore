# lore

**Your knowledge base has a compiler.**

You work with AI coding tools. You learn things — workarounds, architecture decisions, why approach X failed. By the next session, it's all gone. You re-explain. You re-discover. You lose hours.

lore fixes this. It captures knowledge during your AI coding sessions and compiles it into a searchable, version-controlled knowledge base that your AI reads automatically next time.

**You work. lore remembers.**

```bash
pip install lore-kb
lore init
lore demo
```

---

## The problem

Every AI coding session generates knowledge. Today, 99% of it is thrown away.

- You spend 2 hours figuring out that iframe widget automation needs shadow DOM inspection
- You close the terminal
- Three weeks later, same problem, new session, Claude has no memory of last time
- You spend another hour re-discovering the same solution

This happens every week, across every project, compounding into days of wasted time per month.

**Current workarounds (all manual, all fragile):**
- Maintaining CLAUDE.md files by hand (who updates them?)
- Custom `/learn` slash commands (you have to remember to type it)
- Keeping terminal windows open for a week (seriously — power users do this)
- Copy-pasting entire conversations into new sessions
- Sending agents to re-read the whole repo every session

## How lore works

### 1. Capture (automatic or manual)

**Automatic** — lore runs as an MCP server. Claude Code calls it during conversation without you doing anything:

```
You: "let's use engine wrappers instead of custom adapters"

Claude: [internally calls lore_capture({
  type: "decision",
  content: "Wrap agent CLIs instead of building custom adapters",
  why: "Multica review showed wrapping is simpler. 200 lines vs 500.",
  tried_first: "Custom GitHub adapter calling the API directly",
  failed_because: "Contradicted our own thesis — README says wraps not replaces"
})]

Claude: "Makes sense. I'll set up the engine wrapper..."
```

You didn't type anything. lore captured the decision with full reasoning.

**Manual** — for when you want to capture something explicitly:

```bash
lore learn "iframe automation requires shadow DOM inspection" -p myproject
lore decision "Use Redis for sessions" -p api --why "PostgreSQL advisory locks had deadlock issues under load"
lore feedback "Always run tests before committing"
```

### 2. Search (cross-session, structured)

```bash
$ lore search "iframe"
LEARNING   iframe automation requires shadow DOM inspection. Direct
           querySelector fails silently.
           myproject | 2026-03-28

$ lore search --type decision --project api
DECISION   Use Redis for sessions
           Why: PostgreSQL advisory locks had deadlock issues under load
           Tried first: pg_advisory_lock with retry loop
           Outcome: Redis sessions handle 10x the concurrent load
           api | 2026-04-02
```

Not keyword grep — **structured search** that knows types, projects, time, and decision traces.

### 3. Compile (LLM synthesis)

```bash
$ lore compile myproject
Compiling myproject (47 entries)...
✓ Written: ~/.lore/compiled/myproject.md (142 lines)
```

Takes 47 raw entries and produces one clean article:

```markdown
# myproject

## Key Decisions
- **Use engine wrappers, not custom adapters**
  - Why: Multica review showed wrapping is simpler. 200 vs 500 lines.
  - Outcome: Shipped. Generalizes to all agent CLIs.

## Known Pitfalls
- iframe widget automation: use shadow DOM inspection, not querySelector
- Don't use pg_advisory_lock under high concurrency — deadlocks

## Current State
- 9 CLI commands working, E2E tested
- v0.1.0 released with 6 platform binaries

## Rules
- Always run tests before committing
- Never add Co-Authored-By Claude to commits
```

Under 200 lines. CLAUDE.md-compatible. Auto-generated. The AI reads this at the start of every session.

---

## Quick start

### Try it (30 seconds)

```bash
pip install lore-kb
lore init
lore demo
lore search "adapter"
lore compile demo
cat ~/.lore/compiled/demo.md
```

### Use it manually

```bash
# Capture as you work
lore learn "hot reload breaks when config changes" -p myapp
lore decision "Switch to Vite from Webpack" -p frontend \
  --why "Build times dropped from 45s to 3s" \
  --tried-first "esbuild" \
  --failed-because "no HMR support for our plugin setup"
lore fact "API rate limit is 100 req/min per key" -p backend
lore feedback "Use descriptive variable names, not abbreviations"

# Find past knowledge
lore search "rate limit"
lore search --type decision --project frontend

# Compile into an article
lore compile myapp

# See what's captured
lore status
```

### Connect to Claude Code (auto-capture)

```bash
lore install
# Follow the printed instructions to add lore as an MCP server
```

After setup, Claude captures knowledge automatically during every conversation. No manual steps.

---

## What makes lore different

### Decision traces, not just notes

Every tool stores "we use approach X." lore stores the full trace:

```json
{
  "type": "decision",
  "content": "Use Redis for sessions",
  "why": "PostgreSQL advisory locks deadlocked under load",
  "tried_first": "pg_advisory_lock with retry loop",
  "failed_because": "Deadlocks at >50 concurrent connections",
  "outcome": "Redis handles 10x the load, no deadlocks"
}
```

When future-you asks "why don't we use PostgreSQL for sessions?" — the answer is already there with full context. Not "because we decided not to" but **why**, **what we tried first**, and **what happened**.

### Compiled context, not a knowledge dump

Raw captures pile up. lore compiles them into a concise article that fits within the 200-line budget that power users maintain for their CLAUDE.md files. Stale facts are flagged. Superseded entries are excluded. The result is what the AI actually needs, not everything lore knows.

### Stale knowledge detection

```bash
$ lore status
  myapp    47 entries (3 stale)
  backend  23 entries (0 stale)
  ⚠ myapp: 3 facts older than 30 days — verify with 'lore search --stale'
```

Every fact has a staleness date. lore flags facts that are past their expiry so you don't act on outdated information. No other tool does this.

---

## Commands

| Command | What it does |
|---|---|
| `lore init` | Set up ~/.lore/ directory |
| `lore learn "..."` | Capture a reusable learning |
| `lore fact "..."` | Capture a fact (auto-expires in 30 days) |
| `lore decision "..." --why "..."` | Capture a decision with full reasoning trace |
| `lore feedback "..."` | Capture a preference (applies globally) |
| `lore ref "..."` | Capture a reference to external info |
| `lore search "query"` | Search across all knowledge |
| `lore compile <project>` | Synthesize entries into a CLAUDE.md article |
| `lore status` | See what's captured, what's stale |
| `lore serve` | Start the MCP server (Claude Code auto-capture) |
| `lore install` | Print Claude Code integration instructions |
| `lore demo` | Generate sample entries to try it out |

## How it stores knowledge

```
~/.lore/
├── entries/              # Raw captures (JSONL, append-only, git-friendly)
│   ├── myapp.jsonl       # One file per project
│   ├── backend.jsonl
│   └── _global.jsonl     # Feedback and preferences
└── compiled/             # LLM-synthesized articles
    ├── myapp.md          # Auto-generated CLAUDE.md
    └── backend.md
```

- **JSONL** — one JSON object per line. Append-only. Works with `grep`, `jq`, `git diff`.
- **Git-friendly** — commit your `~/.lore/` directory. Knowledge is version-controlled.
- **No database** — just files. Move them, back them up, delete them. No lock-in.

## Comparison

| Tool | Auto-capture | Stores WHY | Compiles | Stale detection | Local-first | CLI |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| Obsidian | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ |
| Notion AI | ✗ | ✗ | partial | ✗ | ✗ | ✗ |
| Fabric | ✗ | ✗ | one-shot | ✗ | ✓ | ✓ |
| Khoj | ✗ | ✗ | ✗ | ✗ | hybrid | ✗ |
| Rewind | ✓ (screen) | ✗ | partial | ✗ | partial | ✗ |
| CLAUDE.md | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ |
| **lore** | **✓ (MCP)** | **✓** | **✓** | **✓** | **✓** | **✓** |

---

## Prerequisites

- **Python 3.10+**
- **Anthropic API key** (optional — for LLM-powered compilation. Without it, lore compiles using structured templates, no AI needed)
- **Claude Code** (optional — for MCP auto-capture. Without it, lore works as a manual CLI tool)

## License

Apache License 2.0 — free for any use, including commercial. No telemetry. No phone-home. Your knowledge stays on your machine.

---

<div align="center">

**[Quick start](#quick-start)** · **[Commands](#commands)** · **[How it works](#how-lore-works)** · **[Why it's different](#what-makes-lore-different)**

</div>
