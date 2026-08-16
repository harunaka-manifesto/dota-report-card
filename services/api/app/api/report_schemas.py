from __future__ import annotations

from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


class DimensionResultSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    key: str
    status: Literal["available", "limited", "unavailable"]
    score: float | None = None
    centered_score: float | None = None
    label: str | None = None
    confidence: str
    confidence_score: float = 0.0
    sample_size: int = 0
    effective_sample_size: float = 0.0
    coverage: float = 0.0
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    confounders: list[str] = Field(default_factory=list)
    missing_reasons: list[str] = Field(default_factory=list)
    copy_: dict[str, Any] | None = Field(default=None, validation_alias=AliasChoices("copy", "copy_"), serialization_alias="copy")
    methodology_version: str = "dna-scoring-1.0.0"
    source_match_ids: list[int] = Field(default_factory=list)


class FreeDnaReportSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: str
    report_variant: Literal["free_player_dna", "free_dna_report"]
    dna_report_variant: Literal["free_dna_report"] | None = None
    noindex: bool = True
    identity: dict[str, Any]
    metadata: dict[str, Any]
    versions: dict[str, Any]
    quality: dict[str, Any]
    dimensions: list[DimensionResultSchema] = Field(min_length=8)
    archetype: dict[str, Any]
    heroes: dict[str, Any]
    pages: list[dict[str, Any]] = Field(min_length=23)
    shares: dict[str, Any]
    deep_dive: dict[str, Any]

    @model_validator(mode="after")
    def validate_free_contract(self) -> FreeDnaReportSchema:
        if self.dna_report_variant != "free_dna_report":
            return self
        keys = [item.key for item in self.dimensions]
        expected = {
            "breadth", "role", "adaptability", "activity",
            "orientation", "resilience", "endurance", "rhythm",
        }
        if set(keys) != expected or len(keys) != len(set(keys)):
            raise ValueError("Free DNA reports must contain each of the eight dimensions once")
        page_ids = [str(item.get("id")) for item in self.pages]
        if len(page_ids) != 23 or len(page_ids) != len(set(page_ids)):
            raise ValueError("Free DNA reports must contain exactly 23 unique story pages")
        descriptors = self.archetype.get("descriptors")
        if not isinstance(descriptors, list) or len(descriptors) != 3:
            raise ValueError("Free DNA archetypes must expose exactly three descriptors")
        if len({item.get("key") for item in descriptors if isinstance(item, dict)}) != 3:
            raise ValueError("Free DNA descriptors must be unique")
        privacy = self.shares.get("privacy_defaults")
        if not isinstance(privacy, dict) or privacy.get("show_raw_id") is not False:
            raise ValueError("Free DNA share cards cannot enable raw IDs")
        return self


def validate_free_dna_report(report: dict[str, Any]) -> dict[str, Any]:
    """Validate and return a JSON-compatible immutable snapshot."""

    return FreeDnaReportSchema.model_validate(report).model_dump(mode="json", by_alias=True)
