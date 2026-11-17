# ViaUnix

Distribuição desktop corporativa baseada em Debian 13 (Trixie), em pt-BR.

## Decisões iniciais (alteráveis)
- Base: Debian 13, amd64, via `live-build` + instalador **Calamares** (wizard gráfico)
- Desktop: GNOME (decisão do projeto, ver ADR 0002)
- Pré-instalado: LibreOffice completo + pt-BR, OpenVPN (+ NetworkManager), firewall nftables, fail2ban, AppArmor
- Firewall: `config/includes.chroot/etc/nftables.conf` (entrada negada por padrão)

## Estrutura
- `auto/config` – parâmetros do live-build
- `config/package-lists` – pacotes
- `config/includes.chroot` – arquivos copiados para o sistema (os-release, firewall…)
- `config/hooks` – scripts executados na construção
- `scripts/build.sh` – gera a ISO (rodar em Linux/WSL2/VM)

## Build
Em Linux como root, copie o projeto para `~/viaunix` e rode `sh scripts/build.sh`.
Como montar a VM de build no VirtualBox: [docs/ambiente-de-build.md](docs/ambiente-de-build.md).
Teste a ISO com QEMU/VirtualBox.

## Próximos passos
1. Gerar a 1ª ISO e validar boot
2. Configurar Calamares (branding, slideshow, partições, criptografia LUKS opcional)
3. Branding: logo, wallpaper, GRUB, Plymouth, tema XFCE
4. Metapacotes `viaunix-base` / `viaunix-desktop`
5. Firewall GUI/perfis (casa/empresa/VPN), kill-switch de VPN
6. Repositório APT próprio, CI, assinatura GPG
