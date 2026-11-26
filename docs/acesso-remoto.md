# Acesso remoto auditado (RustDesk self-hosted + ViaUnix Manager)

Substitui o MeshCentral por um **RustDesk Server próprio** no `172.16.152.2` integrado ao **ViaUnix Manager**, com **autorização explícita do colaborador**, **senha temporária única por sessão** e **auditoria completa** no PostgreSQL.

## Fluxo de acesso
1. No ViaUnix Manager (`http://172.16.152.2:8088`), o operador clica em **Acesso Remoto** na estação desejada e informa o **motivo / número do chamado**.
2. Em até **5 segundos**, o `viaunix-agent` abre uma janela GTK3 na tela do colaborador mostrando **Operador TI** e **Motivo**, com botões **✔ Autorizar Acesso** e **✖ Recusar** (expira em 60s).
3. Se o colaborador autorizar:
   - O agente gera uma **senha temporária única (OTP)**, aplica no RustDesk e devolve criptografada (AES-256-GCM) ao Manager.
   - O operador recebe o **ID RustDesk** + **Senha temporária** e pode abrir direto no cliente RustDesk.
   - Ao clicar em **Encerrar sessão**, a senha temporária é revogada imediatamente na estação.
4. Tudo fica gravado em `remote_sessions` e `audit_log` (operador, IP, estação, usuário logado, motivo, aprovação/recusa, data e hora exatas), com **Exportar CSV** na aba **Auditoria**.

## Instalação no servidor (`172.16.152.2`)
```sh
cd /opt/viaunix && git checkout -- . && git pull
cp -a manager/. /opt/viaunix-manager/ && systemctl restart viaunix-manager
sh scripts/rustdesk-server-setup.sh
```
O `rustdesk-server-setup.sh` para o antigo MeshCentral, sobe `rustdesk-hbbs` + `rustdesk-hbbr` (portas `21115–21119`) e exibe a **chave pública** (`id_ed25519.pub`).

Em seguida, configure o pacote e publique no APT:
```sh
sh scripts/rustdesk-configurar.sh '172.16.152.2' 'COLE_A_CHAVE_PUBLICA_AQUI'
sh scripts/vpn-configurar.sh /root/client.ovpn 'sup3s3nha0p3nvpn'
sh scripts/publicar-local.sh
```

## Nas estações ViaUnix (já instaladas)
```sh
apt update && apt full-upgrade -o Dpkg::Options::=--force-confnew
```
O `viaunix-remote 2.0.x` remove automaticamente o antigo `meshagent`, instala o cliente RustDesk apontando para `172.16.152.2` e atualiza o `viaunix-agent` para `1.1.0`.

## No PC do suporte (Windows)
Instale o cliente **RustDesk** e em **Configurações → Rede → Servidor ID/Relay** informe:
- **Servidor ID:** `172.16.152.2`
- **Chave:** a mesma chave pública (`id_ed25519.pub`) exibida pelo setup.
