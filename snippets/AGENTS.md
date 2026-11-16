## Mobile devices (emulators and simulators)

Several agents run in parallel on this machine and share its Android emulators and iOS simulators.
Never pick a device yourself, and never use a device you didn't lease:

- Before using a device, run `devlease acquire android --wait` (or `ios`) as its own command. It
  boots a fresh, throwaway device and prints its serial (e.g. `emulator-5580`) or UDID. Running it
  again prints the same device while you hold the lease.
- Always name that device explicitly: `adb -s <serial>`, `ANDROID_SERIAL=<serial> ./gradlew ...install...`,
  `xcrun simctl <cmd> <udid>` (never `booted` or `all`), `xcodebuild -destination 'id=<udid>'`. For the
  `device` argument of Mobile MCP (or a similar device MCP), use the MCP device id `devlease acquire`
  reports on stderr (`lease-android-<n>` on Android, the UDID on iOS); `devlease mine` shows it too.
- Run `devlease release` when you're done with devices. `devlease status` shows who holds what.
- Leased devices start clean and are discarded on release; install what you need each time.
- Don't start emulators or boot simulators directly, and don't run `adb kill-server`.
