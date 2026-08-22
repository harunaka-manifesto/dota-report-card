---
type: "architecture"
date: "2026-08-22T13:57:50.747159+00:00"
question: "Complete Dota Report Card v5.2 across hero semantics, recommendations, copy, frontend, Figma, regression QA, and documentation"
contributor: "graphify"
outcome: "corrected"
correction: "Regenerate graphify-out after merging: the existing graph predates the new semantic catalog, full-roster snapshot, strict provenance validator, and recommendation rationale UI."
source_nodes: ["services/api/app/behavior/outcomes.py", "services/api/app/behavior/presentation.py", "services/api/app/content/renderer.py", "services/api/app/heroes/knowledge.py", "services/api/app/heroes/recommendations.py", "services/api/app/reports/dna_assembly.py", "services/api/app/api/report_schemas.py", "apps/web/app/components/story/patterns/pattern-story-screen.tsx"]
---

# Q: Complete Dota Report Card v5.2 across hero semantics, recommendations, copy, frontend, Figma, regression QA, and documentation

## Answer

The existing graph was useful for initial subsystem orientation but stale for the final working tree. Completion required direct repository inspection and tests. Key current seams are behavior outcomes/presentation, content semantic catalog/renderer, full-roster hero knowledge/recommendations, report assembly/schema, React story rendering, and generated documentation.

## Outcome

- Signal: corrected
- Correction: Regenerate graphify-out after merging: the existing graph predates the new semantic catalog, full-roster snapshot, strict provenance validator, and recommendation rationale UI.

## Source Nodes

- services/api/app/behavior/outcomes.py
- services/api/app/behavior/presentation.py
- services/api/app/content/renderer.py
- services/api/app/heroes/knowledge.py
- services/api/app/heroes/recommendations.py
- services/api/app/reports/dna_assembly.py
- services/api/app/api/report_schemas.py
- apps/web/app/components/story/patterns/pattern-story-screen.tsx