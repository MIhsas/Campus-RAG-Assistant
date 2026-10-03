// Async behavior regression for the self-check page (T019).
// Minimal DOM/fetch stub — not real browser evidence, product code uses
// native-DOM-compatible access only (no stub internals).
// Covers: form rendering, result snapshot binding, per-item states with
// citations, modify-recheck, failure shows no new result, insufficient
// basis vs personal unmet distinct, reset keeps old results.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');

const html = fs.readFileSync(
  path.resolve(__dirname, '../src/campus_assistant/static/self-check.html'),
  'utf8'
);
const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/);
if (!scriptMatch) { console.error('No inline script found'); process.exit(1); }
const script = scriptMatch[1];

const EVENTS = new WeakMap();
function trigger(el, name, evt) {
  const store = EVENTS.get(el);
  if (store && typeof store[name] === 'function') store[name](evt || {});
}

class Element {
  constructor(tag = 'div', attrs = {}) {
    this.tag = tag;
    this.attrs = { ...attrs };
    this._children = [];
    this.style = {};
    this.disabled = false;
    this.value = '';
    this.type = '';
    this.text = '';
    this.className = '';
    this.classList = {
      toggle: (cls, force) => {
        const parts = new Set(this.className.split(/\s+/).filter(Boolean));
        const want = force === undefined ? !parts.has(cls) : !!force;
        if (want) parts.add(cls); else parts.delete(cls);
        this.className = [...parts].join(' ');
      },
      contains: cls => this.className.split(/\s+/).filter(Boolean).includes(cls),
    };
  }
  get children() {
    const arr = this._children;
    const collection = { length: arr.length, item: i => arr[i] || null };
    for (let i = 0; i < arr.length; i++) collection[i] = arr[i];
    return collection;
  }
  appendChild(c) { this._children.push(c); return c; }
  addEventListener(e, fn) {
    const store = EVENTS.get(this) || {};
    store[e] = fn;
    EVENTS.set(this, store);
  }
  getAttribute(n) { return n in this.attrs ? this.attrs[n] : null; }
  setAttribute(n, v) { this.attrs[n] = v; }
  matches(sel) {
    if (sel.startsWith('.')) {
      const cls = sel.slice(1);
      return this.className.split(/\s+/).filter(Boolean).includes(cls);
    }
    return this.tag === sel;
  }
  closest(sel) { return this.matches(sel) ? this : null; }
  querySelectorAll(sel) {
    const out = [];
    const walk = e => {
      for (const c of e._children) {
        if (c.matches(sel)) out.push(c);
        walk(c);
      }
    };
    walk(this);
    return out;
  }
  set textContent(v) { this.text = String(v); this._children = []; }
  get textContent() { return this.text + this._children.map(c => c.textContent).join(''); }
  set innerHTML(v) { this.text = String(v); this._children = []; }
}

const RULE = {
  configured: true,
  rule_id: 'rule-transfer-major', rule_version: '1.0',
  title: '转专业条件自查（合成演示）', summary: '四项条件自查演示。',
  is_synthetic: true,
  answer_options: [
    { value: 'yes', label: '是' }, { value: 'no', label: '否' },
    { value: 'unknown', label: '不确定 / 未填写' },
  ],
  not_collected: ['姓名', '学号', '违纪详情'],
  items: [
    { item_id: 't1', title: '是否在入学后第一学年末提出申请', question: '您是否在入学后第一学年末提出转专业申请？', answer_field: 'apply_at_first_year_end', explanation: '原文要求：第一学年末提出申请。', citation: { document_id: 'syn-parse-txt-001', block_id: 'ce15747a6cdf597a', char_start: 0, char_end: 25, quote: '第五条 学生转专业应当在入学后第一学年末提出申请。' } },
    { item_id: 't2', title: '在读期间是否无违纪记录', question: '您在读期间是否无违纪记录？', answer_field: 'no_discipline_record', explanation: '原文条件：无违纪记录。', citation: { document_id: 'syn-parse-txt-001', block_id: 'ce15747a6cdf597a', char_start: 34, char_end: 47, quote: '1. 在读期间无违纪记录；' } },
    { item_id: 't3', title: '前 30%', question: '排名是否前 30%？', answer_field: 'rank_top_30', explanation: '原文条件：前30%。', citation: { document_id: 'syn-parse-txt-001', block_id: 'ce15747a6cdf597a', char_start: 48, char_end: 72, quote: '2. 第一学年加权平均成绩排名在本专业前30%；' } },
    { item_id: 't4', title: '是否通过接收学院组织的考核', question: '是否通过接收学院组织的考核？', answer_field: 'passed_assessment', explanation: '原文条件：通过考核。', citation: { document_id: 'syn-parse-txt-001', block_id: 'ce15747a6cdf597a', char_start: 73, char_end: 88, quote: '3. 通过接收学院组织的考核。' } },
  ],
};

const citationRef = (over = {}) => ({
  usable: true, status: 'ok',
  document_id: 'syn-parse-txt-001', block_id: 'ce15747a6cdf597a',
  char_start: 0, char_end: 25,
  quote: '第五条 学生转专业应当在入学后第一学年末提出申请。',
  document_sha256: 'a'.repeat(64),
  preview_url: '/preview#syn-parse-txt-001/ce15747a6cdf597a',
  note: null, ...over,
});

function resultOk(answers, summaryStatus, itemStatuses) {
  return {
    rule_id: 'rule-transfer-major', rule_version: '1.0',
    rule_title: '转专业条件自查（合成演示）', is_synthetic: true,
    filters: { campus: null, student_type: null, admission_year: null, as_of_date: null },
    filter_summary: { active: false, allowed_count: 2, counting_rules: '统计对象为文档' },
    basis: { status: 'ok', citations: [citationRef()] },
    answers: answers,
    items: RULE.items.map((it, i) => ({
      item_id: it.item_id, title: it.title, question: it.question,
      answer: answers[it.answer_field] || 'unknown',
      status: itemStatuses[i],
      explanation: it.explanation,
      citation: citationRef(),
    })),
    summary_status: summaryStatus,
    summary_text: {
      all_satisfied: '按自填信息满足本演示列出的条件；仍需学校审核，不构成录取、批准或申请成功。',
      has_unsatisfied: '存在未满足项（依据自填信息与合成演示规则）。',
      has_unknown: '仍有待核实项：存在不确定/未填写的必要条件，不能按满足处理。',
      insufficient_basis: '依据不足，无法完成自查（规则原文未通过准入或缺失/内容变化）。',
    }[summaryStatus],
    not_collected: ['姓名', '学号', '违纪详情'],
    disclaimer: '个人自查演示（合成资料、确定性规则）：不代表学校审核结果，不受理申请。',
  };
}

function setup() {
  const ids = {};
  for (const id of ['form-area', 'result-area', 'check-btn', 'reset-btn',
                    'filter-campus', 'filter-student-type', 'filter-admission-year',
                    'filter-as-of-date', 'clear-filters-btn']) {
    ids[id] = new Element(id.endsWith('-btn') ? 'button' : 'div');
  }
  const requests = [];
  const state = { rule: RULE, evalResponse: null };
  const context = {
    document: {
      getElementById: id => ids[id] || null,
      createElement: t => new Element(t),
      createTextNode: t => { const e = new Element(); e.textContent = t; return e; },
    },
    location: { search: '' },
    fetch: (url, options) => {
      if (!options) {
        const payload = url.indexOf('self-check') >= 0
          ? state.rule
          : { filter_options: { campus: ['成都校区'], student_type: ['全日制本科'], admission_year: [2023, 2024] } };
        return Promise.resolve({ ok: true, status: 200, json: async () => payload });
      }
      return new Promise((resolve, reject) => {
        requests.push({ url, body: JSON.parse(options.body), resolve, reject });
      });
    },
  };
  vm.runInNewContext(script, context);
  return { ids, requests, state };
}

const flush = () => new Promise(resolve => setImmediate(resolve));
const ok = (payload) => ({ ok: true, status: 200, json: async () => payload });

(async () => {
  let passed = 0;

  // Scenario 1: form renders four three-state items; submit → snapshot +
  // per-item states + citation preview links
  {
    const s = setup();
    await flush();
    const formTxt = s.ids['form-area'].textContent;
    assert.match(formTxt, /第一学年末/);
    assert.match(formTxt, /违纪/);
    assert.match(formTxt, /考核/);
    assert.match(formTxt, /不收集：姓名、学号、违纪详情/);
    const selects = s.ids['form-area'].querySelectorAll('select');
    assert.equal(selects.length, 4);
    selects[0].value = 'yes';
    selects[1].value = 'yes';
    selects[2].value = 'yes';
    selects[3].value = 'unknown';
    s.state.evalResponse = resultOk(
      { apply_at_first_year_end: 'yes', no_discipline_record: 'yes', rank_top_30: 'yes', passed_assessment: 'unknown' },
      'has_unknown', ['satisfied', 'satisfied', 'satisfied', 'unknown']);
    trigger(s.ids['check-btn'], 'click');
    await flush();
    assert.equal(s.requests.length, 1);
    assert.equal(s.requests[0].body.answers.passed_assessment, 'unknown');
    s.requests[0].resolve(ok(s.state.evalResponse));
    await flush();
    const txt = s.ids['result-area'].textContent;
    assert.match(txt, /本次自查快照/);
    assert.match(txt, /已填：不确定 \/ 未填写/);
    assert.match(txt, /仍有待核实项/);
    assert.match(txt, /待核实/);
    assert.match(txt, /原文：“第五条/);
    assert.match(txt, /查看原文/);
    assert.match(txt, /不代表学校审核结果/);
    passed++;
  }

  // Scenario 2: all satisfied → qualified-by-self-report wording, still school review
  {
    const s = setup();
    await flush();
    const selects = s.ids['form-area'].querySelectorAll('select');
    for (const sel of selects) sel.value = 'yes';
    s.state.evalResponse = resultOk(
      { apply_at_first_year_end: 'yes', no_discipline_record: 'yes', rank_top_30: 'yes', passed_assessment: 'yes' },
      'all_satisfied', ['satisfied', 'satisfied', 'satisfied', 'satisfied']);
    trigger(s.ids['check-btn'], 'click');
    await flush();
    s.requests[0].resolve(ok(s.state.evalResponse));
    await flush();
    assert.match(s.ids['result-area'].textContent, /按自填信息满足本演示列出的条件/);
    assert.match(s.ids['result-area'].textContent, /仍需学校审核/);
    assert.match(s.ids['result-area'].textContent, /不构成录取、批准或申请成功/);
    passed++;
  }

  // Scenario 3: editing the form does not rewrite old results; re-check replaces
  {
    const s = setup();
    await flush();
    const selects = s.ids['form-area'].querySelectorAll('select');
    for (const sel of selects) sel.value = 'yes';
    s.state.evalResponse = resultOk(
      { apply_at_first_year_end: 'yes', no_discipline_record: 'yes', rank_top_30: 'yes', passed_assessment: 'yes' },
      'all_satisfied', ['satisfied', 'satisfied', 'satisfied', 'satisfied']);
    trigger(s.ids['check-btn'], 'click');
    await flush();
    s.requests[0].resolve(ok(s.state.evalResponse));
    await flush();
    assert.match(s.ids['result-area'].textContent, /按自填信息满足/);
    // edit form — old result must remain untouched
    selects[1].value = 'no';
    assert.match(s.ids['result-area'].textContent, /按自填信息满足/, 'old result not rewritten by form edits');
    // re-check → new result
    s.state.evalResponse = resultOk(
      { apply_at_first_year_end: 'yes', no_discipline_record: 'no', rank_top_30: 'yes', passed_assessment: 'yes' },
      'has_unsatisfied', ['satisfied', 'unsatisfied', 'satisfied', 'satisfied']);
    trigger(s.ids['check-btn'], 'click');
    await flush();
    s.requests[1].resolve(ok(s.state.evalResponse));
    await flush();
    assert.match(s.ids['result-area'].textContent, /存在未满足项/);
    assert.match(s.ids['result-area'].textContent, /不满足/);
    passed++;
  }

  // Scenario 4: failure explicitly says no new result; no stale presented as new
  {
    const s = setup();
    await flush();
    trigger(s.ids['check-btn'], 'click');
    await flush();
    s.requests[0].resolve({ ok: false, status: 503, json: async () => ({ code: 'SELF_CHECK_NOT_CONFIGURED', message: '自查规则未配置' }) });
    await flush();
    assert.match(s.ids['result-area'].textContent, /未生成新结果/);
    assert.ok(!/本次自查快照/.test(s.ids['result-area'].textContent));
    passed++;
  }

  // Scenario 5: insufficient basis vs personal unmet are distinct
  {
    const s = setup();
    await flush();
    trigger(s.ids['check-btn'], 'click');
    await flush();
    const basisBad = resultOk({}, 'insufficient_basis', ['basis_unavailable', 'basis_unavailable', 'basis_unavailable', 'basis_unavailable']);
    basisBad.basis = { status: 'insufficient', citations: [citationRef({ usable: false, status: 'source_excluded', quote: null, note: '来源不符合当前筛选条件（不放宽筛选）' })] };
    basisBad.items = basisBad.items.map(i => ({ ...i, citation: basisBad.basis.citations[0] }));
    s.requests[0].resolve(ok(basisBad));
    await flush();
    const txt = s.ids['result-area'].textContent;
    assert.match(txt, /依据不足，无法完成自查/);
    assert.match(txt, /不作为自查依据/);
    assert.ok(!/存在未满足项/.test(txt), 'basis failure is not a personal unmet verdict');
    passed++;
  }

  // Scenario 6: reset clears the form but keeps old results (snapshot intact)
  {
    const s = setup();
    await flush();
    const selects = s.ids['form-area'].querySelectorAll('select');
    for (const sel of selects) sel.value = 'yes';
    s.state.evalResponse = resultOk(
      { apply_at_first_year_end: 'yes', no_discipline_record: 'yes', rank_top_30: 'yes', passed_assessment: 'yes' },
      'all_satisfied', ['satisfied', 'satisfied', 'satisfied', 'satisfied']);
    trigger(s.ids['check-btn'], 'click');
    await flush();
    s.requests[0].resolve(ok(s.state.evalResponse));
    await flush();
    trigger(s.ids['reset-btn'], 'click');
    for (const sel of s.ids['form-area'].querySelectorAll('select')) {
      assert.equal(sel.value, '', 'form cleared');
    }
    assert.match(s.ids['result-area'].textContent, /按自填信息满足/, 'old result kept');
    passed++;
  }

  console.log(`check-self-check-behavior: ${passed} scenarios passed`);
  process.exit(0);
})().catch(e => {
  console.error('FAIL:', e.message);
  console.error(e.stack);
  process.exit(1);
});
