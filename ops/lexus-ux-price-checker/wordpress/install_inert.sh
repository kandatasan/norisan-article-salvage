#!/usr/bin/env bash
# Safe, disabled-by-default UX price MU-plugin install; no WP post edits.
set -euo pipefail
test -n "$XSERVER_SSH_HOST" && test -n "$XSERVER_SSH_USER" && test -n "$GITHUB_RUN_ID"
key="$HOME/.ssh/xserver_deploy_key"
remote="$XSERVER_SSH_USER@$XSERVER_SSH_HOST"
source_file="ops/lexus-ux-price-checker/wordpress/tsurikue-ux-price-embed.php"
stage=".tsurikue-ux-embed-$GITHUB_RUN_ID.php"
test -f "$source_file"
scp -P 10022 -i "$key" -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$HOME/.ssh/known_hosts" "$source_file" "$remote:$stage"
ssh -p 10022 -i "$key" -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$HOME/.ssh/known_hosts" "$remote" bash -s -- "$stage" <<'REMOTE'
set -euo pipefail
name="$1"
[[ "$name" =~ ^\.tsurikue-ux-embed-[0-9]+\.php$ ]] || exit 12
root="$HOME/tsurikue.com/public_html"
candidate="$HOME/$name"
target="$root/wp-content/mu-plugins/tsurikue-ux-price-embed.php"
installed=0
finish() {
    code=$?
    if (( code != 0 && installed == 1 )); then
        rm -f "$target"
        echo "UX_INERT_PLUGIN_ROLLBACK_ATTEMPTED=yes"
    fi
    rm -f "$candidate"
    exit "$code"
}
trap finish EXIT
test -d "$root" && test ! -L "$root" && test -f "$root/wp-config.php"
test -d "$root/wp-content/mu-plugins" && test ! -L "$root/wp-content/mu-plugins"
test -f "$candidate" && test ! -L "$candidate"
php -l "$candidate" >/dev/null
grep -Fq "TSURIKUE_UX_PRICE_ENABLED" "$candidate"
cd "$root"
wp eval '
if (defined("TSURIKUE_UX_PRICE_ENABLED") && TSURIKUE_UX_PRICE_ENABLED === true) {
    throw new RuntimeException("UX plugin activation was not authorized");
}
foreach (array(2948=>"lexus-ux-used",3601=>"lexus-ux250h-used-vs-ux300h") as $id=>$slug) {
    $p=get_post($id);
    if (!$p || $p->post_name!==$slug || $p->post_status!=="publish" || $p->post_type!=="post")
        throw new RuntimeException("UX WordPress target drift: ".$id);
}
'
before="$(wp eval 'echo hash("sha256",get_post(2948)->post_content).":".hash("sha256",get_post(3601)->post_content);')"
test ! -L "$target"
if [[ -e "$target" ]]; then
    test -f "$target"
    cmp -s "$target" "$candidate" || { echo "Existing UX embed differs; refusing overwrite"; exit 15; }
    echo "UX_INERT_PLUGIN_ALREADY_INSTALLED=PASS"
else
    install -m 0644 "$candidate" "$target"
    installed=1
fi
php -l "$target" >/dev/null
wp eval '
if (!has_filter("the_content")) throw new RuntimeException("Content filters unavailable");
if (defined("TSURIKUE_UX_PRICE_ENABLED") && TSURIKUE_UX_PRICE_ENABLED === true)
    throw new RuntimeException("Unexpected UX plugin activation");
'
after="$(wp eval 'echo hash("sha256",get_post(2948)->post_content).":".hash("sha256",get_post(3601)->post_content);')"
[[ "$before" == "$after" ]] || { echo "UX posts changed unexpectedly"; exit 16; }
echo "UX_INERT_PLUGIN_INSTALLED=PASS"
echo "UX_WORDPRESS_CONTENT_UNCHANGED=PASS"
REMOTE
