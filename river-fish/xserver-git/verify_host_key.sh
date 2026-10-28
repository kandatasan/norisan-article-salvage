#!/usr/bin/env bash
# Pin the Xserver SSH host key to the ED25519 fingerprint shown in server settings.
set -euo pipefail
: "${XSERVER_SSH_HOST:?XSERVER_SSH_HOST must be set}"
expected='SHA256:PyIMaiPnrtflg2uTw6UMU6aPE8/qZcmDGsQA8T86veI'
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
scanned="$(mktemp)"
trap 'rm -f "$scanned"' EXIT
ssh-keyscan -T 15 -p 10022 -t ed25519 "$XSERVER_SSH_HOST" > "$scanned" 2>/dev/null
test -s "$scanned"
fingerprint="$(ssh-keygen -lf "$scanned" -E sha256 | awk '$4=="(ED25519)" {print $2}' | head -n1)"
if [[ "$fingerprint" != "$expected" ]]; then
  echo 'SSH host fingerprint mismatch; check official Xserver panel before proceeding.' >&2
  exit 1
fi
install -m 600 "$scanned" "$HOME/.ssh/known_hosts"
echo 'ED25519 SSH host key verified against Xserver panel fingerprint.'
