# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/) e versionamento semântico (`MAJOR.MINOR.PATCH`).
Toda modificação no ViaUnix deve ser registrada aqui **no mesmo commit** que a faz.

## [Não lançado]

### Corrigido
- MeshCentral + `viaunix-remote` 1.0.4: configura `agentPort: 8091` com TLS nativo (`agentPortTls: true`) para o `meshagent` (que exige `wss://`), mantendo a interface web em HTTP na `8090` (`tlsOffload: true`).
- `viaunix-remote` 1.0.2: executa `meshinstall.sh` com `bash` (usava `sh`/dash e falhava em `[[`) e ajusta `wss://` para `ws://` no `meshagent.msh` quando `MESHCENTRAL_URL` é `http://`.
- MeshCentral: habilitado `tlsOffload: true` (`http://172.16.152.2:8090`) porque o firewall/IPS da rede derruba handshakes TLS por IP (sem SNI) em portas altas.
- `viaunix-branding` 1.0.3: corrige tela de login GDM no Debian 13 (grava também em `/usr/share/gdm/dconf/99-viaunix-settings`, atualiza `/etc/gdm3/greeter.dconf-defaults`, roda `generate-config`/`dconf compile` e adiciona fallback `dpkg-divert` no `viaunix-gdm-theme`).
- `viaunix-firewall` 1.0.2: corrige `nftables.conf` com LF puro (CRLF impedia o `nftables` de iniciar), valida sintaxe mostrando erro e reinicia o serviço; `build-packages.sh` remove `\r` de todos os arquivos de texto dos pacotes.
- `viaunix-provision` 1.0.0 (`viaunix-base` 1.0.3): empacotado como `.deb` para rodar também em VMs já instaladas via `apt full-upgrade`, gerando credenciais aleatórias, enviando ao `172.16.152.2:8088` e travando contas `sudo` antigas somente após confirmação do servidor.
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
- Acesso remoto gráfico autônomo via MeshCentral (`docs/acesso-remoto.md`): `scripts/meshcentral-server-setup.sh` (porta `8090`), `scripts/meshcentral-configurar-agente.sh`, pacote `viaunix-remote` 1.0.0 (`WaylandEnable=false` no GDM + instalação automática do `meshagent`, incluído em `viaunix-base` 1.0.5) e botão **Tela Remota** no ViaUnix Manager. Ainda **não testado**.
- **ViaUnix Manager + `viaunix-agent`** (ADR 0007, `docs/manager.md`): painel web em `https://172.16.152.2:8443` (Nginx + FastAPI + PostgreSQL), cofre de senhas em **AES-256-GCM** com chave mestra externa e trilha de auditoria, login via API Júpiter (`ADMIN_USERS`) + admin local de emergência, migração automática de `maquinas.jsonl` e pacote `viaunix-agent` 1.0.0 (`viaunix-base` 1.0.4) para telemetria e ações remotas (reiniciar, desligar, atualizar APT, bloquear tela, rotacionar senhas e console remoto) sem abrir portas no firewall. Ainda **não testado**.
- Provisionamento automático no Calamares (`docs/provisionamento.md`): remove a tela de usuário/hostname/senha, gera credenciais aleatórias únicas (`viaunix-XXXXXX`, `adm-XXXXXX`, senhas fortes) e envia ao servidor `172.16.152.2:8088` (`scripts/provision-server-setup.sh`, `viaunix-maquinas`), com fila de reenvio offline (`viaunix-provision-retry.service`). Ainda **não testado**.
- Tela de login GDM (`viaunix-branding` 1.0.2): remove o logo do Debian 13, aplica o logo ViaUnix (`viaunix-gdm-logo.png` 96×96) + o mesmo papel de parede da área de trabalho no fundo do GDM (`viaunix-gdm-theme` via `gdm-theme.gresource`) e trava `disable-user-list=true` (campo de usuário sempre vazio para estação compartilhada). Ainda **não testado**.
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
