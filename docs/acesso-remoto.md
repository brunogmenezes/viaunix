# Acesso remoto nativo embutido no ViaUnix Manager (noVNC)

Acesso remoto gráfico **100% dentro do navegador** no próprio ViaUnix Manager (`http://172.16.152.2:8088`), sem instalar programa no PC do suporte, sem configurar IP/chave, sem portas extras e com **autorização explícita do colaborador + auditoria completa**.

## Como funciona
1. No ViaUnix Manager, o operador clica em **Acesso Remoto** na estação e informa o **motivo / chamado**.
2. Em até **5 segundos**, o `viaunix-agent` exibe a janela GTK3 na tela do colaborador (**Operador TI** + **Motivo** + **✔ Autorizar** / **✖ Recusar**, expira em 60s).
3. Se o colaborador autorizar:
   - O agente sobe um `x11vnc` efêmero **somente em `127.0.0.1`** com senha única aleatória de 8 caracteres (OTP) — nenhuma porta de entrada é aberta no firewall `nftables`.
   - O agente abre um **túnel WebSocket reverso** (`viaunix-vnc-tunnel`) para o ViaUnix Manager na mesma porta `8088` (`/ws/vnc/agent/{session_id}`).
   - O operador clica em **Abrir Tela Remota Agora**: abre `/vnc.html?session={id}` (usando o pacote oficial `novnc` do Debian) autenticando automaticamente com o OTP — **zero senha para digitar**.
4. Ao clicar em **Encerrar Sessão** (ou fechar a janela), o Manager fecha o WebSocket, o agente mata o `x11vnc` imediatamente e o fim da sessão é registrado no PostgreSQL (`remote_sessions` e `audit_log`).

## Atualização no servidor `172.16.152.2`
```sh
cd /opt/viaunix && git checkout -- . && git pull
apt-get install -y novnc
/opt/viaunix-manager/venv/bin/pip install -r manager/requirements.txt
cp -a manager/. /opt/viaunix-manager/ && systemctl restart viaunix-manager
systemctl disable --now rustdesk-hbbs rustdesk-hbbr 2>/dev/null || true
sh scripts/vpn-configurar.sh /root/client.ovpn 'sup3s3nha0p3nvpn'
sh scripts/publicar-local.sh
```

## Nas estações ViaUnix
Basta clicar em **Atualizar** no ViaUnix Manager (ou rodar `apt update && apt full-upgrade`). O `viaunix-remote 3.0.0` desativa o antigo RustDesk e instala o `x11vnc`, e o `viaunix-agent 1.2.0` ativa o túnel reverso.
