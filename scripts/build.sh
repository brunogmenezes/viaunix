#!/bin/sh
# Executar em Linux (Debian/Ubuntu, WSL2 ou VM) como root.
# Use um diretório no filesystem Linux (ex: ~/viaunix), NÃO em /mnt/c.
set -e
VIAUNIX_VERSION=$(tr -d ' \r\n' < VERSION 2>/dev/null || echo "1.0.0")
echo "=== ViaUnix ISO Build v${VIAUNIX_VERSION} ==="

apt-get update
apt-get install -y live-build debootstrap squashfs-tools xorriso qemu-system-x86 ovmf

# O live-build só executa scripts com permissão de execução
chmod +x auto/* config/hooks/*/* 2>/dev/null || true

# Gera os pacotes .deb do ViaUnix (usados pela ISO e publicados no repositório APT)
apt-get install -y dpkg-dev
sh scripts/build-packages.sh

lb clean --purge || true
lb config
lb build 2>&1 | tee "build-${VIAUNIX_VERSION}.log"

ISO="viaunix-${VIAUNIX_VERSION}-amd64.hybrid.iso"
if [ -f "$ISO" ]; then
    sha256sum "$ISO" > "${ISO}.sha256"
    ls -lh "$ISO" "${ISO}.sha256"
else
    ls -lh ./*.iso
fi
