# Ambiente de build (VirtualBox)

O `live-build` só roda em Linux. Use uma VM Debian 13 dedicada ao build.

## 1. Criar a VM
1. Instale o VirtualBox (virtualbox.org). Habilite a virtualização (VT-x/AMD-V) na BIOS.
2. Nova VM: nome `viaunix-build`, tipo Linux / Debian (64-bit), ISO `debian-13.7.0-amd64-netinst.iso`.
3. Recursos: **4 CPUs, 8 GB RAM, disco 80 GB** (dinâmico). O build baixa vários GB.
4. Rede: NAT. Instale o Debian com o "utilitários de sistema padrão" e **SSH server**; sem desktop é suficiente.

## 2. Preparar
```sh
su -
apt update && apt install -y git live-build sudo
```

## 3. Obter o projeto
Após o repositório estar no GitHub:
```sh
git clone https://github.com/<usuario>/viaunix.git ~/viaunix
cd ~/viaunix
```
(Alternativa: pasta compartilhada do VirtualBox, mas copie para o disco da VM antes do build; **não** rode em pasta compartilhada.)

## 4. Gerar a ISO
```sh
sudo sh scripts/build.sh
```
A ISO aparece na raiz do projeto. Copie-a para o Windows (scp ou pasta compartilhada).

## 5. Testar a ISO
Crie outra VM (`viaunix-teste`, 4 GB RAM, 30 GB disco, EFI habilitado) e inicie pela ISO.
