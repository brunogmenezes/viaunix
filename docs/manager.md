# ViaUnix Manager (Painel Web + Agente)

Painel central de gestão das estações ViaUnix no servidor `172.16.152.2`, sobre **PostgreSQL** e **Nginx (HTTPS na porta `8443`)**.

## Recursos
- **Inventário em tempo real:** status Online/Offline, usuário logado, IP, MAC, CPU, RAM, disco e último contato (heartbeat a cada 30s).
- **Cofre criptografado (AES-256-GCM):** senhas de `adm-XXXXXX` e `root` ficam criptografadas no PostgreSQL usando chave mestra externa (`/etc/viaunix/master.key`, `0600 root:root`). Só são descriptografadas ao clicar em **Senhas**, com registro na auditoria.
- **Ações remotas (sem abrir portas no firewall das estações):** Reiniciar, Desligar, Atualizar (`apt full-upgrade`), Bloquear tela, Rotacionar senhas e Console de comandos remotos com histórico de saída.
- **Login:** API da Júpiter (restrito aos usuários listados em `ADMIN_USERS` no `/etc/viaunix/manager.conf`) + conta `admin` local de emergência (hash `scrypt`).
- **Auditoria:** registra logins, visualizações de senha, provisionamentos e comandos executados.

## Instalação no servidor (`172.16.152.2`)
```sh
cd /opt/viaunix && git checkout -- . && git pull
sh scripts/manager-server-setup.sh
sh scripts/publicar-local.sh
```
O script:
1. Cria o usuário `viaunix` e o banco `viaunix_manager` no PostgreSQL.
2. Gera `/etc/viaunix/master.key` (faça backup!).
3. Substitui o `viaunix-provision-server` antigo na porta `8088` e migra `maquinas.jsonl` para o PostgreSQL com senhas criptografadas (apagando os arquivos em texto puro).
4. Configura o Nginx na porta **HTTPS `8443`** (`https://172.16.152.2:8443`) sem alterar os sites atuais.
5. Exibe **uma única vez** a senha da conta `admin` local de emergência.

## Adicionar mais administradores da TI
Edite `/etc/viaunix/manager.conf`, adicione os usuários da API Júpiter em `ADMIN_USERS=Brunog,OutroAdmin` e reinicie:
```sh
systemctl restart viaunix-manager
```

## Ativar o agente nas VMs já instaladas
```sh
su -
apt update && apt full-upgrade
systemctl status viaunix-agent --no-pager
```
Em até 30 segundos a estação aparece como **ONLINE** em `https://172.16.152.2:8443`.
