#!/usr/bin/env python3
"""Inspect Chinese-region fish ZIP from the official NILIM download index.

Never exports precise collection coordinates, secret or location samples.
Hard-limits the downloaded data and decompressed member size.
"""
from io import BytesIO,StringIO
from urllib.request import Request,urlopen
from urllib.parse import urlparse
from zipfile import ZipFile
import csv,hashlib

URL="https://www.nilim.go.jp/lab/fbg/ksnkankyo/download/slist/RT87_B01.zip"
MAX_DOWNLOAD=75_000_000
MAX_MEMBER=25_000_000

def main():
    assert urlparse(URL).hostname=="www.nilim.go.jp"
    req=Request(URL,headers={"User-Agent":"tsurikue-research-probe/0.1"})
    with urlopen(req,timeout=75) as f:
        payload=f.read(MAX_DOWNLOAD+1)
        print("source:",f.url,"http:",f.status,"compressed_bytes:",len(payload))
    if len(payload)>MAX_DOWNLOAD:raise RuntimeError("ZIP exceeds max download")
    if not payload.startswith(b"PK"):raise RuntimeError("Not a ZIP")
    print("source_zip_sha256:",hashlib.sha256(payload).hexdigest())
    with ZipFile(BytesIO(payload)) as z:
        info=z.infolist()
        print("member_count",len(info),"total_uncompressed",sum(x.file_size for x in info))
        for x in info[:30]:
            print("member:",repr(x.filename),"size:",x.file_size)
            if x.is_dir() or x.file_size>MAX_MEMBER:continue
            if not x.filename.lower().endswith((".csv",".txt")):continue
            raw=z.read(x)
            for enc in ("utf-8-sig","cp932"):
                try:
                    data=raw.decode(enc);break
                except UnicodeDecodeError:continue
            else:
                print("decode_fail");continue
            head=data[:20000].splitlines()[:7]
            print("encoding:",enc,"line_count:",len(data.splitlines()),"sample_line_shapes:",[(len(line),len(list(csv.reader([line]))[0])) for line in head])
            for n,line in enumerate(head):
                fields=list(csv.reader([line]))[0]
                # Never print exact observation locations or coordinates
                print("line",n+1,"first_columns_preview",[(str(v)[:30] if n==0 else "[hidden]") for v in fields[:16]])
if __name__=="__main__":main()
