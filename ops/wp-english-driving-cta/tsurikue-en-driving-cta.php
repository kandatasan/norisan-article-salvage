<?php
/**
 * Plugin Name: Tsurikue English rental-car licence check
 * Description: Display Japan driving-licence requirements next to existing DiscoverCars links in English Travel articles.
 * Version: 1.0.0
 *
 * Scope: front-end rendering only. No post, affiliate URL, or permalink writes.
 */
if (!defined('ABSPATH')) {
    exit;
}

function tsurikue_en_driving_note_html() {
    return <<<'HTML'
<aside class="tsurikue-en-driving-note" data-tsurikue-en-driving="v1" role="note" style="border:1px solid #d6e1e6;border-radius:12px;background:#f7f9fa;padding:16px 18px;margin:22px 0 12px;color:#263b42;">
<p style="font-size:1.04em;font-weight:700;margin:0 0 8px;">Driving in Japan? Check your licence before booking.</p>
<p style="font-size:.95em;line-height:1.75;margin:0 0 9px;">Requirements depend on where your licence was issued. Japan accepts a valid Japanese driving licence, or a <strong>1949 Geneva Convention paper International Driving Permit</strong> (carry your valid home-country licence too). For licences issued in <strong>Switzerland, Germany, France, Belgium, Monaco or Taiwan</strong>, your original licence plus an authorised Japanese translation is another option. A 1968 Vienna Convention IDP is not valid in Japan. Time limits and rental-company document rules apply.</p>
<p style="font-size:.93em;line-height:1.6;margin:0;"><a href="https://www.npa.go.jp/english/bureau/traffic/r8_english.pdf.pdf" target="_blank" rel="noopener noreferrer" style="text-decoration:underline;font-weight:700;">Official rules: Japan's National Police Agency</a> · <a href="https://english.jaf.or.jp/driving-in-japan/drive-in-japan/switch-to-japanese-license" target="_blank" rel="noopener noreferrer" style="text-decoration:underline;">JAF licence &amp; translation guidance</a></p>
</aside>
HTML;
}

/**
 * Pure HTML transformation for a single, existing DiscoverCars affiliate CTA.
 * Does not replace copy, insert another affiliate link, or alter the stored post.
 * When no safely identifiable paragraph exists, leave the input entirely unchanged.
 */
function tsurikue_en_driving_decorate($html) {
    if (!is_string($html) ||
        strpos($html, 'https://www.discovercars.com/?a_aid=tsurikue') === false ||
        strpos($html, 'data-tsurikue-en-driving="v1"') !== false) {
        return $html;
    }

    $pattern = '~<a\b[^>]*\bhref\s*=\s*["\x27]https://www\.discovercars\.com/\?a_aid=tsurikue["\x27][^>]*>~i';
    if (!preg_match($pattern, $html, $matches, PREG_OFFSET_CAPTURE)) {
        return $html;
    }

    $tag = $matches[0][0];
    $tag_at = $matches[0][1];
    $start = strripos(substr($html, 0, $tag_at), '<p');
    if ($start === false) {
        return $html;
    }

    $open_end = strpos($html, '>', $start);
    $close = strpos($html, '</p>', $tag_at);
    if ($open_end === false || $open_end >= $tag_at || $close === false) {
        return $html;
    }
    $opening = substr($html, $start, $open_end - $start + 1);
    if (!preg_match('~^<p(?:\s[^>]*)?>$~i', $opening)) {
        return $html;
    }
    $between = substr($html, $open_end + 1, $tag_at - $open_end - 1);
    if (stripos($between, '</p>') !== false || stripos($between, '<div') !== false) {
        return $html;
    }
    // Existing affiliate code and rel/sponsored attributes are preserved byte-for-byte.
    $css = 'display:inline-flex;align-items:center;justify-content:center;box-sizing:border-box;min-height:44px;max-width:100%;padding:12px 18px;margin:7px 2px 7px 0;border-radius:9px;background:#146d74;color:#fff!important;text-decoration:none!important;font-weight:700;line-height:1.5;white-space:normal;text-align:center;';
    if (preg_match('~\bclass\s*=\s*(["\x27])([^"\x27]*)\1~i', $tag)) {
        $tag = preg_replace_callback(
            '~\bclass\s*=\s*(["\x27])([^"\x27]*)\1~i',
            function ($m) { return 'class=' . $m[1] . trim($m[2] . ' tsurikue-en-rental-button') . $m[1]; },
            $tag,
            1
        );
    } else {
        $tag = preg_replace('~^<a\b~i', '<a class="tsurikue-en-rental-button"', $tag, 1);
    }
    if (preg_match('~\bstyle\s*=\s*(["\x27])([^"\x27]*)\1~i', $tag)) {
        $tag = preg_replace_callback(
            '~\bstyle\s*=\s*(["\x27])([^"\x27]*)\1~i',
            function ($m) use ($css) { return 'style=' . $m[1] . rtrim($m[2], ';') . ';' . $css . $m[1]; },
            $tag,
            1
        );
    } else {
        $tag = preg_replace('~^<a\b~i', '<a style="' . $css . '"', $tag, 1);
    }
    // Insert the visitor safety note before the existing rental CTA paragraph.
    $modified = substr_replace($html, $tag, $tag_at, strlen($matches[0][0]));
    return substr_replace($modified, tsurikue_en_driving_note_html() . "\n", $start, 0);
}

/** Only English Travel article detail pages, never Japanese posts, archives or home. */
function tsurikue_en_driving_filter($content) {
    if (!is_singular('post') || is_admin()) {
        return $content;
    }
    $id = (int) get_queried_object_id();
    if ($id <= 0) {
        return $content;
    }
    $post = get_post($id);
    if (!$post || $post->post_type !== 'post' ||
        !preg_match('/-english$/', $post->post_name) ||
        !has_category('english-travel', $id)) {
        return $content;
    }
    return tsurikue_en_driving_decorate($content);
}
add_filter('the_content', 'tsurikue_en_driving_filter', 35);
