// Exercise the existing browser interaction suite with browser URL query semantics.
const fs=require('fs'),path=require('path');
const filename=path.join(__dirname,'../source-connections-v01/test_widget_runtime.cjs');
const original=fs.readFileSync(filename,'utf8');
const before="String(url).replace('/river-fish-atlas/data/','')";
const after="new URL(String(url),'https://atlas.test/').pathname.replace('/river-fish-atlas/data/','')";
if(original.split(before).length!==2)throw Error('Review the runtime suite fetch adapter');
eval(original.replace(before,after));
