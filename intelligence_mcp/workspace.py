"""Single-project, in-memory workspace for the alpha runtime."""

from dataclasses import dataclass, field
from typing import TypeVar

from intelligence_core.contracts import (
    CoreId,
    Finding,
    Insight,
    IntelligenceItem,
    RawEvidence,
    SourceRecord,
    validate_graph,
)

Entity = SourceRecord | RawEvidence | IntelligenceItem | Finding | Insight
EntityT = TypeVar("EntityT", bound=Entity)
MODEL_SUPPLIED_SYNTHETIC = "model_supplied_synthetic"
HOST_SUPPLIED_PUBLIC_DOCUMENT = "host_supplied_public_document"
_ALLOWED_EVIDENCE_ORIGINS = {
    MODEL_SUPPLIED_SYNTHETIC,
    HOST_SUPPLIED_PUBLIC_DOCUMENT,
}


class EvidenceBoundaryError(ValueError):
    """Raised when evidence crosses an unsupported authority boundary."""


class ProjectLifecycleError(ValueError):
    """Raised when the single active project lifecycle is misused."""


@dataclass(slots=True)
class Workspace:
    """Owns one ephemeral project graph for one server process."""

    project_id: str | None = None
    display_name: str | None = None
    sources: dict[str, SourceRecord] = field(default_factory=dict)
    evidence: dict[str, RawEvidence] = field(default_factory=dict)
    evidence_origins: dict[str, str] = field(default_factory=dict)
    items: dict[str, IntelligenceItem] = field(default_factory=dict)
    findings: dict[str, Finding] = field(default_factory=dict)
    insights: dict[str, Insight] = field(default_factory=dict)

    @staticmethod
    def _metadata(project_id: str, display_name: str | None) -> tuple[str, str | None]:
        validated_id = str(CoreId(project_id))
        if display_name is not None and (
            not display_name or display_name != display_name.strip()
        ):
            raise ProjectLifecycleError(
                "display_name must be non-blank without surrounding whitespace"
            )
        return validated_id, display_name

    def initialize(self, project_id: str, display_name: str | None = None) -> None:
        if self.project_id is not None:
            raise ProjectLifecycleError("a project is already active")
        self.project_id, self.display_name = self._metadata(project_id, display_name)

    def reset(
        self,
        project_id: str,
        expected_current_project_id: str,
        display_name: str | None = None,
    ) -> None:
        validated_id, validated_name = self._metadata(project_id, display_name)
        if self.project_id is None:
            raise ProjectLifecycleError("no project is active")
        if expected_current_project_id != self.project_id:
            raise ProjectLifecycleError("active project confirmation does not match")
        for collection in self._collections():
            collection.clear()
        self.evidence_origins.clear()
        self.project_id = validated_id
        self.display_name = validated_name

    def _require_initialized(self) -> None:
        if self.project_id is None:
            raise ProjectLifecycleError("initialize a project before registering entities")

    def _add(self, entity: EntityT, target: dict[str, EntityT]) -> EntityT:
        self._require_initialized()
        key = str(entity.id)
        if self.get(key) is not None:
            raise ValueError(f"duplicate Core entity id: {key}")
        target[key] = entity
        return entity

    def add_source(self, entity: SourceRecord) -> SourceRecord:
        return self._add(entity, self.sources)

    def add_evidence(
        self,
        entity: RawEvidence,
        origin: str,
    ) -> RawEvidence:
        if origin not in _ALLOWED_EVIDENCE_ORIGINS:
            raise EvidenceBoundaryError("unsupported evidence origin")
        added = self._add(entity, self.evidence)
        self.evidence_origins[str(entity.id)] = origin
        return added

    def evidence_origin(self, evidence_id: str) -> str:
        try:
            return self.evidence_origins[evidence_id]
        except KeyError:
            raise EvidenceBoundaryError("evidence origin is unavailable") from None

    def add_item(self, entity: IntelligenceItem) -> IntelligenceItem:
        return self._add(entity, self.items)

    def add_finding(self, entity: Finding) -> Finding:
        return self._add(entity, self.findings)

    def add_insight(self, entity: Insight) -> Insight:
        return self._add(entity, self.insights)

    def get(self, entity_id: str) -> Entity | None:
        for collection in self._collections():
            if entity_id in collection:
                return collection[entity_id]
        return None

    def _collections(self) -> tuple[dict[str, Entity], ...]:
        return (
            self.sources,
            self.evidence,
            self.items,
            self.findings,
            self.insights,
        )

    def validate(self) -> None:
        self._require_initialized()
        validate_graph(
            sources=self.sources.values(),
            evidence=self.evidence.values(),
            items=self.items.values(),
            findings=self.findings.values(),
            insights=self.insights.values(),
        )

    def counts(self) -> dict[str, int]:
        return {
            "sources": len(self.sources),
            "evidence": len(self.evidence),
            "items": len(self.items),
            "findings": len(self.findings),
            "insights": len(self.insights),
        }
