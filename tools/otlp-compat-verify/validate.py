#!/usr/bin/env python3
"""
agent-log Schema v1 -> OTLP 适配性验证器（零依赖 POC）。

目的：证明 agent-log 的真实事件既能通过自身 Schema v1 校验，
又能被映射成合法的 OTLP LogRecord / Span（OTLP/JSON 结构）。

运行：python3 validate.py
退出码：全部通过 0，任一失败 1。
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.normpath(
    os.path.join(HERE, "..", "..", "docs", "logging-framework", "schema", "log-event.schema.json")
)

# ---- 1. 加载真实 schema ----
with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
    SCHEMA = json.load(f)

REQUIRED = set(SCHEMA["properties"].keys())  # 顶层允许键集合（additionalProperties:false）
SCHEMA_REQUIRED = set(SCHEMA["required"])
LEVEL_ENUM = SCHEMA["properties"]["level"]["enum"]
EVENT_TYPE_RE = re.compile(SCHEMA["properties"]["event_type"]["pattern"])

# ---- 2. 轻量 schema 校验（不依赖 jsonschema，覆盖关键约束）----
def validate_event(ev, name):
    errs = []
    if not isinstance(ev, dict):
        return ["event 不是对象"]
    # 必填
    for r in SCHEMA_REQUIRED:
        if r not in ev:
            errs.append(f"缺少必填字段 {r}")
    # 顶层封闭
    for k in ev:
        if k not in REQUIRED:
            errs.append(f"顶层非法字段 {k}（应进 payload）")
    # level 枚举
    if "level" in ev and ev["level"] not in LEVEL_ENUM:
        errs.append(f"level={ev['level']} 不在枚举 {LEVEL_ENUM}")
    # event_type 正则
    if "event_type" in ev and not EVENT_TYPE_RE.match(ev["event_type"]):
        errs.append(f"event_type={ev['event_type']} 不匹配 {EVENT_TYPE_RE.pattern}")
    # payload 必须对象
    if "payload" in ev and not isinstance(ev["payload"], dict):
        errs.append("payload 必须是对象")
    # ts 可被解析为 RFC3339
    if "ts" in ev:
        try:
            _parse_ts(ev["ts"])
        except Exception as e:
            errs.append(f"ts 解析失败: {e}")
    return errs


def _parse_ts(ts):
    s = ts.replace("Z", "+00:00")
    return datetime.fromisoformat(s)


def to_nanos(ts):
    dt = _parse_ts(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return str(int(dt.timestamp() * 1_000_000_000))


# ---- 3. event_type -> OTLP 级别映射 ----
SEVERITY = {
    "trace": (1, "TRACE"),
    "debug": (5, "DEBUG"),
    "info": (9, "INFO"),
    "warn": (13, "WARN"),
    "error": (17, "ERROR"),
    "critical": (21, "FATAL"),
}

OPERATION_EVENTS = {"network_request", "db_query"}  # 这些额外发 Span


def _av(v):
    """OTLP AnyValue：按 Python 类型选择子字段。"""
    if isinstance(v, bool):
        return {"boolValue": v}
    if isinstance(v, int):
        return {"intValue": str(v)}
    if isinstance(v, float):
        return {"doubleValue": v}
    return {"stringValue": str(v)}


def _attr(key, val):
    return {"key": key, "value": _av(val)}


def to_log_record(ev):
    sev_num, sev_text = SEVERITY[ev["level"]]
    attrs = [
        _attr("agent.event.type", ev["event_type"]),
        _attr("agent.auto", ev["agent_auto"]),
    ]
    if "subsystem" in ev:
        attrs.append(_attr("agent.subsystem", ev["subsystem"]))
    if "category" in ev:
        attrs.append(_attr("agent.category", ev["category"]))
    if "user_id" in ev:
        attrs.append(_attr("enduser.id", ev["user_id"]))  # OTel 语义约定
    for k, v in ev.get("payload", {}).items():
        attrs.append(_attr(f"payload.{k}", v))  # payload 展平 + 前缀

    trace_id = ev.get("trace_id", "")
    rec = {
        "timeUnixNano": to_nanos(ev["ts"]),
        "observedTimeUnixNano": to_nanos(ev["ts"]),
        "severityNumber": sev_num,
        "severityText": sev_text,
        "body": {"stringValue": ev["message"]},
        "attributes": attrs,
    }
    if trace_id:
        rec["traceId"] = trace_id  # OTLP/JSON 用 hex 字符串
    return rec


def to_span(ev):
    """操作类事件额外发一条 CLIENT span（HTTP / DB 语义约定）。"""
    p = ev.get("payload", {})
    if ev["event_type"] == "network_request":
        attrs = [
            _attr("http.request.method", p.get("method", "GET")),
            _attr("url.full", p.get("url", "")),
        ]
        if "status_code" in p:
            attrs.append(_attr("http.response.status_code", p["status_code"]))
        if "server_address" in p:
            attrs.append(_attr("server.address", p["server_address"]))
        name = f"HTTP {p.get('method','')}".strip()
    elif ev["event_type"] == "db_query":
        attrs = [
            _attr("db.system", p.get("db_system", "")),
            _attr("db.operation", p.get("operation", "")),
        ]
        if "statement" in p:
            attrs.append(_attr("db.statement", p["statement"]))
        name = f"DB {p.get('operation','')}".strip()
    else:
        return None

    start = to_nanos(ev["ts"])
    dur_ms = float(p.get("duration_ms", 0))
    # 用 ts 作起点，加 duration 推算 end
    dt = _parse_ts(ev["ts"])
    end_dt = dt.timestamp() * 1_000_000_000 + int(dur_ms * 1_000_000)
    if "status_code" in p:
        failed = p["status_code"] >= 400
    elif ev["event_type"] == "network_request":
        failed = False
    else:
        failed = bool(p.get("error"))
    span = {
        "traceId": ev.get("trace_id", ""),
        "spanId": os.urandom(8).hex(),  # schema 无 span_id，自造
        "name": name or ev["event_type"],
        "kind": "SPAN_KIND_CLIENT",
        "startTimeUnixNano": start,
        "endTimeUnixNano": str(int(end_dt)),
        "attributes": attrs,
        "status": {"code": "STATUS_CODE_ERROR" if failed else "STATUS_CODE_OK"},
    }
    return span


def to_resource(ev):
    res_attrs = [_attr("service.name", ev["service"])]
    if "env" in ev:
        res_attrs.append(_attr("deployment.environment", ev["env"]))
    if "release" in ev:
        res_attrs.append(_attr("service.version", ev["release"]))  # Schema v1.3
    res_attrs.append(_attr("session.id", ev["session_id"]))
    return {"attributes": res_attrs}


def build_envelope(ev):
    rec = to_log_record(ev)
    scope_logs = [{"scope": {"name": "agent-log"}, "logRecords": [rec]}]
    envelope = {"resourceLogs": [{"resource": to_resource(ev), "scopeLogs": scope_logs}]}
    span = to_span(ev)
    if span is not None:
        # 把 span 也放进同一 envelope 的 scopeSpans，便于核对
        envelope["resourceLogs"][0]["scopeLogs"][0].setdefault("scopeSpans", []).append(
            {"scope": {"name": "agent-log"}, "spans": [span]}
        )
    return envelope, rec, span


# ---- 4. 运行时断言（适配性检查）----
def checks_for(ev, name):
    problems = []
    # 4.1 通过自身 schema
    serr = validate_event(ev, name)
    if serr:
        problems.append("schema 校验失败: " + "; ".join(serr))

    env, rec, span = build_envelope(ev)

    # 4.2 级别映射正确
    exp_num, exp_text = SEVERITY[ev["level"]]
    if rec["severityNumber"] != exp_num or rec["severityText"] != exp_text:
        problems.append(f"级别映射错: {rec['severityNumber']}/{rec['severityText']} != {exp_num}/{exp_text}")

    # 4.3 trace_id 16 字节（32 hex）
    if "trace_id" in ev:
        if len(ev["trace_id"]) != 32 or not re.fullmatch(r"[0-9a-f]{32}", ev["trace_id"]):
            problems.append("trace_id 不是 16 字节 hex")
        if rec.get("traceId") != ev["trace_id"]:
            problems.append("OTLP traceId 未正确透传")

    # 4.4 resource 含 service.name + session.id
    res_keys = {a["key"] for a in env["resourceLogs"][0]["resource"]["attributes"]}
    if "service.name" not in res_keys or "session.id" not in res_keys:
        problems.append("resource 缺 service.name / session.id")

    # 4.5 payload 展平 + 前缀
    rec_keys = {a["key"] for a in rec["attributes"]}
    for k in ev.get("payload", {}):
        if f"payload.{k}" not in rec_keys:
            problems.append(f"payload.{k} 未展平到属性")

    # 4.6 操作类事件发 CLIENT span
    if ev["event_type"] in OPERATION_EVENTS:
        if span is None:
            problems.append(f"{ev['event_type']} 未生成 span")
        elif span["kind"] != "SPAN_KIND_CLIENT":
            problems.append("span kind 错误")
        elif int(span["endTimeUnixNano"]) < int(span["startTimeUnixNano"]):
            problems.append("span 结束时间早于开始")

    # 4.7 enduser.id 透传
    if "user_id" in ev and "enduser.id" not in rec_keys:
        problems.append("user_id 未映射到 enduser.id")

    # 4.8 release → resource service.version（Schema v1.3）
    if "release" in ev and "service.version" not in res_keys:
        problems.append("release 未映射到 service.version")

    return problems, env


# ---- 5. 样例事件（全部符合真实 Schema v1）----
SAMPLES = [
    {
        "ts": "2026-11-02T13:37:21.123Z",
        "level": "info",
        "service": "web-api",
        "event_type": "log",
        "session_id": "sess-0001",
        "agent_auto": False,
        "message": "user logged in",
        "env": "prod",
        "user_id": "u_123",
        "category": "auth",
        "payload": {"order_id": "o_99", "amount": 12.5},
    },
    {
        "ts": "2026-11-02T13:37:22.000Z",
        "level": "debug",
        "service": "web-api",
        "event_type": "network_request",
        "session_id": "sess-0001",
        "agent_auto": True,
        "message": "GET https://api.x.com/v1/user -> 200",
        "env": "prod",
        "release": "1.4.2",
        "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
        "payload": {
            "method": "GET",
            "url": "https://api.x.com/v1/user",
            "status_code": 200,
            "server_address": "api.x.com",
            "duration_ms": 42.5,
        },
    },
    {
        "ts": "2026-11-02T13:37:23.500Z",
        "level": "warn",
        "service": "billing-svc",
        "event_type": "db_query",
        "session_id": "sess-0001",
        "agent_auto": True,
        "message": "SELECT took 120ms",
        "env": "prod",
        "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
        "payload": {
            "db_system": "postgresql",
            "operation": "SELECT",
            "statement": "SELECT * FROM orders WHERE id=$1",
            "duration_ms": 120.0,
        },
    },
    {
        "ts": "2026-11-02T13:37:25.000Z",
        "level": "critical",
        "service": "ios-app",
        "event_type": "crash",
        "session_id": "sess-0001",
        "agent_auto": True,
        "message": "uncaught exception",
        "env": "prod",
        "payload": {
            "exception.type": "NSException",
            "exception.message": "index out of bounds",
        },
    },
    {
        "ts": "2026-11-02T13:37:26.000Z",
        "level": "trace",
        "service": "ios-app",
        "event_type": "ui_interaction",
        "session_id": "sess-0001",
        "agent_auto": True,
        "message": "button tapped",
        "payload": {"view": "LoginScreen", "action": "submit"},
    },
]


def main():
    all_ok = True
    print("=" * 70)
    print("agent-log → OTLP 适配性验证")
    print("=" * 70)
    for ev in SAMPLES:
        name = ev["event_type"] + ("(auto)" if ev["agent_auto"] else "(manual)")
        problems, env = checks_for(ev, name)
        status = "PASS" if not problems else "FAIL"
        if problems:
            all_ok = False
        print(f"\n[{status}] {name}  service={ev['service']} level={ev['level']}")
        for p in problems:
            print(f"    - {p}")
        # 展示一条完整 envelope（network_request 那条的 span 最有看点）
    # 单独 dump 一条完整 OTLP/JSON 供核对
    demo = next(e for e in SAMPLES if e["event_type"] == "network_request")
    envelope, _rec, _span = build_envelope(demo)
    print("\n" + "-" * 70)
    print("示例 OTLP/JSON envelope（network_request，含 LogRecord + Span）:")
    print("-" * 70)
    print(json.dumps(envelope, indent=2, ensure_ascii=False))
    print("=" * 70)
    print("总结果:", "ALL PASS ✅" if all_ok else "HAS FAILURES ❌")
    print("=" * 70)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
