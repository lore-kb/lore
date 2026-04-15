# Contributing to lore

Thanks for your interest. lore is early — contributions are welcome.

## What we need most

1. **MCP integrations** — Cursor, Codex, OpenCode support
2. **Compile patterns** — custom templates for different article styles
3. **Offline compilation** — better structured templates without LLM
4. **Tests** — edge cases, integration tests, MCP server tests
5. **Docs** — tutorials, blog posts, translations

## Development

```bash
git clone https://github.com/lore-kb/lore
cd lore
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -v
```

## Code style

We use [ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
pip install ruff
ruff check src/
ruff format src/
```

## Pull requests

- Branch off `main`. One logical change per PR.
- Add tests for new functionality.
- Update the README if you add commands or change behavior.
- Write a real commit message — explain *why*, not just *what*.

## Architecture

```
src/lore/
├── types.py         # Entry dataclass with decision traces
├── store.py         # JSONL read/write/search
├── compiler.py      # LLM synthesis → CLAUDE.md articles
├── mcp_server.py    # MCP server for Claude Code auto-capture
└── cli.py           # Click-based CLI
```

The whole thing is ~600 lines. Read it in 20 minutes.

## License

By contributing you agree your work is licensed under Apache 2.0.
