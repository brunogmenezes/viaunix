# Acesso remoto gráfico autônomo (MeshCentral + `viaunix-remote`)

Permite acessar a tela das estações ViaUnix **direto pelo navegador**, sem instalar aplicativo no PC do suporte e **sem necessidade de o usuário autorizar** (inclusive na tela de login GDM).

## Como funciona
- **Servidor:** MeshCentral rodando no `172.16.152.2` na porta HTTPS **`8090`** (`https://172.16.152.2:8090`).
- **Estações (`viaunix-remote`):**
  1. Configura `WaylandEnable=false` no `/etc/gdm3/daemon.conf` (sessão GNOME em X11, necessária para captura de tela sem confirmação do usuário).
  2. Instala e ativa o agente `meshagent.service` (conexão 100% de saída — o firewall `nftables` continua fechado).
- **ViaUnix Manager:** exibe o botão **Tela Remota (MeshCentral)** abrindo `https://172.16.152.2:8090`.

## Passo a passo de instalação (uma vez no servidor `172.16.152.2`)

### 1. Subir o MeshCentral
```sh
cd /opt/viaunix && git checkout -- . && git pull
sh scripts/meshcentral-server-setup.sh
```
Acesse **`https://172.16.152.2:8090`** no navegador (aceite o certificado autoassinado):
1. Crie sua conta administradora na 1ª tela.
2. Trave novos cadastros em `/opt/meshcentral/meshcentral-data/config.json` trocando `"newAccounts": false` e rode `systemctl restart meshcentral`.
3. Clique em **My Devices → Add a new device group**, crie o grupo **`ViaUnix`** (tipo *Agent*).
4. Dentro do grupo `ViaUnix`, clique em **Add Agent → Linux / BSD / macOS** e olhe o comando exibido — ele termina com a URL e o `MESH_ID` (uma string longa entre aspas).

### 2. Vincular o agente ao pacote `viaunix-remote` e publicar
No servidor `172.16.152.2`:
```sh
cd /opt/viaunix
sh scripts/meshcentral-configurar-agente.sh "https://172.16.152.2:8090" "COLE_O_MESH_ID_AQUI"
sh scripts/publicar-local.sh
```
*(Para que novas ISOs também já venham com o `MESH_ID`, commite `packages/viaunix-remote/etc/viaunix/meshcentral.conf` no Git se o repositório for privado, ou mantenha-o só no servidor de publicação.)*

### 3. Nas estações ViaUnix
Basta atualizar via APT (ou pelo botão **Atualizar** no ViaUnix Manager) e reiniciar uma vez (para o GDM assumir X11):
```sh
apt update && apt full-upgrade -o Dpkg::Options::=--force-confnew
systemctl reboot
```
Após o reboot, a estação aparece automaticamente em `https://172.16.152.2:8090` → clique na máquina → aba **Desktop** → **Connect**.
