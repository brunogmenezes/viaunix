# Provisionamento automático na instalação (`viaunix-provision`)

O instalador Calamares do ViaUnix **não exibe a tela de criação de usuário, nome do computador e senha**. Esses dados são gerados aleatoriamente, sem repetição, e enviados ao servidor remoto (`172.16.152.2`).

## O que é gerado em cada máquina
- **Hostname:** `viaunix-<6 hex>` (ex.: `viaunix-a8f3c1`)
- **Usuário admin local (suporte):** `adm-<6 alnum>` no grupo `sudo`
- **Senha do admin local:** 16 caracteres aleatórios fortes
- **Senha do `root`:** 16 caracteres aleatórios fortes
- **Metadados:** MAC da placa de rede, serial/UUID DMI, IP de origem e data/hora

## Como funciona no servidor (`172.16.152.2`)
1. Instale uma vez (como root):
   ```sh
   cd /opt/viaunix && git pull && sh scripts/provision-server-setup.sh
   ```
2. O serviço `viaunix-provision-server.service` escuta na porta `8088` (`/api/provision`), valida o cabeçalho `X-ViaUnix-Token`, rejeita duplicatas (`409 Conflict`, fazendo o instalador gerar outro par) e grava em:
   - `/var/lib/viaunix-provision/maquinas.jsonl` (`0600 root:root`)
   - `/var/lib/viaunix-provision/maquinas.csv` (`0600 root:root`)
   *(Nunca fica em `/var/www/html`.)*
3. Para consultar todas as máquinas instaladas:
   ```sh
   viaunix-maquinas
   ```

## VMs já instaladas (atualização via APT)
O provisionamento também foi empacotado em **`viaunix-provision`** (incluído em `viaunix-base` 1.0.3). Ao rodar `apt update && apt full-upgrade` em uma VM já instalada que ainda não foi provisionada:
- Gera `hostname`, `adm-XXXXXX` (sudo) e senhas fortes aleatórias e envia ao servidor `172.16.152.2:8088`.
- **Somente após o servidor confirmar recebimento (`201`)**, trava as senhas locais antigas de contas `sudo` anteriores (ex.: usuário criado na instalação antiga).

## Instalação sem rede (contingência)
Se a estação estiver sem acesso ao `172.16.152.2` na hora da instalação, as credenciais são salvas em `/var/lib/viaunix-provision/pending.json` (`0600 root:root`). No 1º boot com rede, `viaunix-provision-retry.service` envia ao servidor e remove o arquivo local.

## Segurança em produção
Antes de distribuir a ISO em produção, troque o `PROVISION_TOKEN` padrão por um segredo gerado aleatoriamente (`openssl rand -hex 24`) em:
- Servidor: `/etc/viaunix/provision-server.conf` (e reinicie `systemctl restart viaunix-provision-server`)
- ISO: `config/includes.chroot/etc/viaunix/provision.conf`
