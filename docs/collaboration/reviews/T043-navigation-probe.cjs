// Astra independent DOM/fetch-stub probe; not browser evidence.
// Reuses existing fixtures in memory; never edits product or executor scripts.
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const root = path.resolve(__dirname, '../../..');
const rows = [];
function fixture(page) {
  const file = path.join(root, 'step2_code/backend/scripts/check-' + page + '-behavior.cjs');
  let source = fs.readFileSync(file, 'utf8').split('(async () => {')[0];
  // Existing suites omit the new checkbox entirely. Model its actual static
  // HTML default and the static navigation href, then execute the real script.
  const nav = page === 'ask' ? 'nav-search' : 'nav-ask';
  const dest = page === 'ask' ? '/search' : '/ask';
  source = source.replace('  const requests = [];',
    `  ids['include-unknown-type'] = new Element('input');
       ids['include-unknown-type'].checked = true;
       ids['${nav}'].href = '${dest}';
       const requests = [];`);
  const mod = new Module(file, module);
  mod.filename = file;
  mod.paths = Module._nodeModulePaths(path.dirname(file));
  mod._compile(source + '\nmodule.exports = {setup, flush, okResponse};', file);
  return {...mod.exports, nav};
}
function check(name, expected, actual) {
  rows.push({name, expected, actual, pass:JSON.stringify(expected) === JSON.stringify(actual)});
}
(async () => {
  for (const page of ['search', 'ask']) {
    const f = fixture(page);
    const s = f.setup('?query=original&student_type=%E6%9C%AC%E7%A7%91&include_unknown_type=0', {
      statusOptions:{campus:[], student_type:['本科'], admission_year:[]}
    });
    await f.flush();
    check(page + ': URL restores checkbox', false, s.ids['include-unknown-type'].checked);
    check(page + ': immediate reverse navigation keeps strict', '0',
      new URL(s.ids[f.nav].href, 'http://local').searchParams.get('include_unknown_type'));
    s.submit('original');
    check(page + ': explicit request preserves strict', false,
      s.requests[0].body.include_unknown_student_type);
    s.requests[0].resolve(f.okResponse({include_unknown_student_type:false,
      filters:{student_type:'本科',campus:null,admission_year:null,as_of_date:null}}));
    await f.flush();
    s.ids['include-unknown-type'].checked = true;
    check(page + ': submitted navigation ignores later control edits', '0',
      new URL(s.ids[f.nav].href, 'http://local').searchParams.get('include_unknown_type'));
  }
  const f = fixture('ask');
  const s = f.setup();
  const old = await f.okResponse({query:'old strict', filters:{student_type:'本科'}}).json();
  s.state.storageRef.campus_ask_history_v1 = JSON.stringify([{id:'old',saved_at:'historical',
    query:'old strict',filters:{student_type:'本科'},mode:'bm25',answer_mode:'extractive',
    status:'evidence_only',result:old}]);
  await f.flush();
  s.submit('current reference');
  s.requests[0].resolve(f.okResponse({query:'current reference',include_unknown_student_type:true}));
  await f.flush();
  const buttons = [];
  function walk(e){if(e.tag==='button') buttons.push(e); for(const c of e.children) walk(c);}
  walk(s.ids['history-list']);
  const count = s.requests.length;
  buttons.find(b => b.textContent==='查看').listeners.click();
  check('old history restores without requests', count, s.requests.length);
  check('old history is labelled strict', true, s.ids['results-area'].textContent.includes('按当时 strict'));
  check('old history navigation uses historical strict', '0',
    new URL(s.ids[f.nav].href,'http://local').searchParams.get('include_unknown_type'));
  const result = {level:'DOM/fetch stub; real product scripts; no model calls',rows,
    failures:rows.filter(r=>!r.pass).length};
  fs.writeFileSync(path.join(__dirname,'T043-navigation-probe.json'), JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify(result,null,2));
  process.exitCode = result.failures ? 1 : 0;
})().catch(e=>{console.error(e);process.exitCode=1;});
