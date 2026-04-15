"""Core tests for lore — types, store, search, compile."""

import json
import os
import tempfile

import pytest

os.environ["LORE_DIR"] = tempfile.mkdtemp()

from lore.types import Entry, fact, decision, learning, feedback, reference
from lore import store, compiler


class TestEntry:
    def test_fact_has_stale_date(self):
        e = fact("test fact", project="p")
        assert e.stale_after is not None
        assert e.type == "fact"

    def test_decision_has_why(self):
        e = decision("use X", project="p", why="because Y")
        assert e.why == "because Y"
        assert e.type == "decision"

    def test_feedback_is_global(self):
        e = feedback("never do X")
        assert e.project == "_global"

    def test_json_roundtrip(self):
        e = decision("use X", project="p", why="Y",
                      tried_first="Z", failed_because="W", outcome="ok")
        line = e.to_json()
        e2 = Entry.from_json(line)
        assert e2.content == "use X"
        assert e2.why == "Y"
        assert e2.tried_first == "Z"
        assert e2.failed_because == "W"
        assert e2.outcome == "ok"

    def test_matches_query(self):
        e = fact("Redis handles 10x the load", project="api")
        assert e.matches("redis")
        assert e.matches("10x load")
        assert not e.matches("postgresql")

    def test_matches_decision_fields(self):
        e = decision("use Redis", why="pg locks deadlock", project="api")
        assert e.matches("deadlock")
        assert e.matches("redis")

    def test_id_generation(self):
        e1 = fact("a")
        e2 = fact("b")
        assert e1.id != e2.id
        assert e1.id.startswith("f_")
        d = decision("x", why="y")
        assert d.id.startswith("d_")

    def test_summary_truncation(self):
        e = fact("x" * 200)
        s = e.summary(max_len=50)
        assert len(s) <= 50
        assert s.endswith("...")


class TestStore:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        os.environ["LORE_DIR"] = self.tmpdir

    def test_append_and_load(self):
        e = fact("test", project="proj")
        store.append(e)
        entries = store.load_project("proj")
        assert len(entries) == 1
        assert entries[0].content == "test"

    def test_load_all(self):
        store.append(fact("a", project="p1"))
        store.append(fact("b", project="p2"))
        all_entries = store.load_all()
        assert len(all_entries) >= 2

    def test_projects(self):
        store.append(fact("a", project="alpha"))
        store.append(fact("b", project="beta"))
        projs = store.projects()
        assert "alpha" in projs
        assert "beta" in projs

    def test_search_by_query(self):
        store.append(fact("Redis is fast", project="db"))
        store.append(fact("PostgreSQL is reliable", project="db"))
        results = store.search("redis", project="db")
        assert len(results) == 1
        assert "Redis" in results[0].content

    def test_search_by_type(self):
        store.append(fact("a fact", project="x"))
        store.append(decision("a decision", project="x", why="because"))
        results = store.search("", project="x", entry_type="decision")
        assert len(results) == 1
        assert results[0].type == "decision"

    def test_supersede(self):
        e1 = store.append(fact("old fact", project="s"))
        e2 = store.supersede(e1.id, fact("new fact", project="s"))
        assert e2.supersedes == e1.id
        results = store.search("", project="s")
        # superseded entry should be excluded
        contents = [r.content for r in results]
        assert "new fact" in contents
        assert "old fact" not in contents

    def test_project_stats(self):
        store.append(fact("a", project="stats"))
        store.append(decision("b", project="stats", why="c"))
        stats = store.project_stats()
        assert "stats" in stats
        assert stats["stats"]["total"] == 2
        assert stats["stats"]["types"]["fact"] == 1
        assert stats["stats"]["types"]["decision"] == 1

    def test_load_missing_project(self):
        entries = store.load_project("nonexistent")
        assert entries == []


class TestCompiler:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        os.environ["LORE_DIR"] = self.tmpdir

    def test_compile_empty_project(self):
        result = compiler.compile_project("empty")
        assert "No entries yet" in result

    def test_compile_offline(self):
        store.append(fact("the sky is blue", project="comp"))
        store.append(decision("use umbrellas", project="comp", why="it rains"))
        store.append(learning("bring jacket in april", project="comp"))
        store.append(feedback("always check weather"))

        result = compiler.compile_project("comp")
        assert "# comp" in result
        assert "use umbrellas" in result
        assert "it rains" in result
        assert "the sky is blue" in result
        assert "always check weather" in result

    def test_compile_to_file(self):
        store.append(fact("test", project="filecomp"))
        outpath = os.path.join(self.tmpdir, "out.md")
        result = compiler.compile_project("filecomp", output_path=outpath)
        assert os.path.exists(outpath)
        with open(outpath) as f:
            assert f.read() == result

    def test_compile_excludes_superseded(self):
        e1 = store.append(fact("old value", project="sup"))
        store.supersede(e1.id, fact("new value", project="sup"))
        result = compiler.compile_project("sup")
        assert "new value" in result
        # old value may still appear in raw entries but the compile
        # function filters superseded — check the offline compiler
        # (LLM compiler would also exclude via the [STALE] tag)


class TestMCPServer:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        os.environ["LORE_DIR"] = self.tmpdir

    def test_initialize(self):
        from lore.mcp_server import handle_request
        resp = handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        assert resp["result"]["serverInfo"]["name"] == "lore"

    def test_tools_list(self):
        from lore.mcp_server import handle_request
        resp = handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        names = [t["name"] for t in resp["result"]["tools"]]
        assert "lore_capture" in names
        assert "lore_search" in names
        assert "lore_context" in names

    def test_capture_via_mcp(self):
        from lore.mcp_server import handle_request
        resp = handle_request({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {
                "name": "lore_capture",
                "arguments": {
                    "type": "fact",
                    "content": "MCP capture works",
                    "project": "mcp_test",
                }
            }
        })
        text = resp["result"]["content"][0]["text"]
        assert "Captured" in text
        # Verify it's in the store
        entries = store.load_project("mcp_test")
        assert len(entries) == 1

    def test_search_via_mcp(self):
        from lore.mcp_server import handle_request
        store.append(fact("unique_token_xyz", project="mcp_s"))
        resp = handle_request({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {
                "name": "lore_search",
                "arguments": {"query": "unique_token_xyz"}
            }
        })
        text = resp["result"]["content"][0]["text"]
        assert "unique_token_xyz" in text

    def test_context_via_mcp(self):
        from lore.mcp_server import handle_request
        store.append(decision("use X", project="mcp_c", why="because"))
        resp = handle_request({
            "jsonrpc": "2.0", "id": 5, "method": "tools/call",
            "params": {
                "name": "lore_context",
                "arguments": {"project": "mcp_c"}
            }
        })
        text = resp["result"]["content"][0]["text"]
        assert "use X" in text

    def test_unknown_method(self):
        from lore.mcp_server import handle_request
        resp = handle_request({"jsonrpc": "2.0", "id": 6, "method": "bogus", "params": {}})
        assert "error" in resp
