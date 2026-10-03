// Async behavior regression for the ask (evidence organizing) page.
// Minimal DOM/fetch/clipboard stub — not real browser coverage and NOT a
// real LLM demo: the generated-path scenario uses a controlled response
// purely to prove rendering of the paragraph+citation contract.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');

const html = fs.readFileSync(
  path.resolve(__dirname, '../src/campus_assistant/static/ask.html'),
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

// Uniform event trigger (this stub keeps listeners on elements).
function trigger(el, name, evt) {
  const fn = el.listeners && el.listeners[name];
  if (typeof fn === 'function') fn(evt || {});
}

// Generic 200 responder for non-/ask endpoints (ASR etc.).
const ok = (payload) => ({ ok: true, status: 200, json: async () => payload });

function setup(locationSearch, stateOverrides) {
  const ids = {};
  for (const id of ['query-input', 'ask-btn', 'generate-btn', 'status-area', 'results-area',
                    'filter-campus', 'filter-student-type', 'filter-admission-year',
                    'filter-as-of-date', 'clear-filters-btn',
                    'history-toggle', 'history-clear-btn', 'history-note', 'history-list',
                    'record-btn', 'record-stop-btn', 'record-cancel-btn',
                    'audio-file', 'transcribe-btn', 'voice-hint', 'transcript-area']) {
    ids[id] = new Element(id.endsWith('-btn') ? 'button' : 'div');
  }
  const modeSelector = new Element('div');
  for (const m of ['bm25', 'dense', 'hybrid']) {
    const b = new Element('button', { 'data-mode': m });
    b.className = 'mode-btn' + (m === 'bm25' ? ' active' : '');
    modeSelector.appendChild(b);
  }
  ids['mode-selector'] = modeSelector;

  const requests = [];
  const storage = {};
  const state = {
    generatorConfigured: false,
    proceduresConfigured: true, // T022-R1: related entry only for configured items
    clipboardMode: 'ok', // 'ok' | 'reject'
    copiedText: null,
    storageFailWrites: false,
    getUserMediaMode: 'ok', // 'ok' | 'reject' | 'unsupported'
    trackStops: 0,
    recorderStarts: 0,
    asrStatus: {
      configured: true,
      provider: 'mock-asr（模拟，非真实识别）',
      model: 'mock-asr-model',
    },
    statusOptions: {
      campus: ['成都校区', '都江堰校区'],
      student_type: ['全日制本科'],
      admission_year: [2023, 2024],
    },
  };
  if (stateOverrides) Object.assign(state, stateOverrides);
  class MockBlob {
    constructor(parts, opts = {}) {
      this.type = opts.type || '';
      this.size = (parts && parts[0] && parts[0].size) || 2048;
    }
  }
  class MockMediaRecorder {
    constructor(stream, opts = {}) {
      this.stream = stream;
      this.mimeType = (opts && opts.mimeType) || 'audio/webm';
      this.state = 'inactive';
      this.ondataavailable = null;
      this.onstop = null;
      this.onerror = null;
    }
    start() { this.state = 'recording'; state.recorderStarts++; }
    stop() {
      this.state = 'inactive';
      if (this.ondataavailable) this.ondataavailable({ data: { size: 2048, type: this.mimeType } });
      if (this.onstop) this.onstop();
    }
  }
  MockMediaRecorder.isTypeSupported = t => t === 'audio/webm;codecs=opus';
  const context = {
    document: {
      getElementById: id => {
        if (ids[id]) return ids[id];
        const find = e => {
          for (const c of e.children) {
            if (c.id === id) return c;
            const r = find(c);
            if (r) return r;
          }
          return null;
        };
        return find(ids['results-area']) || find(ids['history-list']);
      },
      createElement: t => new Element(t),
      createTextNode: t => { const e = new Element(); e.textContent = t; return e; },
    },
    localStorage: {
      getItem: k => (k in storage ? storage[k] : null),
      setItem: (k, v) => {
        if (state.storageFailWrites) throw new Error('storage unavailable');
        storage[k] = String(v);
      },
      removeItem: k => { delete storage[k]; },
      clear: () => { for (const k of Object.keys(storage)) delete storage[k]; },
    },
    navigator: {
      clipboard: {
        writeText: t => {
          if (state.clipboardMode === 'reject') return Promise.reject(new Error('denied'));
          state.copiedText = t;
          return Promise.resolve();
        },
      },
      mediaDevices: {
        getUserMedia: async () => {
          if (state.getUserMediaMode === 'reject') throw new Error('Permission denied');
          return {
            getTracks: () => [{ stop: () => { state.trackStops++; } }],
          };
        },
      },
    },
    Blob: MockBlob,
    MediaRecorder: MockMediaRecorder,
    setTimeout: (fn, ms) => setTimeout(fn, ms),
    clearTimeout: t => clearTimeout(t),
    location: { search: locationSearch || '' },
    fetch: (url, options) => {
      if (!options) {
        if (String(url).indexOf('/asr/status') >= 0) {
          return Promise.resolve({ ok: true, status: 200, json: async () => state.asrStatus });
        }
        if (String(url).indexOf('/api/v1/procedures') >= 0) {
          // T022-R1: configured vs unconfigured branches for related entry gating
          if (state.proceduresConfigured) {
            return Promise.resolve({
              ok: true, status: 200,
              json: async () => ({ configured: true, procedures: [
                { procedure_id: 'proc-apply-defer', title: '缓考申请' },
                { procedure_id: 'proc-review-grade', title: '成绩复核' },
              ] }),
            });
          }
          return Promise.resolve({
            ok: false, status: 503,
            json: async () => ({ code: 'PROCEDURES_NOT_CONFIGURED' }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({
            corpus_status: 'ready',
            answer_mode_default: 'extractive',
            answer_modes_available: state.generatorConfigured ? ['extractive', 'generated'] : ['extractive'],
            generator_configured: state.generatorConfigured,
            available_modes: ['bm25', 'dense', 'hybrid'],
            filter_options: state.statusOptions,
          }),
        });
      }
      return new Promise((resolve, reject) => {
        requests.push({
          url,
          body: typeof options.body === 'string' ? JSON.parse(options.body) : options.body,
          resolve, reject,
        });
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

const evidenceItem = (id, over = {}) => ({
  evidence_id: id, text: '缓考申请原文摘录', document_id: 'doc-1', block_id: 'b1',
  chunk_id: 'c1', char_start: 0, char_end: 8,
  document_sha256: 'a'.repeat(64), title: '缓考办法', source_url: 'https://example.org/p',
  version_label: 'v1', scope: { campus: ['成都校区'], student_type: [], admission_years: [] },
  published_at: '2025-01-01', effective_from: '2025-03-01', effective_to: null,
  is_synthetic: true, preview_url: '/preview#doc-1/b1', ...over,
});

const okResponse = (over = {}) => ({
  ok: true,
  status: 200,
  json: async () => ({
    query: '缓考申请', query_tokens: ['缓考'], mode: 'bm25', answer_mode: 'extractive',
    status: 'evidence_only', answer: null, answer_error: null,
    disclaimer: '以下是相关原文摘录，尚未生成答案，需核对适用条件。',
    evidence: [evidenceItem('E1')], evidence_state: 'ok',
    empty_message: null, insufficient_reason: null,
    budget: { max_items: 5, max_total_chars: 6000, included_items: 1, included_chars: 8, skipped_items: 0, duplicate_chunks: 0 },
    filters: null,
    filter_summary: { active: false, document_total: 1, allowed_count: 1, excluded_counts: {}, counting_rules: '统计对象为文档', notes: [] },
    ...over,
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

  // Scenario 1: extractive ask — label, disclaimer, evidence card, snapshot
  {
    const s = setup();
    await flush();
    s.ids['filter-admission-year'].value = '2023';
    s.submit('缓考申请');
    assert.equal(s.requests[0].body.answer_mode, 'extractive');
    assert.deepEqual(s.requests[0].body.filters, {
      campus: null, student_type: null, admission_year: 2023, as_of_date: null,
    });
    s.requests[0].resolve(okResponse({
      filters: { campus: null, student_type: null, admission_year: 2023, as_of_date: null },
    }));
    await flush();
    const txt = s.ids['results-area'].textContent;
    assert.match(txt, /原文摘录 \/ 未生成答案/);
    assert.match(txt, /尚未生成答案，需核对适用条件/);
    assert.match(txt, /E1/);
    assert.match(txt, /缓考申请原文摘录/);
    assert.match(txt, /查看原文/);
    assert.match(txt, /问题：缓考申请/);
    assert.match(txt, /条件：年级=2023/);
    passed++;
  }

  // Scenario 2 (T011-R1 rule): status refresh after success must not clear
  // filters; the next ask still carries the same conditions.
  {
    const s = setup();
    await flush();
    s.ids['filter-campus'].value = '成都校区';
    s.ids['filter-admission-year'].value = '2023';
    s.submit('缓考申请');
    s.requests[0].resolve(okResponse({
      filters: { campus: '成都校区', student_type: null, admission_year: 2023, as_of_date: null },
    }));
    await flush();
    await flush(); // post-success status refresh finished
    assert.equal(s.ids['filter-campus'].value, '成都校区', 'campus survives status refresh');
    assert.equal(s.ids['filter-admission-year'].value, '2023', 'year survives status refresh');
    s.submit('缓考申请');
    assert.deepEqual(s.requests[1].body.filters, {
      campus: '成都校区', student_type: null, admission_year: 2023, as_of_date: null,
    }, 'next ask keeps the conditions');
    s.requests[1].resolve(okResponse());
    await flush();
    passed++;
  }

  // Scenario 3: failure retry uses the submitted snapshot (query/mode/filters)
  {
    const s = setup();
    await flush();
    const modeBtns = s.ids['mode-selector'].querySelectorAll('.mode-btn');
    s.ids['mode-selector'].listeners.click({ target: modeBtns[1] }); // dense
    s.ids['filter-campus'].value = '成都校区';
    s.submit('original');
    s.requests[0].reject(new Error('network'));
    await flush();
    s.ids['query-input'].value = 'draft';
    s.ids['filter-campus'].value = '';
    s.ids['mode-selector'].listeners.click({ target: modeBtns[0] });
    const retryBtn = findButton(s.ids['results-area']);
    assert.ok(retryBtn, 'retry button should exist');
    retryBtn.listeners.click();
    await flush();
    assert.equal(s.requests[1].body.query, 'original');
    assert.equal(s.requests[1].body.mode, 'dense');
    assert.deepEqual(s.requests[1].body.filters, {
      campus: '成都校区', student_type: null, admission_year: null, as_of_date: null,
    });
    s.requests[1].resolve(okResponse());
    await flush();
    assert.match(s.ids['results-area'].textContent, /问题：original/);
    passed++;
  }

  // Scenario 4: copy assembles question + conditions + sourced excerpts;
  // copy failure gives an explicit message
  {
    const s = setup();
    s.submit('缓考申请');
    s.requests[0].resolve(okResponse());
    await flush();
    const copyBtn = s.ids['results-area'].querySelectorAll('button')
      .find(b => b.textContent === '复制问题与摘录');
    assert.ok(copyBtn, 'copy button should exist');
    copyBtn.listeners.click();
    await flush();
    assert.ok(s.state.copiedText, 'text was copied');
    assert.match(s.state.copiedText, /问题：缓考申请/);
    assert.match(s.state.copiedText, /【E1】/);
    assert.match(s.state.copiedText, /来源：https:\/\/example.org\/p/);
    assert.match(s.state.copiedText, /原文：/);
    assert.match(s.ids['results-area'].textContent, /已复制为纯文本/);

    const s2 = setup();
    s2.state.clipboardMode = 'reject';
    s2.submit('缓考申请');
    s2.requests[0].resolve(okResponse());
    await flush();
    const copyBtn2 = s2.ids['results-area'].querySelectorAll('button')
      .find(b => b.textContent === '复制问题与摘录');
    copyBtn2.listeners.click();
    await flush();
    assert.match(s2.ids['results-area'].textContent, /复制失败，请手动选择文本复制/);
    passed++;
  }

  // Scenario 5: empty states are understandable and distinct
  for (const [stateName, msg] of [
    ['no_admissible_docs', '没有满足所选条件的资料，无法整理依据；可清除条件后重试。'],
    ['no_hits', '满足条件的资料中没有检索命中，无法整理依据。'],
    ['budget_empty', '命中内容均超出本次整理的字符预算（整条无法装入），未截取或拼接原文。'],
  ]) {
    const s = setup();
    s.submit('缓考申请');
    s.requests[0].resolve(okResponse({
      status: 'evidence_only', evidence: [], evidence_state: stateName, empty_message: msg,
    }));
    await flush();
    assert.match(s.ids['results-area'].textContent, new RegExp(msg.slice(0, 10)));
    assert.doesNotMatch(s.ids['results-area'].textContent, /【E1】/);
    passed++;
  }

  // Scenario 6: generator unconfigured — notice shown, generate disabled
  {
    const s = setup();
    await flush();
    assert.equal(s.ids['generate-btn'].disabled, true, 'generate disabled without provider');
    assert.match(s.ids['status-area'].textContent, /自动作答未配置/);
    // 整理依据 stays usable
    assert.equal(s.ids['ask-btn'].disabled, false);
    passed++;
  }

  // Scenario 7: controlled generated response renders paragraphs + citation
  // chips. This proves rendering of the contract only — NOT a real LLM demo.
  {
    const s = setup();
    await flush();
    s.state.generatorConfigured = true;
    s.ids['status-area'].innerHTML = '';
    // re-trigger status load via a successful ask path is enough for buttons;
    // render a controlled generated response
    s.submit('缓考申请');
    assert.equal(s.requests[0].body.answer_mode, 'extractive');
    s.requests[0].resolve({
      ok: true, status: 200,
      json: async () => ({
        query: '缓考申请', query_tokens: ['缓考'], mode: 'bm25', answer_mode: 'extractive',
        status: 'generated', answer_error: null,
        answer: { paragraphs: [{ text: '缓考申请须经学院批准。', evidence_ids: ['E1'], citations: [{ evidence_id: 'E1', document_id: 'doc-1', block_id: 'b1', preview_url: '/preview#doc-1/b1' }] }] },
        disclaimer: '自动生成内容仅供参考，引用仅证明定位有效，需人工核对适用条件与语义支持。',
        evidence: [evidenceItem('E1')], evidence_state: 'ok',
        empty_message: null, insufficient_reason: null,
        budget: { max_items: 5, max_total_chars: 6000, included_items: 1, included_chars: 8, skipped_items: 0, duplicate_chunks: 0 },
        filters: null,
        filter_summary: { active: false, document_total: 1, allowed_count: 1, excluded_counts: {}, counting_rules: 'x', notes: [] },
      }),
    });
    await flush();
    const txt = s.ids['results-area'].textContent;
    assert.match(txt, /自动生成（需人工核对/);
    assert.match(txt, /缓考申请须经学院批准。/);
    assert.match(txt, /E1/, 'citation chip rendered');
    assert.match(txt, /需人工核对适用条件与语义支持/);
    passed++;
  }

  // Scenario 9 (T015): citation chip locates & highlights its evidence card
  {
    const s = setup();
    s.state.generatorConfigured = true; // before initial status load picks it up
    await flush();
    s.ids['query-input'].value = '缓考申请';
    s.ids['generate-btn'].listeners.click(); // generated request
    assert.equal(s.requests[0].body.answer_mode, 'generated');
    s.requests[0].resolve({
      ok: true, status: 200,
      json: async () => ({
        query: '缓考申请', query_tokens: ['缓考'], mode: 'bm25', answer_mode: 'generated',
        status: 'generated',
        answer: { paragraphs: [{ text: '【模拟输出】缓考申请须经学院批准。', evidence_ids: ['E1'], citations: [{ evidence_id: 'E1', document_id: 'doc-1', block_id: 'b1', preview_url: '/preview#doc-1/b1' }] }] },
        disclaimer: '自动生成内容仅供参考，引用仅证明定位有效，需人工核对适用条件与语义支持。',
        evidence: [evidenceItem('E1')], evidence_state: 'ok',
        empty_message: null, insufficient_reason: null,
        budget: { max_items: 5, max_total_chars: 6000, included_items: 1, included_chars: 8, skipped_items: 0, duplicate_chunks: 0 },
        filters: null,
        filter_summary: { active: false, document_total: 1, allowed_count: 1, excluded_counts: {}, counting_rules: 'x', notes: [] },
      }),
    });
    await flush();
    const chips = s.ids['results-area'].querySelectorAll('.cite-chip');
    assert.equal(chips.length, 1, 'citation chip rendered');
    chips[0].listeners.click({ preventDefault() {} });
    const card = s.ids['results-area'].children.find(c => c.id === 'ev-E1');
    assert.ok(card, 'evidence card exists');
    assert.match(card.className, /highlight/, 'citation click highlights the evidence card');
    assert.ok(card.children.some(c => c.textContent === '查看原文'), 'card keeps 原文 link');
    passed++;
  }

  // Scenario 10 (T015): generation failure → 查看本次问题的原文依据 uses the
  // failed request's query/filters snapshot (extractive, no model call)
  {
    const s = setup();
    s.state.generatorConfigured = true; // before initial status load picks it up
    await flush();
    s.ids['filter-admission-year'].value = '2023';
    s.ids['query-input'].value = '缓考申请需要什么材料';
    s.ids['generate-btn'].listeners.click();
    assert.equal(s.requests[0].body.answer_mode, 'generated');
    assert.equal(s.requests[0].body.filters.admission_year, 2023);
    s.requests[0].resolve({ ok: false, status: 502, json: async () => ({ code: 'GENERATOR_ERROR', message: '生成器执行失败；可改用原文摘录（answer_mode=extractive）。' }) });
    await flush();
    const txt = s.ids['results-area'].textContent;
    assert.match(txt, /生成失败 \/ 未返回答案/, 'failure labeled distinctly');
    assert.match(txt, /可改用原文摘录/);
    // edit controls after failure — the fallback must use the snapshot
    s.ids['filter-admission-year'].value = '';
    s.ids['query-input'].value = 'draft';
    const btns = s.ids['results-area'].querySelectorAll('button');
    const evBtn = btns.find(b => b.textContent === '查看本次问题的原文依据');
    assert.ok(evBtn, 'extractive fallback button exists');
    evBtn.listeners.click();
    await flush();
    assert.equal(s.requests[1].body.answer_mode, 'extractive', 'fallback is extractive — no model call');
    assert.equal(s.requests[1].body.query, '缓考申请需要什么材料');
    assert.deepEqual(s.requests[1].body.filters, { campus: null, student_type: null, admission_year: 2023, as_of_date: null },
      'fallback keeps the failed request filters, not the edited controls');
    s.requests[1].resolve(okResponse({
      filters: { campus: null, student_type: null, admission_year: 2023, as_of_date: null },
    }));
    await flush();
    assert.match(s.ids['results-area'].textContent, /原文摘录 \/ 未生成答案/);
    passed++;
  }

  // Scenario 11 (T015): opt-in local history — save/view/delete/clear;
  // restoring history makes NO requests
  {
    const s = setup();
    await flush();
    s.ids['history-toggle'].checked = true;
    s.ids['history-toggle'].listeners.change();
    assert.match(s.ids['history-note'].textContent, /仅保存在此浏览器本机/);
    s.submit('问题甲');
    s.requests[0].resolve(okResponse());
    await flush();
    s.submit('问题乙');
    s.requests[1].resolve(okResponse({
      status: 'insufficient_evidence', insufficient_reason: '材料不足',
      evidence: [], evidence_state: 'no_hits', empty_message: null,
    }));
    await flush();
    assert.match(s.ids['history-list'].textContent, /问题甲/);
    assert.match(s.ids['history-list'].textContent, /问题乙/);
    // restore: view issues no request
    const reqCount = s.requests.length;
    const viewBtn = s.ids['history-list'].querySelectorAll('button').find(b => b.textContent === '查看');
    viewBtn.listeners.click();
    await flush();
    assert.equal(s.requests.length, reqCount, 'history view makes no request');
    assert.match(s.ids['results-area'].textContent, /历史结果，资料可能已更新/);
    // delete single (newest first: 问题乙 is the first item)
    const delBtn = s.ids['history-list'].querySelectorAll('button').find(b => b.textContent === '删除');
    delBtn.listeners.click();
    assert.ok(!/问题乙/.test(s.ids['history-list'].textContent), 'deleted entry gone');
    assert.match(s.ids['history-list'].textContent, /问题甲/);
    // toggle off keeps records and explains state
    s.ids['history-toggle'].checked = false;
    s.ids['history-toggle'].listeners.change();
    assert.match(s.ids['history-note'].textContent, /仍保留/);
    // clear all
    s.ids['history-clear-btn'].listeners.click();
    assert.ok(!/问题甲/.test(s.ids['history-list'].textContent), 'cleared');
    assert.match(s.ids['history-note'].textContent, /未开启保存/);
    passed++;
  }

  // Scenario 12 (T015): storage unavailable — notice shown, Q&A unaffected
  {
    const s = setup();
    await flush();
    s.state.storageFailWrites = true;
    s.ids['history-toggle'].checked = true;
    s.ids['history-toggle'].listeners.change();
    s.submit('问题丙');
    s.requests[0].resolve(okResponse());
    await flush();
    assert.match(s.ids['results-area'].textContent, /原文摘录 \/ 未生成答案/, 'Q&A still works');
    assert.match(s.ids['history-note'].textContent, /本机存储不可用/);
    passed++;
  }

  // T018: related procedures entry carries the RESULT snapshot (not controls)
  {
    const s = setup();
    await flush();
    s.ids['filter-admission-year'].value = '2023';
    s.ids['filter-campus'].value = '成都校区';
    s.submit('缓考申请须由谁批准？');
    s.requests[0].resolve(okResponse({
      filters: { campus: '成都校区', student_type: null, admission_year: 2023, as_of_date: null },
    }));
    await flush();
    const txt = s.ids['results-area'].textContent;
    assert.match(txt, /相关事项入口/);
    assert.match(txt, /不代表系统判断您符合办理条件/);
    const findLink = el => el.querySelectorAll('a').find(a => String(a.href || '').indexOf('/procedures?') === 0);
    const link = findLink(s.ids['results-area']);
    assert.ok(link, 'procedures link exists');
    assert.match(link.href, /procedure_id=proc-apply-defer/);
    assert.match(link.href, /admission_year=2023/);
    assert.ok(link.href.indexOf('campus=' + encodeURIComponent('成都校区')) >= 0);
    // editing controls afterwards must not rewrite the rendered snapshot link
    s.ids['filter-admission-year'].value = '';
    s.ids['filter-campus'].value = '都江堰校区';
    assert.equal(findLink(s.ids['results-area']).href, link.href, 'link bound to result snapshot');
    passed++;
  }

  // T022-R1: unconfigured template -> no dead entry, explicit note
  {
    const s = setup(null, { proceduresConfigured: false });
    await flush();
    s.submit('缓考申请须由谁批准？');
    s.requests[0].resolve(okResponse({}));
    await flush();
    const txt = s.ids['results-area'].textContent;
    assert.match(txt, /本次运行未配置对应指南/, 'explicit unconfigured note');
    const findLink = el => el.querySelectorAll('a').find(a => String(a.href || '').indexOf('/procedures?') === 0);
    assert.ok(!findLink(s.ids['results-area']), 'no dead procedures link when unconfigured');
    passed++;
  }

  // T018: history result entry uses the HISTORY conditions, not current controls
  {
    const s = setup();
    await flush();
    s.ids['history-toggle'].checked = true;
    s.ids['history-toggle'].listeners.change();
    s.ids['filter-admission-year'].value = '2023';
    s.submit('缓考申请流程');
    s.requests[0].resolve(okResponse({
      filters: { campus: null, student_type: null, admission_year: 2023, as_of_date: null },
    }));
    await flush();
    // user edits controls but does NOT re-ask
    s.ids['filter-admission-year'].value = '2024';
    const viewBtn = s.ids['history-list'].querySelectorAll('button').find(b => b.textContent === '查看');
    viewBtn.listeners.click();
    await flush();
    const findLink = el => el.querySelectorAll('a').find(a => String(a.href || '').indexOf('/procedures?') === 0);
    const link = findLink(s.ids['results-area']);
    assert.ok(link);
    assert.match(link.href, /admission_year=2023/, 'history conditions, not current controls');
    assert.ok(!/admission_year=2024/.test(link.href));
    assert.match(s.ids['results-area'].textContent, /本条历史条件/);
    passed++;
  }

  // T018: no keyword match → no related entry
  {
    const s = setup();
    s.submit('宿舍门禁时间是几点？');
    s.requests[0].resolve(okResponse());
    await flush();
    assert.ok(!/相关事项入口/.test(s.ids['results-area'].textContent));
    passed++;
  }

  // T018: home demo question prefill via URL query
  {
    const s = setup('?query=' + encodeURIComponent('缓考申请须由谁批准？'));
    assert.equal(s.ids['query-input'].value, '缓考申请须由谁批准？');
    passed++;
  }

  // T020 voice: record → stop → transcribe → edit → explicit use; never auto-ask
  {
    const s = setup();
    await flush();
    trigger(s.ids['record-btn'], 'click');
    await flush();
    assert.match(s.ids['voice-hint'].textContent, /录音中/);
    assert.equal(s.state.recorderStarts, 1);
    trigger(s.ids['record-stop-btn'], 'click');
    await flush();
    assert.equal(s.ids['transcribe-btn'].disabled, false, 'transcribe enabled after stop');
    trigger(s.ids['transcribe-btn'], 'click');
    await flush();
    const tReq = s.requests.find(r => String(r.url).indexOf('/asr/transcribe') >= 0);
    assert.ok(tReq, 'transcribe request sent');
    tReq.resolve(ok({ text: '缓考申请须经所在学院批准', provider: 'mock-asr（模拟，非真实识别）', model: 'mock-asr-model', duration_seconds: 1.2, elapsed_ms: 5, confidence: null }));
    await flush();
    assert.match(s.ids['transcript-area'].textContent, /识别结果/);
    assert.match(s.ids['transcript-area'].textContent, /不会自动提问/);
    const ta = s.ids['transcript-area'].querySelectorAll('textarea')[0];
    assert.equal(ta.value, '缓考申请须经所在学院批准');
    const useBtn = s.ids['transcript-area'].querySelectorAll('button').find(b => b.textContent === '使用此文本');
    assert.ok(useBtn);
    trigger(useBtn, 'click');
    assert.equal(s.ids['query-input'].value, '缓考申请须经所在学院批准');
    // transcribe/use never triggered /ask
    assert.ok(!s.requests.some(r => String(r.url).indexOf('/api/v1/ask') >= 0), 'no auto ask');
    passed++;
  }

  // T020 voice: transcribe failure keeps the original question
  {
    const s = setup();
    await flush();
    s.ids['query-input'].value = '原问题保持不变';
    trigger(s.ids['record-btn'], 'click');
    await flush();
    trigger(s.ids['record-stop-btn'], 'click');
    await flush();
    trigger(s.ids['transcribe-btn'], 'click');
    await flush();
    const tReq = s.requests.find(r => String(r.url).indexOf('/asr/transcribe') >= 0);
    tReq.resolve({ ok: false, status: 400, json: async () => ({ code: 'AUDIO_TOO_LARGE', message: '音频超过 5 MB 限制' }) });
    await flush();
    assert.match(s.ids['transcript-area'].textContent, /音频超过 5 MB 限制/);
    assert.match(s.ids['transcript-area'].textContent, /原问题未被修改/);
    assert.equal(s.ids['query-input'].value, '原问题保持不变');
    passed++;
  }

  // T020 voice: existing question text requires the explicit 替换问题输入 action
  {
    const s = setup();
    await flush();
    s.ids['query-input'].value = '已有问题文字';
    trigger(s.ids['record-btn'], 'click');
    await flush();
    trigger(s.ids['record-stop-btn'], 'click');
    await flush();
    trigger(s.ids['transcribe-btn'], 'click');
    await flush();
    const tReq = s.requests.find(r => String(r.url).indexOf('/asr/transcribe') >= 0);
    tReq.resolve(ok({ text: '识别的新文本', provider: 'mock-asr（模拟，非真实识别）', model: 'm', duration_seconds: 1.0, elapsed_ms: 3, confidence: null }));
    await flush();
    assert.equal(s.ids['query-input'].value, '已有问题文字', 'not overwritten by transcript');
    const useBtn = s.ids['transcript-area'].querySelectorAll('button').find(b => b.textContent === '替换问题输入');
    assert.ok(useBtn, 'explicit replace label when text exists');
    trigger(useBtn, 'click');
    assert.equal(s.ids['query-input'].value, '识别的新文本');
    passed++;
  }

  // T020 voice: microphone permission denied keeps upload/text paths
  {
    const s = setup();
    await flush();
    s.state.getUserMediaMode = 'reject';
    trigger(s.ids['record-btn'], 'click');
    await flush();
    assert.match(s.ids['voice-hint'].textContent, /无法获取麦克风/);
    assert.match(s.ids['voice-hint'].textContent, /原问题未被修改/);
    assert.equal(s.ids['transcribe-btn'].disabled, true);
    // upload path still available
    s.ids['audio-file'].files = [{ name: 'q.wav', size: 2048 }];
    trigger(s.ids['audio-file'], 'change');
    assert.equal(s.ids['transcribe-btn'].disabled, false);
    passed++;
  }

  // T020 voice: cancel releases the microphone track
  {
    const s = setup();
    await flush();
    trigger(s.ids['record-btn'], 'click');
    await flush();
    trigger(s.ids['record-cancel-btn'], 'click');
    await flush();
    assert.equal(s.state.trackStops, 1, 'track stopped on cancel');
    assert.equal(s.ids['transcribe-btn'].disabled, true);
    assert.match(s.ids['voice-hint'].textContent, /已取消并释放麦克风/);
    passed++;
  }

  // T020-R1: no_speech（空/空白转写）不显示成功编辑器、不改问题
  {
    const s = setup();
    await flush();
    s.ids['query-input'].value = '原问题保持不变';
    trigger(s.ids['record-btn'], 'click');
    await flush();
    trigger(s.ids['record-stop-btn'], 'click');
    await flush();
    trigger(s.ids['transcribe-btn'], 'click');
    await flush();
    const tReq = s.requests.find(r => String(r.url).indexOf('/asr/transcribe') >= 0);
    tReq.resolve(ok({ status: 'no_speech', text: '', message: '未识别到有效语音，请重录或重新选择音频', provider: 'mock', model: 'm', duration_seconds: 1.0, elapsed_ms: 3, confidence: null }));
    await flush();
    assert.match(s.ids['transcript-area'].textContent, /未识别到有效语音/);
    assert.equal(s.ids['transcript-area'].querySelectorAll('textarea').length, 0, 'no success editor');
    assert.equal(s.ids['query-input'].value, '原问题保持不变');
    passed++;
  }

  // T020-R1: clearing the editor then 使用此文本 must not wipe the question
  {
    const s = setup();
    await flush();
    s.ids['query-input'].value = '原问题保持不变';
    trigger(s.ids['record-btn'], 'click');
    await flush();
    trigger(s.ids['record-stop-btn'], 'click');
    await flush();
    trigger(s.ids['transcribe-btn'], 'click');
    await flush();
    const tReq = s.requests.find(r => String(r.url).indexOf('/asr/transcribe') >= 0);
    tReq.resolve(ok({ status: 'ok', text: '识别文本', provider: 'mock', model: 'm', duration_seconds: 1.0, elapsed_ms: 3, confidence: null }));
    await flush();
    const ta = s.ids['transcript-area'].querySelectorAll('textarea')[0];
    ta.value = '   ';
    const useBtn = s.ids['transcript-area'].querySelectorAll('button').find(b => b.textContent === '替换问题输入');
    trigger(useBtn, 'click');
    assert.equal(s.ids['query-input'].value, '原问题保持不变', 'blank transcript must not clear question');
    assert.match(s.ids['voice-hint'].textContent, /识别文本为空，未修改问题输入/);
    passed++;
  }

  // T020-R1: unconfigured ASR shown before recording; text entry kept
  {
    const s = setup();
    s.state.asrStatus = { configured: false };
    await flush();
    await flush();
    assert.match(s.ids['voice-hint'].textContent, /本地语音识别未配置/);
    assert.equal(s.ids['record-btn'].disabled, true);
    assert.equal(s.ids['query-input'].disabled, false, 'text entry stays available');
    passed++;
  }

  console.log(`check-ask-behavior: ${passed} scenarios passed`);
  process.exit(0);
})().catch(e => {
  console.error('FAIL:', e.message);
  console.error(e.stack);
  process.exit(1);
});
