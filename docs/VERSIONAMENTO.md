# Fluxo de versionamento

## Regras
1. Tudo que define o ViaUnix está no Git: configs, pacotes, branding, scripts, docs. ISOs **não** (ficam no `.gitignore`; publique como *release*).
2. Branches: `main` (estável), `develop` (integração), `feature/<tema>`.
3. Commits no padrão *Conventional Commits* em português: `feat(firewall): ...`, `fix(pacotes): ...`, `docs: ...`, `chore: ...`.
4. Cada mudança relevante atualiza o `CHANGELOG.md` e, se for decisão de arquitetura, cria um ADR em `docs/decisoes/`.
5. Releases: tag `vX.Y.Z` em `main` (ex.: `v1.0.0`). Atualize `VERSION_ID` em `config/includes.chroot/etc/os-release`.
6. Base Debian: registre a versão de base no CHANGELOG (ex.: "base Debian 13.7"). Para acompanhar atualizações do Debian, refaça o build e revise o diff de pacotes.

## Atualização futura
- Como tudo é reproduzível via `lb build`, atualizar = alterar listas/configs, rodar build, testar em VM, taguear.
- Mudanças do usuário final sobre o sistema instalado serão entregues por metapacotes `.deb` versionados (fase futura).

## Documentação
- `docs/decisoes/` – ADRs (por que escolhemos X)
- `docs/arquitetura.md` – visão geral
- `docs/firewall.md` – regras e como alterá-las
