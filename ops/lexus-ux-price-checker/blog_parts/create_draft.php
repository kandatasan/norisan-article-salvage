<?php
/**
 * Safely create one draft SWELL blog part for Lexus UX price checking.
 * No posts, advertisements, existing blog parts, or published content are modified.
 */
if (!defined('ABSPATH')) { exit(10); }
if (!post_type_exists('blog_parts') || !shortcode_exists('blog_parts')) {
    throw new RuntimeException('SWELL blog_parts is not registered');
}
$title = 'レクサスUX中古車相場チェック（一般中古車・CPO）';
$slug = 'lexus-ux-price-checker-tool';
$content = "<!-- wp:html -->\n"
    . '<iframe title="レクサスUXの中古車参考価格｜一般中古車とCPO" src="https://tsurikue.com/ux-price-checker/?model=250h&amp;grade=all&amp;year=2021" '
    . 'loading="lazy" referrerpolicy="strict-origin-when-cross-origin" width="100%" height="620" '
    . 'style="display:block;width:100%;max-width:100%;height:620px;border:0;border-radius:12px;" '
    . 'aria-label="レクサスUXの中古車価格比較"></iframe>'
    . "\n<!-- /wp:html -->";
$all = get_posts(array(
    'post_type' => 'blog_parts',
    'post_status' => array('publish','draft','pending','private','future','trash'),
    'posts_per_page' => -1,
    'fields' => 'ids',
));
$matches = array();
foreach ($all as $post_id) {
    $p = get_post((int)$post_id);
    if (!$p) continue;
    if ($p->post_name === $slug || $p->post_title === $title || strpos((string)$p->post_content, 'ux-price-checker/?') !== false) {
        $matches[] = $p;
    }
}
if (count($matches) > 1) throw new RuntimeException('Ambiguous UX blog parts; refusing duplicate');
if (count($matches) === 1) {
    $existing = $matches[0];
    if ($existing->post_name !== $slug || $existing->post_title !== $title || $existing->post_content !== $content || $existing->post_status === 'trash') {
        throw new RuntimeException('Existing blog part differs: manual review required; id='.(int)$existing->ID);
    }
    echo 'UX_SWELL_PART_STATUS='.$existing->post_status.PHP_EOL;
    echo 'UX_SWELL_PART_ID='.(int)$existing->ID.PHP_EOL;
    echo 'UX_SWELL_PART_SHORTCODE=[blog_parts id="'.(int)$existing->ID.'"]'.PHP_EOL;
    echo 'UX_SWELL_PART_ALREADY_EXISTS=YES'.PHP_EOL;
    return;
}
$admins = get_users(array('role'=>'administrator','fields'=>'ID','number'=>1,'orderby'=>'ID','order'=>'ASC'));
if (!is_array($admins) || count($admins) !== 1) throw new RuntimeException('Cannot resolve a WordPress administrator author');
$id = wp_insert_post(array(
    'post_type' => 'blog_parts',
    'post_status' => 'draft',
    'post_title' => $title,
    'post_name' => $slug,
    'post_content' => $content,
    'post_author' => (int)$admins[0],
    'comment_status' => 'closed',
    'ping_status' => 'closed',
), true);
if (is_wp_error($id)) throw new RuntimeException('Draft creation error: '.$id->get_error_code());
$created = get_post((int)$id);
if (!$created || $created->post_type !== 'blog_parts' || $created->post_status !== 'draft'
 || $created->post_title !== $title || $created->post_name !== $slug || $created->post_content !== $content) {
    wp_delete_post((int)$id, true);
    throw new RuntimeException('Draft mismatch; only newly-created draft rolled back');
}
echo 'UX_SWELL_PART_STATUS=draft'.PHP_EOL;
echo 'UX_SWELL_PART_ID='.(int)$id.PHP_EOL;
echo 'UX_SWELL_PART_SHORTCODE=[blog_parts id="'.(int)$id.'"]'.PHP_EOL;
echo 'UX_SWELL_PART_CREATED=YES'.PHP_EOL;
