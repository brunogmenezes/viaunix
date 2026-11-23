# Atualizações do ViaUnix (repositório APT próprio)

Objetivo: corrigir e evoluir o ViaUnix **sem reinstalar**. Nas máquinas, basta `apt update && apt upgrade`.

## Como funciona
O que define o ViaUnix está em pacotes `.deb` versionados (`packages/`):

| Pacote | Conteúdo |
|---|---|
| `viaunix-base` | Metapacote: lista de tudo que o sistema deve ter (GNOME, LibreOffice, OpenVPN...) |
| `viaunix-firewall` | `/etc/nftables.conf` |
| `viaunix-branding` | Wallpaper, bloqueio, login, Plymouth, GRUB (reaplica as travas a cada update) |
| `viaunix-release` | `os-release` e `issue` |
| `viaunix-archive-keyring` | Chave GPG + fonte APT do repositório |

Os pacotes ficam num repositório APT assinado (GPG) no servidor. Atualizações do Debian continuam vindo do Debian.

**Não** é atualizável por APT o que é só da ISO (instalador Calamares, sessão Live). Isso só muda em instalações novas.

## Servidor: IP ou domínio?
- **IP funciona.** Basta `REPO_URL=http://172.16.152.2/viaunix/apt` em [repo.conf](../repo.conf).
- **HTTP é aceitável:** o APT valida a assinatura GPG, então adulterar pacotes no caminho não passa.
- **Subdomínio é opcional**, mas recomendado a longo prazo (ex.: `apt.suaempresa.com.br`, com HTTPS): se o IP mudar, é só atualizar o DNS; com IP fixo na ISO, as máquinas ficam presas a ele (ou precisam receber um pacote novo com a URL nova).

## Configuração inicial (uma vez)
1. **No servidor** (como root), com o projeto clonado ou só o script copiado:
   ```sh
   sh scripts/repo-server-setup.sh
   ```
   Cria o repositório (reprepro), gera a chave GPG e publica `viaunix-archive-keyring.gpg`.
2. **Copie a chave pública para o projeto** (na VM de build) e faça commit:
   ```sh
   scp root@172.16.152.2:/var/www/html/viaunix/apt/viaunix-archive-keyring.gpg \
       packages/viaunix-archive-keyring/usr/share/keyrings/
   git add packages && git commit -m "feat(repo): chave publica do repositorio" && git push
   ```
3. **Faça backup da chave privada** do servidor (`gpg --export-secret-keys`). Quem a tem controla as atualizações de todas as máquinas.
4. **SSH sem senha** da VM de build para o servidor: `ssh-copy-id root@172.16.152.2`.
5. **Publique a 1ª versão:** `sh scripts/publicar.sh`.

## Rotina de atualização
1. Altere o que for preciso (ex.: `packages/viaunix-firewall/etc/nftables.conf`).
2. **Aumente a `Version`** do pacote alterado em `packages/<pacote>/DEBIAN/control` (ex.: `1.0.0` → `1.0.1`). Sem isso, o APT não vê atualização e o reprepro recusa.
3. Registre no `CHANGELOG.md` e faça commit/push.
4. Na VM de build: `git pull && sh scripts/publicar.sh`.
5. Nas máquinas: `sudo apt update && sudo apt upgrade` (use `full-upgrade` se o `viaunix-base` ganhar dependências novas).

Para adicionar um aplicativo ao padrão do sistema: inclua-o em `Depends` do `viaunix-base`, aumente a versão e publique.

## VM já instalada (sem o repositório ainda)
Faça o *bootstrap* uma vez (como root), depois do passo 5 acima:
```sh
curl -fsSL http://172.16.152.2/viaunix/apt/viaunix-archive-keyring.gpg -o /usr/share/keyrings/viaunix-archive-keyring.gpg
cat > /etc/apt/sources.list.d/viaunix.sources <<'EOF'
Types: deb
URIs: http://172.16.152.2/viaunix/apt
Suites: trixie
Components: main
Signed-By: /usr/share/keyrings/viaunix-archive-keyring.gpg
EOF
apt update
apt install -o Dpkg::Options::=--force-confnew viaunix-base
```
A partir daí, `apt update && apt upgrade` basta.

## Cuidados
- Arquivos em `/etc` marcados como *conffile* (firewall, fonte APT): se o usuário editar, o APT pergunta antes de sobrescrever. O branding **não** é conffile de propósito, para as travas serem sempre reaplicadas.
- Atualizações automáticas (`unattended-upgrades`) ficam para uma fase seguinte, se desejado.
- ISO nova: `sh scripts/build.sh` já constrói os `.deb` e os embute; a ISO só precisa ser refeita para mudanças do instalador/Live.
