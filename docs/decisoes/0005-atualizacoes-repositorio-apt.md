# ADR 0005 – Atualizações via repositório APT próprio

- **Data:** 2026-11-23
- **Status:** Aceita

## Contexto
As customizações estavam copiadas na imagem (`includes.chroot`), sem caminho de atualização: qualquer correção exigia nova ISO e reinstalação.

## Decisão
Empacotar as customizações em `.deb` (`viaunix-base`, `-firewall`, `-branding`, `-release`, `-archive-keyring`), publicá-las num repositório APT assinado com GPG (reprepro, servidor web próprio) e fazer a ISO instalar o metapacote `viaunix-base`. O repositório é acessado por IP (`repo.conf`), podendo migrar para domínio/HTTPS depois.

## Consequências
- Toda mudança exige subir a versão do pacote (disciplina de versionamento, alinhada ao Git).
- `os-release` e `issue` usam `dpkg-divert` para coexistir com `base-files`.
- A chave privada GPG passa a ser ativo crítico (backup, acesso restrito).
- Itens exclusivos da ISO (Calamares, sessão Live) não são atualizáveis por APT.
