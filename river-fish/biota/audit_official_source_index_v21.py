#!/usr/bin/env python3
"""Inventory verified MLIT index URLs for *unreviewed* survey source groups.

This deliberately downloads only the public index HTML, never biological
observations or archive contents. Filenames are NOT trusted as species groups.
This provides a staged queue for human/schema review before any new imports.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
from urllib.parse import urljoin
from html.parser import HTMLParser

from inspect_nationwide_source_v06 import fetch

HERE=Path(__file__).resolve().parent
PINS=HERE/"benthic_sources_v19.json"
REGIONS={"81":"hokkaido","82":"tohoku","83":"kanto","84":"hokuriku",
         "85":"chubu","86":"kinki","87":"chugoku","88":"shikoku","89":"kyushu"}
BASE="https://www.nilim.go.jp/lab/fbg/ksnkankyo/download/slist/"
INDEX="https://www.nilim.go.jp/lab/fbg/ksnkankyo/dl_00_index.html"
PATTERN=re.compile(r"^"+re.escape(BASE)+r"(RT8[1-9]_[A-Za-z0-9]+\.zip)$")
MAX_INDEX_BYTES=600_000

class OfficialLinks(HTMLParser):
    def __init__(self):
        super().__init__(); self.hrefs=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower()!="a":return
        vals=dict(attrs)
        if "href" in vals and isinstance(vals["href"],str):
            self.hrefs.append(vals["href"])

def inventory(html,index_url=INDEX,pins_path=PINS):
    if index_url!=INDEX:
        raise ValueError("Unexpected source index: review authority")
    pins=json.loads(Path(pins_path).read_text(encoding="utf-8"))
    if pins["verified_index_url"]!=INDEX or pins["public_site_status"]!="research_only":
        raise ValueError("Existing vetted source registry changed")
    known={r["region"]:r["source_url"] for r in pins["regions"]}
    if set(known)!=set(REGIONS.values()):
        raise ValueError("Incomplete 9-region source registry")
    parser=OfficialLinks()
    parser.feed(html.decode("utf-8",errors="replace") if isinstance(html,bytes) else html)
    urls=set()
    ignored=0
    for href in parser.hrefs:
        absolute=urljoin(index_url,href)
        if PATTERN.fullmatch(absolute):
            urls.add(absolute)
        else:
            ignored+=1
    by_region=defaultdict(list)
    for url in sorted(urls):
        source=PATTERN.fullmatch(url).group(1)
        region_code=source[2:4]
        by_region[REGIONS[region_code]].append(url)
    missing=[region for region,source_url in known.items() if source_url not in by_region[region]]
    if missing:raise ValueError("Official index missing previously verified benthic sources: "+",".join(missing))
    if not urls or any(len(by_region[r])<2 for r in known):
        raise ValueError("Index biological source candidates unexpectedly sparse; inspect official HTML")
    result=[]
    for number,region in REGIONS.items():
        entries=[{
            "url":url,
            "official_index_link_found":True,
            "survey_category":"benthic_animals" if url==known[region] else None,
            "verified_by_previous_v19":url==known[region],
            "archive_sha256_checked":bool(url==known[region]),
            "source_schema_checked":bool(url==known[region]),
            "next_action":"existing_v19_source" if url==known[region] else "inspect_archive_hash_member_header_then_assign_category"
        } for url in by_region[region]]
        result.append({"region":region,"official_region_code":number,
                       "candidate_count":len(entries),"candidates":entries})
    return {
        "index_url":INDEX,
        "evidence":"public_direct_link_inventory_only",
        "new_biological_observations_imported":0,
        "new_survey_categories_approved":0,
        "wordpress_modified":False,
        "individual_river_or_prefecture_inferred":False,
        "raw_archive_downloaded":False,
        "raw_observation_locations_collected":False,
        "candidate_url_count":len(urls),
        "existing_v19_benthic_sources":9,
        "ignored_unrelated_or_unsafe_links":ignored,
        "regions":result,
        "next_review":"Assign plants/birds/amphibians/insects only after archive checksum, sheet and original biological category verified."
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    a=p.parse_args()
    raw=fetch(INDEX,MAX_INDEX_BYTES)
    if b"RT87_B02.zip" not in raw:
        # No loose discovery if the official trusted reference is not present.
        raise ValueError("Official index structure changed; do not guess sources")
    result=inventory(raw)
    target=Path(a.out)
    if target.exists():raise FileExistsError("Will not overwrite existing source inventory")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="regions"},ensure_ascii=False))
if __name__=="__main__":
    main()
