// Async behavior regression for the compare page (T017).
// Minimal DOM/fetch/clipboard stub — not real browser evidence.
// Covers: group/version selection → compare request with ids, explicit
// change-type labels (not color-only), swap flips sides, default
// changes-only vs show-all, copy summary, failure never shows stale result
// as a new success, and submit-time snapshot binding.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');

const html = fs.readFileSync(
  path.resolve(__dirname, '../src/campus_assistant/static/compare.html'),
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
    this.checked = false;
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
      for (const c of e.children) {
        if (c.matches(sel)) out.push(c);
        walk(c);
      }
    };
    walk(this);
    return out;
  }
  set textContent(v) { this.text = String(v); this.children = []; }
  get textContent() { return this.text + this.children.map(c => c.textContent).join(''); }
  set innerHTML(v) { this.text = String(v); this.children = []; }
}

function setup() {
  const ids = {};
  for (const id of ['group-select', 'left-select', 'right-select', 'swap-btn',
                    'compare-btn', 'show-all-toggle', 'result-area']) {
    ids[id] = new Element(id.endsWith('-btn') ? 'button' : (id.endsWith('-select') || id.includes('toggle') ? 'select' : 'div'));
  }
  const requests = [];
  const state = {
    groups: {
      groups: [
        { policy_group_id: 'syn-cmp-defer', versions: [
          { document_id: 'cmp-defer-v1', version_label: '虚构 2024 版', published_at: '2024-01-01', effective_from: '2024-03-01', effective_to: '2025-02-28', title: '缓考申请办法（虚构测试）', is_synthetic: true },
          { document_id: 'cmp-defer-v2', version_label: '虚构 2025 版', published_at: '2025-01-01', effective_from: '2025-03-01', effective_to: null, title: '缓考申请办法（虚构测试）', is_synthetic: true },
        ]},
        { policy_group_id: 'syn-cmp-grades', versions: [
          { document_id: 'cmp-grades-1', version_label: '虚构 v1', published_at: null, effective_from: null, effective_to: null, title: '成绩登记须知（虚构测试）', is_synthetic: true },
        ]},
      ],
    },
    compareResponse: null,
    clipboardMode: 'ok',
    copiedText: null,
  };
  const context = {
    document: {
      getElementById: id => ids[id] || null,
      createElement: t => new Element(t),
      createTextNode: t => { const e = new Element(); e.textContent = t; return e; },
    },
    navigator: {
      clipboard: {
        writeText: t => {
          if (state.clipboardMode === 'reject') return Promise.reject(new Error('denied'));
          state.copiedText = t;
          return Promise.resolve();
        },
      },
    },
    fetch: (url, options) => {
      if (!options) {
        return Promise.resolve({ ok: true, status: 200, json: async () => state.groups });
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

const sideRef = (text, over = {}) => ({
  document_id: 'cmp-defer-v1', block_id: 'b1', char_start: 0, char_end: text.length,
  text, kind: 'paragraph', document_sha256: 'a'.repeat(64),
  preview_url: '/preview#cmp-defer-v1/b1', ...over,
});

const compareOk = () => ({
  left: { document_id: 'cmp-defer-v1', policy_group_id: 'syn-cmp-defer', title: '缓考申请办法（虚构测试）',
    version_label: '虚构 2024 版', published_at: '2024-01-01', effective_from: '2024-03-01', effective_to: '2025-02-28',
    scope: { campus: ['成都校区'], student_type: ['全日制本科'], admission_years: [2022, 2023] },
    document_sha256: 'a'.repeat(64), is_synthetic: true, source_url: 'https://example.org/cmp/v1' },
  right: { document_id: 'cmp-defer-v2', policy_group_id: 'syn-cmp-defer', title: '缓考申请办法（虚构测试）',
    version_label: '虚构 2025 版', published_at: '2025-01-01', effective_from: '2025-03-01', effective_to: null,
    scope: { campus: ['成都校区'], student_type: ['全日制本科'], admission_years: [2023, 2024] },
    document_sha256: 'b'.repeat(64), is_synthetic: true, source_url: 'https://example.org/cmp/v2' },
  counts: { added: 1, deleted: 1, modified: 1, unchanged: 3 },
  entries: [
    { diff_id: 'D1', change_type: 'unchanged', clause_key: '第一条', diff_segments: null,
      left: sideRef('第一条 本办法所称缓考。'), right: sideRef('第一条 本办法所称缓考。', { document_id: 'cmp-defer-v2', preview_url: '/preview#cmp-defer-v2/b1' }) },
    { diff_id: 'D2', change_type: 'modified', clause_key: '第二条',
      diff_segments: [{ op: 'equal', text: '第二条 缓考申请须在考试前 ' }, { op: 'delete', text: '5' }, { op: 'insert', text: '3' }, { op: 'equal', text: ' 个工作日提交。' }],
      left: sideRef('第二条 缓考申请须在考试前 5 个工作日提交。'),
      right: sideRef('第二条 缓考申请须在考试前 3 个工作日提交。', { document_id: 'cmp-defer-v2', preview_url: '/preview#cmp-defer-v2/b2' }) },
    { diff_id: 'D3', change_type: 'deleted', clause_key: '第三条', diff_segments: null,
      left: sideRef('第三条 申请缓考须同时提交书面情况说明。'), right: null },
    { diff_id: 'D4', change_type: 'added', clause_key: '第四条', diff_segments: null,
      left: null, right: sideRef('第四条 学院应在收到申请后 3 个工作日内完成审批。', { document_id: 'cmp-defer-v2', preview_url: '/preview#cmp-defer-v2/b3' }) },
  ],
  algorithm: { note: '对齐顺序…', limitations: ['条款重编号会被识别为删除+新增。'] },
  disclaimer: '文字差异对比：不判断哪个版本适用于某个学生；日期较新不等于现行有效；差异不构成资格或政策适用结论。',
});

(async () => {
  let passed = 0;

  // Scenario 1: groups load → compare → labels/counts/texts/preview/snapshot
  {
    const s = setup();
    await flush();
    assert.match(s.ids['group-select'].textContent, /syn-cmp-defer/);
    assert.match(s.ids['left-select'].textContent, /cmp-defer-v1/);
    assert.match(s.ids['right-select'].textContent, /cmp-defer-v2/);
    s.ids['left-select'].value = 'cmp-defer-v1';
    s.ids['right-select'].value = 'cmp-defer-v2';
    s.ids['compare-btn'].listeners.click();
    await flush();
    assert.equal(s.requests.length, 1);
    assert.deepEqual(s.requests[0].body, { left_document_id: 'cmp-defer-v1', right_document_id: 'cmp-defer-v2' });
    s.requests[0].resolve(ok(compareOk()));
    await flush();
    const txt = s.ids['result-area'].textContent;
    assert.match(txt, /对比快照：左 cmp-defer-v1（虚构 2024 版） ↔ 右 cmp-defer-v2（虚构 2025 版）/);
    assert.match(txt, /新增 1 条/);
    assert.match(txt, /删除 1 条/);
    assert.match(txt, /修改 1 条/);
    assert.match(txt, /未变 3 条/, 'overview shows true unchanged count even when entries hidden');
    // explicit labels (not color-only)
    assert.match(txt, /修改/);
    assert.match(txt, /新增/);
    assert.match(txt, /删除/);
    assert.match(txt, /第二条 缓考申请须在考试前 5 个工作日提交。/);
    assert.match(txt, /查看原文/);
    assert.match(txt, /日期较新不等于现行有效/);
    // default: unchanged entries hidden
    assert.ok(!/第一条 本办法所称缓考。/.test(txt), 'unchanged hidden by default');
    passed++;
  }

  // Scenario 2: swap flips sides in the next request
  {
    const s = setup();
    await flush();
    s.ids['left-select'].value = 'cmp-defer-v1';
    s.ids['right-select'].value = 'cmp-defer-v2';
    s.ids['swap-btn'].listeners.click();
    assert.equal(s.ids['left-select'].value, 'cmp-defer-v2');
    assert.equal(s.ids['right-select'].value, 'cmp-defer-v1');
    s.ids['compare-btn'].listeners.click();
    await flush();
    assert.deepEqual(s.requests[0].body, { left_document_id: 'cmp-defer-v2', right_document_id: 'cmp-defer-v1' });
    passed++;
  }

  // Scenario 3: show-all reveals unchanged entries
  {
    const s = setup();
    await flush();
    s.ids['compare-btn'].listeners.click();
    await flush();
    s.requests[0].resolve(ok(compareOk()));
    await flush();
    assert.ok(!/第一条 本办法所称缓考。/.test(s.ids['result-area'].textContent));
    s.ids['show-all-toggle'].checked = true;
    s.ids['show-all-toggle'].listeners.change();
    assert.match(s.ids['result-area'].textContent, /第一条 本办法所称缓考。/, 'show-all renders unchanged');
    assert.match(s.ids['result-area'].textContent, /未变/);
    passed++;
  }

  // Scenario 4: copy summary contains identities, types, clause texts
  {
    const s = setup();
    await flush();
    s.ids['compare-btn'].listeners.click();
    await flush();
    s.requests[0].resolve(ok(compareOk()));
    await flush();
    const copyBtn = s.ids['result-area'].querySelectorAll('button').find(b => b.textContent === '复制差异摘要');
    assert.ok(copyBtn);
    copyBtn.listeners.click();
    await flush();
    assert.ok(s.state.copiedText);
    assert.match(s.state.copiedText, /版本对比摘要/);
    assert.match(s.state.copiedText, /左：cmp-defer-v1（虚构 2024 版）/);
    assert.match(s.state.copiedText, /右：cmp-defer-v2（虚构 2025 版）/);
    assert.match(s.state.copiedText, /【修改】第二条/);
    assert.match(s.state.copiedText, /【删除】第三条/);
    assert.match(s.state.copiedText, /【新增】第四条/);
    assert.match(s.state.copiedText, /5 个工作日/);
    assert.match(s.state.copiedText, /cmp-defer-v1\/b1/);
    assert.match(s.state.copiedText, /不代表资格或政策适用结论/);
    passed++;
  }

  // Scenario 5: failure shows error and never presents stale result as new
  {
    const s = setup();
    await flush();
    s.ids['compare-btn'].listeners.click();
    await flush();
    s.requests[0].resolve(ok(compareOk()));
    await flush();
    assert.match(s.ids['result-area'].textContent, /对比快照/);
    // second compare fails
    s.ids['left-select'].value = 'cmp-defer-v1';
    s.ids['right-select'].value = 'cmp-grades-1';
    s.ids['compare-btn'].listeners.click();
    await flush();
    assert.ok(!/对比快照/.test(s.ids['result-area'].textContent), 'stale result cleared at request start');
    s.requests[1].resolve({ ok: false, status: 400, json: async () => ({ code: 'CROSS_POLICY_GROUP', message: '只能比较同一政策分组下的版本' }) });
    await flush();
    assert.match(s.ids['result-area'].textContent, /只能比较同一政策分组下的版本/);
    assert.match(s.ids['result-area'].textContent, /未生成新比较结果/);
    assert.ok(!/对比快照/.test(s.ids['result-area'].textContent), 'no stale result after failure');
    passed++;
  }

  console.log(`check-comparison-behavior: ${passed} scenarios passed`);
  process.exit(0);
})().catch(e => {
  console.error('FAIL:', e.message);
  console.error(e.stack);
  process.exit(1);
});
