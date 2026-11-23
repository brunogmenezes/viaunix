#!/bin/sh
# Inclui no repositório (reprepro) apenas os .deb cuja versão ainda não foi publicada.
# Uso: repo-incluir.sh <REPO_BASE> <CODENAME> arquivo.deb...
set -e
BASE=$1; CODENAME=$2; shift 2

for deb in "$@"; do
    name=$(dpkg-deb -f "$deb" Package)
    ver=$(dpkg-deb -f "$deb" Version)
    if reprepro -b "$BASE" list "$CODENAME" "$name" | grep -q " $ver\$"; then
        echo "= $name $ver ja publicado (pulando)"
    else
        echo "+ $name $ver novo, publicando"
        reprepro -b "$BASE" includedeb "$CODENAME" "$deb"
    fi
done
reprepro -b "$BASE" export
