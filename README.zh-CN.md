# ChatGPT Deep Research Markdown Exporter Chrome 插件

[English](README.md) | 中文

用于从具体 ChatGPT 对话中直接导出已打开的 **Deep Research 全屏报告**，生成 **Markdown (.md)** 并将内部引用解析为可点击链接。

## 本 Fork 的更新

本 fork（v0.2.17）基于原版插件（[qpwm06/chatgpt-deep-research-md-exporter](https://github.com/qpwm06/chatgpt-deep-research-md-exporter)，v0.2.5）增强，主要区别：

- **可用的下载与正确文件名** — 下载文件以插件识别出的报告标题 + 本地时间命名，如 `gpt-电子围栏技术调研报告_2026-10-15_11-02.md`；Chrome 会忽略 `chrome.downloads.download` 的 `filename` 参数（导致文件名变成 blob UUID 乱码），因此改用 anchor `download` 属性 + 自包含 data URL 实现可靠命名
- **全屏报告识别修复** — 内容脚本注入扩展到跨域报告 iframe（`*.web-sandbox.oaiusercontent.com`），解决"没有识别到当前全屏报告"的识别失败
- **秒级结构化快速路径** — 优先从页面内嵌数据流重建报告，保留原始 LaTeX 定界符与完整引用映射；逐个展开 citation 轮播的 DOM 慢速方式仅作回退
- **多报告会话正确选择** — 同一会话包含多份深度调研时，按当前打开报告的标题（优先可见的报告 frame）选择对应数据，不再总是导出第一份报告；展开来源面板的点击只在上 DOM 兜底时发生、且限定在当前全屏层内，不会再把 ChatGPT 视图切换到其他报告
- **引用渲染与编号** — 引用输出为 `[[N](url)]`，渲染为 `[1][2][3]`，不会触发数学渲染器的行间公式误判或 Obsidian wikilink；ChatGPT 会话级稀疏编号（如 50 跳到 103）会重排为连续序列
- **文末参考文献列表** — 自动追加编号与正文引用一一对应、可点击的参考文献列表，并显示来源标题（有真实标题用真实标题，否则用 URL 派生的 `域名 · 路径词`）
- **回归测试** — 19 项 Playwright 端到端测试与真实浏览器下载探针（`tests/`）

便于搜索的名称：

- ChatGPT Deep Research Markdown Exporter
- ChatGPT Deep Research 导出 Markdown Chrome 插件
- ChatGPT Deep Research 引用导出插件
- ChatGPT 对话报告导出 Markdown

## 功能说明

- 将 ChatGPT Deep Research 报告导出为 `.md`
- 直接在具体 ChatGPT 对话中工作，不需要先生成分享或邀请链接
- 在具体对话页只提取当前打开的全屏报告，不再自动选择最后一条助手消息
- 继续兼容能够提供结构化报告数据的旧分享页
- 将 ChatGPT 内部研究引用转换为正文内联 Markdown 链接，形如 `[[2](url)]`（中括号在链接外侧，渲染为带中括号的 `[2]`），连续引用不会粘连成一串数字，且不产生 `\[` 转义、不会被数学渲染器误认成行间公式
- 按 citation 轮播中实际存在的来源卡片拆分合并引用，单来源 citation 仍只导出一个链接
- 保留 Markdown 表格内的 citation 链接
- 自动打开 ChatGPT 的“显示代码”视图，导出 Mermaid 源码而不是渲染后的 SVG
- 导出结果更适合导入 Obsidian、Notion、Typora、GitHub
- 支持直接下载和复制到剪贴板

## 为什么要做这个插件

ChatGPT Deep Research 默认导出有时会保留 ChatGPT 内部引用格式，离开原页面后不方便使用。

这个插件会直接从当前对话页面重建报告，因此无需先创建分享链接，也能导出带可点击引用的 Markdown 文档。

## 支持页面类型

- 普通具体对话：`https://chatgpt.com/c/...`
- 项目内具体对话：`https://chatgpt.com/g/.../c/...`
- 兼容的旧版报告分享页仍作为后备路径保留

## 安装方法

1. 打开 `chrome://extensions`
2. 打开 `开发者模式`
3. 点击 `加载已解压的扩展程序`
4. 选择目录：`chatgpt-deep-research-md-exporter`

## 使用方法

1. 打开包含 Deep Research 结果的具体 ChatGPT 对话
2. 将报告打开为全屏视图
3. 点击插件图标
4. 可选设置标题前缀，默认：`gpt-`
5. 可选选择导出方式：`自动`（默认，优先快速内嵌数据、失败转 DOM）、`仅快速`（内嵌数据未命中时直接报错）、`仅 DOM`（始终按渲染页面逐个展开，慢但与屏幕内容一致）
6. 点击 `开始识别`
7. 如果按钮可用，可点击 `LaTeX $ 修正`，将 `\[ ... \]` 或仅含数学内容的 `[ ... ]` 块转换为 `$$ ... $$`
8. 点击 `下载 Markdown` 或 `复制 Markdown`

## 导出行为

- 导出方式可在弹窗中选择：自动模式优先从页面内嵌数据流直接重建报告（秒级完成、保留原始 LaTeX 分隔符与完整引用映射），仅当内嵌数据缺失或与当前打开的报告不一致时才退回逐个展开 citation 轮播的 DOM 方式；仅快速模式不做回退；仅 DOM 模式完全跳过内嵌数据
- 下载文件名使用 `报告标题 + 导出时间`，例如 `gpt-报告标题_2026-10-13_19-30.md`；优先使用插件识别出的报告标题，浏览器标签页标题仅在有意义时（非空且不是会话 ID 等机器标识）作为兜底
- 导出的标题可加前缀，默认 `gpt-`
- 正文引用会转换成 `[[N](url)]` 形式的 Markdown 内联链接（中括号在链接外侧），渲染为带中括号的 `[N]`
- 引用编号按正文首次出现顺序重排为连续序列；ChatGPT 原始编号是会话级的、中间可能有空洞（如 50 跳到 103），导出后会自动消除跳号
- 文末自动追加参考文献列表（`## 参考文献` 或 `## References`，按报告语言选择）；条目编号与正文引用一一对应、可点击跳转来源，并带来源标题——有真实标题（来源面板）时用真实标题，否则用 URL 派生的可读标题（`域名 · 路径词`）
- 一个 citation 对应多张来源卡片时，会导出为多个独立编号链接
- 忽略域名分组顶部链接，避免把同域名下的无关 URL 绑定到 citation
- Mermaid 图表从源码视图导出
- 全屏报告正文优先于外围聊天内容
- 用户提问、输入框和无关助手回复不会进入导出结果
- 可选的 LaTeX 修正支持 `\[ ... \]` 和仅含数学内容的 `[ ... ]`，不会修改 Markdown 链接、普通方括号文本或代码块
- 下载通过 anchor 的 `download` 属性 + 自包含 data URL 触发，文件名可靠生效（Chrome 会忽略 `chrome.downloads.download` 的 `filename` 参数，曾导致 blob UUID 文件名）；即使“另存为”对话框导致扩展弹窗关闭，下载也能完成

## 文件说明

- `manifest.json`: Chrome MV3 插件清单
- `popup.html` / `popup.css` / `popup.js`: 弹窗界面与导出交互
- `content.js`: 报告提取、引用解析与 Markdown 生成逻辑
- `page-bridge.js`: 用于控制 ChatGPT citation tooltip 的受限页面桥接脚本
- `diagnostic.html` / `diagnostic.js`: 一键真实页面诊断导出，用于排查问题

## 注意事项

- 本项目不调用 OpenAI 私有接口
- 如果 ChatGPT 页面结构后续调整，可能需要更新选择器或解析规则
- 为获得最稳定的结果，请先打开全屏报告再导出
- 未打开全屏报告时会明确提示，不会从多轮会话中猜测目标报告

## 友链

- 社区友链：[LINUX DO](https://linux.do)

## 关键词

`ChatGPT Deep Research`, `Deep Research Markdown`, `ChatGPT Chrome Extension`, `ChatGPT 引用导出`, `对话报告`, `Markdown 导出`, `Chrome 插件`
