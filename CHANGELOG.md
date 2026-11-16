# Changelog

## 0.2.0 (2026-11-16)

- Guard hooks now run only for shell tools and the configured device MCP servers (new `mcp_servers`
  setting, default `["mobile-mcp"]`), not for every MCP tool. Other MCP servers never start devlease.
  Changing `mcp_servers` / `mcp_tool_patterns` rewrites installed hooks. Run `devlease hooks install`
  once after upgrading to narrow existing hooks.
- `mcp_tool_patterns` now defaults to `["mobile_*"]` (extra globs only).

## 0.1.1 (2026-11-16)

- `uninstall` no longer lists the same hook file twice when run from the home directory.
- `init`/`doctor`/`uninstall` find the iOS master by name when its UDID is no longer in the config.
- Installer: fix the README link.

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
