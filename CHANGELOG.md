# Changelog

## 0.1.0 (2026-11-16)

First public release, extracted from a private setup.

- Lease throwaway Android emulators (APFS-cloned slot AVDs, `-read-only`) and iOS simulators
  (`simctl clone`) to parallel agent sessions, with a per-platform cap.
- `init` / `edit` / `rebuild` for the device masters; Android masters are created from the newest
  installed Google Play system image with hardware graphics acceleration.
- Owner detection for Claude Code, Codex, Gemini CLI, Copilot CLI, OpenCode and other agent CLIs.
- Guard hooks for Claude Code, Codex, Gemini CLI, Copilot CLI and OpenCode (`devlease hooks install`).
- Agent skill (`npx skills add gohlinka2/devlease`), AGENTS.md snippet, agent-oriented INSTALL.md.
- `config`, `doctor` and `uninstall` commands.
