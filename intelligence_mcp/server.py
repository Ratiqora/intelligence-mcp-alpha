"""stdio MCP server exposing a bounded in-memory evidence graph."""

import argparse
from datetime import datetime
from hashlib import sha256
from hmac import compare_digest
from pathlib import Path
from typing import Literal

from intelligence_core.contracts import (
    SYNTHETIC_DOCUMENT_SOURCE_KIND,
    CollectionContext,
    CoreId,
    Finding,
    Insight,
    IntelligenceItem,
    ProducerKind,
    ProducerRef,
    RawEvidence,
    SourceRecord,
    SourceReference,
)
from mcp.server.mcpserver import MCPServer

from . import __version__
from .diagnostics import DiagnosticRecorder
from .host_ingestion import TrustedTextPreload, preload_trusted_text
from .views import entity_view, host_ingestion_view, project_view, trace_view
from .workspace import EvidenceBoundaryError, Workspace


def _ids(values: list[str]) -> tuple[CoreId, ...]:
    return tuple(CoreId(value) for value in values)


def _deterministic(method: str) -> ProducerRef:
    return ProducerRef(
        kind=ProducerKind.DETERMINISTIC,
        method=method,
        method_version="1",
    )


def _parse_collected_at(value: str) -> datetime:
    normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    collected_at = datetime.fromisoformat(normalized)
    if collected_at.tzinfo is None:
        raise ValueError("collected_at must include a timezone")
    return collected_at


def create_server(workspace: Workspace | None = None) -> MCPServer:
    state = workspace or Workspace()
    diagnostics = DiagnosticRecorder()
    mcp = MCPServer(
        "Ratiqora Project Intelligence Alpha",
        instructions=(
            "Initialize one ephemeral project before registering evidence. "
            "Reset it explicitly between independent projects. "
            "Model-callable evidence is synthetic, integrity-checked, and non-verbatim. "
            "Host-preloaded public text is verbatim, bounded, and memory-only. "
            "Raw evidence bytes and local paths are never returned or persisted."
        ),
    )

    @mcp.tool()
    @diagnostics.capture("initialize_project")
    def initialize_project(
        project_id: str,
        display_name: str | None = None,
    ) -> dict[str, object]:
        """Initialize the single active in-memory project."""
        state.initialize(project_id, display_name)
        return project_view(state)

    @mcp.tool()
    @diagnostics.capture("reset_project")
    def reset_project(
        project_id: str,
        expected_current_project_id: str,
        display_name: str | None = None,
    ) -> dict[str, object]:
        """Discard the active graph and initialize a clean in-memory project."""
        state.reset(project_id, expected_current_project_id, display_name)
        return project_view(state)

    @mcp.tool()
    @diagnostics.capture("register_source")
    def register_source(
        source_id: str,
        source_kind: Literal["public_document", "synthetic_document"],
        source_instance: str,
        external_reference: str,
        collected_at: str,
        collector_method: str = "manual",
    ) -> dict[str, object]:
        """Register provenance; collected_at must be timezone-aware ISO 8601."""
        entity = SourceRecord(
            id=CoreId(source_id),
            source=SourceReference(
                source_kind=source_kind,
                source_instance=source_instance,
                external_reference=external_reference,
            ),
            collection=CollectionContext(
                collected_at=_parse_collected_at(collected_at),
                collector_method=collector_method,
                collector_method_version="1",
            ),
        )
        return entity_view(state.add_source(entity))

    @mcp.tool()
    @diagnostics.capture("register_evidence")
    def register_evidence(
        evidence_id: str,
        source_record_id: str,
        synthetic_content: object,
        expected_integrity: str,
        content_mode: Literal["model_supplied_synthetic"],
    ) -> dict[str, object]:
        """Register integrity-checked synthetic input; never verbatim source capture."""
        if not isinstance(synthetic_content, str):
            raise EvidenceBoundaryError("synthetic_content must be a string")
        source = state.sources.get(source_record_id)
        if source is None:
            raise EvidenceBoundaryError("source must exist before evidence ingestion")
        if source.source.source_kind != SYNTHETIC_DOCUMENT_SOURCE_KIND:
            raise EvidenceBoundaryError(
                "model-supplied evidence requires a synthetic_document source"
            )
        payload = synthetic_content.encode("utf-8")
        actual_integrity = f"sha256:{sha256(payload).hexdigest()}"
        if not compare_digest(actual_integrity, expected_integrity):
            raise EvidenceBoundaryError("evidence integrity does not match")
        entity = RawEvidence(
            id=CoreId(evidence_id),
            source_record_id=CoreId(source_record_id),
            content=payload,
            integrity=actual_integrity,
        )
        added = state.add_evidence(entity, content_mode)
        return entity_view(added, state.evidence_origin(evidence_id))

    @mcp.tool()
    @diagnostics.capture("register_item")
    def register_item(
        item_id: str,
        normalized_content: str,
        evidence_ids: list[str],
    ) -> dict[str, object]:
        """Register a normalized intelligence item linked to evidence."""
        entity = IntelligenceItem(
            id=CoreId(item_id),
            normalized_content=normalized_content,
            evidence_ids=_ids(evidence_ids),
            producer=_deterministic("mcp.register_item"),
        )
        return entity_view(state.add_item(entity))

    @mcp.tool()
    @diagnostics.capture("register_finding")
    def register_finding(
        finding_id: str,
        statement: str,
        supporting_item_ids: list[str],
        supporting_evidence_ids: list[str],
    ) -> dict[str, object]:
        """Register a finding with explicit item and evidence support."""
        entity = Finding(
            id=CoreId(finding_id),
            statement=statement,
            supporting_item_ids=_ids(supporting_item_ids),
            supporting_evidence_ids=_ids(supporting_evidence_ids),
            producer=_deterministic("mcp.register_finding"),
        )
        return entity_view(state.add_finding(entity))

    @mcp.tool()
    @diagnostics.capture("register_insight")
    def register_insight(
        insight_id: str,
        statement: str,
        supporting_finding_ids: list[str],
        supporting_evidence_ids: list[str],
    ) -> dict[str, object]:
        """Register an insight with explicit finding and evidence support."""
        entity = Insight(
            id=CoreId(insight_id),
            statement=statement,
            supporting_finding_ids=_ids(supporting_finding_ids),
            supporting_evidence_ids=_ids(supporting_evidence_ids),
            producer=_deterministic("mcp.register_insight"),
        )
        return entity_view(state.add_insight(entity))

    @mcp.tool()
    @diagnostics.capture("validate_project")
    def validate_project() -> dict[str, object]:
        """Validate all Core references and evidence-closure invariants."""
        state.validate()
        return {"valid": True, **project_view(state)}

    @mcp.tool()
    def get_diagnostics() -> dict[str, object]:
        """Read bounded, content-free errors to recover from failed tool calls."""
        return diagnostics.report()

    @mcp.tool()
    def get_host_ingestion() -> dict[str, object]:
        """Read content-free metadata for host-preloaded evidence."""
        return host_ingestion_view(state)

    @mcp.tool()
    def get_support_report() -> dict[str, object]:
        """Build safe runtime metadata that a client can copy into a support report."""
        host_ingestion = host_ingestion_view(state)
        host_entries = host_ingestion["entries"]
        return {
            "report_version": 1,
            "runtime": {
                "package": "ratiqora-intelligence-mcp",
                "version": __version__,
                "transport": "stdio",
                "retention": "memory_only",
            },
            "project": {
                "initialized": state.project_id is not None,
                "counts": state.counts(),
            },
            "host_ingestion": {
                "entry_count": len(host_entries),
                "client_attachment_binding": (
                    "unverified" if host_entries else "not_applicable"
                ),
            },
            "diagnostics": diagnostics.report(),
            "safety": {
                "raw_evidence_included": False,
                "tool_inputs_included": False,
                "exception_messages_included": False,
                "filesystem_paths_included": False,
                "project_identifiers_included": False,
            },
        }

    @mcp.resource("ratiqora://project")
    def read_project() -> dict[str, object]:
        """Read safe project metadata and entity counts."""
        return project_view(state)

    @mcp.resource("ratiqora://host-ingestion")
    def read_host_ingestion() -> dict[str, object]:
        """Read safe IDs and metadata for host-preloaded evidence."""
        return host_ingestion_view(state)

    @mcp.resource("ratiqora://entity/{entity_id}")
    @diagnostics.capture_resource("read_entity")
    def read_entity(entity_id: str) -> dict[str, object]:
        """Read one safe entity view; evidence content is always redacted."""
        entity = state.get(entity_id)
        if entity is None:
            raise ValueError("unknown entity")
        origin = (
            state.evidence_origin(entity_id)
            if isinstance(entity, RawEvidence)
            else None
        )
        return entity_view(entity, origin)

    @mcp.resource("ratiqora://trace/{entity_id}")
    @diagnostics.capture_resource("read_trace")
    def read_trace(entity_id: str) -> dict[str, object]:
        """Read the explicit references carried by an entity."""
        return trace_view(state, entity_id)

    @mcp.resource("ratiqora://diagnostics")
    def read_diagnostics() -> dict[str, object]:
        """Read bounded, content-free runtime error diagnostics."""
        return diagnostics.report()

    return mcp


def _startup_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trusted-text-file")
    parser.add_argument("--project-id")
    parser.add_argument("--display-name")
    parser.add_argument("--source-id")
    parser.add_argument("--evidence-id")
    parser.add_argument("--source-instance")
    parser.add_argument("--external-reference")
    parser.add_argument("--collected-at")
    return parser


def _preloaded_workspace(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> Workspace:
    workspace = Workspace()
    preload_fields = {
        "trusted_text_file": args.trusted_text_file,
        "project_id": args.project_id,
        "source_id": args.source_id,
        "evidence_id": args.evidence_id,
        "source_instance": args.source_instance,
        "external_reference": args.external_reference,
        "collected_at": args.collected_at,
    }
    if not any(preload_fields.values()):
        return workspace
    if not all(preload_fields.values()):
        parser.error("trusted text preload requires all host metadata")
    try:
        preload_trusted_text(
            workspace,
            TrustedTextPreload(
                path=Path(args.trusted_text_file),
                project_id=args.project_id,
                display_name=args.display_name,
                source_id=args.source_id,
                evidence_id=args.evidence_id,
                source_instance=args.source_instance,
                external_reference=args.external_reference,
                collected_at=_parse_collected_at(args.collected_at),
            ),
        )
    except Exception:  # noqa: BLE001
        parser.exit(2, "trusted text preload failed\n")
    return workspace


def main() -> None:
    parser = _startup_parser()
    workspace = _preloaded_workspace(parser, parser.parse_args())
    create_server(workspace).run(transport="stdio")


if __name__ == "__main__":
    main()

