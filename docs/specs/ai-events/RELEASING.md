# RELEASING — npm / PyPI 发布操作手册

> 面向人：本手册记录**只能人工完成**的账号、凭据与首发步骤。
> Agent 不得自动执行任何 `publish` / `upload`（对外可见且不可逆，受 AGENTS.md §3 ASK FIRST 约束）。
> 适用仓库：`agent-log-python`、`agent-log-web`（monorepo 内为 submodule）。
> 状态快照见同目录 `handoff.md`「发布准备状态」；本文件只写**稳定操作流程**。
> 核实时间：2026-11-14（依据 npm / PyPI / GitHub 官方文档）。

## 0. 先读：两条路径的不对称

|                          | PyPI（python）                                                                       | npm（web）                                                                         |
| ------------------------ | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| 包名                     | `cn.lovexiaov.agent.log`（规范化后 `cn-lovexiaov-agent-log`）                        | `cn.lovexiaov.agent.log`（unscoped）                                               |
| 版本                     | `1.4.0`                                                                              | `1.4.0`                                                                            |
| 首次发布能否全自动       | **能**：可预配 _pending publisher_，首次使用即创建项目、无需 API token               | **不能**：Trusted Publishing 要求包名已存在于 registry，首次必须手动 `npm publish` |
| 2FA 后如何传凭据         | 必须用 **API token**（`__token__`）；账密会被拒                                      | 交互式发布输 OTP；CI 用带 _bypass 2FA_ 的 Granular Access Token                    |
| `release.yml` 的认证方式 | Trusted Publishing（OIDC，免 token，`id-token: write`）                              | `secrets.NPM_TOKEN` + `--provenance`                                               |
| 当前既定决策             | **v1.4.0 手动首发；tag 保持 publish-config 不动；release.yml 只进 main，管未来版本** | 同左                                                                               |

已确认的事实（不要重复排查）：

- 包名含点是合法的：`validate-npm-package-name` 官方示例 `example.com` 即带点；本包名全小写、URL-safe、不以 `.` 开头。两个 registry 上均**未被占用**。
- 本机 `~/.npmrc` 把 registry 指向 `https://registry.npmmirror.com`（淘宝镜像），**publish 前必须切回官方源**，否则报 `ENEEDAUTH`。
- 本机 git 走 `gh auth git-credential`，用的是**经典 PAT `ghp_…`**，当前 scopes 为 `admin:org, admin:public_key, delete:packages, repo, write:packages` —— **缺 `workflow`**，这是 `release.yml` 推送被拒的唯一原因。
- Python 端本机**未安装 `twine`**；`dist/` 在两端都不入库（`.gitignore`），发布前必须现构建。
- 版本号一经上传**永久占用**，删除 release 也不能重传同名同版本；只能 bump 版本。

## 1. 一次性准备（人工，约 10 分钟）

### 1.1 npm 账号

1. 注册：https://www.npmjs.com/signup —— 用户名 / 邮箱 / 密码
2. **点邮箱验证链接**（未验证不能 publish）
3. 头像 → Account settings → **Two-Factor Authentication → Enable 2FA**，用验证器 App 扫码，**保存恢复码**
   - 官方现行规则：所有包发布要求 **2FA，或带「bypass 2FA」的 Granular Access Token**
4. 验证登录：`npm login --registry=https://registry.npmjs.org/` → `npm whoami`

> 免费账号即可。本包是 unscoped（无 `@`），默认 public，无需建组织、无需付费、无需 `--access public`（加了也无害）。

### 1.2 PyPI 账号

1. 注册：https://pypi.org/account/register/
2. 验证邮箱
3. Account settings → **Two-factor authentication → 启用**（PyPI 强制）
4. 可选演练：https://test.pypi.org/account/register/（**独立账号**，需单独开 2FA）

### 1.3 GitHub PAT 加 `workflow` scope

GitHub → Settings → Developer settings → Personal access tokens → **Tokens (classic)** → 找到 `ghp_…` → **Edit → 勾选 `workflow` → Update**。

- 服务端改 scope，token 字符串不变，本机无需任何改动。
- 若是 fine-grained PAT：需 **Workflows = Read and write**。
- 若 `gh` 持有的是 OAuth token：`gh auth refresh -h github.com -s workflow`。

### 1.4 本机 npm registry（只影响手动发布）

**不要改全局 `~/.npmrc`**，在命令里显式指定即可：

```bash
npm config get registry    # 当前是 npmmirror，属预期
# 所有 publish / login / view 命令都带：
#   --registry=https://registry.npmjs.org/
```

## 2. 手动首发 v1.4.0（按既定决策）

### 2.1 Python → PyPI

```bash
cd /Users/marco/Dev-project/ai-dev-spec/logging-framework/python/AgentLog

python3 -m pip install -U build twine       # 本机缺 twine
rm -rf dist build *.egg-info                # 均为 .gitignore 产物
python3 -m build                            # 产出 sdist + wheel
python3 -m twine check dist/*
python3 -m twine upload dist/*              # 需 API token
```

凭据（**2FA 开启后账密登录会失败，必须用 token**）：在 https://pypi.org/manage/account/token/ 建 API token，然后二选一：

```bash
# a) 环境变量（推荐，不落盘）
TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-<你的token> python3 -m twine upload dist/*

# b) ~/.pypirc（注意权限 600）
# [pypi]
#   username = __token__
#   password = pypi-<你的token>
```

产物实测（2026-11-11）：`cn_lovexiaov_agent_log-1.4.0-py3-none-any.whl`（含全部 `agentlog` 模块 + LICENSE + METADATA）与 `.tar.gz`（含 `agentlog/` + README + LICENSE + pyproject）。

### 2.2 Web → npm

```bash
cd /Users/marco/Dev-project/ai-dev-spec/logging-framework/web/Observability

pnpm build                                  # dist/ 不入库，必须先构建
npm pack --dry-run                           # 核对：仅 33 个 dist 文件、含 .d.ts、无 src/
npm login --registry=https://registry.npmjs.org/
npm publish --registry=https://registry.npmjs.org/ --otp=<验证器6位码>
```

**不要加 `--provenance`**：provenance 需要 OIDC 身份令牌，只有 CI（GitHub Actions + `id-token: write`）能签发；本地发布会静默丢证明或直接失败。CI 侧 `release.yml` 里已带 `--provenance`，是对的。

`--otp` 是验证器 App 的 6 位动态码，**不是** access token；把 `npm_xxx` 塞进 `--otp` 会得到 `403 Two-factor authentication ... is required`。

## 3. 恢复 `release.yml` 到 main（加完 scope 后）

两个子仓的发布工作流提交被保存在本地分支 `wip/release-ci`，**未删除、未改写**：

| 子仓   | `wip/release-ci` | 当前 main（= tag v1.4.0） |
| ------ | ---------------- | ------------------------- |
| python | `ed04461`        | `71bd978`                 |
| web    | `ca1b97f`        | `1f02605`                 |

```bash
cd /Users/marco/Dev-project/ai-dev-spec/logging-framework/python/AgentLog
git checkout main && git merge wip/release-ci && git push origin main
# 同理在 logging-framework/web/Observability 执行一遍
```

- **tag v1.4.0 不动**（仍指向 publish-config 提交，不含 release.yml）——这是已确认的决策。
- 合并后 main 前进而 tag 未动，monorepo 指针是否跟进是**可选**的：不跟也不影响 clone（现指针 `71bd978`/`1f02605` 已在远端存在）；若要跟，先把子仓 push 成功再更新 gitlink（参见 MEMORY.md：指针只能指向远端已存在的提交）。
- monorepo `33124fe` 已修掉此前「指针指向本地未推送提交」的悬空引用，全新 `clone --recurse-submodules` 实测通过。

## 4. 未来版本的自动化（v1.4.1+）

### 4.1 让 `release.yml` 真正能跑起来

| 仓库   | 需要配的东西                           | 入口                                                                        |
| ------ | -------------------------------------- | --------------------------------------------------------------------------- |
| python | **PyPI pending publisher**（免 token） | https://pypi.org/manage/account/publishing/ → _Add a new pending publisher_ |
| web    | GitHub Secret **`NPM_TOKEN`**          | 仓库 Settings → Secrets and variables → Actions → New repository secret     |

**PyPI pending publisher 字段**（官方支持「项目尚不存在时预配置」，首次使用即创建项目并自动转为普通 publisher）：

| 字段              | 值                                                                        |
| ----------------- | ------------------------------------------------------------------------- |
| PyPI project name | `cn-lovexiaov-agent-log`（若表单要求原始名则填 `cn.lovexiaov.agent.log`） |
| Owner             | `lovexiaov`                                                               |
| Repository name   | `agent-log-python`                                                        |
| Workflow name     | `release.yml`（只填文件名，不带路径）                                     |
| Environment name  | 留空（现有 workflow 未声明 environment）                                  |

> 注意：pending publisher **不预留包名**，仅在首次实际发布时创建项目；若期间被他人抢注会失效。首次 publish 有时需到 PyPI 侧点一次批准。

**`NPM_TOKEN`**：npm → Access Tokens → **Granular Access Token**，勾 **bypass 2FA**、权限限定到该包、设置合理过期时间。值只放进 GitHub Secrets，**绝不写进仓库或本手册**。

### 4.2 发新版流程

1. 两端 bump 版本（`pyproject.toml` + `__version__` / `SDK_VERSION`；`package.json` + `SDK_VERSION`），按 T10 的 13 处字面量清单同步
2. 提交、打 tag `v1.4.1`（此时 tag 内含 `release.yml`）
3. 推送 tag → 两个 workflow 自动构建并发布
4. 按 §5 验证

### 4.3 可选升级：web 改用 npm Trusted Publishing（OIDC 免 token）

首发成功后才可做（包名须已存在）。要求 **npm CLI ≥ 11.5.1 / Node ≥ 22.14.0**，且需**同时改 `release.yml` 三处**：

- 删除 `NODE_AUTH_TOKEN` env 与 `secrets.NPM_TOKEN` 依赖
- 删除 `setup-node` 的 `registry-url`（它会注入占位 `NODE_AUTH_TOKEN`，导致 npm 不走 OIDC）
- 确认 `permissions: id-token: write`（已有）；`npm publish` 会自动附带 provenance

在 https://www.npmjs.com/package/cn.lovexiaov.agent.log/access → **Trusted Publisher** 添加：Organization/User `lovexiaov`、Repository `agent-log-web`、Workflow filename `release.yml`、Environment 留空。**大小写敏感、逐字匹配**，不一致会报认证错而非提示。

## 5. 验证清单（每次发布后）

```bash
# PyPI
pip install --index-url https://pypi.org/simple cn.lovexiaov.agent.log==1.4.0
python3 -c "import agentlog; print(agentlog.__version__)"
open https://pypi.org/project/cn-lovexiaov-agent-log/

# npm（干净临时目录，验证三个 exports 子路径）
npm view cn.lovexiaov.agent.log version --registry=https://registry.npmjs.org/
npm pack cn.lovexiaov.agent.log --dry-run
open https://www.npmjs.com/package/cn.lovexiaov.agent.log
```

检查项：版本号正确、README 渲染正常、wheel/sdist 齐全、npm tarball 含 `dist/*.d.ts` 且无 `src/` 泄漏、三个导出入口可解析。

## 6. 故障速查

| 现象                                                                                                | 原因                                        | 处理                                            |
| --------------------------------------------------------------------------------------------------- | ------------------------------------------- | ----------------------------------------------- |
| `ENEEDAUTH` / publish 401                                                                           | 本机 registry 指向 npmmirror                | 命令加 `--registry=https://registry.npmjs.org/` |
| `403 Two-factor authentication ... required`                                                        | 未开 2FA，或 `--otp` 填了 token             | 开 2FA；`--otp` 填验证器 6 位码                 |
| `refusing to allow a Personal Access Token to create or update workflow ... without workflow scope` | PAT 缺 `workflow`                           | §1.3 加 scope                                   |
| PyPI 上传用账密被拒                                                                                 | 开 2FA 后必须 token                         | 用 `__token__` + API token                      |
| provenance 绿勾不出现                                                                               | 本地发布无 OIDC，或 CI 缺 `id-token: write` | 本地别加 `--provenance`；CI 检查权限块          |
| Trusted Publishing 认证失败                                                                         | 字段大小写/路径不匹配                       | Owner/Repo/Workflow 逐字核对，只填文件名        |
| `fatal: reference is not a tree`（clone 子模块）                                                    | gitlink 指向未推送的本地提交                | 指针改回远端已存在提交（见 `33124fe`）          |
| `Version already exists` / 403                                                                      | 版本号永久占用                              | bump 版本，不可重传                             |

## 7. 不可逆提醒

- 首次上传即**永久占用包名与版本号**；`npm unpublish` / PyPI 删除 release 都不能复用。
- 打 tag 前确认版本号已同步全部字面量（T10 清单），否则 `xlang_verify.py` 会报 `telemetry.sdk.version` 差异。
- 所有对外发布动作须经人工确认后执行；本手册只是清单，不是自动授权。
