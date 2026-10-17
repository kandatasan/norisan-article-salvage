#!/usr/bin/env python3
"""Explain rejected official rows by category only; never print fish station names."""
from collections import Counter
from aggregate_official_workbook import get_official_zip, excel_rows

def main():
    raw,_=get_official_zip()
    c=Counter()
    miss=Counter()
    categories={}
    for row in excel_rows(raw):
        category=row.get('C','[blank]')
        c[category]+=1
        categories.setdefault(category,set()).add(row.get('J',''))
        if not row.get('F'):miss['watershed_blank']+=1
        if not row.get('G'):miss['year_blank']+=1
        if not row.get('J'):miss['fish_name_blank']+=1
    print("public source category distribution",dict(c))
    print("blank field totals",dict(miss))
    for kind,names in categories.items():
        print("category",kind,"unique_names",len(names),"sample_names",sorted(names)[:70])
        print("invertebrate_keyword_names",sorted([s for s in names if any(k in s for k in ("エビ","カニ","貝","ヤドカリ","イカ","タコ","クラゲ"))])[:30])
if __name__=='__main__':main()
