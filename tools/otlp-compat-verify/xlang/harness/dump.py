#!/usr/bin/env python3
"""Python 端的基准 dump：读样例事件数组，写出只含 logs / traces 的 OTLP/JSON。

用法：python3 dump.py <samples.json> <logs.out> <traces.out>
依赖：PYTHONPATH 指向 logging-framework/python/AgentLog。
"""
import json
import sys

from agentlog.otlp import to_otlp_logs, to_otlp_spans


def main() -> int:
    samples_path, logs_path, traces_path = sys.argv[1:4]
    with open(samples_path, "r", encoding="utf-8") as f:
        events = json.load(f)
    with open(logs_path, "w", encoding="utf-8") as f:
        json.dump(to_otlp_logs(events), f, ensure_ascii=False)
    with open(traces_path, "w", encoding="utf-8") as f:
        json.dump(to_otlp_spans(events), f, ensure_ascii=False)
    print("python: logs+traces written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
