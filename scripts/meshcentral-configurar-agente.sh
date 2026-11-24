#!/bin/sh
# Configura o pacote viaunix-remote com o comando de instalacao do agente gerado no MeshCentral.
# Uso (no servidor, dentro de /opt/viaunix):
#   sh scripts/meshcentral-configurar-agente.sh "<URL_BASE>" "<MESH_ID>"
# Exemplo (pegando os dados do comando 'Add Agent -> Linux' do MeshCentral):
#   sh scripts/meshcentral-configurar-agente.sh "https://172.16.152.2:8090" "SEU_ID_DO_GRUPO_AQUI"
set -e
cd "$(dirname "$0")/.."

URL="$1"
MESH_ID="$2"
if [ -z "$URL" ] || [ -z "$MESH_ID" ]; then
    echo "Uso: sh scripts/meshcentral-configurar-agente.sh <URL_MESHCENTRAL> <MESH_ID>" >&2
    echo "Exemplo: sh scripts/meshcentral-configurar-agente.sh https://172.16.152.2:8090 'abc123...'" >&2
    exit 1
fi

CONF=packages/viaunix-remote/etc/viaunix/meshcentral.conf
cat > "$CONF" <<EOF
# Configuracao do agente MeshCentral (gerada por scripts/meshcentral-configurar-agente.sh)
MESHCENTRAL_URL=$URL
MESH_ID=$MESH_ID
EOF

# Incrementa automaticamente o ultimo digito da Version do viaunix-remote para publicar via APT
CTRL=packages/viaunix-remote/DEBIAN/control
CUR=$(awk '/^Version:/{print $2}' "$CTRL")
MAJ_MIN=$(echo "$CUR" | cut -d. -f1,2)
PATCH=$(echo "$CUR" | cut -d. -f3)
NEXT="${MAJ_MIN}.$((PATCH + 1))"
sed -i "s/^Version:.*/Version: $NEXT/" "$CTRL"

echo "Configurado $CONF (viaunix-remote -> $NEXT)."
echo "Agora publique com: sh scripts/publicar-local.sh"
