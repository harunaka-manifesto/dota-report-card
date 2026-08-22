"""Errors raised by the hero-knowledge pipeline.

Errors are deliberately typed so the CLI can report a source/schema failure
without converting it into a successful empty snapshot.
"""

from __future__ import annotations


class HeroKnowledgeError(Exception):
    """Base class for expected pipeline failures."""


class ConfigurationError(HeroKnowledgeError):
    """The requested pipeline configuration is invalid."""


class FetchError(HeroKnowledgeError):
    """A source request failed after bounded retries."""


class SourceSchemaError(HeroKnowledgeError):
    """A source response did not match the expected schema."""


class ValidationError(HeroKnowledgeError):
    """A normalized or knowledge snapshot failed invariant checks."""

    def __init__(self, message: str, errors: tuple[str, ...] | list[str] = ()) -> None:
        self.errors = tuple(errors)
        super().__init__(message)


class GovernanceError(HeroKnowledgeError):
    """Live retrieval is not allowed by the recorded source policy."""


class ParseError(HeroKnowledgeError):
    """A source page could not be parsed safely."""
