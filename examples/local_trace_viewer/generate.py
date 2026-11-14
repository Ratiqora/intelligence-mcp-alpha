"""Generate a synthetic trace viewer or decision brief through installed MCP."""

import argparse
import asyncio
import hashlib
import json
import os
import secrets
import sys
from pathlib import Path
from threading import Thread

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

TITLES = {
    "SourceRecord": "Synthetic source",
    "RawEvidence": "Synthetic evidence",
    "IntelligenceItem": "Sample observation",
    "Finding": "Sample finding",
    "Insight": "Sample insight",
}


def project_node(value: dict[str, object], title: str) -> dict[str, object]:
    """Copy an explicit UI allowlist; never export an evidence object wholesale."""
    kind = value["entity_type"]
    if kind not in TITLES or value.get("contract_version") != "2":
        raise ValueError("unsupported synthetic entity")
    result = {key: value[key] for key in ("id", "entity_type", "contract_version")}
    result["title"] = title
    if kind == "RawEvidence":
        if ("content" in value or value.get("content_redacted") is not True
                or value.get("evidence_origin") != "model_supplied_synthetic"):
            raise ValueError("evidence export boundary violated")
        for key in ("source_record_id", "integrity", "evidence_origin"):
            result[key] = value[key]
    elif kind == "SourceRecord":
        source = value["source"]
        if source["source_kind"] != "synthetic_document":
            raise ValueError("only synthetic sources are supported")
        for key in ("source_kind", "external_reference"):
            result[key] = source[key]
        result["collected_at"] = value["collection"]["collected_at"]
    else:
        keys = {
            "IntelligenceItem": ("normalized_content", "evidence_ids"),
            "Finding": ("statement", "supporting_item_ids", "supporting_evidence_ids"),
            "Insight": ("statement", "supporting_finding_ids", "supporting_evidence_ids"),
        }[kind]
        for key in keys:
            result[key] = value[key]
        result["producer_kind"] = value["producer"]["kind"]
    return result


def render_html(scenarios: list[dict[str, object]], template: str) -> str:
    data = json.dumps(scenarios, ensure_ascii=False)
    data = data.replace("<", r"\u003c").replace(">", r"\u003e").replace("&", r"\u0026")
    if template.count("__TRACE_DATA__") != 1:
        raise ValueError("invalid viewer template")
    return template.replace("__TRACE_DATA__", data)


UPLOAD_OBSERVATIONS = (
    "Uploading a 12 MB photo failed.",
    "Uploading another 12 MB photo succeeded.",
    "Uploading a 2 MB photo succeeded.",
)
UPLOAD_FINDING = "Two photos of the same size had different outcomes. The cause of the failure is still unknown."
UPLOAD_INSIGHT = "Before changing the upload size limit, compare file formats and error messages under the same conditions."


async def scenario(count: int, label: str, *, uploads: bool = False) -> dict[str, object]:
    payloads: list[str] = []
    nodes: list[dict[str, object]] = []
    captured: list[str] = []
    read_fd, write_fd = os.pipe()

    def drain() -> None:
        with os.fdopen(read_fd, encoding="utf-8") as reader:
            captured.append(reader.read())

    def check_private(text: str) -> None:
        if any(payload in text for payload in payloads):
            raise ValueError("synthetic content exposure; output suppressed")

    thread = Thread(target=drain, daemon=True)
    thread.start()
    parameters = StdioServerParameters(
        command=sys.executable, args=["-I", "-m", "intelligence_mcp.server"],
    )
    try:
        with os.fdopen(write_fd, "w", encoding="utf-8") as errlog:
            async with (
                stdio_client(parameters, errlog=errlog) as streams,
                ClientSession(*streams) as session,
            ):
                await session.initialize()

                async def call(name: str, arguments: dict[str, object]) -> dict[str, object]:
                    result = await session.call_tool(name, arguments)
                    check_private(str(result))
                    if result.is_error or result.structured_content is None:
                        raise ValueError("synthetic MCP call failed; output suppressed")
                    value = result.structured_content
                    if name.startswith("register_"):
                        kind = value["entity_type"]
                        title = TITLES[kind]
                        if kind != "Insight":
                            title += " " + str(len([n for n in nodes
                                                   if n["entity_type"] == kind]) + 1)
                        nodes.append(project_node(value, title))
                    return value

                await call("initialize_project", {"project_id": "trace-viewer-synthetic"})
                for index in range(count):
                    await call("register_source", {
                        "source_id": f"s{index}", "source_kind": "synthetic_document",
                        "source_instance": "local-trace-viewer",
                        "external_reference": f"synthetic://trace-viewer/{index}",
                        "collected_at": "2026-10-24T12:00:00+00:00",
                    })
                    payload = "synthetic-" + secrets.token_hex(32)
                    payloads.append(payload)
                    await call("register_evidence", {
                        "evidence_id": f"e{index}", "source_record_id": f"s{index}",
                        "synthetic_content": payload,
                        "expected_integrity": "sha256:" + hashlib.sha256(
                            payload.encode()).hexdigest(),
                        "content_mode": "model_supplied_synthetic",
                    })
                    await call("register_item", {
                        "item_id": f"i{index}",
                        "normalized_content": (
                            UPLOAD_OBSERVATIONS[index] if uploads
                            else "This observation was written for the demo."
                        ),
                        "evidence_ids": [f"e{index}"],
                    })
                findings = []
                for start in range(0, count, 3):
                    findings.append(f"f{start}")
                    await call("register_finding", {
                        "finding_id": f"f{start}",
                        "statement": (
                            UPLOAD_FINDING if uploads
                            else "This sample finding links to the observations and evidence below."
                        ),
                        "supporting_item_ids": [f"i{i}" for i in range(
                            start, min(start + 3, count))],
                        "supporting_evidence_ids": [f"e{i}" for i in range(
                            start, min(start + 3, count))],
                    })
                await call("register_insight", {
                    "insight_id": "result",
                    "statement": (
                        UPLOAD_INSIGHT if uploads
                        else "This sample insight shows how to follow the evidence trail."
                    ),
                    "supporting_finding_ids": findings,
                    "supporting_evidence_ids": [f"e{i}" for i in range(count)],
                })
                validation = await call("validate_project", {})
                expected = {"sources": count, "evidence": count, "items": count,
                            "findings": len(findings), "insights": 1}
                if validation.get("valid") is not True or validation["counts"] != expected:
                    raise ValueError("synthetic graph failed validation")
    finally:
        thread.join(timeout=10)
    if thread.is_alive():
        raise ValueError("stderr capture did not terminate")
    check_private("".join(captured))
    result = {"label": label, "counts": expected, "root_id": "result", "nodes": nodes}
    if uploads:
        result["id"] = "conflicting-uploads"
    check_private(json.dumps(result, ensure_ascii=False))
    return result


async def generate(output: Path, *, uploads: bool = False) -> None:
    scenarios = []
    for count, label in ((1, "Small · 1 evidence record"), (5, "Medium · 5 evidence records"),
                         (25, "Large · 25 evidence records")):
        scenarios.append(await asyncio.wait_for(scenario(count, label), timeout=90))
    if uploads:
        scenarios.append(await asyncio.wait_for(
            scenario(3, "Photo uploads · conflicting reports", uploads=True), timeout=90,
        ))
    template = Path(__file__).with_name("viewer.template.html").read_text(encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError("output already exists; do not overwrite")
    output.write_text(render_html(scenarios, template), encoding="utf-8")
    print(json.dumps({"viewer": "PASS", "synthetic_only": True, "scenarios": len(scenarios),
                      "evidence_counts": [1, 5, 25] + ([3] if uploads else [])}, sort_keys=True))


UPLOAD_REPORT_ROLES = (
    ("Supports the concern", "The failure is worth investigating."),
    (
        "Challenges the explanation",
        "A successful upload at the same size weakens a size-only explanation.",
    ),
    ("Adds context", "A smaller upload succeeded; it does not identify a reliable limit."),
)


def render_decision_brief(brief: dict[str, object]) -> str:
    """Follow the linked, redacted view. Evidence roles are editorial annotations."""
    nodes = {node["id"]: node for node in brief["nodes"]}
    insight = nodes[brief["root_id"]]
    finding_id, = insight["supporting_finding_ids"]
    finding = nodes[finding_id]
    observations = [nodes[item_id] for item_id in finding["supporting_item_ids"]]
    if tuple(item["normalized_content"] for item in observations) != UPLOAD_OBSERVATIONS:
        raise ValueError("unexpected observations")

    lines = [
        "# Decision brief: Photo upload limit",
        "",
        "Should the team lower the photo upload limit based on these reports?",
        "",
        "**Recommendation: Investigate the failure before lowering the limit.**",
        "",
        f"**Finding:** {finding['statement']}",
        "",
        f"**Trace:** `{insight['id']}` → `{finding_id}` → reports below.",
        "",
        "## Reports behind the finding",
        "",
        "| Role | Sample report | What it tells us | Trace |",
        "| --- | --- | --- | --- |",
    ]
    source_notes = []
    for item, (role, note) in zip(observations, UPLOAD_REPORT_ROLES, strict=True):
        evidence_id, = item["evidence_ids"]
        evidence = nodes[evidence_id]
        if evidence_id not in finding["supporting_evidence_ids"]:
            raise ValueError("evidence not linked to finding")
        source = nodes[evidence["source_record_id"]]
        lines.append(
            f"| {role} | {item['normalized_content']} | {note} | "
            f"`{item['id']}` → `{evidence_id}` → `{source['id']}` |"
        )
        source_notes.append(
            f"- `{source['id']}` — `{source['external_reference']}`."
        )

    lines += [
        "",
        "## What we still do not know",
        "",
        "These reports do not establish the cause of the failure or a safe size limit. "
        "The file formats, error messages and upload conditions are unknown.",
        "",
        f"**Next step:** {insight['statement']}",
        "",
        "## Source references",
        "",
        *source_notes,
        "",
        "Fictional example. The observations and their roles were written for this scenario. "
        "MCP checks the links and keeps raw evidence out of the report; "
        "valid links do not establish that a claim is true.",
    ]
    return "\n".join(lines) + "\n"


async def generate_report(output: Path) -> None:
    brief = await asyncio.wait_for(
        scenario(len(UPLOAD_OBSERVATIONS), "Photo uploads", uploads=True),
        timeout=90,
    )
    report = render_decision_brief(brief)
    with output.open("x", encoding="utf-8") as stream:
        stream.write(report)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--conflicting-uploads", action="store_true")
    mode.add_argument("--decision-brief", action="store_true", help="Write a Markdown brief")
    arguments = parser.parse_args()
    if arguments.decision_brief:
        try:
            asyncio.run(generate_report(arguments.output))
        except FileExistsError:
            print("PILOT_REPORT=FAIL output already exists", file=sys.stderr)
            return 1
        except Exception:  # noqa: BLE001
            print("PILOT_REPORT=FAIL output_suppressed=true", file=sys.stderr)
            return 1
        print("PILOT_REPORT=PASS synthetic_only=true")
        return 0
    try:
        asyncio.run(generate(arguments.output, uploads=arguments.conflicting_uploads))
    except Exception:  # noqa: BLE001
        print("TRACE_VIEWER=FAIL output_suppressed=true", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
