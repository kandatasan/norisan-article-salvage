#!/usr/bin/env python3
"""Safely prepare and apply AdSense cleanup changes on tsurikue.com.

The default authenticated-dry-run fetches only explicitly listed published
posts/pages with context=edit, reads content.raw, and writes backups/diffs.
Apply mode is guarded by an exact confirmation string, sends only content,
rolls back earlier updates after any failure, and verifies the final content.
"""
from __future__ import annotations

import argparse
import base64
import collections
import csv
import difflib
import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

TARGET_DOCUMENTS = {1883: ('posts', 'https://tsurikue.com/aoriika-nikki/'),
 1887: ('posts', 'https://tsurikue.com/etajima-sightseeing/'),
 1892: ('posts', 'https://tsurikue.com/higashihiroshima-ramen/'),
 1911: ('posts', 'https://tsurikue.com/hiroshima-bokujyou/'),
 1939: ('posts', 'https://tsurikue.com/hiroshima-sanin-1night-2days/'),
 1955: ('posts', 'https://tsurikue.com/sera-sightseeing/'),
 1973: ('pages', 'https://tsurikue.com/profile/'),
 1996: ('posts', 'https://tsurikue.com/serakankounokotsu/'),
 2011: ('posts', 'https://tsurikue.com/yuki-town-drive/'),
 2026: ('posts', 'https://tsurikue.com/yuki-hotaru/'),
 2041: ('posts', 'https://tsurikue.com/hiroshima-sightseeing/'),
 2063: ('posts', 'https://tsurikue.com/hiroshima-hajimarinoteras/'),
 2075: ('posts', 'https://tsurikue.com/uminos-spa-resort/'),
 2096: ('posts', 'https://tsurikue.com/oliveoil/'),
 2115: ('posts', 'https://tsurikue.com/mamegashima/'),
 2125: ('posts', 'https://tsurikue.com/human-beach-nagase/'),
 2135: ('posts', 'https://tsurikue.com/kantan-aoriika/'),
 2152: ('posts', 'https://tsurikue.com/aoriika-oisiiyo/'),
 2157: ('posts', 'https://tsurikue.com/inkonohane-tsuretayo/'),
 2180: ('posts', 'https://tsurikue.com/irohasushi/'),
 2222: ('posts', 'https://tsurikue.com/ux-resale/'),
 2240: ('posts', 'https://tsurikue.com/ux-mitsumori/'),
 2255: ('pages', 'https://tsurikue.com/'),
 2329: ('posts', 'https://tsurikue.com/ux300h/'),
 2350: ('posts', 'https://tsurikue.com/kanritsuriba/'),
 2358: ('posts', 'https://tsurikue.com/everyman-iiyo/'),
 2391: ('posts', 'https://tsurikue.com/trout-cooking/'),
 2408: ('posts', 'https://tsurikue.com/muvalley/'),
 2437: ('posts', 'https://tsurikue.com/motonosumi/'),
 2456: ('posts', 'https://tsurikue.com/kulabotaisyoukan/'),
 2479: ('posts', 'https://tsurikue.com/tsunoshima/')}

EDIT_MEMOS = {'【ここに、ウミノスの外観または海が見える写真】',
 '【ここに、オリーブオイルを試している写真】',
 '【ここに、ご近所さんからいただいたサトイモの写真】',
 '【ここに、山陰1泊2日ドライブ旅のアイキャッチ写真】'}

LEGACY_REPLACEMENTS = {'※この記事は旧つりくえ！の釣行記をもとに、当時の体験を残しながら再編集しています。釣り場の状況、立入可否、ローカルルールなどは変わることがあるため、実際に釣行する場合は最新情報を確認してください。': '※この記事は、実際の釣行体験をもとに2026年7月に内容を整理しています。釣り場の状況、立入可否、ローカルルールなどは変わることがあるため、実際に釣行する場合は最新情報を確認してください。',
 '※この記事は旧つりくえ！の江田島観光体験をもとに再編集しています。営業時間・メニュー・営業状況・利用条件・潮干狩りのルールなどは変わることがあるため、実際に行く場合は公式情報や現地の最新情報を確認してください。': '※この記事は、実際に江田島を観光した体験をもとに2026年7月に内容を整理しています。営業時間・メニュー・営業状況・利用条件・潮干狩りのルールなどは変わることがあるため、実際に行く場合は公式情報や現地の最新情報を確認してください。',
 '旧記事では「5月1日〜7月31日までは禁漁」と書いていましたが、こういうルールは変わる可能性があるので、実際に行く前に必ず最新情報を確認してください。': '禁漁期間や採取ルールは変わる可能性があるため、実際に行く前に必ず最新情報を確認してください。',
 '昔の記事の情報だけで行くのではなく、今の営業状況を確認してから行く方が安心です。': '古い情報だけで判断せず、今の営業状況を確認してから行く方が安心です。',
 '※この記事は旧つりくえ！の記事をもとに、当時実際に食べた感想を残しながら再編集しています。営業時間・定休日・メニュー・価格・営業状況・駐車場などは変わることがあるため、実際に行く場合は最新情報を確認してください。': '※この記事は、実際に食べ歩いた体験をもとに2026年7月に内容を整理しています。営業時間・定休日・メニュー・価格・営業状況・駐車場などは変わることがあるため、実際に行く場合は最新情報を確認してください。',
 'この記事は、過去に実際に食べた体験をもとに再編集しています。': 'この記事は、実際に食べた体験をもとに2026年7月に内容を整理しています。',
 '※この記事は旧つりくえ！の記事をもとに、当時実際に行った体験を残しながら再編集しています。営業時間・定休日・体験メニュー・料金・営業状況などは変わることがあるため、実際に行く場合は公式情報や最新情報を確認してください。': '※この記事は、実際に訪れた体験をもとに2026年7月に内容を整理しています。営業時間・定休日・体験メニュー・料金・営業状況などは変わることがあるため、実際に行く場合は公式情報や最新情報を確認してください。',
 '旧記事は少し散らかっていたので、今回は実際に行った場所・移動の流れ・感じたことを残しつつ、旅行記事として読みやすく整理しています。': '今回は、実際に行った場所・移動の流れ・感じたことが分かりやすいよう、旅行記として整理しています。',
 '※この記事は旧つりくえ！の旅行記をもとに、当時の体験を残しながら再編集しています。営業時間・料金・営業状況・道路状況・駐車場などは変わることがあるため、実際に行く場合は公式情報や最新情報を確認してください。': '※この記事は、実際の旅行体験をもとに2026年7月に内容を整理しています。営業時間・料金・営業状況・道路状況・駐車場などは変わることがあるため、実際に行く場合は公式情報や最新情報を確認してください。',
 'この記事は、過去に実際に行った体験をもとに再編集しています。': 'この記事は、実際に行った体験をもとに2026年7月に内容を整理しています。',
 '※この記事は過去の世羅観光体験をもとに再編集しています。営業時間・定休日・開園時期・料金・営業状況などは変わることがあるため、実際に行く場合は公式情報や最新情報を確認してください。': '※この記事は、実際に世羅を観光した体験をもとに2026年7月に内容を整理しています。営業時間・定休日・開園時期・料金・営業状況などは変わることがあるため、実際に行く場合は公式情報や最新情報を確認してください。',
 '昔の休日ブログで残していた体験記や写真をサルベージしながら、実際に行った場所、食べたもの、釣った魚、走った道などを、できるだけ当時の空気感も残してまとめています。': '広島・山口を中心に、実際に行った場所、食べたもの、釣った魚、走った道などを、写真とともに当時の空気感も残しながら紹介しています。',
 '※この記事は過去に実際に行った体験をもとに再編集しています。開園時期・花の見頃・営業時間・料金・営業状況などは変わることがあるため、実際に行く場合は公式情報や最新情報を確認してください。': '※この記事は、実際に訪れた体験をもとに2026年7月に内容を整理しています。開園時期・花の見頃・営業時間・料金・営業状況などは変わることがあるため、実際に行く場合は公式情報や最新情報を確認してください。',
 '※この記事は過去に実際に湯来町で遊んだ体験をもとに再編集しています。営業時間・定休日・料金・営業状況・体験内容・予約条件などは変わることがあるため、実際に行く場合は公式情報や最新情報を確認してください。': '※この記事は、実際に湯来町で遊んだ体験をもとに2026年7月に内容を整理しています。営業時間・定休日・料金・営業状況・体験内容・予約条件などは変わることがあるため、実際に行く場合は公式情報や最新情報を確認してください。',
 '※この記事は過去に実際に湯来町でホタルを見に行った体験をもとに再編集しています。ホタルの発生時期・鑑賞できる場所・交通状況・施設の営業状況などは変わることがあるため、実際に行く場合は最新情報を確認してください。': '※この記事は、実際に湯来町でホタルを見た体験をもとに2026年7月に内容を整理しています。ホタルの発生時期・鑑賞できる場所・交通状況・施設の営業状況などは変わることがあるため、実際に行く場合は最新情報を確認してください。',
 '※この記事は、実際に行った体験記事をもとに再編集した広島観光・レジャーのまとめです。営業時間・料金・営業状況・イベント内容などは変わることがあるため、実際に行く場合は公式情報や最新情報を確認してください。': '※この記事は、実際に訪れた広島の観光・レジャースポットをまとめたものです。営業時間・料金・営業状況・イベント内容などは変わることがあるため、実際に行く場合は公式情報や最新情報を確認してください。',
 '※この記事は過去に実際に行った体験をもとに再編集しています。営業時間・定休日・メニュー・営業状況などは変わることがあるため、実際に行く場合は公式情報や最新情報を確認してください。': '※この記事は、実際に訪れた体験をもとに2026年7月に内容を整理しています。営業時間・定休日・メニュー・営業状況などは変わることがあるため、実際に行く場合は公式情報や最新情報を確認してください。',
 '旧記事を書いた当時は、海鮮丼、海鮮網焼き、カレー、せんじがらなどが気になっていました。': '訪問当時は、海鮮丼、海鮮網焼き、カレー、せんじがらなどが気になっていました。',
 '※この記事は過去の体験をもとに再編集しています。釣り場のルール、立入可否、駐車場所、釣れる時期などは変わることがあります。実際に行く場合は、現地の案内や最新情報を確認して、安全第一で楽しんでください。': '※この記事は、実際の釣行体験をもとに2026年7月に内容を整理しています。釣り場のルール、立入可否、駐車場所、釣れる時期などは変わることがあります。実際に行く場合は、現地の案内や最新情報を確認して、安全第一で楽しんでください。',
 '※この記事は過去の体験をもとに再編集しています。魚介類の保存・解凍・加熱、貝類の採取ルールなどは状況によって注意が必要です。実際に食べる場合は、鮮度や保存状態を確認し、安全第一で楽しんでください。': '※この記事は、実際に調理して食べた体験をもとに2026年7月に内容を整理しています。魚介類の保存・解凍・加熱、貝類の採取ルールなどは状況によって注意が必要です。実際に食べる場合は、鮮度や保存状態を確認し、安全第一で楽しんでください。',
 '※この記事は過去の体験をもとに再編集しています。営業時間・料金・持ち帰り匹数・レギュレーション・営業状況などは変わる可能性があります。実際に行く場合は、公式情報や現地の最新情報を確認してください。': '※この記事は、実際の釣行体験をもとに2026年7月に内容を整理しています。営業時間・料金・持ち帰り匹数・レギュレーション・営業状況などは変わる可能性があります。実際に行く場合は、公式情報や現地の最新情報を確認してください。',
 '旧記事の記録では、当時は3時間券、半日券、1日券などがありました。': '訪問当時は、3時間券、半日券、1日券などがありました。',
 '※この記事は2023年ごろの体験をもとに再編集しています。営業時間・定休日・価格・メニュー・駐車場などは変わる可能性があります。実際に行く場合は、店舗の最新情報を確認してください。': '※この記事は2023年ごろに実際に訪れた体験をもとに、2026年7月に内容を整理しています。営業時間・定休日・価格・メニュー・駐車場などは変わる可能性があります。実際に行く場合は、店舗の最新情報を確認してください。',
 '旧記事を書いた当時、海鮮丼は600円でした。': '訪問当時、海鮮丼は600円でした。',
 'この記事を再編集した時点でも同じ価格で提供されているようですが、内容や価格は変わる可能性があるため、行く前に最新情報を確認してください。': '2026年7月に確認した時点でも同じ価格で提供されているようですが、内容や価格は変わる可能性があるため、行く前に最新情報を確認してください。',
 '旧記事掲載時の価格は420円。': '訪問当時の価格は420円。',
 '旧記事掲載時は、握りも100円から200円ほどの手頃なものが多く、いろいろ食べやすかったです。': '訪問当時は、握りも100円から200円ほどの手頃なものが多く、いろいろ食べやすかったです。',
 '以下は、旧記事を掲載した当時の情報です。': '以下は、訪問当時の情報です。',
 '旧記事掲載時は、国道を挟んだ海側の広場が駐車スペースとして案内されていました。': '訪問当時は、国道を挟んだ海側の広場が駐車スペースとして案内されていました。',
 'この記事を再編集した時点でも同じ価格で提供されているようですが、値段や内容は変わる可能性があります。': '2026年7月に確認した時点でも同じ価格で提供されているようですが、値段や内容は変わる可能性があります。',
 '旧記事掲載時は、国道を挟んだ海側の広場が駐車可能な場所として案内されていました。': '訪問当時は、国道を挟んだ海側の広場が駐車可能な場所として案内されていました。',
 '※この記事は2022年11月に訪れた時の体験をもとに再編集しています。営業時間・料金・レンタル内容・持ち帰り匹数・釣り場のルールなどは変わる可能性があるため、実際に行く場合は公式情報や現地の最新案内を確認してください。': '※この記事は2022年11月に訪れた体験をもとに、2026年7月に内容を整理しています。営業時間・料金・レンタル内容・持ち帰り匹数・釣り場のルールなどは変わる可能性があるため、実際に行く場合は公式情報や現地の最新案内を確認してください。',
 '※この記事は2023年に公開した購入・実釣記録をもとに再編集しています。価格・在庫・セット内容・商品仕様は変わる可能性があるため、購入前に販売ページの最新情報を確認してください。': '※この記事は2023年に購入・実釣した記録をもとに、2026年7月に内容を整理しています。価格・在庫・セット内容・商品仕様は変わる可能性があるため、購入前に販売ページの最新情報を確認してください。',
 '※この記事は2023年に公開した実食記録をもとに再編集しています。魚の持ち帰り方法や生食の可否は、管理釣り場や魚の状態によって異なります。現地の案内を確認し、判断できない場合は十分に加熱してください。': '※この記事は2023年の実食体験をもとに、2026年7月に内容を整理しています。魚の持ち帰り方法や生食の可否は、管理釣り場や魚の状態によって異なります。現地の案内を確認し、判断できない場合は十分に加熱してください。'}

SPECIAL_ALT_BY_IMAGE = {
    (2255, 2269): "つりくえ！トップページのメインビジュアル",
    (2255, 2298): "釣りカテゴリー",
    (2255, 2297): "観光・レジャーカテゴリー",
    (2255, 2299): "グルメカテゴリー",
    (2255, 2300): "車カテゴリー",
}

DEAD_PATH = "/fishingpage"
DEAD_REPLACEMENT = "https://tsurikue.com/category/fishing/"
FORBIDDEN_TERMS = (
    "旧つりくえ！",
    "旧記事",
    "昔の記事",
    "昔の休日ブログ",
    "サルベージ",
    "再編集",
    "焼き直し",
    "移植",
    "復活記事",
)
EXPECTED_COUNTS = {
    "documents": 31,
    "edit_memos": 4,
    "legacy_replacements": 34,
    "link_replacements": 1,
    "alt_additions": 183,
    "remaining_edit_memos": 0,
    "remaining_legacy_terms": 0,
    "remaining_dead_links": 0,
    "remaining_blank_alts": 0,
}
APPLY_CONFIRMATION = "APPLY-ADSENSE-CLEANUP-20260711"
HOSTS = {"tsurikue.com", "www.tsurikue.com"}

WP_PARAGRAPH_RE = re.compile(
    r"(?P<whole><!--\s*wp:paragraph(?:\s+\{.*?\})?\s*-->\s*(?P<html><p\b[^>]*>.*?</p>)\s*<!--\s*/wp:paragraph\s*-->)",
    re.I | re.S,
)
P_INNER_RE = re.compile(r"(?P<open><p\b[^>]*>)(?P<body>.*?)(?P<close></p>)", re.I | re.S)
TAG_RE = re.compile(r"<!--.*?-->|<[^>]+>", re.S)
ANCHOR_RE = re.compile(
    r"<a\b[^>]*?href\s*=\s*(?P<q>[\"'])(?P<href>.*?)(?P=q)[^>]*>.*?</a\s*>",
    re.I | re.S,
)
TOKEN_RE = re.compile(
    r"(?P<heading><h(?P<level>[1-6])\b[^>]*>.*?</h(?P=level)>)|(?P<img><img\b[^>]*>)",
    re.I | re.S,
)
BLANK_ALT_RE = re.compile(r"\balt\s*=\s*(?P<q>[\"'])\s*(?P=q)", re.I)
WP_IMAGE_ID_RE = re.compile(r"\bwp-image-(\d+)\b", re.I)
GENERIC_MEMO_RE = re.compile(
    r"【\s*ここに[^】]*(?:写真|画像|アイキャッチ)[^】]*】|"
    r"(?:TODO|後で追加|写真を入れる|画像を入れる|写真を挿入|画像を挿入)",
    re.I,
)


@dataclass
class Action:
    kind: str
    before: str
    after: str
    detail: str


@dataclass
class Result:
    original: str
    updated: str
    actions: list[Action] = field(default_factory=list)
    remaining_edit_memos: list[str] = field(default_factory=list)
    remaining_legacy_terms: list[str] = field(default_factory=list)
    remaining_dead_links: list[str] = field(default_factory=list)
    remaining_blank_alts: int = 0


@dataclass
class Document:
    post_id: int
    endpoint_name: str
    title: str
    link: str
    content: str


@dataclass
class RunSummary:
    affected_documents: int
    edit_memos: int
    legacy_replacements: int
    link_replacements: int
    alt_additions: int
    remaining_edit_memos: int
    remaining_legacy_terms: int
    remaining_dead_links: int
    remaining_blank_alts: int


def visible_text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", fragment))).strip()


def normalize_internal_path(href: str) -> str | None:
    value = html.unescape(href).strip()
    if not value or value.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    if value.startswith("//"):
        value = "https:" + value
    parsed = urllib.parse.urlsplit(value)
    if (parsed.scheme or parsed.netloc) and (parsed.hostname or "").lower() not in HOSTS:
        return None
    path = urllib.parse.unquote(parsed.path or "/")
    if not path.startswith("/"):
        path = "/" + path
    path = re.sub(r"/{2,}", "/", path)
    return path.rstrip("/").lower() or "/"


def replace_paragraph_inner(whole: str, replacement: str) -> str:
    def repl(match: re.Match) -> str:
        return match.group("open") + html.escape(replacement, quote=False) + match.group("close")
    updated, count = P_INNER_RE.subn(repl, whole, count=1)
    if count != 1:
        raise ValueError("Could not replace paragraph body safely")
    return updated


def remove_edit_memos(content: str, actions: list[Action]) -> str:
    def repl(match: re.Match) -> str:
        whole = match.group("whole")
        text = visible_text(match.group("html"))
        if text not in EDIT_MEMOS:
            return whole
        actions.append(Action("delete_edit_memo", whole, "", text))
        return ""
    return WP_PARAGRAPH_RE.sub(repl, content)


def replace_legacy_paragraphs(content: str, actions: list[Action]) -> str:
    def repl(match: re.Match) -> str:
        whole = match.group("whole")
        text = visible_text(match.group("html"))
        replacement = LEGACY_REPLACEMENTS.get(text)
        if replacement is None:
            return whole
        updated = replace_paragraph_inner(whole, replacement)
        actions.append(Action("replace_legacy_text", whole, updated, text))
        return updated
    return WP_PARAGRAPH_RE.sub(repl, content)


def replace_dead_links(content: str, actions: list[Action]) -> str:
    def repl(match: re.Match) -> str:
        href = match.group("href")
        if normalize_internal_path(href) != DEAD_PATH:
            return match.group(0)
        before = match.group(0)
        after = before.replace(href, DEAD_REPLACEMENT, 1)
        actions.append(Action("replace_dead_link", before, after, href))
        return after
    return ANCHOR_RE.sub(repl, content)


def image_id(tag: str) -> int | None:
    match = WP_IMAGE_ID_RE.search(tag)
    return int(match.group(1)) if match else None


def short_title(title: str) -> str:
    return title.split("｜", 1)[0].strip()


def contextual_label(raw_heading: str | None, title: str) -> str:
    if not raw_heading:
        return re.sub(r"(?:へ|だった|です)$", "", short_title(title)).strip(" 　。")
    label = visible_text(raw_heading)
    if "｜" in label:
        left, right = [part.strip() for part in label.split("｜", 1)]
        if re.match(r"^(?:\d+日目|宿泊|周辺スポット|[①-⑳])", left):
            label = right
        else:
            label = left
    label = re.sub(r"^(?:\d+[．.]\s*)", "", label)
    if "は、" in label and len(label.split("は、", 1)[0]) >= 5:
        label = label.split("は、", 1)[0]
    label = re.sub(r"(?:へ|だった|です)$", "", label).strip(" 　。")
    return label or short_title(title)


def alt_base(post_id: int, title: str, heading: str | None, img_tag: str) -> str:
    key = (post_id, image_id(img_tag))
    if key in SPECIAL_ALT_BY_IMAGE:
        return SPECIAL_ALT_BY_IMAGE[key]
    return contextual_label(heading, title)


def fill_blank_alts(content: str, post_id: int, title: str, actions: list[Action]) -> str:
    heading: str | None = None
    candidates: list[tuple[int, str]] = []
    for token in TOKEN_RE.finditer(content):
        if token.group("heading"):
            heading = token.group("heading")
            continue
        img_tag = token.group("img")
        if BLANK_ALT_RE.search(img_tag):
            candidates.append((token.start(), alt_base(post_id, title, heading, img_tag)))

    totals = collections.Counter(base for _, base in candidates)
    seen: collections.Counter[str] = collections.Counter()
    heading = None

    def repl(token: re.Match) -> str:
        nonlocal heading
        if token.group("heading"):
            heading = token.group("heading")
            return token.group(0)
        img_tag = token.group("img")
        if not BLANK_ALT_RE.search(img_tag):
            return img_tag
        base = alt_base(post_id, title, heading, img_tag)
        seen[base] += 1
        alt = base if totals[base] == 1 else f"{base}（{seen[base]}枚目）"
        escaped = html.escape(alt, quote=True)
        updated = BLANK_ALT_RE.sub(lambda match: f'alt="{escaped}"', img_tag, count=1)
        actions.append(Action("add_alt", img_tag, updated, alt))
        return updated

    return TOKEN_RE.sub(repl, content)


def find_remaining_dead_links(content: str) -> list[str]:
    return [
        match.group("href")
        for match in ANCHOR_RE.finditer(content)
        if normalize_internal_path(match.group("href")) == DEAD_PATH
    ]


def transform(document: Document) -> Result:
    actions: list[Action] = []
    updated = remove_edit_memos(document.content, actions)
    updated = replace_legacy_paragraphs(updated, actions)
    updated = replace_dead_links(updated, actions)
    updated = fill_blank_alts(updated, document.post_id, document.title, actions)
    updated = re.sub(r"\n{4,}", "\n\n\n", updated)

    remaining_edit_memos = GENERIC_MEMO_RE.findall(visible_text(updated))
    remaining_legacy_terms = [term for term in FORBIDDEN_TERMS if term in visible_text(updated)]
    remaining_dead_links = find_remaining_dead_links(updated)
    remaining_blank_alts = len(BLANK_ALT_RE.findall(updated))
    return Result(
        document.content,
        updated,
        actions,
        remaining_edit_memos,
        remaining_legacy_terms,
        remaining_dead_links,
        remaining_blank_alts,
    )


def request_json(
    url: str,
    *,
    method: str = "GET",
    auth_header: str | None = None,
    payload: dict | None = None,
) -> dict:
    headers = {"Accept": "application/json", "User-Agent": "tsurikue-adsense-cleanup/1.0"}
    data = None
    if auth_header:
        headers["Authorization"] = auth_header
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def make_auth_header(user: str, app_password: str) -> str:
    token = base64.b64encode(f"{user}:{app_password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def endpoint_for(site_url: str, endpoint_name: str, post_id: int) -> str:
    return f"{site_url.rstrip('/')}/wp-json/wp/v2/{endpoint_name}/{post_id}"


def document_from_edit_row(row: dict, endpoint_name: str, expected_url: str) -> Document:
    if row.get("status") != "publish":
        raise ValueError(f"Document {row.get('id')} is not published")
    content = (row.get("content") or {}).get("raw")
    if content is None:
        raise ValueError(f"Document {row.get('id')} response did not include content.raw")
    link = row.get("link", "")
    if link.rstrip("/") != expected_url.rstrip("/"):
        raise ValueError(
            f"Document {row.get('id')} URL mismatch. expected={expected_url} actual={link}"
        )
    return Document(
        int(row["id"]),
        endpoint_name,
        html.unescape((row.get("title") or {}).get("raw") or (row.get("title") or {}).get("rendered", "")),
        link,
        content,
    )


def fetch_authenticated_documents(site_url: str, user: str, app_password: str) -> list[Document]:
    header = make_auth_header(user, app_password)
    documents = []
    fields = "id,status,link,title,content"
    for post_id, (endpoint_name, expected_url) in TARGET_DOCUMENTS.items():
        query = urllib.parse.urlencode({"context": "edit", "_fields": fields})
        row = request_json(
            f"{endpoint_for(site_url, endpoint_name, post_id)}?{query}",
            auth_header=header,
        )
        if int(row.get("id", 0)) != post_id:
            raise ValueError(f"Requested ID {post_id} but received {row.get('id')}")
        documents.append(document_from_edit_row(row, endpoint_name, expected_url))
    return documents


def fetch_xml(path: Path) -> list[Document]:
    ns = {
        "wp": "http://wordpress.org/export/1.2/",
        "content": "http://purl.org/rss/1.0/modules/content/",
    }
    tree = ET.parse(path)
    found: dict[int, Document] = {}
    endpoint_for_type = {"post": "posts", "page": "pages"}
    for item in tree.findall("./channel/item"):
        post_id = int(item.findtext("wp:post_id", default="0", namespaces=ns))
        if post_id not in TARGET_DOCUMENTS:
            continue
        post_type = item.findtext("wp:post_type", namespaces=ns)
        status = item.findtext("wp:status", namespaces=ns)
        if status != "publish" or post_type not in endpoint_for_type:
            continue
        endpoint_name = endpoint_for_type[post_type]
        expected_endpoint, expected_url = TARGET_DOCUMENTS[post_id]
        link = item.findtext("link", default="")
        if endpoint_name != expected_endpoint or link.rstrip("/") != expected_url.rstrip("/"):
            raise ValueError(f"XML identity mismatch for ID {post_id}")
        found[post_id] = Document(
            post_id,
            endpoint_name,
            item.findtext("title", default=""),
            link,
            item.findtext("content:encoded", default="", namespaces=ns),
        )
    missing = sorted(set(TARGET_DOCUMENTS) - set(found))
    if missing:
        raise ValueError(f"XML did not contain all target documents: {missing}")
    return [found[post_id] for post_id in TARGET_DOCUMENTS]


def summarize(rows: list[tuple[Document, Result]]) -> RunSummary:
    affected = [(doc, result) for doc, result in rows if result.actions or result.updated != result.original]
    count = lambda kind: sum(
        action.kind == kind for _, result in rows for action in result.actions
    )
    return RunSummary(
        affected_documents=len(affected),
        edit_memos=count("delete_edit_memo"),
        legacy_replacements=count("replace_legacy_text"),
        link_replacements=count("replace_dead_link"),
        alt_additions=count("add_alt"),
        remaining_edit_memos=sum(len(result.remaining_edit_memos) for _, result in rows),
        remaining_legacy_terms=sum(len(result.remaining_legacy_terms) for _, result in rows),
        remaining_dead_links=sum(len(result.remaining_dead_links) for _, result in rows),
        remaining_blank_alts=sum(result.remaining_blank_alts for _, result in rows),
    )


def validate_expected(summary: RunSummary) -> None:
    actual = {
        "documents": summary.affected_documents,
        "edit_memos": summary.edit_memos,
        "legacy_replacements": summary.legacy_replacements,
        "link_replacements": summary.link_replacements,
        "alt_additions": summary.alt_additions,
        "remaining_edit_memos": summary.remaining_edit_memos,
        "remaining_legacy_terms": summary.remaining_legacy_terms,
        "remaining_dead_links": summary.remaining_dead_links,
        "remaining_blank_alts": summary.remaining_blank_alts,
    }
    if actual != EXPECTED_COUNTS:
        raise SystemExit(
            f"Preflight counts did not match expected values. expected={EXPECTED_COUNTS} actual={actual}"
        )


def write_report(
    output: Path,
    rows: list[tuple[Document, Result]],
    source: str,
    mode: str,
    apply_status: dict[int, str] | None = None,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "backups").mkdir(exist_ok=True)
    (output / "diffs").mkdir(exist_ok=True)
    (output / "after").mkdir(exist_ok=True)
    summary = summarize(rows)

    with (output / "cleanup-summary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "post_id", "endpoint", "title", "url", "edit_memos",
            "legacy_replacements", "link_replacements", "alt_additions",
            "remaining_edit_memos", "remaining_legacy_terms",
            "remaining_dead_links", "remaining_blank_alts", "apply_status",
        ])
        for doc, result in rows:
            writer.writerow([
                doc.post_id,
                doc.endpoint_name,
                doc.title,
                doc.link,
                sum(a.kind == "delete_edit_memo" for a in result.actions),
                sum(a.kind == "replace_legacy_text" for a in result.actions),
                sum(a.kind == "replace_dead_link" for a in result.actions),
                sum(a.kind == "add_alt" for a in result.actions),
                len(result.remaining_edit_memos),
                len(result.remaining_legacy_terms),
                len(result.remaining_dead_links),
                result.remaining_blank_alts,
                (apply_status or {}).get(doc.post_id, "not-run"),
            ])

    lines = [
        "# つりくえ！AdSense再申請前 cleanup",
        "",
        f"- モード: {mode}",
        f"- 取得元: {source}",
        f"- 変更対象文書数: **{summary.affected_documents}**",
        f"- 編集メモ削除: **{summary.edit_memos}**",
        f"- 旧記事・再編集・サルベージ表現の置換: **{summary.legacy_replacements}**",
        f"- 404内部リンク修正: **{summary.link_replacements}**",
        f"- alt追加: **{summary.alt_additions}**",
        f"- 編集メモ残存: **{summary.remaining_edit_memos}**",
        f"- 対象表現残存: **{summary.remaining_legacy_terms}**",
        f"- 404リンク残存: **{summary.remaining_dead_links}**",
        f"- alt空欄残存: **{summary.remaining_blank_alts}**",
        "",
    ]
    if apply_status:
        lines += ["## apply結果", ""]
        for post_id in TARGET_DOCUMENTS:
            lines.append(f"- {post_id}: {apply_status.get(post_id, 'not-run')}")
        lines.append("")

    labels = {
        "delete_edit_memo": "編集メモを削除",
        "replace_legacy_text": "制作事情の表現を読者向け表現へ置換",
        "replace_dead_link": "404内部リンクを実在カテゴリーへ修正",
        "add_alt": "altテキストを追加",
    }
    for doc, result in rows:
        name = f"{doc.endpoint_name[:-1]}-{doc.post_id}"
        (output / "backups" / f"{name}.html").write_text(doc.content, encoding="utf-8")
        (output / "after" / f"{name}.html").write_text(result.updated, encoding="utf-8")
        diff = "".join(difflib.unified_diff(
            doc.content.splitlines(keepends=True),
            result.updated.splitlines(keepends=True),
            fromfile=f"before/{name}.html",
            tofile=f"after/{name}.html",
        ))
        (output / "diffs" / f"{name}.diff").write_text(diff, encoding="utf-8")
        doc_actions = result.actions
        if not doc_actions:
            continue
        lines += [
            f"## {doc.title}",
            "",
            f"- ID: `{doc.post_id}`",
            f"- REST endpoint: `{doc.endpoint_name}`",
            f"- URL: {doc.link}",
            "",
        ]
        for index, action in enumerate(doc_actions, 1):
            lines += [
                f"### {index}. {labels[action.kind]}",
                "",
                f"- 内容: {action.detail}",
                "",
                "変更前:",
                "```html",
                action.before.strip(),
                "```",
                "",
                "変更後:",
                "```html",
                action.after.strip() or "（削除）",
                "```",
                "",
            ]
    (output / "cleanup-report.md").write_text("\n".join(lines), encoding="utf-8")


def apply_updates_with_rollback(
    site_url: str,
    user: str,
    app_password: str,
    rows: list[tuple[Document, Result]],
) -> dict[int, str]:
    header = make_auth_header(user, app_password)
    statuses: dict[int, str] = {}
    updated_docs: list[Document] = []
    try:
        for doc, result in rows:
            if result.updated == result.original:
                statuses[doc.post_id] = "skipped-no-change"
                continue
            request_json(
                endpoint_for(site_url, doc.endpoint_name, doc.post_id),
                method="POST",
                auth_header=header,
                payload={"content": result.updated},
            )
            statuses[doc.post_id] = "updated"
            updated_docs.append(doc)
    except Exception as error:
        statuses[doc.post_id] = f"failed: {type(error).__name__}"
        rollback_errors: list[int] = []
        for old_doc in reversed(updated_docs):
            try:
                request_json(
                    endpoint_for(site_url, old_doc.endpoint_name, old_doc.post_id),
                    method="POST",
                    auth_header=header,
                    payload={"content": old_doc.content},
                )
                statuses[old_doc.post_id] = "rolled-back"
            except Exception as rollback_error:
                statuses[old_doc.post_id] = f"rollback-failed: {type(rollback_error).__name__}"
                rollback_errors.append(old_doc.post_id)
        if rollback_errors:
            raise RuntimeError(
                f"Update failed and rollback also failed for IDs {rollback_errors}"
            ) from error
        raise RuntimeError("Update failed; all earlier updates were rolled back") from error
    return statuses


def verify_after_apply(site_url: str, user: str, app_password: str) -> None:
    documents = fetch_authenticated_documents(site_url, user, app_password)
    rows = [(doc, transform(doc)) for doc in documents]
    summary = summarize(rows)
    if (
        summary.edit_memos
        or summary.legacy_replacements
        or summary.link_replacements
        or summary.alt_additions
        or summary.remaining_edit_memos
        or summary.remaining_legacy_terms
        or summary.remaining_dead_links
        or summary.remaining_blank_alts
    ):
        raise SystemExit(f"Post-apply verification failed: {summary}")


def credentials_from_args(args) -> tuple[str, str]:
    user = args.wp_user or os.environ.get("TSURIKUE_WP_USER")
    app_password = args.wp_app_password or os.environ.get("TSURIKUE_WP_APP_PASSWORD")
    if not user or not app_password:
        raise SystemExit("WordPress credentials are required for authenticated modes")
    return user, app_password


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xml", type=Path)
    parser.add_argument("--site-url", default="https://tsurikue.com")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/tsurikue-adsense-cleanup"),
    )
    parser.add_argument(
        "--mode",
        choices=("xml-dry-run", "authenticated-dry-run", "apply"),
        default="xml-dry-run",
    )
    parser.add_argument("--wp-user")
    parser.add_argument("--wp-app-password")
    parser.add_argument("--apply-confirmation", default="")
    args = parser.parse_args()

    try:
        if args.mode == "apply" and args.apply_confirmation != APPLY_CONFIRMATION:
            raise SystemExit(
                f"apply mode requires confirmation string {APPLY_CONFIRMATION}"
            )
        if args.xml:
            documents = fetch_xml(args.xml)
            source = f"WordPress XML: {args.xml}"
        elif args.mode in {"authenticated-dry-run", "apply"}:
            user, app_password = credentials_from_args(args)
            documents = fetch_authenticated_documents(args.site_url, user, app_password)
            source = "WordPress REST API authenticated context=edit content.raw"
        else:
            raise SystemExit("xml-dry-run requires --xml")
    except urllib.error.HTTPError as error:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "connection-error.txt").write_text(
            f"HTTP {error.code}", encoding="utf-8"
        )
        raise
    except Exception as error:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "connection-error.txt").write_text(
            type(error).__name__, encoding="utf-8"
        )
        raise

    rows = [(doc, transform(doc)) for doc in documents]
    summary = summarize(rows)
    write_report(args.output_dir, rows, source, args.mode)
    validate_expected(summary)

    apply_status = None
    if args.mode == "apply":
        # All original raw-content backups already exist before the first POST.
        user, app_password = credentials_from_args(args)
        apply_status = apply_updates_with_rollback(
            args.site_url, user, app_password, rows
        )
        verify_after_apply(args.site_url, user, app_password)
        write_report(args.output_dir, rows, source, args.mode, apply_status)

    print(f"Affected documents: {summary.affected_documents}")
    print(f"Edit memos deleted: {summary.edit_memos}")
    print(f"Legacy wording replacements: {summary.legacy_replacements}")
    print(f"Dead links replaced: {summary.link_replacements}")
    print(f"Alt additions: {summary.alt_additions}")
    print(f"Remaining blank alts: {summary.remaining_blank_alts}")
    print(f"Report: {args.output_dir / 'cleanup-report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
