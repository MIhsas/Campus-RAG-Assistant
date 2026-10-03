// T023-R1 workflow.html 因果链检查（vm stub 层级，非真实浏览器）。
// 覆盖：① 年份严格校验（2023 / 留空 / abc、2023abc）；② 新请求清空旧结果，
// 422 与网络异常共用清理（“本次未生成新结果”，无残留办理入口）；③ 成功结果绑定提交时快照。
// 真实浏览器交互验证由 Astra 补验，本脚本不冒充浏览器证据。
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');

const html = fs.readFileSync(
  path.join(__dirname, '..', 'src', 'campus_assistant', 'static', 'workflow.html'), 'utf8');
const m = html.match(/<script>([\s\S]*)<\/script>/);
if (!m) { console.error('No inline script found'); process.exit(1); }
const script = m[1];

class Element {
  constructor(tag) {
    this.tagName = tag; this.children = []; this.className = '';
    this._text = ''; this._html = ''; this.style = { display: '' };
    this.value = ''; this.disabled = false; this.href = ''; this.listeners = {};
  }
  appendChild(c) { this.children.push(c); return c; }
  addEventListener(name, fn) { this.listeners[name] = fn; }
  querySelector(sel) {
    const cls = String(sel).replace(/^\./, '');
    const find = e => {
      if (String(e.className || '').split(/\s+/).includes(cls)) return e;
      for (const c of e.children || []) { const r = find(c); if (r) return r; }
      return null;
    };
    return find(this);
  }
  set textContent(v) { this._text = String(v); this.children = []; }
  get textContent() {
    return this._text + this.children.map(c => c.textContent || '').join('');
  }
  set innerHTML(v) { this._html = String(v); if (this._html === '') { this.children = []; this._text = ''; } }
  get innerHTML() { return this._html; }
}

function setup() {
  const ids = {};
  for (const id of ['proc', 'query', 'campus', 'student_type', 'admission_year', 'as_of-date',
                    'as_of_date', 'run-fixed', 'run-plan', 'planner-hint', 'fallback',
                    'steps-panel', 'run-label', 'steps', 'tool-trace', 'stop-info',
                    'evidence-panel', 'evidence', 'draft-panel', 'draft', 'draft-actions']) {
    ids[id] = new Element(id === 'proc' ? 'select' : (id.startsWith('run-') ? 'button' : 'div'));
  }
  for (const p of ['steps-panel', 'evidence-panel', 'draft-panel', 'fallback']) ids[p].style.display = 'none';
  ids['run-plan'].style.display = 'none';

  const requests = [];
  const state = {
    agentStatus: {
      agent_mode: 'off', planner: null, remote_planner: false,
      workflow: { fixed_available: true, reason: null },
      tools: [{ name: 'search_policy' }, { name: 'build_checklist_draft' }],
      budget: { max_plan_rounds: 4, max_tool_calls: 6, deadline_s: 30 },
    },
    procedures: { procedures: [{ procedure_id: 'proc-apply-defer', title: '缓考申请' }] },
  };

  const context = {
    document: {
      getElementById: id => ids[id] || null,
      createElement: t => new Element(t),
      createTextNode: t => { const e = new Element(); e.textContent = t; return e; },
    },
    fetch: (url, options) => {
      if (!options) {
        if (String(url).indexOf('/api/v1/agent/status') >= 0) {
          return Promise.resolve({ ok: true, status: 200, json: async () => state.agentStatus });
        }
        if (String(url).indexOf('/api/v1/procedures') >= 0) {
          return Promise.resolve({ ok: true, status: 200, json: async () => state.procedures });
        }
        return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
      }
      return new Promise((resolve, reject) => {
        requests.push({
          url: String(url),
          body: typeof options.body === 'string' ? JSON.parse(options.body) : options.body,
          resolve, reject,
        });
      });
    },
  };
  vm.runInNewContext(script, context);
  return { ids, requests, state };
}

const flush = () => new Promise(resolve => setImmediate(resolve));
const okDraft = {
  workflow_kind: 'fixed', workflow_label: '固定流程（选事项→查找依据→整理草稿），非大模型 Agent',
  status: 'completed', stop_reason: null, message: null, input_needed: [],
  snapshot: { procedure_id: 'proc-apply-defer', query: '缓考', filters: { campus: null, student_type: null, admission_year: 2023, as_of_date: null } },
  steps: [{ step_id: 'select_procedure', title: '选事项', status: 'ok', detail: '已选定' }],
  events: [{ round: 1, kind: 'tool_call', tool: 'search_policy', status: 'ok', summary: '命中 1 条' }],
  tool_calls_used: 2, plan_rounds_used: 1,
  results: {
    search: { query: '缓考', hit_count: 1, hits: [{ chunk: { text: '原文', document_id: 'd1', block_id: 'b1' }, preview_url: '/preview#d1/b1' }] },
    draft: { procedure_id: 'proc-apply-defer', title: '缓考申请', saveable: true, status: 'ready', steps: [] },
  },
  budget: { max_plan_rounds: 1, max_tool_calls: 2 }, cancellable_note: '同步工具不可中途取消。',
};

let passed = 0;

(async () => {
  // ① 年份严格校验：合法 2023 / 空白=不限 / abc、2023abc 拒绝且不提交
  {
    const s = setup();
    await flush();
    s.ids.query.value = '缓考';
    s.ids.proc.value = 'proc-apply-defer';

    s.ids.admission_year.value = '2023';
    s.ids['run-fixed'].listeners.click();
    await flush();
    assert.equal(s.requests.length, 1, '2023 submits');
    assert.equal(s.requests[0].body.filters.admission_year, 2023, 'valid year kept as int');
    s.requests[0].resolve({ ok: true, status: 200, json: async () => okDraft });
    await flush();

    s.ids.admission_year.value = '';
    s.ids['run-fixed'].listeners.click();
    await flush();
    assert.equal(s.requests.length, 2, 'blank submits');
    assert.equal(s.requests[1].body.filters.admission_year, null, 'blank = 不限');
    s.requests[1].resolve({ ok: true, status: 200, json: async () => okDraft });
    await flush();

    s.ids.admission_year.value = 'abc';
    s.ids['run-fixed'].listeners.click();
    await flush();
    assert.equal(s.requests.length, 2, 'abc must NOT submit');
    assert.match(s.ids['stop-info'].textContent, /入学年份格式无效/, 'abc shows strict error');
    assert.match(s.ids['stop-info'].textContent, /未提交本次请求/);

    s.ids.admission_year.value = '2023abc';
    s.ids['run-fixed'].listeners.click();
    await flush();
    assert.equal(s.requests.length, 2, '2023abc must NOT submit (no truncation)');
    assert.match(s.ids['stop-info'].textContent, /入学年份格式无效/);
    passed++;
  }

  // ② 成功 → 422 失败：旧结果/办理入口清空，明确本次未生成新结果
  {
    const s = setup();
    await flush();
    s.ids.query.value = '缓考';
    s.ids.admission_year.value = '2023';
    s.ids['run-fixed'].listeners.click();
    await flush();
    s.requests[0].resolve({ ok: true, status: 200, json: async () => okDraft });
    await flush();
    assert.equal(s.ids['evidence-panel'].style.display, '', 'evidence shown after success');
    assert.equal(s.ids['draft-panel'].style.display, '', 'draft shown after success');
    const linkBefore = s.ids['draft-actions'].children.find(c => String(c.href || '').indexOf('/procedures?') === 0);
    assert.ok(linkBefore, 'procedures link exists after success');
    assert.match(s.ids['run-label'].textContent, /本次提交快照/, 'snapshot shown');
    assert.match(s.ids['run-label'].textContent, /年级=2023/, 'snapshot bound to submitted filters');

    // 修改输入框后，展示仍绑定旧快照
    s.ids.admission_year.value = '';
    assert.match(s.ids['run-label'].textContent, /年级=2023/, 'display stays bound to submitted snapshot');

    // 失败请求（422）
    s.ids['as_of_date'].value = 'bad-date';
    s.ids['run-fixed'].listeners.click();
    await flush();
    assert.equal(s.requests.length, 2);
    s.requests[1].resolve({ ok: false, status: 422, json: async () => ({ message: '参数校验失败：as_of_date' }) });
    await flush();
    assert.equal(s.ids['evidence-panel'].style.display, 'none', 'stale evidence hidden');
    assert.equal(s.ids['draft-panel'].style.display, 'none', 'stale draft hidden');
    const linkAfter = s.ids['draft-actions'].children.find(c => String(c.href || '').indexOf('/procedures?') === 0);
    assert.ok(!linkAfter, 'stale procedures link removed');
    assert.match(s.ids['stop-info'].textContent, /本次未生成新结果/);
    assert.match(s.ids['stop-info'].textContent, /参数校验失败/);
    passed++;
  }

  // ③ 网络异常与 422 共用清理逻辑
  {
    const s = setup();
    await flush();
    s.ids.query.value = '缓考';
    s.ids['run-fixed'].listeners.click();
    await flush();
    s.requests[0].resolve({ ok: true, status: 200, json: async () => okDraft });
    await flush();
    assert.equal(s.ids['draft-panel'].style.display, '', 'first run success');

    s.ids['run-fixed'].listeners.click();
    await flush();
    s.requests[1].reject(new Error('network down'));
    await flush();
    assert.equal(s.ids['evidence-panel'].style.display, 'none', 'network error: stale evidence hidden');
    assert.equal(s.ids['draft-panel'].style.display, 'none', 'network error: stale draft hidden');
    assert.match(s.ids['stop-info'].textContent, /网络错误/);
    assert.match(s.ids['stop-info'].textContent, /本次未生成新结果/);
    const linkAfter = s.ids['draft-actions'].children.find(c => String(c.href || '').indexOf('/procedures?') === 0);
    assert.ok(!linkAfter, 'network error: stale link removed');
    passed++;
  }

  // ④ T024：DeepSeek 模式按钮/提示 + partial 渲染 + 加载零规划请求
  {
    const s = setup();
    s.state.agentStatus = {
      agent_mode: 'deepseek',
      planner: { kind: 'deepseek', label: 'DeepSeek 规划（mock，未联调验证）', uses_http: true, model: 'mock-model' },
      remote_planner: true, planner_live_verified: false,
      workflow: { fixed_available: true, reason: null },
      tools: [{ name: 'search_policy' }, { name: 'build_checklist_draft' }],
      budget: { max_plan_rounds: 4, max_tool_calls: 6, deadline_s: 30 },
    };
    await flush();
    assert.match(s.ids['run-plan'].textContent, /DeepSeek 规划/, 'deepseek button labelled');
    assert.match(s.ids['planner-hint'].textContent, /planner_live_verified=false/, 'hint says unverified');
    assert.match(s.ids['planner-hint'].textContent, /显式点击/, 'hint says explicit click only');
    assert.equal(s.requests.length, 0, 'load/status issues zero planning requests');

    s.ids.query.value = '缓考';
    s.ids['run-plan'].listeners.click();
    await flush();
    assert.equal(s.requests.length, 1, 'explicit click issues exactly one run request');
    assert.equal(s.requests[0].url, '/api/v1/agent/plan/run', 'plan button targets plan/run');
    s.requests[0].resolve({ ok: true, status: 200, json: async () => ({
      workflow_kind: 'deepseek_planner', workflow_label: 'DeepSeek 规划（mock，未联调验证）',
      status: 'partial', stop_reason: 'planner_error',
      message: '规划服务请求失败（HTTP 500）。已保留已完成部分的结果。',
      input_needed: [], plan_rounds_used: 2, tool_calls_used: 1, planner_http_attempts: 2,
      budget: { max_plan_rounds: 4 }, snapshot: { procedure_id: 'proc-apply-defer', query: '缓考', filters: null },
      events: [
        { round: 1, kind: 'plan_decision', tool: 'search_policy', status: 'ok', summary: '动作 call', action: { type: 'call' } },
        { round: 1, kind: 'tool_call', tool: 'search_policy', status: 'ok', summary: '命中 1 条' },
      ],
      results: { search: { query: '缓考', hit_count: 1, hits: [] }, draft: null },
    }) });
    await flush();
    assert.match(s.ids['stop-info'].textContent, /规划服务请求失败（HTTP 500）/, 'partial failure honestly shown');
    assert.match(s.ids['stop-info'].textContent, /已保留已完成部分/, 'partial keeps completed results note');
    assert.match(s.ids['tool-trace'].textContent, /规划 HTTP 尝试：2/, 'attempts shown');
    assert.match(s.ids['tool-trace'].textContent, /规划动作 call/, 'plan action events shown');
    assert.equal(s.ids['draft-panel'].style.display, 'none', 'no draft result to show');
    // T024-R1：结果区按本次响应标注 DeepSeek，不误标模拟
    assert.match(s.ids['run-label'].textContent, /DeepSeek 规划/, 'deepseek result labelled deepseek');
    assert.match(s.ids['run-label'].textContent, /已配置 ≠ 已联调验证/, 'deepseek result keeps unverified note');
    assert.ok(!/模拟规划/.test(s.ids['run-label'].textContent), 'deepseek result NOT labelled simulated');
    passed++;
  }

  // ⑤ T024-R1：模拟响应对照——结果区标模拟；固定响应标固定流程（按响应而非按钮）
  {
    const s = setup();
    await flush();
    s.ids.query.value = '缓考';
    s.ids['run-plan'].listeners.click();
    await flush();
    s.requests[0].resolve({ ok: true, status: 200, json: async () => ({
      workflow_kind: 'simulated_planner', workflow_label: '模拟规划，非DeepSeek实时规划',
      status: 'completed', stop_reason: 'finished', message: '查找依据与办理草稿均已生成。',
      input_needed: [], plan_rounds_used: 3, tool_calls_used: 2, planner_http_attempts: 0,
      budget: { max_plan_rounds: 4 }, snapshot: { procedure_id: 'proc-apply-defer', query: '缓考', filters: null },
      events: [], results: { search: { query: '缓考', hit_count: 0, hits: [] }, draft: { procedure_id: 'proc-apply-defer', saveable: true, steps: [] } },
    }) });
    await flush();
    assert.match(s.ids['run-label'].textContent, /模拟规划/, 'simulated result labelled simulated');
    assert.ok(!/DeepSeek 规划/.test(s.ids['run-label'].textContent), 'simulated result NOT labelled deepseek');

    s.ids['run-fixed'].listeners.click();
    await flush();
    s.requests[1].resolve({ ok: true, status: 200, json: async () => ({
      workflow_kind: 'fixed', workflow_label: '固定流程（选事项→查找依据→整理草稿），非大模型 Agent',
      status: 'completed', stop_reason: 'finished', message: '查找依据与办理草稿均已生成。',
      input_needed: [], plan_rounds_used: 1, tool_calls_used: 2, planner_http_attempts: 0,
      budget: { max_plan_rounds: 1 }, snapshot: { procedure_id: 'proc-apply-defer', query: '缓考', filters: null },
      events: [], results: { search: { query: '缓考', hit_count: 0, hits: [] }, draft: { procedure_id: 'proc-apply-defer', saveable: true, steps: [] } },
    }) });
    await flush();
    assert.match(s.ids['run-label'].textContent, /固定流程/, 'fixed result labelled fixed');
    assert.match(s.ids['run-label'].textContent, /非大模型 Agent/, 'fixed result keeps non-LLM note');
    assert.ok(!/模拟规划|DeepSeek 规划/.test(s.ids['run-label'].textContent), 'fixed result not labelled as a planner');
    passed++;
  }

  console.log(`check-workflow-behavior: ${passed} scenarios passed（vm stub 层级，非真实浏览器）`);
})().catch(e => { console.error('FAIL:', e.message); process.exit(1); });
