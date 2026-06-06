---
name: planning-artifact-curator
description: Captures accepted decisions, open questions, risks, acceptance evidence, and next actions for the DwC-A to cloud-optimized geospatial formats project into docs, ADRs, demo notes, output specs, viewer contracts, and session logs.
---

# Skill: Planning Artifact Curator

## Purpose

Keep durable project decisions for this DwC-A conversion prototype in repository documents instead of leaving them only in chat.

## When to use

Use this skill when:
- an architecture, output-format, parser, converter, tiling or viewer-contract decision is accepted;
- a planning session creates open questions, risks or next actions;
- demo evidence or validation results should be recorded;
- docs need to distinguish accepted decisions from exploratory ideas.

## Instructions

### 1. Identify durable outputs

Separate:
- accepted decisions;
- proposed but not accepted options;
- open questions;
- risks and mitigations;
- acceptance or demo evidence;
- files that need update.

### 2. Update appropriate artifacts

Use:
- `docs/` for project-facing architecture, output specification, parser behavior, converter usage, viewer contract, deployment and demo documentation;
- `planning/` for durable internal planning;
- `planning/decisions/` for ADR-style decisions;
- `session_logs/` for exploratory notes and unresolved questions.

Do not create planning files just to mirror chat. Create them when they preserve decisions or handoff context that future work will rely on.

### 3. Keep file-based boundaries visible

For each durable decision, mark whether it affects:
- DwC-A parsing;
- field mapping and normalization;
- geospatial conversion;
- GeoParquet/FlatGeobuf/PMTiles outputs;
- metadata/provenance;
- static viewer contract;
- deployment/static hosting;
- optional GBIF acquisition or taxonomy enrichment.

Call out when an accepted decision intentionally avoids a permanent backend, database, scheduler or cloud-specific dependency.

### 4. Preserve source-of-truth discipline

If documents conflict:
- identify the canonical file;
- update only accepted conclusions;
- keep hypotheses and open questions clearly marked;
- avoid duplicating the same decision inconsistently.

## Output expectations

When curating planning artifacts, return:

1. Files created or updated.
2. Content summary per file.
3. Accepted decisions recorded.
4. Open questions preserved.
5. Suggested next work item.

## Checklist

- Were accepted decisions separated from hypotheses?
- Is the DwC-A/converter/viewer boundary clear?
- Was an ADR created for long-lived tradeoffs when needed?
- Are acceptance/demo materials updated when relevant?
- Can the next session continue without rereading the whole chat?
