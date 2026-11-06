// tooling/adapters/kotlin.mjs
// Kotlin (JVM) 适配器。命令在含 gradlew 的模块根目录执行（纯 Kotlin/JVM 模块，无需 Android SDK）。
// 语言知识全部收口在此：新增 Kotlin 模块只需在模块根放 .toolchain.json 并声明 adapter: "kotlin"。
export default {
  name: "kotlin",
  stages: {
    // Kotlin 编译器本身即类型检查；用 compileKotlin 比 build 更快、更聚焦。
    typecheck: "./gradlew compileKotlin",
    // JVM 单元测试（SchemaTests / LoggerTests 等），无需 Android。
    test: "./gradlew test",
    // 完整构建（含 jar 产出）；非 Android 模块无需 SDK。
    build: "./gradlew build",
    // Kotlin 无内置 linter；接入 ktlint/detekt 后在此补 lint 阶段，避免破坏契约。
  },
};
