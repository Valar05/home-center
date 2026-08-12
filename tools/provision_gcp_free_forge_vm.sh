#!/bin/sh
set -eu
say(){ printf '\n[gcp-forge] %s\n' "$*"; }
ok(){ printf '[ok] %s\n' "$*"; }
fail(){ printf '[blocked] %s\n' "$*" >&2; exit 1; }
have(){ command -v "$1" >/dev/null 2>&1; }
STATE_DIR="$HOME/.home-center/cloud-forge"
mkdir -p "$STATE_DIR"
GCLOUD=''
run_gcloud(){
  if [ "$GCLOUD" = termux ]; then gcloud "$@"; else proot-distro login debian -- gcloud "$@"; fi
}
ensure_ipv6(){
  say "Proving the phone has IPv6 before creating an IPv6-only public forge"
  if ! curl -6 -fsS --connect-timeout 8 https://www.google.com/generate_204 >/dev/null 2>&1; then
    fail "This network has no working IPv6. Free-only GCP public access would require a paid IPv4, so no VM was created. Switch the phone to an IPv6-capable network and rerun."
  fi
  ok "Phone IPv6 path proven"
}
ensure_gcloud(){
  if have gcloud; then GCLOUD=termux; ok "Existing gcloud found"; return; fi
  have pkg || fail "Run this from Termux."
  if ! have proot-distro; then
    say "Installing Termux proot-distro"
    pkg install -y proot-distro
  fi
  if ! proot-distro login debian -- true >/dev/null 2>&1; then
    say "Installing Debian tool capsule for Google Cloud CLI"
    proot-distro install debian
  fi
  if ! proot-distro login debian -- sh -lc 'command -v gcloud >/dev/null 2>&1'; then
    say "Installing Google Cloud CLI inside Debian capsule"
    proot-distro login debian -- sh -lc 'set -eu; apt-get update; apt-get install -y ca-certificates curl gnupg; mkdir -p /usr/share/keyrings; curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor --yes -o /usr/share/keyrings/cloud.google.gpg; printf "%s\n" "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" > /etc/apt/sources.list.d/google-cloud-sdk.list; apt-get update; apt-get install -y google-cloud-cli'
  fi
  GCLOUD=proot
  ok "Google Cloud CLI available"
}
ensure_auth(){
  acct=$(run_gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null | head -n 1 || true)
  if [ -z "$acct" ]; then
    say "Google requires one account authorization gesture"
    run_gcloud auth login --no-launch-browser
    acct=$(run_gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null | head -n 1 || true)
  fi
  [ -n "$acct" ] || fail "Google account authorization did not complete. Rerun after login."
  ok "Authenticated as $acct"
}
choose_project(){
  project=$(run_gcloud config get-value project 2>/dev/null | tr -d '\r' || true)
  [ "$project" != '(unset)' ] || project=''
  if [ -z "$project" ]; then
    projects=$(run_gcloud projects list --filter='lifecycleState:ACTIVE' --format='value(projectId)' 2>/dev/null || true)
    count=$(printf '%s\n' "$projects" | sed '/^$/d' | wc -l | tr -d ' ')
    if [ "$count" = 1 ]; then project=$(printf '%s\n' "$projects" | sed -n '1p'); else
      printf '\nAvailable GCP projects:\n%s\n' "$projects"
      printf 'Project ID for Home Center forge: '
      IFS= read -r project || true
    fi
  fi
  [ -n "$project" ] || fail "A GCP project ID is required."
  run_gcloud config set project "$project" >/dev/null
  PROJECT_ID=$project
  ok "Project: $PROJECT_ID"
}
ensure_resources(){
  REGION=us-central1
  ZONE=us-central1-a
  NETWORK=home-center-forge-net
  SUBNET=home-center-forge-subnet
  INSTANCE=home-center-forge-01
  say "Enabling required Google APIs"
  run_gcloud services enable compute.googleapis.com storage.googleapis.com
  if ! run_gcloud compute networks describe "$NETWORK" >/dev/null 2>&1; then
    say "Creating dedicated custom VPC"
    run_gcloud compute networks create "$NETWORK" --subnet-mode=custom
  fi
  if ! run_gcloud compute networks subnets describe "$SUBNET" --region="$REGION" >/dev/null 2>&1; then
    say "Creating external-IPv6 dual-stack subnet"
    run_gcloud compute networks subnets create "$SUBNET" --network="$NETWORK" --range=10.42.0.0/24 --stack-type=IPV4_IPV6 --ipv6-access-type=EXTERNAL --region="$REGION"
  fi
  if ! run_gcloud compute firewall-rules describe home-center-forge-ipv6 >/dev/null 2>&1; then
    run_gcloud compute firewall-rules create home-center-forge-ipv6 --network="$NETWORK" --direction=INGRESS --action=ALLOW --rules=tcp:22,tcp:3000,tcp:2222 --source-ranges='::/0'
  fi
  if ! run_gcloud compute instances describe "$INSTANCE" --zone="$ZONE" >/dev/null 2>&1; then
    say "Creating Always Free-sized e2-micro with NO external IPv4"
    run_gcloud compute instances create "$INSTANCE" --zone="$ZONE" --machine-type=e2-micro --boot-disk-type=pd-standard --boot-disk-size=10GB --image-family=debian-12 --image-project=debian-cloud --network-interface="network=$NETWORK,subnet=$SUBNET,stack-type=IPV4_IPV6,ipv6-network-tier=PREMIUM,no-address"
  else
    ok "Existing forge VM preserved"
  fi
  HOST=$(run_gcloud compute instances describe "$INSTANCE" --zone="$ZONE" --format='value(networkInterfaces[0].ipv6AccessConfigs[0].externalIpv6)' | tr -d '\r')
  [ -n "$HOST" ] || fail "VM exists but no external IPv6 was discoverable. No paid IPv4 fallback was attempted."
  printf '%s\n' "FORGE_HOST=$HOST" "FORGE_USER=$(whoami)" "FORGE_PORT=22" "GCP_PROJECT=$PROJECT_ID" "GCP_ZONE=$ZONE" > "$STATE_DIR/gcp-provisioned.env"
  ok "Forge VM IPv6: $HOST"
  printf 'FORGE_HOST=%s\nFORGE_USER=%s\nFORGE_PORT=22\n' "$HOST" "$(whoami)"
}
main(){ ensure_ipv6; ensure_gcloud; ensure_auth; choose_project; ensure_resources; }
main "$@"
