# devlease

**Give every AI coding agent its own throwaway Android emulator or iOS simulator.**

When several agents (Claude Code, Codex, Gemini CLI, Copilot CLI, OpenCode, ...) work in parallel on
one Mac, they fight over the same emulators and simulators: one agent installs over another's app,
`adb install` hits every connected device (including your own phone), and `simctl ... booted` picks
whatever happens to be running. `devlease` fixes that with short-lived device **leases**:

- `devlease acquire android --wait` boots a fresh device for the calling agent session and prints its
  serial/UDID. Each device is cloned from a **master** you set up once (sign-ins, settings, apps), so
  every lease starts from the same clean state.
- `devlease release` throws the device away. Leases are also freed automatically when the agent
  session ends or its process exits.
- The number of devices per platform is capped (`android.slots`, `ios.slots`) so your RAM survives.
- Optional **guard hooks** block device commands that don't target the session's own lease
  (`adb` without `-s`, `simctl booted`, Gradle `installDebug` without `ANDROID_SERIAL`, a Mobile MCP
  call with someone else's device, ...), and tell the agent what to do instead.

```text
$ devlease acquire android --wait
devlease: android-0 ready in 9 s (serial emulator-5580, MCP device id: lease-android-0)
emulator-5580
$ adb -s emulator-5580 install app.apk
$ devlease release
devlease: released android-0 (emulator-5580)
```

devlease only **leases** devices. It doesn't tap, swipe or screenshot. For that, pair it with
[**Mobile MCP**](https://github.com/mobile-next/mobile-mcp) (recommended) or any similar device MCP
that takes a device id: pass it the *MCP device id* that `devlease acquire` prints. The guard hook
checks Mobile MCP out of the box; add other device MCPs with
`devlease config set mcp_servers '["mobile-mcp", "<other-server>"]'`.

> **Requirements:** macOS, Python 3.8+ (ships with Xcode's command line tools). Android: Android
> Studio's SDK with the emulator and at least one phone system image. iOS: Xcode with an iOS
> simulator runtime. Linux and Windows are not supported.

## Install

### Let your agent do it

Paste this into your agent:

> Install devlease for me by following https://github.com/gohlinka2/devlease/blob/main/INSTALL.md

[INSTALL.md](INSTALL.md) is written for agents. It installs the CLI, the skill, the hooks and the
instructions for the harnesses you use, then asks you to set up the device masters.

### By hand

```bash
# 1. CLI (to ~/.local/bin; needs it on PATH)
curl -fsSL https://raw.githubusercontent.com/gohlinka2/devlease/main/install.sh | sh
#    or with Homebrew:
brew install gohlinka2/tap/devlease

# 2. Agent skill: Claude Code, Codex, Gemini CLI, Copilot, OpenCode, Cursor and many more
npx skills add gohlinka2/devlease -g -y        # or: devlease skill install

# 3. Guard hooks for the agents you use (all detected ones by default)
devlease hooks install                          # or: devlease hooks install claude

# 4. Always-on instructions: append the snippet to your global agent instructions
devlease snippet >> ~/.claude/CLAUDE.md         # see the table below for other agents

# 5. Device masters: each opens a window, you set the device up and close it
devlease init android
devlease init ios

devlease doctor                                 # check everything
```

## Setting up the masters

Each platform has one master device. Leased devices are cloned from it, so whatever you put on the
master (Google/Apple sign-in, locale, developer options, disabled animations, test accounts, apps)
is there on every lease.

| Command | What it does |
|---------|--------------|
| `devlease init android` | Creates a fresh `lease-master-android` AVD from the newest installed Google Play system image (Pixel-sized, hardware graphics acceleration), opens it in a window for you to set up, and when you close the window builds the slot AVDs. |
| `devlease init ios` | Creates a fresh `lease-master-ios` simulator (newest iPhone and iOS runtime), opens it in Simulator for you to set up, and waits until you shut it down. |
| `devlease edit android\|ios` | Opens the existing master again to change its data, then rebuilds the slots. Use this whenever the starting state should change. |
| `devlease rebuild android` | Rebuilds the slot AVDs from the master without opening it (e.g. after changing `android.slots`). |
| `devlease init <platform> --no-setup` | Skips the window: a clean, untouched device. |
| `devlease init <platform> --force` | Deletes the master (and its slots) and starts over. |

The masters must be closed while agents lease devices, and `init`/`edit`/`rebuild` refuse to run
while any device is leased.

How the clones work: on Android every slot is an APFS copy-on-write clone of the master AVD with its
own quick-boot snapshot (so it boots in seconds and uses almost no extra disk), started with
`emulator -read-only` so nothing it does is kept. On iOS each lease is `xcrun simctl clone` of the
master, deleted on release.

## Using it (what agents do)

```bash
devlease acquire android --wait   # or ios; stdout: serial/UDID, stderr: MCP device id
devlease mine                     # this session's devices
devlease release                  # discard them
devlease status                   # every slot and who holds it
```

The [skill](skills/devlease/SKILL.md) and the [snippet](snippets/AGENTS.md) teach agents the rules:
lease first, always name the device (`adb -s`, `ANDROID_SERIAL=`, `simctl <udid>`,
`xcodebuild -destination id=`, `flutter -d`, `maestro --device`, the MCP `device` argument), release
when done.

**Who owns a lease?** The nearest ancestor agent process of the `devlease` call (`claude`, `codex`,
`gemini`, `copilot`, `opencode`, `cursor-agent`, `amp`, `goose`, `droid`, `qwen`, `kiro-cli`,
`crush`, `aider`, `cline`, `auggie`, `kimi`, `junie`; add more with `config set agent_names`). The
agent's shell commands and its hooks resolve to the same process, so two sessions in the same
repository still get different devices. Run from a plain terminal, the owner is the git worktree.
Set `DEVLEASE_OWNER_PID` to override.

## Agent harness support

| Harness | Skill | Guard hook | Release on session end |
|---------|-------|------------|------------------------|
| Claude Code | yes | `PreToolUse` in `~/.claude/settings.json` | `SessionEnd` |
| Codex CLI | yes | `PreToolUse` in `~/.codex/hooks.json` (Codex may ask you to trust it via `/hooks`) | `SessionEnd` |
| Gemini CLI | yes | `BeforeTool` in `~/.gemini/settings.json` | `SessionEnd` |
| GitHub Copilot CLI | yes | `~/.copilot/hooks/devlease.json` | `SessionEnd` |
| OpenCode (v2) | yes | plugin `~/.config/opencode/plugins/devlease.js` | when the process exits |
| Cursor CLI, Amp, Goose, Droid, Kiro, Cline, others | yes (via `npx skills`) | instructions only | when the process exits |

`devlease hooks install` with no argument installs hooks for every harness it detects; add
`--project` to write the project's config (e.g. `.claude/settings.json`) instead of your user
config. Existing hook entries are kept, and a `.devlease-backup` copy is written first.
The Claude Code hook is used every day. The Codex, Gemini, Copilot and OpenCode hooks follow those
tools' documented hook formats and are covered by unit tests. Please open an issue if one misbehaves.

Where to put the snippet (`devlease snippet`) so it's always in context:

| Harness | Global instructions file |
|---------|--------------------------|
| Claude Code | `~/.claude/CLAUDE.md` |
| Codex CLI | `~/.codex/AGENTS.md` |
| Gemini CLI | `~/.gemini/GEMINI.md` |
| Copilot CLI | `~/.copilot/instructions/devlease.instructions.md` |
| OpenCode | `~/.config/opencode/AGENTS.md` |
| Per project | the repository's `AGENTS.md` |

The skill holds the details and loads when an agent is about to touch a device. The snippet is
short and always loaded, so agents don't run `adb` before they think of the skill. Use both.

## Configuration

`devlease config` prints the effective settings; `devlease config set KEY VALUE` changes one
(values are JSON, or a plain string). Only changed keys are stored, in `~/.devlease/config.json`.

| Key | Default | Meaning |
|-----|---------|---------|
| `android.slots` / `ios.slots` | `2` | Max devices leased at once per platform. Each running emulator takes ~2-4 GB RAM. Run `devlease rebuild android` after changing `android.slots`. |
| `android.system_image` | newest installed | e.g. `system-images;android-36;google_apis_playstore;arm64-v8a` |
| `android.template_avd` | `null` | Copy the hardware config of one of your AVDs instead of the built-in phone profile. |
| `android.avd_config` | `{}` | Extra `config.ini` values for the master, e.g. `{"hw.ramSize": "4096"}`. |
| `android.headless` | `true` | `false` shows leased emulators in a window. |
| `android.base_port` | `5580` | Slot *n* runs on port `base_port + 2n` (serial `emulator-<port>`). |
| `android.boot_timeout_s` | `240` | |
| `ios.device_type` / `ios.runtime` | newest iPhone / iOS | Used by `devlease init ios`, e.g. `com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro`. |
| `protected_serials` | `[]` | Devices agents must never touch, e.g. your physical phone's serial. |
| `agent_names` | `[]` | Extra agent process names for owner detection. |
| `mcp_servers` | `["mobile-mcp"]` | Device MCP servers (the name you gave the server in your agent's MCP config) whose `device` argument the guard hook checks. Hooks only run for these servers' tools; other MCP servers (Figma, GitHub, ...) never reach devlease. Installed hooks update automatically when you change this. |
| `mcp_tool_patterns` | `["mobile_*"]` | Extra tool-name globs, for agents that call MCP tools without the server prefix. |
| `mcp_device_args` | `["device", "deviceId", "device_id", "udid", "serial"]` | Argument names that carry the device id. |

Environment: `DEVLEASE_HOME` (state dir, default `~/.devlease`), `ANDROID_HOME` /
`ANDROID_AVD_HOME`, `DEVLEASE_OWNER_PID`, `DEVLEASE_HOOK=off` (disable the guard),
`DEVLEASE_HOOK_LOG=<file>` (log raw hook payloads).

## Uninstall

```bash
devlease uninstall            # lists everything and asks step by step (devices, hooks, skill, state, binary)
devlease uninstall --dry-run  # only list
devlease uninstall --all      # remove everything without asking (or pick: --devices --hooks --skill --state --binary)
```

Only devices devlease created are deleted (`lease-master-android`, `lease-android-*`, the iOS master
and `lease-ios-*`), never your own AVDs or simulators. Homebrew installs: `brew uninstall devlease`
for the command itself.

## Development

```bash
git clone https://github.com/gohlinka2/devlease && cd devlease
ln -sf "$PWD/devlease" ~/.local/bin/devlease     # use the checkout (skill and snippet are found next to it)
python3 -m unittest discover -s tests
```

`devlease` is a single Python file with no dependencies.

## Disclaimer

This tool was built agentically: the code and docs were written by AI coding agents under human
direction and review, not by hand. It has been used daily on one machine; test it on yours before
you rely on it, and report problems in the issues.

## License

[MIT](LICENSE)
