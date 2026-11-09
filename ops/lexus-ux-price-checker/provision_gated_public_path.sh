#!/usr/bin/env bash
# Provision a new gated UX static folder only; never publish unreviewed prices or edit WP.
set -euo pipefail
test -n "$XSERVER_SSH_HOST" && test -n "$XSERVER_SSH_USER" && test -n "$GITHUB_RUN_ID"
src="ops/lexus-ux-price-checker"
test -f "$src/index.html" && test -f "$src/data/reference_price_bands.json"
python3 - "$src/data/reference_price_bands.json" <<'PY'
import json,sys
a=json.load(open(sys.argv[1]))
assert a['publication_reviewed'] is False
assert a['research_preview_only'] is True
assert a['price_basis']=='total'
PY
remote="$XSERVER_SSH_USER@$XSERVER_SSH_HOST"
key="$HOME/.ssh/xserver_deploy_key"
opts="-p 10022 -i $key -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$HOME/.ssh/known_hosts"
temp=".tsurikue-ux-gated-$GITHUB_RUN_ID"
ssh $opts "$remote" bash -s -- "$temp" <<'REMOTE'
set -euo pipefail
name="$1"
[[ "$name" =~ ^\.tsurikue-ux-gated-[0-9]+$ ]] || exit 20
root="$HOME/tsurikue.com/public_html"
test -d "$root" && test ! -L "$root" && test -f "$root/wp-config.php"
test ! -e "$HOME/$name" && test ! -L "$HOME/$name"
mkdir -p "$HOME/$name/data"
REMOTE
rsync -az -e "ssh $opts" --include='/index.html' --include='/data/' --include='/data/reference_price_bands.json' --exclude='*' "$src/" "$remote:$temp/"
ssh $opts "$remote" bash -s -- "$temp" "$GITHUB_RUN_ID" <<'REMOTE'
set -euo pipefail
name="$1"; run="$2"
[[ "$name" =~ ^\.tsurikue-ux-gated-[0-9]+$ ]] || exit 21
[[ "$run" =~ ^[0-9]+$ ]] || exit 22
root="$HOME/tsurikue.com/public_html"
candidate="$HOME/$name"
target="$root/ux-price-checker"
marker=".tsurikue-ux-gated-managed"
test -d "$root" && test ! -L "$root" && test -f "$root/wp-config.php"
test ! -L "$target" && test ! -L "$candidate"
test -f "$candidate/index.html" && test -f "$candidate/data/reference_price_bands.json"
php -r '$a=json_decode(file_get_contents($argv[1]),true); if(!$a || $a["publication_reviewed"]!==false || $a["research_preview_only"]!==true)exit(1);' "$candidate/data/reference_price_bands.json"
printf '%s\n' "$run" > "$candidate/$marker"
cat > "$candidate/.htaccess" <<'HT'
<IfModule mod_headers.c>
Header always set X-Robots-Tag "noindex, nofollow"
</IfModule>
HT
if [[ -e "$target" ]]; then
  test -d "$target" && test -f "$target/$marker" || { echo "Existing target is not ours; refusing"; exit 23; }
  cmp -s "$target/index.html" "$candidate/index.html" || { echo "Existing target differs; refusing"; exit 24; }
  cmp -s "$target/data/reference_price_bands.json" "$candidate/data/reference_price_bands.json" || { echo "Existing JSON differs; refusing"; exit 25; }
  rm -rf "$candidate"
  echo "UX_GATED_PATH_EXISTING_MATCH=PASS"
else
  mv "$candidate" "$target"
  echo "UX_GATED_PATH_PROVISIONED=PASS"
fi
REMOTE
url="https://tsurikue.com/ux-price-checker"
curl -fsSL --retry 2 --max-time 25 "$url/index.html" -o /tmp/ux-gated-index.html
cmp -s /tmp/ux-gated-index.html "$src/index.html" || { echo "Gated HTML HTTPS mismatch"; exit 31; }
curl -fsSL --retry 2 --max-time 25 "$url/data/reference_price_bands.json" -o /tmp/ux-gated-price.json
cmp -s /tmp/ux-gated-price.json "$src/data/reference_price_bands.json" || { echo "Gated JSON HTTPS mismatch"; exit 32; }
echo "UX_GATED_PUBLIC_PATH_HTTPS=PASS"
echo "UX_PRICES_PUBLICATION_GATE=OFF"
