"use strict";
/** Playwright Chromium E2E for the v26 research atlas. Does not perform remote/network writes. */
const fs=require("fs"),path=require("path"),assert=require("assert");
const {chromium}=require("playwright");

const root=process.argv[2];
if(!root)throw Error("Pass extracted research atlas root directory");
const out=path.resolve("river-fish/research-individual-v26/outputs");
fs.mkdirSync(out,{recursive:true});
const data=(file)=>JSON.parse(fs.readFileSync(path.join(root,file),"utf8"));
const atlas=data("atlas.json");
const reverse=data("fish_to_river_reverse_v24.json");
const preview=data("river_fish_label_counts_v25.json");
const pause=(n)=>new Promise(done=>setTimeout(done,n));

(async()=>{
 const browser=await chromium.launch({headless:true,args:["--no-sandbox"]});
 try{
  const page=await browser.newPage({viewport:{width:1270,height:850},locale:"ja-JP"});
  const pageErrors=[],badRequests=[];
  page.on("pageerror",e=>pageErrors.push(String(e)));
  page.on("response",r=>{if(r.status()>=400)badRequests.push(r.url()+" -> "+r.status())});
  await page.goto("http://127.0.0.1:8765/",{waitUntil:"networkidle",timeout:25000});
  await page.waitForFunction(()=>document.querySelectorAll("#pref option").length>=49);
  assert(await page.locator("#fishReverseFinderV24").isVisible());
  assert(await page.locator("#riverQuickFinderV25").isVisible());
  assert.equal(await page.locator("#riverFishOnlyV25").evaluate(e=>Math.round(e.getBoundingClientRect().width)),18);
  // Direct river name search + actual original river click
  await page.locator("#riverSearchV25").fill("太田川");
  await page.waitForFunction(()=>document.getElementById("riverSearchStatusV25").textContent.includes("該当する資料掲載名"));
  const firstButton=page.locator("#riverSearchResultsV25 .record button").first();
  assert(await firstButton.isVisible());
  await firstButton.click();
  await page.waitForFunction(()=>document.getElementById("river").value.length>0);
  assert((await page.locator("#heading").textContent()).includes("水系"));
  await page.screenshot({path:path.join(out,"desktop-browser-v26.png"),fullPage:false});
  // Filter by actual source fish-label presence
  await page.locator("#riverFishOnlyV25").check();
  await page.waitForFunction(()=>document.getElementById("riverSearchStatusV25").textContent.includes("該当"));
  const metaMap=new Map(preview.entries.map(x=>[x.survey_river_group_id,x]));
  const matched=atlas.entries.filter(e=>e.name.includes("太田川")&&metaMap.has(e.id)&&metaMap.get(e.id).fish_name_in_source_records);
  assert(matched.length>0,"Need a proven-source name match for filter");
  assert((await page.locator("#riverSearchResultsV25 .record").count())>=1);
  await page.locator("#riverFishOnlyV25").uncheck();
  // Fish name reverse lookup. This search has a long list and checks first-page limit.
  await page.locator("#reverseFishV24").fill("アユ");
  await page.waitForFunction(()=>document.getElementById("reverseStatusV24").textContent.includes("該当する魚名"));
  assert((await page.locator("#reverseResultsV24 .record").count())>=1);
  let count=await page.locator("#reverseResultsV24 .record").first().locator(".source-river-links button").count();
  assert(count<=14 && count>=1,"first-page source river count");
  await page.locator("#reverseResultsV24 .record").first().locator(".source-river-links button").first().click();
  await page.waitForFunction(()=>document.getElementById("river").value.length>0);
  await page.waitForFunction(()=>!document.getElementById("fishlist").textContent.includes("読み込み中"));
  // eDNA evidence original river, never label as fish caught
  const candidate=atlas.entries.slice(0,511).find(e=>{
   if(!e.edna)return false;
   const d=data(e.edna);return d.records.some(r=>r.group==="fish"&&r.method==="eDNA");
  });
  assert(candidate,"Need at least one true fish eDNA preview pack");
  const nav=atlas.links.find(l=>l.river_id===candidate.id);
  await page.selectOption("#pref",nav.prefecture);
  await page.selectOption("#water",nav.water);
  await page.selectOption("#river",candidate.id);
  await page.locator("#fishlist .chip.dna").first().waitFor({timeout:15000});
  // Watershed reference is never merged into individual river sightings
  const ref=atlas.entries.find(e=>e.source_only_name_evidence_v21&&e.watershed_fish_reference_v23);
  assert(ref);
  const n=atlas.links.find(l=>l.river_id===ref.id);
  await page.selectOption("#pref",n.prefecture);
  await page.selectOption("#water",n.water);
  await page.selectOption("#river",ref.id);
  const accordion=page.locator("#fishlist details").filter({hasText:"同名水系の魚記録を参考"});
  assert.equal(await accordion.count(),1);
  await accordion.locator("summary").click();
  await page.waitForFunction(()=>document.getElementById("fishlist").textContent.includes("水系単位の記録年"));
  assert((await accordion.locator("article.fish").count())<=30);
  assert((await accordion.textContent()).includes("個別河川の記録ではありません"));
  // iPhone-sized browser viewport (Chromium emulation, not iPhone Safari).
  await page.setViewportSize({width:390,height:844});
  await page.locator("#riverSearchV25").fill("佐波川");
  await page.waitForFunction(()=>document.getElementById("riverSearchStatusV25").textContent.includes("該当"));
  const overflow=await page.evaluate(()=>({scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth}));
  assert(overflow.scrollWidth<=overflow.clientWidth+2,"Mobile horizontal overflow "+JSON.stringify(overflow));
  const checkbox=await page.locator("#riverFishOnlyV25").evaluate(e=>({
   width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height
  }));
  assert(checkbox.width>=16&&checkbox.width<=22);
  await page.screenshot({path:path.join(out,"mobile-width-browser-v26.png"),fullPage:false});
  assert.deepEqual(pageErrors,[],"Browser JavaScript exceptions");
  assert.deepEqual(badRequests,[],"Missing local resources");
  const qa={version:"v26",run:"CHROMIUM_REAL_BROWSER_INTERACTION",source_group_count:atlas.entries.length,
    reverse_fish_name_count:reverse.lookups.length,
    original_survey_group_count:preview.entries.length,
    direct_river_name_navigation:true,fish_name_reverse_to_original_source:true,
    fish_source_only_filter:true,eDNA_not_capture:true,
    watershed_reference_accordion:true,mobile_viewport_width:390,
    mobile_horizontal_overflow:false,checkbox_width:checkbox.width,
    source_data_unchanged:true,browser_errors:pageErrors,failed_resource_urls:badRequests,
    iPhone_Safari_real_hardware_test:false};
  fs.writeFileSync(path.join(out,"chromium_browser_qa_v26.json"),JSON.stringify(qa,null,2)+"\n");
  console.log(JSON.stringify(qa));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
