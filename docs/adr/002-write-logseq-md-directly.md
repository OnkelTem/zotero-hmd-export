# ADR 002: Write Markdown files directly to a configured directory

Status: Accepted  
Date: 2026-10-23

## Context

The target is a directory of Markdown pages, often a file-based Logseq graph's
`pages` folder. A Logseq graph is not required by the writer; the same output can
be consumed by any Markdown tool. Using an application API would add setup,
authentication, and coupling.

## Decision

Write generated Markdown files directly to `output_dir`, which points to the
final pages directory. Use an atomic replace. Do not use the Logseq HTTP API.
Do not infer a graph root or append `pages`. Keep application names out of code
identifiers; comments may mention Logseq.

## Consequences

- The output directory must already exist.
- A consumer such as Logseq may need a page reopened or a re-index to show an
  external write.
- No API server or token is required.
- A DB-backed consumer would require a different writer and a new ADR.
