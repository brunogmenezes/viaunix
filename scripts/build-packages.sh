#!/bin/sh
# Gera os .deb de packages/* em out/debs/ e copia para config/packages.chroot/
# (para a ISO). Rodar em Linux. Requer: dpkg-dev.
set -e
cd "$(dirname "$0")/.."
. ./repo.conf

KEY=packages/viaunix-archive-keyring/usr/share/keyrings/viaunix-archive-keyring.gpg
if [ ! -s "$KEY" ]; then
    echo "ERRO: falta a chave publica do repositorio: $KEY" >&2
    echo "Rode scripts/repo-server-setup.sh no servidor e copie a chave (veja docs/atualizacoes.md)." >&2
    exit 1
fi

STAGE=build/stage
OUT=out/debs
rm -rf "$STAGE" "$OUT"
mkdir -p "$STAGE" "$OUT" config/packages.chroot
cp -a packages/. "$STAGE/"

# Substitui placeholders do repositório
sed -i "s|@REPO_URL@|$REPO_URL|g; s|@CODENAME@|$CODENAME|g" \
    "$STAGE/viaunix-archive-keyring/etc/apt/sources.list.d/viaunix.sources"

for d in "$STAGE"/*/; do
    find "$d" -type d -exec chmod 755 {} +
    find "$d" -type f ! -path '*/DEBIAN/*' -exec chmod 644 {} +
    for s in preinst postinst prerm postrm; do
        [ -f "$d/DEBIAN/$s" ] && chmod 755 "$d/DEBIAN/$s"
    done
    dpkg-deb --root-owner-group -Zxz --build "$d" "$OUT"
done

rm -f config/packages.chroot/viaunix-*.deb
cp "$OUT"/*.deb config/packages.chroot/
ls -lh "$OUT"
