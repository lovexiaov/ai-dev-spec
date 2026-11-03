// tooling/adapters/swift.mjs
// Swift (SwiftPM) 适配器。命令在含 Package.swift 的模块根目录执行。
export default {
  name: "swift",
  stages: {
    lint: "swiftlint",
    typecheck: "swift build",
    test: "swift test",
    build: "swift build",
  },
};
