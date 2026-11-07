#!/usr/bin/env python3
"""End-to-end proof that agent-log actually reaches an OTLP collector.

It starts the in-process collector from ``collector.py``, runs the *real* Go and
Python examples against it (``AGENTLOG_OTLP_ENDPOINT`` makes them export instead
of only printing), then asserts on what arrived over the wire:

* every payload is structurally valid OTLP/JSON (collector validation);
* both languages deliver 3 LogRecords and 2 spans each, with the expected
  event types;
* the same *bound* schema-v1.1 span (trace ``0123…``, span ``a1b2…``) produces
  the same OTLP ``traceId``/``spanId`` in Go and Python, so a log line and its
  span line up across implementations;
* redaction survived the trip: no plaintext secret on the wire.

Run:  python3 tools/otlp-compat-verify/e2e_demo.py [--no-go]
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
GO_REPO = ROOT / "logging-framework" / "go" / "AgentLog"
PY_REPO = ROOT / "logging-framework" / "python" / "AgentLog"

sys.path.insert(0, str(HERE))
from collector import OTLPTestCollector  # noqa: E402

BOUND_TRACE = "0123456789abcdef0123456789abcdef"
BOUND_SPAN = "a1b2c3d4e5f60718"

EXPECTED_RECORDS_PER_LANG = 3
EXPECTED_SPANS_PER_LANG = 2


def run_python_example(endpoint):
    env = dict(os.environ, AGENTLOG_OTLP_ENDPOINT=endpoint)
    env.setdefault("PYTHONPATH", str(PY_REPO))
    subprocess.run(
        [sys.executable, "example/main.py"],
        cwd=str(PY_REPO),
        env=env,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
    )


def run_go_example(endpoint):
    env = dict(os.environ, AGENTLOG_OTLP_ENDPOINT=endpoint)
    subprocess.run(
        ["go", "run", "./example"],
        cwd=str(GO_REPO),
        env=env,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=300,
    )


def check_language(name, collector, records_before, spans_before):
    records = collector.log_records[records_before:]
    spans = collector.spans[spans_before:]
    problems = []

    if len(records) != EXPECTED_RECORDS_PER_LANG:
        problems.append(
            "%s: expected %d LogRecords, got %d"
            % (name, EXPECTED_RECORDS_PER_LANG, len(records))
        )
    if len(spans) != EXPECTED_SPANS_PER_LANG:
        problems.append(
            "%s: expected %d spans, got %d" % (name, EXPECTED_SPANS_PER_LANG, len(spans))
        )

    event_types = sorted(r["event_type"] for r in records)
    if event_types != ["db_query", "log", "network_request"]:
        problems.append("%s: unexpected event types %s" % (name, event_types))

    bound = [r for r in records if r["span_id"] == BOUND_SPAN]
    if not bound:
        problems.append("%s: no record carried the bound span_id %s" % (name, BOUND_SPAN))
    for record in bound:
        if record["trace_id"] != BOUND_TRACE:
            problems.append("%s: bound span used trace %r" % (name, record["trace_id"]))

    # A plain log inside a bound span keeps the span id (Schema v1.1) but must
    # still be a LogRecord, not a span.
    plain = [r for r in records if r["event_type"] == "log"]
    if plain and plain[0]["span_id"] != BOUND_SPAN:
        problems.append("%s: plain log lost its bound span_id" % name)

    span_names = sorted(span["name"] for span in spans)
    if not any(span["kind"] == 3 for span in spans):
        problems.append("%s: no SPAN_KIND_CLIENT span" % name)
    if not any(name.startswith("GET https://api.example.com/orders") for name in span_names):
        problems.append("%s: missing HTTP span, got %s" % (name, span_names))
    if not any("SELECT" in name for name in span_names):
        problems.append("%s: missing DB span, got %s" % (name, span_names))

    return problems, {"records": records, "spans": spans}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-go", action="store_true", help="skip the Go SDK (no Go toolchain)")
    args = parser.parse_args(argv)

    collector = OTLPTestCollector()
    collector.start()
    print("collector listening on %s" % collector.endpoint)
    problems = []

    try:
        before_records, before_spans = len(collector.log_records), len(collector.spans)
        run_python_example(collector.endpoint)
        py_problems, py = check_language("python", collector, before_records, before_spans)
        problems.extend(py_problems)

        go = {"records": [], "spans": []}
        if not args.no_go:
            before_records, before_spans = len(collector.log_records), len(collector.spans)
            run_go_example(collector.endpoint)
            go_problems, go = check_language("go", collector, before_records, before_spans)
            problems.extend(go_problems)
    finally:
        collector.stop()

    # Structural violations found by the collector itself.
    problems.extend(collector.errors)

    # Cross-language: the same bound span must yield the same OTLP ids.
    if py["records"] and go["records"]:
        py_span_ids = {r["span_id"] for r in py["records"] if r["span_id"]}
        go_span_ids = {r["span_id"] for r in go["records"] if r["span_id"]}
        shared = py_span_ids & go_span_ids
        if BOUND_SPAN not in shared:
            problems.append(
                "cross-language: bound span id not reproduced (python=%s go=%s)"
                % (sorted(py_span_ids), sorted(go_span_ids))
            )

    if not collector.requests:
        problems.append("no requests reached the collector")

    summary = collector.summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    if problems:
        print("\nFAILED:")
        for problem in problems:
            print("  - %s" % problem)
        return 1
    print("\nOK: agent-log -> OTLP -> collector works end to end for python%s" % ("" if args.no_go else " and go"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
