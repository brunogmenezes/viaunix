# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/) e versionamento semântico (`MAJOR.MINOR.PATCH`).
Toda modificação no ViaUnix deve ser registrada aqui **no mesmo commit** que a faz.

## [Não lançado]

### Alterado
- Desktop definido como GNOME em vez de XFCE (ADR 0002); Calamares confirmado (ADR 0001).

### Adicionado
- Guia de ambiente de build com VirtualBox (`docs/ambiente-de-build.md`).

### Adicionado
- Esqueleto do projeto com `live-build` sobre Debian 13 (trixie), amd64.
- Pacotes: XFCE, LibreOffice completo pt-BR, OpenVPN + NetworkManager, nftables, fail2ban, AppArmor, Calamares.
- Firewall nftables padrão (entrada negada, saída liberada).
- Identidade (`os-release`, `issue`) e locale pt-BR / fuso America/Sao_Paulo.
- Documentação em `docs/` e fluxo de versionamento.
