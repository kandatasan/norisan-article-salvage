#!/usr/bin/env python3
"""GET-only final verification of 23 CTN posts: 19 exact outputs + 4 untouched."""
import base64, hashlib, json, os, urllib.parse, urllib.request
from pathlib import Path
AFTER = [[2222,"ux-resale","f157449077971c7d7407519a3d54fba6e2ce402603a7c9d2986b6bcfb38b8c40","査定額に納得してから、売るか決めればOK。"],[2240,"ux-mitsumori","9e004747da93b15ec981521de26203ba19924ff9f0ec5a572ea925a8d42d6a6d","やり取りは最大3社。売却は査定額を見てから。"],[2329,"ux300h","d206b74cc65ade9b6701f219c363cb13f5d5a223ddbe123fa29db3ba869dbb92","やり取りは最大3社。電話の負担を抑えて比較。"],[2517,"ux-koukai","60dfdee41d23b9350d785f2b899397289bf5924cbb9ce0dea1ab7a42386934fe","売却は査定額に納得してから決めればOK。"],[2948,"lexus-ux-used","339883b44f2bbb27884284c80a47714ff1c5955009286e2b4ada544c005da6a4","やり取りは最大3社。電話の負担を抑えて比較。"],[2956,"lexus-ux-price","341d4e02b6d88b852ffbd9e9b14bbe4568b0cbc65d5718176511c973ec78a0b2","売却は、査定額を見てから決めればOK。"],[2962,"lexus-ux-discount","ba4e38b0594f2deb03509e2523a76ae9f0b308b94b4c726097443a7bba38120d","やり取りは最大3社。売却は納得してから。"],[3570,"lexus-ux-emotional-explorer","e2fa856b99e1239ac12ac37307dd4a5c7f61ca14a0b85d779be096e11cd27f11","やり取りは最大3社。買い替えは予算を見てから。"],[3601,"lexus-ux250h-used-vs-ux300h","b64f109c73c123ccb79b4bc83a06e13a46a9334c3e2dcc7162f8af2cbc9b9abf","売るかどうかは、査定額を見てから。"],[3604,"lexus-ux-vs-nx","4ae2c1e61aa8a935e439e48c603178703c4d57d958c693a17749121b2eaaa6b6","やり取りは最大3社。売却するかは金額を見てから。"],[3606,"lexus-ux-vs-lbx","3c28bbaa1941c1f04571d865df3c78b5c8d2ed936eb347eca8e57ede15501866","やり取りする買取店は最大3社。"],[3608,"lexus-lbx-regret","2819140868dec82a01b5d69d956a88ea06dacf18a6b6d1016022f99187a9753a","売却は、査定額に納得してから決めればOK。"],[3611,"lexus-lbx-options","cefccaeedaeb842c477fae8f6965aaaa3d359d701204ef00d77bbf5a61197031","売却は、査定額に納得してから決めればOK。"],[3614,"car-sell-high","73ffc46ebb16c32ea767c2a47e205a0d3687e7a4aff1534bbdb2c347851777a8","納得できる金額なら、そのとき売却を考える。"],[3835,"goodbuy","802817dac7379326a63f47d5cfbe6d74468fb1c4718637c564db26fa17181794","やり取りは最大3社。売るかどうかは金額を見てから。"],[3863,"lexus-lbx-cheap","f487736ddadb765e839782ce835d0f9640efe15f15ad5034f08f7b7c46707244","装備を削る前に、今の車の買取額も比較。"],[3936,"lexus-lbx-price","cccc15f226acf06ed0cc8eb73a033175aebd9aa2eb81c56bf9c195205e1f0c17","最大3社とのやり取り。売却は納得してから。"],[3767,"landcruiser-fj-price","5c53b28ddfe1c8a33460290a9948510f6c09c2a414bfefabb83b45d7e4d2f599","やり取りは最大3社。売却は査定額を見てから。"],[3816,"landcruiser-fj-cheap","c3dcc2158edfe030299b0001f4c3d578c9e8b98d8b030cac2d83901962257c70","買取店とのやり取りは最大3社。売却は納得してから。"]]
NOOPS = [[3774,"landcruiser-fj-review","ed2fac0d6c00e14e8b1eadc13f4bb6261f74e84bb9ced2f3fa6774ed3fbd6b27"],[3777,"landcruiser-fj-rear-seat","94ecf1d71a5e46d1744a58070b42dcf448d25a7c4dcf25726f33f47e5bb2dc05"],[3778,"landcruiser-fj-drawbacks","498d0992f9e815751972ab670f1902d6b1801f0efcce270756a59b35c9cd7613"],[4004,"tanto-model-history","55cc74c22f38e046b2018c6db2acfaba3a8abf204a6ce162f8f9d5d564d70307"]]
base='https://tsurikue.com/wp-json/wp/v2/posts/'
user=os.getenv('TSURIKUE_WP_USER')
pwd=os.getenv('TSURIKUE_WP_APP_PASSWORD')
if not user or not pwd: raise SystemExit('Missing WP GET credentials')
auth='Basic '+base64.b64encode((user+':'+pwd).encode()).decode()
out=[]
for record in AFTER+NOOPS:
    pid,slug,expected=record[:3]
    query=urllib.parse.urlencode({'context':'edit','_fields':'id,slug,status,content,title,featured_media'})
    req=urllib.request.Request(base+str(pid)+'?'+query,headers={'Authorization':auth,'User-Agent':'tsurikue-ctn-final-verify/1.0'})
    try:
        with urllib.request.urlopen(req,timeout=40) as r:row=json.load(r)
        raw=row['content']['raw']
        digest=hashlib.sha256(raw.encode()).hexdigest()
        identity=row['id']==pid and row['slug']==slug and row['status']=='publish'
        text_present=(len(record)==3 or (record[3] in raw and record[3] in row['content'].get('rendered','')))
        okay=identity and digest==expected and text_present
        out.append({'post_id':pid,'slug':slug,'check':'changed' if len(record)==4 else 'unchanged','matched':okay,'expected_sha':expected,'actual_sha':digest,'microcopy_present':text_present,'public_status':row['status']})
        print(('PASS ' if okay else 'FAIL ')+str(pid)+' '+slug + ('' if okay else ' actual='+digest+' expected='+expected+' microcopy='+str(text_present)),flush=True)
    except Exception as exc:
        out.append({'post_id':pid,'slug':slug,'matched':False,'error':str(exc)})
        print('ERROR '+str(pid)+' '+str(exc),flush=True)
Path('reports/ctn-final-verify').mkdir(parents=True,exist_ok=True)
Path('reports/ctn-final-verify/results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
success=sum(1 for row in out if row['matched'])
print('FINAL_RESULT',success,'/',len(out),flush=True)
if success!=23: raise SystemExit('FINAL_VERIFICATION_FAILED')
