<p align="center">
  <img src="https://raw.githubusercontent.com/lore-kb/lore/main/docs/assets/banner.svg" alt="lore — your knowledge base has a compiler" width="100%">
</p>

<div align="center">

# lore

### *Your next 10x isn't a faster model. It's never re-discovering what you already know.*

The open-source knowledge compiler for AI coding sessions.

[![PyPI](https://img.shields.io/pypi/v/lore-kb)](https://pypi.org/project/lore-kb/)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue?logo=python&logoColor=white)](https://pypi.org/project/lore-kb/)
[![CI](https://github.com/lore-kb/lore/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/lore-kb/lore/actions/workflows/ci.yml?query=branch%3Amain)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Status](https://img.shields.io/badge/status-alpha-orange)](https://github.com/lore-kb/lore/releases)

</div>

---

## 60-second try

```bash
pip install lore-kb
lore init && lore demo
lore search "adapter"
lore compile demo && cat ~/.lore/compiled/demo.md
```

Captures six sample entries, searches across them, and compiles them into a CLAUDE.md-compatible article in under a minute.

> **Status:** v0.1.0 alpha — first public release (2026-04-23). See [releases](https://github.com/lore-kb/lore/releases) for changelog. Feedback welcome via [issues](https://github.com/lore-kb/lore/issues).

---

## Why lore exists

Every AI coding session generates knowledge. Today, 99% of it is thrown away.

- You spend 2 hours figuring out a tricky workaround. Close the terminal. Gone.
- Three weeks later, same problem, new session. Claude has no memory. You re-discover it.
- You maintain CLAUDE.md files by hand — but who actually updates them?
- You keep terminal windows open for **a week** because closing them loses context.

> *"Each session is now 1M token context. You keep prompting and developing for hours, sometimes days. Having this searchable would be the real magic."*
> — early user, 2026-04

**lore captures knowledge from your AI coding sessions — facts, decisions, learnings — and compiles them into a searchable, version-controlled knowledge base.** It works two ways: **automatically** via an MCP server that Claude Code calls during conversation (zero friction), or **manually** via CLI when you want to capture something explicitly. Knowledge persists across sessions, is searchable, and compiles into clean CLAUDE.md-compatible articles.

<p align="center"><code>You work. lore remembers.</code></p>

Current workarounds are all manual and fragile: custom `/learn` commands, copy-pasting chats, sending agents to re-read entire repos, Obsidian + MCP, session hooks. Everyone is building the same hacky solution independently. lore replaces all of that with one tool.

---

## What makes lore different

| | Auto-capture | Stores WHY | Compiles articles | Stale detection | Local-first | CLI-first |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| **Obsidian** | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ |
| **Notion AI** | ✗ | ✗ | partial | ✗ | ✗ | ✗ |
| **Fabric** | ✗ | ✗ | one-shot | ✗ | ✓ | ✓ |
| **Khoj** | ✗ | ✗ | ✗ | ✗ | hybrid | ✗ |
| **Rewind** | ✓ (screen) | ✗ | partial | ✗ | partial | ✗ |
| **CLAUDE.md** | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ |
| **lore** | **✓ (MCP)** | **✓** | **✓** | **✓** | **✓** | **✓** |

**The gap:** every tool either requires manual capture (which people skip) or captures everything without structure (which is noise). Nothing automatically captures **structured knowledge** from AI coding sessions and **compiles** it into something useful.

---

## Features

- **Auto-capture via MCP** — Claude Code calls lore during conversation. You never type `lore` anything. Knowledge flows in as a side effect of working.
- **Decision traces** — not just *what* you decided, but *why*, *what you tried first*, *why it failed*, and *what happened after*. Six months later, the full context is still there.
- **LLM compiler** — takes 50 raw entries and produces one 150-line article. CLAUDE.md-compatible. Under the 200-line budget power users maintain. Auto-generated.
- **Cross-session search** — structured search that knows types (fact vs decision vs learning), projects, time, and outcomes. Not grep — intelligence.
- **Stale detection** — facts expire after 30 days by default. `lore status` flags what needs re-verification. No more acting on outdated information.
- **Local-first** — JSONL files on disk. No database. No cloud. No telemetry. No phone-home. Git-friendly. Your knowledge stays on your machine.

---

## How it works

```
┌─────────────────────────────────────────────────────────────┐
│                     YOUR WORK SESSION                       │
│                                                             │
│  You ↔ Claude Code (normal conversation)                    │
│         │                                                   │
│         ├─ detects a fact ──────→ lore_capture (automatic)  │
│         ├─ makes a decision ───→ lore_capture (automatic)   │
│         └─ receives feedback ──→ lore_capture (automatic)   │
│                                                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  ~/.lore/   │
                    │  entries/   │  JSONL (append-only, git-friendly)
                    │  *.jsonl    │
                    └──────┬──────┘
                           │
                     lore compile
                           │
                    ┌──────▼──────┐
                    │  compiled/  │
                    │  project.md │  CLAUDE.md-compatible article
                    └─────────────┘
```

### What gets captured

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

Not just **what** — but **why**, **what was tried first**, **why it failed**, and **what happened**. This is a decision trace. When future-you asks "why don't we use PostgreSQL for sessions?" the answer is already there.

### What gets compiled

```markdown
# api

## Key Decisions
- **Use Redis for sessions**
  - Why: PostgreSQL advisory locks deadlocked under load
  - Outcome: Redis handles 10x the load, no deadlocks

## Known Pitfalls
- pg_advisory_lock deadlocks at >50 concurrent connections

## Current State
- API rate limit is 100 req/min per key

## Rules
- Always run tests before committing
```

Under 200 lines. Only the relevant stuff. Stale facts excluded. The AI reads this at the start of every session.

---

## Quick Start

### Install

```bash
pip install lore-kb
```

Python 3.10+. Optional: set `ANTHROPIC_API_KEY` for LLM-powered compilation (without it, lore compiles offline using structured templates).

### Capture your first knowledge

```bash
# A learning you want to remember
lore learn "iframe automation requires shadow DOM inspection" -p myproject

# A decision with full reasoning
lore decision "Use Redis for sessions" -p api \
  --why "PostgreSQL advisory locks deadlocked under load" \
  --tried-first "pg_advisory_lock with retry loop" \
  --failed-because "Deadlocks at >50 concurrent connections" \
  --outcome "Redis handles 10x the load, no deadlocks"

# A fact (auto-expires in 30 days)
lore fact "API rate limit is 100 req/min per key" -p backend

# A rule (applies across all projects)
lore feedback "Always run tests before committing"
```

### Search past knowledge

```bash
lore search "rate limit"
lore search --type decision --project api
lore search "iframe"
```

### Compile into an article

```bash
lore compile myproject
# → ~/.lore/compiled/myproject.md (142 lines, CLAUDE.md-compatible)
```

---

## Connect to Claude Code

lore ships as an MCP server. After setup, Claude captures knowledge **automatically** during every conversation.

```bash
lore install
```

This prints the config to add to your Claude Code settings. After that, Claude has three tools:

| MCP Tool | What Claude does with it |
|---|---|
| `lore_capture` | Stores a fact, decision, learning, or feedback **proactively** during conversation |
| `lore_search` | Finds relevant knowledge from past sessions when context is needed |
| `lore_context` | Loads the compiled project summary at the start of a conversation |

You never type anything. Claude calls these tools as a side effect of working with you.

---

## Commands

| Command | What it does |
|---|---|
| `lore init` | Set up `~/.lore/` directory |
| `lore demo` | Generate sample entries to try it out |
| `lore learn "..."` | Capture a reusable learning |
| `lore fact "..."` | Capture a fact (auto-expires in 30 days) |
| `lore decision "..." --why "..."` | Capture a decision with full reasoning trace |
| `lore feedback "..."` | Capture a rule or preference (applies globally) |
| `lore ref "..."` | Capture a reference to external info |
| `lore search "query"` | Search across all captured knowledge |
| `lore compile <project>` | Synthesize entries into a CLAUDE.md-compatible article |
| `lore status` | See what's captured, what's stale |
| `lore serve` | Start the MCP server (for Claude Code auto-capture) |
| `lore install` | Print Claude Code integration instructions |

---

## Storage

```
~/.lore/
├── entries/              # Raw captures (JSONL, append-only)
│   ├── myapp.jsonl       # One file per project
│   ├── backend.jsonl
│   └── _global.jsonl     # Feedback and preferences
└── compiled/             # LLM-synthesized articles
    ├── myapp.md          # Auto-generated, CLAUDE.md-compatible
    └── backend.md
```

- **JSONL** — one JSON object per line. `grep`, `jq`, `git diff` all work.
- **Git-friendly** — commit `~/.lore/`. Your knowledge is version-controlled.
- **No database** — just files. Move them, back them up, sync them. Zero lock-in.

---

## Works with your existing knowledge base

Already have Obsidian, a wiki, CLAUDE.md files, or a custom KB? lore doesn't replace any of that. It sits **underneath** as the capture + compilation engine.

### The three-layer model

```
Layer 1: lore entries        ← raw facts/decisions (captured automatically)
                ↓
Layer 2: compiled summary    ← LLM-synthesized, ~150 lines (AI reads this)
                ↓
Layer 3: your full articles  ← human-maintained, has the story + context (you read this)
```

**Layer 2 doesn't replace Layer 3.** The compiled summary is what the AI reads at session start — concise, current, actionable. Your full articles keep the narrative: why decisions were made, what was tried, the chronological story of how a project evolved.

### Before and after

| | Before lore | With lore |
|---|---|---|
| **Capture** | Stop working, open notes, write something | Automatic — lore captures during conversation |
| **AI context** | You maintain CLAUDE.md by hand | lore compiles a summary the AI reads automatically |
| **Your articles** | You manually update everything | Lighter updates — just add new narrative. lore handles the summary. |
| **Search** | Open Obsidian, Cmd+F, browse pages | `lore search "query"` — instant, cross-project, structured |
| **Staleness** | Nobody knows if old notes are still accurate | `lore status` flags facts older than 30 days |

### What lore does NOT replace

- **Your Obsidian vault** — lore's compiled markdown works as an Obsidian vault. Open `~/.lore/compiled/` alongside your existing vault.
- **Your full articles** — session notes, decision narratives, historical context stay yours. lore supplements, not supplants.
- **Your domain knowledge** — concepts, frameworks, reference material that isn't project-specific. lore is for project knowledge, not encyclopedias.
- **Your raw source docs** — PDFs, screenshots, email threads. lore captures from conversations, not files.

---

## Contributing

lore is early and we need help with:

- **MCP integrations** — Cursor, Codex, OpenCode support
- **Compile patterns** — custom templates for different article styles
- **Offline compilation** — better structured templates without LLM
- **Testing** — more edge-case coverage
- **Docs** — tutorials, blog posts, translations

See [CONTRIBUTING.md](CONTRIBUTING.md) and the [issues](https://github.com/lore-kb/lore/issues) for specific tasks.

---

## License

Apache License 2.0 — free for any use, including commercial. **No telemetry. No phone-home. Your knowledge stays on your machine.**

---

Built by [Swathi](https://github.com/SwathiMystery) because she kept closing terminals and losing a week's context.

<div align="center">

**[Star on GitHub](https://github.com/lore-kb/lore)** · **`pip install lore-kb`** · **[Issues](https://github.com/lore-kb/lore/issues)**

</div>
