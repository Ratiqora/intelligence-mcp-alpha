"""Safe public views; RawEvidence bytes never cross this boundary."""

from intelligence_core.contracts import (
    Finding,
    Insight,
    IntelligenceItem,
    RawEvidence,
    SourceRecord,
)

from .workspace import (
    HOST_SUPPLIED_PUBLIC_DOCUMENT,
    Entity,
    EvidenceBoundaryError,
    Workspace,
)


def _producer(entity: IntelligenceItem | Finding | Insight) -> dict[str, str | None]:
    value = entity.producer
    return {
        "kind": value.kind.value,
        "method": value.method,
        "method_version": value.method_version,
        "actor_ref": value.actor_ref,
        "provider": value.provider,
        "model": value.model,
    }


def entity_view(
    entity: Entity,
    evidence_origin: str | None = None,
) -> dict[str, object]:
    common: dict[str, object] = {
        "id": str(entity.id),
        "entity_type": type(entity).__name__,
        "contract_version": entity.contract_version,
    }
    if isinstance(entity, SourceRecord):
        return common | {
            "source": {
                "source_kind": entity.source.source_kind,
                "source_instance": entity.source.source_instance,
                "external_reference": entity.source.external_reference,
            },
            "collection": {
                "collected_at": entity.collection.collected_at.isoformat(),
                "collector_method": entity.collection.collector_method,
                "collector_method_version": entity.collection.collector_method_version,
            },
        }
    if isinstance(entity, RawEvidence):
        if evidence_origin is None:
            raise EvidenceBoundaryError("evidence origin is unavailable")
        return common | {
            "source_record_id": str(entity.source_record_id),
            "integrity": entity.integrity,
            "evidence_origin": evidence_origin,
            "verbatim_source_capture": (
                evidence_origin == HOST_SUPPLIED_PUBLIC_DOCUMENT
            ),
            "content_redacted": True,
        }
    if isinstance(entity, IntelligenceItem):
        return common | {
            "normalized_content": entity.normalized_content,
            "evidence_ids": [str(value) for value in entity.evidence_ids],
            "producer": _producer(entity),
        }
    if isinstance(entity, Finding):
        return common | {
            "statement": entity.statement,
            "supporting_item_ids": [str(value) for value in entity.supporting_item_ids],
            "supporting_evidence_ids": [
                str(value) for value in entity.supporting_evidence_ids
            ],
            "producer": _producer(entity),
            "finding_type": entity.finding_type,
        }
    return common | {
        "statement": entity.statement,
        "supporting_finding_ids": [
            str(value) for value in entity.supporting_finding_ids
        ],
        "supporting_evidence_ids": [
            str(value) for value in entity.supporting_evidence_ids
        ],
        "producer": _producer(entity),
    }


def project_view(workspace: Workspace) -> dict[str, object]:
    return {
        "initialized": workspace.project_id is not None,
        "project_id": workspace.project_id,
        "display_name": workspace.display_name,
        "counts": workspace.counts(),
    }


def host_ingestion_view(workspace: Workspace) -> dict[str, object]:
    """Build content-free metadata for host-preloaded evidence."""
    entries: list[dict[str, object]] = []
    for evidence_id, evidence in workspace.evidence.items():
        if workspace.evidence_origin(evidence_id) != HOST_SUPPLIED_PUBLIC_DOCUMENT:
            continue
        source = workspace.sources[str(evidence.source_record_id)]
        entries.append(
            {
                "source": entity_view(source),
                "evidence": entity_view(evidence, HOST_SUPPLIED_PUBLIC_DOCUMENT),
            }
        )
    return {
        "retention": "memory_only",
        "client_attachment_binding": "unverified",
        "entries": entries,
    }


def trace_view(workspace: Workspace, entity_id: str) -> dict[str, object]:
    entity = workspace.get(entity_id)
    if entity is None:
        raise ValueError("unknown entity")
    origin = (
        workspace.evidence_origin(entity_id)
        if isinstance(entity, RawEvidence)
        else None
    )
    return entity_view(entity, origin)

