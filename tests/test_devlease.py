"""Unit tests for devlease's guard logic, hook payload parsing, config and hook installation.

Run: python3 -m unittest discover -s tests
"""
import importlib.machinery
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
_TMP = tempfile.mkdtemp(prefix="devlease-test-")
os.environ["DEVLEASE_HOME"] = _TMP

loader = importlib.machinery.SourceFileLoader("devlease", str(ROOT / "devlease"))
spec = importlib.util.spec_from_loader("devlease", loader)
dl = importlib.util.module_from_spec(spec)
loader.exec_module(dl)

SERIAL = "emulator-5580"
UDID = "11111111-2222-3333-4444-555555555555"
OTHER_UDID = "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"
LEASED = {"android": {SERIAL}, "ios": {UDID}, "mcp": {"lease-android-0"}}
NONE = {"android": set(), "ios": set(), "mcp": set()}
PROTECTED = {"R5CRC47TCAK"}


def check(cmd, leased=LEASED):
    return dl.check_command(cmd, leased, PROTECTED)


class GuardTests(unittest.TestCase):
    def assertAllowed(self, cmd, leased=LEASED):
        self.assertIsNone(check(cmd, leased), cmd)

    def assertBlocked(self, cmd, leased=LEASED):
        self.assertIsNotNone(check(cmd, leased), cmd)

    def test_adb(self):
        self.assertAllowed(f"adb -s {SERIAL} install app.apk")
        self.assertAllowed("adb devices")
        self.assertAllowed(f"ANDROID_SERIAL={SERIAL} adb shell ls")
        self.assertAllowed(f"export ANDROID_SERIAL={SERIAL}; adb shell ls")
        self.assertAllowed('adb -s "$SERIAL" shell ls')
        self.assertBlocked('adb -s "$SERIAL" shell ls', NONE)
        self.assertBlocked("adb install app.apk")
        self.assertBlocked("adb -d shell ls")
        self.assertBlocked("adb kill-server")
        self.assertBlocked("adb -s emulator-5554 shell ls")
        self.assertBlocked("adb -s R5CRC47TCAK shell ls")
        self.assertIn("protected", check("adb -s R5CRC47TCAK shell ls"))

    def test_chains_and_wrappers(self):
        self.assertBlocked(f"adb -s {SERIAL} shell ls && adb install x.apk")
        self.assertBlocked("cd app; timeout 30 adb install x.apk")
        self.assertBlocked("bash -c 'adb install x.apk'")
        self.assertAllowed(f"bash -c 'adb -s {SERIAL} install x.apk'")
        self.assertAllowed("cat <<EOF > notes.md\nadb install x.apk\nEOF")
        self.assertAllowed("echo 'adb install x.apk is bad'")

    def test_gradle(self):
        self.assertAllowed("./gradlew assembleDebug")
        self.assertAllowed(f"ANDROID_SERIAL={SERIAL} ./gradlew :app:installDebug")
        self.assertBlocked("./gradlew installDebug")
        self.assertBlocked("./gradlew connectedAndroidTest")
        self.assertBlocked("ANDROID_SERIAL=emulator-5554 ./gradlew installDebug")

    def test_simctl(self):
        self.assertAllowed("xcrun simctl list devices")
        self.assertAllowed(f"xcrun simctl install {UDID} App.app")
        self.assertAllowed('xcrun simctl launch "$UDID" com.example', )
        self.assertBlocked("xcrun simctl install booted App.app")
        self.assertBlocked("xcrun simctl shutdown all")
        self.assertBlocked(f"xcrun simctl boot {OTHER_UDID}")
        self.assertBlocked("xcrun simctl openurl x://y")

    def test_xcodebuild(self):
        self.assertAllowed("xcodebuild -scheme App build")
        self.assertAllowed(f"xcodebuild -scheme App -destination 'id={UDID}' test")
        self.assertAllowed("xcodebuild -scheme App -destination 'generic/platform=iOS Simulator' build")
        self.assertBlocked("xcodebuild -scheme App -destination 'platform=iOS Simulator,name=iPhone 17' test")
        self.assertBlocked(f"xcodebuild -scheme App -destination 'id={OTHER_UDID}' test")
        self.assertBlocked("xcodebuild -scheme App test")

    def test_emulator_flutter_maestro(self):
        self.assertAllowed("emulator -list-avds")
        self.assertBlocked("emulator -avd Pixel_9a")
        self.assertAllowed(f"flutter run -d {SERIAL}")
        self.assertAllowed(f"flutter run --device-id={UDID}")
        self.assertAllowed("flutter test test/widget_test.dart")
        self.assertBlocked("flutter run")
        self.assertBlocked("flutter run -d all")
        self.assertBlocked("flutter test integration_test/app_test.dart")
        self.assertAllowed(f"maestro --device {SERIAL} test flow.yaml")
        self.assertBlocked("maestro test flow.yaml")

    def test_unrelated(self):
        self.assertAllowed("ls -la && git status")
        self.assertAllowed("devlease acquire android --wait")


class PayloadTests(unittest.TestCase):
    def test_claude_codex_gemini(self):
        for tool in ("Bash", "run_shell_command", "bash"):
            name, args, cwd = dl.normalize_payload({"tool_name": tool, "tool_input": {"command": "adb devices"},
                                                    "cwd": "/x"})
            self.assertEqual(dl.shell_command(name, args), "adb devices")
            self.assertEqual(cwd, "/x")

    def test_copilot_native(self):
        name, args, _ = dl.normalize_payload({"toolName": "bash", "toolArgs": json.dumps({"command": "adb devices"})})
        self.assertEqual(dl.shell_command(name, args), "adb devices")

    def test_codex_exec_list(self):
        name, args, _ = dl.normalize_payload({"tool_name": "exec_command", "tool_input": {"cmd": ["adb", "devices"]}})
        self.assertEqual(dl.shell_command(name, args), "adb devices")

    def test_non_shell(self):
        name, args, _ = dl.normalize_payload({"tool_name": "Read", "tool_input": {"file_path": "/x"}})
        self.assertIsNone(dl.shell_command(name, args))

    def test_mcp_names(self):
        cfg = dl.load_config()
        for tool in ("mcp__mobile-mcp__mobile_take_screenshot", "mcp_mobile-mcp_mobile_take_screenshot",
                     "mobile-mcp/mobile_take_screenshot", "mobile-mcp_mobile_take_screenshot",
                     "mobile_take_screenshot"):
            self.assertEqual(dl.mcp_tool_device(tool, {"device": "lease-android-0"}, cfg), "lease-android-0", tool)
        self.assertIsNone(dl.mcp_tool_device("mcp__github__get_issue", {"device": "x"}, cfg))
        self.assertIsNone(dl.mcp_tool_device("mcp__mobile-mcp__mobile_list_available_devices", {}, cfg))


class HookTests(unittest.TestCase):
    def run_hook(self, payload, leased):
        stdin = io.StringIO(json.dumps(payload))
        with mock.patch.object(dl, "leased_devices", return_value=leased), \
                mock.patch.object(dl, "current_owner", return_value={"agent_pid": 1, "worktree": "/x"}), \
                mock.patch.object(sys, "stdin", stdin), redirect_stderr(io.StringIO()) as e:
            try:
                return dl.hook_pretool(), e.getvalue()
            except SystemExit as ex:
                return ex.code, e.getvalue()

    def test_blocks_with_exit_2(self):
        code, msg = self.run_hook({"tool_name": "Bash", "tool_input": {"command": "adb install x.apk"}}, LEASED)
        self.assertEqual(code, 2)
        self.assertIn("devlease: blocked", msg)

    def test_allows(self):
        code, _ = self.run_hook({"tool_name": "Bash", "tool_input": {"command": f"adb -s {SERIAL} install x"}}, LEASED)
        self.assertEqual(code, 0)

    def test_mcp(self):
        p = {"tool_name": "mcp__mobile-mcp__mobile_take_screenshot", "tool_input": {"device": "lease-android-1"}}
        self.assertEqual(self.run_hook(p, LEASED)[0], 2)
        p["tool_input"]["device"] = "lease-android-0"
        self.assertEqual(self.run_hook(p, LEASED)[0], 0)

    def test_garbage(self):
        with mock.patch.object(sys, "stdin", io.StringIO("not json")):
            self.assertEqual(dl.hook_pretool(), 0)


class OwnerTests(unittest.TestCase):
    def test_node_cli_detected_by_script_name(self):
        self.assertTrue(dl.is_agent(dl._names("node", "node /opt/homebrew/bin/gemini --yolo")))
        self.assertTrue(dl.is_agent(dl._names("/opt/homebrew/bin/copilot", "copilot")))
        self.assertTrue(dl.is_agent(dl._names("claude", "claude --resume")))
        self.assertFalse(dl.is_agent(dl._names("node", "node server.js")))
        self.assertFalse(dl.is_agent(dl._names("zsh", "-zsh")))


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.patch = mock.patch.dict(dl.HARNESSES, {
            "claude": (self.tmp / "claude.json",) + dl.HARNESSES["claude"][1:],
            "gemini": (self.tmp / "gemini.json",) + dl.HARNESSES["gemini"][1:],
            "copilot": (self.tmp / "hooks/devlease.json",) + dl.HARNESSES["copilot"][1:],
            "opencode": (self.tmp / "plugins/devlease.js",) + dl.HARNESSES["opencode"][1:],
        })
        self.patch.start()
        self.launch = mock.patch.object(dl, "launcher", return_value="/usr/local/bin/devlease")
        self.launch.start()

    def tearDown(self):
        self.patch.stop()
        self.launch.stop()

    def test_settings_roundtrip_keeps_other_hooks(self):
        path = self.tmp / "claude.json"
        other = {"matcher": "*", "hooks": [{"type": "command", "command": "other-tool"}]}
        path.write_text(json.dumps({"model": "x", "hooks": {"PreToolUse": [other]}}))
        with redirect_stderr(io.StringIO()):
            dl.install_hooks("claude", False)
            dl.install_hooks("claude", False)  # idempotent
        data = json.loads(path.read_text())
        pre = data["hooks"]["PreToolUse"]
        self.assertEqual(len(pre), 2)
        self.assertEqual(pre[1]["matcher"], "Bash|mcp__.*")
        self.assertEqual(pre[1]["hooks"][0]["command"], "/usr/local/bin/devlease hook pretool")
        self.assertEqual(len(data["hooks"]["SessionEnd"]), 1)
        self.assertTrue(dl.hooks_installed("claude", False))
        with redirect_stderr(io.StringIO()):
            self.assertTrue(dl.uninstall_hooks("claude", False))
        data = json.loads(path.read_text())
        self.assertEqual(data, {"model": "x", "hooks": {"PreToolUse": [other]}})
        self.assertFalse(dl.hooks_installed("claude", False))

    def test_old_absolute_hook_is_replaced(self):
        path = self.tmp / "claude.json"
        old = {"matcher": "Bash|mcp__mobile-mcp__.*",
               "hooks": [{"type": "command", "command": "~/.local/bin/devlease hook pretool", "timeout": 10}]}
        path.write_text(json.dumps({"hooks": {"PreToolUse": [old]}}))
        with redirect_stderr(io.StringIO()):
            dl.install_hooks("claude", False)
        pre = json.loads(path.read_text())["hooks"]["PreToolUse"]
        self.assertEqual(len(pre), 1)
        self.assertEqual(pre[0]["matcher"], "Bash|mcp__.*")

    def test_gemini_ms_timeout(self):
        with redirect_stderr(io.StringIO()):
            dl.install_hooks("gemini", False)
        entry = json.loads((self.tmp / "gemini.json").read_text())["hooks"]["BeforeTool"][0]
        self.assertEqual(entry["matcher"], "run_shell_command|mcp_.*")
        self.assertEqual(entry["hooks"][0]["timeout"], 10000)

    def test_copilot_and_opencode_files(self):
        with redirect_stderr(io.StringIO()):
            dl.install_hooks("copilot", False)
            dl.install_hooks("opencode", False)
        cop = json.loads((self.tmp / "hooks/devlease.json").read_text())
        self.assertEqual(cop["hooks"]["PreToolUse"][0]["bash"], "/usr/local/bin/devlease hook pretool")
        js = (self.tmp / "plugins/devlease.js").read_text()
        self.assertIn('const DEVLEASE = "/usr/local/bin/devlease"', js)
        self.assertIn('ctx.tool.hook("execute.before"', js)
        with redirect_stderr(io.StringIO()):
            self.assertTrue(dl.uninstall_hooks("copilot", False))
            self.assertTrue(dl.uninstall_hooks("opencode", False))
        self.assertFalse((self.tmp / "plugins/devlease.js").exists())


class ConfigTests(unittest.TestCase):
    def test_set_and_merge(self):
        with redirect_stderr(io.StringIO()):
            dl.set_config_value("android.slots", 3)
        cfg = dl.load_config()
        self.assertEqual(cfg["android"]["slots"], 3)
        self.assertEqual(cfg["android"]["base_port"], 5580)
        self.assertEqual(json.loads(dl.CONFIG.read_text()), {"android": {"slots": 3}})
        dl.CONFIG.unlink()

    def test_generic_defaults(self):
        cfg = dl.DEFAULT_CONFIG
        self.assertEqual(cfg["protected_serials"], [])
        self.assertIsNone(cfg["android"]["template_avd"])
        self.assertIsNone(cfg["ios"]["device_type"])


if __name__ == "__main__":
    unittest.main()
