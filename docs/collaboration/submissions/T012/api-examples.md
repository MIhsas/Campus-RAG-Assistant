# T012 API 示例

真实请求/响应摘自 `ask-demo.json`（本地 parse-corpus、BM25、未调用任何模型）。字段有省略处注明“…”，完整输出见该 JSON。合成语料，不代表真实学校政策。

## GET /api/v1/ask/status

```json
{
  "corpus_status": "ready",
  "answer_mode_default": "extractive",
  "answer_modes_available": ["extractive"],
  "generator_configured": false,
  "generator_identity": null,
  "available_modes": ["bm25"],
  "filter_options": {"campus": ["成都校区"], "student_type": ["全日制本科"], "admission_years": [2024]},
  "request_id": "…"
}
```

## POST /api/v1/ask（extractive + 筛选）

请求：

```json
{
  "query": "缓考申请需要什么材料",
  "top_k": 5,
  "mode": "bm25",
  "answer_mode": "extractive",
  "filters": {"campus": "成都校区", "admission_year": 2023, "as_of_date": "2026-09-22"}
}
```

响应（200，节选 E1；3 条证据均来自 syn-parse-txt-001，2023 级命中）：

```json
{
  "query": "缓考申请需要什么材料",
  "mode": "bm25",
  "answer_mode": "extractive",
  "status": "evidence_only",
  "answer": null,
  "disclaimer": "以下是相关原文摘录，尚未生成答案，需核对适用条件。",
  "evidence_state": "ok",
  "evidence": [
    {
      "evidence_id": "E1",
      "text": "第二条 学生因病或其他原因不能参加期末考试的，应在考前提交缓考申请。缓考申请须经所在学院批准…",
      "document_id": "syn-parse-txt-001",
      "block_id": "9df6bfbd98df733e",
      "chunk_id": "…",
      "char_start": 0,
      "char_end": 63,
      "document_sha256": "…",
      "title": "合成测试教务管理办法（正文解析示例）",
      "source_url": "https://example.org/policy/parse/txt",
      "version_label": "解析示例 v1",
      "scope": {"campus": ["成都校区"], "student_type": ["全日制本科"], "admission_years": [2023, 2024]},
      "published_at": "2025-01-15",
      "effective_from": "2025-03-01",
      "effective_to": null,
      "is_synthetic": true,
      "preview_url": "/preview#syn-parse-txt-001/9df6bfbd98df733e"
    }
  ],
  "budget": {"max_items": 5, "max_total_chars": 6000, "included_items": 3, "included_chars": 214, "skipped_items": 0, "duplicate_chunks": 0},
  "filters": {"campus": "成都校区", "student_type": null, "admission_year": 2023, "as_of_date": "2026-09-22"},
  "filter_summary": {"active": true, "document_total": 2, "allowed_count": 1, "…": "…"}
}
```

## 无符合条件的资料（不凭空回答）

请求 `filters: {"admission_year": 1900}` → 200：

```json
{
  "status": "evidence_only",
  "answer": null,
  "evidence": [],
  "evidence_state": "no_admissible_docs",
  "empty_message": "没有满足所选条件的资料，无法整理依据；可清除条件后重试。"
}
```

## generated 未配置生成器（503，不伪装成生成答案）

请求 `answer_mode: "generated"` → 503：

```json
{
  "code": "GENERATOR_NOT_CONFIGURED",
  "message": "自动作答未配置；可使用原文摘录（answer_mode=extractive）。运行时模型 API/预算需由用户之后提供。",
  "request_id": "…"
}
```

## generated（注入 AnswerProvider 后，测试受控输出示例）

仅示意协议形状（单元测试中的 fake 输出，**不是真实 LLM 结果**）：

```json
{
  "status": "generated",
  "answer": {
    "paragraphs": [
      {
        "text": "缓考申请须经学院批准。",
        "evidence_ids": ["E1"],
        "citations": [
          {"evidence_id": "E1", "document_id": "syn-parse-txt-001", "block_id": "9df6bfbd98df733e", "preview_url": "/preview#syn-parse-txt-001/9df6bfbd98df733e"}
        ]
      }
    ]
  },
  "disclaimer": "自动生成内容仅供参考，引用仅证明定位有效，需人工核对适用条件与语义支持。"
}
```

生成失败（空输出/非法格式/未知引用）→ 502 `GENERATOR_INVALID_OUTPUT`；生成器异常 → 502 `GENERATOR_ERROR`；两者均不返回部分坏答案，提示可改用原文摘录。provider 判断材料不足 → 200 `status=insufficient_evidence`（独立状态，检索非空时不强行作答）。
