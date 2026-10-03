// Async behavior regression for the procedures page (T016).
// Minimal DOM/fetch/localStorage stub — not real browser evidence.
// Covers: draft with filters, saveability gate, save-only persistence with
// duplicate-submit protection, refresh restore without requests, progress /
// notes / personal steps / reminder sorting / deletion, verify keeps user
// progress, and storage-unavailable handling.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');

const html = fs.readFileSync(
  path.resolve(__dirname, '../src/campus_assistant/static/procedures.html'),
  'utf8'
);
const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/);
if (!scriptMatch) { console.error('No inline script found'); process.exit(1); }
const script = scriptMatch[1];

// T018-R1: 事件存入桩外 WeakMap；children 模拟原生 HTMLCollection（无 forEach/map），
// 使产品代码对数组专有方法/测试桩内部属性的依赖立即暴露。
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
    this.checked = false;
    this.type = '';
    this.placeholder = '';
    this.text = '';
    this.className = '';
    this.classList = {
      toggle: (cls, force) => {
        const parts = new Set(this.className.split(/\s+/).filter(Boolean));
        const want = force === undefined ? !parts.has(cls) : !!force;
        if (want) parts.add(cls); else parts.delete(cls);
        this.className = [...parts].join(' ');
      },
      add: cls => {
        const parts = new Set(this.className.split(/\s+/).filter(Boolean));
        parts.add(cls);
        this.className = [...parts].join(' ');
      },
      remove: cls => {
        const parts = new Set(this.className.split(/\s+/).filter(Boolean));
        parts.delete(cls);
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

const citation = (over = {}) => ({
  required: true, status: 'ok', document_id: 'syn-parse-txt-001',
  block_id: '9df6bfbd98df733e', char_start: 0, char_end: 38,
  quote: '第二条 学生因病或其他特殊原因不能参加期末考试的，应当在考试前提出缓考申请。',
  document_sha256: 'a'.repeat(64), preview_url: '/preview#syn-parse-txt-001/9df6bfbd98df733e',
  document_title: '合成测试教务管理办法', version_label: '解析示例 v1',
  scope: { campus: ['成都校区'], student_type: ['全日制本科'], admission_years: [2023, 2024] },
  effective_from: '2025-03-01', effective_to: null, is_synthetic: true, note: null,
  ...over,
});

const draftOk = () => ({
  procedure_id: 'proc-apply-defer', title: '缓考申请（合成演示）',
  summary: '缓考申请流程', template_version: '1.0', is_synthetic: true,
  filters: { campus: null, student_type: null, admission_year: 2024, as_of_date: null },
  filter_summary: { active: true, allowed_count: 2, counting_rules: '统计对象为文档' },
  steps: [
    { step_id: 'd1', title: '考试前提出缓考申请', detail: '应当在考试前提出缓考申请。', status: 'ok', fallback: null,
      citations: [citation()], unspecified: ['申请入口'] },
    { step_id: 'd2', title: '经所在学院批准', detail: '须经所在学院批准。', status: 'ok', fallback: null,
      citations: [citation({ char_start: 38, char_end: 50, quote: '缓考申请须经所在学院批准' })], unspecified: [] },
  ],
  saveable: true, status: 'ready', issues: [],
  disclaimer: '合成演示清单，不代表学校受理或资格认证；政策步骤来自原文引用，缺失信息不编造。',
});

function setup(sharedStorage, locationSearch) {
  const ids = {};
  for (const id of ['item-cards', 'draft-area', 'todo-area', 'todo-filter',
                    'todo-storage-note', 'filter-campus', 'filter-student-type',
                    'filter-admission-year', 'filter-as-of-date', 'clear-filters-btn',
                    'draft-btn', 'save-btn', 'import-note']) {
    ids[id] = new Element(id.endsWith('-btn') ? 'button' : 'div');
  }
  const requests = [];
  const storage = sharedStorage || {};
  const state = {
    procedures: {
      configured: true, is_synthetic: true,
      procedures: [
        { procedure_id: 'proc-apply-defer', title: '缓考申请（合成演示）', summary: '缓考申请流程', template_version: '1.0', is_synthetic: true, step_count: 2 },
        { procedure_id: 'proc-review-grade', title: '成绩复核（合成演示）', summary: '成绩复核流程', template_version: '1.0', is_synthetic: true, step_count: 3 },
      ],
    },
    filter_options: { campus: ['成都校区'], student_type: ['全日制本科'], admission_year: [2023, 2024] },
    draftResponse: draftOk(),
    verifyResponse: { status: 'unchanged', issues: [], current_template_version: '1.0' },
    promptAnswer: '我的个人步骤',
    storageFailWrites: false,
  };
  const context = {
    document: {
      getElementById: id => ids[id] || null,
      createElement: t => new Element(t),
      createTextNode: t => { const e = new Element(); e.textContent = t; return e; },
    },
    window: { addEventListener() {} },
    location: { search: locationSearch || '' },
    prompt: () => state.promptAnswer,
    localStorage: {
      getItem: k => (k in storage ? storage[k] : null),
      setItem: (k, v) => {
        if (state.storageFailWrites) throw new Error('storage unavailable');
        storage[k] = String(v);
      },
      removeItem: k => { delete storage[k]; },
      clear: () => { for (const k of Object.keys(storage)) delete storage[k]; },
    },
    fetch: (url, options) => {
      if (!options) {
        // GET: procedures list or search status
        const payload = url.indexOf('/procedures') >= 0 ? state.procedures : { filter_options: state.filter_options };
        return Promise.resolve({ ok: true, status: 200, json: async () => payload });
      }
      return new Promise((resolve, reject) => {
        requests.push({ url, body: JSON.parse(options.body), resolve, reject });
      });
    },
  };
  vm.runInNewContext(script, context);
  return { ids, requests, state, storage };
}

const flush = () => new Promise(resolve => setImmediate(resolve));
const ok = (payload) => ({ ok: true, status: 200, json: async () => payload });

(async () => {
  let passed = 0;

  // Scenario 1: item + filters → draft with citations; saveable enables save
  {
    const s = setup();
    await flush();
    assert.match(s.ids['item-cards'].textContent, /缓考申请（合成演示）/);
    assert.match(s.ids['item-cards'].textContent, /成绩复核（合成演示）/);
    const card = s.ids['item-cards'].querySelectorAll('.item-card')[0];
    trigger(card, 'click');
    s.ids['filter-admission-year'].value = '2024';
    trigger(s.ids['draft-btn'], 'click');
    await flush();
    assert.equal(s.requests.length, 1);
    assert.match(s.requests[0].url, /proc-apply-defer\/draft$/);
    assert.equal(s.requests[0].body.filters.admission_year, 2024);
    s.requests[0].resolve(ok(draftOk()));
    await flush();
    const txt = s.ids['draft-area'].textContent;
    assert.match(txt, /模板 1\.0/);
    assert.match(txt, /原文：“第二条/);
    assert.match(txt, /查看原文/);
    assert.match(txt, /资料未说明：申请入口/);
    assert.match(txt, /合成演示清单/);
    assert.equal(s.ids['save-btn'].disabled, false, 'saveable draft enables save');
    passed++;
  }

  // Scenario 2: not saveable → explicit refusal, save disabled
  {
    const s = setup();
    await flush();
    trigger(s.ids['item-cards'].querySelectorAll('.item-card')[0], 'click');
    const bad = draftOk();
    bad.saveable = false;
    bad.status = 'insufficient';
    bad.issues = ['步骤「考试前提出缓考申请」：来源不符合当前筛选条件（syn-parse-txt-001/9df6bfbd98df733e）'];
    bad.steps[0].status = 'failed';
    bad.steps[0].fallback = '资料未说明，请向办理部门核实。';
    s.state.draftResponse = bad;
    s.ids['filter-admission-year'].value = '2023';
    trigger(s.ids['draft-btn'], 'click');
    await flush();
    s.requests[0].resolve(ok(bad));
    await flush();
    assert.match(s.ids['draft-area'].textContent, /资料不足\/依据需更新/);
    assert.match(s.ids['draft-area'].textContent, /不放宽筛选/);
    assert.equal(s.ids['save-btn'].disabled, true, 'unsavable draft keeps save disabled');
    passed++;
  }

  // Scenario 3: zero persistence before save; duplicate-save protection;
  // explicit 另存为新清单
  {
    const s = setup();
    await flush();
    trigger(s.ids['item-cards'].querySelectorAll('.item-card')[0], 'click');
    trigger(s.ids['draft-btn'], 'click');
    await flush();
    s.requests[0].resolve(ok(draftOk()));
    await flush();
    assert.equal(s.storage['campus_procedures_todos_v1'], undefined, 'no persistence before save click');
    trigger(s.ids['save-btn'], 'click');
    trigger(s.ids['save-btn'], 'click'); // double click — must not duplicate
    assert.equal(JSON.parse(s.storage['campus_procedures_todos_v1']).length, 1, 'duplicate save prevented');
    assert.match(s.ids['draft-area'].textContent, /已保存到我的待办/);
    const again = s.ids['draft-area'].querySelectorAll('button').find(b => b.textContent === '另存为新清单');
    assert.ok(again);
    trigger(again, 'click');
    assert.equal(JSON.parse(s.storage['campus_procedures_todos_v1']).length, 2, 'explicit new list allowed');
    passed++;
  }

  // Scenario 4: refresh restore — items render, interactions make no requests
  {
    const storage = {};
    const s1 = setup(storage);
    await flush();
    trigger(s1.ids['item-cards'].querySelectorAll('.item-card')[0], 'click');
    trigger(s1.ids['draft-btn'], 'click');
    await flush();
    s1.requests[0].resolve(ok(draftOk()));
    await flush();
    trigger(s1.ids['save-btn'], 'click');
    const s2 = setup(storage); // "refresh"
    await flush();
    await flush();
    assert.match(s2.ids['todo-area'].textContent, /缓考申请（合成演示）/);
    assert.match(s2.ids['todo-area'].textContent, /政策步骤/);
    assert.match(s2.ids['todo-area'].textContent, /保存时的依据，可能已更新/);
    assert.match(s2.ids['todo-area'].textContent, /进度 0\/2/);
    const reqBefore = s2.requests.length;
    // progress toggle — pure local
    const cb = s2.ids['todo-area'].querySelectorAll('input').find(i => i.type === 'checkbox');
    cb.checked = true;
    trigger(cb, 'change');
    await flush();
    assert.equal(s2.requests.length, reqBefore, 'restore/toggle make no requests');
    assert.match(s2.ids['todo-area'].textContent, /进度 1\/2/);
    passed++;
  }

  // Scenario 5: notes, personal step, reminder sorting, deletion, filter
  {
    const s = setup();
    await flush();
    trigger(s.ids['item-cards'].querySelectorAll('.item-card')[0], 'click');
    trigger(s.ids['draft-btn'], 'click');
    await flush();
    s.requests[0].resolve(ok(draftOk()));
    await flush();
    trigger(s.ids['save-btn'], 'click');
    // personal step
    s.state.promptAnswer = '打印成绩单';
    const addBtn = s.ids['todo-area'].querySelectorAll('button').find(b => b.textContent === '+ 添加个人步骤');
    trigger(addBtn, 'click');
    await flush();
    assert.match(s.ids['todo-area'].textContent, /打印成绩单/);
    assert.match(s.ids['todo-area'].textContent, /个人步骤/);
    // set reminders: policy d2 gets 2026-12-01, personal 2026-01-01
    const dates = s.ids['todo-area'].querySelectorAll('input').filter(i => i.type === 'date');
    dates[1].value = '2026-12-01'; trigger(dates[1], 'change');
    dates[2].value = '2026-01-01'; trigger(dates[2], 'change');
    await flush();
    const sortBtn = s.ids['todo-area'].querySelectorAll('button').find(b => b.textContent === '按提醒日期排序');
    trigger(sortBtn, 'click');
    await flush();
    const titles = s.ids['todo-area'].querySelectorAll('.t-item-title').map(t => t.textContent);
    assert.deepEqual(titles, ['打印成绩单', '经所在学院批准', '考试前提出缓考申请'], 'reminder asc, empty last');
    // personal note persistence
    const note = s.ids['todo-area'].querySelectorAll('input').find(i => i.placeholder === '个人备注（仅本机保存）');
    note.value = '带身份证';
    trigger(note, 'change');
    // delete personal item
    const delBtn = s.ids['todo-area'].querySelectorAll('button').find(b => b.textContent === '删除');
    trigger(delBtn, 'click');
    await flush();
    assert.ok(!/打印成绩单/.test(s.ids['todo-area'].textContent));
    // done filter
    s.ids['todo-filter'].value = 'done';
    trigger(s.ids['todo-filter'], 'change');
    assert.ok(!/考试前提出缓考申请/.test(s.ids['todo-area'].textContent), 'done filter hides undone');
    s.ids['todo-filter'].value = 'undone';
    trigger(s.ids['todo-filter'], 'change');
    assert.match(s.ids['todo-area'].textContent, /考试前提出缓考申请/);
    // delete whole list
    const delList = s.ids['todo-area'].querySelectorAll('button').find(b => b.textContent === '删除本清单');
    trigger(delList, 'click');
    assert.match(s.ids['todo-area'].textContent, /暂无待办/);
    passed++;
  }

  // Scenario 6: verify changed keeps progress and notes, no silent overwrite
  {
    const s = setup();
    await flush();
    trigger(s.ids['item-cards'].querySelectorAll('.item-card')[0], 'click');
    trigger(s.ids['draft-btn'], 'click');
    await flush();
    s.requests[0].resolve(ok(draftOk()));
    await flush();
    trigger(s.ids['save-btn'], 'click');
    const cb = s.ids['todo-area'].querySelectorAll('input').find(i => i.type === 'checkbox');
    cb.checked = true; trigger(cb, 'change');
    const note = s.ids['todo-area'].querySelectorAll('input').find(i => i.placeholder === '个人备注（仅本机保存）');
    note.value = '保留我'; trigger(note, 'change');
    s.state.verifyResponse = { status: 'changed', issues: ['模板版本已变化（保存时 1.0，当前 1.1）'], current_template_version: '1.1' };
    const verifyBtn = s.ids['todo-area'].querySelectorAll('button').find(b => b.textContent === '核对当前依据');
    trigger(verifyBtn, 'click');
    const vReq = s.requests.find(r => /\/verify$/.test(r.url));
    assert.ok(vReq, 'verify request sent');
    vReq.resolve(ok(s.state.verifyResponse));
    await flush();
    assert.match(s.ids['todo-area'].textContent, /依据已变化或不可用，请复核/);
    const note2 = s.ids['todo-area'].querySelectorAll('input').find(i => i.placeholder === '个人备注（仅本机保存）');
    assert.equal(note2.value, '保留我', 'note kept');
    assert.match(s.ids['todo-area'].textContent, /进度 1\/2/, 'progress kept');
    passed++;
  }

  // Scenario 7: storage unavailable — no 保存成功, draft still viewable
  {
    const s = setup();
    await flush();
    s.state.storageFailWrites = true;
    trigger(s.ids['item-cards'].querySelectorAll('.item-card')[0], 'click');
    trigger(s.ids['draft-btn'], 'click');
    await flush();
    s.requests[0].resolve(ok(draftOk()));
    await flush();
    trigger(s.ids['save-btn'], 'click');
    await flush();
    assert.match(s.ids['draft-area'].textContent, /保存失败：本机存储不可用/);
    assert.ok(!/已保存到我的待办/.test(s.ids['draft-area'].textContent), 'no success message');
    assert.match(s.ids['draft-area'].textContent, /考试前提出缓考申请/, 'draft still visible');
    passed++;
  }

  // T016-R1 chain 1: excluded optional content never rendered nor saved;
  // 待核实 status kept through save → refresh; 2024 contrast keeps valid quote
  {
    const d23 = draftOk();
    d23.filters = { campus: null, student_type: null, admission_year: 2023, as_of_date: null };
    d23.steps = [
      d23.steps[0], d23.steps[1],
      { step_id: 'd4', title: '确认材料与办理时点', detail: '材料与时点以适用资料所载为准；未覆盖部分请向办理部门核实。',
        status: 'degraded', fallback: '资料未说明，请向办理部门核实。',
        citations: [{ required: false, usable: false, status: 'source_excluded',
          document_id: 'syn-parse-docx-001', block_id: '0a7595fda827d87e', char_start: 0, char_end: 19,
          quote: null, document_sha256: 'b'.repeat(64),
          preview_url: '/preview#syn-parse-docx-001/0a7595fda827d87e',
          document_title: '合成测试课程成绩登记表', version_label: '解析示例 v1',
          scope: { campus: ['成都校区'], student_type: ['全日制本科'], admission_years: [2024] },
          effective_from: '2025-03-01', effective_to: null, is_synthetic: true,
          note: '来源不符合当前筛选条件（不放宽筛选）' }],
        unspecified: ['其他可能要求的材料'] },
    ];
    const storage = {};
    const s = setup(storage);
    await flush();
    trigger(s.ids['item-cards'].querySelectorAll('.item-card')[0], 'click');
    s.state.draftResponse = d23;
    s.ids['filter-admission-year'].value = '2023';
    trigger(s.ids['draft-btn'], 'click');
    await flush();
    s.requests[0].resolve(ok(d23));
    await flush();
    const draftTxt = s.ids['draft-area'].textContent;
    assert.ok(!/需医院证明/.test(draftTxt), 'excluded material not rendered');
    assert.ok(!/3个工作日/.test(draftTxt), 'excluded deadline not rendered');
    assert.match(draftTxt, /资料未说明/);
    assert.match(draftTxt, /未作为可用办理依据/);
    assert.match(draftTxt, /待核实\/未说明项/, 'banner reflects partial unknown');
    trigger(s.ids['save-btn'], 'click');
    const saved = storage['campus_procedures_todos_v1'];
    assert.ok(!/需医院证明/.test(saved) && !/3个工作日/.test(saved), 'excluded content never saved');
    assert.ok(/资料未说明/.test(saved), 'pending semantics preserved in snapshot');
    const s2 = setup(storage); // refresh
    await flush();
    const todoTxt = s2.ids['todo-area'].textContent;
    assert.ok(!/需医院证明/.test(todoTxt) && !/3个工作日/.test(todoTxt), 'restored todo clean');
    assert.match(todoTxt, /待核实/, 'restored todo keeps 待核实 state');
    // 2024 contrast: valid material quote rendered normally
    const d24 = draftOk();
    d24.steps = [d24.steps[0], d24.steps[1],
      { step_id: 'd4', title: '确认材料与办理时点', detail: '材料与时点以适用资料所载为准。',
        status: 'ok', fallback: null,
        citations: [{ required: false, usable: true, status: 'ok',
          document_id: 'syn-parse-docx-001', block_id: '0a7595fda827d87e', char_start: 0, char_end: 19,
          quote: '缓考申请\t考试前3个工作日\t需医院证明', document_sha256: 'b'.repeat(64),
          preview_url: '/preview#syn-parse-docx-001/0a7595fda827d87e',
          document_title: '合成测试课程成绩登记表', version_label: '解析示例 v1',
          scope: { campus: ['成都校区'], student_type: ['全日制本科'], admission_years: [2024] },
          effective_from: '2025-03-01', effective_to: null, is_synthetic: true, note: null }],
        unspecified: ['其他可能要求的材料'] }];
    trigger(s2.ids['item-cards'].querySelectorAll('.item-card')[0], 'click');
    s2.state.draftResponse = d24;
    s2.ids['filter-admission-year'].value = '2024';
    trigger(s2.ids['draft-btn'], 'click');
    await flush();
    s2.requests[0].resolve(ok(d24));
    await flush();
    assert.match(s2.ids['draft-area'].textContent, /需医院证明/, '2024 contrast keeps valid quote');
    passed++;
  }

  // T016-R1 chain 3: a failed new draft invalidates the old saveable draft
  {
    const s = setup();
    await flush();
    trigger(s.ids['item-cards'].querySelectorAll('.item-card')[0], 'click');
    trigger(s.ids['draft-btn'], 'click');
    await flush();
    s.requests[0].resolve(ok(draftOk()));
    await flush();
    assert.equal(s.ids['save-btn'].disabled, false, 'first draft saveable');
    // new request with different conditions — fails
    s.ids['filter-admission-year'].value = '2023';
    trigger(s.ids['draft-btn'], 'click');
    await flush();
    assert.equal(s.ids['save-btn'].disabled, true, 'old draft invalidated at request start');
    s.requests[1].resolve({ ok: false, status: 503, json: async () => ({ code: 'PROCEDURES_NOT_CONFIGURED', message: '办事模板未配置' }) });
    await flush();
    assert.match(s.ids['draft-area'].textContent, /草稿请求失败：HTTP 503/);
    assert.match(s.ids['draft-area'].textContent, /旧草稿已失效/);
    assert.equal(s.ids['save-btn'].disabled, true, 'failed request keeps save disabled');
    trigger(s.ids['save-btn'], 'click'); // attempt anyway — must be a no-op
    await flush();
    assert.equal(s.storage['campus_procedures_todos_v1'], undefined, 'zero todos written from stale draft');
    passed++;
  }

  // T018-R1: 带入 2023 + 选中成绩复核 → 手动生成提交正确 procedure_id/filters；
  // 加载本身零 draft/保存请求（预选只用公共 selectProcedure，不依赖桩内部属性）
  {
    const s = setup(null, '?procedure_id=proc-review-grade&query=' +
      encodeURIComponent('成绩复核') + '&admission_year=2023');
    await flush();
    await flush();
    assert.equal(s.ids['filter-admission-year'].value, '2023');
    const noteTxt = s.ids['import-note'].textContent;
    assert.match(noteTxt, /已带入条件（来自问答结果快照）/);
    assert.match(noteTxt, /成绩复核/);
    assert.match(noteTxt, /不会自动保存待办，也不会调用模型/);
    // 事项预选生效（selected 类 + 后续草稿请求指向正确事项）
    const gradeCard = s.ids['item-cards'].querySelectorAll('.item-card')
      .find(c => c.getAttribute('data-procedure-id') === 'proc-review-grade');
    assert.ok(gradeCard.classList.contains('selected'), 'imported procedure preselected');
    const posts = s.requests.filter(r => String(r.url).indexOf('/draft') >= 0);
    assert.equal(posts.length, 0, 'import makes no draft request');
    assert.equal(s.storage['campus_procedures_todos_v1'], undefined, 'import writes nothing');
    // explicit click is required — request must use the imported procedure + filters
    trigger(s.ids['draft-btn'], 'click');
    await flush();
    const draftReq = s.requests.find(r => String(r.url).indexOf('/draft') >= 0);
    assert.ok(draftReq);
    assert.match(draftReq.url, /proc-review-grade\/draft$/);
    assert.equal(draftReq.body.filters.admission_year, 2023);
    draftReq.resolve(ok(draftOk()));
    await flush();
    passed++;
  }

  // T018: missing imported option kept and reported (never silently dropped)
  {
    const s = setup(null, '?admission_year=2019&query=' + encodeURIComponent('缓考'));
    await flush();
    await flush();
    assert.equal(s.ids['filter-admission-year'].value, '2019', 'missing option value kept');
    assert.match(s.ids['import-note'].textContent, /已保留该条件/);
    passed++;
  }

  console.log(`check-procedures-behavior: ${passed} scenarios passed`);
  process.exit(0);
})().catch(e => {
  console.error('FAIL:', e.message);
  console.error(e.stack);
  process.exit(1);
});
