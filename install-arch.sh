#!/bin/bash
# Install/update the Live Gamer 4K (GC573) driver via DKMS on Arch / CachyOS.
# DKMS rebuilds it automatically whenever a kernel is installed or updated.
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "Run with sudo: sudo $0"; exit 1; }

SRC="$(cd "$(dirname "$0")" && pwd)"
NAME=lg4k
VER=$(sed -n 's/^PACKAGE_VERSION="\(.*\)"/\1/p' "$SRC/dkms.conf")

# Headers for every installed kernel (linux -> linux-headers, linux-cachyos -> linux-cachyos-headers, ...)
HEADERS=$(pacman -Qq | grep -E '^linux(-[a-z0-9-]+)?$' | grep -vE -- '-(firmware|api-headers|headers|docs)' | sed 's/$/-headers/')
pacman -S --needed --noconfirm dkms $HEADERS

# Drop any previous DKMS registration so updated sources are picked up
if [ -e "/var/lib/dkms/$NAME/$VER" ]; then
    dkms remove -m "$NAME" -v "$VER" --all
fi
rm -rf "/usr/src/$NAME-$VER"
mkdir -p "/usr/src/$NAME-$VER"
cp -r "$SRC/driver" "$SRC/AverMediaLib_64.a" "$SRC/dkms.conf" "/usr/src/$NAME-$VER/"

dkms add -m "$NAME" -v "$VER"
for kdir in /usr/lib/modules/*/build; do
    dkms install -m "$NAME" -v "$VER" -k "$(basename "$(dirname "$kdir")")"
done
dkms status -m "$NAME"

if [ "${1:-}" = "--no-load" ]; then
    echo "Installed. Reboot to load the new driver."
    exit 0
fi

modprobe -r cx511h 2>/dev/null || true
modprobe cx511h && echo "cx511h loaded. Video devices:" && ls -1 /dev/video* 2>/dev/null
