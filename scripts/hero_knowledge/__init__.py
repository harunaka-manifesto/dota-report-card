"""Versioned hero-knowledge ingestion pipeline.

The package is intentionally kept outside ``services/api/app``.  Its source
models and fetch dependencies are build-time concerns; the API consumes only
the checked-in/generated knowledge snapshot through its repository seam.
"""

SCHEMA_VERSION = "hero-knowledge-schema-1.0.0"
PARSER_VERSION = "opendota-parser-1.0.0"
MECHANIC_RULE_VERSION = "mechanic-rules-1.0.0"
BEHAVIOR_RULE_VERSION = "behavior-rules-1.0.0"
