#!/usr/bin/env python3
"""Deterministically archive the read-only research v0.8 SQLite to checked parts."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3

PART_SIZE=7_500_000
def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()
def package(db,output):
    db=Path(db);output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    gz=output/"river_biota_literal_names_v08.sqlite.gz"
    if gz.exists():raise FileExistsError(gz)
    with db.open("rb") as src,gz.open("wb") as target:
        with gzip.GzipFile(filename="",mode="wb",fileobj=target,mtime=0,compresslevel=9) as compressor:
            for data in iter(lambda:src.read(1024*1024),b""):compressor.write(data)
    parts=[]
    with gz.open("rb") as f:
        for i in range(100):
            chunk=f.read(PART_SIZE)
            if not chunk:break
            dest=output/f"river_biota_literal_names_v08.sqlite.gz.part{i:03d}"
            if dest.exists():raise FileExistsError(dest)
            dest.write_bytes(chunk)
            parts.append({"name":dest.name,"bytes":len(chunk),"sha256":sha(dest)})
    manifest={"version":8,"db_name":"river_biota_literal_names_v08.sqlite",
              "db_sha256":sha(db),"db_bytes":db.stat().st_size,
              "gzip_sha256":sha(gz),"gzip_bytes":gz.stat().st_size,"parts":parts}
    (output/"snapshot_parts_v08.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    gz.unlink()
    return manifest
def verify(parts_dir,db):
    parts_dir=Path(parts_dir);db=Path(db)
    meta=json.loads((parts_dir/"snapshot_parts_v08.json").read_text())
    if meta["version"]!=8 or db.exists():raise ValueError("Invalid v08 manifest or output exists")
    # Reassemble in /tmp near the restored DB, not within the source/output tree.
    z=db.with_name(meta["db_name"]+".gz")
    with z.open("wb") as out:
        for part in meta["parts"]:
            inp=parts_dir/part["name"]
            if inp.stat().st_size!=part["bytes"] or sha(inp)!=part["sha256"]:
                raise ValueError("Corrupted part "+part["name"])
            with inp.open("rb") as f:
                for chunk in iter(lambda:f.read(1024*1024),b""):out.write(chunk)
    if sha(z)!=meta["gzip_sha256"]:raise ValueError("Gzip manifest hash mismatch")
    with gzip.open(z,"rb") as src,db.open("wb") as dst:
        for chunk in iter(lambda:src.read(1024*1024),b""):dst.write(chunk)
    if db.stat().st_size!=meta["db_bytes"] or sha(db)!=meta["db_sha256"]:
        raise ValueError("New DB hash mismatch")
    c=sqlite3.connect(f"file:{db.resolve()}?mode=ro",uri=True)
    try:
        if c.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise ValueError("SQLite integrity check failed")
        if c.execute("SELECT COUNT(*) FROM river").fetchone()[0]!=428:
            raise ValueError("Research individual river identity count regression")
        if c.execute("SELECT SUM(historical_contexts) FROM literal_taxon_label").fetchone()[0]!=553351:
            raise ValueError("Historical context conservation failed")
        if c.execute("SELECT COUNT(*) FROM category_summary").fetchone()[0]!=1712:
            raise ValueError("Four panels for all river names missing")
    finally:c.close()
    return meta
def main():
    p=argparse.ArgumentParser();p.add_argument("action",choices=("package","verify"))
    p.add_argument("--db",required=True);p.add_argument("--parts-dir",required=True)
    a=p.parse_args()
    result=package(a.db,a.parts_dir) if a.action=="package" else verify(a.parts_dir,a.db)
    print(json.dumps({"version":result["version"],"bytes":result["db_bytes"],"parts":len(result["parts"]),"sha256":result["db_sha256"]}))
if __name__=="__main__":main()
