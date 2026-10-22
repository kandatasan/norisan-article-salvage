const fs=require('fs'),path=require('path'),assert=require('assert');
const {JSDOM,VirtualConsole}=require(process.env.JSDOM_MODULE||'jsdom');
const directory=process.argv[2],htmlFile=process.argv[3];
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn){for(let i=0;i<250;i++){if(fn())return;await sleep(10)}throw Error('Widget did not reach the expected state')}
(async()=>{
 const errors=[],consoleCapture=new VirtualConsole();consoleCapture.on('jsdomError',e=>errors.push(String(e)));
 const dom=new JSDOM(fs.readFileSync(htmlFile,'utf8'),{
  url:'https://atlas.test/',runScripts:'dangerously',virtualConsole:consoleCapture,pretendToBeVisual:true,
  beforeParse(w){w.HTMLElement.prototype.scrollIntoView=function(){};w.fetch=async url=>{
   const file=path.join(directory,String(url).replace('/river-fish-atlas/data/',''));
   return fs.existsSync(file)?{ok:true,json:async()=>JSON.parse(fs.readFileSync(file,'utf8'))}:{ok:false,status:404};
  }}
 });
 const w=dom.window,root=w.document.getElementById('tsurikue-river-atlas-inline-v26').shadowRoot;
 const $=id=>root.getElementById(id),change=id=>$(id).dispatchEvent(new w.Event('change'));
 const input=(id,value)=>{$(id).value=value;$(id).dispatchEvent(new w.Event('input'))};
 const select=(id,value)=>{$(id).value=value;change(id)};
 await until(()=>$('pref').options.length>40);
 select('pref','広島県');select('water','黒瀬川');
 const option=[...$('river').options].find(x=>x.textContent==='竹保川【資料に魚名掲載】');assert(option);
 select('river',option.value);await until(()=>$('fishlist').querySelector('h3'));
 assert.deepStrictEqual([...$('fishlist').querySelectorAll('h3')].map(x=>x.textContent),['オイカワ','ドンコ']);
 assert($('fishlist').textContent.includes('底生生物調査での魚類記録'));
 assert(!$('fishlist').textContent.includes('ミナミメダカ'));
 $('atlasTabRiver').click();input('riverSearchV25','竹保川');
 await until(()=>$('riverSearchResultsV25').querySelector('button'));
 assert($('riverSearchResultsV25').textContent.includes('県・市の公開資料に魚名掲載'));
 $('riverFishOnlyV25').checked=true;change('riverFishOnlyV25');
 await until(()=>$('riverSearchResultsV25').querySelector('button'));
 assert($('riverSearchResultsV25').textContent.includes('竹保川'));
 $('atlasTabFish').click();input('reverseFishV24','ドンコ');
 await until(()=>$('reverseResultsV24').querySelector('strong'));
 for(const expand of [...$('reverseResultsV24').querySelectorAll('button')].filter(b=>b.textContent==='さらに河川名の記録を見る'))while(!expand.hidden)expand.click();
 const back=[...$('reverseResultsV24').querySelectorAll('button')].find(b=>b.textContent.includes('黒瀬川水系・竹保川'));assert(back);back.click();
 await until(()=>$('fishlist').textContent.includes('ドンコ'));
 select('pref','鳥取県');select('water','日野川');
 const hoshoji=[...$('river').options].find(x=>x.textContent==='法勝寺川【資料に魚名掲載】');assert(hoshoji);select('river',hoshoji.value);
 await until(()=>$('fishlist').textContent.includes('資料の確認種表'));
 const names=[...$('fishlist').querySelectorAll('h3')].map(x=>x.textContent);
 assert(names.includes('アユ'));assert(names.length>=7,'Existing historical fish records should remain');
 assert.strictEqual(errors.length,0,errors.join('\n'));
 console.log('SOURCE_WIDGET_DOM_QA_OK',JSON.stringify({riverSearch:true,fishOnlyFilter:true,reverseNavigation:true,heldFishExcluded:true,existingDataRetained:true}));
 dom.window.close();
})().catch(e=>{console.error(e);process.exitCode=1});
