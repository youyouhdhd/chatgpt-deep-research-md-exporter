# ChatGPT Deep Research Markdown Exporter Chrome Extension

English | [中文](README.zh-CN.md)

Chrome extension for exporting an open **ChatGPT Deep Research full-screen report** directly from its conversation to **Markdown (.md)** with resolved inline citations.

## Updates in This Fork

This fork (v0.2.15) extends the original extension ([qpwm06/chatgpt-deep-research-md-exporter](https://github.com/qpwm06/chatgpt-deep-research-md-exporter), v0.2.5) with:

- **Working download with correct file names** — downloaded files are named after the detected report title plus a local timestamp, e.g. `gpt-Report Title_2026-10-15_11-02.md`; Chrome ignores the `filename` option of `chrome.downloads.download` (which used to produce blob-UUID file names), so downloads are issued through an anchor `download` attribute with a self-contained data URL instead
- **Fullscreen report detection fix** — the content script is now also injected into the cross-origin report iframe (`*.web-sandbox.oaiusercontent.com`), fixing the "没有识别到当前全屏报告" failure on fullscreen reports
- **Fast structured export path** — the report is rebuilt from the page's embedded data stream in seconds, preserving original LaTeX delimiters and the full citation map; the slow per-citation carousel DOM walk only runs as a fallback
- **Correct report selection in multi-report conversations** — when a conversation contains several Deep Research reports, the payload matching the currently open report's title is selected (visible frames preferred), instead of always exporting the first report
- **Clean citation rendering and numbering** — citations are exported as `[[N](url)]`, rendering as `[1][2][3]` without triggering display-math renderers or Obsidian wikilinks; ChatGPT's conversation-wide citation numbers (which skip values, e.g. 50 → 103) are renumbered into a contiguous sequence
- **References section** — a numbered, clickable reference list is appended at the end, matching the inline citation numbers and showing source titles (panel titles when available, URL-derived `host · path words` otherwise)
- **Regression tests** — 19 Playwright end-to-end tests plus a real-browser download probe (`tests/`)

Search-friendly names:

- ChatGPT Deep Research Markdown Exporter
- ChatGPT Deep Research Export to Markdown Chrome Extension
- ChatGPT Deep Research Citation Exporter
- ChatGPT Conversation Report Exporter

## What It Does

- Exports ChatGPT Deep Research reports to `.md`
- Works directly in a specific ChatGPT conversation; no shared link is required
- Exports only the currently open full-screen report on direct conversation pages
- Keeps legacy structured extraction for compatible shared pages
- Resolves ChatGPT internal research citations into inline Markdown links in the form `[[2](url)]` (brackets outside the link), which renders as a bracketed `[2]`; consecutive citations stay visually separated instead of merging into a digit run, and no `\[` escapes are emitted so math renderers cannot mistake citations for display formulas
- Expands a merged citation into every source card actually present in its carousel, while keeping single-source citations single
- Preserves citation links inside Markdown tables
- Opens ChatGPT's `Show code` view to export Mermaid source instead of rendered SVG markup
- Keeps the output clean for Obsidian, Notion, Typora, and GitHub
- Supports direct download and clipboard copy

## Why This Extension Exists

ChatGPT Deep Research exports may leave citations in ChatGPT-internal form, which is inconvenient outside the original page.

This extension rebuilds the report from the currently open conversation page, so a Deep Research report can be exported without creating a shared link first.

## Supported Page Types

- Direct conversations: `https://chatgpt.com/c/...`
- Project conversations: `https://chatgpt.com/g/.../c/...`
- Compatible legacy shared report pages remain supported as a fallback

## Installation

1. Open `chrome://extensions`
2. Enable `Developer mode`
3. Click `Load unpacked`
4. Select this folder: `chatgpt-deep-research-md-exporter`

## Usage

1. Open the specific ChatGPT conversation containing the Deep Research result
2. Open the report in full-screen view
3. Click the extension icon
4. Optionally set a title prefix, default: `gpt-`
5. Click `Start Detection`
6. If available, click `Fix LaTeX $` to convert `\[ ... \]` or math-only `[ ... ]` blocks to `$$ ... $$`
7. Click `Download Markdown` or `Copy Markdown`

## Output Behavior

- The report is rebuilt from the page's embedded data stream first (seconds, keeps original LaTeX delimiters and the full citation map); the slower per-citation carousel DOM walk only runs when the embedded data is missing or does not match the open report
- Downloaded files are named `report title + export time`, e.g. `gpt-Report Title_2026-10-13_19-30.md`; the report title detected by the extension is used first, and the ChatGPT tab title is only used as a fallback when it is meaningful (not empty and not a machine identifier such as a conversation ID)
- The exported title can be prefixed, default `gpt-`
- Inline citations are converted to Markdown links in the form `[[N](url)]`, which renders as a bracketed `[N]`
- Citation numbers are renumbered to a contiguous sequence by first appearance; ChatGPT's own citation indexes are conversation-wide and can skip numbers (e.g. 50 → 103), so gaps do not survive the export
- A references list is appended at the end (`## References` / `## 参考文献` depending on the report language); each entry is numbered to match the inline citations, links to its source URL, and shows the source title when available, or a readable URL-derived title (`host · path words`) otherwise
- Multiple source cards attached to one citation are exported as distinct numbered links
- Domain-group headers are ignored so unrelated same-domain URLs are not attached to a citation
- Mermaid diagrams are exported from their source-code view
- Full-screen report content is preferred over the surrounding conversation
- User prompts, the composer, and unrelated assistant replies are excluded
- Optional LaTeX correction converts `\[ ... \]` and math-only `[ ... ]` display delimiters while leaving Markdown links, plain bracketed text, and code blocks intact
- Downloads are triggered through an anchor's `download` attribute with a self-contained data URL, which names the file reliably (Chrome ignores the `filename` option of `chrome.downloads.download`, which used to produce blob-UUID file names); the file still downloads correctly even when the Save As dialog closes the popup

## Files

- `manifest.json`: Chrome MV3 extension manifest
- `popup.html` / `popup.css` / `popup.js`: popup UI and export actions
- `content.js`: extraction, citation resolution, and Markdown generation
- `page-bridge.js`: narrowly scoped bridge for ChatGPT's citation tooltip controls
- `diagnostic.html` / `diagnostic.js`: one-click real-page diagnostic exporter used for troubleshooting

## Notes

- This project does not call private OpenAI APIs
- If ChatGPT changes its page structure, selectors or parsing rules may need updates
- Open the full-screen report before exporting for the most reliable result
- Direct conversation export stops with a clear prompt when no full-screen report is open

## Friend Link

- Community friend link: [LINUX DO](https://linux.do)

## Keywords

`ChatGPT Deep Research`, `Deep Research Markdown`, `ChatGPT Chrome Extension`, `ChatGPT citation export`, `conversation report`, `Markdown exporter`, `Chrome extension`
