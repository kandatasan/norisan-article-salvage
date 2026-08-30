#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

BASE_PATH = Path(__file__).with_name("apply_public_internal_links_once.py")
SPEC = importlib.util.spec_from_file_location("tsurikue_internal_link_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load internal-link base")
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)

BATCH_MARKER = "lexus-20260830"
PATCHES: list[dict[str, Any]] = json.loads(r'''[{"id":2870,"slug":"lexus-ux-review","title":"レクサスUXの評価・感想は？1万km以上乗った元オーナーが本音レビュー","insertions":[{"anchor":"<p>特に気になったのは、<strong>後席・荷室・価格</strong>です。</p>","targets":["lexus-ux-rear-seat","lexus-ux-cargo","lexus-ux-interior"],"text":"後席の実用性は<a href=\"https://tsurikue.com/lexus-ux-rear-seat/\">大人4人で乗った後部座席の感想</a>、荷物については<a href=\"https://tsurikue.com/lexus-ux-cargo/\">UXの荷室を実際に使った感想</a>、質感が気になる人は<a href=\"https://tsurikue.com/lexus-ux-interior/\">UXの内装レビュー</a>でそれぞれ詳しく紹介しています。"},{"anchor":"<p>現行UX300hのボディサイズは、全長4,495mm・全幅1,840mm・全高1,540mm。<br>最小回転半径は5.2mです。</p>","targets":["lexus-ux-size"],"text":"車幅1,840mmが実際に扱いやすかったのか、駐車場や狭い道での感覚は<a href=\"https://tsurikue.com/lexus-ux-size/\">レクサスUXのサイズ・取り回しの記事</a>にまとめています。"},{"anchor":"<p>1万km以上乗った経験から考えると、UXが合いやすいのはこんな人です。</p>","targets":["lexus-ux-buyer"],"text":"年齢層や年収より「どんな使い方ならUXがハマるか」を詳しく見たい人は、<a href=\"https://tsurikue.com/lexus-ux-buyer/\">レクサスUXを買う人・向いている人の記事</a>も参考にしてみてください。"},{"anchor":"<p>そのうえで今からもう一度選ぶなら、<strong>まず中古のUX250hを探します。</strong></p>","targets":["lexus-ux-used"],"text":"中古相場、CPO、前期・後期の違いまで含めた選び方は、<a href=\"https://tsurikue.com/lexus-ux-used/\">レクサスUXの中古は狙い目？</a>で整理しています。"}],"sha":"654357b78624ef62b2d0d076314cf38ef57fd9d83bfff1a339b234f5191dd9d2","targets":["lexus-ux-rear-seat","lexus-ux-cargo","lexus-ux-interior","lexus-ux-size","lexus-ux-buyer","lexus-ux-used"],"text":"contextual insertions"},{"id":2517,"slug":"ux-koukai","title":"レクサスUXはひどい？616万円で買って後悔した欠点と満足している理由","insertions":[{"anchor":"<p>レクサスUXの後席は狭いです。<br>\nここは、かばえません</p>","targets":["lexus-ux-rear-seat"],"text":"実際に大人4人で1〜2時間走ったときの使い勝手は、<a href=\"https://tsurikue.com/lexus-ux-rear-seat/\">レクサスUXの後部座席レビュー</a>で写真つきで詳しく紹介しています。"},{"anchor":"<p>UXはSUVですが、荷室の広さで選ぶ車ではありません。<br>\n日常の買い物や夫婦2人の旅行なら使えますが、大きな荷物を積むには割り切りが必要です。</p>","targets":["lexus-ux-cargo"],"text":"ゴルフバッグや大きな段ボールを積むとどうなるかは、<a href=\"https://tsurikue.com/lexus-ux-cargo/\">レクサスUXの荷室を実際に使った記事</a>で確認できます。"},{"anchor":"<p>私の感想としては、UXの内装全体がしょぼいというより、前席と後席で印象が違うというのが正直なところです。</p>","targets":["lexus-ux-interior"],"text":"前席・後席の質感やF SPORTの内装をもう少し細かく見たい人は、<a href=\"https://tsurikue.com/lexus-ux-interior/\">レクサスUXの内装レビュー</a>に写真をまとめています。"},{"anchor":"<p>約616万円で新車を買った私が言います。<br><strong>今もう一度UXを買うなら、中古です。</strong></p>","targets":["lexus-ux-used"],"text":"200〜300万円台の相場感やCPO、前期・後期の違いは、<a href=\"https://tsurikue.com/lexus-ux-used/\">中古UXの選び方</a>で詳しく整理しています。"}],"sha":"a4c7048c2af856cc27a820d6e771f661d58ef6e6b654b3142f4725cffacbfd71","targets":["lexus-ux-rear-seat","lexus-ux-cargo","lexus-ux-interior","lexus-ux-used"],"text":"contextual insertions"},{"id":2240,"slug":"ux-mitsumori","title":"レクサスUXの見積もり公開｜総額616万円で選んだ特別仕様車とオプション","insertions":[{"anchor":"<p>私が購入したのは、2023年に納車されたレクサスUX250h Fスポーツ特別仕様車「Emotional Explorer」です。<br>2023年6月に初度登録され、オプションや諸費用を含む支払総額は6,156,510円でした。</p>","targets":["lexus-ux-price"],"text":"現行UX300hの車両価格や乗り出し価格との違いは、<a href=\"https://tsurikue.com/lexus-ux-price/\">レクサスUXの価格記事</a>で比較しています。"},{"anchor":"<p>少なくとも私の周囲では、レクサスで大きな値引きを狙うのは難しそうでした。</p>","targets":["lexus-ux-discount"],"text":"私の値引き0円の実体験と、値引きが難しいときに負担を減らす方法は、<a href=\"https://tsurikue.com/lexus-ux-discount/\">レクサスUXの値引き記事</a>にまとめています。"}],"sha":"affbae6147edd90e9a707f609f46221c8228fe0ffe57acc5fc13e06c2a3e069b","targets":["lexus-ux-price","lexus-ux-discount"],"text":"contextual insertions"},{"id":2956,"slug":"lexus-ux-price","title":"レクサスUXの価格はいくら？乗り出し価格とグレード別の違い","insertions":[{"anchor":"<p>価格だけ知りたいならここまでで十分。<br>「その616万円の中身を見たい」という人は、見積もり記事を見ると分かりやすいです。</p>","targets":["lexus-ux-discount"],"text":"「そこから値引きできるの？」が気になる人は、<a href=\"https://tsurikue.com/lexus-ux-discount/\">値引き0円だった実体験と安く買う方法</a>もあわせてどうぞ。"},{"anchor":"<p>もちろん、特別仕様車と現行F SPORTをそのまま同条件として比べることはできません。<br>それでも「250hから300hになったら一気に100万円高くなった」という感じではありません。</p>","targets":["ux300h"],"text":"価格だけでなく走り・メーター・シフトノブの違いまで比べたい人は、<a href=\"https://tsurikue.com/ux300h/\">UX250hオーナーがUX300hへ試乗した比較記事</a>で確認できます。"}],"sha":"05969fc6c36efe4da0d856c001b6e8614d12553f121bc064b947bdccea04cda1","targets":["lexus-ux-discount","ux300h"],"text":"contextual insertions"},{"id":2874,"slug":"lexus-ux-poor","title":"レクサスUXは貧乏・見栄っ張りに見える？実際に所有して感じたこと","insertions":[{"anchor":"<p>私はUXを新車で買いましたが、今の相場を見ると<strong>「中古でもよかったな」</strong>と思える価格差です。</p>","targets":["lexus-ux-used"],"text":"実際の中古相場やCPO、前期・後期の違いは、<a href=\"https://tsurikue.com/lexus-ux-used/\">レクサスUXの中古は狙い目？</a>で詳しく見ています。"},{"anchor":"<p>私が1万km以上乗って感じたのは、<strong>サイズと使い方がハマる人ほど満足しやすい車</strong>だということです。</p>","targets":["lexus-ux-buyer"],"text":"どんな人ならUXと相性がいいのかは、<a href=\"https://tsurikue.com/lexus-ux-buyer/\">レクサスUXを買う人・向いている使い方の記事</a>でさらに掘り下げています。"}],"sha":"13a39a7d77084a9293cc89527e436994c35d1baa7d666f7a9431853f50b116fa","targets":["lexus-ux-used","lexus-ux-buyer"],"text":"contextual insertions"},{"id":2897,"slug":"lexus-ux-interior","title":"レクサスUXの内装はしょぼい？実際に触って感じた高級感と気になる部分","insertions":[{"anchor":"<p>UXを試乗するときは、運転席だけで終わらせず、一度後席にも座ってみてください。</p>","targets":["lexus-ux-rear-seat"],"text":"後席の広さそのものが気になる人は、<a href=\"https://tsurikue.com/lexus-ux-rear-seat/\">大人4人で乗ったUXの後部座席レビュー</a>も見ておくとイメージしやすいです。"},{"anchor":"<p>現行UX300hのF SPORTは内装色や加飾などが当時とは変わっています。中古でUX250hを狙う場合も、年式やグレード、特別仕様車で内装の印象が変わるので、写真を見比べる価値があります。</p>","targets":["ux300h","lexus-ux-used"],"text":"250hと300hのメーター・シフトまわりの違いは<a href=\"https://tsurikue.com/ux300h/\">UX300h試乗比較</a>、中古で前期・後期まで見比べたい人は<a href=\"https://tsurikue.com/lexus-ux-used/\">中古UXの選び方</a>にまとめています。"}],"sha":"3af8a91e8b5e2062922b1886acb22612ac59ba12e9c4a8ea119f7e8a11486668","targets":["lexus-ux-rear-seat","ux300h","lexus-ux-used"],"text":"contextual insertions"},{"id":2329,"slug":"ux300h","title":"レクサスUX300hを試乗｜UX250hオーナーが比較して感じた3つの違い","insertions":[{"anchor":"<p>内装も、ダッシュボードやセンターモニターの基本的な形は大きく変わっていません。</p>","targets":["lexus-ux-interior"],"text":"UX250hの前席・後席を含めた質感は、<a href=\"https://tsurikue.com/lexus-ux-interior/\">レクサスUXの内装レビュー</a>で写真つきで詳しく紹介しています。"},{"anchor":"<p>中古でUX250hとUX300hを選ぶなら、同じ予算でどんな車両が出ているかを見比べるのが早いです。</p>","targets":["lexus-ux-used"],"text":"中古相場や前期・後期、CPOまでまとめて比較するなら、<a href=\"https://tsurikue.com/lexus-ux-used/\">レクサスUXの中古は狙い目？</a>も参考になります。"}],"sha":"bcab3e742bb9f1520f0e4099a3ab8375584183df4e1b3ee5942df09317730c70","targets":["lexus-ux-interior","lexus-ux-used"],"text":"contextual insertions"},{"id":2575,"slug":"ccwatergold","title":"CCウォーターゴールドの評価は？プレミアを使って感じた効果・防汚・ムラの注意点","insertions":[{"anchor":"<p>洗車後は、ボディが濡れた状態のままCCウォーターゴールドプレミアをスプレーします。</p>","targets":["lexus-spindle-grille-carwash"],"text":"レクサスF SPORTの細かいグリルまで時短で洗いたい人は、<a href=\"https://tsurikue.com/lexus-spindle-grille-carwash/\">スピンドルグリルの洗車方法</a>も写真つきで紹介しています。"}],"sha":"096557caee09efda667cd9c956577502802416c03ada657966dca7bda2f7034b","targets":["lexus-spindle-grille-carwash"],"text":"contextual insertions"},{"id":2886,"slug":"lexus-ux-size","title":"レクサスUXのサイズは大きい？車幅・全長・取り回しを元オーナー目線で解説","insertions":[{"anchor":"<p>後席や荷室の狭さまで確認したい人は、<a href=\"https://tsurikue.com/ux-koukai/\">UXを買って感じた欠点</a>で詳しく紹介しています。</p>","targets":["lexus-ux-rear-seat","lexus-ux-cargo"],"text":"個別に見るなら、<a href=\"https://tsurikue.com/lexus-ux-rear-seat/\">UXの後部座席レビュー</a>と<a href=\"https://tsurikue.com/lexus-ux-cargo/\">UXの荷室レビュー</a>で実際の使い勝手を詳しく確認できます。"}],"sha":"e3938eb8b6dc981e6767f3aee1192be63d650e48f0ece72073c77c15c59e9b4c","targets":["lexus-ux-rear-seat","lexus-ux-cargo"],"text":"contextual insertions"},{"id":2948,"slug":"lexus-ux-used","title":"レクサスUXの中古は狙い目？新車と比べて中古をおすすめしたい理由","insertions":[{"anchor":"<p>写真は左から<strong>UX250h前期 → UX250h後期 → UX300h</strong>です。<br>前期から後期ではモニターサイズの違いが分かりやすく、前期にあるアナログ時計は今見てもかっこいいです。<br>250h後期と300hを比べると、メーターパネルとシフトノブの違いが目につきます。</p>","targets":["lexus-ux-interior"],"text":"内装の質感や前席・後席の違いまで見たい人は、<a href=\"https://tsurikue.com/lexus-ux-interior/\">レクサスUXの内装レビュー</a>もあわせてどうぞ。"}],"sha":"603ff35615b5deae74ddc7fce6cb913b8e77f1aa4cdf4f89f024072a73240698","targets":["lexus-ux-interior"],"text":"contextual insertions"}]''')


def patch_marker(slug: str) -> str:
    return f"<!-- tsurikue-internal-links:{BATCH_MARKER}:{slug} -->"


def desired_content(current: str, patch: dict[str, Any]) -> str:
    desired = current
    for index, insertion in enumerate(patch["insertions"], start=1):
        anchor = insertion["anchor"]
        if desired.count(anchor) != 1:
            raise RuntimeError(f"{patch['slug']}: anchor occurrence changed for insertion {index}")
        marker = patch_marker(patch["slug"]) + "\n" if index == 1 else ""
        block = (
            "\n\n" + marker +
            "<!-- wp:paragraph -->\n" +
            f"<p>{insertion['text']}</p>\n" +
            "<!-- /wp:paragraph -->"
        )
        desired = desired.replace(anchor, anchor + block, 1)
    return desired


base.BATCH_MARKER = BATCH_MARKER
base.REPORT_DIR = Path("reports/lexus-internal-links-20260830")
base.PATCHES = PATCHES
base.patch_marker = patch_marker
base.desired_content = desired_content

if __name__ == "__main__":
    raise SystemExit(base.main())
