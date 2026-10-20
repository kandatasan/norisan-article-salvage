#!/usr/bin/env python3
"""Research v26: responsive a11y polish and reproducible Chromium-ready ZIP, without data edits."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import hashlib,json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
OUT=HERE/"outputs"
ORIGINAL=ROOT/"research-individual-v25"/"outputs"/"river_fish_direct_search_v25.zip"
ORIGINAL_QA=ROOT/"research-individual-v25"/"outputs"/"river_fish_direct_search_qa_v25.json"
ZIP=OUT/"river_fish_browser_review_v26.zip"
QA=OUT/"river_fish_browser_review_qa_v26.json"

CSS="""
/* v26 preview-only mobile/a11y polish for new fish and river discovery controls. */
#riverFishOnlyV25{width:18px;min-width:18px;height:18px;min-height:18px;vertical-align:middle;accent-color:#0b687c;margin:0 7px 0 0;padding:0}
#riverQuickFinderV25 label[for="riverFishOnlyV25"]{display:flex;align-items:center;gap:5px;margin:12px 0 4px;font-weight:500;line-height:1.45}
#riverSearchResultsV25 .record button,#reverseResultsV24 .record button{
 margin:4px 5px 5px 0;max-width:100%;white-space:normal;
 text-align:left;overflow-wrap:anywhere;line-height:1.55;
}
#riverSearchResultsV25 .record,#reverseResultsV24 .record{overflow-wrap:anywhere}
#reverseFishV24,#riverSearchV25{max-width:100%;min-width:0}
#riverQuickFinderV25 button:focus-visible,#fishReverseFinderV24 button:focus-visible{
 outline:3px solid #e6a246;outline-offset:2px
}
@media(max-width:730px){
 #riverQuickFinderV25,#fishReverseFinderV24{padding:15px}
 #reverseResultsV24 .record button,#riverSearchResultsV25 .record button{display:block;width:100%;margin:7px 0}
}
"""
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    prev=json.loads(ORIGINAL_QA.read_text(encoding="utf-8"))
    source_sha=hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()
    assert source_sha==prev["archive_sha256"]
    with ZipFile(ORIGINAL) as source:
        assert source.testzip() is None
        html=source.read("index.html").decode("utf-8")
        assert html.count("</style>")==1
        assert html.count('id="riverFishOnlyV25"')==1
        assert html.count('id="reverseFishV24"')==1
        assert html.count("v0.25")>=1
        assert "#riverFishOnlyV25" not in html,"CSS override already exists"
        html=html.replace("</style>",CSS+"\n</style>")
        html=html.replace("v0.25","v0.26")
        with ZipFile(ZIP,"w",compression=ZIP_DEFLATED,compresslevel=8) as out:
            for file in source.namelist():
                blob=source.read(file)
                if file=="index.html":blob=html.encode("utf-8")
                elif file=="readme_preview.txt":
                    blob=("つりくえ！河川魚類図鑑 v0.26 研究用ブラウザQA対象。\n"
                          "511件の元調査グループと1057件の公式資料掲載名を保持。\n"
                          "魚と川の双方向検索・中国地方13水系の参考魚・iPhone幅対応の試験版。\n"
                          "データ内容と出典、地理的同一性、調査方法を変更しません。\n"
                          "本番WordPressは未変更。\n").encode("utf-8")
                out.writestr(file,blob)
        with ZipFile(ZIP) as audit:
            assert audit.testzip() is None
            assert audit.read("index.html").decode().count("#riverFishOnlyV25")==1
            for file in source.namelist():
                if file not in ("index.html","readme_preview.txt"):
                    assert audit.read(file)==source.read(file),file
        result={"version":"v26","research_only":True,"original_v25_SHA256":source_sha,
          "existing_source_display_groups_unchanged":1568,
          "existing_named_fish_reverse_search_candidates_unchanged":349,
          "all_data_and_references_byte_identical_to_v25":True,
          "changes":["preview CSS checkbox size","responsive search result button wrap","keyboard focus ring"],
          "requires_chromium_end_to_end_test":True,
          "not_a_Safari_real_device_test":True,
          "not_wordpress_or_production":True,
          "zip":ZIP.name,"zip_sha256":hashlib.sha256(ZIP.read_bytes()).hexdigest()}
        QA.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":main()
