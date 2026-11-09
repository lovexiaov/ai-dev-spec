// 跨语言一致性 dump（Kotlin/Android）：读样例事件数组，写出 logs / traces 两份 OTLP/JSON。
//
// 用法：kotlinc -cp <agentlog-core.jar> Dump.kt -d dump.jar
//       java -cp dump.jar:<agentlog-core.jar> DumpKt <samples.json> <logs.out> <traces.out>
import cn.lovexiaov.agent.log.Json
import cn.lovexiaov.agent.log.JsonValue
import cn.lovexiaov.agent.log.LogEvent
import cn.lovexiaov.agent.log.OtlpMapper
import cn.lovexiaov.agent.log.toJsonValue
import java.io.File

@Suppress("UNCHECKED_CAST")
fun main(args: Array<String>) {
    require(args.size >= 3) { "usage: DumpKt <samples.json> <logs.out> <traces.out>" }
    val samples = Json.parse(File(args[0]).readText()) as List<Any?>

    val events = samples.map { raw ->
        val m = raw as Map<String, Any?>
        fun str(key: String): String? = m[key] as? String
        val payload = (m["payload"] as? Map<String, Any?>)
            ?.mapValues { (_, v) -> v.toJsonValue() }
        LogEvent(
            ts = str("ts") ?: "",
            level = str("level") ?: "info",
            service = str("service") ?: "",
            subsystem = str("subsystem"),
            category = str("category"),
            eventType = str("event_type") ?: "log",
            sessionId = str("session_id") ?: "",
            traceId = str("trace_id"),
            spanId = str("span_id"),
            agentAuto = m["agent_auto"] as? Boolean ?: false,
            message = str("message") ?: "",
            env = str("env"),
            userId = str("user_id"),
            payload = payload,
        )
    }

    val batch = OtlpMapper.toOtlp(events) as JsonValue.Obj
    File(args[1]).writeText(OtlpMapper.toOtlpJson(batch.value.getValue("logs")))
    File(args[2]).writeText(OtlpMapper.toOtlpJson(batch.value.getValue("traces")))
    println("kotlin: logs+traces written")
}
