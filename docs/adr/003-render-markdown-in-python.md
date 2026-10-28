# ADR 003: Render Markdown in Python

Status: Accepted  
Date: 2026-10-23

## Context

The previous implementation used a Nunjucks template in the Obsidian plugin. The
template required workarounds for mutable state and was tied to Obsidian. The
user explicitly requested a Python project that renders the list-based Markdown
directly, without a template engine.

## Decision

Build the output in Python code in `render.py`. Do not add Jinja2, Nunjucks, or
another template engine.

## Consequences

- Rendering is testable with plain `unittest`.
- The formatting rules live in one place and are documented in
  `docs/output-format.md`.
- Changing the format requires code changes and tests, not template edits.
