#!/usr/bin/env python3
"""OFFLINE localhost-only atlas preview with indexed, lazy four-category lookups.

GET /                                     small interactive HTML (no embedded 250k names)
GET /api/v1/prefectures                   47 pref names, counts
GET /api/v1/watersheds?pref=広島県          sourced documentary basin entrances
GET /api/v1/rivers?pref=広島県&watershed=太田川   name-first river links
GET /api/v1/river/rn_<24-hex>?category=fish&limit=20&offset=0

Not a production server. NO modifications to WordPress, Xserver, source
SQLite, original survey records. No remote listeners or external browser API.
Official prefecture/river evidence remains restricted as in v07.
"""
from __future__ import annotations
import argparse
from contextlib import closing
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs,urlsplit

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"research-individual-v08"))
from read_full_literal_name_index_v08 import GROUPS,connect,read

RIVER_ID=re.compile(r"^/api/v1/river/(rn_[a-f0-9]{24})$")
MAX_RESPONSE_BYTES=300_000

class AtlasData:
    def __init__(self,db,nav,html):
        self.db=Path(db).resolve();self.html=Path(html).resolve()
        data=json.loads(Path(nav).read_text(encoding="utf-8"))
        if len(data["prefectures"])!=47 or len(data["rivers"])!=428:
            raise ValueError("Incomplete research river atlas")
        self.prefs={p["prefecture"]:p for p in data["prefectures"]}
        self.river_map={r["identity_key"]:r for r in data["rivers"]}
        self.basins={}
        self.pref_rivers={}
        for w in data["prefecture_watershed_entries"]:
            self.basins.setdefault(w["prefecture"],[]).append(w)
        for x in data["prefecture_river_links"]:
            self.pref_rivers.setdefault((x["prefecture"],x["watershed"]),[]).append(x)
        if sum(len(x) for x in self.basins.values())<80 or sum(len(x) for x in self.pref_rivers.values())<489:
            raise ValueError("Official research crosswalk is incomplete")
        with closing(connect(db)) as c:
            if c.execute("SELECT COUNT(*) FROM river").fetchone()[0]!=428:
                raise ValueError("v08 compact source index changed")
            if c.execute("SELECT SUM(historical_contexts) FROM literal_taxon_label").fetchone()[0]!=553351:
                raise ValueError("Full literal label context conservation failed")

    def lookup(self,route,params):
        def exactly_one(key,required=True,default=None,maxlen=100):
            found=params.get(key,[])
            if not found:
                if required:raise ValueError("Missing parameter "+key)
                return default
            if len(found)!=1 or len(found[0])>maxlen:
                raise ValueError("Invalid parameter "+key)
            return found[0]
        if route=="/api/v1/prefectures":
            return {"status":"ok","items":list(self.prefs.values()),
                    "notice":"Official prefecture/basin source entry points, not proof that every named tributary flows within each prefecture."}
        if route=="/api/v1/watersheds":
            pref=exactly_one("pref")
            if pref not in self.prefs:raise ValueError("Unknown prefecture")
            return {"status":"ok","prefecture":pref,"items":self.basins.get(pref,[]),
                    "notice":"Watersheds mentioned in sources about this prefecture. No biology is assigned at watershed scope."}
        if route=="/api/v1/rivers":
            pref=exactly_one("pref");water=exactly_one("watershed")
            if pref not in self.prefs:raise ValueError("Unknown prefecture")
            if not any(x["watershed"]==water for x in self.basins.get(pref,[])):
                raise ValueError("Watershed is not a documented entry for this prefecture")
            out=[]
            for r in self.pref_rivers.get((pref,water),[]):
                item=self.river_map[r["identity_key"]]
                out.append({
                    "identity_key":item["identity_key"],"river_name":item["river_name"],
                    "watershed_name":item["watershed_name"],
                    "river_code_optional":item["river_code"],
                    "historical_contexts":item["survey_record_contexts"],
                    "individual_river_prefecture_mention":bool(r["individual_river_explicit_prefecture_mentions"]),
                    "river_location_in_prefecture":r["river_location_in_prefecture"]
                })
            return {"status":"ok","prefecture":pref,"watershed_name":water,"items":out,
                    "notice":"Only watershed membership in survey names. Listed rivers are not all confirmed to flow through the selected prefecture."}
        m=RIVER_ID.fullmatch(route)
        if m:
            key=m.group(1)
            if key not in self.river_map:raise ValueError("Unknown research river ID")
            category=exactly_one("category",required=False,default="fish",maxlen=30)
            if category not in GROUPS:raise ValueError("Unknown biological category")
            try:
                limit=int(exactly_one("limit",required=False,default="20",maxlen=4))
                offset=int(exactly_one("offset",required=False,default="0",maxlen=7))
            except (ValueError,TypeError) as e:raise ValueError("Invalid pagination") from e
            if limit<1 or limit>50 or offset<0 or offset>100000:
                raise ValueError("Pagination is outside supported limits")
            with closing(connect(self.db)) as c:
                return read(c,identity_key=key,category=category,limit=limit,offset=offset)
        raise KeyError("Unsupported research API path")

class Handler(BaseHTTPRequestHandler):
    app:AtlasData=None
    server_version="ResearchRiverAtlas/0.9"
    sys_version=""
    def respond(self,status,obj,typ="application/json; charset=utf-8"):
        if isinstance(obj,str):body=obj.encode("utf-8")
        else:body=json.dumps(obj,ensure_ascii=False,separators=(",",":")).encode("utf-8")
        if len(body)>MAX_RESPONSE_BYTES:
            body=b'{"status":"too_large","items":[]}'
            status=500
        self.send_response(status)
        self.send_header("Content-Type",typ)
        self.send_header("Content-Length",str(len(body)))
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("X-Frame-Options","DENY")
        self.send_header("Cache-Control","no-store")
        self.send_header("Referrer-Policy","no-referrer")
        # This is a LOCAL research server; interface needs inline JS/CSS.
        self.send_header("Content-Security-Policy","default-src 'self'; connect-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'none'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers();self.wfile.write(body)
    def do_GET(self):
        u=urlsplit(self.path)
        if u.path in ("/","/index.html"):
            return self.respond(200,self.app.html.read_text(encoding="utf-8"),"text/html; charset=utf-8")
        if not u.path.startswith("/api/v1/"):
            return self.respond(404,{"status":"not_found"})
        try:
            if len(u.query)>1500:raise ValueError("Oversized query")
            params=parse_qs(u.query,keep_blank_values=False,max_num_fields=12)
            obj=self.app.lookup(u.path,params)
            self.respond(200,obj)
        except (ValueError,UnicodeDecodeError) as exc:
            self.respond(400,{"status":"bad_request","reason":str(exc)[:120]})
        except KeyError:
            self.respond(404,{"status":"not_found"})
        except Exception:
            self.respond(500,{"status":"research_api_error"})
    def log_message(self,*args):
        pass

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",required=True);p.add_argument("--nav",required=True)
    p.add_argument("--html",default=str(HERE/"index.html"))
    p.add_argument("--host",default="127.0.0.1")
    p.add_argument("--port",type=int,default=8877)
    args=p.parse_args()
    if args.host not in ("127.0.0.1","localhost"):
        raise ValueError("Do not expose research server publicly")
    if not 0<=args.port<=65535:raise ValueError("Invalid port")
    app=AtlasData(args.db,args.nav,args.html)
    class AppHandler(Handler):pass
    AppHandler.app=app
    srv=ThreadingHTTPServer((args.host,args.port),AppHandler)
    print("Research only: http://127.0.0.1:"+str(srv.server_address[1])+"/",flush=True)
    try:srv.serve_forever(poll_interval=.1)
    except KeyboardInterrupt:pass
    finally:srv.server_close()

if __name__=="__main__":main()
