"""Application boundaries for the in-memory evaluation workspace."""
import unittest
from datetime import datetime, timezone

from intelligence_core.contracts import CollectionContext, CoreId, SourceRecord, SourceReference

from intelligence_mcp.limits import InputLimitError, bounded_bytes, bounded_text
from intelligence_mcp.server import (
    MAX_SUMMARY_BYTES,
    MAX_SYNTHETIC_BYTES,
    _ids,
)
from intelligence_mcp.workspace import MAX_PROJECT_ENTITIES, Workspace


class InputLimitsTest(unittest.TestCase):
    def test_utf8_boundaries(self):
        for limit in (MAX_SUMMARY_BYTES, MAX_SYNTHETIC_BYTES):
            exact = "é" * (limit // 2)
            self.assertEqual(len(bounded_bytes(exact, limit)), limit)
            with self.assertRaises(InputLimitError):
                bounded_bytes(exact + "a", limit)
        with self.assertRaises(InputLimitError):
            bounded_text("a" * (MAX_SUMMARY_BYTES + 1), MAX_SUMMARY_BYTES)
        with self.assertRaises(InputLimitError):
            _ids(["s"] * (MAX_PROJECT_ENTITIES + 1))

    def test_full_workspace_rejects_next_entity_and_reset_releases_capacity(self):
        state = Workspace()
        state.initialize("first")
        ref = SourceReference("synthetic_document", "demo", "fixture")
        context = CollectionContext(datetime.now(timezone.utc), "fixture", "1")
        for i in range(MAX_PROJECT_ENTITIES):
            state.add_source(SourceRecord(CoreId(f"s{i}"), ref, context))
        overflow = SourceRecord(CoreId("extra"), ref, context)
        with self.assertRaises(InputLimitError):
            state.add_source(overflow)
        self.assertIsNone(state.get("extra"))
        self.assertEqual(state.counts()["sources"], MAX_PROJECT_ENTITIES)
        state.reset("second", "first")
        self.assertEqual(state.add_source(overflow), overflow)
