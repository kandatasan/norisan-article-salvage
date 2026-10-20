#!/usr/bin/env python3
"""Research-only source-linked river directory on the fish atlas v20, NO fish inference."""
import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "outputs"
V20 = ROOT / "research-individual-v20" / "outputs" / "river_fish_general_editorial_stars_v20.zip"
V20QA = ROOT / "research-individual-v20" / "outputs" / "fish_general_star_qa_v20.json"
ZIP = OUT / "river_fish_47pref_official_name_directory_v21.zip"
QA = OUT / "river_official_directory_qa_v21.json"
EVIDENCE = OUT / "river_official_source_evidence_v21.csv"
CROSSWALK = OUT / "unresolved_195_exact_name_review_candidates_v21.csv"
UNKNOWN_WATER = "水系未確認（公式資料の川名）"

def records(filename):
    with (ROOT.parent / "river-fish" / filename).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def normalize(name, value):
    assert value and value.strip(), name
    return value.strip()

def data_bytes(obj):
    return (json.dumps(obj, ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8")

def source_rows():
    out=[]
    def add(pref,typ,water,name,code,url,source_id,context):
        assert typ in {"river","watershed"}
        pref=normalize("prefecture",pref);name=normalize("name",name)
        if typ=="watershed":
            assert water.strip()==name, (source_id, water, name)
        else:
            water=water.strip() or UNKNOWN_WATER
        assert url.startswith("https://") and len(source_id)>2
        out.append({"prefecture":pref,"type":typ,"watershed":water,"name":name,
                    "source_id":source_id,"source_url":url,"source_context":context,
                    "official_code_status":"UNLINKED","fish_evidence_status":"NO_FISH_EVIDENCE_FROM_THIS_SOURCE",
                    "physical_identity_status":"NOT_VERIFIED"})
    for x in records("multi_prefecture_source_mentions_v13.csv"):
        if x["evidence_kind"] not in {"river","watershed"}:continue
        add(x["prefecture"],x["evidence_kind"],x["watershed_explicit_in_source"],
            x["literal_name"],"",x["source_url"],x["evidence_id"],x["source_scope"])
    for x in records("remaining_32pref_source_mentions_v14.csv"):
        if x["label_type"] not in {"river","watershed"}:continue # planning region NOT a river
        add(x["prefecture"],x["label_type"],x["watershed_explicit_in_source"],
            x["name_as_written"],"",x["source_page_url"],x["mention_id"],x["source_document_scope"])
    for x in records("chugoku_second_class_watersheds_v10.csv"):
        add(x["prefecture"],"watershed",x["watershed_label_as_written"],
            x["watershed_label_as_written"],"",x["source_page_url"],x["record_id"],"second_class_watershed")
    for x in records("yamaguchi_river_municipality_mentions_v10.csv"):
        add(x["prefecture"],"river",x["watershed_label_as_written"],
            x["river_name_as_written"],"",x["source_url"],x["evidence_id"],x["source_document_context"])
    for x in records("river_registry_hiroshima_v01.csv"):
        add(x["prefecture"],"river",x["watershed"],x["river_name"],"",
            x["source_url"],x["river_id"],x["source_kind"]+"_source_staged")
    for x in records("river_name_mentions_hiroshima_v02.csv"):
        # watershed unverified, never place by guess.
        add(x["prefecture"],"river",x["watershed_name"] if x["watershed_review_status"]=="verified" else "",
            x["river_name"],"",x["source_url"],x["mention_id"],x["source_listing_class"]+"_unlinked_watershed")
    for x in records("research-individual-v21/gunma_official_river_mentions_v21.csv"):
        add(x["prefecture"],x["record_type"],x["watershed_name"],
            x["river_name"],"",x["source_url"],x["source_id"],x["source_review"])
    assert len(out)==len({x["source_id"] for x in out}),"unique original evidence IDs"
    return out

def build():
    OUT.mkdir(parents=True,exist_ok=True)
    upstream=json.loads(V20QA.read_text(encoding="utf-8"))
    sha=hashlib.sha256(V20.read_bytes()).hexdigest()
    assert sha==upstream["zip_sha256"],"v20 checksum does not match audited source"
    with ZipFile(V20) as z:
        assert z.testzip() is None
        atlas=json.loads(z.read("atlas.json"))
        master=json.loads(z.read("fish_master.json"))
        oldentries=atlas["entries"]
        oldlinks=atlas["links"]
        assert len(oldentries)==511 and len(master["taxa"])==639
        assert len(atlas["prefectures"])==47
        assert atlas["research_display_name_groups"]==511
        unknown_ids={l["river_id"] for l in oldlinks if l["prefecture"]==atlas["unknown_prefecture_bucket"]}
        assert len(unknown_ids)==195, len(unknown_ids)
        sources=source_rows()
        groups=defaultdict(list)
        for x in sources:
            assert x["prefecture"] in atlas["prefectures"],x
            k=(x["prefecture"],x["type"],x["watershed"],x["name"])
            groups[k].append(x)
        # Treat exact same pref+water+name as a DISPLAY group only, not an identified river.
        newentries=[]; newlinks=[]
        exact=defaultdict(set)
        for (pref,kind,water,name),evidence in sorted(groups.items()):
            digest=hashlib.sha256(("\x00".join((pref,kind,water,name))).encode()).hexdigest()[:24]
            id="official21_"+digest
            assert id not in {e["id"] for e in oldentries}
            entry={
                "id":id,"water":water,"name":name,"kind":"official_"+kind+"_name_only_v21",
                "region":None,"old":{},"edna":None,"river_code":None,
                "is_a_verified_individual_physical_river":False,
                "source_only_name_evidence_v21":True,
                "source_label_type":kind,
                "source_prefecture":pref,
                "source_evidence_ids":sorted(x["source_id"] for x in evidence),
                "official_source_urls":sorted({x["source_url"] for x in evidence}),
                "source_identity_status":"NAME_MENTION_ONLY_NO_PHYSICAL_RIVER_IDENTITY_OR_FISH_JOIN",
                "fish_occurrences_linked_from_this_source":0,
            }
            newentries.append(entry)
            newlinks.append({"prefecture":pref,"water":water,"river_id":id})
            if kind=="river" and water!=UNKNOWN_WATER:exact[(water,name)].add(pref)
        assert len(newentries)==len(groups)
        assert len({e["id"] for e in newentries})==len(newentries)
        assert len({e["prefecture"] for e in newlinks})==47
        # Original source-fish entries/links are strictly retained (no auto-assignment).
        atlas["entries"]=oldentries+newentries
        atlas["links"]=oldlinks+newlinks
        assert atlas["entries"][:511]==oldentries
        assert atlas["links"][:len(oldlinks)]==oldlinks
        atlas["source_only_directory_v21"]={
            "source_rows":len(sources),"display_name_groups":len(newentries),
            "river_name_groups":sum(e["source_label_type"]=="river" for e in newentries),
            "watershed_name_groups":sum(e["source_label_type"]=="watershed" for e in newentries),
            "prefectures_with_source_name_navigation":47,
            "old_fish_evidence_groups_unchanged":511,
            "old_unknown_location_groups_unresolved":195,
            "no_new_fish_records_from_technical_river_sources":True,
            "national_code_and_river_identity_not_resolved":True,
        }
        old_id={e["id"]:e for e in oldentries}
        candidates=[]
        for id in sorted(unknown_ids):
            obj=old_id[id]
            hits=sorted(exact.get((obj["water"],obj["name"]),[]))
            if hits:
                candidates.append({"old_river_id":id,"recorded_water":obj["water"],
                                   "recorded_river_name":obj["name"],
                                   "prefecture_candidates":"|".join(hits),
                                   "status":"DO_NOT_AUTO_LINK_PHYSICAL_IDENTITY_UNVERIFIED",
                                   "reason":"exact watershed+river label in provincial source; segment/location still needs verification"})
        outbuf=io.StringIO()
        w=csv.DictWriter(outbuf,fieldnames=["old_river_id","recorded_water","recorded_river_name",
            "prefecture_candidates","status","reason"],lineterminator="\n")
        w.writeheader();w.writerows(candidates)
        CROSSWALK.write_text(outbuf.getvalue(),encoding="utf-8-sig")
        evbuf=io.StringIO()
        ew=csv.DictWriter(evbuf,fieldnames=list(sources[0]),lineterminator="\n")
        ew.writeheader();ew.writerows(sources)
        EVIDENCE.write_text(evbuf.getvalue(),encoding="utf-8-sig")
        with ZipFile(ZIP,"w",compression=ZIP_DEFLATED,compresslevel=8) as out:
            for path in z.namelist():
                data=z.read(path)
                if path=="atlas.json":data=data_bytes(atlas)
                elif path=="index.html":
                    html=data.decode("utf-8")
                    # Insert source-only display without changing any existing fish-to-river evidence.
                    injection="""function sourceOnlyDetail(e){
 $(\"heading\").textContent=(e.source_label_type===\"watershed\"?\"水系の掲載情報｜\":e.water+\"水系｜\")+e.name;
 empty($(\"attribution\"));
 $(\"attribution\").appendChild(node(\"span\",\"県の公式資料に名前が掲載されています。魚の調査記録とはまだ接続していません。\"));
 for(const [i,url] of e.official_source_urls.entries()){
  const a=node(\"a\",\" 公式資料\"+(i+1));a.href=url;a.target=\"_blank\";a.rel=\"noopener noreferrer\";$(\"attribution\").appendChild(a)
 }
 $(\"fishsearch\").value=\"\";$(\"fishsearch\").disabled=true;
 $(\"count\").textContent=\"魚の調査記録：未紐付け\";
 empty($(\"fishlist\"));
 $(\"fishlist\").appendChild(node(\"p\",e.source_label_type===\"watershed\"?
  \"水系名だけが公式資料で確認されています。個別の河川名と魚の記録はまだ未接続です。\":
  \"この川の名前は公式資料にありますが、魚の調査記録はまだ未接続です。魚がいないという意味ではありません。\",\"notice\"));
 $(\"more\").hidden=true;
}
"""
                    marker="async function chooseRiver(){"
                    assert html.count(marker)==1,"viewer change needs human review"
                    html=html.replace(marker,injection+"\n"+marker)
                    needle=" const e=current;\n $(\"heading\")"
                    assert html.count(needle)==1,"chooseRiver insertion anchor changed"
                    html=html.replace(needle," const e=current;\n if(e.source_only_name_evidence_v21){sourceOnlyDetail(e);return;}\n $(\"fishsearch\").disabled=false;\n $(\"heading\")")
                    render="function render(){\n if(!current)return;"
                    assert html.count(render)==1,"render insertion anchor changed"
                    html=html.replace(render,"function render(){\n if(!current)return;\n if(current.source_only_name_evidence_v21){sourceOnlyDetail(current);return;}")
                    html=html.replace("v0.20","v0.21")
                    note='<p class="note">研究用試作。511は元調査資料の河川名グループ数で'
                    assert html.count(note)==1
                    html=html.replace(note,'<p class="note">公式資料で名前だけ確認した川・水系を追加。魚の記録がない表示は「まだ未接続」であり、魚が生息しないという意味ではありません。水系未確認の川は専用の項目へ分けています。既存の魚記録511グループと全国の川の本数を混同しません。</p>\n'+note)
                    data=html.encode("utf-8")
                elif path=="readme_preview.txt":
                    data=("全国河川魚類図鑑v21 研究版。都道府県→水系→川名の公式掲載を新しく接続。\n"
                          "元の魚類調査用511河川名グループは変更・自動結合していません。\n"
                          "魚データのない公式掲載名には魚がいないのではなく「調査記録は未接続」と表示。\n"
                          "195所在県未確定は引き続き未確定。公式資料への部分一致は自動同定しません。\n"
                          "元資料・eDNA・魚星評価の区分は維持。本番WordPressには未反映。\n").encode("utf-8")
                out.writestr(path,data)
            out.writestr("river_official_source_evidence_v21.csv",evbuf.getvalue().encode("utf-8-sig"))
            out.writestr("unresolved_195_exact_name_review_candidates_v21.csv",outbuf.getvalue().encode("utf-8-sig"))
        with ZipFile(ZIP) as chk:
            assert chk.testzip() is None
            a=json.loads(chk.read("atlas.json"))
            assert a["entries"][:511]==oldentries
            assert len(a["entries"])==511+len(newentries)
            assert len(a["links"])==len(oldlinks)+len(newlinks)
            assert "sourceOnlyDetail" in chk.read("index.html").decode()
        qa={
            "version":"v21","research_only":True,"v20_source_sha256":sha,
            "original_fish_evidence_groups":511,"original_undetermined_prefecture_groups":195,
            "new_source_evidence_rows":len(sources),"new_source_only_navigation_groups":len(newentries),
            "new_river_name_groups":sum(e["source_label_type"]=="river" for e in newentries),
            "new_watershed_name_groups":sum(e["source_label_type"]=="watershed" for e in newentries),
            "new_name_groups_total_with_original":511+len(newentries),
            "navigable_official_source_prefectures":len({e["prefecture"] for e in newlinks}),
            "candidate_not_approved_old_unknown_group_exact_pair_matches":len(candidates),
            "new_fish_observations":0,"original_fish_taxon_source_labels":len(master["taxa"]),
            "old_fish_evidence_associations_unchanged":True,
            "no_unverified_prefecture_autofill":True,
            "no_wp_or_live_api_changes":True,
            "zip":ZIP.name,"zip_sha256":hashlib.sha256(ZIP.read_bytes()).hexdigest(),
        }
        QA.write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(qa,ensure_ascii=False))
if __name__=="__main__":
    build()
