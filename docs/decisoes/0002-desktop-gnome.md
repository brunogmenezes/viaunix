# ADR 0002 – Desktop: GNOME

- **Data:** 2026-11-17
- **Status:** Aceita

## Contexto
O ViaUnix é um desktop de trabalho corporativo. Substitui a escolha provisória por XFCE.

## Decisão
Usar **GNOME** (`task-gnome-desktop` + `gdm3`), que é o desktop padrão do Debian: bem testado, moderno e com boa integração a VPN (NetworkManager) e políticas corporativas (dconf).

## Consequências
- Consome mais recursos que XFCE; a VM de teste deve ter pelo menos 4 GB de RAM.
- Personalização via dconf/gsettings, extensões e tema em `config/includes.chroot`.
