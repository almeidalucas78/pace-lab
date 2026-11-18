# Servidor na Oracle

Como o servidor do Pace Lab é criado e mantido (fase 9, etapa 1; decisões nos ADRs 0014 e 0015). Tudo pelo terminal com a OCI CLI, exceto o login.

## O que é
- Máquina `pacelab` na Oracle Always Free, região São Paulo (`sa-saopaulo-1`): `VM.Standard.A1.Flex` (ARM) com 2 OCPUs e 12 GB de memória (ou 1 OCPU e 6 GB, se só esse tamanho estiver disponível) e disco de 50 GB (dos 200 GB grátis; dá para aumentar depois, nunca diminuir).
- Ubuntu 26.04 LTS. O primeiro boot (`infra/oracle/cloud-init.yaml`) liga as atualizações de segurança automáticas (com reinício às 4h quando preciso), instala o Docker e o Tailscale, e proíbe login por senha e como root.
- Rede `pacelab-vcn` com uma sub-rede pública e o firewall `pacelab-firewall`: nenhuma porta aberta para a internet, a não ser o SSH a partir do IP de casa durante a instalação (depois fechado).
- Acesso administrativo só pelo Tailscale. O endereço público do Pace Lab (Tailscale Funnel) entra numa etapa seguinte.

## Pré-requisitos (no PC)
1. **OCI CLI** num ambiente separado do projeto:
   ```powershell
   py -3.13 -m venv $HOME\.oci-cli
   & "$HOME\.oci-cli\Scripts\python.exe" -m pip install oci-cli
   ```
2. **Login da CLI** (abre o navegador; vale 1 hora, renovável até 24 h com `oci session refresh --profile pacelab`):
   ```powershell
   & "$HOME\.oci-cli\Scripts\oci.exe" session authenticate --region sa-saopaulo-1 --tenancy-name <conta> --profile-name pacelab
   ```
3. **Chave SSH** (a privada nunca sai do PC; guarde uma cópia e a passphrase no gerenciador de senhas):
   ```powershell
   ssh-keygen -t ed25519 -f $HOME\.ssh\pacelab-oracle -C "pacelab-oracle"
   ```

## Criar
No Git Bash, na raiz do repositório:
```bash
infra/oracle/criar-servidor.sh "$(curl -s https://api.ipify.org)"
```
O script cria a rede, o firewall, a sub-rede e a máquina, e imprime o comando de SSH. Pode rodar de novo: reaproveita o que já existe.

Quando a Oracle está sem máquina A1 livre ("Out of host capacity", comum em São Paulo), deixe tentando enquanto o PC estiver ligado, alternando 2 OCPUs/12 GB e 1 OCPU/6 GB (a sessão da CLI renova sozinha até 24 h depois do login):
```bash
TENTATIVAS=60 INTERVALO=600 infra/oracle/criar-servidor.sh "$(curl -s https://api.ipify.org)"
``` Ele recusa rodar se já houver uma máquina `pacelab` ligada. O IP impresso não vai para o repositório: ponha em `data/checagens-locais.txt`.

## Primeiro acesso e Tailscale
1. Espere uns minutos (o cloud-init termina depois de a máquina ligar) e entre:
   ```bash
   ssh -i ~/.ssh/pacelab-oracle ubuntu@<ip-público>
   cloud-init status --wait   # deve terminar em "status: done"
   ```
2. Ligue o Tailscale na mesma tailnet do PC e do celular (mostra um link para aprovar no navegador):
   ```bash
   sudo tailscale up
   ```
3. Do PC, confira que entra pelo Tailscale: `ssh -i ~/.ssh/pacelab-oracle ubuntu@<nome-ou-ip-100.x-no-tailscale>`.

## Fechar o SSH para a internet
Com o acesso pelo Tailscale funcionando, o firewall fica sem nenhuma entrada (só a mensagem de ICMP que a rede precisa):
```bash
OCI=~/.oci-cli/Scripts/oci.exe; A="--profile pacelab --auth security_token"
T=$(grep -A10 '^\[pacelab\]' ~/.oci/config | grep -m1 '^tenancy=' | cut -d= -f2)
SL=$($OCI network security-list list $A -c "$T" --display-name pacelab-firewall --query 'data[0].id' --raw-output)
$OCI network security-list update $A --security-list-id "$SL" --force \
  --ingress-security-rules '[{"source":"0.0.0.0/0","protocol":"1","isStateless":false,"icmpOptions":{"type":3,"code":4}}]'
```
Para abrir de novo numa emergência (Tailscale fora do ar), rode o mesmo comando com a regra de SSH do seu IP, como no `criar-servidor.sh`.

## Manutenção
- Atualizações de segurança: automáticas, todo dia; reinício às 4h quando o pacote pedir.
- Ver o que foi atualizado: `less /var/log/unattended-upgrades/unattended-upgrades.log`.
- Atualizações maiores (versão do Docker, do Ubuntu): à mão, com backup antes.

## Riscos conhecidos
- **A Oracle pode recolher a máquina parada:** CPU, rede e memória abaixo de 20% por 7 dias. Decisão de 16/11/2026: ficar no Always Free e aceitar o risco; a defesa é o backup diário fora da máquina (etapa 6) e a máquina recriável por este guia. Se a Oracle avisar, reavaliar a conta Pay As You Go.
- **Falta de máquina A1 na região** ("Out of host capacity"): São Paulo tem um só domínio de disponibilidade. Em 16/11/2026, 9 tentativas em 1h30 falharam. Tentar com o rodízio acima; sem login por chave de API (decisão do usuário), cada dia de tentativas começa com o login da CLI.

## Nunca vai para o repositório
IP público da máquina, OCIDs, nome da conta da Oracle, nome da máquina no Tailscale e o arquivo `~/.oci/config`. O `data/checagens-locais.txt` bloqueia os que forem anotados lá.
