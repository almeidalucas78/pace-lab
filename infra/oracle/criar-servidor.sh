#!/usr/bin/env bash
# Cria a rede e a máquina do Pace Lab na Oracle pela OCI CLI (fase 9, etapa 1; guia em docs/servidor.md).
#
# Uso (Git Bash, depois de `oci session authenticate --profile-name pacelab`):
#   infra/oracle/criar-servidor.sh <seu-ip-de-casa> [chave-publica]
#
# - <seu-ip-de-casa>: único IP que pode abrir SSH até o Tailscale estar ligado (veja com `curl -s https://api.ipify.org`).
# - [chave-publica]: padrão ~/.ssh/pacelab-oracle.pub.
# - TENTATIVAS (padrão 1) e INTERVALO (segundos, padrão 600): quando a Oracle responde "Out of host capacity",
#   espera e tenta de novo, renovando a sessão da CLI a cada volta (a sessão renova até 24 h após o login).
# - TAMANHOS (padrão "2:12 1:6"): OCPUs:GB de memória pedidos em rodízio, uma opção por tentativa
#   (o menor às vezes sai quando o maior está em falta).
# Pode rodar de novo: reaproveita a rede, o firewall e a sub-rede que já existirem com os mesmos nomes.
# Nada de IP, OCID ou chave é gravado no repositório; o script só imprime no terminal.
set -euo pipefail

IP_CASA="${1:?informe o seu IP de casa (curl -s https://api.ipify.org)}"
CHAVE_PUB="${2:-$HOME/.ssh/pacelab-oracle.pub}"
PERFIL="${OCI_PERFIL:-pacelab}"
OCI="${OCI_EXE:-$HOME/.oci-cli/Scripts/oci.exe}"
TENTATIVAS="${TENTATIVAS:-1}"
INTERVALO="${INTERVALO:-600}"
AQUI="$(cd "$(dirname "$0")" && pwd)"

# Formas e tamanhos (Always Free: até 2 OCPUs e 12 GB de A1; 200 GB de disco no total).
FORMA="VM.Standard.A1.Flex"
read -r -a TAMANHOS <<<"${TAMANHOS:-2:12 1:6}"
DISCO_GB=50
IMAGEM_PREFIXO="Canonical-Ubuntu-26.04-aarch64-"

[[ "$IP_CASA" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "IP inválido: $IP_CASA" >&2; exit 1; }
[[ -f "$CHAVE_PUB" ]] || { echo "Chave pública não encontrada: $CHAVE_PUB" >&2; exit 1; }

# A OCI CLI do Windows precisa de caminhos do Windows.
caminho() { if command -v cygpath >/dev/null; then cygpath -m "$1"; else echo "$1"; fi; }
oci_() { "$OCI" --profile "$PERFIL" --auth security_token "$@"; }
# Primeiro id da lista (vazio se não houver).
primeiro() { local v; v="$(oci_ "$@" --query 'data[0].id' --raw-output 2>/dev/null || true)"; [[ "$v" == ocid1.* ]] && echo "$v" || true; }

TENANCY="$(grep -A10 "^\[$PERFIL\]" "$HOME/.oci/config" | grep -m1 '^tenancy=' | cut -d= -f2)"
[[ -n "$TENANCY" ]] || { echo "Perfil $PERFIL sem tenancy em ~/.oci/config" >&2; exit 1; }

if [[ -n "$(primeiro compute instance list -c "$TENANCY" --display-name pacelab --lifecycle-state RUNNING)" ]]; then
  echo "Já existe uma máquina 'pacelab' ligada; nada a fazer." >&2; exit 1
fi

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

echo "1/6 Rede pacelab-vcn"
VCN="$(primeiro network vcn list -c "$TENANCY" --display-name pacelab-vcn --lifecycle-state AVAILABLE)"
[[ -n "$VCN" ]] || VCN="$(oci_ network vcn create -c "$TENANCY" --cidr-blocks '["10.0.0.0/16"]' --display-name pacelab-vcn \
  --dns-label pacelab --wait-for-state AVAILABLE --query 'data.id' --raw-output)"

echo "2/6 Saída para a internet"
IGW="$(primeiro network internet-gateway list -c "$TENANCY" --vcn-id "$VCN" --display-name pacelab-igw)"
[[ -n "$IGW" ]] || IGW="$(oci_ network internet-gateway create -c "$TENANCY" --vcn-id "$VCN" --is-enabled true \
  --display-name pacelab-igw --wait-for-state AVAILABLE --query 'data.id' --raw-output)"
RT="$(oci_ network vcn get --vcn-id "$VCN" --query 'data."default-route-table-id"' --raw-output)"
oci_ network route-table update --rt-id "$RT" --force --wait-for-state AVAILABLE \
  --route-rules "[{\"destination\":\"0.0.0.0/0\",\"destinationType\":\"CIDR_BLOCK\",\"networkEntityId\":\"$IGW\"}]" >/dev/null

echo "3/6 Regras de firewall (entrada: só SSH do seu IP; o resto fechado)"
cat > "$TMP/saida.json" <<'JSON'
[{"destination":"0.0.0.0/0","protocol":"all","isStateless":false}]
JSON
cat > "$TMP/entrada.json" <<JSON
[
  {"source":"$IP_CASA/32","protocol":"6","isStateless":false,"tcpOptions":{"destinationPortRange":{"min":22,"max":22}}},
  {"source":"0.0.0.0/0","protocol":"1","isStateless":false,"icmpOptions":{"type":3,"code":4}}
]
JSON
SL="$(primeiro network security-list list -c "$TENANCY" --vcn-id "$VCN" --display-name pacelab-firewall)"
if [[ -n "$SL" ]]; then
  oci_ network security-list update --security-list-id "$SL" --force --wait-for-state AVAILABLE \
    --egress-security-rules "file://$(caminho "$TMP/saida.json")" \
    --ingress-security-rules "file://$(caminho "$TMP/entrada.json")" >/dev/null
else
  SL="$(oci_ network security-list create -c "$TENANCY" --vcn-id "$VCN" --display-name pacelab-firewall \
    --egress-security-rules "file://$(caminho "$TMP/saida.json")" \
    --ingress-security-rules "file://$(caminho "$TMP/entrada.json")" \
    --wait-for-state AVAILABLE --query 'data.id' --raw-output)"
fi

echo "4/6 Sub-rede pública"
SUBNET="$(primeiro network subnet list -c "$TENANCY" --vcn-id "$VCN" --display-name pacelab-subnet)"
[[ -n "$SUBNET" ]] || SUBNET="$(oci_ network subnet create -c "$TENANCY" --vcn-id "$VCN" --cidr-block 10.0.0.0/24 \
  --display-name pacelab-subnet --dns-label publica --route-table-id "$RT" \
  --security-list-ids "[\"$SL\"]" --prohibit-public-ip-on-vnic false \
  --wait-for-state AVAILABLE --query 'data.id' --raw-output)"

echo "5/6 Imagem do Ubuntu e domínio de disponibilidade"
IMAGEM="$(oci_ compute image list -c "$TENANCY" --operating-system "Canonical Ubuntu" --shape "$FORMA" \
  --sort-by TIMECREATED --sort-order DESC --all \
  --query "data[?starts_with(\"display-name\", '$IMAGEM_PREFIXO')] | [0].id" --raw-output)"
[[ "$IMAGEM" == ocid1.* ]] || { echo "Imagem $IMAGEM_PREFIXO* não encontrada" >&2; exit 1; }
AD="$(oci_ iam availability-domain list -c "$TENANCY" --query 'data[0].name' --raw-output)"

echo "6/6 Máquina pacelab ($FORMA, disco de $DISCO_GB GB)"
INST=""
for ((t = 1; t <= TENTATIVAS; t++)); do
  TAM="${TAMANHOS[$(((t - 1) % ${#TAMANHOS[@]}))]}"
  OCPUS="${TAM%%:*}"; MEMORIA_GB="${TAM##*:}"
  echo "  tentativa $t de $TENTATIVAS ($(date '+%d/%m %H:%M')): $OCPUS OCPUs, $MEMORIA_GB GB"
  if SAIDA="$(oci_ compute instance launch -c "$TENANCY" --availability-domain "$AD" --display-name pacelab \
      --shape "$FORMA" --shape-config "{\"ocpus\":$OCPUS,\"memoryInGBs\":$MEMORIA_GB}" \
      --image-id "$IMAGEM" --subnet-id "$SUBNET" --assign-public-ip true --hostname-label pacelab \
      --boot-volume-size-in-gbs "$DISCO_GB" \
      --ssh-authorized-keys-file "$(caminho "$CHAVE_PUB")" \
      --user-data-file "$(caminho "$AQUI/cloud-init.yaml")" \
      --wait-for-state RUNNING --query 'data.id' --raw-output 2>&1)"; then
    INST="$(grep -m1 -o 'ocid1\.instance[^" ]*' <<<"$SAIDA")"
    break
  fi
  if grep -q "Out of host capacity" <<<"$SAIDA"; then
    echo "  sem máquina livre na região (Out of host capacity)"
  else
    echo "$SAIDA" >&2; exit 1
  fi
  if (( t < TENTATIVAS )); then
    sleep "$INTERVALO"
    "$OCI" session refresh --profile "$PERFIL" >/dev/null 2>&1 || { echo "Sessão da CLI expirou; faça o login de novo e rode outra vez." >&2; exit 2; }
  fi
done
[[ -n "$INST" ]] || { echo "Sem máquina depois de $TENTATIVAS tentativas; rode de novo mais tarde." >&2; exit 3; }

IP="$(oci_ compute instance list-vnics --instance-id "$INST" --query 'data[0]."public-ip"' --raw-output)"
echo
echo "Pronto. A máquina está ligada; o primeiro boot (cloud-init) ainda leva alguns minutos."
echo "Entrar:  ssh -i ~/.ssh/pacelab-oracle ubuntu@$IP"
echo "Não grave este IP no repositório (ponha em data/checagens-locais.txt)."
