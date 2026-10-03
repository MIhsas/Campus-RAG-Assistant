// Independent unit-level execution of the real inline JS with a minimal DOM/fetch stub.
// Complements browser verification; it does not claim visual/browser coverage.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const html = fs.readFileSync(path.resolve(__dirname, '../../../step2_code/backend/src/campus_assistant/static/search.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
class Element {
  constructor(tag='div'){this.tag=tag;this.children=[];this.listeners={};this.style={};this.disabled=false;this.value='';this.text='';}
  appendChild(c){this.children.push(c);return c;}
  addEventListener(e,fn){this.listeners[e]=fn;}
  set textContent(v){this.text=String(v);this.children=[];}
  get textContent(){return this.text+this.children.map(c=>c.textContent).join('');}
  set innerHTML(v){this.text=String(v);this.children=[];}
}
function setup(){
  const ids=Object.fromEntries(['query-input','search-btn','status-area','results-area'].map(id=>[id,new Element()]));
  const requests=[];
  const context={document:{getElementById:id=>ids[id],createElement:t=>new Element(t),createTextNode:t=>{const e=new Element();e.textContent=t;return e;}},fetch:(url,options)=>{
    if(!options)return Promise.resolve({ok:true,json:async()=>({status:'ready',parsed_count:1,synthetic_count:1,chunk_count:1,indexed_chunk_count:1,errors:[]})});
    return new Promise((resolve,reject)=>requests.push({body:JSON.parse(options.body),resolve,reject}));
  }};
  vm.runInNewContext(script,context);
  return {ids,requests,submit(q){ids['query-input'].value=q;ids['query-input'].listeners.keydown({key:'Enter'});}};
}
const flush=()=>new Promise(resolve=>setImmediate(resolve));
const ok=()=>({ok:true,status:200,json:async()=>({query_tokens:['x'],hits:[],indexed_chunk_count:1})});
const findButton=e=>e.tag==='button'?e:e.children.map(findButton).find(Boolean);
(async()=>{
  for(const failure of [false,true]){
    const s=setup();s.submit('A');s.submit(' ');
    assert.equal(s.requests.length,1);assert.equal(s.ids['search-btn'].disabled,false);
    failure?s.requests[0].reject(new Error('old failure')):s.requests[0].resolve(ok());await flush();
    assert.match(s.ids['results-area'].textContent,/请输入搜索关键词/);assert.equal(s.ids['search-btn'].disabled,false);
    s.ids['query-input'].value='B';s.ids['search-btn'].listeners.click();
    assert.equal(s.requests[1].body.query,'B');s.requests[1].resolve(ok());await flush();
    assert.match(s.ids['results-area'].textContent,/查询：B/);assert.equal(s.ids['search-btn'].disabled,false);
  }
  for(const failure of [false,true]){
    const s=setup();s.submit('A');s.submit('B');
    failure?s.requests[0].reject(new Error('old failure')):s.requests[0].resolve(ok());await flush();
    assert.equal(s.ids['search-btn'].disabled,true);assert.match(s.ids['results-area'].textContent,/搜索中/);
    s.requests[1].resolve(ok());await flush();assert.equal(s.ids['search-btn'].disabled,false);assert.match(s.ids['results-area'].textContent,/查询：B/);
  }
  for(const kind of ['http','json','network']){
    const s=setup();s.submit('original');
    if(kind==='network')s.requests[0].reject(new Error('network'));
    else s.requests[0].resolve(kind==='http'?{ok:false,status:500}:{ok:true,status:200,json:async()=>{throw new Error('json');}});
    await flush();s.ids['query-input'].value='draft';findButton(s.ids['results-area']).listeners.click();
    assert.equal(s.requests[1].body.query,'original');s.requests[1].resolve(ok());await flush();
    assert.match(s.ids['results-area'].textContent,/查询：original/);assert.equal(s.ids['query-input'].value,'draft');
  }
  console.log('PASS: 7 async scenarios (blank late success/failure, A/B late success/failure, HTTP/JSON/network retry)');
})().catch(e=>{console.error(e);process.exitCode=1;});
