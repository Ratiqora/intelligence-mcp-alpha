"""Check byte boundaries, safe errors and unchanged state through stdio."""

import sys
import unittest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MetadataTest(unittest.IsolatedAsyncioTestCase):
    async def test_utf8_boundaries_and_atomic_rejection(self):
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "intelligence_mcp.server"]
        )
        async with stdio_client(params) as streams, ClientSession(*streams) as session:
            await session.initialize()

            async def rejected(name, args):
                result = await session.call_tool(name, args)
                self.assertTrue(result.is_error)
                self.assertIn("RQ-LIMIT-001", result.model_dump_json())
                self.assertNotIn("éé", result.model_dump_json())

            identifier = "é" * 128
            await rejected("initialize_project", {"project_id": identifier + "a"})
            init = await session.call_tool("initialize_project", {"project_id": identifier})
            self.assertEqual(init.structured_content["project_id"], identifier)
            reference = "é" * 2048
            args = {
                "source_id": "s1",
                "source_kind": "synthetic_document",
                "source_instance": "test",
                "collector_method": "manual",
                "external_reference": reference,
                "collected_at": "2026-01-01T00:00:00Z",
            }
            for field, value in (
                ("external_reference", reference + "a"),
                ("source_id", identifier + "a"),
                ("collector_method", identifier + "a"),
                ("source_instance", identifier + "a"),
                ("collected_at", "2" * 65),
            ):
                await rejected("register_source", args | {field: value})
            source = await session.call_tool("register_source", args)
            self.assertEqual(source.structured_content["source"]["external_reference"], reference)
            await rejected(
                "register_item",
                {"item_id": "i1", "normalized_content": "test", "evidence_ids": [identifier + "a"]},
            )
            for field in ("display_name", "expected_current_project_id"):
                await rejected(
                    "reset_project",
                    {"project_id": "next", "expected_current_project_id": identifier}
                    | {field: identifier + "a"},
                )
            report = (await session.call_tool("get_support_report", {})).structured_content
            self.assertEqual(
                report["project"]["counts"],
                {
                    "sources": 1,
                    "evidence": 0,
                    "items": 0,
                    "findings": 0,
                    "insights": 0,
                },
            )
            self.assertNotIn("éé", str(report))
