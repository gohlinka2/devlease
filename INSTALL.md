# Installing devlease (instructions for AI agents)

You are installing [devlease](https://github.com/gohlinka2/devlease) for your user. It gives each
agent session its own throwaway Android emulator / iOS simulator. Follow the steps in order, tell
the user what you did after each, and ask when a step needs their decision. Don't skip the
questions marked **Ask**.

## 1. Check prerequisites

```bash
uname -s                 # must be Darwin (macOS only)
python3 --version        # 3.8+
```

If either fails, stop and tell the user devlease can't run here.

## 2. Install the CLI

Use Homebrew if the user prefers it and `brew` exists, otherwise the installer script:

```bash
curl -fsSL https://raw.githubusercontent.com/gohlinka2/devlease/main/install.sh | sh
# or: brew install gohlinka2/tap/devlease
```

The script puts `devlease` in `~/.local/bin`. If it reports that this directory isn't on `PATH`,
add the line it prints to the user's shell profile (`~/.zshrc` by default) and use the full path
`~/.local/bin/devlease` for the rest of this session. Then run `devlease --version`.

## 3. Install the agent skill

```bash
npx skills add gohlinka2/devlease -g -y
```

This installs the `devlease` skill for every agent harness it detects (Claude Code, Codex, Gemini
CLI, Copilot, OpenCode, Cursor, ...). If `npx` isn't available, run `devlease skill install`
instead (copies it to `~/.claude/skills` and `~/.agents/skills`).

## 4. Install the guard hooks

**Ask** the user which agents they use (suggest the ones detected by `devlease hooks status` /
installed on the machine), then:

```bash
devlease hooks install            # every detected harness, or name them:
devlease hooks install claude     # claude | codex | gemini | copilot | opencode
```

The hooks block device commands that don't name the session's own leased device. Hooks take effect
in new agent sessions. Codex may ask the user to review the new hook (`/hooks`).

## 5. Add the always-on instructions

`devlease snippet` prints a short section for the agent's global instructions. Append it (don't
overwrite) to the global instructions file of each harness the user uses, unless a section about
devlease is already there:

| Harness | File |
|---------|------|
| Claude Code | `~/.claude/CLAUDE.md` |
| Codex CLI | `~/.codex/AGENTS.md` |
| Gemini CLI | `~/.gemini/GEMINI.md` |
| Copilot CLI | `~/.copilot/instructions/devlease.instructions.md` |
| OpenCode | `~/.config/opencode/AGENTS.md` |

```bash
{ echo; devlease snippet; } >> ~/.claude/CLAUDE.md
```

If the user has a physical device they never want agents to touch, **ask** for its serial
(`adb devices` lists it) and protect it: `devlease config set protected_serials '["<serial>"]'`.

## 6. Configure the pool

**Ask** how many devices may run at once per platform (default 2 each; each emulator needs roughly
2-4 GB of RAM, so 2 is right for 16 GB, 3-4 for 32 GB+). Then, if they want a different number:

```bash
devlease config set android.slots 3
devlease config set ios.slots 3
```

Also ask whether they want Android, iOS, or both. Other settings: see the README's Configuration
section (`devlease config` shows them all).

## 7. Create the device masters (the user does this step)

Each master opens in a window for the user to set up by hand: sign in to accounts, set the locale,
enable developer options, install apps, and so on. Everything on the master is on every leased
device. Ask the user to run these in their own terminal (they block until the window is closed):

```bash
devlease init android     # Android Studio's SDK with a Google Play phone system image is required
devlease init ios         # Xcode with an iOS simulator runtime is required
```

If the user wants clean devices with no manual setup, you may run
`devlease init android --no-setup` / `devlease init ios --no-setup` yourself (takes a few minutes).
If `init android` reports that no system image is installed, tell the user to install one in Android
Studio (Settings > Languages & Frameworks > Android SDK > SDK Platforms, a "Google Play" image for
their CPU).

Later, `devlease edit android|ios` changes a master's data and rebuilds the leased copies.

## 8. Recommend Mobile MCP

devlease only leases devices. To let agents drive them (tap, type, screenshot, read the UI),
recommend [Mobile MCP](https://github.com/mobile-next/mobile-mcp) if the user doesn't have a device
MCP yet. Agents pass the *MCP device id* that `devlease acquire` prints as the MCP's `device`
argument. The guard hook checks Mobile MCP (server name `mobile-mcp`) by default. If the user
registered Mobile MCP under another name, or uses a different device MCP, set the server names as they
appear in the agent's MCP config, e.g. `devlease config set mcp_servers '["mobile-mcp", "my-device-mcp"]'`
(installed hooks are updated automatically). Don't add non-device MCPs.

## 9. Verify

```bash
devlease doctor
```

Everything except the masters should be `[ok]` before step 7; everything after it. If masters
exist, do a quick test: `devlease acquire android --wait`, then `adb -s <serial> shell getprop
ro.product.model`, then `devlease release`. Finally, tell the user that new agent sessions pick up
the skill, hooks and instructions, and how to uninstall: `devlease uninstall`.
