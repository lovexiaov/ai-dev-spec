import com.scaffold.agentlog.Json;
import com.scaffold.agentlog.OtlpMapper;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.List;
import java.util.Map;

/**
 * 跨语言一致性 dump：读样例事件数组，写出 logs / traces 两份 OTLP/JSON。
 *
 * <p>用法：{@code java XlangMain <samples.json> <logs.out> <traces.out>}
 */
public final class XlangMain {
    private XlangMain() {}

    @SuppressWarnings("unchecked")
    public static void main(String[] args) throws Exception {
        String text = new String(Files.readAllBytes(Paths.get(args[0])), StandardCharsets.UTF_8);
        List<Object> events = (List<Object>) Json.parse(text);
        Map<String, Object> both = OtlpMapper.toOtlp(events, null);
        Files.write(Paths.get(args[1]),
                OtlpMapper.toOtlpJson(both.get("logs")).getBytes(StandardCharsets.UTF_8));
        Files.write(Paths.get(args[2]),
                OtlpMapper.toOtlpJson(both.get("traces")).getBytes(StandardCharsets.UTF_8));
        System.out.println("java: logs+traces written");
    }
}
