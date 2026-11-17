# Firewall

Arquivo: `config/includes.chroot/etc/nftables.conf` (instalado em `/etc/nftables.conf`, serviço `nftables`).

- Entrada: negada por padrão; permite loopback, conexões já estabelecidas, ICMP limitado, DHCP.
- Encaminhamento: negado.
- Saída: liberada.
- SSH de entrada: desligado (linha comentada na cadeia `input`).
- Logs: `journalctl -k | grep viaunix-fw`.

Mudanças devem ser feitas no repositório, registradas no CHANGELOG e testadas em VM (`nft -c -f nftables.conf` valida a sintaxe).
