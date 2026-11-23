# ADR 0006 – Autenticação via API Júpiter (`viaunix-auth`)

- **Data:** 2026-11-23
- **Status:** Aceita

## Contexto
As estações ViaUnix precisam validar usuário e senha corporativos na API `https://api.jupiter.com.br/action/Usuario/logar`, mantendo contas locais de emergência/suporte e sem exigir reinstalação.

## Decisão
Criar o pacote `viaunix-auth` integrado ao PAM via `pam-auth-update` (`/usr/share/pam-configs/viaunix-auth`, prioridade 192, após `pam_unix`) usando `pam_exec.so expose_authtok` e script Python 3 sem dependências externas (`/usr/sbin/viaunix-auth`).

- Primeiro login cria o usuário Linux local automaticamente sem `sudo` e com senha local travada (`!`), impedindo bypass via `pam_unix`.
- Cache offline em `/var/lib/viaunix-auth/cache.json` com `scrypt`, revogado imediatamente em resposta 4xx da API.
- GDM configurado com `disable-user-list=true`.
- Incluído no metapacote `viaunix-base` (1.0.1) para entrega via `apt update && apt full-upgrade`.

## Consequências
- Contas locais com senha (como `root` e admin de suporte) continuam entrando mesmo sem rede.
- O token JWT retornado pela API é usado apenas como confirmação de login (não é persistido em disco nem registrado em log).
- Desinstalar `viaunix-auth` remove o perfil do PAM via `pam-auth-update` e restaura a lista de usuários do GDM.
