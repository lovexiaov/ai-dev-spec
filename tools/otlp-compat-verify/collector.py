#!/usr/bin/env python3
"""A throwaway OTLP/HTTP collector for verifying agent-log exporters end to end.

It accepts ``POST /v1/logs`` and ``POST /v1/traces`` (OTLP/JSON), validates the
structural invariants of every record/span it receives, and reports a summary.
No OpenTelemetry dependency: it is a few hundred lines of ``http.server`` so the
verification can run anywhere, including CI.

Two ways to use it:

1. **Standalone** — useful to point a real app at, or to eyeball the payload::

       python3 collector.py --port 4318
       # in another shell: AGENTLOG_OTLP_ENDPOINT=http://127.0.0.1:4318 python3 example/main.py

   With ``--expect-records`` / ``--expect-spans`` it exits non-zero unless the
   expectations were met, which makes it usable as a CI gate.

2. **Imported** — :class:`OTLPTestCollector` runs in a thread, so a test can
   assert on what actually went over the wire (see ``e2e_demo.py``).
"""

import argparse
import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOGS_PATH = "/v1/logs"
TRACES_PATH = "/v1/traces"

TRACE_ID_RE = re.compile(r"^[0-9a-f]{32}$")
SPAN_ID_RE = re.compile(r"^[0-9a-f]{16}$")


class OTLPTestCollector:
    """In-process OTLP/JSON collector that records and validates requests.

    Usage::

        with OTLPTestCollector() as collector:
            ...                      # export to collector.endpoint
        collector.assert_clean()
    """

    def __init__(self, host="127.0.0.1", port=0):
        self.host = host
        self.port = port
        self.requests = []          # raw request log
        self.log_records = []       # flattened LogRecords
        self.spans = []             # flattened Spans
        self.errors = []            # structural violations
        self._server = None
        self._thread = None
        self._lock = threading.Lock()

    # -- lifecycle ------------------------------------------------------- #

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc_info):
        self.stop()

    def start(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_POST(self):  # noqa: N802 - stdlib naming
                outer._handle(self)

            def log_message(self, *args):
                pass

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            kwargs={"poll_interval": 0.02},
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None

    @property
    def endpoint(self):
        return "http://%s:%d" % (self.host, self.port)

    # -- request handling ------------------------------------------------ #

    def _handle(self, handler):
        length = int(handler.headers.get("Content-Length") or 0)
        raw = handler.rfile.read(length)
        content_type = (handler.headers.get("Content-Type") or "").lower()
        path = handler.path

        entry = {"path": path, "content_type": content_type, "bytes": len(raw)}
        with self._lock:
            self.requests.append(entry)

        if path not in (LOGS_PATH, TRACES_PATH):
            self._fail("unexpected path %r" % path)
            return self._reply(handler, 404, {"error": "unknown signal"})
        if "application/json" not in content_type:
            self._fail("unexpected content-type %r for %s" % (content_type, path))
            return self._reply(handler, 415, {"error": "expected application/json"})

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._fail("%s body is not valid JSON: %s" % (path, exc))
            return self._reply(handler, 400, {"error": "malformed JSON"})

        with self._lock:
            if path == LOGS_PATH:
                self._ingest_logs(payload)
            else:
                self._ingest_traces(payload)
        return self._reply(handler, 200, {})

    def _reply(self, handler, status, body):
        encoded = json.dumps(body).encode("utf-8")
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(encoded)))
        handler.end_headers()
        handler.wfile.write(encoded)

    def _fail(self, message):
        with self._lock:
            self.errors.append(message)

    # -- validation ------------------------------------------------------ #

    def _ingest_logs(self, payload):
        groups = payload.get("resourceLogs")
        if not isinstance(groups, list):
            self.errors.append("logs: missing resourceLogs list")
            return
        for group in groups:
            service = _attribute(group.get("resource"), "service.name")
            session = _attribute(group.get("resource"), "session.id")
            for scope in group.get("scopeLogs") or []:
                for record in scope.get("logRecords") or []:
                    self._validate_record(record, service, session)

    def _validate_record(self, record, service, session):
        self.log_records.append(
            {
                "service": service,
                "session": session,
                "event_type": _attribute(record, "agent.event.type", scope="attributes"),
                "severity_text": record.get("severityText"),
                "severity_number": record.get("severityNumber"),
                "message": (record.get("body") or {}).get("stringValue"),
                "trace_id": record.get("traceId"),
                "span_id": record.get("spanId"),
            }
        )
        if not isinstance(record.get("timeUnixNano"), str):
            self.errors.append("logRecord.timeUnixNano must be a string (int64 JSON rule)")
        if not isinstance(record.get("severityNumber"), int):
            self.errors.append("logRecord.severityNumber must be an integer")
        if "body" not in record:
            self.errors.append("logRecord.body missing")
        if "traceId" in record and not TRACE_ID_RE.match(str(record["traceId"])):
            self.errors.append("logRecord.traceId is not 32 lowercase hex: %r" % (record["traceId"],))
        if "spanId" in record and not SPAN_ID_RE.match(str(record["spanId"])):
            self.errors.append("logRecord.spanId is not 16 lowercase hex: %r" % (record["spanId"],))

    def _ingest_traces(self, payload):
        groups = payload.get("resourceSpans")
        if not isinstance(groups, list):
            self.errors.append("traces: missing resourceSpans list")
            return
        for group in groups:
            service = _attribute(group.get("resource"), "service.name")
            for scope in group.get("scopeSpans") or []:
                for span in scope.get("spans") or []:
                    self._validate_span(span, service)

    def _validate_span(self, span, service):
        self.spans.append(
            {
                "service": service,
                "name": span.get("name"),
                "kind": span.get("kind"),
                "trace_id": span.get("traceId"),
                "span_id": span.get("spanId"),
                "start": span.get("startTimeUnixNano"),
                "end": span.get("endTimeUnixNano"),
                "attributes": {kv["key"]: kv["value"] for kv in span.get("attributes") or []},
            }
        )
        if not TRACE_ID_RE.match(str(span.get("traceId"))):
            self.errors.append("span.traceId is not 32 lowercase hex: %r" % (span.get("traceId"),))
        if not SPAN_ID_RE.match(str(span.get("spanId"))):
            self.errors.append("span.spanId is not 16 lowercase hex: %r" % (span.get("spanId"),))
        for key in ("startTimeUnixNano", "endTimeUnixNano"):
            if not isinstance(span.get(key), str):
                self.errors.append("span.%s must be a string (int64 JSON rule)" % key)
        try:
            if int(span["endTimeUnixNano"]) < int(span["startTimeUnixNano"]):
                self.errors.append("span end precedes start: %r" % (span.get("name"),))
        except (KeyError, TypeError, ValueError):
            self.errors.append("span has non-numeric time window")

    # -- assertions ------------------------------------------------------ #

    def assert_clean(self):
        if self.errors:
            raise AssertionError("collector rejected payloads:\n  " + "\n  ".join(self.errors))

    def summary(self):
        event_types = {}
        for record in self.log_records:
            event_types[record["event_type"]] = event_types.get(record["event_type"], 0) + 1
        services = sorted({r["service"] for r in self.log_records if r["service"]})
        return {
            "requests": len(self.requests),
            "log_records": len(self.log_records),
            "spans": len(self.spans),
            "event_types": event_types,
            "services": services,
            "errors": list(self.errors),
        }


def _attribute(container, key, scope=None):
    """Read one attribute from a resource or an OTLP object."""
    if not isinstance(container, dict):
        return None
    if scope:
        pairs = container.get(scope) or []
    else:
        pairs = (container.get("attributes") or [])
    for kv in pairs:
        if kv.get("key") == key:
            return (kv.get("value") or {}).get("stringValue")
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description="Minimal OTLP/JSON collector for agent-log verification")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4318)
    parser.add_argument("--expect-records", type=int, default=None, help="exit non-zero unless this many LogRecords arrive")
    parser.add_argument("--expect-spans", type=int, default=None, help="exit non-zero unless this many spans arrive")
    parser.add_argument("--timeout", type=float, default=60.0, help="stop after this many seconds")
    args = parser.parse_args(argv)

    collector = OTLPTestCollector(host=args.host, port=args.port)
    collector.start()
    print("listening on %s (Ctrl-C to stop)" % collector.endpoint, flush=True)

    def satisfied():
        if args.expect_records is not None and len(collector.log_records) < args.expect_records:
            return False
        if args.expect_spans is not None and len(collector.spans) < args.expect_spans:
            return False
        return True

    try:
        if args.expect_records is None and args.expect_spans is None:
            time.sleep(args.timeout)
        else:
            waited = 0.0
            while waited < args.timeout and not satisfied():
                time.sleep(0.05)
                waited += 0.05
    except KeyboardInterrupt:
        pass
    finally:
        collector.stop()

    print(json.dumps(collector.summary(), indent=2, ensure_ascii=False))
    problems = list(collector.errors)
    if args.expect_records is not None and len(collector.log_records) != args.expect_records:
        problems.append("expected %d LogRecords, got %d" % (args.expect_records, len(collector.log_records)))
    if args.expect_spans is not None and len(collector.spans) != args.expect_spans:
        problems.append("expected %d spans, got %d" % (args.expect_spans, len(collector.spans)))
    if problems:
        print("\nFAILED:")
        for problem in problems:
            print("  - %s" % problem)
        return 1
    print("\nOK: payloads are structurally valid OTLP/JSON")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
