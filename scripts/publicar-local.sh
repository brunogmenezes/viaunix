#!/bin/sh
# Atualiza e publica o repositório APT DIRETAMENTE NO SERVIDOR, a partir do Git.
# Uso (no servidor, como root, dentro do clone do projeto):  sh scripts/publicar-local.sh
# Requer: git, dpkg-dev, reprepro (instalados pelo repo-server-setup.sh / abaixo).
# IMPORTANTE: aumente a Version do pacote alterado em packages/<pacote>/DEBIAN/control.
set -e
cd "$(dirname "$0")/.."
. ./repo.conf

git pull --ff-only
apt-get install -y dpkg-dev reprepro >/dev/null

# A chave pública já existe no servidor: usa-a se ainda não estiver no projeto
KEY=packages/viaunix-archive-keyring/usr/share/keyrings/viaunix-archive-keyring.gpg
if [ ! -s "$KEY" ] && [ -s "$REPO_WEB_DIR/viaunix-archive-keyring.gpg" ]; then
    cp "$REPO_WEB_DIR/viaunix-archive-keyring.gpg" "$KEY"
    echo "AVISO: chave copiada para $KEY. Faça commit dela no projeto (necessária para gerar a ISO)."
fi

sh scripts/build-packages.sh
sh scripts/repo-incluir.sh "$REPO_BASE" "$CODENAME" out/debs/*.deb
echo "Publicado. Nas máquinas: apt update && apt upgrade"
