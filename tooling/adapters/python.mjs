// tooling/adapters/python.mjs
// Python (stdlib-only) 适配器。命令在含 agentlog/ 包的模块根目录执行。
// 该实现坚持零第三方依赖，故不引入 ruff / mypy / pytest；
// typecheck 与 build 无对应动作，省略后 gate-runner 会自动跳过。
export default {
  name: "python",
  stages: {
    // 语法/字节码编译检查（stdlib）。
    lint: "python3 -m compileall -q agentlog",
    // 标准库 unittest（含 SchemaTests / C7 字段集断言）。
    test: "python3 -m unittest discover -s tests",
  },
};
