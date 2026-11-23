#!/bin/sh
# Prepara o SERVIDOR do repositório APT do ViaUnix (rodar UMA vez, como root, no servidor).
# Debian/Ubuntu com servidor web servindo /var/www/html (Apache ou Nginx).
set -e
REPO_BASE=${REPO_BASE:-/srv/viaunix-repo}
REPO_WEB_DIR=${REPO_WEB_DIR:-/var/www/html/viaunix/apt}
CODENAME=${CODENAME:-trixie}
UIDNAME="ViaUnix Repositorio <brunogmenezes@hotmail.com>"

apt-get update
apt-get install -y reprepro gnupg

mkdir -p "$REPO_BASE/conf" "$REPO_BASE/incoming" "$REPO_WEB_DIR"

# Chave GPG de assinatura (sem senha, para publicar de forma automatizada)
if ! gpg --list-secret-keys "$UIDNAME" >/dev/null 2>&1; then
    gpg --batch --passphrase '' --quick-generate-key "$UIDNAME" rsa4096 sign never
fi
KEYID=$(gpg --list-secret-keys --with-colons "$UIDNAME" | awk -F: '/^fpr/ {print $10; exit}')

cat > "$REPO_BASE/conf/options" <<EOF
outdir $REPO_WEB_DIR
EOF

cat > "$REPO_BASE/conf/distributions" <<EOF
Origin: ViaUnix
Label: ViaUnix
Suite: stable
Codename: $CODENAME
Architectures: amd64 all
Components: main
Description: Repositorio de atualizacoes do ViaUnix
SignWith: $KEYID
EOF

# Chave pública (binária, usada em Signed-By) e versão ASCII
gpg --export "$KEYID" > "$REPO_WEB_DIR/viaunix-archive-keyring.gpg"
gpg --armor --export "$KEYID" > "$REPO_WEB_DIR/viaunix-archive-keyring.asc"

reprepro -b "$REPO_BASE" export
echo "OK. Chave: $KEYID"
echo "Copie $REPO_WEB_DIR/viaunix-archive-keyring.gpg para packages/viaunix-archive-keyring/usr/share/keyrings/ no projeto."
echo "BACKUP: guarde a chave privada (gpg --export-secret-keys $KEYID) em local seguro."
