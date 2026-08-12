#!/bin/sh
set -eu
say(){ printf '\n[oci-forge] %s\n' "$*"; }
ok(){ printf '[ok] %s\n' "$*"; }
fail(){ printf '[blocked] %s\n' "$*" >&2; exit 1; }
have(){ command -v "$1" >/dev/null 2>&1; }
STATE_DIR="$HOME/.home-center/cloud-forge"
mkdir -p "$STATE_DIR"
run_oci(){ proot-distro login debian -- oci "$@"; }
ensure_cli(){
  have proot-distro || { say "Installing Termux Debian capsule"; pkg install -y proot-distro; }
  proot-distro login debian -- true >/dev/null 2>&1 || proot-distro install debian
  if ! proot-distro login debian -- sh -lc 'command -v oci >/dev/null 2>&1'; then
    say "Installing OCI CLI in Debian capsule"
    proot-distro login debian -- sh -lc 'set -eu; apt-get update; apt-get install -y python3 python3-venv ca-certificates curl; python3 -m venv /opt/oci; /opt/oci/bin/pip install -U pip oci-cli; ln -sf /opt/oci/bin/oci /usr/local/bin/oci'
  fi
  ok "OCI CLI available"
}
ensure_auth(){
  if run_oci iam region list >/dev/null 2>&1; then ok "OCI authentication already valid"; return; fi
  say "Oracle account authentication is required once"
  printf '%s\n' "Complete Oracle sign-in when the OCI bootstrap opens it. It creates and uploads the API key automatically."
  proot-distro login debian -- oci setup bootstrap
  run_oci iam region list >/dev/null 2>&1 || fail "OCI authentication did not complete. Rerun after finishing Oracle login."
  ok "OCI authentication proven"
}
ensure_network(){
  TENANCY=$(run_oci iam availability-domain list --query 'data[0]."compartment-id"' --raw-output)
  AD=$(run_oci iam availability-domain list --query 'data[0].name' --raw-output)
  [ -n "$TENANCY" ] && [ "$TENANCY" != null ] || fail "Could not determine tenancy compartment."
  VCN=$(run_oci network vcn list --compartment-id "$TENANCY" --display-name home-center-forge-vcn --query 'data[0].id' --raw-output 2>/dev/null || true)
  if [ -z "$VCN" ] || [ "$VCN" = null ]; then
    say "Creating Always Free VCN"
    VCN=$(run_oci network vcn create --compartment-id "$TENANCY" --display-name home-center-forge-vcn --cidr-block 10.42.0.0/16 --dns-label hcforge --wait-for-state AVAILABLE --query 'data.id' --raw-output)
  fi
  IGW=$(run_oci network internet-gateway list --compartment-id "$TENANCY" --vcn-id "$VCN" --display-name home-center-forge-igw --query 'data[0].id' --raw-output 2>/dev/null || true)
  if [ -z "$IGW" ] || [ "$IGW" = null ]; then
    IGW=$(run_oci network internet-gateway create --compartment-id "$TENANCY" --vcn-id "$VCN" --display-name home-center-forge-igw --is-enabled true --wait-for-state AVAILABLE --query 'data.id' --raw-output)
  fi
  RT=$(run_oci network route-table list --compartment-id "$TENANCY" --vcn-id "$VCN" --query 'data[0].id' --raw-output)
  run_oci network route-table update --rt-id "$RT" --route-rules "[{\"cidrBlock\":\"0.0.0.0/0\",\"networkEntityId\":\"$IGW\"}]" --force >/dev/null
  SL=$(run_oci network security-list list --compartment-id "$TENANCY" --vcn-id "$VCN" --query 'data[0].id' --raw-output)
  run_oci network security-list update --security-list-id "$SL" --ingress-security-rules '[{"protocol":"6","source":"0.0.0.0/0","tcpOptions":{"destinationPortRange":{"min":22,"max":22}}},{"protocol":"6","source":"0.0.0.0/0","tcpOptions":{"destinationPortRange":{"min":3000,"max":3000}}},{"protocol":"6","source":"0.0.0.0/0","tcpOptions":{"destinationPortRange":{"min":2222,"max":2222}}}]' --force >/dev/null
  SUBNET=$(run_oci network subnet list --compartment-id "$TENANCY" --vcn-id "$VCN" --display-name home-center-forge-subnet --query 'data[0].id' --raw-output 2>/dev/null || true)
  if [ -z "$SUBNET" ] || [ "$SUBNET" = null ]; then
    SUBNET=$(run_oci network subnet create --compartment-id "$TENANCY" --vcn-id "$VCN" --display-name home-center-forge-subnet --cidr-block 10.42.1.0/24 --dns-label forge --route-table-id "$RT" --security-list-ids "[\"$SL\"]" --wait-for-state AVAILABLE --query 'data.id' --raw-output)
  fi
}
ensure_instance(){
  INSTANCE=$(run_oci compute instance list --compartment-id "$TENANCY" --display-name home-center-forge-01 --lifecycle-state RUNNING --query 'data[0].id' --raw-output 2>/dev/null || true)
  if [ -z "$INSTANCE" ] || [ "$INSTANCE" = null ]; then
    say "Selecting Always Free compute shape"
    SHAPE=VM.Standard.E2.1.Micro
    IMAGE=$(run_oci compute image list --compartment-id "$TENANCY" --operating-system Ubuntu --shape "$SHAPE" --sort-by TIMECREATED --sort-order DESC --query 'data[0].id' --raw-output 2>/dev/null || true)
    if [ -z "$IMAGE" ] || [ "$IMAGE" = null ]; then
      SHAPE=VM.Standard.A1.Flex
      IMAGE=$(run_oci compute image list --compartment-id "$TENANCY" --operating-system Ubuntu --shape "$SHAPE" --sort-by TIMECREATED --sort-order DESC --query 'data[0].id' --raw-output)
    fi
    [ -n "$IMAGE" ] && [ "$IMAGE" != null ] || fail "No compatible Ubuntu Always Free image found."
    PUBKEY=$(cat "$HOME/.ssh/id_ed25519.pub")
    META=$(python - <<PY
import json
print(json.dumps({'ssh_authorized_keys': '''$PUBKEY'''}))
PY
)
    say "Launching Always Free Ubuntu VM with public IPv4"
    if [ "$SHAPE" = VM.Standard.A1.Flex ]; then
      INSTANCE=$(run_oci compute instance launch --availability-domain "$AD" --compartment-id "$TENANCY" --display-name home-center-forge-01 --shape "$SHAPE" --shape-config '{"ocpus":1,"memoryInGBs":6}' --image-id "$IMAGE" --subnet-id "$SUBNET" --assign-public-ip true --metadata "$META" --wait-for-state RUNNING --query 'data.id' --raw-output)
    else
      INSTANCE=$(run_oci compute instance launch --availability-domain "$AD" --compartment-id "$TENANCY" --display-name home-center-forge-01 --shape "$SHAPE" --image-id "$IMAGE" --subnet-id "$SUBNET" --assign-public-ip true --metadata "$META" --wait-for-state RUNNING --query 'data.id' --raw-output)
    fi
  else
    ok "Existing OCI forge VM preserved"
  fi
  VNIC=$(run_oci compute vnic-attachment list --compartment-id "$TENANCY" --instance-id "$INSTANCE" --query 'data[0]."vnic-id"' --raw-output)
  HOST=$(run_oci network vnic get --vnic-id "$VNIC" --query 'data."public-ip"' --raw-output)
  [ -n "$HOST" ] && [ "$HOST" != null ] || fail "VM is running but has no public IPv4."
  printf '%s\n' "FORGE_HOST=$HOST" "FORGE_USER=ubuntu" "FORGE_PORT=22" > "$STATE_DIR/oci-provisioned.env"
  cat "$STATE_DIR/oci-provisioned.env"
  ok "OCI Always Free forge VM IPv4: $HOST"
}
main(){ ensure_cli; ensure_auth; ensure_network; ensure_instance; }
main "$@"
