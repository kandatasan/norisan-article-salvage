#!/usr/bin/env python3
"""Inspect the official download landing page, without guessing data links.

Only reads a fixed MLIT/NILIM URL and prints small redacted excerpts.
Does not download a species dataset, publish data or contact WordPress.
"""
from urllib.request import Request, urlopen
from html.parser import HTMLParser
import re
from html import unescape

URL = "https://www.nilim.go.jp/lab/fbg/ksnkankyo/dl_00_index.html"

class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts=[]
        self.images=[]
        self.forms=[]
        self.links=[]
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag=="script" and d.get("src"):self.scripts.append(d["src"])
        if tag=="img" and "btn" in d.get("src","").lower():self.images.append(d)
        if tag=="form":self.forms.append(d)
        if tag=="a":self.links.append(d)

def main():
    req=Request(URL,headers={"User-Agent":"tsurikue-research-probe/0.1"})
    with urlopen(req, timeout=35) as res:
        raw=res.read(300_000)
        print("url:",res.url,"status:",res.status,"bytes read:",len(raw),"ctype:",res.headers.get("content-type"))
    page=raw.decode("cp932",errors="replace") if b"charset=shift_jis" in raw[:3000].lower() else raw.decode("utf-8",errors="replace")
    parser=PageParser();parser.feed(page)
    print("scripts:",parser.scripts[:20])
    print("forms:",parser.forms[:5])
    print("download buttons:",parser.images[:5])
    print("link targets sample:",[x.get("href","") for x in parser.links if x.get("href","").lower().endswith((".zip",".csv"))][:15])
    for needle in ("中国","dl_btn01","download","Download","CSV","csv"):
        matches=list(re.finditer(re.escape(needle),page,re.I))
        print("MATCH",needle,"count",len(matches))
        for m in matches[:3]:
            print("excerpt:",unescape(re.sub(r"\s+"," ",page[max(0,m.start()-300):m.end()+400]))[:750])
    for js in parser.scripts:
        if js.startswith(("http://","https://")):continue
        if not js or ".." in js:continue
        from urllib.parse import urljoin,urlparse
        u=urljoin(URL,js)
        if urlparse(u).netloc not in ("www.nilim.go.jp","gis.nilim.go.jp"):continue
        try:
            with urlopen(Request(u,headers={"User-Agent":"tsurikue-research-probe/0.1"}),timeout=20) as res: body=res.read(250_000)
            t=body.decode("utf-8",errors="replace")
            print("SCRIPT",u,"len",len(body))
            for needle in ("csv","download","dl_"):
                for m in list(re.finditer(needle,t,re.I))[:2]:
                    print("JS excerpt:",re.sub(r"\s+"," ",t[max(0,m.start()-200):m.end()+300])[:650])
        except Exception as e:
            print("script fetch unavailable",u,type(e).__name__)
if __name__=="__main__":main()
