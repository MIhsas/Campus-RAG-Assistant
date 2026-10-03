"""Unified normal run entry (T022).

One recommended entry for running the service on a designated local corpus
package. Optional features are ALL off by default and enabled only
explicitly; nothing synthetic (example corpora, mock generator, demo
templates) is ever loaded implicitly.

Options:
  --manifest / --corpus-root   designated corpus (required)
  --embedding-model-dir        local vector model dir (enables dense/hybrid)
  --asr-model-dir              local ASR model dir (enables voice input)
  --generator deepseek         explicit generator switch (key from local env
                               ONLY: CAMPUS_GENERATOR/DEEPSEEK_API_KEY;
                               never in CLI/JSON/status/logs; no probe at
                               startup)
  --planner deepseek           explicit planner switch (T024, default off,
                               independent of --generator; key from local env
                               ONLY: CAMPUS_PLANNER/DEEPSEEK_API_KEY; startup /
                               status / fixed workflow issue ZERO planning
                               requests; never probed)
  --procedures / --self-check  explicit template/rule config paths

Configuration priority: explicit CLI options; generator credentials only
from local environment variables. Requesting a feature without its required
config produces a clear degrade message — never a silent "enabled".
"Configured" and "verified (model loaded / connection)" are reported
separately; the startup performs no model-service probing.

Usage (PowerShell, paths with spaces are quoted):
    & .\\.venv\\Scripts\\python.exe scripts\\serve-corpus.py `
        --manifest '<pkg>\\manifest.json' --corpus-root '<pkg>'
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path


def _ensure_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream.encoding and stream.encoding.lower().replace("-", "") == "utf8":
                continue
            wrapped = io.TextIOWrapper(stream.buffer, encoding="utf-8", line_buffering=True)
            if stream is sys.stdout:
                sys.stdout = wrapped
            else:
                sys.stderr = wrapped
        except (AttributeError, OSError):
            pass


def build_app(
    *,
    manifest: Path,
    corpus_root: Path,
    embedding_model_dir: str | None = None,
    asr_model_dir: str | None = None,
    procedures: Path | None = None,
    self_check: Path | None = None,
    generator: str = "off",
    provider_factory=None,
    demo_home: bool = False,
    planner=None,
    planner_mode: str = "off",
    planner_factory=None,
):
    """Assemble the app from explicit options. Returns (app, config_report).

    config_report: list of (line, ok) describing what is configured vs
    degraded — 已配置 与 已验证（加载/连接）分开表述。
    """
    from campus_assistant.main import create_app

    report: list[tuple[str, bool]] = []

    # --- 向量检索（可选，本地目录；不自动下载） ---
    embedding_path = None
    if embedding_model_dir:
        if Path(embedding_model_dir).is_dir():
            embedding_path = embedding_model_dir
            report.append((f"向量检索：已配置（本地模型目录 {Path(embedding_model_dir).name}）", True))
        else:
            report.append(("向量检索：请求启用但模型目录不存在（不自动下载）——已降级，仅 BM25", False))

    # --- ASR（可选，本地目录） ---
    asr_adapter = None
    if asr_model_dir:
        if Path(asr_model_dir).is_dir():
            from campus_assistant.asr.adapter import FunASRParaformerAdapter

            asr_adapter = FunASRParaformerAdapter(asr_model_dir)
            report.append((f"语音识别：已配置（{asr_adapter.model_id}；模型将在首次转写时加载）", True))
        else:
            report.append(("语音识别：请求启用但模型目录不存在——已降级，文字提问仍可用", False))

    # --- 生成器（显式开关；密钥仅本地环境变量；启动不探测） ---
    answer_provider = None
    if generator == "deepseek":
        if provider_factory is not None:
            answer_provider = provider_factory()
        else:
            from campus_assistant.qa.deepseek import provider_from_env

            answer_provider = provider_from_env()
        if answer_provider is None:
            report.append((
                "生成器：请求启用但配置不完整（需 CAMPUS_GENERATOR=deepseek 与 DEEPSEEK_API_KEY）"
                "——已降级，原文摘录仍可用", False))
        else:
            report.append((
                f"生成器：已配置（{getattr(answer_provider, 'provider_id', '未标注身份')}；"
                "未验证服务连接，启动不探测）", True))
    else:
        report.append(("生成器：未启用（仅原文摘录；--generator deepseek 显式开启）", True))

    # --- 办事模板 / 自查规则（显式注入） ---
    procedures_path = None
    if procedures is not None:
        if Path(procedures).is_file():
            procedures_path = procedures
            report.append((f"办事模板：已配置（{Path(procedures).name}）", True))
        else:
            report.append((f"办事模板：请求启用但文件不存在——已降级（{Path(procedures).name}）", False))
    else:
        report.append(("办事模板：未配置（不代表学校事项无模板）", True))

    rule_path = None
    if self_check is not None:
        if Path(self_check).is_file():
            rule_path = self_check
            report.append((f"自查规则：已配置（{Path(self_check).name}）", True))
        else:
            report.append((f"自查规则：请求启用但文件不存在——已降级（{Path(self_check).name}）", False))
    else:
        report.append(("自查规则：未配置（不代表学校事项无规则）", True))

    # --- 规划器（T024，独立显式开关，默认关闭；与 --generator 相互独立） ---
    if planner is not None:
        report.append((
            f"规划器：已注入（{getattr(planner, 'planner_kind', 'unknown')}）；未联调验证真实服务", True))
    elif planner_mode == "deepseek":
        if planner_factory is not None:
            planner = planner_factory()
        else:
            from campus_assistant.agent.deepseek_planner import planner_from_env

            planner = planner_from_env()
        if planner is None:
            report.append((
                "规划器：请求启用但配置不完整（需 CAMPUS_PLANNER=deepseek 与 DEEPSEEK_API_KEY）"
                "——已降级，Agent 模式关闭（固定流程不受影响）", False))
        else:
            report.append((
                f"规划器：已配置（{getattr(planner, 'model', 'deepseek')}，结构化动作；"
                "未联调验证真实服务，启动不探测）", True))
    else:
        report.append(("规划器：未启用（--planner deepseek 显式开启；与 --generator 相互独立）", True))

    app = create_app(
        manifest_path=manifest,
        corpus_root=corpus_root,
        embedding_model_path=embedding_path,
        answer_provider=answer_provider,
        procedures_path=procedures_path,
        self_check_path=rule_path,
        asr_adapter=asr_adapter,
        demo_home=demo_home,
        planner=planner,
    )

    # --- 语料与“已验证”状态（基于实际加载结果，非配置声明） ---
    parsed = len(app.state.corpus_data or [])
    total = app.state.document_count
    report.insert(0, (
        f"语料：文档 {total}，解析成功 {parsed}"
        + (f"，错误 {len(app.state.corpus_errors)}（详情见 /api/v1/search/status）" if app.state.corpus_errors else ""),
        parsed > 0,
    ))
    if embedding_path is not None:
        if app.state.embedding_service is not None:
            report.append(("向量检索：模型加载完成（dense/hybrid 可用）", True))
        else:
            report.append((
                "向量检索：已配置但模型加载失败——仅 BM25（原因见 /api/v1/search/status 的 embedding_error）",
                False))
    return app, report


def main() -> int:
    _ensure_utf8_streams()
    parser = argparse.ArgumentParser(description="统一正常运行入口（指定语料包；功能全部默认关闭）")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--corpus-root", required=True)
    parser.add_argument("--port", type=int, default=8040)
    parser.add_argument("--embedding-model-dir", default=None, help="可选：本地向量模型目录（不自动下载）")
    parser.add_argument("--asr-model-dir", default=None, help="可选：本地 ASR 模型目录（不自动下载）")
    parser.add_argument("--generator", choices=["off", "deepseek"], default="off",
                        help="生成器显式开关；密钥仅取本地环境变量")
    parser.add_argument("--planner", choices=["off", "deepseek"], default="off",
                        help="规划器独立显式开关（默认关，与 --generator 相互独立；密钥仅取本地环境变量）")
    parser.add_argument("--procedures", default=None, help="可选：办事模板 JSON 路径（显式注入）")
    parser.add_argument("--self-check", default=None, help="可选：自查规则 JSON 路径（显式注入）")
    args = parser.parse_args()

    app, report = build_app(
        manifest=Path(args.manifest),
        corpus_root=Path(args.corpus_root),
        embedding_model_dir=args.embedding_model_dir,
        asr_model_dir=args.asr_model_dir,
        procedures=Path(args.procedures) if args.procedures else None,
        self_check=Path(args.self_check) if args.self_check else None,
        generator=args.generator,
        planner_mode=args.planner,
    )

    print("配置报告（来源：启动参数与本地环境；不读取/不显示密钥）：")
    for line, ok in report:
        print(("  ✓ " if ok else "  ⚠ ") + line)
    print(f"打开 http://127.0.0.1:{args.port}/ （首页显示当前服务能力）")

    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
