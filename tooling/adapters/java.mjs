// tooling/adapters/java.mjs
// Java (Maven) 适配器。命令在含 pom.xml 的模块根目录执行。
export default {
  name: "java",
  stages: {
    // checkstyle：与 Kotlin 的 ktlint 对位，保证契约层代码风格一致。
    lint: "mvn -q -B checkstyle:check",
    // 编译器本身即类型检查；compile 比 build 更快、更聚焦。
    typecheck: "mvn -q -B -DskipTests compile",
    // JUnit 5 单元测试（含 SchemaTests / C7 字段集断言）。
    test: "mvn -q -B test",
    // 完整打包（jar）；跳过测试以复用 test 阶段结果。
    build: "mvn -q -B -DskipTests package",
  },
};
