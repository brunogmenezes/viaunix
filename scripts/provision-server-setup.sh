#!/bin/sh
# Instala e ativa o servidor receptor de provisionamento no servidor (172.16.152.2).
# Rodar UMA vez como root dentro do clone (/opt/viaunix):  sh scripts/provision-server-setup.sh
set -e
cd "$(dirname "$0")/.."

install -d -m 700 /etc/viaunix /var/lib/viaunix-provision
install -m 755 scripts/viaunix-provision-server.py /usr/local/sbin/viaunix-provision-server

if [ ! -f /etc/viaunix/provision-server.conf ]; then
    cp config/includes.chroot/etc/viaunix/provision.conf /etc/viaunix/provision-server.conf
    # Adiciona BIND/PORT mantendo o mesmo PROVISION_TOKEN
    printf '\nBIND=0.0.0.0\nPORT=8088\n' >> /etc/viaunix/provision-server.conf
    chmod 600 /etc/viaunix/provision-server.conf
fi

# Utilitario rapido para consultar as maquinas instaladas no servidor
cat > /usr/local/sbin/viaunix-maquinas <<'EOF'
#!/bin/sh
CSV=/var/lib/viaunix-provision/maquinas.csv
if [ ! -s "$CSV" ]; then
    echo "Nenhuma maquina registrada ainda em $CSV"
    exit 0
fi
column -s, -t < "$CSV"
EOF
chmod 755 /usr/local/sbin/viaunix-maquinas

cat > /etc/systemd/system/viaunix-provision-server.service <<'EOF'
[Unit]
Description=ViaUnix - Servidor receptor de provisionamento
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/sbin/viaunix-provision-server
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now viaunix-provision-server.service
systemctl status --no-pager viaunix-provision-server.service || true
echo ""
echo "OK. Consulte maquinas instaladas com: viaunix-maquinas"
echo "Arquivo protegido (0600 root:root): /var/lib/viaunix-provision/maquinas.csv"
