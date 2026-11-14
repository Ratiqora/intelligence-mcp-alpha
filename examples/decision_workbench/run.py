"""Serve the decision workbench on loopback and validate before rendering Markdown."""

import argparse
import csv
import io
import json
import re
import secrets
from datetime import datetime, timezone
from hashlib import sha256
from hmac import compare_digest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from intelligence_core.contracts import (
    CollectionContext,
    CoreId,
    Finding,
    IntelligenceItem,
    ProducerKind,
    ProducerRef,
    RawEvidence,
    SourceRecord,
    SourceReference,
    validate_graph,
)

MAX_BODY = 65536
SOURCE_ID = re.compile(r"S[1-9][0-9]{0,5}")
ROLES = {
    "supports": "Supports the finding",
    "challenges": "Challenges the finding",
    "context": "Adds context",
}

CSV_HEADER = ["observation", "source_reference", "source_type", "role"]
CSV_SOURCE_KINDS = {"fictional": "synthetic_document", "public": "public_document"}


class BriefError(ValueError):
    """Messages contain field names and row numbers, never user values."""


def field(value, name, limit):
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > limit
        or any(ord(c) < 32 and c not in "\r\n\t" for c in value)
    ):
        raise BriefError(f"{name} must contain 1–{limit} characters of text.")
    return value.strip()


def rows(value, name):
    if (
        not isinstance(value, list)
        or not 1 <= len(value) <= 12
        or not all(isinstance(row, dict) for row in value)
    ):
        raise BriefError(f"Enter 1–12 {name}.")
    return value


def plain(value):
    text = " ".join(value.split())
    return re.sub(r"[&<>`*_~\[\]\\|#!:+.=-]", lambda m: f"&#{ord(m[0])};", text)


def parse_observations_csv(body):
    """Read an entire bounded CSV before allowing it to replace the form rows."""
    reader = csv.reader(io.StringIO(body.decode("utf-8-sig"), newline=""), strict=True)
    sources = {}
    observations = []
    try:
        if next(reader, None) != CSV_HEADER:
            raise BriefError("The CSV header must be observation,source_reference,source_type,role.")
        for record, row in enumerate(reader, 1):
            if record > 12:
                raise BriefError("The CSV can contain at most 12 observations.")
            if len(row) != len(CSV_HEADER):
                raise BriefError(f"CSV record {record} must contain exactly four columns.")
            text, reference, kind, role = row
            text = field(text, f"Observation in CSV record {record}", 600)
            reference = field(reference, f"Source reference in CSV record {record}", 240)
            if kind not in CSV_SOURCE_KINDS:
                raise BriefError(f"Use fictional or public in CSV record {record}.")
            if role not in ROLES:
                raise BriefError(f"Use supports, challenges, or context in CSV record {record}.")
            key = (reference, kind)
            if key not in sources:
                sources[key] = {
                    "id": f"S{len(sources) + 1}",
                    "kind": CSV_SOURCE_KINDS[kind],
                    "reference": reference,
                }
            observations.append({"text": text, "role": role, "source": sources[key]["id"]})
    except csv.Error:
        raise BriefError("The CSV contains malformed fields or quotes.") from None
    if not observations:
        raise BriefError("The CSV must contain at least one observation.")
    return {"sources": list(sources.values()), "observations": observations}


def build_brief(data):
    if not isinstance(data, dict):
        raise BriefError("Expected a decision brief object.")
    question = field(data.get("question"), "Decision question", 240)
    finding_text = field(data.get("finding"), "Finding", 700)
    unknowns = field(data.get("unknowns"), "Unknowns", 700)
    next_step = field(data.get("next"), "Next step", 700)
    collection = CollectionContext(datetime.now(timezone.utc), "manual_workbench_entry", "1")
    producer = ProducerRef(ProducerKind.HUMAN, "manual_workbench_entry", "1", "local-author")
    sources = {}
    for number, row in enumerate(rows(data.get("sources"), "sources"), 1):
        identifier = row.get("id")
        if not isinstance(identifier, str) or not SOURCE_ID.fullmatch(identifier):
            raise BriefError(f"Source row {number} has an invalid ID.")
        source_id = CoreId(identifier)
        if source_id in sources:
            raise BriefError(f"Source row {number} repeats a source ID.")
        kind = row.get("kind")
        if kind not in ("synthetic_document", "public_document"):
            raise BriefError(f"Choose the kind for source row {number}.")
        reference = field(row.get("reference"), f"Source reference {number}", 240)
        sources[source_id] = SourceRecord(
            source_id, SourceReference(kind, "local-workbench", reference), collection
        )

    evidence, items, roles = [], [], []
    for number, row in enumerate(rows(data.get("observations"), "observations"), 1):
        source = row.get("source")
        if not isinstance(source, str) or not SOURCE_ID.fullmatch(source):
            raise BriefError(f"Choose a source for observation {number}.")
        role = row.get("role")
        if not isinstance(role, str) or role not in ROLES:
            raise BriefError(f"Choose a role for observation {number}.")
        observation = field(row.get("text"), f"Observation {number}", 600)
        # Bind the authored observation, never the cited document or its contents.
        payload = observation.encode("utf-8")
        raw = RawEvidence(
            CoreId(f"E{number}"), CoreId(source), payload, f"sha256:{sha256(payload).hexdigest()}"
        )
        evidence.append(raw)
        items.append(IntelligenceItem(CoreId(f"O{number}"), observation, (raw.id,), producer))
        roles.append(ROLES[role])

    finding = Finding(
        CoreId("F1"), finding_text, tuple(item.id for item in items),
        tuple(raw.id for raw in evidence), producer,
    )
    try:
        validate_graph(
            sources=sources.values(),
            evidence=evidence,
            items=items,
            findings=[finding],
            insights=[],
        )
    except ValueError:
        for number, raw in enumerate(evidence, 1):
            if raw.source_record_id not in sources:
                raise BriefError(f"Observation {number} points to a missing source.") from None
        raise BriefError("Ratiqora could not validate the reference structure.") from None

    report = [
        "# Decision brief", "", "## Decision question", "", plain(question), "",
        "## Finding", "", plain(finding.statement), "",
        "## Observations and references", "",
        "| Observation | Role | Summary | Source |",
        "| --- | --- | --- | --- |",
    ]
    for item, raw, role in zip(items, evidence, roles, strict=True):
        report.append(
            f"| {item.id} | {role} | {plain(item.normalized_content)} | {raw.source_record_id} |"
        )
    report.extend(["", "## Sources", ""])
    for source in sources.values():
        kind = (
            "Fictional" if source.source.source_kind == "synthetic_document" else "Public citation"
        )
        report.append(f"- {source.id} ({kind}): {plain(source.source.external_reference)}")
    report.extend([
        "", "## What is still unknown", "", plain(unknowns), "",
        "## Next step", "", plain(next_step), "",
        "Ratiqora checked the internal references. The author supplied the observations, roles, "
        "and finding. Cited materials were not opened or authenticated.", "",
    ])
    return "\n".join(report)


def handler(page, token, port):
    host = f"127.0.0.1:{port}"
    origin = f"http://{host}"

    class WorkbenchHandler(BaseHTTPRequestHandler):
        def setup(self):
            self.request.settimeout(5)
            super().setup()

        def log_message(self, *_args):
            pass

        def send_body(self, status, content_type, content):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.end_headers()
            self.wfile.write(content)

        def send_json(self, status, data):
            self.send_body(status, "application/json", json.dumps(data).encode("utf-8"))

        def do_GET(self):
            if self.headers.get("Host") != host or self.path != "/":
                self.send_json(404, {"error": "Page not found."})
                return
            self.send_body(200, "text/html; charset=utf-8", page)

        def do_POST(self):
            if (
                self.path not in ("/brief", "/import-csv")
                or self.headers.get("Host") != host
                or self.headers.get("Origin") != origin
                or not compare_digest(
                    self.headers.get("X-Workbench-Token", "").encode("latin-1"), token.encode()
                )
            ):
                self.send_json(403, {"error": "Open the workbench from its local address."})
                return
            importing = self.path == "/import-csv"
            content_type = "text/csv" if importing else "application/json"
            if self.headers.get_content_type() != content_type:
                self.send_json(415, {"error": f"Expected {content_type}."})
                return
            length = self.headers.get("Content-Length", "")
            if not re.fullmatch(r"[0-9]{1,6}", length) or not 0 < int(length) <= MAX_BODY:
                self.send_json(413, {"error": "The request is empty or exceeds 64 KiB."})
                return
            try:
                body = self.rfile.read(int(length))
                if len(body) != int(length):
                    raise BriefError("The request is incomplete.")
                result = (
                    parse_observations_csv(body) if importing
                    else {"markdown": build_brief(json.loads(body.decode("utf-8")))}
                )
            except BriefError as error:
                self.send_json(400, {"error": str(error)})
            except (ValueError, RecursionError):
                message = "The CSV must use valid UTF-8." if importing else "Invalid brief input."
                self.send_json(400, {"error": message})
            else:
                self.send_json(200, result)

    return WorkbenchHandler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    token = secrets.token_urlsafe(32)
    template = Path(__file__).with_name("index.html").read_text(encoding="utf-8")
    page = template.replace("__WORKBENCH_TOKEN__", token).encode("utf-8")
    try:
        with HTTPServer(("127.0.0.1", args.port), handler(page, token, args.port)) as server:
            print(f"Open http://127.0.0.1:{args.port}/ in your browser. Press Ctrl+C to stop.")
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    except OSError:
        parser.exit(1, "The local workbench could not use this port. Try --port 8766.\n")


if __name__ == "__main__":
    main()
