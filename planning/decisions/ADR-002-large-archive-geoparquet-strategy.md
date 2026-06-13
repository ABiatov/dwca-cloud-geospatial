# ADR-002: Large Archive GeoParquet Strategy

Status: Accepted

Date: 2026-06-12

## Context

The converter is expected to handle large Darwin Core Archive occurrence
datasets, including archives with tens of millions of records.

Prompt 07 implemented a streaming PyArrow GeoParquet writer that writes
accepted normalized occurrence records into Parquet row groups. However, the
current parser and normalizer APIs still materialize records before writer
handoff in tests and future orchestration.

GeoParquet reading and writing guidance in the local Geomermaids cookbooks
highlights that cloud-native spatial query performance depends on right-sized
row groups, ZSTD compression, row-group pruning metadata, spatial ordering and,
when appropriate, partitioned datasets.

## Decision

The project must implement an end-to-end chunked large-archive pipeline before
claiming support for tens of millions of occurrence records.

The required large-archive pipeline shape is:

- streaming/chunked occurrence reader;
- chunked normalization result handoff;
- streaming GeoParquet accepted-record writer;
- streaming rejected-record/report writer;
- bounded-memory counts and warning aggregation.

For large GeoParquet outputs:

- GeoParquet remains `1.1.0` by default for broad compatibility.
- WKB point geometry remains the default geometry encoding.
- ZSTD compression and row groups around 100,000 rows remain default writer
  settings.
- A GeoParquet 1.1 covering `bbox` struct column is default-on for large
  outputs.
- Spatial sorting is default-on for large outputs and strategy-configurable.
- Partitioned GeoParquet dataset output is an optional large-dataset mode
  enabled by explicit configuration or a documented threshold.

Partitioning may use source attributes, administrative attributes or a coarse
spatial grid depending on the expected query pattern. It must remain a
file-based output mode and must not require a permanent database or API
service.

## Consequences

The core conversion API should not lock future implementation into fully
materialized accepted or rejected record tuples when iterators or chunked
result objects can preserve the same semantics.

Processing metadata must reconcile counts, conversion failures, warnings,
file-level bounds, output record counts and rejected reports after chunked
processing.

GeoParquet validators should distinguish baseline small-output validity from
large-output optimization requirements. Small fixtures and small local outputs
may omit the covering bbox column until the implementation exists, but
large-output conversion must not rely only on file-level bbox metadata.

Future CLI and core options should expose large-output behavior explicitly,
including bbox covering, spatial sort strategy, partitioning mode, partition
key and threshold when applicable.

## Deferred

- Choosing the first production spatial sort implementation.
- Defining exact large-output thresholds.
- Implementing partitioned GeoParquet output.
- Evaluating GeoParquet 2.0 as an opt-in post-MVP output after downstream
  reader support is proven.

## Follow-Up Work

- Update bundle metadata writers to record large-output options and strategies.
- Update validation to check large-output declarations and GeoParquet bbox
  covering when present.
- Design chunked parser and normalization handoff objects.
- Add bounded-memory large fixture or synthetic benchmark tests before MVP
  hardening claims large-archive support.
