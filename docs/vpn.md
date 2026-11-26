# VPN corporativa automática (`viaunix-vpn`)

Conecta automaticamente a estação ViaUnix na VPN OpenVPN usando o **mesmo usuário e senha** digitados no login ou no desbloqueio de tela, com a senha da chave privada configurada automaticamente (`askpass`).

## Como funciona
1. **Antes do login (tela de login GDM):** o `viaunix-vpn` (1.1.0+) exibe uma barra flutuante **ViaUnix VPN** no canto superior esquerdo do GDM (`/usr/share/gdm/greeter/autostart/viaunix-vpn-greeter.desktop` → `/usr/libexec/viaunix-vpn-gui --greeter`), permitindo conectar/desconectar na VPN antes de fazer login (e também aparece como app **ViaUnix VPN** no menu do GNOME).
2. Ao fazer login no GDM (ou desbloquear a tela), o `viaunix-auth` (1.0.3+) também passa usuário e senha via `stdin` para `/usr/sbin/viaunix-vpn-connect`.
2. As credenciais são salvas **somente em RAM** (`/run/viaunix-vpn/auth`, `tmpfs`, `0600 root:root`).
3. O serviço `openvpn-client@viaunix.service` sobe sem travar o login (`--no-block`), lendo `/etc/openvpn/client/viaunix.conf` e `/etc/viaunix/vpn-keypass` (`0600 root:root`).
4. **Estação bloqueada:** como roda como serviço de sistema (`systemd`), **bloquear a tela não derruba a VPN** — e se a rede oscilar enquanto bloqueada, o OpenVPN reconecta automaticamente (`ping-restart 45`, `connect-retry 1`). Se precisar conectar/reiniciar manualmente com a estação bloqueada, basta rodar `systemctl restart openvpn-client@viaunix` pelo Console do ViaUnix Manager.
5. **Troca de usuário:** se outro colaborador logar na mesma estação, `/run/viaunix-vpn/auth` é atualizado e o túnel reconecta com as credenciais do novo usuário.

## Como configurar no servidor `172.16.152.2` (sem expor a chave no GitHub)
1. Copie o arquivo `.ovpn` para o servidor (ex.: `/root/client.ovpn`).
2. No servidor, configure e publique o pacote:
   ```sh
   cd /opt/viaunix && git checkout -- . && git pull
   sh scripts/vpn-configurar.sh /root/client.ovpn 'SENHA_DA_CHAVE_PRIVADA'
   sh scripts/publicar-local.sh
   ```
3. Nas estações ViaUnix:
   ```sh
   apt update && apt full-upgrade
   ```
4. Confira após logar:
   ```sh
   viaunix-vpn-status
   ```
