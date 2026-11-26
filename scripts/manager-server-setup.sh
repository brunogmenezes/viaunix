#!/bin/sh
# Instala e ativa o ViaUnix Manager no servidor 172.16.152.2 (PostgreSQL + Nginx HTTPS :8443).
# Rodar UMA vez como root dentro do clone (/opt/viaunix):  sh scripts/manager-server-setup.sh
set -e
cd "$(dirname "$0")/.."

MGR_DIR=/opt/viaunix-manager
CONF=/etc/viaunix/manager.conf
MASTER_KEY=/etc/viaunix/master.key
SSL_DIR=/etc/viaunix/ssl

apt-get update
apt-get install -y python3-venv python3-pip openssl postgresql-client novnc

install -d -m 700 /etc/viaunix "$SSL_DIR"
install -d -m 755 "$MGR_DIR"

# 1. Chave mestra AES-256 (fora do banco; FACA BACKUP!)
if [ ! -s "$MASTER_KEY" ]; then
    python3 -c 'import base64, os; print(base64.b64encode(os.urandom(32)).decode())' > "$MASTER_KEY"
    chmod 600 "$MASTER_KEY"
    echo "Chave mestra AES-256 gerada em $MASTER_KEY (FACA BACKUP!)."
fi

# 2. Banco PostgreSQL + usuario dedicado
if [ ! -f "$CONF" ]; then
    DB_PASS=$(openssl rand -hex 20)
    SESSION_SECRET=$(openssl rand -hex 32)
    LOCAL_ADMIN_PASS=$(openssl rand -base64 14 | tr -dc 'A-Za-z0-9' | head -c 16)
    LOCAL_ADMIN_HASH=$(python3 -c "import hashlib, os, sys; s=os.urandom(16); h=hashlib.scrypt(sys.argv[1].encode(), salt=s, n=2**14, r=8, p=1, dklen=32); print(s.hex()+':'+h.hex())" "$LOCAL_ADMIN_PASS")

    # Aproveita o mesmo PROVISION_TOKEN ja configurado no servidor (se existir)
    PROV_TOKEN="viaunix-provision-alterar-em-producao"
    if [ -f /etc/viaunix/provision-server.conf ]; then
        T=$(awk -F= '/^PROVISION_TOKEN=/{print $2; exit}' /etc/viaunix/provision-server.conf)
        [ -n "$T" ] && PROV_TOKEN="$T"
    elif [ -f packages/viaunix-provision/etc/viaunix/provision.conf ]; then
        T=$(awk -F= '/^PROVISION_TOKEN=/{print $2; exit}' packages/viaunix-provision/etc/viaunix/provision.conf)
        [ -n "$T" ] && PROV_TOKEN="$T"
    fi

    su - postgres -c "psql -tc \"SELECT 1 FROM pg_roles WHERE rolname='viaunix'\" | grep -q 1 || psql -c \"CREATE USER viaunix WITH PASSWORD '$DB_PASS';\""
    su - postgres -c "psql -c \"ALTER USER viaunix WITH PASSWORD '$DB_PASS';\""
    su - postgres -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname='viaunix_manager'\" | grep -q 1 || psql -c \"CREATE DATABASE viaunix_manager OWNER viaunix;\""

    cat > "$CONF" <<EOF
# ViaUnix Manager - configuracao do servidor (permissao 0600 root:root)
DATABASE_URL=postgresql://viaunix:$DB_PASS@127.0.0.1/viaunix_manager
MASTER_KEY_FILE=$MASTER_KEY
SESSION_SECRET=$SESSION_SECRET
PROVISION_TOKEN=$PROV_TOKEN
JUPITER_API_URL=https://api.jupiter.com.br/action/Usuario/logar
# Usuarios da API Jupiter autorizados a acessar o painel (separados por virgula)
ADMIN_USERS=Brunog
# Conta admin local de emergencia
LOCAL_ADMIN_USER=admin
LOCAL_ADMIN_HASH=$LOCAL_ADMIN_HASH
EOF
    chmod 600 "$CONF"
    SHOW_LOCAL_PASS="$LOCAL_ADMIN_PASS"
fi

# 3. Virtualenv + dependencias Python
cp -a manager/. "$MGR_DIR/"
if [ ! -d "$MGR_DIR/venv" ]; then
    python3 -m venv "$MGR_DIR/venv"
fi
"$MGR_DIR/venv/bin/pip" install --upgrade pip >/dev/null
"$MGR_DIR/venv/bin/pip" install -r "$MGR_DIR/requirements.txt"

# 4. Substitui o receptor antigo na porta 8088 (mantem 100% compatibilidade)
if systemctl is-active --quiet viaunix-provision-server.service 2>/dev/null; then
    systemctl stop viaunix-provision-server.service
    systemctl disable viaunix-provision-server.service
fi

# 5. Migra maquinas.jsonl antigo para o PostgreSQL com senhas criptografadas
"$MGR_DIR/venv/bin/python" "$MGR_DIR/migrate_jsonl.py"

# 6. Servico systemd (ouve em 0.0.0.0:8088 para agentes/provisionamento e proxy do Nginx)
cat > /etc/systemd/system/viaunix-manager.service <<EOF
[Unit]
Description=ViaUnix Manager (API + Painel Web + Cofre AES-256)
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
WorkingDirectory=$MGR_DIR
Environment=VIAUNIX_MANAGER_CONF=$CONF
ExecStart=$MGR_DIR/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8088 --proxy-headers
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now viaunix-manager.service

# 7. Certificado TLS autoassinado + Nginx dedicado na porta HTTPS 8443 (nao mexe em outros sites)
if [ ! -f "$SSL_DIR/viaunix-manager.crt" ]; then
    openssl req -x509 -nodes -days 1825 -newkey rsa:2048 \
        -keyout "$SSL_DIR/viaunix-manager.key" \
        -out "$SSL_DIR/viaunix-manager.crt" \
        -subj "/CN=172.16.152.2/O=ViaUnix" \
        -addext "subjectAltName=IP:172.16.152.2"
    chmod 600 "$SSL_DIR/viaunix-manager.key"
fi

cat > /etc/nginx/sites-available/viaunix-manager <<EOF
server {
    listen 8443 ssl;
    server_name _;

    ssl_certificate     $SSL_DIR/viaunix-manager.crt;
    ssl_certificate_key $SSL_DIR/viaunix-manager.key;
    ssl_protocols       TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://127.0.0.1:8088;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
EOF

ln -sf /etc/nginx/sites-available/viaunix-manager /etc/nginx/sites-enabled/viaunix-manager
nginx -t
systemctl reload nginx

echo ""
echo "=============================================================="
echo "ViaUnix Manager ativo!"
echo "Painel Web (HTTPS): https://172.16.152.2:8443"
echo "Login TI (API Jupiter): usuarios em ADMIN_USERS ($CONF)"
if [ -n "${SHOW_LOCAL_PASS:-}" ]; then
    echo "Conta admin local de emergencia: usuario=admin  senha=$SHOW_LOCAL_PASS"
    echo "(Anote esta senha agora; ela fica salva apenas como hash scrypt.)"
fi
echo "IMPORTANTE: faca backup da chave mestra $MASTER_KEY!"
echo "=============================================================="
