# Autenticação externa (`viaunix-auth`)

O pacote `viaunix-auth` integra o login do ViaUnix (GDM/GNOME, tela de bloqueio, SSH) à API da Júpiter:

- **Endpoint:** `POST https://api.jupiter.com.br/action/Usuario/logar`
- **Payload:** `{"usuario": "...", "senha": "..."}`
- **Aprovação:** HTTP 200 com `accessToken` não vazio.

## Como funciona no PAM
1. `pam_unix` roda primeiro (prioridade 256): coleta a senha e autentica **contas locais** (`root` e o administrador criado na instalação) sem depender da rede.
2. Se não for conta local, o PAM chama `/usr/sbin/viaunix-auth` via `pam_exec.so expose_authtok` (prioridade 192).
3. Se a API aprovar:
   - No primeiro login, cria o usuário Linux automaticamente (`/home/<usuario>`, shell `/bin/bash`, **sem `sudo`** e com senha local travada `!` em `/etc/shadow`).
   - Salva um hash `scrypt` com sal em `/var/lib/viaunix-auth/cache.json` (`0600 root:root`) para permitir login offline.
4. Se a API recusar (HTTP 4xx):
   - Apaga o cache offline daquele usuário (revogação imediata) e nega o login.
5. Se a máquina estiver **offline** (erro de rede/timeout):
   - Valida contra o cache `scrypt` local (se `ALLOW_OFFLINE_CACHE=true`).

## Tela de login (GDM)
O pacote configura `disable-user-list=true` no GDM (`/etc/dconf/db/gdm.d/10-viaunix-auth`), exibindo direto os campos de **Usuário** e **Senha**, para qualquer colaborador digitar seu login sem precisar clicar em "Não está na lista?".

## Configuração
Arquivo: `/etc/viaunix/auth.conf` (permissão `600`, somente `root`).
- `API_URL` – URL de autenticação.
- `TIMEOUT` – tempo limite em segundos (padrão: `10`).
- `AUTO_CREATE_USER` – cria usuário local no 1º acesso (padrão: `true`).
- `USER_GROUPS` – grupos extras do usuário criado (`sudo` é sempre ignorado).
- `ALLOW_OFFLINE_CACHE` – permite login sem rede usando hash da última senha válida (padrão: `true`).
- `VERIFY_TLS` – valida certificado HTTPS (padrão: `true`).
- `LOCAL_ONLY_USERS` – usuários que nunca consultam a API (padrão: `root`).

## Como testar e depurar
```sh
# Testar comunicação com a API sem alterar usuários locais
sudo /usr/sbin/viaunix-auth --test nome_usuario

# Ver logs de autenticação (nunca registra senha nem token)
journalctl -t viaunix-auth -n 30

# Conferir se o perfil PAM está ativo em /etc/pam.d/common-auth
grep viaunix-auth /etc/pam.d/common-auth
```
