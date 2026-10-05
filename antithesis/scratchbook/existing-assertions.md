---
sut_path: /home/exedev/wellnest
commit: 9e9e52f1a8f7948ebfc911fe95571579a1ff37c5
updated: 2026-10-05
external_references:
  - path: https://github.com/sy00n89/wellnest
    why: Upstream repo named by the user as the outside source; checked for issues, PRs, and wiki (no issues, no wiki, one merged PR #1 "local dev").
---

# Existing Antithesis Assertions

## Summary

The codebase has **no existing Antithesis instrumentation**.

Scan performed:

- Case-insensitive search for `antithesis` across `*.py`, `*.js`, `*.jsx`, `*.json`, `*.txt` in the repo, excluding `node_modules/` and `.claude/`: no matches.
- No `antithesis` package in `backend/requirements.txt`, `backend/requirements-dev.txt`, `mocks/anthropic/requirements.txt`, or `package.json`.
- No calls to `always`, `sometimes`, `reachable`, `unreachable`, `always_or_unreachable`, or `setup_complete` from any Antithesis SDK.

Every SUT-side assertion suggested in `properties/*.md` is therefore **missing** and would be new.

## Assumptions

- The `.claude/worktrees/claude-md/` directory is an untracked, stale copy of the repo and is not part of the SUT.

## Open Questions

- None.
