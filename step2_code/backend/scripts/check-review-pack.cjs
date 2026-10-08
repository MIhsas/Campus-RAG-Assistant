// T036: behavior checks for the offline human-review pack (DOM/JS stub).
// NOT a real browser run — evidence level: 代码/桩依据.
// Verifies: all opinions default 未复核; no localStorage/网络; export produces a
// NEW JSON with input identity SHAs; one simulated 需修订+意见 exports while the
// rest stay 未复核; default pack carries no test selections.
// With --write-sample <path> it also writes the simulated export as a demo file
// (record_title carries "模拟操作测试" — it is NOT a real review conclusion).
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const packArg = process.argv.indexOf('--pack-dir');
const outDir = packArg >= 0 ? path.resolve(process.argv[packArg + 1]) : path.resolve(__dirname, '../.cache/human-review/T036-v1');
const html = fs.readFileSync(path.join(outDir, 'review.html'), 'utf8');
const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/);
if (!scriptMatch) { console.error('FAIL: no inline script'); process.exit(1); }

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
    return new NodeListLike(out); // NodeList 形态（非 Array、无 some）——见 T036-R2
  }
}

class Blob {
  constructor(parts, opts) { this.parts = parts; this.opts = opts; this.size = (parts[0] || '').length; }
  text() { return Promise.resolve(this.parts.join('')); }
}

// T036-R2: querySelectorAll must behave like a real DOM NodeList —
// non-Array, indexable, iterable, with forEach/item, and WITHOUT Array
// methods such as some/filer/map/flatMap. Code that assumes a plain array
// must fail here exactly as it would in a browser.
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
    return new NodeListLike(out); // NodeList 形态
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

// 1) default: every opinion 未复核, empty reviewer, no pre-filled date
const exportBtn = byId('export-btn');
exportBtn.click();
ok(capturedDownload, 'export produced a download blob');
capturedDownload.text().then(text => {
  const rec = JSON.parse(text);
  ok(rec.record_type === 'human_review_record', 'record_type is human_review_record');
  ok(rec.reviewer === '', 'reviewer default empty');
  ok(rec.record_title === '', 'record_title default empty (no test data in default pack)');
  const allOps = [];
  rec.question_opinions.forEach(q => {
    allOps.push(q.opinion);
    q.evidence_opinions.forEach(e => allOps.push(e.opinion));
  });
  rec.template_opinions.forEach(p => p.steps.forEach(s => {
    allOps.push(s.opinion);
    s.citation_opinions.forEach(c => allOps.push(c.opinion));
  }));
  ok(allOps.every(o => o === '未复核'), `all ${allOps.length} opinions default 未复核`);
  ok(rec.tally['未复核'] === allOps.length, 'tally counts match');
  // input identity SHAs present
  ok(rec.pack_identity.inputs.questions.sha256.startsWith('5fde70a3'), 'questions SHA in export');
  ok(rec.pack_identity.inputs.procedures.sha256.startsWith('78f1c1d9'), 'procedures SHA in export');

  // 2) simulate ONE 需修订+意见 (clearly labelled), others stay 未复核
  // find the first question opinion select+textarea via rendered state keys:
  // the page state lives in context closure — re-run export after poking UI nodes.
  const qCard = documentStub.querySelectorAll('.card')[0];
  const rows = qCard.querySelectorAll('.opinion-row');
  ok(rows.length >= 2, 'question card has item + question opinion rows');
  const firstRow = rows[0];
  const sel = firstRow.querySelectorAll('select')[0];
  const ta = firstRow.querySelectorAll('textarea')[0];
  sel.value = '需修订';
  (sel.listeners.change || []).forEach(fn => fn({}));
  ta.value = '示例意见：此条跨度建议复核（模拟操作测试）';
  (ta.listeners.input || []).forEach(fn => fn({}));
  byId('record-title').value = '模拟操作测试（MiMo 演示导出，非真实复核结论）';
  byId('reviewer').value = '（模拟测试，非真人复核）';
  capturedDownload = null;
  exportBtn.click();
  return capturedDownload.text();
}).then(text2 => {
  const rec2 = JSON.parse(text2);
  ok(rec2.record_title.indexOf('模拟操作测试') >= 0, 'simulated sample labelled 模拟操作测试');
  const revised = [];
  let unreviewed = 0;
  rec2.question_opinions.forEach(q => {
    if (q.opinion === '需修订') revised.push(q.question_id + '/q');
    if (q.opinion === '未复核') unreviewed++;
    q.evidence_opinions.forEach(e => {
      if (e.opinion === '需修订') revised.push(q.question_id + '/' + e.evidence_id);
      if (e.opinion === '未复核') unreviewed++;
    });
  });
  rec2.template_opinions.forEach(p => p.steps.forEach(s => {
    if (s.opinion === '需修订') revised.push('t/' + s.step_id);
    if (s.opinion === '未复核') unreviewed++;
    s.citation_opinions.forEach(c => {
      if (c.opinion === '需修订') revised.push('t/' + s.step_id + '/' + c.block_id);
      if (c.opinion === '未复核') unreviewed++;
    });
  }));
  ok(revised.length === 1, `exactly one item changed (got ${revised.length}: ${revised.join(',')})`);
  ok(revised[0].indexOf('模拟') < 0 && rec2.question_opinions[0].evidence_opinions[0].comment.indexOf('模拟操作测试') >= 0,
     'the one change carries the comment');
  ok(unreviewed >= 70, `all other items stay 未复核 (${unreviewed})`);
  ok(rec2.pack_identity.inputs.questions.sha256.startsWith('5fde70a3'), 'input SHA unchanged after edit');
  ok(rec2.tally['需修订'] === 1, 'tally reflects exactly one 需修订');

  // ---- T036-R1: opinion filter uses the CARD's own opinion rows (完整归属) ----
  const visibleCards = pane => byId(pane).children
    .filter(c => !(c.className.split(/\s+/).includes('hidden')))
    .map(c => (c.getAttribute('data-search') || 'summary').split(' ')[0]);
  const fire = el => (el.listeners.change || []).forEach(fn => fn({}));

  // ---- T036-R2: stub must present NodeList shape for .op-sel (真实守护) ----
  const shapeProbe = byId('questions-pane').children[0].querySelectorAll('.op-sel');
  ok(shapeProbe && !Array.isArray(shapeProbe) && Array.isArray(shapeProbe._items),
     '.op-sel query returns NodeList-shaped non-Array');
  ok(typeof shapeProbe.some === 'undefined' && typeof shapeProbe.map === 'undefined' &&
     typeof shapeProbe.flatMap === 'undefined', 'NodeList shape has NO Array methods (some/map/flatMap)');
  ok(typeof shapeProbe.forEach === 'function' && typeof shapeProbe.item === 'function',
     'NodeList shape has forEach/item');
  ok(typeof shapeProbe[Symbol.iterator] === 'function' && shapeProbe[0],
     'NodeList shape is indexable and iterable');

  // state at this point: exactly one 需修订 = q01 的 f1-s1（其余 113 未复核）
  const filterSel = byId('filter-op');
  filterSel.value = '需修订';
  fire(filterSel);
  const qVis = visibleCards('questions-pane');
  ok(qVis.length === 1 && qVis[0] === 'q01',
     `需修订 filter shows ONLY q01 (got ${qVis.join(',')}) — 同名 f1-s1 的其他题不误入`);
  ok(!qVis.includes('q02'), 'q02 (同名 f1-s1) stays hidden — no short-ID misattribution');

  // switch back: 未复核 shows cards that actually have 未复核 rows (incl. q01's other rows)
  filterSel.value = '未复核';
  fire(filterSel);
  ok(visibleCards('questions-pane').length === 24, '未复核 filter: all 24 cards (每卡均有未复核行) ');
  filterSel.value = '';
  fire(filterSel);
  ok(visibleCards('questions-pane').length === 24, 'empty filter shows all cards');

  // template: one citation 需修订 → only its own step card; other steps & summary not pulled in
  const tPane = byId('template-pane');
  const stepCards = tPane.children.filter(c => (c.getAttribute('data-search') || '') !== '');
  const firstStep = stepCards[0];
  const citSel = firstStep.querySelectorAll('.op-sel')[0];
  ok(citSel, 'step card exposes its own opinion selects');
  citSel.value = '需修订';
  fire(citSel);
  filterSel.value = '需修订';
  fire(filterSel);
  const tVis = visibleCards('template-pane');
  ok(tVis.length === 1 && tVis[0] === firstStep.getAttribute('data-search').split(' ')[0],
     `template 需修订 filter shows ONLY that step (got ${tVis.join(',')})`);
  ok(!tVis.includes('summary'), 'summary card (无意见行) 不计入匹配步骤');
  const lastStep = stepCards[stepCards.length - 1];
  ok(!tVis.includes(lastStep.getAttribute('data-search').split(' ')[0]),
     'other steps (含共享块 d64f4351 的末步) not misattributed');

  // change-opinion re-applies current filter immediately
  citSel.value = '未复核';
  fire(citSel);
  ok(visibleCards('template-pane').length === 0,
     'switching opinion to 未复核 re-filters immediately (需修订 filter now matches nothing)');

  // 3) offline invariants already enforced by stub (localStorage/fetch throw) — reached here = none used
  console.log(`check-review-pack: ${passed} checks passed (DOM/JS stub — 非真实浏览器)`);
  // optional sample write
  const wi = process.argv.indexOf('--write-sample');
  if (wi >= 0 && process.argv[wi + 1]) {
    fs.writeFileSync(process.argv[wi + 1], text2, 'utf8');
    console.log('wrote simulated sample:', process.argv[wi + 1]);
  }
  process.exit(0);
}).catch(e => { console.error('FAIL:', e.message); process.exit(1); });
