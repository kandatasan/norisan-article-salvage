#!/usr/bin/env python3
"""Inspect official MLIT Kyushu watershed/river pair page; do not infer codes.

Read-only research stage. This page supplies watershed + river-name context,
but NOT a ten-digit river code. No B->A promotion is permitted by this script.
"""
import argparse
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
import urllib.request

SOURCE="https://www.mlit.go.jp/river/hourei_tsutatsu/riyou/kasen_riyou/oudan/kyuushuu.html"
BASINS=set("遠賀川 山国川 筑後川 矢部川 松浦川 大分川 大野川 番匠川 五ヶ瀬川 小丸川 大淀川 川内川 肝属川 球磨川 緑川 白川 菊池川 六角川 嘉瀬川 本明川".split())
class TableReader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows=[];self.current_row=None;self.current_cell=None
    def handle_starttag(self,tag,attrs):
        if tag=="tr":self.current_row=[]
        elif tag in ("td","th") and self.current_row is not None:self.current_cell=[]
        elif tag=="br" and self.current_cell is not None:self.current_cell.append("\n")
    def handle_data(self,data):
        if self.current_cell is not None:self.current_cell.append(data)
    def handle_endtag(self,tag):
        if tag in ("td","th") and self.current_cell is not None:
            self.current_row.append("".join(self.current_cell))
            self.current_cell=None
        if tag=="tr" and self.current_row is not None:
            self.rows.append(self.current_row);self.current_row=None

def fetch():
    req=urllib.request.Request(SOURCE,headers={"User-Agent":"Tsurikue-research-kyushu-v04/1.0"})
    with urllib.request.urlopen(req,timeout=45) as response:
        if response.status!=200 or response.url!=SOURCE:raise ValueError("Unexpected government URL/redirect")
        b=response.read(2_000_001)
        if len(b)>2_000_000:raise ValueError("Oversized HTML")
        c=response.headers.get_content_charset()
    fallback=c or "cp932"
    try:s=b.decode(fallback)
    except UnicodeDecodeError:
        # The archived distribution page can use EUC-JP or Shift_JIS.
        for enc in ["cp932","euc_jp","utf-8"]:
            try:s=b.decode(enc);fallback=enc;break
            except UnicodeDecodeError:continue
        else:raise ValueError("Unknown charset in MLIT HTML")
    return b,s,fallback

def probe(out):
    raw,html,encoding=fetch()
    parser=TableReader();parser.feed(html)
    def tidy(s):
        return "\n".join(re.sub(r"\s+"," ",line.strip()) for line in s.splitlines() if line.strip())
    table_rows=[[tidy(cell) for cell in row] for row in parser.rows if row]
    hits=[(i,row) for i,row in enumerate(table_rows) if any(basin in row[0].splitlines() for basin in BASINS)]
    data={"source_url":SOURCE,"source_sha256":hashlib.sha256(raw).hexdigest(),"encoding":encoding,
          "html_bytes":len(raw),"total_table_rows":len(table_rows),
          "basin_rows":len(hits),"basin_list_count":len(BASINS),
          "sample_rows": [{"index":i,"cells":row[:3]} for i,row in hits[:8]],
          "prohibited_as_ten_digit_approval":True,
          "source_is_river_map_distribution_list":True}
    Path(out).parent.mkdir(parents=True,exist_ok=True)
    Path(out).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(data,ensure_ascii=False))
    return data
if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--out",required=True)
    args=ap.parse_args();probe(args.out)
