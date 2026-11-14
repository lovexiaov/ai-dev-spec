---
name: multi-repo-release
description: ai-dev-spec 六端 SDK 子仓 + monorepo 的多仓发版与 submodule 指针维护 SOP。打 tag、重指 tag、推送子仓、更新 gitlink、排查 workflow scope / macOS runner 排队 / CI 红灯，或准备 npm/PyPI 首次发布时使用。
agent_created: true
---

# 多仓发版与 submodule 指针维护

## 结构

`ai-dev-spec`（monorepo）通过 gitlink 挂六个独立子仓：`logging-framework/{python,go,java,android,web,macos}`。
发版动作横跨 **7 个仓库**（六子仓 + monorepo），任一环漏推都会让远端状态不自洽。

## 发版前检查清单

1. **逐仓确认在 `main`**：子仓 checkout 后默认 **detached HEAD**，`git rev-parse --abbrev-ref HEAD` 必须是 `main`；
   否则 push 显示 "Everything up-to-date"、tag 打到游离提交。
2. **格式化器 + 跨端校验**：按 `xlang-verify` skill 走一遍（gofmt / ktlint / prettier + `xlang_verify.py`）。
   历史教训：tag 已打但 Go CI 红在 `gofmt` 对齐；`xlang_verify` 只校验运行时、不校验格式。
3. **工作区干净**：按 hunk 拆分提交后 `git diff` 逐仓核对未暂存残留（索引树不自洽只有 CI 能发现）。
4. **人工确认**：force push、tag 重指、npm/PyPI 发布、GitHub Release 均属「不可逆 / 对外可见」，必须先获人工确认。

## 顺序

1. 六子仓各自 `git commit` → annotated tag `vN.N.N`（核对 `vN.N.N^{}` == HEAD）→
   `git push origin main` + `git push origin vN.N.N`。
2. **改了 `.github/workflows/*` 时**：推送所用 PAT 必须带 `workflow` scope（fine-grained PAT 需
   Workflows = Read and write）。本机 git 走 `gh auth git-credential` 的经典 `ghp_…` token；
   缺 scope 会报 `refusing to allow a Personal Access Token to create or update workflow`。
   加 scope 在服务端改、token 字符串不变；OAuth token 用 `gh auth refresh -h github.com -s workflow`。
3. **tag 已推但 CI 红**：追加修复提交 → `git push --force origin vN.N.N` 重指 tag（仅限刚发布、无外部消费）
   → monorepo 补一条子模块指针提交。
4. **更新 monorepo gitlink**：先用 `git ls-remote` 确认目标 commit **已推送到子仓远端**，
   再 `git add <submodule>` → commit → push（pre-push 会跑 gate-runner 全量门禁）。
   **绝不把本地未推送的提交写进 gitlink**：全新 `clone --recurse-submodules` 会因 `reference is not a tree` 失败。
   若本地已有未推送提交：子仓 `git checkout -b wip/<topic>` 保存 + `git branch -f main <pushed-commit>`，再更新指针。
5. **CI 收尾**：7 仓全 success 才算完成。GitHub 托管 macOS arm64 runner 常容量不足
   （"job not acquired by Runner" 排队超时），**与代码无关**，`gh run rerun --failed` 重跑即可。

## npm / PyPI 发布（见 `docs/specs/ai-events/RELEASING.md`）

- 两端包名 `cn.lovexiaov.agent.log`；Go module path 例外保持 `github.com/lovexiaov/agent-log-go`。
- **首次发布不对称**：PyPI 支持 _pending publisher_（项目不存在也能预配、首次使用即创建项目、免 API token）；
  **npm Trusted Publishing 要求包名已存在 → v1.4.0 首发必须手动 `npm publish`**。
- `--provenance` 只能在 CI 用（需 OIDC `id-token: write`），本地发布不带该 flag。
- 本机 `~/.npmrc` registry = `registry.npmmirror.com`，publish 必须显式
  `--registry=https://registry.npmjs.org/`；本机可能未装 `twine`（先 `pip install twine`）。
- PyPI 开 2FA 后账密上传被拒，用 `__token__` + API token；npm 需验证邮箱 + 2FA（或 bypass-2FA Granular Token）。
- **首次上传永久占用包名与版本号**，同一版本不能重传。

## 最终验证

- `git ls-remote` 核对每仓 main 与 tag 指向一致；monorepo `git ls-tree HEAD <submodule>` 的每个 gitlink
  都能在子仓远端找到。
- 做一次全新 clone 验证：`git clone --recurse-submodules` 成功检出六个子仓、无 dangling reference。
- 7 仓 CI 全绿后再把 `tasks.md` 的发布项标 done（验证门禁）。
