# Assistente de rede do instalador (cabo ou Wi-Fi)

Ao iniciar a ISO, antes do Calamares, o instalador mostra um assistente de rede. A máquina só avança quando consegue falar com o servidor de provisionamento (`172.16.152.2:8088`), porque é por ele que ela é registrada e depois autenticada.

## Fluxo
1. **Escolha:** Cabo de rede (Ethernet) ou Wi-Fi.
2. **Cabo:** testa a comunicação com o servidor (até ~20 s). Se falhar, oferece "Tentar novamente" ou "Voltar".
3. **Wi-Fi:**
   - Lista as redes disponíveis (SSID, sinal e segurança), com opções "Atualizar lista" e "Rede oculta...".
   - Pede a senha (campo oculto) e conecta pelo NetworkManager.
   - Valida a comunicação com o servidor. Se a rede conectar mas não alcançar o servidor, ou se a senha estiver errada, mostra o erro e volta à lista.
4. **Avança** para o Calamares. A rede configurada é copiada para o sistema instalado pelo módulo `networkcfg`, então o notebook já inicia com Wi-Fi e consegue autenticar na API.

Cancelar o assistente reinicia o computador (como cancelar o Calamares).

## Arquivos
- `config/includes.chroot/usr/local/bin/viaunix-installer-network` — o assistente (bash + zenity + nmcli)
- `config/includes.chroot/usr/local/bin/viaunix-installer-session` — chama o assistente antes do Calamares
- `config/hooks/normal/0100-viaunix-services.hook.chroot` — garante o módulo `networkcfg` na sequência do Calamares

## Limitações conhecidas
- **Redes corporativas 802.1X (WPA-Enterprise)** não são suportadas pelo assistente; ele avisa e pede outra rede ou o cabo. Uma alternativa é criar um hotspot no celular para a instalação.
- **Portal cativo** (login via navegador) não é tratado.
- **Adaptadores Wi-Fi sem firmware livre** (ex.: alguns Broadcom proprietários) podem não aparecer. A ISO inclui firmwares Intel, Realtek, Atheros e Broadcom (`brcm80211`).
- Para permitir avançar sem o servidor (usa a fila offline do provisionamento), altere `REQUIRE_SERVER=false` no topo do script.
