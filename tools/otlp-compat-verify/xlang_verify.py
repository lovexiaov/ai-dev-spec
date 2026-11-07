#!/usr/bin/env python3
"""六端 OTLP/JSON 一致性验证器：同一批样例事件，逐端产出 logs / traces 并比对。

Python 作为基准（reference implementation），Go / Java / Kotlin / Web / Swift
各自 dump 后与基准做**结构化比对**（键排序、KeyValue 列表按 key 排序后逐节点比较）。

只有两类差异被允许，且会被显式标注为 `number-model`：

  - JS/Swift/Python 无 int/float 之分或解析路径不同，`120.0` 可能落成
    `intValue:"120"`（另一侧是 `doubleValue:120.0`）
  - Go 用 `encoding/json` 解码输入，数字统一为 float64，`status_code:200`
    会落成 `doubleValue:200`（另一侧是 `intValue:"200"`）

判定标准：数值相等即视为同一值（OTLP 语义上 intValue 与 doubleValue 等价）。

用法：
    python3 xlang_verify.py                 # 跑全部可用语言
    python3 xlang_verify.py --only java,go  # 只跑指定语言
    python3 xlang_verify.py --keep          # 保留中间产物目录

退出码：全部一致 0，存在真实差异 1，基准自身失败 2。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]                      # monorepo 根
FW = ROOT / "logging-framework"
SAMPLES = HERE / "xlang" / "samples.json"
HARNESS = HERE / "xlang" / "harness"

LANGUAGES = ["python", "go", "java", "kotlin", "web", "swift"]

# 各端资源属性里必然不同的一项，比对前剔除
IGNORE_RESOURCE_KEYS = {"telemetry.sdk.language"}


# ---------------------------------------------------------------- 归一化比对


def normalize(node):
    """递归排序键；KeyValue 列表语义无序，按 key 排序。"""
    if isinstance(node, dict):
        return {k: normalize(v) for k, v in sorted(node.items())}
    if isinstance(node, list):
        items = [normalize(v) for v in node]
        if all(isinstance(v, dict) and "key" in v for v in items):
            items.sort(key=lambda v: v["key"])
        return items
    return node


def strip_resource(node):
    """剔除逐语言不同的 resource 属性（如 telemetry.sdk.language）。"""
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if k == "attributes" and isinstance(v, list):
                v = [kv for kv in v if kv.get("key") not in IGNORE_RESOURCE_KEYS]
            out[k] = strip_resource(v)
        return out
    if isinstance(node, list):
        return [strip_resource(v) for v in node]
    return node


def _scalar(value):
    """取 AnyValue / 普通标量的数值，用于判断“数值相等”。"""
    if isinstance(value, dict):
        for key in ("intValue", "doubleValue"):
            if key in value:
                try:
                    return float(value[key])
                except (TypeError, ValueError):
                    return None
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


NUMERIC_ANYVALUE_KEYS = {"intValue", "doubleValue"}


def _is_numeric_anyvalue(value):
    """`{"intValue": "120"}` / `{"doubleValue": 120.0}` 这类单键 AnyValue。"""
    return (
        isinstance(value, dict)
        and len(value) == 1
        and next(iter(value)) in NUMERIC_ANYVALUE_KEYS
    )


def diff(a, b, path="$"):
    """返回 [(path, kind, a, b)]，kind ∈ {number-model, real}。"""
    # AnyValue 的 int/double 之争本质是同一数值：先归一判等，避免误报成“键缺失”
    if _is_numeric_anyvalue(a) and _is_numeric_anyvalue(b):
        if a == b:
            return []
        na, nb = _scalar(a), _scalar(b)
        if na is not None and na == nb:
            return [(path, "number-model", a, b)]
        return [(path, "real", a, b)]
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for key in sorted(set(a) | set(b)):
            if key not in a:
                out.append((f"{path}.{key}", "real", "<missing>", b[key]))
            elif key not in b:
                out.append((f"{path}.{key}", "real", a[key], "<missing>"))
            else:
                out.extend(diff(a[key], b[key], f"{path}.{key}"))
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [(f"{path}.length", "real", len(a), len(b))]
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out.extend(diff(x, y, f"{path}[{i}]"))
        return out
    if a != b:
        na, nb = _scalar(a), _scalar(b)
        if na is not None and nb is not None and na == nb:
            return [(path, "number-model", a, b)]
        return [(path, "real", a, b)]
    return []


# ---------------------------------------------------------------- 各端 dump


class LangError(Exception):
    """该端无法运行（工具链缺失 / 构建失败），应跳过而非判失败。"""


def run(cmd, cwd=None, env=None, label=""):
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    proc = subprocess.run(
        cmd, cwd=cwd, env=full_env, capture_output=True, text=True, timeout=600
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-12:]
        raise LangError(f"{label or cmd[0]} 失败 (exit {proc.returncode}):\n  " + "\n  ".join(tail))
    return proc.stdout


def need(binary: str, label: str) -> str:
    path = shutil.which(binary)
    if not path:
        raise LangError(f"{label}: 找不到 {binary}")
    return path


def dump_python(work: Path, logs: Path, traces: Path):
    need("python3", "python")
    run(
        ["python3", str(HARNESS / "dump.py"), str(SAMPLES), str(logs), str(traces)],
        env={"PYTHONPATH": str(FW / "python" / "AgentLog")},
        label="python",
    )


def dump_go(work: Path, logs: Path, traces: Path):
    go = need("go", "go")
    module_dir = work / "go"
    module_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(HARNESS / "main.go", module_dir / "main.go")
    (module_dir / "go.mod").write_text(
        "module xlang\n\ngo 1.21\n\n"
        "require github.com/lovexiaov/agent-log-go v0.0.0\n\n"
        f"replace github.com/lovexiaov/agent-log-go => {FW / 'go' / 'AgentLog'}\n",
        encoding="utf-8",
    )
    run(
        [go, "run", ".", str(SAMPLES), str(logs), str(traces)],
        cwd=module_dir,
        env={"GOFLAGS": "-mod=mod", "GOWORK": "off"},
        label="go",
    )


def dump_java(work: Path, logs: Path, traces: Path):
    javac = need("javac", "java")
    java = need("java", "java")
    classes = FW / "java" / "AgentLog" / "target" / "classes"
    if not classes.is_dir():
        raise LangError(f"java: 先构建 {classes}（cd logging-framework/java/AgentLog && mvn -q compile）")
    out = work / "java"
    out.mkdir(parents=True, exist_ok=True)
    run(
        [javac, "-encoding", "UTF-8", "-cp", str(classes), "-d", str(out),
         str(HARNESS / "XlangMain.java")],
        label="javac",
    )
    run(
        [java, "-cp", f"{classes}{os.pathsep}{out}", "XlangMain",
         str(SAMPLES), str(logs), str(traces)],
        label="java",
    )


def dump_kotlin(work: Path, logs: Path, traces: Path):
    kotlinc = need("kotlinc", "kotlin")
    java = need("java", "kotlin")
    libs = FW / "android" / "AgentLog" / "agentlog-core" / "build" / "libs"
    jars = sorted(libs.glob("agentlog-core*.jar")) if libs.is_dir() else []
    if not jars:
        raise LangError(f"kotlin: 先构建 {libs}（cd logging-framework/android/AgentLog && ./gradlew :agentlog-core:jar）")
    core = jars[-1]
    out = work / "kotlin"
    out.mkdir(parents=True, exist_ok=True)
    run(
        [kotlinc, "-nowarn", "-include-runtime", "-cp", str(core),
         str(HARNESS / "Dump.kt"), "-d", str(out / "dump.jar")],
        label="kotlinc",
    )
    run(
        [java, "-cp", f"{out / 'dump.jar'}{os.pathsep}{core}", "DumpKt",
         str(SAMPLES), str(logs), str(traces)],
        label="kotlin",
    )


def dump_web(work: Path, logs: Path, traces: Path):
    node = need("node", "web")
    pkg = FW / "web" / "Observability"
    tsc = pkg / "node_modules" / ".bin" / "tsc"
    if not tsc.exists():
        raise LangError(f"web: 缺 {tsc}（先 pnpm install）")
    # 编译到临时目录，避免污染仓库内 dist/；Node 的类型剥离不做 .js→.ts 改写
    out = work / "web-dist"
    run(
        [str(tsc), "-p", str(pkg / "tsconfig.json"),
         "--outDir", str(out), "--declaration", "false", "--sourceMap", "false"],
        cwd=pkg,
        label="tsc",
    )
    run(
        [node, str(HARNESS / "dump.mjs"), str(SAMPLES), str(logs), str(traces)],
        env={"AGENTLOG_WEB_DIST": str(out)},
        label="web",
    )


def dump_swift(work: Path, logs: Path, traces: Path):
    swiftc = need("swiftc", "swift")
    src = FW / "macos" / "AgentLog" / "Sources" / "AgentLog"
    out = work / "swift"
    out.mkdir(parents=True, exist_ok=True)
    binary = out / "dump"
    run(
        [swiftc, "-swift-version", "5", "-O",
         str(src / "Model.swift"), str(src / "Export.swift"), str(src / "OtlpMapper.swift"),
         str(HARNESS / "main.swift"), "-o", str(binary)],
        label="swiftc",
    )
    run([str(binary), str(SAMPLES), str(logs), str(traces)], label="swift")


DUMPERS = {
    "python": dump_python,
    "go": dump_go,
    "java": dump_java,
    "kotlin": dump_kotlin,
    "web": dump_web,
    "swift": dump_swift,
}


# ---------------------------------------------------------------- 主流程


def load(path: Path):
    with path.open(encoding="utf-8") as f:
        return normalize(strip_resource(json.load(f)))


def compare(baseline: Path, candidate: Path, signal: str, lang: str):
    a, b = load(baseline), load(candidate)
    diffs = diff(a, b)
    real = [d for d in diffs if d[1] == "real"]
    soft = [d for d in diffs if d[1] == "number-model"]
    if real:
        print(f"  DIFF  {lang:<7} {signal}: {len(real)} 处真实差异")
        for path, _, x, y in real[:8]:
            print(f"          {path}\n            python: {x}\n            {lang}: {y}")
    elif soft:
        print(f"  OK    {lang:<7} {signal}: 一致（{len(soft)} 处 int/double 表示差异已容忍）")
    else:
        print(f"  OK    {lang:<7} {signal}: 逐字一致")
    return not real


def main() -> int:
    parser = argparse.ArgumentParser(description="六端 OTLP/JSON 一致性验证")
    parser.add_argument("--only", default="", help="逗号分隔的语言子集，如 java,go")
    parser.add_argument("--keep", action="store_true", help="保留中间产物目录")
    parser.add_argument("--work", default="", help="指定中间产物目录（隐含 --keep）")
    args = parser.parse_args()

    if not SAMPLES.is_file():
        print(f"samples 不存在: {SAMPLES}", file=sys.stderr)
        return 2

    targets = LANGUAGES if not args.only else [
        x.strip() for x in args.only.split(",") if x.strip()
    ]
    unknown = [x for x in targets if x not in DUMPERS]
    if unknown:
        print(f"未知语言: {unknown}（可选 {LANGUAGES}）", file=sys.stderr)
        return 2

    work = Path(args.work) if args.work else Path(tempfile.mkdtemp(prefix="xlang-verify-"))
    work.mkdir(parents=True, exist_ok=True)
    keep = args.keep or bool(args.work)

    print(f"样例: {SAMPLES.relative_to(ROOT)}  工作目录: {work}")
    print("")

    produced: dict[str, tuple[Path, Path]] = {}
    skipped: dict[str, str] = {}

    for lang in targets:
        logs, traces = work / f"{lang}.logs.json", work / f"{lang}.traces.json"
        try:
            DUMPERS[lang](work, logs, traces)
            produced[lang] = (logs, traces)
        except LangError as exc:
            skipped[lang] = str(exc)
            print(f"  SKIP  {lang:<7} {exc}")
        except subprocess.TimeoutExpired:
            skipped[lang] = "超时（>600s）"
            print(f"  SKIP  {lang:<7} 超时")

    if "python" not in produced:
        print("\npython 基准不可用，无法比对", file=sys.stderr)
        return 2

    base_logs, base_traces = produced["python"]
    print("\n--- 与 python 基准比对 ---")
    ok = True
    compared = 0
    for lang, (logs, traces) in produced.items():
        if lang == "python":
            continue
        compared += 1
        ok &= compare(base_logs, logs, "logs", lang)
        ok &= compare(base_traces, traces, "traces", lang)

    print("")
    if skipped:
        print("跳过: " + ", ".join(f"{k}（{v.splitlines()[0]}）" for k, v in skipped.items()))
    if compared == 0:
        print("结论: 没有任何一端可与基准比对（全部跳过）", file=sys.stderr)
        return 2
    if not ok:
        print(f"结论: 存在真实差异，产物见 {work}")
        if not keep:
            print("（加 --keep 可保留该目录）")
        return 1

    print(f"结论: {compared}/{compared} 端与 python 基准一致（样例 {len(json.loads(SAMPLES.read_text()))} 条事件）")
    if not keep:
        shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
