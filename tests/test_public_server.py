"""Exercise the source checkout over real stdio, with only public dependencies."""
import json
import sys
import unittest
from hashlib import sha256

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from intelligence_mcp.trial import run_trial


class PublicServerTest(unittest.IsolatedAsyncioTestCase):
    async def test_source_to_insight_trial(self):
        report = await run_trial()
        self.assertIs(report["valid"], True)
        self.assertEqual(report["counts"], dict.fromkeys(
            ("sources", "evidence", "items", "findings", "insights"), 1
        ))

    async def test_evidence_view_and_broken_reference(self):
        params = StdioServerParameters(command=sys.executable, args=["-m", "intelligence_mcp.server"])
        async with stdio_client(params) as streams, ClientSession(*streams) as session:
            await session.initialize()

            async def call(name, **args):
                response = await session.call_tool(name, args)
                self.assertFalse(response.is_error)
                return response.structured_content

            await call("initialize_project", project_id="demo")
            await call("register_source", source_id="s1", source_kind="synthetic_document",
                       source_instance="demo", external_reference="fictional fixture",
                       collected_at="2026-01-01T00:00:00Z")
            sample = "fixture content for public test"
            await call("register_evidence", evidence_id="e1", source_record_id="s1",
                       synthetic_content=sample, content_mode="model_supplied_synthetic",
                       expected_integrity="sha256:" + sha256(sample.encode()).hexdigest())
            for resource in ("entity", "trace"):
                result = await session.read_resource(f"ratiqora://{resource}/e1")
                view = json.loads(result.contents[0].text)
                self.assertIs(view["content_redacted"], True)
                self.assertEqual(view["source_record_id"], "s1")
                self.assertNotIn(sample, result.model_dump_json())
            await call("register_item", item_id="i1", normalized_content="summary",
                       evidence_ids=["missing"], producer_kind="deterministic")
            invalid = await session.call_tool("validate_project", {})
            self.assertTrue(invalid.is_error)
