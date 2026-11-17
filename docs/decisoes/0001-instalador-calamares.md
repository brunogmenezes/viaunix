# ADR 0001 – Instalador: Calamares

- **Data:** 2026-11-17
- **Status:** Proposta (aguardando confirmação)

## Contexto
O instalador padrão do Debian (debian-installer) é em modo texto e em etapas pouco amigáveis. Queremos um instalador em formato wizard, voltado ao desktop corporativo.

## Decisão
Usar o **Calamares**: instalador gráfico, independente de distribuição, usado por Manjaro, KDE neon e outras. Passo a passo visual: idioma, fuso, teclado, particionamento (com criptografia opcional), usuário, resumo, instalação. É personalizável (logo, textos, slideshow, etapas) e já empacotado no Debian.

## Consequências
- Exige gerar uma ISO **Live** (o usuário testa o sistema antes de instalar) com `live-build`.
- Config do Calamares será versionada em `installer/`.
- Alternativa descartada: preseed no debian-installer (menos "wizard").
