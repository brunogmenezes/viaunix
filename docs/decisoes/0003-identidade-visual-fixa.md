# ADR 0003 – Identidade visual fixa (logo Júpiter)

- **Data:** 2026-11-17
- **Status:** Aceita

## Decisão
O logo Júpiter Internet (`branding/logo-jupiter.png`) é a identidade visual padrão e **não alterável pelo usuário**:
- Papel de parede (claro e escuro) e tela de bloqueio: `viaunix-wallpaper.png` (3840x2160, logo centralizado sobre fundo azul-escuro), gerado por `scripts/gerar-wallpaper.ps1`.
- Tela de login (GDM): logo em `/usr/share/pixmaps/viaunix-logo.png`.

## Implementação
- Padrões via dconf em `/etc/dconf/db/local.d/00-viaunix-visual`.
- Travas em `/etc/dconf/db/local.d/locks/00-viaunix-visual`: o GNOME (Configurações, gsettings) bloqueia a alteração por usuários comuns.
- `dconf update` executado pelo hook de build.

## Limites
Um administrador (root/sudo) ainda consegue editar `/etc/dconf`; o bloqueio é para o usuário comum, não contra o administrador. Para dificultar mais, pode-se restringir sudo e proteger os arquivos via pacote `viaunix-branding`.

## Pendentes
Plymouth (boot), GRUB e Calamares com o mesmo logo.
