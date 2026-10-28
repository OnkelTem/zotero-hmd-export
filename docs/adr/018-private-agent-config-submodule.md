# ADR 018: Private agent configuration submodule

Status: Accepted
Date: 2026-10-28

## Context

The main repository is public, but agent definitions and skills are private.
They also need versioning so different projects can use different revisions.
Keeping `.opencode` in the main repository would publish the agent configuration
and couple its history to the application code.

OpenCode discovers `.opencode` in the project and its ancestors, plus the global
config. A sibling directory is not discovered automatically. Skills and agents
therefore need a project-visible mount.

## Decision

- Keep agents and skills in a private repository, separate from the application.
- Consume it as a git submodule at `agents/`.
- Track `.opencode` as a symlink to `agents/.opencode` so OpenCode discovers the
  config, agents, and skills.
- Pin a commit or tag in the main repository. Different projects may pin
  different revisions.
- Keep only the project-specific `feature-manager` skill in the private
  repository. Global `py-manager`, `docs-manager`, and `ask-user` remain global.
- Reference `agents/AGENTS.md` from the main `AGENTS.md`; do not load it
  automatically through `instructions`.
- The main project must build and test without the submodule. Without it, local
  agents and `feature-manager` are unavailable; use the main `AGENTS.md` and
  global skills.
- Document the private submodule and the clone/init command in `README.md`.
- Do not commit agent secrets or private URLs beyond the submodule URL required
  by `.gitmodules`.

## Alternatives

- **`.opencode` in the main repository**: simplest discovery, but publishes
  private agent configuration and couples agent history to application history.
- **Global skills only**: no private content, but no project-specific versioning
  or isolation.
- **Sibling repository plus a relative symlink**: works locally but is not
  reproducible; clones depend on an external checkout and an unpinned version.
- **Submodule directly at `.opencode`**: clean and symlink-free, but requires the
  agents repository root to be the `.opencode` contents. The selected layout
  keeps the agents repository root available for `AGENTS.md` and other files.
- **`opencode.json` paths to a sibling repository**: can load skills, but does
  not reliably load markdown agent definitions and relative instruction paths
  are awkward.

## Consequences

- The public repository contains a submodule gitlink, `.gitmodules`, and a
  symlink, but no agent or skill content.
- Clones that need agent tooling require access to the private submodule:
  `git clone --recurse-submodules` or `git submodule update --init`.
- Clones without access can still install, lint, and test the exporter.
- Worktrees require `git submodule update --init` in each worktree.
- `.gitmodules` exposes the private repository URL. This is accepted in exchange
  for reproducibility.
- Updating agents is an explicit submodule commit change, not a moving symlink.
