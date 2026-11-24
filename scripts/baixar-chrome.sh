#!/bin/sh
# Baixa o pacote oficial do Google Chrome (amd64) para incluir no repositorio APT e na ISO.
# Usa cache em build/cache/ com -z (so baixa de novo se houver versao mais recente no Google).
set -e
cd "$(dirname "$0")/.."

CACHE=build/cache
OUT=out/debs
DEB="$CACHE/google-chrome-stable_current_amd64.deb"
URL="https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"

mkdir -p "$CACHE" "$OUT" config/packages.chroot

echo "Verificando Google Chrome em $URL ..."
if [ -s "$DEB" ]; then
    curl -fsSL -z "$DEB" -o "$DEB" "$URL"
else
    curl -fsSL -o "$DEB" "$URL"
fi

VER=$(dpkg-deb -f "$DEB" Version)
cp "$DEB" "$OUT/google-chrome-stable_${VER}_amd64.deb"
rm -f config/packages.chroot/google-chrome-stable*.deb
cp "$DEB" "config/packages.chroot/google-chrome-stable_${VER}_amd64.deb"
echo "Google Chrome pronto: versao $VER"
