from __future__ import annotations

from .memory_lancedb import MemoryLanceDBAdapter


class MiladyMemoryAdapter(MemoryLanceDBAdapter):
    """Milady adapter for canonical memory tools over Gateway invoke."""

    name = "milady-memory"

    def initialize(self, config: dict) -> None:
        merged = dict(config)
        merged.setdefault("gateway_namespace", "milady")
        super().initialize(merged)
