#!/usr/bin/env python3
"""Explain rejected official rows by category only; never print fish station names."""
from collections import Counter
from aggregate_official_workbook import get_official_zip, excel_rows

def main():
    raw,_=get_official_zip()
    c=Counter()
    miss=Counter()
    for row in excel_rows(raw):
        c[row.get('C','[blank]')]+=1
        if not row.get('F'):miss['watershed_blank']+=1
        if not row.get('G'):miss['year_blank']+=1
        if not row.get('J'):miss['fish_name_blank']+=1
    print("public source category distribution",dict(c))
    print("blank field totals",dict(miss))
if __name__=='__main__':main()
