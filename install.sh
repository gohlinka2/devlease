#!/bin/sh
# devlease installer: curl -fsSL https://raw.githubusercontent.com/gohlinka2/devlease/main/install.sh | sh
#
# Options (pass after `sh -s --` when piping):
#   --version <tag>   install a specific release (default: latest release, else main)
#   --bin-dir <dir>   where the devlease command goes (default: ~/.local/bin, or $DEVLEASE_BIN)
#   --uninstall       run `devlease uninstall` (asks which parts to remove)
set -eu

REPO="gohlinka2/devlease"
BIN_DIR="${DEVLEASE_BIN:-$HOME/.local/bin}"
SHARE_DIR="$HOME/.local/share/devlease"
VERSION=""
UNINSTALL=0

while [ $# -gt 0 ]; do
  case "$1" in
    --version) VERSION="$2"; shift 2 ;;
    --bin-dir) BIN_DIR="$2"; shift 2 ;;
    --uninstall) UNINSTALL=1; shift ;;
    -h|--help) sed -n '2,8p' "$0" 2>/dev/null || true; exit 0 ;;
    *) echo "devlease install: unknown option $1" >&2; exit 2 ;;
  esac
done

say() { printf '%s\n' "$*"; }
fail() { printf 'devlease install: %s\n' "$*" >&2; exit 1; }

if [ "$UNINSTALL" = 1 ]; then
  command -v devlease >/dev/null 2>&1 || fail "devlease is not on PATH"
  exec devlease uninstall
fi

[ "$(uname -s)" = "Darwin" ] || fail "devlease supports macOS only"
command -v python3 >/dev/null 2>&1 || fail "python3 not found (install Xcode command line tools: xcode-select --install)"
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' || fail "python 3.8+ required"
command -v curl >/dev/null 2>&1 || fail "curl not found"

if [ -z "$VERSION" ]; then
  latest=$(curl -fsSLI -o /dev/null -w '%{url_effective}' "https://github.com/$REPO/releases/latest" 2>/dev/null || true)
  case "$latest" in
    */tag/*) VERSION="${latest##*/tag/}" ;;
    *) VERSION="main" ;;
  esac
fi
case "$VERSION" in
  main) url="https://github.com/$REPO/archive/refs/heads/main.tar.gz" ;;
  *) url="https://github.com/$REPO/archive/refs/tags/$VERSION.tar.gz" ;;
esac

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
say "devlease: downloading $REPO@$VERSION"
curl -fsSL "$url" -o "$tmp/devlease.tar.gz" || fail "download failed: $url"
tar -xzf "$tmp/devlease.tar.gz" -C "$tmp"
src=$(find "$tmp" -mindepth 1 -maxdepth 1 -type d -name 'devlease-*' | head -n 1)
[ -n "$src" ] && [ -f "$src/devlease" ] || fail "unexpected archive layout"

mkdir -p "$BIN_DIR" "$SHARE_DIR"
if [ -L "$BIN_DIR/devlease" ]; then rm "$BIN_DIR/devlease"; fi
cp "$src/devlease" "$BIN_DIR/devlease"
chmod +x "$BIN_DIR/devlease"
rm -rf "$SHARE_DIR/skills" "$SHARE_DIR/snippets"
cp -R "$src/skills" "$src/snippets" "$SHARE_DIR/"
say "devlease: installed $("$BIN_DIR/devlease" --version) to $BIN_DIR/devlease"

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) say ""
     say "NOTE: $BIN_DIR is not on your PATH. Add it, e.g.:"
     say "  echo 'export PATH=\"$BIN_DIR:\$PATH\"' >> ~/.zshrc && export PATH=\"$BIN_DIR:\$PATH\"" ;;
esac

cat <<EOF

Next steps (see https://github.com/$REPO#setup):
  1. Agent skill (Claude Code, Codex, Gemini CLI, Copilot, OpenCode, Cursor, ...):
       npx skills add $REPO -g -y        (or: devlease skill install)
  2. Guard hooks for the agents you use (blocks device commands that skip the lease):
       devlease hooks install            (or name one: claude | codex | gemini | copilot | opencode)
  3. Always-on instructions: paste the output of \`devlease snippet\` into your global AGENTS.md / CLAUDE.md
  4. Create the device masters (opens a window for you to set each one up):
       devlease init android
       devlease init ios
  5. Check everything: devlease doctor
EOF
