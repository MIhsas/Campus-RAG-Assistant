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

function setup() {
  const ids = {};
  for (const id of ['query-input', 'search-btn', 'status-area', 'results-area',
                    'filter-campus', 'filter-student-type', 'filter-admission-year',
                    'filter-as-of-date', 'clear-filters-btn']) {
    ids[id] = new Element();
  }
  const modeSelector = new Element('div');
  for (const m of ['bm25', 'dense', 'hybrid']) {
    const b = new Element('button', { 'data-mode': m });
    b.className = 'mode-btn' + (m === 'bm25' ? ' active' : '');
    modeSelector.appendChild(b);
  }
  ids['mode-selector'] = modeSelector;

  const requests = [];
  const state = {
    statusOptions: {
      campus: ['成都校区', '都江堰校区'],
      student_type: ['全日制本科'],
      admission_year: [2024, 2025],
    },
  };
  const context = {
    document: {
      getElementById: id => ids[id],
      createElement: t => new Element(t),
      createTextNode: t => { const e = new Element(); e.textContent = t; return e; },
    },
    fetch: (url, options) => {
      if (!options) {
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
        requests.push({ body: JSON.parse(options.body), resolve, reject });
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

  console.log(`check-search-behavior: ${passed} scenarios passed`);
  process.exit(0);
})().catch(e => {
  console.error('FAIL:', e.message);
  process.exit(1);
});
