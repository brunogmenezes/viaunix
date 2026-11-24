# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/) e versionamento semântico (`MAJOR.MINOR.PATCH`).
Toda modificação no ViaUnix deve ser registrada aqui **no mesmo commit** que a faz.

## [Não lançado]

### Corrigido
- `viaunix-auth` 1.0.2: usa caminho absoluto `/usr/sbin/useradd` e `PATH` explícito (no contexto do GDM/PAM, `/usr/sbin` não vem no `PATH`).
- `viaunix-auth` 1.0.1: ajusta `pam_succeed_if` em `/etc/pam.d/gdm-password` para ignorar `user_unknown` no 1º login de usuários da API (sem liberar `root`), adiciona `useradd --badname` para nomes com maiúsculas (ex.: `Brunog`) e registra no syslog qualquer saída antecipada/erro.
- Publicação: `scripts/repo-incluir.sh` publica só pacotes com versão nova (antes o reprepro recusava os `.deb` recompilados com mesma versão) e sempre exporta o índice.
- `viaunix-firewall` 1.0.1: usa `dpkg-divert` para `/etc/nftables.conf` (conflito com o pacote `nftables` ao instalar).
- `repo-server-setup.sh`: `Architectures` do reprepro sem `all` (erro "contains an architecture called 'all'"); pacotes `all` já são aceitos.
- Instalador: falha "Erro do Gerenciador de Pacotes" (apt remove, código 100) ao remover pacotes live. Adicionado `etc/calamares/modules/packages.conf` próprio, sem `live-task-*`.
- Build: conflito `grub-efi-amd64` x `grub-pc`; agora `grub-efi-amd64` + `grub-pc-bin` (instala em UEFI e BIOS), `shim-signed`, `efibootmgr`.
- Build: `auto/config` sem permissão de execução era ignorado pelo live-build (usava `testing`/`main`). Agora marcado como executável no Git e `build.sh` aplica `chmod +x`.
- Build: `--parent-archive-areas` com `non-free-firmware` (firmwares/microcode não eram encontrados); removidos `evince` e `network-manager-gnome` da lista (sem candidato no trixie; o `task-gnome-desktop` já traz leitor de PDF e integração de rede).

### Alterado
- Desktop definido como GNOME em vez de XFCE (ADR 0002); Calamares confirmado (ADR 0001).
- `docs/ambiente-de-build.md` com a URL real do repositório e instrução de `git pull`.
- Firewall, branding, `os-release`/`issue` saíram de `includes.chroot` para pacotes; a ISO instala só `viaunix-base` + itens do Live/instalador. `build.sh` agora gera os `.deb`.
- **Pré-requisito do build:** a chave pública do repositório precisa estar em `packages/viaunix-archive-keyring/usr/share/keyrings/` (ver docs).

### Adicionado
- Google Chrome (`google-chrome-stable`) incluído automaticamente no repositório APT e na ISO via `scripts/baixar-chrome.sh` (`viaunix-base` 1.0.2).
- Atalho automático do Google Chrome na Área de Trabalho no GNOME (`viaunix-branding` 1.0.1): instala/habilita a extensão `gnome-shell-extension-desktop-icons-ng` (`ding@rastersoft.com`) e cria/confia o atalho em `Área de trabalho` via autostart XDG para usuários novos e existentes. Ainda **não testado**.
- Autenticação externa via API Júpiter (`viaunix-auth` 1.0.0, ADR 0006, `docs/autenticacao.md`): PAM (`pam-auth-update` + `pam_exec`), criação automática de usuário sem `sudo`, cache offline com `scrypt` e revogação, e login direto sem lista no GDM. Incluído em `viaunix-base` 1.0.1. Ainda **não testado**.
- `scripts/publicar-local.sh`: o servidor do repositório puxa do Git, gera os `.deb` e publica localmente (sem SSH/scp). Ainda **não testado**.
- Atualizações por APT (ADR 0005, `docs/atualizacoes.md`): pacotes `.deb` em `packages/` (`viaunix-base`, `-firewall`, `-branding`, `-release`, `-archive-keyring`), `repo.conf`, `scripts/build-packages.sh`, `scripts/publicar.sh`, `scripts/repo-server-setup.sh`. Ainda **não testado**.- Live exclusivo para instalação: abre só o Calamares em tela cheia, sem desktop/terminal (ADR 0004). Fuso America/Sao_Paulo no Calamares e `systemd-timesyncd`. Ainda **não testado**.
- Branding no boot (tema Plymouth `viaunix`), GRUB do sistema instalado (`/etc/default/grub.d/viaunix.cfg`) e Calamares (`/etc/calamares/branding/viaunix`, slideshow pt-BR). Ainda **não testado** em ISO.
- `gerar-wallpaper.ps1` agora também gera os derivados (GRUB, Plymouth, Calamares).
- Hooks com permissão de execução registrada no Git.
- Identidade visual Júpiter: papel de parede, tela de bloqueio e logo de login travados via dconf (ADR 0003).
- Script `scripts/gerar-wallpaper.ps1`.
- Guia de ambiente de build com VirtualBox (`docs/ambiente-de-build.md`).

### Adicionado (base inicial)
- Esqueleto do projeto com `live-build` sobre Debian 13 (trixie), amd64.
- Pacotes: GNOME, LibreOffice completo pt-BR, OpenVPN + NetworkManager, nftables, fail2ban, AppArmor, Calamares.
- Firewall nftables padrão (entrada negada, saída liberada).
- Identidade (`os-release`, `issue`) e locale pt-BR / fuso America/Sao_Paulo.
- Documentação em `docs/` e fluxo de versionamento.
