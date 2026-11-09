// 跨语言一致性 dump（Swift/macOS）：读样例事件数组，写出 logs / traces 两份 OTLP/JSON。
//
// 用法：swiftc ... main.swift -o dump && ./dump <samples.json> <logs.out> <traces.out>
import Foundation

let args = CommandLine.arguments
guard args.count >= 4 else {
    FileHandle.standardError.write(Data("usage: dump <samples.json> <logs.out> <traces.out>\n".utf8))
    exit(2)
}

let samples = try JSONDecoder().decode(
    [[String: AgentValue]].self, from: Data(contentsOf: URL(fileURLWithPath: args[1])))

func text(_ map: [String: AgentValue], _ key: String) -> String? {
    if case .string(let v)? = map[key] { return v }
    return nil
}

let entries: [AgentLogEntry] = samples.map { map in
    AgentLogEntry(
        ts: text(map, "ts") ?? "",
        level: text(map, "level") ?? "info",
        service: text(map, "service") ?? "",
        subsystem: text(map, "subsystem") ?? "",
        category: text(map, "category") ?? "",
        eventType: text(map, "event_type") ?? "log",
        sessionId: text(map, "session_id") ?? "",
        traceId: text(map, "trace_id"),
        spanId: text(map, "span_id"),
        agentAuto: map["agent_auto"] == .bool(true),
        message: text(map, "message") ?? "",
        env: text(map, "env"),
        release: text(map, "release"),
        userId: text(map, "user_id"),
        payload: {
            if case .object(let p)? = map["payload"] { return p }
            return nil
        }()
    )
}

let batch = try OtlpMapper.toOtlp(entries)
guard case .object(let root) = batch, let logs = root["logs"], let traces = root["traces"] else {
    fatalError("unexpected batch shape")
}
try OtlpMapper.json(logs).write(toFile: args[2], atomically: true, encoding: .utf8)
try OtlpMapper.json(traces).write(toFile: args[3], atomically: true, encoding: .utf8)
print("swift: logs+traces written")
