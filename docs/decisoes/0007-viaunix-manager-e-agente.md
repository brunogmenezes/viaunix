# ADR 0007 – ViaUnix Manager (PostgreSQL + Nginx) e Agente (`viaunix-agent`)

- **Data:** 2026-11-24
- **Status:** Aceita

## Contexto
Precisamos gerenciar centralmente as estações ViaUnix a partir de um painel web no servidor `172.16.152.2` (que já roda PostgreSQL e Nginx), com senhas criptografadas em repouso e ações remotas (reiniciar, atualizar, rotacionar senhas, executar comandos) sem enfraquecer o firewall das estações.

## Decisão
- **Backend/Painel (`manager/`):** FastAPI + PostgreSQL + AES-256-GCM (chave mestra externa `/etc/viaunix/master.key`, `0600 root:root`), servido em `https://172.16.152.2:8443` via Nginx (site dedicado, sem interferir em sites existentes).
- **Login:** API Júpiter (restrito a `ADMIN_USERS`) + conta `admin` local de emergência (`scrypt`).
- **Agente (`viaunix-agent` 1.0.0 em `viaunix-base` 1.0.4):** conexão 100% de saída (polling a cada 30s) autenticada por token único por máquina (armazenado apenas como SHA-256 no banco).
- **Migração:** substitui `viaunix-provision-server` na porta `8088`, migrando `maquinas.jsonl` para o PostgreSQL criptografado e removendo arquivos em texto puro.

## Consequências
- O firewall `nftables` das estações continua 100% fechado para entrada.
- A chave mestra `/etc/viaunix/master.key` é crítica (perder a chave impede descriptografar senhas salvas; rotacionar senhas via agente resolve em máquinas online).
- Fase futura (Fase 3): tela remota gráfica (RustDesk self-hosted ou MeshCentral) acoplada ao painel.
