"""Verify declared authorship on tool responses and later resource reads."""

import json
import sys
import unittest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class AttributionTest(unittest.IsolatedAsyncioTestCase):
    async def test_declarations_are_required_preserved_and_not_verified(self):
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "intelligence_mcp.server"]
        )
        async with stdio_client(params) as streams, ClientSession(*streams) as session:
            await session.initialize()
            await session.call_tool("initialize_project", {"project_id": "fixture"})
            for kind, args, decl in [
                (
                    "item",
                    {"item_id": "i", "normalized_content": "summary", "evidence_ids": ["e"]},
                    {"producer_kind": "human", "actor_ref": "reviewer-A"},
                ),
                (
                    "finding",
                    {
                        "finding_id": "f",
                        "statement": "finding",
                        "supporting_item_ids": ["i"],
                        "supporting_evidence_ids": ["e"],
                    },
                    {
                        "producer_kind": "ai_assisted",
                        "provider": "fixture-provider",
                        "model": "fixture-model",
                    },
                ),
                (
                    "insight",
                    {
                        "insight_id": "n",
                        "statement": "insight",
                        "supporting_finding_ids": ["f"],
                        "supporting_evidence_ids": ["e"],
                    },
                    {"producer_kind": "deterministic"},
                ),
            ]:
                name = "register_" + kind
                for invalid in (
                    {},
                    {"producer_kind": "human"},
                    {"producer_kind": "ai_assisted"},
                    {"producer_kind": "unreported"},
                    {"producer_kind": "human", "actor_ref": "a", "model": "invalid"},
                    {"producer_kind": "ai_assisted", "provider": "p", "model": "é" * 129},
                ):
                    rejected = await session.call_tool(name, args | invalid)
                    self.assertTrue(rejected.is_error)
                result = await session.call_tool(name, args | decl)
                self.assertFalse(result.is_error)
                producer = result.structured_content["producer"]
                self.assertEqual(producer["kind"], decl["producer_kind"])
                self.assertEqual(producer["attribution"], "caller_declared")
                for key in ("actor_ref", "provider", "model"):
                    self.assertEqual(producer[key], decl.get(key))
                for resource in ("trace", "entity"):
                    uri = "ratiqora://" + resource + "/" + result.structured_content["id"]
                    read = await session.read_resource(uri)
                    self.assertEqual(json.loads(read.contents[0].text)["producer"], producer)
