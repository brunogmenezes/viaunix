#!/bin/sh
# Baixa o .deb oficial do cliente RustDesk (x86_64) para incluir no repositorio APT e na ISO.
set -e
cd "$(dirname "$0")/.."

CACHE=build/cache
OUT=out/debs
mkdir -p "$CACHE" "$OUT" config/packages.chroot

URL=$(curl -fsSL https://api.github.com/repos/rustdesk/rustdesk/releases/latest \
    | grep -oE 'https://[^"]+rustdesk-[0-9.]+-x86_64\.deb' | head -n 1)

if [ -z "$URL" ]; then
    echo "AVISO: nao foi possivel consultar a URL do RustDesk; usando cache local se existir." >&2
    DEB=$(ls -t "$CACHE"/rustdesk-*.deb 2>/dev/null | head -n 1 || true)
else
    FNAME=$(basename "$URL")
    DEB="$CACHE/$FNAME"
    if [ ! -s "$DEB" ]; then
        echo "Baixando $FNAME ..."
        curl -fsSL "$URL" -o "$DEB"
    fi
fi

[ -s "${DEB:-}" ] || { echo "ERRO: pacote rustdesk .deb ausente." >&2; exit 1; }
VER=$(dpkg-deb -f "$DEB" Version)
cp "$DEB" "$OUT/rustdesk_${VER}_amd64.deb"
rm -f config/packages.chroot/rustdesk*.deb
cp "$DEB" "config/packages.chroot/rustdesk_${VER}_amd64.deb"
echo "RustDesk pronto: versao $VER"
