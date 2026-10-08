#!/usr/bin/env bash
# Deploy the N-ATLAS-Kit gateway to Modal and connect Lafiya to it.
#
# Run from Git Bash in the Lafiya project folder:
#     bash scripts/deploy_natlas_gateway.sh
#
# Prerequisites (one-off, done by you):
#   - Accepted terms on the 5 NCAIR1 Hugging Face repos and created a READ token
#   - Modal account with a payment method (needed for GPUs, even on free credit)
#   - python -m modal setup   (browser login)
#
# Secrets never leave your machine except to Modal: the HF token is read silently,
# the gateway key is generated locally and written only to Modal and Lafiya's .env.
set -euo pipefail

# Windows consoles default to cp1252, which cannot print the progress bars in Modal's build
# logs (e.g. "█") and makes the Modal CLI crash mid-deploy. Force UTF-8 output.
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8

LAFIYA_DIR="$(cd "$(dirname "$0")/.." && pwd)"
KIT_DIR="${KIT_DIR:-$LAFIYA_DIR/../N-ATLAS-Kit}"
MODAL="python -m modal"
ENV_FILE="$LAFIYA_DIR/.env"

step() { printf '\n==> %s\n' "$*"; }

secret_exists() {  # JSON output does not depend on terminal width/formatting
  $MODAL secret list --json 2>/dev/null | grep -q "\"$1\""
}

set_env() {  # set_env KEY VALUE  -> create or replace KEY in Lafiya's .env
  touch "$ENV_FILE"
  grep -v "^$1=" "$ENV_FILE" > "$ENV_FILE.tmp" || true
  printf '%s=%s\n' "$1" "$2" >> "$ENV_FILE.tmp"
  mv "$ENV_FILE.tmp" "$ENV_FILE"
}

[ -f "$KIT_DIR/serve/modal_app.py" ] || {
  step "Cloning N-ATLAS-Kit into $KIT_DIR"
  git clone --depth 1 https://github.com/Kambah123/N-ATLAS-Kit "$KIT_DIR"
}

step "Checking Modal login"
if ! $MODAL app list >/dev/null 2>&1; then  # needs a valid token; 'profile current' does not
  echo "Not logged in. Run:  python -m modal setup   then re-run this script."
  exit 1
fi
echo "Logged in (profile: $($MODAL profile current))"

step "Hugging Face token -> Modal secret 'natlas-hf'"
CREATE_HF=1
if secret_exists natlas-hf; then
  read -r -p "Secret natlas-hf already exists. Replace it with a new token? [y/N] " ANSWER
  [[ "$ANSWER" =~ ^[Yy] ]] || CREATE_HF=0
fi
if [ "$CREATE_HF" = 1 ]; then
  while true; do
    read -r -s -p "Paste your Hugging Face READ token (input hidden): " HF_TOKEN; echo
    # Pasting can bring invisible characters along; HF tokens are only letters, digits and "_".
    HF_TOKEN="$(printf '%s' "$HF_TOKEN" | LC_ALL=C tr -cd 'A-Za-z0-9_')"
    if [[ "$HF_TOKEN" != hf_* ]]; then
      echo "That doesn't look like a Hugging Face token (it should start with hf_). Try again."
      continue
    fi
    WHO="$(curl -s -H "Authorization: Bearer $HF_TOKEN" https://huggingface.co/api/whoami-v2 || true)"
    if printf '%s' "$WHO" | grep -q '"name"'; then
      echo "Token OK for Hugging Face user: $(printf '%s' "$WHO" | sed -n 's/^{"type":"user","id":"[^"]*","name":"\([^"]*\)".*/\1/p')"
      break
    fi
    echo "Hugging Face rejected that token (invalid or incomplete). Copy it again from"
    echo "https://huggingface.co/settings/tokens and paste with right-click / Shift+Insert."
  done
  $MODAL secret create --force natlas-hf HF_TOKEN="$HF_TOKEN" >/dev/null  # --force overwrites an old one
  unset HF_TOKEN WHO
  echo "Created."
fi

step "Gateway API key -> Modal secret 'natlas-api' and Lafiya .env"
if secret_exists natlas-api; then
  if grep -q '^NATLAS_API_KEY=.\+' "$ENV_FILE" 2>/dev/null; then
    echo "Secret natlas-api exists and Lafiya .env already has NATLAS_API_KEY - keeping both."
  else
    echo "Secret natlas-api exists but Lafiya's .env has no key. Delete 'natlas-api' in the Modal"
    echo "dashboard and re-run, or add NATLAS_API_KEY=<one of its NATLAS_API_KEYS> to .env yourself."
    exit 1
  fi
else
  API_KEY="$(openssl rand -hex 32)"
  $MODAL secret create natlas-api NATLAS_API_KEYS="$API_KEY" >/dev/null
  set_env NATLAS_API_KEY "$API_KEY"
  unset API_KEY
  echo "Created and saved to $ENV_FILE"
fi

cd "$KIT_DIR"

step "Pre-flight: HF token + model terms (no GPU)"
$MODAL run serve/modal_preflight.py --skip-gpu

step "Pre-flight: GPU access (bills a few cents)"
$MODAL run serve/modal_preflight.py

step "Deploying the gateway (first start downloads ~15 GB; this can take a while)"
DEPLOY_LOG="$(mktemp)"
$MODAL deploy serve/modal_app.py | tee "$DEPLOY_LOG"
URL="$(grep -oE 'https://[A-Za-z0-9._-]+natlas-serve-natlasservice-serve\.modal\.run' "$DEPLOY_LOG" | head -1 || true)"
rm -f "$DEPLOY_LOG"
if [ -z "$URL" ]; then
  # Newer Modal CLIs only print the dashboard link; web endpoints follow a fixed pattern.
  WORKSPACE="$($MODAL profile current 2>/dev/null | tr -d '[:space:]')"
  [ -n "$WORKSPACE" ] && URL="https://${WORKSPACE}--natlas-serve-natlasservice-serve.modal.run"
fi
[ -n "$URL" ] || { echo "Could not work out the gateway URL - copy it into .env as NATLAS_BASE_URL."; exit 1; }

set_env NATLAS_BASE_URL "$URL"
set_env NATLAS_MODEL "NCAIR1/N-ATLaS"
set_env NATLAS_TIMEOUT "60"

step "Done. Gateway: $URL"
echo "Warm it up and test it (the first cold start can take several minutes):"
echo "    cd \"$LAFIYA_DIR\" && python manage.py natlas_check"
