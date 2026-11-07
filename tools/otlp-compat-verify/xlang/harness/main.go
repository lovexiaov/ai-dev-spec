// 跨语言一致性 dump（Go）：读样例事件数组，写出 logs / traces 两份 OTLP/JSON。
//
// 用法：go run . <samples.json> <logs.out> <traces.out>
package main

import (
	"encoding/json"
	"fmt"
	"os"

	agentlog "github.com/lovexiaov/agent-log-go/agentlog"
)

func main() {
	if len(os.Args) < 4 {
		fmt.Fprintln(os.Stderr, "usage: xlang <samples.json> <logs.out> <traces.out>")
		os.Exit(2)
	}
	raw, err := os.ReadFile(os.Args[1])
	if err != nil {
		panic(err)
	}
	var events []map[string]interface{}
	if err := json.Unmarshal(raw, &events); err != nil {
		panic(err)
	}
	items := make([]interface{}, len(events))
	for i, e := range events {
		items[i] = e
	}
	logs, err := agentlog.ToOTLPLogs(items, nil)
	if err != nil {
		panic(err)
	}
	traces, err := agentlog.ToOTLPSpans(items, nil)
	if err != nil {
		panic(err)
	}
	if err := os.WriteFile(os.Args[2], []byte(agentlog.ToOTLPJSON(logs)), 0o644); err != nil {
		panic(err)
	}
	if err := os.WriteFile(os.Args[3], []byte(agentlog.ToOTLPJSON(traces)), 0o644); err != nil {
		panic(err)
	}
	fmt.Println("go: logs+traces written")
}
