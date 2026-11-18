# Maintainer: jimOnAir <https://github.com/jimOnAir>
# vibekey — Ulanzi AU05 control surface for Manjaro KDE / X11 (spec.md §9).
# Single package: vibekeyd daemon + PySide6 Panel + vibekey-config CLI.
pkgname=vibekey
pkgver=0.1.0
pkgrel=24
pkgdesc="Ulanzi AU05 keypad as a KDE/X11 control surface — daemon, Panel, dictation & agent Presets (port of jimmibram/vibekey-driver)"
arch=('x86_64')
url="https://github.com/jimOnAir/vibekey"
license=('MIT')
depends=('python' 'pyside6' 'xdotool' 'wmctrl' 'libnotify')
optdepends=('handy: Dictation Preset — AUR, never hard-depended (docs pin 0.10.1)'
            'orca: agent Presets')
source=("$pkgname-$pkgver.tar.gz::$url/archive/v$pkgver.tar.gz")
sha256sums=('SKIP')   # replace with the real digest once tag v$pkgver is pushed

build() {
  cd "$srcdir/$pkgname-$pkgver"
  # deterministic gate (spec §10.1): every shipped Python file must compile
  python -m py_compile bin/vibekeyd bin/vibekey-config panel/panel.py tools/render_icons.py
}

package() {
  cd "$pkgname-$pkgver"
  install -Dm755 bin/vibekeyd            "$pkgdir/usr/lib/vibekey/bin/vibekeyd"
  install -Dm755 bin/vibekey-config      "$pkgdir/usr/lib/vibekey/bin/vibekey-config"
  install -Dm644 actions.json            "$pkgdir/usr/lib/vibekey/actions.json"
  install -Dm644 panel/panel.py          "$pkgdir/usr/lib/vibekey/panel/panel.py"
  install -d "$pkgdir/usr/bin"
  cat > "$pkgdir/usr/bin/vibekey-panel" <<'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, "/usr/lib/vibekey/panel")
from panel import main
sys.exit(main())
EOF
  chmod 755 "$pkgdir/usr/bin/vibekey-panel"
  install -Dm644 systemd/vibekeyd.service       "$pkgdir/usr/lib/systemd/user/vibekeyd.service"
  install -Dm644 udev/70-ulanzi-vibekey.rules   "$pkgdir/usr/lib/udev/rules.d/70-ulanzi-vibekey.rules"
  install -Dm644 sysusers/vibekey.conf          "$pkgdir/usr/lib/sysusers.d/vibekey.conf"
  install -Dm644 LICENSE                        "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
  install -Dm644 README.md                      "$pkgdir/usr/share/doc/$pkgname/README.md"
  local page
  for page in docs/*.md; do
    install -Dm644 "$page" "$pkgdir/usr/share/doc/$pkgname/$(basename "$page")"
  done
  local size
  for size in 16 22 24 32 48 64 128 256; do
    install -Dm644 "panel/icons/${size}x${size}/vibekey.png" \
      "$pkgdir/usr/share/icons/hicolor/${size}x${size}/apps/vibekey.png"
  done
  install -Dm644 panel/icons/vibekey.svg "$pkgdir/usr/share/icons/hicolor/scalable/apps/vibekey.svg"
  install -Dm644 panel/vibekey-panel.desktop "$pkgdir/usr/share/applications/vibekey-panel.desktop"
}

_retrigger_dongle() {
  # ported from upstream vibekey-install-access:28-37 (spec §9): reload rules,
  # then apply them to the attached Dongle without waiting for its watchdog
  udevadm control --reload
  udevadm trigger --subsystem-match=input --attr-match=idVendor=fff1 2>/dev/null || true
  udevadm trigger --subsystem-match=hidraw --attr-match=idVendor=fff1 2>/dev/null || true
  for dev in /sys/bus/usb/devices/*; do
    [[ -f $dev/idVendor && -f $dev/idProduct ]] || continue
    if [[ $(<"$dev/idVendor") == fff1 && $(<"$dev/idProduct") == 00dd ]]; then
      udevadm trigger --parent-match="$dev" --action=add || true
    fi
  done
  udevadm settle --timeout=5 || true
}

post_install() {
  systemd-sysusers vibekey.conf || true
  _retrigger_dongle
  echo ">>> vibekey: ONE manual step remains —  gpasswd -a $SUDO_USER vibekey   (then re-login)"
  echo ">>> then:    systemctl --user enable --now vibekeyd"
}

post_upgrade() {
  _retrigger_dongle
}

post_remove() {
  udevadm control --reload || true
  echo ">>> vibekey: user state survives by design; to fully tear down:"
  echo ">>>   systemctl --user disable --now vibekeyd;  gpasswd -d $SUDO_USER vibekey"
  echo ">>>   rm -rf ~/.config/vibekey ~/.config/autostart/vibekey-panel.desktop"
}
