// tooling/adapters/go.mjs
// Go (modules) 适配器。命令在含 go.mod 的模块根目录执行。
export default {
  name: "go",
  stages: {
    // gofmt 有输出即视为未格式化 → 失败。
    lint: 'test -z "$(gofmt -l .)"',
    // go vet 静态检查（类型/可疑构造）。
    typecheck: "go vet ./...",
    // go test（含 TestSchemaConformance / C7 字段集断言）。
    test: "go test ./...",
    build: "go build ./...",
  },
};
