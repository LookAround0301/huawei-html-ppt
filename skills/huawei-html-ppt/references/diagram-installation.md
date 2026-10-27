# 绘图依赖：只读预检 → 询问 → 安装 → 自检

此流程由 `scripts/diagram_adapter/doctor.py` 和宿主 Agent 协作。doctor **只读、不下载、不安装、不运行绘图源码**；它不拥有宿主调度能力，也不会把 `install: true`、任务配置或生成的安装计划当成用户同意。

## 可复用安装引导 Prompt

> 在调用独立绘图能力前，先运行 `diagram-doctor` 做只读预检，读取固定 dependency lock 和原仓运行说明。依赖已满足就直接继续，不重复询问安装。先检查 common 依赖；独立绘图 Agent 选定 report / drawio / tikz 后，再做对应后端预检，不为一个后端安装全部后端。
>
> 若有缺失，先整理组件、官方来源、准确版本/哈希、目标环境和安装目录、下载/磁盘规模与潜在影响、选用后端，以及可复用的已有包/缓存。未被上游固定的操作系统包版本需要先查明并披露，不编造“固定版本”。不要先执行安装再补问。向用户明确询问“是否按这份方案安装到这个位置？”
>
> 只有获得当前对话对这份具体方案的明确确认，才执行列出的正常安装步骤。确认不等于允许任意后续下载、sudo、改安全设置或覆盖文件；方案、位置或权限变化时重新征求同意。拒绝时保持 blocked，不降级成简陋图，不反复询问同一个已拒绝且未变更的方案。
>
> 安装后重新运行只读 doctor，再执行独立仓记录的最小后端自检。工具存在不等于渲染能成功；记录实际结果后继续原绘图任务。若平台缺乏安装权限、网络或独立 Agent 调度能力，准确报告缺口；一条 Prompt 不保证宿主能执行。

## 只读命令

```sh
python skills/huawei-html-ppt/scripts/ppt.py diagram-doctor doctor-request.json
```

示例请求：

```json
{
  "infra_root": "/project/tools/infra-io-generator-pinned",
  "backend": "common",
  "agent_dispatch_available": true
}
```

`backend` 可为 `common`、`report`、`drawio`、`tikz`。没有 `infra_root` 时读取 `INFRA_IO_ROOT`；缺失也只报告，不创建目录。调度能力值来自实际宿主工具清单，不凭配置变成能力。宿主可记录已拒绝状态 `installation_decision: "declined"`；这只阻止重复询问，不授予任何权限。

结果列出 checks 和 install_plan，`installation_executed` 恒为 false。`ready_for_workflow` 仅指本次静态检查条件满足，不是渲染/视觉通过。`plan_requires_resolution` 表示仍须把平台版本、明确位置、下载规模与影响补齐后询问；输出不是自动执行脚本。

## 组件和安装边界

| 范围 | 检查与来源 | 位置 / 影响 |
|---|---|---|
| 全部 | Git、Python ≥3.10、独立仓固定 commit、其 requirements.txt 精确 pins | 独立版本目录和项目 venv；不替换系统 Python |
| 高层交付/PDF | `pdfinfo`、`pdftotext`（[Poppler](https://poppler.freedesktop.org/)） | 复用已有工具；平台版本先披露 |
| 视觉检查/报告导出 | [Inkscape](https://inkscape.org/release/) | 复用已安装版本；是否可启动另做自检 |
| draw.io | Node ≥20、仓库 lock 中的 Playwright、Chromium、固定 Graph bundle 哈希 | 浏览器缓存与磁盘开销单独列明；不因启动失败关闭安全沙箱 |
| TikZ | [TeX Live](https://tug.org/texlive/)、XeLaTeX、standalone、TikZ/PGF、fontspec、所用字体、Poppler 导出工具 | 完整 TeX 可能很大，先复用合法现成包/格式；不要为画一张图盲装整套 |
| 调度 | 宿主真实独立 Agent 工具 | **不能通过 pip/npm 安装补齐**；缺少即 blocked |

Git doctor 禁用可选 index 锁和 fsmonitor，不执行 checkout/reset/clean。dirty checkout 或版本不同只报告，保留用户修改；优先使用另一个已确认的版本目录，不覆盖现有仓。忽略目录中的已有运行缓存可复用；不要为了预检清空缓存。TeX `TEXMF` / `TEXFORMATS` 可指向已有合法资源；在任务目录生成新格式/缓存属于会写盘的安装配置步骤，必须包含在已确认方案里，doctor 不执行。

## 确认后的可执行步骤示例

下列只是一份待用户确认的 POSIX 环境模板，不会被 doctor 调用。`DEST`、`VENV` 必须先替换为用户确认的新路径；`PIN` 必须来自当前 lock。先检查路径不存在，不能把升级写成 `git reset --hard`。

```sh
# 仅在已获得本次方案确认后执行；路径已有内容时停止并复用/另选，不覆盖。
test ! -e "$DEST" && test ! -e "$VENV" || exit 1
git clone --no-checkout https://github.com/grandolantow/infra-io-generator.git "$DEST"
git -C "$DEST" checkout --detach "$PIN"
python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install -r "$DEST/requirements.txt"
# 后续用该 venv Python 调用主工具，INFRA_IO_ROOT 指向 DEST。
```

执行前披露 pip 安装可能下载并构建依赖代码，核对 requirements 来源与 pins。Windows 使用相应 venv `Scripts/python.exe` 及 Git，不能照抄 POSIX 路径判断。已有可用 venv 不应重新创建；先读版本再决定复用或另建。

只有选择 draw.io 后端且用户批准对应下载，才按固定仓的 package-lock 执行项目内 `npm ci --ignore-scripts`，再按原仓运行说明配置/安装匹配浏览器。安装浏览器是额外下载，不由 npm 存在自动授权。已有 `PLAYWRIGHT_MODULE`、`CHROME_BINARY` 与匹配缓存优先复用；Graph bundle 必须满足其 manifest 哈希，不下载浮动 dev 文件替代。

Inkscape、Poppler、TeX 与字体没有跨平台通用无权限安装命令。宿主应使用官方发行包或已批准的平台包管理器，先给出确切包版本/位置/影响，再询问；需要管理员权限时单独停下请求或交由用户处理，不能自行 sudo。TeX 首先区分“包未安装”与“已有包但格式/cache 未配置”，只在允许目录做已确认配置，不读取禁止目录、不改系统权限。

## 恢复原绘图任务

1. 重新执行同 backend 的 doctor；满足的项目不再次询问安装。
2. 按独立仓运行说明在新任务输出目录做最小 render 自检；记录实际退出码/产物，失败不称完成。
3. 恢复原 brief 和独立绘图 Agent 工作流，多方案/源/QA/PDF要求不因安装受阻而缩水。
4. 依赖版本升级须审查并更新固定 lock，保留旧任务产物；不能让新安装覆盖历史图或已验证版本。
