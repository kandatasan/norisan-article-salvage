#!/usr/bin/env bash
# Guarded deployment: only /ux-price-checker; fail closed and restore previous version on mismatch.
set -euo pipefail
: "${XSERVER_SSH_HOST:?}" "${XSERVER_SSH_USER:?}" "${GITHUB_RUN_ID:?}"
src="ops/lexus-ux-price-checker"
remote="$XSERVER_SSH_USER@$XSERVER_SSH_HOST"
key="$HOME/.ssh/xserver_deploy_key"
opts="-p 10022 -i $key -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$HOME/.ssh/known_hosts"
stage=".tsurikue-ux-price-release-$GITHUB_RUN_ID"
curl -fsSL --max-time 30 --retry 3 --retry-delay 3 "https://tsurikue.com/ux-price-checker-ci-preview/index.html?ux_rev=${GITHUB_RUN_ID}" -o /tmp/ux-price-preview.html
curl -fsSL --max-time 30 --retry 3 --retry-delay 3 "https://tsurikue.com/ux-price-checker-ci-preview/data/reference_price_bands.json?ux_rev=${GITHUB_RUN_ID}" -o /tmp/ux-price-preview.json
cmp /tmp/ux-price-preview.html "$src/index.html"
cmp /tmp/ux-price-preview.json "$src/data/reference_price_bands.json"
echo UX_PRICE_STAGING_PARITY=PASS
ssh $opts "$remote" bash -s -- "$stage" <<'REMOTE'
set -euo pipefail
stage="$1"; [[ "$stage" =~ ^\.tsurikue-ux-price-release-[0-9]+$ ]] || exit 20
root="$HOME/tsurikue.com/public_html"
test -d "$root" && test ! -L "$root" && test -f "$root/wp-config.php"
test ! -e "$HOME/$stage" && test ! -L "$HOME/$stage"
test ! -L "$root/ux-price-checker"
cd "$root"
wp eval 'if (get_page_by_path("ux-price-checker", OBJECT, array("post","page"))) throw new RuntimeException("WordPress path conflict");'
mkdir -p "$HOME/$stage/data"
REMOTE
rsync -az -e "ssh $opts" --include='/index.html' --include='/data/' --include='/data/reference_price_bands.json' --exclude='*' "$src/" "$remote:$stage/"
ssh $opts "$remote" bash -s -- "$stage" "$GITHUB_RUN_ID" <<'REMOTE'
set -euo pipefail
stage="$1"; run="$2"
[[ "$stage" =~ ^\.tsurikue-ux-price-release-[0-9]+$ ]] || exit 20
[[ "$run" =~ ^[0-9]+$ ]] || exit 21
root="$HOME/tsurikue.com/public_html"
dest="$root/ux-price-checker"
backup="$HOME/.tsurikue-ux-price-backup-$run"
candidate="$HOME/$stage"
test -d "$root" && test ! -L "$root" && test -f "$root/wp-config.php"
test -d "$candidate" && test ! -L "$candidate"
test -f "$candidate/index.html" && test -f "$candidate/data/reference_price_bands.json"
test ! -L "$dest" && test ! -e "$backup"
php -r '$d=json_decode(file_get_contents($argv[1]),true); if(!$d || ($d["publication_reviewed"]??false)!==true || ($d["research_preview_only"]??true)!==false || ($d["limited_sample_release"]??false)!==true || count($d["cohorts"]??[])<9)exit(1);' "$candidate/data/reference_price_bands.json"
grep -Fq 'id="general-price"' "$candidate/index.html"
grep -Fq 'id="cpo-price"' "$candidate/index.html"
# v0.17 grade-specific price integrity: never reuse all-grade pool for F SPORT/base.
grep -Fq "if(b.grade==='all'||b.grade!==grade) return false;" "$candidate/index.html"
! grep -Fq '全グレード' "$candidate/index.html"
php -r '$d=json_decode(file_get_contents($argv[1]),true);foreach($d["cohorts"] as $c){if(($c["grade"]??"")==="all")exit(9);}if(($d["archived_pooled_cohort_count"]??0)<17)exit(10);' "$candidate/data/reference_price_bands.json"
grep -Fq '中央値約' "$candidate/index.html"
php -r '$d=json_decode(file_get_contents($argv[1]),true);$has=function($m,$g,$y,$seg)use($d){foreach($d["cohorts"] as $c){if($c["model"]===$m&&$c["grade"]===$g&&$c["year"]===$y&&$c["market_segment"]===$seg&&($c["sample_size"]??0)>=5)return true;}return false;};if(!$has("250h","fs",2019,"general_market")||!$has("250h","fs",2021,"general_market")||!$has("300h","fs",2024,"lexus_cpo")||!$has("250h","c",2020,"general_market")||!$has("250h","c",2020,"lexus_cpo"))exit(1);' "$candidate/data/reference_price_bands.json"
# Compact user-approved UI; keep disclosure before the selector and remove old long explanation.
grep -Fq 'レクサスUX 中古相場チェックツール' "$candidate/index.html"
grep -Fq '※価格は参考程度です。' "$candidate/index.html"
! grep -Fq '価格について：</strong>' "$candidate/index.html"
# v0.15 three-selector UX: never deploy stale color UI or unsupported multi-year fallback logic.
! grep -Fq 'id="color"' "$candidate/index.html"
grep -Fq 'maxYear-minYear<=4' "$candidate/index.html"
! grep -Eiq 'px.a8.net|www15.a8.net' "$candidate/index.html"
printf '%s\n' 'ux-price-managed-v1' > "$candidate/.tsurikue-ux-price-managed"
cat > "$candidate/.htaccess" <<'HT'
<IfModule mod_headers.c>
Header always set X-Robots-Tag "noindex, nofollow"
Header always set Cache-Control "no-cache, max-age=0, must-revalidate"
</IfModule>
HT
if [[ -e "$dest" ]]; then
  test -d "$dest" && test -f "$dest/.tsurikue-ux-price-managed" || { echo 'Unmanaged existing target; stop'; exit 22; }
  mv "$dest" "$backup"
fi
if ! mv "$candidate" "$dest"; then
  test ! -d "$backup" || mv "$backup" "$dest"
  echo UX_PRICE_PRODUCTION_SWITCH_FAILED
  exit 23
fi
echo UX_PRICE_PRODUCTION_SWITCH=PASS
REMOTE
set +e
curl -fsSL --max-time 30 --retry 2 "https://tsurikue.com/ux-price-checker/index.html?ux_rev=${GITHUB_RUN_ID}" -o /tmp/ux-price-production.html &&
cmp -s /tmp/ux-price-production.html "$src/index.html" &&
curl -fsSL --max-time 30 --retry 2 "https://tsurikue.com/ux-price-checker/data/reference_price_bands.json?ux_rev=${GITHUB_RUN_ID}" -o /tmp/ux-price-production.json &&
cmp -s /tmp/ux-price-production.json "$src/data/reference_price_bands.json"
verified=$?
set -e
if [[ "$verified" -ne 0 ]]; then
  echo 'UX_PRICE_PRODUCTION_HTTPS=FAIL; attempting rollback'
  ssh $opts "$remote" bash -s -- "$GITHUB_RUN_ID" <<'REMOTE'
set -euo pipefail
run="$1"; [[ "$run" =~ ^[0-9]+$ ]] || exit 30
root="$HOME/tsurikue.com/public_html"
dest="$root/ux-price-checker"
backup="$HOME/.tsurikue-ux-price-backup-$run"
failed="$HOME/.tsurikue-ux-price-failed-$run"
test -d "$root" && test ! -L "$root" && test -f "$root/wp-config.php"
test -d "$dest" && test ! -L "$dest" && test -f "$dest/.tsurikue-ux-price-managed"
test ! -e "$failed" && test ! -L "$failed"
mv "$dest" "$failed"
if [[ -d "$backup" && ! -L "$backup" ]]; then mv "$backup" "$dest"; fi
echo UX_PRICE_PRODUCTION_ROLLBACK_ATTEMPTED=YES
REMOTE
  exit 31
fi
echo UX_PRICE_PRODUCTION_HTTPS=PASS
