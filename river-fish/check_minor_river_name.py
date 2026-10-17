#!/usr/bin/env python3
"""Inspect whether a small river appears in official China fish records.

Exact, literal river names only. Prints counts, never fish names or stations.
The parent watershed's records must not be relabeled as tributary records.
"""
import argparse
import collections
import re
import unicodedata
import xml.etree.ElementTree as ET
from io import BytesIO
from zipfile import ZipFile

from aggregate_official_workbook import MEMBER, M, get_official_zip


def normalize(s):
    return unicodedata.normalize("NFKC",str(s or "")).replace("\u3000"," ").strip()


def iter_named_rivers(downloaded_zip):
    with ZipFile(BytesIO(downloaded_zip)) as z:
        book=z.read(MEMBER)
    with ZipFile(BytesIO(book)) as z:
        strings=[]
        with z.open("xl/sharedStrings.xml") as f:
            for event,element in ET.iterparse(f,events=("end",)):
                if element.tag == M+"si":
                    strings.append("".join(t.text or "" for t in element.iter(M+"t")))
                    element.clear()
        with z.open("xl/worksheets/sheet1.xml") as f:
            for _, row in ET.iterparse(f,events=("end",)):
                if row.tag != M+"row":continue
                found={}
                for cell in row.findall(M+"c"):
                    code=re.match(r"^[A-Z]+",cell.get("r",""))
                    key=code.group(0) if code else None
                    if key not in ("C","F","G","M"):continue
                    value=cell.findtext(M+"v") or ""
                    if cell.get("t")=="s" and value.isdecimal():
                        value=strings[int(value)]
                    found[key]=normalize(value)
                if found.get("M")=="河川名":
                    pass
                elif found:
                    yield found
                row.clear()


def inspect(name):
    source,_=get_official_zip()
    counts=collections.Counter()
    total=0
    parent=collections.Counter()
    for record in iter_named_rivers(source):
        total+=1
        # Literal name comparison; no fuzzy match, no parent-watershed inference.
        if normalize(record.get("M"))==normalize(name):
            counts[(record.get("C"),record.get("F"),record.get("G"))]+=1
            parent[record.get("F")]+=1
    print("river_query",repr(name))
    print("source_row_count",total)
    print("exact_river_name_rows",sum(counts.values()))
    print("match_by_category_watershed_year",sorted(counts.items()))
    print("matching_parent_watersheds",dict(parent))
    print("RESULT_UNVERIFIED_FISH" if not counts else "RESULT_RECORDS_EXIST_NOT_SPECIES_CLEARED")
    print("Small-river names are not automatically equal to the parent's fish occurrences.")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--river",required=True)
    args=parser.parse_args()
    inspect(args.river)
