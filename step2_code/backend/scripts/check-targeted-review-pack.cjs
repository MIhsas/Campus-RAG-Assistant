// T042: behavior checks for the offline targeted review pack (DOM/JS stub).
// NOT a real browser run — evidence level: 代码/桩依据.
// Verifies: 8 cards with domain-separated IDs; all opinions default 未复核;
// no localStorage/fetch/external resources; export produces a NEW JSON with
// input identity SHAs; simulated answer:q10 需修订+P3说明 exports while
// revision:q10 and the other 6 stay 未复核; default pack carries no test
// selections. With --write-sample <path> it writes the simulated export as a
// demo file (record_title carries "模拟操作测试" — NOT a real review).
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const packArg = process.argv.indexOf('--pack-dir');
const outDir = packArg >= 0 ? path.resolve(process.argv[packArg + 1]) : path.resolve(__dirname, '../.cache/human-review/T042-v1');
const html = fs.readFileSync(path.join(outDir, 'review.html'), 'utf8');
const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/);
if (!scriptMatch) { console.error('FAIL: no inline script'); process.exit(1); }
// 预扫描：真实 API/外链模式（排除内联脚本与正文提及语——"无 localStorage" 不算使用）
const outsideScript = html.replace(/<script>[\s\S]*?<\/script>/g, '');
if (/(src|href)\s*=\s*["']https?:/i.test(outsideScript) || /localStorage\s*[.\[]/.test(outsideScript) || /\bfetch\s*\(/.test(outsideScript)) {
  console.error('FAIL: external resource / storage API usage detected');
  process.exit(1);
}

class Element {
  constructor(tag = 'div') {
    this.tag = tag;
    this.children = [];
    this.listeners = {};
    this.attrs = {};
    this.value = '';
    this.textContent = '';
    this._innerHTML = '';
    this.className = '';
    this.classList = {
      toggle: (cls, force) => {
        const parts = new Set(this.className.split(/\s+/).filter(Boolean));
        const want = force === undefined ? !parts.has(cls) : !!force;
        if (want) parts.add(cls); else parts.delete(cls);
        this.className = [...parts].join(' ');
      },
      add: c => { if (!this.className.split(/\s+/).includes(c)) this.className += ' ' + c; },
      remove: c => { this.className = this.className.split(/\s+/).filter(x => x && x !== c).join(' '); },
    };
  }
  appendChild(c) { this.children.push(c); return c; }
  removeChild(c) { this.children = this.children.filter(x => x !== c); }
  addEventListener(e, fn) { (this.listeners[e] = this.listeners[e] || []).push(fn); }
  click() { (this.listeners.click || []).forEach(fn => fn({})); }
  setAttribute(k, v) { this.attrs[k] = v; }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  set innerHTML(v) { this._innerHTML = String(v); this.children = []; }
  get innerHTML() { return this._innerHTML; }
  matches(sel) {
    if (sel.startsWith('.')) return this.className.split(/\s+/).filter(Boolean).includes(sel.slice(1));
    return this.tag === sel;
  }
  querySelectorAll(sel) {
    const out = [];
    const walk = e => { for (const c of e.children) { if (c.matches && c.matches(sel)) out.push(c); walk(c); } };
    walk(this);
    return new NodeListLike(out); // 真实 NodeList 形态（非 Array、无 some/map）
  }
}

class Blob {
  constructor(parts, opts) { this.parts = parts; this.opts = opts; this.size = (parts[0] || '').length; }
  text() { return Promise.resolve(this.parts.join('')); }
}

class NodeListLike {
  constructor(items) {
    this._items = items;
    this.length = items.length;
    items.forEach((e, i) => { this[i] = e; });
  }
  item(i) { return this[i] || null; }
  forEach(cb) { this._items.forEach((e, i) => cb(e, i, this)); }
  [Symbol.iterator]() { return this._items[Symbol.iterator](); }
}

const ids = {};
const byId = id => ids[id] || (ids[id] = new Element('div'));

let capturedDownload = null;
const documentStub = {
  getElementById: id => byId(id),
  createElement: t => new Element(t),
  querySelectorAll: sel => {
    const out = [];
    Object.values(ids).forEach(e => { if (e.matches(sel)) out.push(e); out.push(...e.querySelectorAll(sel)); });
    return new NodeListLike(out);
  },
  body: new Element('body'),
};
const urlStub = {
  createObjectURL: blob => { capturedDownload = blob; return 'blob:stub'; },
  revokeObjectURL: () => {},
};

const context = {
  document: documentStub,
  Blob,
  URL: urlStub,
  console,
  Date,
  JSON,
  Object,
  Array,
  Set,
  Math,
  window: {},
  localStorage: { getItem: () => { throw new Error('localStorage must not be used'); },
                  setItem: () => { throw new Error('localStorage must not be used'); } },
  fetch: () => { throw new Error('fetch must not be used (offline pack)'); },
};
vm.runInNewContext(scriptMatch[1], context);

let passed = 0;
const ok = (cond, msg) => {
  if (!cond) { console.error('FAIL:', msg); process.exit(1); }
  passed++;
  console.log('OK  ', msg);
};

const exportBtn = byId('export-btn');
const cards = Array.from(documentStub.querySelectorAll('.card'));
ok(cards.length === 8, `8 cards rendered (got ${cards.length})`);
const cardIds = cards.map(c => c.getAttribute('data-card-id'));
ok(cardIds.join(',') === 'revision:q08,revision:q10,revision:u03,revision:u04,answer:q08,answer:q10,answer:u03,answer:u04',
   'domain-separated stable IDs in order');
ok(byId('zones').children.length > 0, 'two zones rendered');

// NodeList shape guard (T036-R2 lesson kept)
const probe = cards[0].querySelectorAll('.op-sel');
ok(probe && !Array.isArray(probe) && typeof probe.some === 'undefined' && typeof probe.map === 'undefined',
   '.op-sel query returns NodeList-shaped non-Array (no some/map)');
ok(typeof probe.forEach === 'function' && typeof probe.item === 'function' && typeof probe[Symbol.iterator] === 'function',
   'NodeList has forEach/item/iterator');

// 1) default export: all 8 未复核, no prefilled reviewer/date/title
exportBtn.click();
ok(capturedDownload, 'export produced a download blob');
capturedDownload.text().then(text => {
  const rec = JSON.parse(text);
  ok(rec.record_type === 'targeted_review_record', 'record_type is targeted_review_record');
  ok(rec.items.length === 8, 'export covers exactly 8 items');
  ok(rec.items.every(i => i.opinion === '未复核'), 'all 8 default 未复核');
  ok(rec.items.every(i => i.comment === ''), 'all comments empty by default');
  ok(rec.reviewer === '' && rec.review_date === '' && rec.record_title === '',
     'reviewer/review_date/record_title default empty (不预填签名/日期)');
  ok(rec.tally['未复核'] === 8, 'tally counts 8 unreviewed');
  ok(rec.pack_identity.inputs.questions.sha256.startsWith('4e39229e'), 'questions SHA in export');
  ok(rec.pack_identity.inputs.live_answers_full.sha256.length === 64, 'live answers SHA in export');
  ok(rec.review_scope.indexOf('8 项') >= 0, 'review_scope present');

  // 2) simulate ONLY answer:q10 需修订 + P3 comment
  const q10 = cards.find(c => c.getAttribute('data-card-id') === 'answer:q10');
  const rows = q10.querySelectorAll('.opinion-row');
  ok(rows.length === 1, 'exactly one top-level opinion row per card (8 total, no per-citation spam)');
  const sel = rows[0].querySelectorAll('select')[0];
  const ta = rows[0].querySelectorAll('textarea')[0];
  sel.value = '需修订';
  (sel.listeners.change || []).forEach(fn => fn({}));
  ta.value = 'P3「不纳入上述组成比例」系推断，请核实（模拟操作测试）';
  (ta.listeners.input || []).forEach(fn => fn({}));
  byId('record-title').value = '模拟操作测试（MiMo 演示导出，非真实复核结论）';
  byId('reviewer').value = '（模拟测试，非真人复核）';
  capturedDownload = null;
  exportBtn.click();
  return capturedDownload.text();
}).then(text2 => {
  const rec2 = JSON.parse(text2);
  ok(rec2.record_title.indexOf('模拟操作测试') >= 0, 'simulated sample labelled 模拟操作测试');
  const revised = rec2.items.filter(i => i.opinion === '需修订');
  const unreviewed = rec2.items.filter(i => i.opinion === '未复核');
  ok(revised.length === 1 && revised[0].id === 'answer:q10', 'exactly answer:q10 changed to 需修订');
  ok(revised[0].comment.indexOf('P3') >= 0 && revised[0].comment.indexOf('模拟操作测试') >= 0, 'P3 comment carried');
  ok(unreviewed.length === 7, `other 7 stay 未复核 (got ${unreviewed.length})`);
  const revQ10 = rec2.items.find(i => i.id === 'revision:q10');
  ok(revQ10 && revQ10.opinion === '未复核', 'revision:q10 unaffected (domain-separated state)');
  ok(rec2.tally['需修订'] === 1 && rec2.tally['未复核'] === 7, 'tally reflects exactly one 需修订');
  ok(rec2.pack_identity.inputs.questions.sha256.startsWith('4e39229e'), 'input SHA unchanged after edit');
  ok(rec2.exported_at && rec2.review_date === '', 'export time recorded; review_date still unfilled');

  console.log(`check-targeted-review-pack: ${passed} checks passed (DOM/JS stub — 非真实浏览器)`);
  const wi = process.argv.indexOf('--write-sample');
  if (wi >= 0 && process.argv[wi + 1]) {
    fs.writeFileSync(process.argv[wi + 1], text2, 'utf8');
    console.log('wrote simulated sample:', process.argv[wi + 1]);
  }
  process.exit(0);
}).catch(e => { console.error('FAIL:', e.message); process.exit(1); });
