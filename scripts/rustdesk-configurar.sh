#!/bin/sh
# Configura o servidor e a chave publica do RustDesk no pacote viaunix-remote (no servidor 172.16.152.2).
# Uso: sh scripts/rustdesk-configurar.sh '172.16.152.2' 'CHAVE_PUBLICA_ID_ED25519_PUB'
set -e
cd "$(dirname "$0")/.."

HOST="$1"
KEY="$2"
if [ -z "$HOST" ] || [ -z "$KEY" ]; then
    echo "Uso: sh scripts/rustdesk-configurar.sh <HOST> <CHAVE_PUBLICA>" >&2
    exit 1
fi

CONF=packages/viaunix-remote/etc/viaunix/rustdesk.conf
mkdir -p "$(dirname "$CONF")"
cat > "$CONF" <<EOF
RUSTDESK_SERVER='$HOST'
RUSTDESK_KEY='$KEY'
EOF

CTRL=packages/viaunix-remote/DEBIAN/control
CUR=$(awk '/^Version:/{print $2}' "$CTRL")
MAJ_MIN=$(echo "$CUR" | cut -d. -f1,2)
PATCH=$(echo "$CUR" | cut -d. -f3)
NEXT="${MAJ_MIN}.$((PATCH + 1))"
sed -i "s/^Version:.*/Version: $NEXT/" "$CTRL"

echo "RustDesk configurado em $CONF (viaunix-remote -> $NEXT)."
echo "Publique com: sh scripts/publicar-local.sh"
