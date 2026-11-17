# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/) e versionamento semântico (`MAJOR.MINOR.PATCH`).
Toda modificação no ViaUnix deve ser registrada aqui **no mesmo commit** que a faz.

## [Não lançado]

### Alterado
- Desktop definido como GNOME em vez de XFCE (ADR 0002); Calamares confirmado (ADR 0001).
- `docs/ambiente-de-build.md` com a URL real do repositório e instrução de `git pull`.

### Adicionado
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
