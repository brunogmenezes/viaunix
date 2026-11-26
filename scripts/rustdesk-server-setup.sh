#!/bin/sh
# Instala e ativa o RustDesk Server (hbbs + hbbr) no servidor 172.16.152.2.
# Portas usadas pelo RustDesk: TCP 21115-21119, UDP 21116 (criptografia propria Curve25519).
# Rodar UMA vez como root:  sh scripts/rustdesk-server-setup.sh
set -e

RD_DIR=/opt/rustdesk-server
RD_HOST=${RD_HOST:-172.16.152.2}

apt-get update
apt-get install -y curl unzip

mkdir -p "$RD_DIR"
cd "$RD_DIR"

if [ ! -x "$RD_DIR/hbbs" ] || [ ! -x "$RD_DIR/hbbr" ]; then
    echo "Buscando ultima versao do rustdesk-server no GitHub..."
    URL=$(curl -fsSL https://api.github.com/repos/rustdesk/rustdesk-server/releases/latest \
        | grep -oE 'https://[^"]+rustdesk-server-linux-amd64\.zip' | head -n 1)
    [ -n "$URL" ] || { echo "ERRO: nao foi possivel localizar o zip do rustdesk-server." >&2; exit 1; }
    curl -fsSL "$URL" -o /tmp/rustdesk-server.zip
    unzip -o -j /tmp/rustdesk-server.zip "amd64/hbbs" "amd64/hbbr" -d "$RD_DIR"
    rm -f /tmp/rustdesk-server.zip
    chmod 755 "$RD_DIR/hbbs" "$RD_DIR/hbbr"
fi

cat > /etc/systemd/system/rustdesk-hbbs.service <<EOF
[Unit]
Description=RustDesk ID/Rendezvous Server (hbbs) - ViaUnix
After=network.target

[Service]
Type=simple
WorkingDirectory=$RD_DIR
ExecStart=$RD_DIR/hbbs -r $RD_HOST:21117 -k _
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/rustdesk-hbbr.service <<EOF
[Unit]
Description=RustDesk Relay Server (hbbr) - ViaUnix
After=network.target

[Service]
Type=simple
WorkingDirectory=$RD_DIR
ExecStart=$RD_DIR/hbbr -k _
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Para e desabilita o MeshCentral antigo se existir
if systemctl is-active --quiet meshcentral.service 2>/dev/null; then
    systemctl stop meshcentral.service
    systemctl disable meshcentral.service
fi

systemctl daemon-reload
systemctl enable --now rustdesk-hbbs.service rustdesk-hbbr.service
sleep 2

PUBKEY=$(cat "$RD_DIR/id_ed25519.pub" 2>/dev/null || true)
echo ""
echo "=============================================================="
echo "RustDesk Server ativo em $RD_HOST!"
echo "Chave publica (id_ed25519.pub): $PUBKEY"
echo ""
echo "Configure o pacote viaunix-remote e publique no APT:"
echo "  cd /opt/viaunix"
echo "  sh scripts/rustdesk-configurar.sh '$RD_HOST' '$PUBKEY'"
echo "  sh scripts/publicar-local.sh"
echo "=============================================================="
