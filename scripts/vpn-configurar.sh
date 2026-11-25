#!/bin/sh
# Embute o perfil .ovpn e a senha da chave privada no pacote viaunix-vpn (no servidor 172.16.152.2).
# NUNCA commite o .ovpn nem o vpn-keypass em repositorio Git publico!
# Uso:
#   sh scripts/vpn-configurar.sh /caminho/para/client.ovpn 'SENHA_CHAVE_PRIVADA'
set -e
cd "$(dirname "$0")/.."

OVPN="$1"
KEYPASS="$2"
if [ -z "$OVPN" ] || [ ! -f "$OVPN" ] || [ -z "$KEYPASS" ]; then
    echo "Uso: sh scripts/vpn-configurar.sh <arquivo.ovpn> '<senha_chave_privada>'" >&2
    exit 1
fi

DEST_CONF=packages/viaunix-vpn/etc/openvpn/client/viaunix.conf
DEST_PASS=packages/viaunix-vpn/etc/viaunix/vpn-keypass
mkdir -p "$(dirname "$DEST_CONF")" "$(dirname "$DEST_PASS")"

# Copia o .ovpn removendo CRLF e ajusta auth-user-pass + askpass
sed 's/\r$//' "$OVPN" \
    | sed -E 's|^auth-user-pass.*|auth-user-pass /run/viaunix-vpn/auth|' > "$DEST_CONF"

if ! grep -q "^auth-user-pass " "$DEST_CONF"; then
    printf '\nauth-user-pass /run/viaunix-vpn/auth\n' >> "$DEST_CONF"
fi
if ! grep -q "^askpass " "$DEST_CONF"; then
    printf 'askpass /etc/viaunix/vpn-keypass\n' >> "$DEST_CONF"
fi
if ! grep -q "^status " "$DEST_CONF"; then
    printf 'status /run/viaunix-vpn/status 10\n' >> "$DEST_CONF"
fi

printf '%s\n' "$KEYPASS" > "$DEST_PASS"
chmod 600 "$DEST_CONF" "$DEST_PASS"

# Incrementa automaticamente o patch da versao do viaunix-vpn
CTRL=packages/viaunix-vpn/DEBIAN/control
CUR=$(awk '/^Version:/{print $2}' "$CTRL")
MAJ_MIN=$(echo "$CUR" | cut -d. -f1,2)
PATCH=$(echo "$CUR" | cut -d. -f3)
NEXT="${MAJ_MIN}.$((PATCH + 1))"
sed -i "s/^Version:.*/Version: $NEXT/" "$CTRL"

echo "Perfil VPN configurado em $DEST_CONF (viaunix-vpn -> $NEXT)."
echo "Agora publique no repositorio interno com: sh scripts/publicar-local.sh"
