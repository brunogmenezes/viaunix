# ADR 0004 – Live exclusivo para instalação

- **Data:** 2026-11-23
- **Status:** Aceita

## Decisão
A ISO não oferece desktop Live: ao iniciar, abre **somente o Calamares**, em tela cheia, já em pt-BR e fuso America/Sao_Paulo.

## Implementação
- Unit `viaunix-live-installer.service` (só roda com `boot=live` no kernel) executa `/usr/local/sbin/viaunix-live-setup` antes do GDM.
- O script cria a sessão X11 `viaunix-installer`, configura login automático do usuário live, bloqueia a senha dele e mascara os consoles tty2–6.
- A sessão (`/usr/local/bin/viaunix-installer-session`) inicia o `matchbox-window-manager` (sem barras/menus) e o `sudo calamares`; ao encerrar, reinicia o computador.
- Tudo é escrito em áreas voláteis do Live, então o sistema instalado inicia o GNOME normalmente.
- Fuso: parâmetro de boot `timezone=`, `locale.conf` do Calamares e hook de build; sincronismo de hora com `systemd-timesyncd`.

## Limites
Não é uma barreira de segurança: quem controla o menu de boot da ISO ou a BIOS pode contornar. Para diagnóstico, existe o modo de recuperação do menu de boot da ISO (a avaliar).

## Consequências
- Cancelar o instalador reinicia a máquina.
- Para depurar uma ISO, é preciso editar o parâmetro de boot (tecla `e` no menu) e remover `boot=live` não resolve: use um build de teste sem este serviço (desabilitar `viaunix-live-installer.service` no hook).
