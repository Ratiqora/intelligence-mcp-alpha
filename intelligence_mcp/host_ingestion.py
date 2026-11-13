"""Trusted host-only preload for one bounded local UTF-8 document."""

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from intelligence_core.contracts import (
    CollectionContext,
    CoreId,
    RawEvidence,
    SourceRecord,
    SourceReference,
)

from .workspace import (
    HOST_SUPPLIED_PUBLIC_DOCUMENT,
    EvidenceBoundaryError,
    Workspace,
)

MAX_TRUSTED_TEXT_BYTES = 1024 * 1024


@dataclass(frozen=True, slots=True)
class TrustedTextPreload:
    """Host-authorized metadata for a single local text capture."""

    path: Path
    project_id: str
    display_name: str | None
    source_id: str
    evidence_id: str
    source_instance: str
    external_reference: str
    collected_at: datetime


def _read_bounded_utf8(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise EvidenceBoundaryError("trusted input must be a regular non-symlink file")
    if path.stat().st_size > MAX_TRUSTED_TEXT_BYTES:
        raise EvidenceBoundaryError("trusted input exceeds the size limit")
    with path.open("rb") as stream:
        payload = stream.read(MAX_TRUSTED_TEXT_BYTES + 1)
    if not payload:
        raise EvidenceBoundaryError("trusted input must not be empty")
    if len(payload) > MAX_TRUSTED_TEXT_BYTES:
        raise EvidenceBoundaryError("trusted input exceeds the size limit")
    try:
        payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise EvidenceBoundaryError("trusted input must be valid UTF-8") from None
    if b"\x00" in payload:
        raise EvidenceBoundaryError("trusted input must be text")
    return payload


def preload_trusted_text(workspace: Workspace, config: TrustedTextPreload) -> None:
    """Read once and seed the workspace without retaining a filesystem path."""
    payload = _read_bounded_utf8(config.path)
    source = SourceRecord(
        id=CoreId(config.source_id),
        source=SourceReference(
            source_kind="public_document",
            source_instance=config.source_instance,
            external_reference=config.external_reference,
        ),
        collection=CollectionContext(
            collected_at=config.collected_at,
            collector_method="trusted_local_text_preload",
            collector_method_version="1",
        ),
    )
    evidence = RawEvidence(
        id=CoreId(config.evidence_id),
        source_record_id=source.id,
        content=payload,
        integrity=f"sha256:{sha256(payload).hexdigest()}",
    )
    workspace.initialize(config.project_id, config.display_name)
    workspace.add_source(source)
    workspace.add_evidence(evidence, HOST_SUPPLIED_PUBLIC_DOCUMENT)
