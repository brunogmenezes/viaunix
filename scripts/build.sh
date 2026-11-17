#!/bin/sh
# Executar em Linux (Debian/Ubuntu, WSL2 ou VM) como root.
# Use um diretório no filesystem Linux (ex: ~/viaunix), NÃO em /mnt/c.
set -e
apt-get update
apt-get install -y live-build debootstrap squashfs-tools xorriso qemu-system-x86 ovmf

# O live-build só executa scripts com permissão de execução
chmod +x auto/* config/hooks/*/* 2>/dev/null || true

lb clean --purge || true
lb config
lb build 2>&1 | tee build.log
ls -lh ./*.iso
