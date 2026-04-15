"""Entry types for lore's knowledge store.

Each entry represents one atomic piece of knowledge. The key insight
is that decisions carry WHY (reasoning + what was tried first + outcome),
not just WHAT. This is what makes lore different from a note-taking app.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Optional
import json
import uuid


@dataclass
class Entry:
    """A single knowledge entry in the lore store."""

    id: str = ""
    type: str = ""  # fact | decision | learning | feedback | reference
    project: str = ""  # project name (e.g., "procuracy", "jumkey")
    content: str = ""  # the knowledge itself

    # Decision trace fields (what makes lore unique)
    why: Optional[str] = None  # reasoning behind a decision
    tried_first: Optional[str] = None  # what was tried before this
    failed_because: Optional[str] = None  # why the first approach failed
    outcome: Optional[str] = None  # what happened after the decision

    # Metadata
    tags: list[str] = field(default_factory=list)
    source: Optional[str] = None  # conversation/context where captured
    ts: str = ""  # ISO timestamp
    verified: Optional[str] = None  # last verified date
    stale_after: Optional[str] = None  # when to flag for re-verification
    supersedes: Optional[str] = None  # ID of entry this replaces

    def __post_init__(self):
        if not self.id:
            prefix = self.type[0] if self.type else "e"
            self.id = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        if not self.ts:
            self.ts = datetime.now().isoformat()
        if not self.stale_after and self.type == "fact":
            # Facts default to 30-day staleness
            stale = datetime.now() + timedelta(days=30)
            self.stale_after = stale.strftime("%Y-%m-%d")

    def to_json(self) -> str:
        """Serialize to a single JSON line (for JSONL storage)."""
        d = {k: v for k, v in asdict(self).items() if v is not None and v != [] and v != ""}
        # Always include id, type, project, content, ts
        for key in ("id", "type", "project", "content", "ts"):
            if key not in d:
                d[key] = getattr(self, key)
        return json.dumps(d, ensure_ascii=False)

    @classmethod
    def from_json(cls, line: str) -> "Entry":
        """Deserialize from a JSON line."""
        d = json.loads(line)
        # Handle tags as list
        if "tags" in d and isinstance(d["tags"], str):
            d["tags"] = d["tags"].split(",")
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def matches(self, query: str) -> bool:
        """Check if this entry matches a search query (case-insensitive)."""
        q = query.lower()
        searchable = " ".join(filter(None, [
            self.content, self.why, self.tried_first,
            self.failed_because, self.outcome,
            self.project, " ".join(self.tags),
        ])).lower()
        # All query words must appear somewhere
        return all(word in searchable for word in q.split())

    @property
    def is_stale(self) -> bool:
        """Check if this entry is past its stale_after date."""
        if not self.stale_after:
            return False
        try:
            return datetime.now().strftime("%Y-%m-%d") > self.stale_after
        except ValueError:
            return False

    @property
    def age_days(self) -> int:
        """Days since this entry was created."""
        try:
            created = datetime.fromisoformat(self.ts)
            return (datetime.now() - created).days
        except (ValueError, TypeError):
            return 0

    def summary(self, max_len: int = 80) -> str:
        """One-line summary for search results."""
        text = self.content[:max_len]
        if len(self.content) > max_len:
            text = text[:max_len - 3] + "..."
        return text


def fact(content: str, project: str = "", **kwargs) -> Entry:
    """Create a fact entry."""
    return Entry(type="fact", content=content, project=project, **kwargs)


def decision(content: str, project: str = "", why: str = "", **kwargs) -> Entry:
    """Create a decision entry with reasoning."""
    return Entry(type="decision", content=content, project=project, why=why, **kwargs)


def learning(content: str, project: str = "", **kwargs) -> Entry:
    """Create a learning entry (reusable insight)."""
    return Entry(type="learning", content=content, project=project, **kwargs)


def feedback(content: str, **kwargs) -> Entry:
    """Create a feedback entry (user preference/rule). Always global."""
    return Entry(type="feedback", content=content, project="_global", **kwargs)


def reference(content: str, project: str = "", **kwargs) -> Entry:
    """Create a reference entry (pointer to external info)."""
    return Entry(type="reference", content=content, project=project, **kwargs)
