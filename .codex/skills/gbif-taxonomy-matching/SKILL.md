---
name: gbif-taxonomy-matching
description: Guides optional GBIF taxonomic matching for DwC-A geospatial conversion, including usageKey, scientificName, matchType, confidence, problematic matches, checklist datasets, manual decisions, and provenance when taxonomy enrichment is explicitly in scope.
---

# Skill: GBIF Taxonomy Matching

## Purpose

Design and review optional taxonomic matching workflows that enrich DwC-A records with GBIF taxonomy evidence while preserving reviewability and provenance. The baseline converter must still work without taxonomy matching.

## When to use

Use this skill when work involves:
- matching source scientific names through GBIF Backbone, COL XR or checklist datasets;
- interpreting `usageKey`, `scientificName`, `matchType`, `confidence`, rank and status;
- separating reliable and problematic matches;
- handling `HIGHERRANK`, fuzzy, ambiguous or no-match cases;
- designing manual decisions, variants and review queues;
- deciding how taxonomy evidence is written into output metadata or tables.

Do not use this skill for simple preservation of source Darwin Core taxon fields.

## Instructions

### 1. Use official taxonomy behavior as evidence

Check:
- Species API: `https://techdocs.gbif.org/en/openapi/v1/species`
- taxonomy interpretation: `https://techdocs.gbif.org/en/data-processing/taxonomy-interpretation`
- checklist issues/flags: `https://techdocs.gbif.org/en/data-use/checklist-issues-and-flags`
- API downloads taxonomy support: `https://techdocs.gbif.org/en/data-use/api-downloads`.

GBIF supports multiple taxonomic contexts in occurrence processing. Store the selected `checklistKey` or the default taxonomy assumption used at match time.

### 2. Preserve source and normalized evidence

For every matched source name keep:
- source record ID or source row reference;
- raw submitted name from the archive;
- normalized input used for matching;
- request parameters, including rank, higher taxonomy hints and `checklistKey`;
- GBIF response fields: `usageKey`, `scientificName`, accepted usage where present, rank, status, `matchType`, `confidence`, alternatives and diagnostics;
- matching API version or documentation date where relevant;
- timestamp and tool version.

Do not overwrite raw names with normalized names. Store normalized names as derived evidence.

### 3. Classify matches conservatively

Default reliable match criteria:
- exact or high-confidence match at the expected taxonomic rank;
- accepted usage or resolvable synonym with accepted usage;
- no severe taxonomy issue that prevents linking source records to the target taxon.

Default problematic criteria:
- `matchType = HIGHERRANK`;
- match rank is higher than the expected record level;
- fuzzy, ambiguous or multiple-candidate result;
- low confidence or missing `usageKey`;
- conflict between identifier-based and name-based matching;
- checklist-specific mismatch between GBIF Backbone, COL XR or another taxonomy.

Thresholds and rule versions must be configurable and auditable. Do not silently promote problematic matches to reliable just because it simplifies filtering.

### 4. Manual decisions

For problematic names:
- create a review queue as CSV/Parquet/JSON suitable for human editing or later UI work;
- preload prior manual decisions and variants;
- show only new or changed unresolved names where practical;
- allow decisions such as accepted usage key, accepted name, synonym, verbatim scientific name, excluded spelling, deferred and rejected;
- record reviewer, decision timestamp, decision status, rationale, evidence source and supersession history.

Manual decisions must be replayable in later conversions. If a decision changes, keep the old decision as superseded rather than deleting it.

### 5. Output implications

Taxonomy enrichment should be optional and clearly marked in output metadata. Every enriched record should be traceable back to:
- source archive/file/row;
- raw scientific name;
- automatic match record;
- manual decision or variant, if used;
- GBIF/checklist evidence, if used.

Keep raw Darwin Core taxon fields available where practical so users can inspect the original source data.

### 6. Output expectations

When answering taxonomy-matching tasks, return:

1. Matching inputs and selected taxonomy/checklist.
2. Fields to store from GBIF.
3. Reliable/problematic classification rule.
4. Manual decision workflow.
5. Output files or metadata affected.
6. Re-run and supersession behavior.

## Checklist

- Are raw source names preserved?
- Are `usageKey`, `scientificName`, `matchType` and `confidence` stored?
- Are `HIGHERRANK` and rank mismatches problematic by default?
- Is `checklistKey` explicit where taxonomy matters?
- Are manual variants separate from automatic GBIF matches?
- Can a later output explain why a name was accepted, rejected or remapped?
