"""Generate a synthetic-only, redacted local trace viewer through installed MCP."""

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
    "SourceRecord": "منبع مصنوعی",
    "RawEvidence": "شاهد مصنوعی",
    "IntelligenceItem": "قلم تحلیل نمونه",
    "Finding": "یافتهٔ نمونه",
    "Insight": "نتیجهٔ نمونه",
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
    "بارگذاری یک عکس ۱۲ مگابایتی ناموفق بود.",
    "بارگذاری یک عکس دیگر با حجم ۱۲ مگابایت موفق بود.",
    "بارگذاری یک عکس ۲ مگابایتی موفق بود.",
)
UPLOAD_FINDING = "عکس‌های هم‌حجم نتیجهٔ متفاوت داشتند؛ علت خطا هنوز معلوم نیست."
UPLOAD_INSIGHT = "پیش از تغییر سقف حجم، فرمت و پیام خطا را در شرایط یکسان بررسی کنید."


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
                            else "این قلم، مشاهده‌ای از پیش تعریف‌شده در نمونه است."
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
                            else "این یافتهٔ مصنوعی به تحلیل‌ها و شواهد زیر ارجاع دارد."
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
                        else "این نتیجهٔ از پیش تعریف‌شده، مسیر ارجاع‌های نمونه را نشان می‌دهد."
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
    check_private(json.dumps(result, ensure_ascii=False))
    return result


async def generate(output: Path, *, uploads: bool = False) -> None:
    scenarios = []
    for count, label in ((1, "سبک · یک شاهد"), (5, "متوسط · پنج شاهد"),
                         (25, "بزرگ‌تر · بیست‌وپنج شاهد")):
        scenarios.append(await asyncio.wait_for(scenario(count, label), timeout=90))
    if uploads:
        scenarios.append(await asyncio.wait_for(
            scenario(3, "بارگذاری عکس · گزارش‌های متناقض", uploads=True), timeout=90,
        ))
    template = Path(__file__).with_name("viewer.template.html").read_text(encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError("output already exists; do not overwrite")
    output.write_text(render_html(scenarios, template), encoding="utf-8")
    print(json.dumps({"viewer": "PASS", "synthetic_only": True, "scenarios": len(scenarios),
                      "evidence_counts": [1, 5, 25] + ([3] if uploads else [])}, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--conflicting-uploads", action="store_true")
    arguments = parser.parse_args()
    try:
        asyncio.run(generate(arguments.output, uploads=arguments.conflicting_uploads))
    except Exception:  # noqa: BLE001
        print("TRACE_VIEWER=FAIL output_suppressed=true", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
