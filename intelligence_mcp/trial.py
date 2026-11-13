"""Deterministic local alpha trial driven through a real MCP client."""

import asyncio
import json
import sys
from hashlib import sha256

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def _call(
    session: ClientSession,
    name: str,
    arguments: dict[str, object],
) -> dict[str, object]:
    result = await session.call_tool(name, arguments)
    if result.is_error or result.structured_content is None:
        raise RuntimeError(f"{name} failed")
    if name.startswith("register_") and result.structured_content.get("contract_version") != "2":
        raise RuntimeError("trial entity contract version mismatch")
    return result.structured_content


async def run_trial() -> dict[str, object]:
    """Run one synthetic source-to-insight project and return a safe summary."""
    raw_content = bytes.fromhex(
        "73796e7468657469632d616c7068612d65766964656e6365"
    ).decode("ascii")
    expected_integrity = f"sha256:{sha256(raw_content.encode('utf-8')).hexdigest()}"
    parameters = StdioServerParameters(
        command=sys.executable,
        args=(["-I"] if sys.flags.isolated else []) + ["-m", "intelligence_mcp.server"],
    )
    async with stdio_client(parameters) as streams:  # noqa: SIM117
        async with ClientSession(*streams) as session:
            await session.initialize()
            await _call(
                session,
                "initialize_project",
                {
                    "project_id": "synthetic-independent-project-v1",
                    "display_name": "Synthetic Independent Project",
                },
            )
            await _call(
                session,
                "register_source",
                {
                    "source_id": "trial-source-1",
                    "source_kind": "synthetic_document",
                    "source_instance": "local-alpha-trial",
                    "external_reference": "synthetic://project-brief",
                    "collected_at": "2026-01-01T00:00:00+00:00",
                },
            )
            evidence = await _call(
                session,
                "register_evidence",
                {
                    "evidence_id": "trial-evidence-1",
                    "source_record_id": "trial-source-1",
                    "synthetic_content": raw_content,
                    "expected_integrity": expected_integrity,
                    "content_mode": "model_supplied_synthetic",
                },
            )
            if raw_content in json.dumps(evidence, sort_keys=True):
                raise RuntimeError("RawEvidence content escaped the server boundary")
            if evidence["integrity"] != expected_integrity:
                raise RuntimeError("RawEvidence integrity verification failed")
            if evidence["evidence_origin"] != "model_supplied_synthetic":
                raise RuntimeError("RawEvidence origin was not explicit")
            if evidence["verbatim_source_capture"] is not False:
                raise RuntimeError("model-supplied evidence was labeled verbatim")
            await _call(
                session,
                "register_item",
                {
                    "item_id": "trial-item-1",
                    "normalized_content": "The synthetic project has a bounded objective.",
                    "evidence_ids": ["trial-evidence-1"],
                },
            )
            await _call(
                session,
                "register_finding",
                {
                    "finding_id": "trial-finding-1",
                    "statement": "The project objective is explicitly traceable.",
                    "supporting_item_ids": ["trial-item-1"],
                    "supporting_evidence_ids": ["trial-evidence-1"],
                },
            )
            await _call(
                session,
                "register_insight",
                {
                    "insight_id": "trial-insight-1",
                    "statement": "The project can be evaluated through a closed evidence trace.",
                    "supporting_finding_ids": ["trial-finding-1"],
                    "supporting_evidence_ids": ["trial-evidence-1"],
                },
            )
            validation = await _call(session, "validate_project", {})

    return {
        "scenario_id": "synthetic-independent-project-v1",
        "valid": validation["valid"],
        "project_id": validation["project_id"],
        "counts": validation["counts"],
        "trace_ids": {
            "source": "trial-source-1",
            "evidence": "trial-evidence-1",
            "item": "trial-item-1",
            "finding": "trial-finding-1",
            "insight": "trial-insight-1",
        },
    }


def main() -> None:
    print(json.dumps(asyncio.run(run_trial()), sort_keys=True))


if __name__ == "__main__":
    main()
