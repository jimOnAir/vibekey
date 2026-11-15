#!/bin/bash
# build.sh — build the vibekey package from the committed HEAD.
#
#   ./build.sh                  build (pkgrel unchanged)
#   ./build.sh --bump "why"     commit a pkgrel+1 bump, then build
#   ./build.sh --install        also sudo pacman -U the result
#
# The artifact is deterministic w.r.t. git: it packages `git archive HEAD`,
# so an unclean tree is a hard error (pass --allow-dirty to override).
# Output lands in dist/ (kept git-ignored; the last 3 builds are retained).
set -euo pipefail

here="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
cd "$here"

bump="" install=0 allow_dirty=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --bump)    bump="${2:?--bump needs a message}"; shift 2 ;;
    --install) install=1; shift ;;
    --allow-dirty) allow_dirty=1; shift ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

command -v makepkg >/dev/null || { echo "makepkg not found (Arch required)" >&2; exit 1; }

if [[ $allow_dirty -eq 0 && -n $(git status --porcelain) ]]; then
  echo "working tree is dirty — the package would not match any commit." >&2
  echo "commit first, or re-run with --allow-dirty." >&2
  exit 1
fi

if [[ -n $bump ]]; then
  rel=$(grep -E '^pkgrel=' PKGBUILD | cut -d= -f2)
  sed -i -E "s/^pkgrel=${rel}$/pkgrel=$((rel + 1))/" PKGBUILD
  git add PKGBUILD
  git commit -q -m "pkgrel=$((rel + 1)): ${bump}"
  echo "bumped pkgrel -> $((rel + 1)) (committed)"
fi

source ./PKGBUILD            # plain variable assignments + functions; safe
tarball="${pkgname}-${pkgver}.tar.gz"

echo "==> packaging $(git rev-parse --short HEAD) as ${tarball}"
rm -f "$tarball"
rm -rf src pkg
git archive --format=tar --prefix="${pkgname}-${pkgver}/" HEAD | gzip > "$tarball"

makepkg -d --noconfirm      # -d: skip dep install (needs sudo — that's --install's job)

pkgfile="${pkgname}-${pkgver}-${pkgrel}-x86_64.pkg.tar.zst"
[[ -f $pkgfile ]] || { echo "expected artifact $pkgfile not produced" >&2; exit 1; }

echo "==> verifying package structure"
files=$(pacman -Qlp "$pkgfile" | sed 's|^[^ ]* ||')   # keep the leading slash
need=(
  /usr/lib/vibekey/bin/vibekeyd
  /usr/lib/vibekey/bin/vibekey-config
  /usr/lib/vibekey/actions.json
  /usr/lib/vibekey/panel/panel.py
  /usr/bin/vibekey-panel
  /usr/lib/systemd/user/vibekeyd.service
  /usr/lib/udev/rules.d/70-ulanzi-vibekey.rules
  /usr/lib/sysusers.d/vibekey.conf
  /usr/share/applications/vibekey-panel.desktop
  /usr/share/icons/hicolor/32x32/apps/vibekey.png
  /usr/share/icons/hicolor/scalable/apps/vibekey.svg
  /usr/share/licenses/vibekey/LICENSE
)
for f in "${need[@]}"; do
  echo "$files" | grep -qx "$f" || { echo "MISSING in package: $f" >&2; exit 1; }
done
n_icons=$(echo "$files" | grep -c 'icons/hicolor/.*/apps/vibekey.png')
[[ $n_icons -eq 8 ]] || { echo "expected 8 hicolor PNGs, found $n_icons" >&2; exit 1; }
pacman -Qip "$pkgfile" | grep -q 'pyside6' || { echo "deps wrong" >&2; exit 1; }
echo "    structure OK ($(echo "$files" | wc -l) files)"

mkdir -p dist
find dist -name "${pkgname}-*.pkg.tar.zst" -printf '%T@ %p\n' 2>/dev/null | sort -rn | tail -n +3 | cut -d' ' -f2- | xargs -r rm --
mv -f "$pkgfile" dist/
rm -rf src pkg "$tarball"
echo "==> dist/$(basename dist/"$pkgfile")"

if [[ $install -eq 1 ]]; then
  sudo pacman -U "dist/${pkgfile}"
else
  echo "install with:  sudo pacman -U dist/${pkgfile}"
fi
