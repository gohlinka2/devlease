---
name: devlease
description: Lease a private, throwaway Android emulator or iOS simulator with `devlease` before running, installing, testing or screenshotting a mobile app, and use only that device. Use whenever you are about to touch an emulator or simulator (adb, gradle install/connectedCheck, xcrun simctl, xcodebuild test/run, flutter run, maestro, Mobile MCP or another device MCP), when a device command was blocked by devlease, or when the user mentions devlease, leased devices, or several agents sharing emulators/simulators.
---

# devlease: use only the device you leased

Several agents share this machine's emulators and simulators. `devlease` gives each agent session its
own fresh device, cloned from a master the user set up, and discards it on release. Never pick a
device yourself and never use one you didn't lease: other agents and the user's own devices are on
the same machine.

## Lease

Run this as its own command, before any device work:

```bash
devlease acquire android --wait     # or: devlease acquire ios --wait
```

- stdout: the device. Android serial (e.g. `emulator-5580`) or iOS simulator UDID.
- stderr: the **MCP device id** for Mobile MCP and similar tools: `lease-android-<n>` on Android
  (the AVD name), the UDID on iOS.
- Booting takes ~10-60 s; `--wait` waits if all slots are busy. Running it again prints the same
  device while you hold the lease, so call it again (or `devlease mine`) in each new shell instead
  of remembering the serial. `devlease mine` prints `platform<TAB>serial/UDID<TAB>mcp: <id>`.
- The device starts clean (only what the user put on the master). Install your app every time.

## Use it explicitly, every time

| Tool | Do | Never |
|------|----|-------|
| adb | `adb -s <serial> ...` | bare `adb install`, `adb -d/-e`, `adb kill-server` |
| Gradle | `ANDROID_SERIAL=<serial> ./gradlew installDebug` / `connectedCheck` | install/connected tasks without `ANDROID_SERIAL` |
| simctl | `xcrun simctl <cmd> <udid> ...` | `booted`, `all` |
| xcodebuild | `-destination 'id=<udid>'` | `name=iPhone ...` destinations |
| Flutter | `flutter run -d <serial/udid>` | no `-d`, `-d all` |
| Maestro | `maestro --device <serial/udid> test ...` | no `--device` |
| Mobile MCP / device MCPs | pass the MCP device id as the `device` argument | devices from `mobile_list_available_devices` you didn't lease |
| Emulator / Simulator | let devlease boot them | `emulator -avd ...`, `simctl boot`, opening Simulator.app |

Each shell call may be a fresh shell, so set the variable in the same call you use it:

```bash
SERIAL=$(devlease acquire android --wait) && adb -s "$SERIAL" install -r app.apk
```

## Release

```bash
devlease release            # all your devices; or: devlease release android
```

Release when you are done with device work. Leases are also freed automatically when your session
ends, but releasing early frees the slot for other agents. `devlease status` shows every slot and
who holds it.

## When something goes wrong

- **A command was blocked by devlease** (a hook checks device commands): read the reason, then
  re-run it with your leased serial/UDID. Don't work around the hook.
- **"all slots are taken"**: use `--wait`. Don't release other agents' devices.
- **"master missing" / "slot AVD missing"**: the user hasn't set devlease up yet. Ask them to run
  `devlease init android` (or `ios`) in their own terminal; it opens a window for manual setup. Run
  `devlease doctor` to see what is missing.
- **Device misbehaves**: `devlease release android` then acquire again for a fresh one.
- Don't edit devlease's config or masters (`init`, `edit`, `rebuild`, `config set`) unless the user
  asks you to.
