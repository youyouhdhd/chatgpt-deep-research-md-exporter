const statusNode = document.getElementById('status');
const summaryNode = document.getElementById('summary');
const warningsNode = document.getElementById('warnings');
const startButton = document.getElementById('startButton');
const latexFixButton = document.getElementById('latexFixButton');
const downloadButton = document.getElementById('downloadButton');
const copyButton = document.getElementById('copyButton');
const titlePrefixInput = document.getElementById('titlePrefixInput');
const localeEnButton = document.getElementById('localeEnButton');
const localeZhButton = document.getElementById('localeZhButton');
const heroTitleNode = document.getElementById('heroTitle');
const heroSubtitleNode = document.getElementById('heroSubtitle');
const prefixLabelNode = document.getElementById('prefixLabel');
const tipsTitleNode = document.getElementById('tipsTitle');
const tip1Node = document.getElementById('tip1');
const tip2Node = document.getElementById('tip2');
const tip3Node = document.getElementById('tip3');

let cachedExport = null;
let cachedTabId = null;
let cachedTabUrl = null;
let cachedPrefix = 'gpt-';
let currentLocale = 'en';

const MESSAGES = {
  en: {
    hero_title: 'Markdown Export',
    hero_subtitle: 'Export the open full-screen report from a ChatGPT conversation to `.md`.',
    prefix_label: 'Title Prefix',
    status_idle: 'Open the report full screen, then start detection.',
    status_checking: 'Checking current tab…',
    status_generating: 'Generating Markdown…',
    status_ready: 'Page detected. You can download or copy now.',
    status_download_started: 'Markdown download started.',
    status_copied: 'Markdown copied to clipboard.',
    status_latex_fixed: 'LaTeX display delimiters were converted to `$$`.',
    status_latex_unchanged: 'No LaTeX display formulas using `\\[ ... \\]` or bare `[ ... ]` were found.',
    start_button: 'Start Detection',
    latex_fix_button: 'Fix LaTeX $',
    download_button: 'Download Markdown',
    copy_button: 'Copy Markdown',
    tips_title: 'How To Use',
    tip1: 'Open a specific ChatGPT conversation, then open its Deep Research report full screen.',
    tip2: 'If source URLs are incomplete, expand the page’s Sources panel before exporting.',
    tip3: 'The extension rebuilds Markdown from the page instead of relying on ChatGPT’s default download.',
    summary_title: 'Title',
    summary_sources: 'Source Links',
    summary_citations: 'Inline Citations',
    summary_length: 'Markdown Length',
    summary_latex_fixes: 'LaTeX Fixes Available',
    error_tab: 'No readable active tab was found.',
    error_page: 'Please open a Deep Research report in a ChatGPT conversation first.',
    generic_export_failed: 'Export failed.',
    generic_download_failed: 'Download failed.',
    generic_copy_failed: 'Copy failed.',
  },
  'zh-CN': {
    hero_title: 'Markdown 导出',
    hero_subtitle: '直接把 ChatGPT 对话中已打开的全屏报告导出为 `.md`。',
    prefix_label: '标题前缀',
    status_idle: '请先打开目标报告的全屏视图，然后点击开始识别。',
    status_checking: '正在检查当前标签页…',
    status_generating: '正在生成 Markdown…',
    status_ready: '页面已识别，可以下载或复制。',
    status_download_started: 'Markdown 已开始下载。',
    status_copied: 'Markdown 已复制到剪贴板。',
    status_latex_fixed: '已将 LaTeX 行间公式分隔符转换为 `$$`。',
    status_latex_unchanged: '没有发现使用 `\\[ ... \\]` 或裸 `[ ... ]` 的 LaTeX 行间公式。',
    start_button: '开始识别',
    latex_fix_button: 'LaTeX $ 修正',
    download_button: '下载 Markdown',
    copy_button: '复制 Markdown',
    tips_title: '使用说明',
    tip1: '进入具体 ChatGPT 对话，并先把其中的 Deep Research 报告全屏打开。',
    tip2: '如果来源 URL 提取不全，先把页面中的 Sources 区域展开后再导出。',
    tip3: '扩展不会调用 ChatGPT 自带下载，而是直接从页面内容生成 Markdown。',
    summary_title: '标题',
    summary_sources: '来源链接',
    summary_citations: '文内引用',
    summary_length: 'Markdown 长度',
    summary_latex_fixes: '可修正 LaTeX',
    error_tab: '没有可用的当前标签页。',
    error_page: '请先进入具体 ChatGPT 对话并打开 Deep Research 全屏报告。',
    generic_export_failed: '导出失败。',
    generic_download_failed: '下载失败。',
    generic_copy_failed: '复制失败。',
  },
};

function t(key) {
  return MESSAGES[currentLocale]?.[key] || MESSAGES.en[key] || key;
}

async function readStoredPrefix() {
  try {
    return String(localStorage.getItem('titlePrefix') || 'gpt-');
  } catch {
    return 'gpt-';
  }
}

async function writeStoredPrefix(prefix) {
  try {
    localStorage.setItem('titlePrefix', prefix);
  } catch {}
}

async function readStoredLocale() {
  try {
    const stored = String(localStorage.getItem('uiLocale') || 'en');
    return stored === 'zh-CN' ? 'zh-CN' : 'en';
  } catch {
    return 'en';
  }
}

async function writeStoredLocale(locale) {
  try {
    localStorage.setItem('uiLocale', locale);
  } catch {}
}

function applyLocale() {
  document.documentElement.lang = currentLocale;
  document.title = currentLocale === 'zh-CN' ? 'Deep Research 导出' : 'Deep Research Export';
  heroTitleNode.textContent = t('hero_title');
  heroSubtitleNode.textContent = t('hero_subtitle');
  prefixLabelNode.textContent = t('prefix_label');
  startButton.textContent = t('start_button');
  latexFixButton.textContent = t('latex_fix_button');
  downloadButton.textContent = t('download_button');
  copyButton.textContent = t('copy_button');
  tipsTitleNode.textContent = t('tips_title');
  tip1Node.textContent = t('tip1');
  tip2Node.textContent = t('tip2');
  tip3Node.textContent = t('tip3');
  localeEnButton.classList.toggle('active', currentLocale === 'en');
  localeZhButton.classList.toggle('active', currentLocale === 'zh-CN');
}

async function loadLocale() {
  currentLocale = await readStoredLocale();
  applyLocale();
}

async function saveLocale(locale) {
  currentLocale = locale === 'zh-CN' ? 'zh-CN' : 'en';
  await writeStoredLocale(currentLocale);
  applyLocale();
}

async function loadPrefix() {
  cachedPrefix = await readStoredPrefix();
  titlePrefixInput.value = cachedPrefix;
}

async function savePrefix(prefix) {
  cachedPrefix = String(prefix || '');
  await writeStoredPrefix(cachedPrefix);
}

function currentPrefix() {
  return String(titlePrefixInput.value || '').trim();
}

function setBusy(isBusy) {
  startButton.disabled = isBusy;
  latexFixButton.disabled = isBusy || !cachedExport || countLatexDisplayDelimiters(cachedExport.markdown) === 0;
  downloadButton.disabled = isBusy || !cachedExport;
  copyButton.disabled = isBusy || !cachedExport;
}

function setStatus(message) {
  statusNode.textContent = message;
}

function countLatexDisplayDelimiters(markdown) {
  return fixLatexDisplayDelimiters(markdown).replacementCount;
}

function looksLikeBareLatexFormula(formula) {
  const text = String(formula || '').trim();
  if (!text || /^https?:\/\//i.test(text)) return false;
  // 引用链接（形如 [N](url)）不是公式，即使 URL 里带下划线等公式特征字符。
  if (/\]\(/.test(text) || /https?:\/\//i.test(text)) return false;
  return (
    /\\[A-Za-z]+/.test(text)
    || /[_^]\s*(?:\{|[A-Za-z0-9])/.test(text)
    || /[=+*/<>]|(?:^|\s)-(?:\s|$)/.test(text)
  );
}

function fixLatexInMarkdownText(markdown) {
  let replacementCount = 0;
  let fixed = String(markdown || '').replace(/\\\[\s*([\s\S]*?)\s*\\\]/g, (_match, formula) => {
    replacementCount += 1;
    return `$$\n${String(formula || '').trim()}\n$$`;
  });

  fixed = fixed.replace(/(^|\n)[ \t]*\[\s*([^\n]*?)\s*\][ \t]*(?=\n|$)/g, (match, leadingNewline, formula) => {
    if (!looksLikeBareLatexFormula(formula)) return match;
    replacementCount += 1;
    return `${leadingNewline}$$\n${String(formula || '').trim()}\n$$`;
  });

  return { markdown: fixed, replacementCount };
}

function fixLatexDisplayDelimiters(markdown) {
  let replacementCount = 0;
  const parts = String(markdown || '').split(/(```[\s\S]*?```|~~~[\s\S]*?~~~)/g);
  const fixed = parts.map((part) => {
    if (/^(?:```|~~~)/.test(part)) return part;
    const result = fixLatexInMarkdownText(part);
    replacementCount += result.replacementCount;
    return result.markdown;
  }).join('');

  return { markdown: fixed, replacementCount };
}

function renderSummary(result) {
  const lines = [
    `${t('summary_title')}: ${result.title || '-'}`,
    `${t('summary_sources')}: ${result.sourceCount}`,
    `${t('summary_citations')}: ${result.citationCount}`,
    `${t('summary_length')}: ${result.markdown.length}`,
    `${t('summary_latex_fixes')}: ${countLatexDisplayDelimiters(result.markdown)}`,
  ];

  summaryNode.innerHTML = '';
  for (const line of lines) {
    const row = document.createElement('div');
    row.textContent = line;
    summaryNode.appendChild(row);
  }
  summaryNode.classList.remove('hidden');
}

function renderWarnings(warnings) {
  if (!warnings || warnings.length === 0) {
    warningsNode.classList.add('hidden');
    warningsNode.textContent = '';
    return;
  }

  warningsNode.textContent = warnings.join('\n');
  warningsNode.classList.remove('hidden');
}

async function getActiveTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  return tabs[0] || null;
}

function isDirectConversationUrl(url) {
  try {
    return /(?:^|\/)c\/[a-z0-9-]+(?:\/|$)/i.test(new URL(url).pathname);
  } catch {
    return false;
  }
}

function normalizedCompareText(value) {
  return String(value || '')
    .replace(/\s+/g, ' ')
    .replace(/[：:]+$/g, '')
    .trim()
    .toLowerCase();
}

function titlesReferToSameReport(candidate, heading) {
  const left = normalizedCompareText(candidate);
  const right = normalizedCompareText(heading);
  if (!left || !right) return false;
  if (left === right) return true;
  // 渲染出来的标题可能被截断或追加了说明文字，双向包含即视为同一份报告。
  const shorter = left.length < right.length ? left : right;
  const longer = left.length < right.length ? right : left;
  return shorter.length >= 6 && longer.includes(shorter);
}

async function collectReportFrameHeadings(tab, orderedFrameIds) {
  const entries = [];
  for (const frameId of orderedFrameIds) {
    try {
      const response = await chrome.tabs.sendMessage(tab.id, {
        type: 'DEEP_RESEARCH_REPORT_HEADING',
      }, { frameId });
      if (response?.ok && normalizedCompareText(response.heading)) {
        entries.push({
          frameId,
          heading: String(response.heading || ''),
          visible: response.visible !== false,
        });
      }
    } catch {}
  }
  return entries;
}

async function tryStructuredFastPath(tab, message, headingEntries) {
  // 同一会话可能包含多份深度调研：内嵌数据流里第一份不一定是当前打开的那份。
  // 先取"可见"报告 frame 的标题锁定目标，再让顶层按标题选出对应的 payload。
  const open = headingEntries.find((entry) => entry.visible) || headingEntries[0];
  if (!open) return null;

  let structured = null;
  try {
    structured = await chrome.tabs.sendMessage(tab.id, {
      type: 'DEEP_RESEARCH_EXPORT_STRUCTURED_REPORT',
      titlePrefix: message?.titlePrefix,
      sourceUrl: message?.sourceUrl,
      matchTitle: open.heading,
    }, { frameId: 0 });
  } catch {
    return null;
  }
  if (!structured?.ok || !structured?.result?.markdown) return null;

  // citation 映射未命中时 payload 数据不完整，交给 DOM 路径兜底。
  const citationCount = Number(structured.result.citationCount) || 0;
  if (citationCount === 0) return null;

  const prefix = String(message?.titlePrefix || '').trim();
  const rawTitle = String(structured.result.title || '');
  const candidate = prefix && rawTitle.startsWith(prefix) ? rawTitle.slice(prefix.length) : rawTitle;
  if (!normalizedCompareText(candidate)) return null;
  // 双保险：选中的 payload 标题必须仍与打开的报告标题对应。
  if (!titlesReferToSameReport(candidate, open.heading)) return null;
  return structured;
}

async function sendExportMessage(tab, message) {
  if (!isDirectConversationUrl(tab.url) || !chrome.webNavigation?.getAllFrames) {
    return chrome.tabs.sendMessage(tab.id, message);
  }

  let frames = [];
  try {
    frames = await chrome.webNavigation.getAllFrames({ tabId: tab.id }) || [];
  } catch {}

  // ChatGPT 的报告沙箱域名可能调整；按特征识别报告 frame，而不是写死单一 host。
  const isReportFrameUrl = (url) => /deep-research|web-sandbox\.oaiusercontent\.com/i.test(String(url || ''));
  const orderedFrameIds = frames
    .sort((left, right) => {
      const leftReport = isReportFrameUrl(left.url) ? 1 : 0;
      const rightReport = isReportFrameUrl(right.url) ? 1 : 0;
      if (leftReport !== rightReport) return rightReport - leftReport;
      if (left.frameId === 0) return 1;
      if (right.frameId === 0) return -1;
      return left.frameId - right.frameId;
    })
    .map((frame) => frame.frameId)
    .filter((frameId, index, items) => Number.isInteger(frameId) && items.indexOf(frameId) === index);

  if (!orderedFrameIds.includes(0)) orderedFrameIds.push(0);

  let openedSources = false;
  // 控制按钮与报告正文可能分属父子 frame；先跨 frame 展开来源，再读取正文。
  for (const frameId of orderedFrameIds) {
    try {
      const response = await chrome.tabs.sendMessage(tab.id, {
        type: 'DEEP_RESEARCH_OPEN_SOURCES',
      }, { frameId });
      openedSources ||= response?.openedSources === true;
    } catch {}
  }
  if (openedSources) {
    await new Promise((resolve) => window.setTimeout(resolve, 1000));
  }

  // 快路径：顶层页面的内嵌 payload 含报告原始 Markdown（LaTeX 完整）与完整引用映射。
  // 同一会话多份报告时，按"可见报告 frame 的标题"选出当前打开的那一份，
  // 避免逐个打开 citation 轮播（上百处引用需一两分钟）的同时避免错选第一份。
  let headingEntries = [];
  if (message?.type === 'DEEP_RESEARCH_EXPORT_MARKDOWN') {
    headingEntries = await collectReportFrameHeadings(tab, orderedFrameIds);
    const fastResponse = await tryStructuredFastPath(tab, message, headingEntries);
    if (fastResponse) return fastResponse;
  }

  let lastError = null;
  const failedResponses = [];
  // Deep Research 正文位于跨域 iframe；逐帧请求可避免顶层错误抢先覆盖正确结果。
  // 未打开（不可见）的报告 frame 排到最后：隐藏的旧报告 iframe 若先命中会把导出
  // 指向错误的那一份报告。
  const hiddenFrameIds = new Set(
    headingEntries.filter((entry) => !entry.visible).map((entry) => entry.frameId),
  );
  const exportFrameOrder = hiddenFrameIds.size > 0
    ? [
        ...orderedFrameIds.filter((frameId) => !hiddenFrameIds.has(frameId)),
        ...orderedFrameIds.filter((frameId) => hiddenFrameIds.has(frameId)),
      ]
    : orderedFrameIds;
  for (const frameId of exportFrameOrder) {
    try {
      const response = await chrome.tabs.sendMessage(tab.id, message, { frameId });
      if (response?.ok) return response;
      if (response) failedResponses.push(response);
    } catch (error) {
      lastError = error;
    }
  }

  if (failedResponses.length > 0) {
    // 跨域报告 frame 排在最前，其错误最接近真实原因；与其余 frame 的错误去重后合并展示。
    const errors = [];
    for (const response of failedResponses) {
      const messageText = String(response?.error || '').trim();
      if (messageText && !errors.includes(messageText)) errors.push(messageText);
    }
    return { ok: false, error: errors.join('｜') || null };
  }
  throw lastError || new Error(t('generic_export_failed'));
}

async function requestExport(force = false) {
  const tab = await getActiveTab();
  if (!tab?.id || !tab.url) {
    throw new Error(t('error_tab'));
  }

  if (!/^https:\/\/(chatgpt\.com|chat\.openai\.com)\//i.test(tab.url)) {
    throw new Error(t('error_page'));
  }

  if (!force && cachedExport && cachedTabId === tab.id && cachedTabUrl === tab.url) {
    return cachedExport;
  }

  const response = await sendExportMessage(tab, {
    type: 'DEEP_RESEARCH_EXPORT_MARKDOWN',
    titlePrefix: currentPrefix(),
    sourceUrl: tab.url,
  });

  if (!response?.ok) {
    throw new Error(response?.error || t('generic_export_failed'));
  }

  cachedTabId = tab.id;
  cachedTabUrl = tab.url;
  cachedExport = response.result;
  return response.result;
}

function buildDownloadDataUrl(markdown) {
  const bytes = new TextEncoder().encode(String(markdown || ''));
  // 大报告分块转 base64，避免 String.fromCharCode 一次展开超限。
  const CHUNK_SIZE = 8192;
  let binary = '';
  for (let index = 0; index < bytes.length; index += CHUNK_SIZE) {
    binary += String.fromCharCode(...bytes.subarray(index, index + CHUNK_SIZE));
  }
  return `data:text/markdown;charset=utf-8;base64,${btoa(binary)}`;
}

// Chrome 会忽略 chrome.downloads.download 的 filename 参数（blob 会被存成
// blob UUID 文件名），而 anchor 的 download 属性可以正确命名；data URL 自包含，
// 即使“另存为”对话框导致扩展弹窗关闭，下载也能完成。
function triggerNamedDownload(url, filename) {
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
}

function sanitizeFilename(name) {
  const cleaned = String(name || 'deep-research-report')
    .replace(/[\\/:*?"<>|]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 120);

  return `${cleaned || 'deep-research-report'}.md`;
}

function cleanConversationTitle(rawTitle) {
  let text = String(rawTitle || '').trim();
  if (!text) return '';
  text = text
    .replace(/\s*[|–—-]\s*ChatGPT\s*$/i, '')
    .replace(/^\s*ChatGPT\s*[|–—-]\s*/i, '')
    .trim();
  if (!text || /^(chatgpt|new chat|新的聊天)$/i.test(text)) return '';
  return text;
}

function looksLikeMachineIdentifier(text) {
  const value = String(text || '').trim();
  if (!value) return true;
  // 会话 UUID、无空格的长字母数字横线串等机器标识不适合当文件名，应退回报告标题。
  if (/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)) return true;
  if (value.length >= 16 && /^[0-9a-z_-]+$/i.test(value)) return true;
  const digits = (value.match(/\d/g) || []).length;
  const alnum = (value.match(/[0-9a-z]/gi) || []).length;
  if (value.length >= 16 && digits >= 4 && alnum === value.length) return true;
  return false;
}

function formatFileTimestamp(date = new Date()) {
  const pad = (value) => String(value).padStart(2, '0');
  return [
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`,
    `${pad(date.getHours())}-${pad(date.getMinutes())}`,
  ].join('_');
}

// 文件名优先使用插件识别出的报告标题（与检测摘要一致、最可靠）；
// 识别标题缺失时退回会话标题，且会话标题形似机器 ID 时不用。
function buildDownloadFilename(tab, result) {
  const reportTitle = String(result?.title || '').trim();
  const conversationTitle = cleanConversationTitle(tab?.title);
  const base = reportTitle
    || (conversationTitle && !looksLikeMachineIdentifier(conversationTitle)
      ? `${currentPrefix()}${conversationTitle}`
      : '')
    || 'Deep Research Report';
  return sanitizeFilename(`${base}_${formatFileTimestamp()}`);
}

async function downloadMarkdown() {
  setBusy(true);
  setStatus(t('status_generating'));

  try {
    const result = await requestExport(false);
    renderSummary(result);
    renderWarnings(result.warnings);

    const tab = await getActiveTab();
    const filename = buildDownloadFilename(tab, result);
    triggerNamedDownload(buildDownloadDataUrl(result.markdown), filename);
    setStatus(t('status_download_started'));
  } catch (error) {
    setStatus(error instanceof Error ? error.message : String(error || t('generic_download_failed')));
  } finally {
    setBusy(false);
  }
}

async function copyMarkdown() {
  setBusy(true);
  setStatus(t('status_generating'));

  try {
    const result = await requestExport(false);
    renderSummary(result);
    renderWarnings(result.warnings);
    await navigator.clipboard.writeText(result.markdown);
    setStatus(t('status_copied'));
  } catch (error) {
    setStatus(error instanceof Error ? error.message : String(error || t('generic_copy_failed')));
  } finally {
    setBusy(false);
  }
}

function fixCachedLatex() {
  if (!cachedExport) return;

  const fixed = fixLatexDisplayDelimiters(cachedExport.markdown);
  if (fixed.replacementCount === 0) {
    setStatus(t('status_latex_unchanged'));
    setBusy(false);
    return;
  }

  cachedExport = { ...cachedExport, markdown: fixed.markdown };
  renderSummary(cachedExport);
  setStatus(`${t('status_latex_fixed')} (${fixed.replacementCount})`);
  setBusy(false);
}

async function inspectCurrentTab() {
  cachedExport = null;
  cachedTabId = null;
  cachedTabUrl = null;
  setBusy(true);
  setStatus(t('status_checking'));

  try {
    const result = await requestExport(true);
    renderSummary(result);
    renderWarnings(result.warnings);
    setStatus(t('status_ready'));
  } catch (error) {
    cachedExport = null;
    cachedTabId = null;
    cachedTabUrl = null;
    renderWarnings([]);
    summaryNode.classList.add('hidden');
    setStatus(error instanceof Error ? error.message : String(error || t('generic_export_failed')));
  } finally {
    setBusy(false);
  }
}

startButton.addEventListener('click', inspectCurrentTab);
latexFixButton.addEventListener('click', fixCachedLatex);
downloadButton.addEventListener('click', downloadMarkdown);
copyButton.addEventListener('click', copyMarkdown);
localeEnButton.addEventListener('click', async () => {
  await saveLocale('en');
});
localeZhButton.addEventListener('click', async () => {
  await saveLocale('zh-CN');
});
titlePrefixInput.addEventListener('change', async () => {
  await savePrefix(currentPrefix());
  cachedExport = null;
  cachedTabId = null;
  cachedTabUrl = null;
  renderWarnings([]);
  summaryNode.classList.add('hidden');
  setStatus(t('status_idle'));
  setBusy(false);
});
document.addEventListener('DOMContentLoaded', async () => {
  await loadLocale();
  await loadPrefix();
  setStatus(t('status_idle'));
  setBusy(false);
});

// 仅供真实 Chrome 回归测试使用；普通扩展弹窗不会带 reload 参数。
if (new URLSearchParams(location.search).get('reload') === '1') {
  document.title = 'Reloading extension';
  window.setTimeout(() => chrome.runtime.reload(), 100);
}
