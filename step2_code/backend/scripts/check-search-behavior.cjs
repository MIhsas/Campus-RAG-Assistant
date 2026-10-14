// Async behavior regression for search page.
// Minimal DOM/fetch stub — does not claim real browser coverage.
// Covers: request invalidation races, retry snapshot (mode/query/filters),
// filter condition snapshot, clear-filters, filter empty states.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');

const html = fs.readFileSync(
  path.resolve(__dirname, '../src/campus_assistant/static/search.html'),
  'utf8'
);
const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/);
if (!scriptMatch) { console.error('No inline script found'); process.exit(1); }
const script = scriptMatch[1];

class Element {
  constructor(tag = 'div', attrs = {}) {
    this.tag = tag;
    this.attrs = { ...attrs };
    this.children = [];
    this.listeners = {};
    this.style = {};
    this.disabled = false;
    this.value = '';
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
  appendChild(c) { this.children.push(c); return c; }
  addEventListener(e, fn) { this.listeners[e] = fn; }
  getAttribute(n) { return n in this.attrs ? this.attrs[n] : null; }
  setAttribute(n, v) { this.attrs[n] = v; }
  matches(sel) {
    const cls = sel.replace(/^\./, '');
    return this.className.split(/\s+/).filter(Boolean).includes(cls);
  }
  closest(sel) { return this.matches(sel) ? this : null; }
  querySelectorAll(sel) {
    const cls = sel.replace(/^\./, '');
    return this.children.filter(c =>
      (c.className || '').split(/\s+/).filter(Boolean).includes(cls)
    );
  }
  set textContent(v) { this.text = String(v); this.children = []; }
  get textContent() { return this.text + this.children.map(c => c.textContent).join(''); }
  set innerHTML(v) { this.text = String(v); this.children = []; }
}

// Native-select semantics (T031-R1): assigning a value with no matching
// option stores '' — exactly what real <select> does. This is what caused
// the two P1 bugs, so the stub must reproduce it rather than accept any
// string.
class SelectElement extends Element {
  constructor(attrs = {}) {
    super('select', attrs);
    this._value = '';
  }
  get value() {
    const opts = this.children.filter(c => c.tag === 'option');
    if (opts.some(o => String(o.value) === String(this._value))) return String(this._value);
    return opts.length ? String(opts[0].value) : '';
  }
  set value(v) {
    const s = (v === null || v === undefined) ? '' : String(v);
    const opts = this.children.filter(c => c.tag === 'option');
    this._value = (s === '' || opts.some(o => String(o.value) === s)) ? s : '';
  }
  set innerHTML(v) { this.children = []; this.text = String(v); this._value = ''; }
}

function makeSelect(ids, id, optionValues) {
  const sel = new SelectElement();
  for (const v of optionValues) {
    const o = new Element('option');
    o.value = v;
    sel.appendChild(o);
  }
  ids[id] = sel;
  return sel;
}

function setup(locationSearch, stateOverrides) {
  const ids = {};
  for (const id of ['query-input', 'search-btn', 'status-area', 'results-area',
                    'filter-as-of-date', 'clear-filters-btn',
                    'clear-source-btn', 'source-hint', 'nav-ask', 'candidate-area']) {
    ids[id] = new Element();
  }
  // T043-R1：真实 checkbox 桩（静态 HTML 默认 checked；支持 checked 真实读写）
  ids['include-unknown-type'] = new Element('input');
  ids['include-unknown-type'].checked = true;
  // Native selects with their static-HTML initial options (T031-R1 stubs).
  makeSelect(ids, 'filter-campus', ['']);
  makeSelect(ids, 'filter-student-type', ['']);
  makeSelect(ids, 'filter-admission-year', ['']);
  makeSelect(ids, 'source-mode', ['all', 'doc']);
  makeSelect(ids, 'source-doc', ['']);
  const modeSelector = new Element('div');
  for (const m of ['bm25', 'dense', 'hybrid']) {
    const b = new Element('button', { 'data-mode': m });
    b.className = 'mode-btn' + (m === 'bm25' ? ' active' : '');
    modeSelector.appendChild(b);
  }
  ids['mode-selector'] = modeSelector;

  const requests = [];
  const state = {
    catalog: [], // T031: source-selection catalog entries
    deferCatalog: false, // T031-R1: hold the catalog response until releaseCatalog()
    releaseCatalog: null,
    statusOptions: {
      campus: ['成都校区', '都江堰校区'],
      student_type: ['全日制本科'],
      admission_year: [2024, 2025],
    },
  };
  if (stateOverrides) Object.assign(state, stateOverrides);
  const context = {
    document: {
      getElementById: id => ids[id],
      createElement: t => new Element(t),
      createTextNode: t => { const e = new Element(); e.textContent = t; return e; },
    },
    location: { search: locationSearch || '' },
    fetch: (url, options) => {
      if (!options) {
        if (String(url).indexOf('/api/v1/search/documents') >= 0) {
          // T031: source-selection catalog (deferrable for restore-timing chains)
          const respond = () => Promise.resolve({
            ok: true, status: 200,
            json: async () => ({
              status: 'ok', available: true,
              documents: state.catalog || [],
              count: (state.catalog || []).length,
            }),
          });
          if (state.deferCatalog) {
            return new Promise(resolve => {
              state.releaseCatalog = () => resolve(respond());
            });
          }
          return respond();
        }
        // GET status — filter_options read at json() time so tests can
        // change the option set mid-flight.
        return Promise.resolve({
          ok: true,
          json: async () => ({
            status: 'ready', parsed_count: 1, synthetic_count: 1,
            chunk_count: 1, indexed_chunk_count: 1, errors: [],
            available_modes: ['bm25', 'dense', 'hybrid'],
            filter_options: state.statusOptions,
          }),
        });
      }
      return new Promise((resolve, reject) => {
        requests.push({ url: String(url), body: JSON.parse(options.body), resolve, reject });
      });
    },
  };
  vm.runInNewContext(script, context);
  return {
    ids,
    requests,
    state,
    submit(q) {
      ids['query-input'].value = q;
      ids['query-input'].listeners.keydown({ key: 'Enter' });
    },
  };
}

const flush = () => new Promise(resolve => setImmediate(resolve));
const okResponse = (overrides = {}) => ({
  ok: true,
  status: 200,
  json: async () => ({
    query_tokens: ['x'], hits: [], indexed_chunk_count: 1,
    filters: null,
    filter_summary: {
      active: false, document_total: 1, allowed_count: 1,
      excluded_counts: {}, counting_rules: '统计对象为文档', notes: [],
    },
    ...overrides,
  }),
});

const findButton = e => {
  if (e.tag === 'button') return e;
  for (const c of e.children) {
    const found = findButton(c);
    if (found) return found;
  }
  return null;
};

(async () => {
  let passed = 0;

  // Test 1: Blank after search — old request invalidated, button restored
  for (const failure of [false, true]) {
    const s = setup();
    s.submit('A');
    s.submit(' ');
    assert.equal(s.requests.length, 1, 'blank should not create new request');
    assert.equal(s.ids['search-btn'].disabled, false, 'button should be restored after blank');
    failure ? s.requests[0].reject(new Error('fail')) : s.requests[0].resolve(okResponse());
    await flush();
    assert.match(s.ids['results-area'].textContent, /请输入搜索关键词/);
    assert.equal(s.ids['search-btn'].disabled, false);
    // Can submit new query
    s.ids['query-input'].value = 'B';
    s.ids['search-btn'].listeners.click();
    assert.equal(s.requests[1].body.query, 'B');
    s.requests[1].resolve(okResponse());
    await flush();
    assert.match(s.ids['results-area'].textContent, /查询：B/);
    assert.equal(s.ids['search-btn'].disabled, false);
    passed++;
  }

  // Test 2: A→B — A completes after B, B's result stays
  for (const failure of [false, true]) {
    const s = setup();
    s.submit('A');
    s.submit('B');
    failure ? s.requests[0].reject(new Error('fail')) : s.requests[0].resolve(okResponse());
    await flush();
    assert.equal(s.ids['search-btn'].disabled, true, 'B still loading');
    assert.match(s.ids['results-area'].textContent, /搜索中/);
    s.requests[1].resolve(okResponse());
    await flush();
    assert.equal(s.ids['search-btn'].disabled, false);
    assert.match(s.ids['results-area'].textContent, /查询：B/);
    passed++;
  }

  // Test 3: HTTP/network/JSON failures — retry uses original params
  for (const kind of ['http', 'json', 'network']) {
    const s = setup();
    s.submit('original');
    if (kind === 'network') {
      s.requests[0].reject(new Error('network'));
    } else if (kind === 'http') {
      s.requests[0].resolve({ ok: false, status: 500 });
    } else {
      s.requests[0].resolve({ ok: true, status: 200, json: async () => { throw new Error('json'); } });
    }
    await flush();
    // Edit input but retry button should use original params
    s.ids['query-input'].value = 'draft';
    const retryBtn = findButton(s.ids['results-area']);
    assert.ok(retryBtn, 'retry button should exist');
    retryBtn.listeners.click();
    await flush();
    assert.equal(s.requests[1].body.query, 'original', 'retry should use original query');
    s.requests[1].resolve(okResponse());
    await flush();
    assert.match(s.ids['results-area'].textContent, /查询：original/);
    passed++;
  }

  // Test 4: Retry snapshot keeps mode/query/filters after controls are edited
  {
    const s = setup();
    await flush(); // status loaded → mode buttons enabled
    const modeBtns = s.ids['mode-selector'].querySelectorAll('.mode-btn');
    s.ids['mode-selector'].listeners.click({ target: modeBtns[1] }); // dense
    s.ids['filter-campus'].value = '成都校区';
    s.ids['filter-admission-year'].value = '2024';
    s.ids['filter-as-of-date'].value = '2025-09-01';
    s.ids['query-input'].value = 'original';
    s.ids['query-input'].listeners.keydown({ key: 'Enter' });
    assert.equal(s.requests[0].body.mode, 'dense');
    assert.deepEqual(s.requests[0].body.filters, {
      campus: '成都校区', student_type: null, admission_year: 2024, as_of_date: '2025-09-01',
    });
    s.requests[0].reject(new Error('network'));
    await flush();
    // Edit query, filters and mode — retry must use the submitted snapshot
    s.ids['query-input'].value = 'draft';
    s.ids['filter-campus'].value = '';
    s.ids['filter-admission-year'].value = '';
    s.ids['filter-as-of-date'].value = '';
    s.ids['mode-selector'].listeners.click({ target: modeBtns[0] });
    const retryBtn = findButton(s.ids['results-area']);
    assert.ok(retryBtn, 'retry button should exist');
    retryBtn.listeners.click();
    await flush();
    assert.equal(s.requests[1].body.query, 'original');
    assert.equal(s.requests[1].body.mode, 'dense', 'retry keeps submitted mode');
    assert.deepEqual(s.requests[1].body.filters, {
      campus: '成都校区', student_type: null, admission_year: 2024, as_of_date: '2025-09-01',
    }, 'retry keeps submitted filters');
    s.requests[1].resolve(okResponse({
      filters: { campus: '成都校区', student_type: null, admission_year: 2024, as_of_date: '2025-09-01' },
    }));
    await flush();
    assert.match(s.ids['results-area'].textContent, /查询：original/);
    passed++;
  }

  // Test 5: Condition line is a snapshot — later control edits don't rewrite it
  {
    const s = setup();
    s.ids['filter-campus'].value = '成都校区';
    s.submit('缓考');
    s.requests[0].resolve(okResponse({
      filters: { campus: '成都校区', student_type: null, admission_year: null, as_of_date: null },
      filter_summary: {
        active: true, document_total: 2, allowed_count: 1,
        excluded_counts: { scope_mismatch: 1 }, counting_rules: '统计对象为文档',
        notes: ['1 份适用文档未标注截止日期（effective_to=null），不证明永久有效。'],
      },
    }));
    await flush();
    assert.match(s.ids['results-area'].textContent, /条件：校区=成都校区/);
    assert.match(s.ids['results-area'].textContent, /结果：0 条/);
    assert.match(s.ids['results-area'].textContent, /未标注截止/);
    // Editing controls afterwards must not change the rendered condition line
    s.ids['filter-campus'].value = '都江堰校区';
    assert.match(s.ids['results-area'].textContent, /条件：校区=成都校区/);
    passed++;
  }

  // Test 6: Clear-filters resets all four controls
  {
    const s = setup();
    s.ids['filter-campus'].value = '成都校区';
    s.ids['filter-student-type'].value = '全日制本科';
    s.ids['filter-admission-year'].value = '2024';
    s.ids['filter-as-of-date'].value = '2025-09-01';
    s.ids['clear-filters-btn'].listeners.click();
    assert.equal(s.ids['filter-campus'].value, '');
    assert.equal(s.ids['filter-student-type'].value, '');
    assert.equal(s.ids['filter-admission-year'].value, '');
    assert.equal(s.ids['filter-as-of-date'].value, '');
    passed++;
  }

  // Test 7: Empty states distinguish the two filtered cases, with clear action
  {
    const s = setup();
    s.ids['filter-campus'].value = '成都校区';
    s.submit('缓考');
    s.requests[0].resolve(okResponse({
      filters: { campus: '成都校区', student_type: null, admission_year: null, as_of_date: null },
      filter_summary: {
        active: true, document_total: 2, allowed_count: 0,
        excluded_counts: { scope_mismatch: 2 }, counting_rules: '统计对象为文档', notes: [],
      },
    }));
    await flush();
    assert.match(s.ids['results-area'].textContent, /没有满足所选条件的资料/);
    assert.ok(findButton(s.ids['results-area']), 'clear action should exist');

    const s2 = setup();
    s2.ids['filter-campus'].value = '成都校区';
    s2.submit('缓考');
    s2.requests[0].resolve(okResponse({
      filters: { campus: '成都校区', student_type: null, admission_year: null, as_of_date: null },
      filter_summary: {
        active: true, document_total: 2, allowed_count: 1,
        excluded_counts: { scope_mismatch: 1 }, counting_rules: '统计对象为文档', notes: [],
      },
    }));
    await flush();
    assert.match(s2.ids['results-area'].textContent, /满足条件的资料中没有检索命中/);
    assert.ok(findButton(s2.ids['results-area']), 'clear action should exist');

    // No filters + no hits keeps the plain message (not the filtered ones)
    const s3 = setup();
    s3.submit('缓考');
    s3.requests[0].resolve(okResponse());
    await flush();
    assert.match(s3.ids['results-area'].textContent, /无匹配结果/);
    assert.doesNotMatch(s3.ids['results-area'].textContent, /没有满足所选条件|满足条件的资料中没有检索命中/);
    passed++;
  }

  // Test 8: Semantic results follow actual hits, not BM25 token emptiness
  {
    const s = setup();
    await flush();
    const modeBtns = s.ids['mode-selector'].querySelectorAll('.mode-btn');
    s.ids['mode-selector'].listeners.click({ target: modeBtns[1] }); // dense
    s.submit('！！！');
    s.requests[0].resolve(okResponse({
      query_tokens: [],
      hits: [{
        rank: 1, score: 0.71, preview_url: '/preview#a/b',
        chunk: {
          chunk_id: 'c1', document_id: 'd1', block_id: 'b1', text: '语义命中正文',
          metadata: { title: '语义命中文档', scope: { campus: ['成都校区'], student_type: ['全日制本科'], admission_years: [2024] }, effective_from: '2025-03-01', effective_to: null },
        },
        matched_terms: [],
      }],
      indexed_chunk_count: 1,
    }));
    await flush();
    assert.match(s.ids['results-area'].textContent, /语义命中正文/, 'hits shown despite empty query_tokens');
    assert.doesNotMatch(s.ids['results-area'].textContent, /无有效搜索词/);
    // BM25 keeps the token hint when there are no hits
    const s2 = setup();
    s2.submit('！！！');
    s2.requests[0].resolve(okResponse({ query_tokens: [] }));
    await flush();
    assert.match(s2.ids['results-area'].textContent, /无有效搜索词/);
    passed++;
  }

  // Test 9 (T011-R1 P1 regression): select conditions → successful search →
  // post-search status refresh completes → controls keep their values (incl.
  // edits made while the search was in flight) → next search still carries
  // the same conditions.
  {
    const s = setup();
    await flush(); // initial status load fills the option lists
    s.ids['filter-campus'].value = '成都校区';
    s.ids['filter-admission-year'].value = '2024';
    s.ids['filter-as-of-date'].value = '2025-09-01';
    s.submit('缓考');
    assert.deepEqual(s.requests[0].body.filters, {
      campus: '成都校区', student_type: null, admission_year: 2024, as_of_date: '2025-09-01',
    });
    // user edits another control while the search is in flight
    s.ids['filter-student-type'].value = '全日制本科';
    s.requests[0].resolve(okResponse({
      filters: { campus: '成都校区', student_type: null, admission_year: 2024, as_of_date: '2025-09-01' },
      filter_summary: {
        active: true, document_total: 2, allowed_count: 1,
        excluded_counts: {}, counting_rules: '统计对象为文档', notes: [],
      },
    }));
    await flush(); // executeSearch success path fires loadStatus — let it finish
    await flush();
    // the status refresh must not have cleared any filter control
    assert.equal(s.ids['filter-campus'].value, '成都校区', 'campus survives status refresh');
    assert.equal(s.ids['filter-student-type'].value, '全日制本科', 'mid-flight edit survives status refresh');
    assert.equal(s.ids['filter-admission-year'].value, '2024', 'admission_year survives status refresh');
    assert.equal(s.ids['filter-as-of-date'].value, '2025-09-01', 'as_of_date survives status refresh');
    // the rendered snapshot stays bound to the submitted query
    assert.match(s.ids['results-area'].textContent, /条件：校区=成都校区/);
    // search again without touching the controls — conditions still sent
    s.submit('缓考');
    assert.deepEqual(s.requests[1].body.filters, {
      campus: '成都校区', student_type: '全日制本科', admission_year: 2024, as_of_date: '2025-09-01',
    }, 'second search keeps the original conditions');
    s.requests[1].resolve(okResponse());
    await flush();
    passed++;
  }

  // Test 10 (T011-R1 P1): when a selected option vanishes from the corpus
  // options, the constraint is kept and reported — never silently dropped.
  {
    const s = setup();
    await flush();
    s.ids['filter-admission-year'].value = '2024';
    s.submit('缓考');
    // option set changes while the search is in flight — 2024 disappears
    s.state.statusOptions = {
      campus: ['成都校区', '都江堰校区'],
      student_type: ['全日制本科'],
      admission_year: [2025],
    };
    s.requests[0].resolve(okResponse());
    await flush();
    await flush();
    assert.equal(s.ids['filter-admission-year'].value, '2024', 'vanished option keeps the constraint');
    // the kept constraint is a real option entry (real DOM needs it to hold value)
    const yearOpts = s.ids['filter-admission-year'].children;
    assert.ok(
      yearOpts.some(o => o.value === '2024' && o.textContent.indexOf('已不在当前选项') >= 0),
      'vanished selection stays as an option entry'
    );
    assert.match(s.ids['status-area'].textContent, /已不在当前语料选项/, 'user is told the option vanished');
    s.submit('缓考');
    assert.deepEqual(s.requests[1].body.filters, {
      campus: null, student_type: null, admission_year: 2024, as_of_date: null,
    }, 'next search still carries the vanished-but-kept condition');
    s.requests[1].resolve(okResponse());
    await flush();
    passed++;
  }

  // ---- T031: source selection (file scope snapshot, empty states, retry) ----
  const cat23 = {
    document_id: 'doc-2023', title: '转专业实施办法（2023）', version_label: '校教发〔2023〕1号',
    policy_group_id: 'g', published_at: null, effective_from: '2023-05-09', effective_to: null,
    is_synthetic: true,
  };
  const cat26 = {
    document_id: 'doc-2026', title: '转专业实施办法（2026）', version_label: '校教发〔2026〕1号',
    policy_group_id: 'g', published_at: null, effective_from: '2026-01-08', effective_to: null,
    is_synthetic: true,
  };
  const sourceSelected = (id, over = {}) => ({
    selected: true, document_id: id,
    title: id === 'doc-2023' ? cat23.title : cat26.title,
    version_label: id === 'doc-2023' ? cat23.version_label : cat26.version_label,
    policy_group_id: 'g', is_admitted: true,
    allowed_before_selection: 2, allowed_after_selection: 1,
    notes: ['仅在所选文件内检索；不代表该版本现行有效'],
    ...over,
  });

  // Scenario: select 2023 → submit carries the id; status refresh keeps the
  // selection; editing to 2026 does not rewrite the result snapshot line.
  {
    const s = setup();
    s.state.catalog = [cat23, cat26];
    await flush(); await flush();
    s.ids['source-mode'].value = 'doc';
    s.ids['source-mode'].listeners.change();
    s.ids['source-doc'].value = 'doc-2023';
    s.ids['source-doc'].listeners.change();
    s.submit('转专业 课程要求');
    assert.equal(s.requests[0].body.document_id, 'doc-2023', 'submit carries selected document_id');
    s.requests[0].resolve(okResponse({
      hits: [{ rank: 1, score: 1, preview_url: '/preview#doc-2023/b', matched_terms: [],
               chunk: { document_id: 'doc-2023', block_id: 'b', metadata: { title: cat23.title, version_label: cat23.version_label }, text: 'x' } }],
      document_id: 'doc-2023', source_selection: sourceSelected('doc-2023'),
    }));
    await flush(); await flush();
    assert.match(s.ids['results-area'].textContent, /指定文件：转专业实施办法（2023）/, 'result shows source snapshot');
    assert.equal(s.ids['source-doc'].value, 'doc-2023', 'status refresh after search keeps the selection');
    // edit controls after the search — old result line must not change
    s.ids['source-doc'].value = 'doc-2026';
    s.ids['source-doc'].listeners.change();
    assert.match(s.ids['results-area'].textContent, /转专业实施办法（2023）/, 'editing controls does not rewrite the old snapshot');
    passed++;
  }

  // Scenario: empty states distinguish excluded-file from in-file-no-hit.
  {
    const s = setup();
    s.state.catalog = [cat23, cat26];
    await flush(); await flush();
    s.ids['source-mode'].value = 'doc';
    s.ids['source-mode'].listeners.change();
    s.ids['source-doc'].value = 'doc-2026';
    s.ids['source-doc'].listeners.change();
    s.submit('课程');
    s.requests[0].resolve(okResponse({
      hits: [], document_id: 'doc-2026',
      source_selection: sourceSelected('doc-2026', { is_admitted: false, allowed_after_selection: 0 }),
    }));
    await flush();
    assert.match(s.ids['results-area'].textContent, /所选文件被适用条件排除/, 'excluded file gets its own empty state');
    s.submit('课程');
    s.requests[1].resolve(okResponse({
      hits: [], document_id: 'doc-2026',
      source_selection: sourceSelected('doc-2026'),
    }));
    await flush();
    assert.match(s.ids['results-area'].textContent, /所选文件内没有检索命中/, 'in-file no-hit is distinct');
    passed++;
  }

  // Scenario: failure retry reuses the submitted source snapshot, not the
  // edited control.
  {
    const s = setup();
    s.state.catalog = [cat23, cat26];
    await flush(); await flush();
    s.ids['source-mode'].value = 'doc';
    s.ids['source-mode'].listeners.change();
    s.ids['source-doc'].value = 'doc-2023';
    s.ids['source-doc'].listeners.change();
    s.submit('转专业');
    s.requests[0].resolve({ ok: false, status: 503, json: async () => ({ message: '检索不可用' }) });
    await flush();
    // user edits the selector while the failure state is shown
    s.ids['source-doc'].value = 'doc-2026';
    const retryBtn = findButton(s.ids['results-area']);
    assert.ok(retryBtn, 'retry button shown on failure');
    retryBtn.listeners.click();
    await flush();
    assert.equal(s.requests[1].body.document_id, 'doc-2023', 'retry uses the submitted snapshot source');
    s.requests[1].resolve(okResponse({ document_id: 'doc-2023', source_selection: sourceSelected('doc-2023') }));
    await flush();
    passed++;
  }

  // ---- T031-R1: restore chains (native select semantics) ----

  // Chain A (ask→search direction): URL carries student_type + valid file;
  // controls keep both after options load; explicit submit carries originals.
  {
    const s = setup('?query=申请转专业&student_type=本科&document_id=doc-2023', {
      catalog: [cat23, cat26],
      statusOptions: { campus: ['成都校区'], student_type: ['本科'], admission_year: [2023] },
    });
    await flush(); await flush();
    assert.equal(s.ids['filter-student-type'].value, '本科', 'URL student_type restored AFTER options load');
    assert.equal(s.ids['source-mode'].value, 'doc');
    assert.equal(s.ids['source-doc'].value, 'doc-2023', 'URL document_id restored from catalog');
    s.submit('申请转专业 课程要求');
    assert.equal(s.requests.length, 1, 'submit allowed after restore completed');
    assert.equal(s.requests[0].body.document_id, 'doc-2023');
    assert.deepEqual(s.requests[0].body.filters, {
      campus: null, student_type: '本科', admission_year: null, as_of_date: null,
    }, 'explicit submit still carries the restored condition');
    s.requests[0].resolve(okResponse({ document_id: 'doc-2023', source_selection: sourceSelected('doc-2023') }));
    await flush();
    passed++;
  }

  // Chain B: invalid document_id in URL — kept as explicit unavailable
  // selection and submitted as the ORIGINAL id (server 422), never null/all.
  {
    const s = setup('?query=申请转专业&document_id=unavailable-review-file', {
      catalog: [cat23, cat26],
      statusOptions: { campus: [], student_type: ['本科'], admission_year: [] },
    });
    await flush(); await flush();
    assert.equal(s.ids['source-doc'].value, 'unavailable-review-file',
      'stale id preserved as an explicit option value (native select keeps added option)');
    assert.match(s.ids['source-hint'].textContent, /已失效|保留/, 'stale-id warning shown');
    s.submit('申请转专业');
    assert.equal(s.requests.length, 1);
    assert.equal(s.requests[0].body.document_id, 'unavailable-review-file',
      'submit carries the ORIGINAL id for server 422 — never document_id=null');
    s.requests[0].resolve({
      ok: false, status: 422,
      json: async () => ({ message: 'document_id 不在当前成功解析的文档目录中: unavailable-review-file' }),
    });
    await flush();
    assert.match(s.ids['results-area'].textContent, /不在当前成功解析的文档目录/, '422 message surfaces');
    passed++;
  }

  // Chain C: catalog delay — submit is blocked (no request with lost
  // conditions) until restore completes; then the originals are sent.
  {
    const s = setup('?student_type=本科&document_id=doc-2023', {
      catalog: [cat23, cat26], deferCatalog: true,
      statusOptions: { campus: ['成都校区'], student_type: ['本科'], admission_year: [2023] },
    });
    await flush(); // status loaded (filters applied); catalog still pending
    s.submit('申请转专业');
    assert.equal(s.requests.length, 0, 'submit blocked while catalog/restore pending');
    assert.match(s.ids['results-area'].textContent, /暂不提交|正在恢复/, 'block reason shown');
    s.state.releaseCatalog();
    await flush(); await flush();
    s.submit('申请转专业');
    assert.equal(s.requests.length, 1);
    assert.equal(s.requests[0].body.document_id, 'doc-2023');
    assert.equal(s.requests[0].body.filters.student_type, '本科',
      'delayed restore still delivers both conditions on submit');
    s.requests[0].resolve(okResponse({ document_id: 'doc-2023', source_selection: sourceSelected('doc-2023') }));
    await flush();
    passed++;
  }

  // Chain D: 指定文件 mode with no file chosen — blocked, never silently
  // submitted as all-documents.
  {
    const s = setup('', { catalog: [cat23, cat26] });
    await flush(); await flush();
    s.ids['source-mode'].value = 'doc';
    s.ids['source-mode'].listeners.change();
    s.submit('申请转专业');
    assert.equal(s.requests.length, 0, 'doc mode without a file never submits');
    assert.match(s.ids['results-area'].textContent, /请选择文件|切换回/, 'explicit completion hint shown');
    // explicit switch back to all is allowed
    s.ids['source-mode'].value = 'all';
    s.ids['source-mode'].listeners.change();
    s.submit('申请转专业');
    assert.equal(s.requests.length, 1);
    assert.equal(s.requests[0].body.document_id, undefined, 'explicit all-mode submits without document_id');
    s.requests[0].resolve(okResponse());
    await flush();
    passed++;
  }


  // ---- T038: candidate panel — snapshot-bound, explicit-only, seq-guarded ----
  const candBody = r => r.body;
  {
    const s = setup();
    await flush();
    // formal with a date filter
    s.ids['filter-as-of-date'].value = '2026-10-03';
    s.submit('转专业');
    assert.equal(s.requests.length, 1, 'only the formal request is sent (candidates never auto-run)');
    s.requests[0].resolve(okResponse({
      filters: { campus: null, student_type: null, admission_year: null, as_of_date: '2026-10-03' },
      hits: [{ rank: 1, score: 1, preview_url: '/preview#d/b', matched_terms: [],
               chunk: { document_id: 'd', block_id: 'b', metadata: { title: 'T', version_label: 'v' }, text: 'x',
                        locator: { type: 'pdf_page', page: 1 } } }],
    }));
    await flush();
    assert.ok(s.ids['candidate-area'].children.length > 0, 'candidate panel shown after formal success');
    // edit controls AFTER formal submit
    s.ids['filter-as-of-date'].value = '2020-01-01';
    // find the candidate button and date checkbox inside the panel
    const panel = s.ids['candidate-area'];
    const btnsIn = [];
    const walkP = e => { for (const c of (e.children || [])) { if (c.tag === 'button') btnsIn.push(c); walkP(c); } };
    walkP(panel);
    const candBtn = btnsIn.find(b => b.textContent === '查看候选原文');
    assert.ok(candBtn, 'candidate button present');
    // find checkboxes (inputs) — set the date one
    const inputs = [];
    const walkI = e => { for (const c of (e.children || [])) { if (c.tag === 'input') inputs.push(c); walkI(c); } };
    walkI(panel);
    assert.equal(inputs.length, 2, 'two uncertainty checkboxes');
    assert.equal(inputs[0].disabled, false, 'date checkbox enabled (snapshot has as_of)');
    assert.equal(inputs[1].disabled, true, 'student_type checkbox disabled (snapshot lacks it)');
    inputs[0].checked = true;
    candBtn.listeners.click();
    await flush();
    assert.equal(s.requests.length, 2, 'candidate request sent only after explicit click');
    const creq = s.requests[1];
    assert.equal(creq.url, '/api/v1/search/candidates');
    assert.deepEqual(creq.body.uncertainty_dimensions, ['date']);
    assert.equal(creq.body.filters.as_of_date, '2026-10-03', 'candidate uses the RESULT snapshot filters (not edited controls)');
    creq.resolve({ ok: true, status: 200, json: async () => ({
      query: '转专业', uncertainty_dimensions: ['date'], active_dimensions: ['date'],
      filters: { campus: null, student_type: null, admission_year: null, as_of_date: '2026-10-03' },
      document_id: null,
      candidate_summary: { document_total: 20, strict_allowed_count: 5, candidate_document_count: 1, counting_rules: 'r' },
      disclaimer: '未通过所选日期或学生类型条件核实，仅供原文核对，不作为已确认适用的答案依据',
      hits: [{ rank: 1, score: 1, preview_url: '/preview#d/b', unknown_dimensions: ['date'], uncertainty_note: 'n',
               chunk: { document_id: 'd', block_id: 'b', metadata: { title: '未核实资料', version_label: '未标注', scope: {} },
                        text: '候选原文', locator: null } }],
    }) });
    await flush();
    assert.ok(panel.children.length > 0, 'candidate results rendered');
    passed++;
  }

  // stale candidate response must not attach to a NEW result
  {
    const s = setup();
    await flush();
    s.ids['filter-as-of-date'].value = '2026-10-03';
    s.submit('A');
    s.requests[0].resolve(okResponse({
      filters: { campus: null, student_type: null, admission_year: null, as_of_date: '2026-10-03' },
    }));
    await flush();
    const panel = s.ids['candidate-area'];
    const btnsIn = [];
    const walkP = e => { for (const c of (e.children || [])) { if (c.tag === 'button') btnsIn.push(c); walkP(c); } };
    walkP(panel);
    const inputs = [];
    const walkI = e => { for (const c of (e.children || [])) { if (c.tag === 'input') inputs.push(c); walkI(c); } };
    walkI(panel);
    inputs[0].checked = true;
    btnsIn.find(b => b.textContent === '查看候选原文').listeners.click();
    await flush();
    // new formal submit BEFORE the candidate response resolves
    s.submit('B');
    assert.equal(s.ids['candidate-area'].children.length, 0, 'new formal request clears old candidates');
    s.requests[2].resolve(okResponse({
      filters: { campus: null, student_type: null, admission_year: null, as_of_date: '2026-10-03' },
    }));
    await flush();
    // now let the stale candidate response land
    s.requests[1].resolve({ ok: true, status: 200, json: async () => ({
      query: 'A', uncertainty_dimensions: ['date'], active_dimensions: ['date'], filters: {}, document_id: null,
      candidate_summary: { document_total: 20, strict_allowed_count: 5, candidate_document_count: 1, counting_rules: 'r' },
      disclaimer: 'x', hits: [{ rank: 1, score: 1, preview_url: '', unknown_dimensions: ['date'], uncertainty_note: '',
               chunk: { document_id: 'd', block_id: 'b', metadata: {}, text: '旧候选' } }],
    }) });
    await flush();
    const txt = s.ids['candidate-area'].textContent;
    assert.ok(txt.indexOf('旧候选') < 0, 'stale candidate response does NOT attach to the new result');
    passed++;
  }

  // ---- T043-R1: 导航上下文快照——URL 恢复后无需提交即可原样跨页；控件编辑不改写快照 ----
  {
    const s = setup('?query=original&student_type=%E6%9C%AC%E7%A7%91&include_unknown_type=0', {
      statusOptions: { campus: [], student_type: ['本科'], admission_year: [] },
    });
    await flush();
    assert.equal(s.ids['include-unknown-type'].checked, false, 'URL 恢复：开关=关（strict）');
    const nav0 = new URL(s.ids['nav-ask'].href, 'http://local');
    assert.equal(nav0.searchParams.get('include_unknown_type'), '0', 'URL 恢复后不提交，跨页链接仍是 strict');
    assert.equal(nav0.searchParams.get('query'), 'original', '跨页链接保留问题');
    assert.equal(nav0.searchParams.get('student_type'), '本科', '跨页链接保留条件');
    // 提交携带新开关（strict）
    s.submit('original');
    assert.equal(s.requests[0].body.include_unknown_student_type, false, '提交携带开关=strict');
    s.requests[0].resolve(okResponse({
      include_unknown_student_type: false,
      filters: { campus: null, student_type: '本科', admission_year: null, as_of_date: null },
    }));
    await flush();
    // 提交后改控件 → 导航仍用原快照
    s.ids['include-unknown-type'].checked = true;
    assert.equal(new URL(s.ids['nav-ask'].href, 'http://local').searchParams.get('include_unknown_type'), '0',
      '改控件不改写已显示结果的导航快照');
    // 候选参数按结果快照模式
    const panel = s.ids['candidate-area'];
    const btnsIn = [];
    const walkP = e => { for (const c of (e.children || [])) { if (c.tag === 'button') btnsIn.push(c); walkP(c); } };
    walkP(panel);
    const inputs = [];
    const walkI = e => { for (const c of (e.children || [])) { if (c.tag === 'input') inputs.push(c); walkI(c); } };
    walkI(panel);
    const typeCb = inputs[1];
    assert.equal(typeCb.disabled, false, 'student_type 候选框按结果快照启用');
    typeCb.checked = true;
    btnsIn.find(b => b.textContent === '查看候选原文').listeners.click();
    await flush();
    const creq = s.requests[1];
    assert.equal(creq.url, '/api/v1/search/candidates');
    assert.equal(creq.body.include_unknown_student_type, false, '候选请求按结果快照模式（strict）');
    creq.resolve({ ok: true, status: 200, json: async () => ({
      query: 'original', uncertainty_dimensions: ['student_type'], active_dimensions: ['student_type'],
      filters: { campus: null, student_type: '本科', admission_year: null, as_of_date: null },
      document_id: null,
      candidate_summary: { document_total: 20, strict_allowed_count: 5, candidate_document_count: 1, counting_rules: 'r' },
      disclaimer: '未通过所选日期或学生类型条件核实', hits: [],
    }) });
    await flush();
    passed++;
  }

  console.log(`check-search-behavior: ${passed} scenarios passed`);
  process.exit(0);
})().catch(e => {
  console.error('FAIL:', e.message);
  process.exit(1);
});
