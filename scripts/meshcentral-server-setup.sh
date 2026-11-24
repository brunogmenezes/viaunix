#!/bin/sh
# Instala e ativa o MeshCentral no servidor 172.16.152.2 (porta HTTPS 8090).
# Rodar UMA vez como root dentro do clone (/opt/viaunix):  sh scripts/meshcentral-server-setup.sh
set -e

MC_DIR=/opt/meshcentral
MC_PORT=${MC_PORT:-8090}
MC_HOST=${MC_HOST:-172.16.152.2}

apt-get update
apt-get install -y nodejs npm curl

mkdir -p "$MC_DIR/meshcentral-data"
cd "$MC_DIR"

if [ ! -d "$MC_DIR/node_modules/meshcentral" ]; then
    npm install meshcentral --omit=dev
fi

if [ ! -f "$MC_DIR/meshcentral-data/config.json" ]; then
    cat > "$MC_DIR/meshcentral-data/config.json" <<EOF
{
  "\$schema": "https://raw.githubusercontent.com/Ylianst/MeshCentral/master/meshcentral-config-schema.json",
  "settings": {
    "cert": "$MC_HOST",
    "WANonly": false,
    "LANonly": true,
    "port": $MC_PORT,
    "aliasPort": $MC_PORT,
    "redirPort": 0,
    "tlsOffload": true,
    "agentPort": 8091,
    "agentAliasPort": 8091,
    "agentPortTls": true,
    "exactPorts": true,
    "allowLoginToken": true,
    "allowFraming": false,
    "selfUpdate": false
  },
  "domains": {
    "": {
      "title": "ViaUnix Acesso Remoto",
      "title2": "Suporte TI",
      "newAccounts": true,
      "userNameIsEmail": false,
      "desktop": {
        "showConnectionToolbar": false
      }
    }
  }
}
EOF
fi

cat > /etc/systemd/system/meshcentral.service <<EOF
[Unit]
Description=MeshCentral (ViaUnix Acesso Remoto)
After=network.target

[Service]
Type=simple
WorkingDirectory=$MC_DIR
ExecStart=/usr/bin/node $MC_DIR/node_modules/meshcentral
Restart=always
RestartSec=5
LimitNOFILE=1000000

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now meshcentral.service
sleep 3
systemctl status --no-pager meshcentral.service | head -15 || true

echo ""
echo "=============================================================="
echo "MeshCentral ativo!"
echo "Acesse no navegador: http://$MC_HOST:$MC_PORT"
echo "1. Crie sua conta admin na 1a tela."
echo "2. Depois desative novos cadastros em $MC_DIR/meshcentral-data/config.json"
echo "   trocando \"newAccounts\": false e rodando: systemctl restart meshcentral"
echo "3. Crie o grupo de dispositivos 'ViaUnix', clique em 'Add Agent' -> Linux"
echo "   e passe o link do meshinstall.sh ao script scripts/meshcentral-configurar-agente.sh"
echo "=============================================================="
