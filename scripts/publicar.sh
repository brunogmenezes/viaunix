#!/bin/sh
# Constrói os pacotes e publica no repositório APT do ViaUnix.
# Rodar na VM de build. Requer SSH (de preferência com chave) para $REPO_SERVER.
# IMPORTANTE: aumente a Version no DEBIAN/control do pacote alterado
# (ex.: 1.0.0 -> 1.0.1); o reprepro recusa versão já publicada com conteúdo diferente.
set -e
cd "$(dirname "$0")/.."
. ./repo.conf

sh scripts/build-packages.sh

ssh "$REPO_SERVER" "mkdir -p $REPO_BASE/incoming"
scp out/debs/*.deb scripts/repo-incluir.sh "$REPO_SERVER:$REPO_BASE/incoming/"
ssh "$REPO_SERVER" "sh $REPO_BASE/incoming/repo-incluir.sh $REPO_BASE $CODENAME $REPO_BASE/incoming/*.deb && rm -f $REPO_BASE/incoming/*.deb"
echo "Publicado. Nas máquinas: apt update && apt upgrade"
